"""Study SEL-NIGHT + SEL-NIGHT-B: night-leg selection tie-breaks (see round1_prose.md).

SEL-NIGHT: the duplicate-bet survivor rule. The live dedupe (`signals.dedupe_correlated`)
walks picks in `day_ret` ascending order and keeps the first of a correlated group
("most beaten"). SEL-NIGHT replays the frozen live rule on Sharadar SEP+SFP
(1999-2026, delisted included) under alternative walk orders:
  current  day_ret asc (most-beaten first)   A1 day_ret desc (least-beaten)
  A2 vol20 desc   A3 vol20 asc   A4 price asc   A5 adv20 desc   A6 random (placebo)
and compares the per-night leg return of each rule, plus the exact pair-level deltas
for pairs where rules disagree.

SEL-NIGHT-B: cash-starvation order. Replays the SAME kept picks at a binding cash pool
(kappa x needed) and compares buy orders: current day_ret asc / price asc / tilt desc / random.

Live rule as of config.yaml 2026-10-18 (cap 0.15): day_ret<=-8%, IBS<0.10, px 5-2000,
ADV20>=10M, vol20>=0.60, crowd_n 30, max_corr 0.7, tilt v1 k 0.25, weekend x0.5.

Run:  PYTHONPATH=. .venv/bin/python research/sim/sel_night.py [--quick]
Out:  data/research/program/sel_night_out.txt
      data/research/program/sel_night_nights_{which}.parquet   (leg per night per rule)
      data/research/program/sel_night_names_current.parquet    (kept names, current rule + r)
      data/research/program/sel_night_pairs.parquet            (dropped/kept pairs + both r)
"""
from __future__ import annotations

import argparse
import pathlib
import time

import numpy as np
import pandas as pd

from research.sim import nx
from swingtrader.daily import signals as sg

ROOT = pathlib.Path(__file__).resolve().parents[2]
STORE = pathlib.Path.home() / "data" / "sharadar"
PROG = ROOT / "data" / "research" / "program"

LO = pd.Timestamp("1999-01-04")
HI = pd.Timestamp("2026-09-30")
FULL_CHUNKS = [("1999-01-04", "2005-12-31"), ("2006-01-01", "2012-12-31"),
               ("2013-01-01", "2019-12-31"), ("2020-01-01", "2026-09-30")]
QUICK_CHUNKS = [("2015-01-01", "2016-12-31"), ("2020-01-01", "2021-06-30")]

# live rule constants (config.yaml 2026-10-18; NAME_CAP 0.15 per user 2026-10-10)
DAY_RET_MAX, IBS_MAX, PRICE_MIN, PRICE_MAX = -0.08, 0.10, 5.0, 2000.0
ADV_MIN, VOL_MIN, CROWD_N, MAX_CORR = 1e7, 0.60, 30, 0.7
TILT_K, WEEKEND_SCALE, NAME_CAP = 0.25, 0.5, 0.15
DELIST_ACTIONS = {"delisted", "bankruptcyliquidation", "regulatorydelisting", "voluntarydelisting"}

RULES = ["current", "a1_least", "a2_hivol", "a3_lovol", "a4_cheap", "a5_liquid", "a6_random"]


def load_bars(lo: pd.Timestamp, hi: pd.Timestamp) -> pd.DataFrame:
    cols = ["ticker", "date", "open", "high", "low", "close", "volume", "closeunadj"]
    parts = []
    for f in (STORE / "stocks.parquet", STORE / "funds.parquet"):
        t = pd.read_parquet(f, columns=cols, filters=[("date", ">=", lo), ("date", "<=", hi)])
        if len(t):
            parts.append(t)
    b = pd.concat(parts, ignore_index=True)
    b["date"] = pd.to_datetime(b["date"])
    b["closeunadj"] = b["closeunadj"].where(np.isfinite(b["closeunadj"]), b["close"])
    return b.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def load_actions() -> tuple[dict, dict]:
    a = pd.read_parquet(STORE / "actions.parquet", columns=["date", "action", "ticker", "value"])
    a["action"] = a["action"].astype(str).str.lower()
    a["date"] = pd.to_datetime(a["date"])
    dprice, divs = {}, {}
    for tk, g in a[a["action"].isin(DELIST_ACTIONS)].groupby("ticker"):
        g = g.sort_values("date")
        v = pd.to_numeric(g["value"], errors="coerce")
        dprice[tk] = (g["date"].iloc[-1], float(v.iloc[-1]) if np.isfinite(v.iloc[-1]) and v.iloc[-1] > 0 else None)
    dv = a[a["action"] == "dividend"]
    for tk, d, v in zip(dv["ticker"], dv["date"], pd.to_numeric(dv["value"], errors="coerce")):
        if np.isfinite(v):
            divs[(tk, np.datetime64(d, "ns"))] = float(v)
    return dprice, divs


