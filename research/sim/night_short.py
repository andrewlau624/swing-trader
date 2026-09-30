"""Study S: short the shipped night picks after the open, cover later the same session.

    PYTHONPATH=. .venv/bin/python -m research.sim.night_short

Pre-registration: research/drafts/round1_prose.md, "Round 5" (commit 2b935b3, stamped
before any Study S return was computed). Taxable brokerage only.

Short return r = 1 - P_cover / P_entry. Entry A = the daily-panel open of d+1 (auction),
entry B = the close of the 09:30 minute bar. Cover = the close of the last minute bar before
09:45 / 10:00 / 10:30, or the d+1 daily close. Costs per side: the night tier (raw price,
ADV) for auction prints; + 5bp (tier) / + 15bp (tier_hi) for continuous-session prints.
SSR (Rule 201): day-d low <= -10% vs close d-1 -> untradable, scores 0 in the book.
"""
from __future__ import annotations

import glob
import os
import pathlib
import pickle
import time

import numpy as np
import pandas as pd

from . import book as B

ROOT = pathlib.Path(__file__).resolve().parents[2]
AM1 = ROOT / "data/research/night/am1"
OUT = ROOT / "data/research/program/night_short_out.txt"

COVERS = {"09:45": 945, "10:00": 1000, "10:30": 1030, "close": None}
VARIANTS = {f"S{i + 1} {e} cover {c}": (e, c)
            for i, (e, c) in enumerate([(e, c) for e in ("A auc", "B 09:31") for c in COVERS])}
EXTRA = {"tier": 5.0, "tier_hi": 15.0}              # continuous-session spread add-on, per side
PER = (("2021-23", "2021-01-01", "2023-12-31"), ("2024-26", "2024-01-01", "2026-12-31"))
FULL = ("2021-01-01", "2026-12-31")
LOCATE = (1.0, 0.6, 0.3)
N_PLACEBO = 200


def nw_t(x, lags: int = 5) -> float:
    v = np.asarray(x, float)
    v = v[np.isfinite(v)]
    n = len(v)
    if n < 30:
        return float("nan")
    e = v - v.mean()
    var = (e * e).sum() / n
    for k in range(1, lags + 1):
        var += 2 * (1 - k / (lags + 1)) * (e[k:] * e[:-k]).sum() / n
    return v.mean() / np.sqrt(max(var, 1e-18) / n)


def load_minutes():
    """next session -> DataFrame (hm index, symbol columns) of minute closes."""
    out = {}
    for f in sorted(glob.glob(str(AM1 / "*.parquet"))):
        df = pd.read_parquet(f)
        t = df.timestamp.dt.tz_convert("America/New_York")
        df["hm"] = t.dt.hour * 100 + t.dt.minute
        c = df.pivot_table(index="hm", columns="symbol", values="close", aggfunc="last")
        o = df[df.hm == 930].set_index("symbol")["open"]
        out[pd.Timestamp(os.path.basename(f)[:10])] = (c.sort_index(), o[~o.index.duplicated()])
    return out


def prices(C0, O0, sym, O1, C1):
    """(entry A, entry B, cover dict) for one name, or None on missing data / basis fail."""
    if sym not in C0.columns or sym not in O0.index:
        return None
    m_open = float(O0[sym])
    if not (np.isfinite(m_open) and np.isfinite(O1) and O1 > 0
            and abs(m_open / O1 - 1) <= 0.005):
        return None
    col = C0[sym]
    if 930 not in col.index or not np.isfinite(col.at[930]):
        return None
    cov = {}
    for k, hm in COVERS.items():
        if hm is None:
            cov[k] = C1
        else:
            pre = col[col.index < hm].dropna()
            cov[k] = float(pre.iloc[-1]) if len(pre) else np.nan
    return O1, float(col.at[930]), cov