def corr_mats(R: np.ndarray):
    """Correlation matrices over the last-20 and last-19 return windows (right-aligned, NaN-left),
    mirroring the live min-length windows; plus per-row std of the full / last-19 / last-20 series."""
    def cord(X):
        m = X.shape[0]
        C = np.full((m, m), np.nan)
        sd = np.nanstd(X, axis=1)
        ok = np.isfinite(X).all(axis=1) & (sd > 0)
        if ok.sum():
            Z = (X[ok] - X[ok].mean(axis=1, keepdims=True)) / sd[ok, None]
            idx = np.flatnonzero(ok)
            C[np.ix_(idx, idx)] = Z @ Z.T / X.shape[1]
        return C, sd
    C20, sd20 = cord(R)
    C19, sd19 = cord(R[:, 1:])
    sdfull = np.nanstd(R, axis=1)
    return C20, C19, sd20, sd19, sdfull


def dedupe_fast(order: list[int], mats, L: np.ndarray) -> tuple[list[int], list[tuple[int, int]]]:
    """Replicates signals.dedupe_correlated exactly (n = min(len_i, len_k) >= 10, std(rk[-n:]) > 0,
    corr > MAX_CORR), using precomputed correlation matrices."""
    C20, C19, sd20, sd19, sdfull = mats
    kept, dropped, series = [], [], []
    for i in order:
        dup = None
        if L[i] >= 10 and sdfull[i] > 0:
            for k in series:
                n = min(L[i], L[k])
                if n >= 10:
                    sdk = sd20[k] if n == 20 else sd19[k]
                    Cm = C20 if n == 20 else C19
                    if sdk > 0 and np.isfinite(Cm[i, k]) and Cm[i, k] > MAX_CORR:
                        dup = k
                        break
        if dup is None:
            kept.append(i)
            if L[i] >= 10:
                series.append(i)
        else:
            dropped.append((i, dup))
    return kept, dropped


def order_for(rule: str, df: pd.DataFrame, rng: np.random.Generator) -> list[int]:
    """Walk order over df rows (positions 0..m-1) for each survivor rule."""
    if rule == "current":
        return list(np.argsort(df["day_ret"].to_numpy(float), kind="stable"))
    if rule == "a1_least":
        return list(np.argsort(-df["day_ret"].to_numpy(float), kind="stable"))
    if rule == "a2_hivol":
        return list(np.argsort(-df["vol20"].to_numpy(float), kind="stable"))
    if rule == "a3_lovol":
        return list(np.argsort(df["vol20"].to_numpy(float), kind="stable"))
    if rule == "a4_cheap":
        return list(np.argsort(df["price"].to_numpy(float), kind="stable"))
    if rule == "a5_liquid":
        return list(np.argsort(-df["adv"].to_numpy(float), kind="stable"))
    if rule == "a6_random":
        return list(rng.permutation(len(df)))
    raise ValueError(rule)