def main():
    t0 = time.time()
    fs = open(OUT, "w")

    def log(*a):
        s_ = " ".join(str(x) for x in a)
        print(s_, flush=True)
        fs.write(s_ + "\n")
        fs.flush()

    log("== Study S: short the night picks after the open, started", pd.Timestamp.now(), "\n")
    N = B.night_days(raw_price=True, max_corr=0.7)
    P = pickle.load(open(ROOT / "data/research/night/panel.pkl", "rb"))
    O, H, L, C, V = P["open"], P["high"], P["low"], P["close"], P["volume"]
    vol20 = C.pct_change(fill_method=None).rolling(20).std()
    adv20 = (C * V).rolling(20).mean()
    idx = C.index
    nxt_of = {d: idx[i + 1] for i, d in enumerate(idx[:-1])}
    prv_of = {d: idx[i - 1] for i, d in enumerate(idx) if i > 0}
    mins = load_minutes()
    log(f"loaded in {time.time() - t0:4.1f} s: {len(N)} pick days, {len(mins)} minute sessions")

    def ssr(d, sym):
        pd_ = prv_of.get(d)
        if pd_ is None:
            return True
        lo, pc = L.at[d, sym], C.at[pd_, sym]
        return not (np.isfinite(lo) and np.isfinite(pc) and pc > 0) or lo / pc - 1 <= -0.10

    # ---- picks
    rows, n_picks, n_ssr, n_nodata = [], 0, 0, 0
    for d, nd in N.items():
        nx = nxt_of.get(d)
        for j, sym in enumerate(nd.syms):
            n_picks += 1
            base = dict(d=d, nxt=nx, sym=sym, w=min(nd.frac, 0.10), price=nd.price[j],
                        adv=nd.adv[j], scored=False, ssr=False)
            if nx is None or nx not in mins or sym not in C.columns:
                n_nodata += 1; rows.append(base); continue
            if ssr(d, sym):
                n_ssr += 1; base["ssr"] = True; rows.append(base); continue
            C0, O0 = mins[nx]
            got = prices(C0, O0, sym, float(O.at[nx, sym]), float(C.at[nx, sym]))
            if got is None:
                n_nodata += 1; rows.append(base); continue
            a, b, cov = got
            base.update(scored=True, eA=a, eB=b, vdec=float(vol20.at[d, sym]),
                        **{f"c{k}": v for k, v in cov.items()})
            rows.append(base)
    T = pd.DataFrame(rows)
    sc = T[T.scored]
    log(f"picks {n_picks}: scored {len(sc)} ({len(sc) / n_picks:.0%}), SSR {n_ssr} "
        f"({n_ssr / n_picks:.0%}), no minute data / basis fail {n_nodata}")
    log(f"scored by half: " + ", ".join(
        f"{lab} {len(sc[(sc.nxt >= a) & (sc.nxt <= b)])}" for lab, a, b in PER) + "\n")

    # ---- placebo pool: non-pick names in the same am1 files, same filters
    pick_keys = set(zip(T.nxt, T.sym))
    prow = []
    for nx, (C0, O0) in mins.items():
        d = prv_of.get(nx)
        if d is None or nx not in O.index:
            continue
        for sym in C0.columns:
            if (nx, sym) in pick_keys or sym not in C.columns or ssr(d, sym):
                continue
            got = prices(C0, O0, sym, float(O.at[nx, sym]), float(C.at[nx, sym]))
            if got is None:
                continue
            a, b, cov = got
            prow.append(dict(nxt=nx, sym=sym, price=float(C.at[d, sym]),
                             adv=float(adv20.at[d, sym]), eA=a, eB=b,
                             vdec=float(vol20.at[d, sym]), **{f"c{k}": v for k, v in cov.items()}))
    PL = pd.DataFrame(prow)
    PL = PL[np.isfinite(PL.vdec)]
    edges = np.nanquantile(pd.concat([sc.vdec, PL.vdec]), np.linspace(0, 1, 11))
    dec = lambda v: np.clip(np.searchsorted(edges, v, side="right") - 1, 0, 9)
    PL["dec"] = dec(PL.vdec.values)
    sc = sc.assign(dec=dec(sc.vdec.values))
    PL = PL.reset_index(drop=True)
    pools = {k: g.index.values for k, g in PL.groupby(["nxt", "dec"])}
    log(f"placebo pool: {len(PL)} non-pick (session, name) rows\n")

    def net(df, entry, cover, cost):
        tc = B.cost_bps(cost, df.price.values, df.adv.values)
        e = df.eA.values if entry.startswith("A") else df.eB.values
        x = df[f"c{cover}"].values
        r = 1 - x / e
        c_in = tc + (0 if entry.startswith("A") else EXTRA[cost])
        c_out = tc + (0 if cover == "close" else EXTRA[cost])
        return np.clip(r, -1, 1) - (c_in + c_out) / 1e4

    days = C.index[(C.index >= FULL[0]) & (C.index <= FULL[1])]
    rng = np.random.default_rng(11)
    verdict = {}
    for cost in ("tier", "tier_hi"):
        log(f"## cost {cost}  (per-trade bp = mean net, winsorised +-10%; book pp/yr = "
            f"sum of the daily increment / years)")
        log(f"{'variant':22s} {'2021-23 bp (n)':>18s} {'2024-26 bp (n)':>18s} "
            f"{'plc pct':>10s} {'book pp/yr 21-23/24-26':>24s} {'NW t':>6s} "
            f"{'@60% / @30% locate pp/yr':>28s}")
        for lab, (entry, cover) in VARIANTS.items():
            s = sc.copy()
            s["net"] = net(s, entry, cover, cost)
            s = s[np.isfinite(s.net)]
            half_bp, plc, ok = [], [], True
            for _, a, b in PER:
                h = s[(s.nxt >= a) & (s.nxt <= b)]
                m = h.net.clip(-.1, .1).mean()
                half_bp.append((m * 1e4, len(h)))
                # placebo: per pick, a random same-session same-decile non-pick
                pl_net = np.clip(net(PL, entry, cover, cost), -.1, .1)
                pos = [pools.get((r.nxt, r.dec)) for r in h.itertuples()]
                pos = [g for g in pos if g is not None and len(g)]
                pick = np.stack([g[rng.integers(len(g), size=N_PLACEBO)] for g in pos])
                draws = np.nanmean(pl_net[pick], axis=0)
                plc.append((np.array(draws) < m).mean() * 100)
            # book increment, per locate rate
            incs = {}
            for loc in LOCATE:
                keep = rng.random(len(s)) < loc
                inc = (0.5 * s.w * s.net * keep).groupby(s.nxt).sum().reindex(days).fillna(0)
                incs[loc] = inc
            inc = incs[1.0]
            yr = lambda x, a, b: x[a:b].sum() / (len(x[a:b]) / 252) * 100
            bk = [yr(inc, a, b) for _, a, b in PER]
            t = nw_t(inc.values)
            lo = [[yr(incs[l], a, b) for _, a, b in PER] for l in (0.6, 0.3)]
            passed = (all(b_ > 0 for b_, _ in half_bp) and all(p >= 95 for p in plc)
                      and all(x > 0 for x in bk) and t >= 2.0 and all(x > 0 for x in lo[1]))
            verdict.setdefault(lab, []).append(passed)
            log(f"{lab:22s} {half_bp[0][0]:+8.1f} ({half_bp[0][1]:5d}) {half_bp[1][0]:+8.1f} "
                f"({half_bp[1][1]:5d}) {plc[0]:4.0f}/{plc[1]:<4.0f} "
                f"{bk[0]:+10.2f} / {bk[1]:+7.2f}   {t:+5.2f}   "
                f"{lo[0][0]:+.2f}/{lo[0][1]:+.2f}  {lo[1][0]:+.2f}/{lo[1][1]:+.2f}"
                f"  {'PASS' if passed else ''}")
        # gross drift (no cost), for the reading
        log("\n  gross short return, no costs (bp, both halves pooled):")
        for lab, (entry, cover) in VARIANTS.items():
            e = sc.eA if entry.startswith("A") else sc.eB
            g = (1 - sc[f"c{cover}"] / e).clip(-.1, .1)
            log(f"    {lab:22s} {g.mean() * 1e4:+7.1f}  win {(g > 0).mean():.0%}")
        log("")

    log("## verdict per variant (pass at tier AND tier_hi)")
    for lab, v in verdict.items():
        log(f"  {lab:22s} {'PASS' if all(v) else 'fail'}")
    log(f"\ndone in {time.time() - t0:4.0f} s")


if __name__ == "__main__":
    main()