def process_chunk(lo, hi, which, share, master, dprice, divs):
    bars = load_bars(pd.Timestamp(lo) - pd.Timedelta(days=45), pd.Timestamp(hi) + pd.Timedelta(days=10))
    pn = nx.build_panel(bars)
    el = nx.eligible_mask(pn)
    uni = nx.universe_mask(pn, master, which)
    mt = nx.master_by_ticker(master)
    sess = pn["sessions"]
    lo_n, hi_n = np.datetime64(lo), np.datetime64(hi)
    nights = sess[(sess >= lo_n) & (sess <= hi_n)]
    dates = pn["date"]
    keep_all = el & uni

    name_rows, pair_rows, night_rows = [], [], []
    t0 = time.time()
    for dd in nights:
        idx = np.flatnonzero(keep_all & (dates == dd) & np.isfinite(pn["c_prev"]))
        if not len(idx):
            continue
        dr = pn["c"][idx] / pn["c_prev"][idx] - 1.0
        sel = idx[np.isfinite(dr) & (dr <= DAY_RET_MAX)]
        if not len(sel):
            continue
        df = pd.DataFrame({
            "price": pn["cu"][sel], "prev_close": pn["c_prev"][sel] * pn["f"][sel],
            "high": pn["h"][sel] * pn["f"][sel], "low": pn["l"][sel] * pn["f"][sel],
            "vol20": pn["vol20"][sel], "adv": pn["adv"][sel], "row": sel,
        }, index=pn["tickers"][sel])
        picks = sg.loser_picks(df, day_ret_max=DAY_RET_MAX, ibs_max=IBS_MAX,
                               price_min=PRICE_MIN, price_max=PRICE_MAX)
        if picks.empty:
            continue
        rows = picks["row"].to_numpy(int)
        lr = pn["lr"]
        Rl = [lr[max(r - 20, int(pn["start"][r]) + 1):r] for r in rows]
        L = np.array([len(x) for x in Rl])
        R = np.full((len(Rl), 20), np.nan)
        for j, x in enumerate(Rl):
            R[j, 20 - L[j]:] = x
        mats = corr_mats(R)
        si = int(np.searchsorted(sess, dd))
        nxt = pd.Timestamp(sess[si + 1]) if si + 1 < len(sess) else None
        if nxt is None:
            continue
        gs = sg.gap_scale(pd.Timestamp(dd), nxt, WEEKEND_SCALE)
        # outcomes for every pick (same scoring as nx.collect_trades)
        r_out = np.full(len(rows), np.nan)
        for k, r in enumerate(rows):
            tk = picks.index[k]
            if pn["has_next"][r]:
                v = pn["o_next"][r] / pn["c"][r] - 1.0
                dvd = divs.get((tk, np.datetime64(nxt, "ns")))
                if dvd and 0 < dvd / pn["cu"][r] < 0.25:
                    v += dvd / pn["cu"][r]
                r_out[k] = v
            else:
                lastbar = mt.at[tk, "lastpricedate"] if tk in mt.index else pd.NaT
                gone = bool(mt.at[tk, "delisted"]) if tk in mt.index else False
                if pd.isna(lastbar):
                    seg = pn["tickers"][pn["start"][r]:] == tk
                    lastbar = pd.Timestamp(pn["date"][pn["start"][r]:][seg][-1])
                ended = gone and pd.Timestamp(lastbar) <= pd.Timestamp(dd)
                px = dprice.get(tk, (None, None))[1] if ended else None
                if ended and px is not None and 0 < px / pn["cu"][r] <= 5:
                    r_out[k] = px / pn["cu"][r] - 1.0
                else:
                    r_out[k] = -1.0
        night = dict(date=pd.Timestamp(dd), n_picks=len(picks), n_nights_uni=1, gs=float(gs))
        rng = np.random.default_rng(abs(hash((lo, str(dd), which))) % (2**32))
        kept_sets = {}
        for rule in RULES:
            order = order_for(rule, picks, rng)
            kept, dropped = dedupe_fast(order, mats, L)
            kept_sets[rule] = kept
            kdf = picks.iloc[kept]
            krows = rows[kept]
            if not len(kept):
                night[f"leg_{rule}"] = 0.0
                night[f"nk_{rule}"] = 0
                continue
            n_raw = len(kept)
            vol_ok = (kdf["vol20"].to_numpy(float) >= VOL_MIN)
            if not vol_ok.any():
                night[f"leg_{rule}"] = 0.0
                night[f"nk_{rule}"] = int(vol_ok.sum())
                continue
            frac = min(1.0 / int(vol_ok.sum()), NAME_CAP) * min(1.0, CROWD_N / max(n_raw, 1))
            w = sg.night_tilt(kdf["vol20"].to_numpy(float)[vol_ok], kdf["day_ret"].to_numpy(float)[vol_ok], TILT_K)
            per = frac * gs * w
            leg = float(np.sum(per * r_out[kept][vol_ok]))
            night[f"leg_{rule}"] = leg
            night[f"nk_{rule}"] = int(vol_ok.sum())
            night[f"nf_{rule}"] = int(np.sum(kdf["vol20"].to_numpy(float) < VOL_MIN))
            for j, pos in enumerate(np.flatnonzero(vol_ok)):
                kk = int(kept[pos])
                name_rows.append(dict(date=pd.Timestamp(dd), rule=rule, ticker=picks.index[kk], r=float(r_out[kk]),
                                      per=float(per[j]), frac=float(frac), w=float(w[j]),
                                      price=float(picks["price"].iloc[kk]), vol20=float(kdf["vol20"].iloc[pos]),
                                      day_ret=float(kdf["day_ret"].iloc[pos]), adv=float(picks["adv"].iloc[pos])))
            if rule == "current":
                for d_i, k_i in dropped:
                    pair_rows.append(dict(date=pd.Timestamp(dd), dropped=picks.index[d_i], kept=picks.index[k_i],
                                          r_d=float(r_out[d_i]), r_k=float(r_out[k_i]),
                                          vol_d=float(picks["vol20"].iloc[d_i]), vol_k=float(picks["vol20"].iloc[k_i]),
                                          px_d=float(picks["price"].iloc[d_i]), px_k=float(picks["price"].iloc[k_i]),
                                          adv_d=float(picks["adv"].iloc[d_i]), adv_k=float(picks["adv"].iloc[k_i])))
        night_rows.append(night)
    el_t = time.time() - t0
    return (pd.DataFrame(night_rows), pd.DataFrame(name_rows), pd.DataFrame(pair_rows), len(nights), el_t)


def stats_block(nd: pd.DataFrame, which: str) -> list[str]:
    out = []
    nd = nd.copy()
    nd["year"] = nd["date"].dt.year
    for rule in RULES:
        d = (nd[f"leg_{rule}"] - nd["leg_current"]).to_numpy(float) * 1e4  # bp of leg per night
        n = len(d)
        t = d.mean() / (d.std(ddof=1) / np.sqrt(n)) if n > 2 and d.std(ddof=1) > 0 else float("nan")
        h1 = d[nd["year"] <= 2012]
        h2 = d[nd["year"] >= 2013]
        s = np.sort(d)
        ex5 = s[:-5].mean() if len(s) > 10 else float("nan")
        out.append(f"  {rule:10s} d_bp {d.mean():>7.2f} t {t:>6.2f} med {np.median(d):>7.2f} "
                   f"hit {(d > 0).mean():.3f} h1 {h1.mean():>7.2f} h2 {h2.mean():>7.2f} ex5 {ex5:>7.2f} n_night {n}")
    # depth-1 leg level vs current-leg level
    base = nd["leg_current"].mean() * 1e4
    out.append(f"  level current {base:>7.2f} bp/night x250 {base * 250 / 100:>6.2f} %/yr of leg budget")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--which", default="all,primary")
    args = ap.parse_args()
    chunks = QUICK_CHUNKS if args.quick else FULL_CHUNKS
    PROG.mkdir(parents=True, exist_ok=True)
    master = nx.load_master(nx.Paths())
    dprice, divs = load_actions()
    lines = [f"SEL-NIGHT {'QUICK' if args.quick else 'FULL'}: night dedupe-survivor + cash-order study",
             f"window {chunks[0][0]}..{chunks[-1][1]}, universes {args.which}", ""]
    for which in args.which.split(","):
        all_night, all_name, all_pair = [], [], []
        for lo, hi in chunks:
            nd, nm, pr, n_nights, el = process_chunk(lo, hi, which, None, master, dprice, divs)
            all_night.append(nd); all_name.append(nm); all_pair.append(pr)
            lines.append(f"[{which}] {lo}..{hi}: nights {n_nights}, activity nights {len(nd)}, {el:.0f}s")
        nd = pd.concat(all_night, ignore_index=True)
        nm = pd.concat(all_name, ignore_index=True)
        pr = pd.concat(all_pair, ignore_index=True)
        nd.to_parquet(PROG / f"sel_night_nights_{which}.parquet")
        nm.to_parquet(PROG / f"sel_night_names_{which}.parquet")
        pr.to_parquet(PROG / f"sel_night_pairs_{which}.parquet")
        lines.append("")
        lines.append(f"[{which}] SEL-NIGHT leg-level (bp/night vs current; + = rule better):")
        lines += stats_block(nd, which)
        lines.append("")
        # pair-level: current pairs, alt survivor deltas (each pair = one current dedupe event)
        if len(pr):
            rng_p = np.random.default_rng(20261018)
            rnd_flip = rng_p.random(len(pr)) < 0.5
            alt = {
                "a1_least": (pr["r_d"] - pr["r_k"]).to_numpy(float),
                "a2_hivol": np.where(pr["vol_d"].to_numpy(float) > pr["vol_k"].to_numpy(float),
                                     pr["r_d"] - pr["r_k"], 0.0),
                "a3_lovol": np.where(pr["vol_d"].to_numpy(float) < pr["vol_k"].to_numpy(float),
                                     pr["r_d"] - pr["r_k"], 0.0),
                "a4_cheap": np.where(pr["px_d"].to_numpy(float) < pr["px_k"].to_numpy(float),
                                     pr["r_d"] - pr["r_k"], 0.0),
                "a5_liquid": np.where(pr["adv_d"].to_numpy(float) > pr["adv_k"].to_numpy(float),
                                      pr["r_d"] - pr["r_k"], 0.0),
                "a6_random": np.where(rnd_flip, pr["r_d"] - pr["r_k"], 0.0),
            }
            for rule, dv in alt.items():
                d = dv * 1e4
                dd = pd.DataFrame({"date": pr["date"], "d": d})
                by = dd.groupby("date")["d"].mean()
                t = by.mean() / (by.std(ddof=1) / np.sqrt(len(by))) if len(by) > 2 else float("nan")
                s = np.sort(d)
                sw = float((dv != 0).mean())
                lines.append(f"  pairs {rule:10s} n {len(d):7d} swap% {sw:5.1%} mean {d.mean():>7.2f} "
                             f"t(day) {t:>6.2f} med {np.median(d):>7.2f} hit {(d > 0).mean():.3f} "
                             f"ex5 {s[:-5].mean():>7.2f}")
        lines.append("")
    txt = "\n".join(lines) + "\n"
    (PROG / "sel_night_out.txt").write_text(txt)
    print(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
