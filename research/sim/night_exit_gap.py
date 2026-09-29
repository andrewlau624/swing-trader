"""Study A: gap-conditioned night exit — hold past the opening auction on extreme gaps.

    PYTHONPATH=. .venv/bin/python -m research.sim.night_exit_gap

Pre-registration: research/drafts/round1_prose.md (stamped before any variant number).

Accounting (the same convention for base and alternative):
  r0  = the shipped auction return of a night pick, close d -> open d+1 (the pool's own
        nd.ret; for the placebo's hypothetical trade the same formula on the daily panels)
  P_M = the CLOSE of minute M of the next session's minute file on the daily-panel basis;
        basis check: the minute-0 open must match the daily open within 0.5%, else the name
        keeps the shipped exit and is not scored (counted as a skip)
  r_eff = P_M / C_d - 1 where C_d is the close-auction price the book paid (nd.close)
  r_mix = split_at_auction * r0 + (1 - split_at_auction) * r_eff
  diff(bp) = (r_mix - r0) * 1e4 per dollar of notional. The round-trip cost is the same in
        base and alternative under the shipped convention (2 * cost_bps at the decision-price
        tier), so it cancels in the diff; tier / tier_hi enter only the book replay.

Placebo: 200 draws; per qualifying trade a random OTHER name of the SAME next session with
gap <= thr, same vol20-decile bucket (estimator and deciles identical for picks and pool).

Pass bars: (1) mean diff > 0 in BOTH halves; (2) placebo >= 95th pct both halves;
(3) V7 (raw, corr .7) book increment positive in both halves, NW t >= 2.0 over 2021-26;
(4) edge-halves and 5y MC not worse. Adopt needs all four at tier_hi AND tier.
"""
from __future__ import annotations

import glob
import os
import pickle
import pathlib
import time

import numpy as np
import pandas as pd
from scipy import stats as SS

from . import book as B
from .growth import V7, cfg
from .validate import load_sim

ROOT = pathlib.Path(__file__).resolve().parents[2]
GM1 = ROOT / "data/research/night/gm1"
OUT = ROOT / "data/research/program/night_exit_gap_out.txt"

VARIANTS = {
    "E1 g-5 m5":  (-0.05, 5, 0.0),
    "E2 g-5 m15": (-0.05, 15, 0.0),
    "E3 g-5 m30": (-0.05, 30, 0.0),
    "E4 g-8 m30": (-0.08, 30, 0.0),
    "E5 g-5 m30 half-auc": (-0.05, 30, 0.5),
}
PER = (("2021-23", "2021-01-01", "2023-12-31"), ("2024-26", "2024-01-01", "2026-12-31"))
COSTS = ("tier", "tier_hi")


def minute_closes():
    out = {}
    for f in sorted(glob.glob(str(GM1 / "*.parquet"))):
        d = pd.Timestamp(os.path.basename(f)[:10])
        df = pd.read_parquet(f)
        t = df.timestamp.dt.tz_convert("America/New_York")
        df["m"] = t.dt.hour * 60 + t.dt.minute - 570
        df = df[(df.m >= 0) & (df.m <= 390)]
        c = df.pivot_table(index="m", columns="symbol", values="close", aggfunc="last")
        c = c[~c.index.duplicated(keep="last")].ffill()
        out[d] = (c, c.iloc[0])
    return out


def nw_t(x, lags: int = 5) -> float:
    v = x.dropna().values
    n = len(v)
    if n < 30:
        return float("nan")
    e = v - v.mean()
    var = (e * e).sum() / n
    for k in range(1, lags + 1):
        var += 2 * (1 - k / (lags + 1)) * (e[k:] * e[:-k]).sum() / n
    return v.mean() / np.sqrt(max(var, 1e-18) / n)


def half_str(x):
    parts = []
    for _, a, b in PER:
        c, sh, dd = B.stats(x[a:b])
        parts.append(f"{c*100:+6.2f}/{sh:4.2f}")
    c, sh, dd = B.stats(x)
    return "  ".join(parts) + f"  full {c*100:+6.2f}/{sh:4.2f}/{dd*100:4.0f}"


def main():
    t0 = time.time()
    fs = open(OUT, "w")

    def log(*a):
        s_ = " ".join(str(x) for x in a)
        print(s_, flush=True)
        fs.write(s_ + "\n")
        fs.flush()

    log("== Study A: gap-conditioned night exit, started", pd.Timestamp.now(), "\n")
    s = load_sim(raw_price=True)
    s.N = B.night_days(raw_price=True, max_corr=0.7)
    N0 = s.N
    mins = minute_closes()
    log(f"loaded sim + minutes in {time.time()-t0:4.1f} s: {len(N0)} pick days, "
        f"{len(mins)} minute sessions")

    base = {}
    for cost in COSTS:
        kw = {**V7, **cfg(1.0, 0.5, 2), "night_cost": cost}
        base[cost] = s.replay(B.Params(**kw))
        log(f"base V7 raw {cost:7s}: {B.summary(base[cost])}")

    P = pickle.load(open(ROOT / "data/research/night/panel.pkl", "rb"))
    O, C = P["open"], P["close"]                    # the adjusted daily panel (all names)
    Cs = C.pct_change(fill_method=None).rolling(20).std()
    s_night_idx = s.night_idx                       # close d -> open d+1 (the etf panel's basis
    # is the same universe; the pick's own shipped return comes from nd.ret, not from here)

    # 1) minute-session table: rows (nxt, sym, d, close_d, r0, gap, vol20) for every
    #    (next session, name) pair with valid data. r0/gap on the daily panels.
    # 2) for every day's picks, patch auc_ret / i / is_pick.
    rows = []
    for nxt, (C0, O0) in mins.items():
        prev = C.index[C.index < nxt]
        if not len(prev):
            continue
        d = prev[-1]
        if d not in O.index:
            continue
        try:
            d_op = O.loc[nxt]
        except KeyError:
            continue
        for sy in C0.columns:
            if sy not in O0.index or sy not in d_op.index or sy not in C.columns:
                continue
            m_open = float(O0[sy])
            d_open = float(d_op[sy])
            dc = float(C.at[d, sy])
            if not (np.isfinite(m_open) and np.isfinite(d_open) and np.isfinite(dc)
                    and dc > 0 and d_open > 0):
                continue
            if abs(m_open / d_open - 1) > 0.005:
                continue
            vol = float(Cs.at[d, sy]) if (sy in Cs.columns and d in Cs.index) else np.nan
            rows.append(dict(nxt=nxt, sym=sy, d=d, close_d=dc, r0=d_open / dc - 1,
                             gap=m_open / dc - 1, vol20=vol))
    log(f"\nunified table: {len(rows)} (next-session, name) rows")

    n_picks = sum(len(nd.syms) for nd in N0.values())
    n_flagged = 0
    for d, nd in N0.items():
        for j, sy in enumerate(nd.syms):
            hit = [r for r in rows if r["d"] == d and r["sym"] == sy]
            if hit:
                hit[0]["is_pick"] = True
                hit[0]["i"] = j
                hit[0]["auc_ret"] = float(nd.ret[j])
                n_flagged += 1
    tab = pd.DataFrame(rows)
    if "is_pick" not in tab.columns:
        tab["is_pick"] = False
    tab["is_pick"] = tab["is_pick"].fillna(False).astype(bool)
    log(f"night picks flagged in the table: {n_flagged} of {n_picks} pool picks "
        f"(the rest keep the shipped auction exit)\n")

    po_ext = tab[(tab["gap"] <= -0.03) & np.isfinite(tab["vol20"])].copy()
    po_ext["dec"] = pd.qcut(po_ext["vol20"], 10, labels=False, duplicates="drop").astype(float)
    pools = {nxt: g.reset_index(drop=True) for nxt, g in po_ext.groupby("nxt")}
    # the placebo pool: the same rows, minus every pick name of that next session
    po_np = po_ext[po_ext["is_pick"] != True].copy()

    def rmin(nxt, sym, minute):
        C0 = mins[nxt][0]
        if minute not in C0.index:
            return float("nan")
        p = C0.at[minute, sym]
        if isinstance(p, (pd.Series, np.ndarray)):
            p = p[-1]
        return float(p)

    rng = np.random.default_rng(7)
    for cost in COSTS:
        log(f"## cost {cost}")
        kw = {**V7, **cfg(1.0, 0.5, 2), "night_cost": cost}
        for lab, (thr, minute, split) in VARIANTS.items():
            q = tab[(tab["is_pick"]) & (tab["gap"] <= thr) & np.isfinite(tab["auc_ret"])]
            qrows = []
            for r in q.itertuples():
                pm = rmin(r.nxt, r.sym, minute)
                if not np.isfinite(pm):
                    continue
                r_eff = pm / r.close_d - 1
                r_mix = split * r.auc_ret + (1 - split) * r_eff
                pk = pools.get(r.nxt)
                dec = 5
                if pk is not None:
                    hh = pk[pk["sym"] == r.sym]
                    if len(hh):
                        dec = int(hh["dec"].iloc[0])
                qrows.append((r.d, r.nxt, r.sym, (r_mix - r.auc_ret) * 1e4, dec))
            qq = pd.DataFrame(qrows, columns=["d", "nxt", "sym", "diff", "dec"])
            if not len(qq):
                log(f"{lab:22s} no priced qualifying picks\n")
                continue
            m = qq["diff"].mean()
            tf = SS.ttest_1samp(qq["diff"], 0.0)
            log(f"{lab:22s} n {len(qq):5d} ({qq['nxt'].nunique()} sessions) mean {m:+7.2f}bp "
                f"med {qq['diff'].median():+7.2f} t {tf.statistic:+5.2f} "
                f"win {(qq['diff'] > 0).mean():.0%}")
            for _, a, b2 in PER:
                sel = qq[(qq["nxt"] >= a) & (qq["nxt"] <= b2)]
                if len(sel) >= 10:
                    t = SS.ttest_1samp(sel["diff"], 0.0).statistic
                    log(f"{'':22s}  {a}: n {len(sel):4d} mean {sel['diff'].mean():+7.2f}bp "
                        f"med {sel['diff'].median():+7.2f} t {t:+5.2f} "
                        f"win {(sel['diff'] > 0).mean():.0%}")
                else:
                    log(f"{'':22s}  {a}: n {len(sel)} (too few)")

            # placebo: 200 draws, decile-matched other names of the same session
            pool_all = po_np[po_np["gap"] <= thr]
            pr = []
            for _ in range(200):
                all_ = []
                for r in qq.itertuples():
                    po = pool_all[pool_all["nxt"] == r.nxt]
                    if not len(po):
                        continue
                    same = po[(po["dec"] == r.dec) & (po["sym"] != r.sym)]
                    if not len(same):
                        same = po[po["sym"] != r.sym]
                    if not len(same):
                        continue
                    pick = same.iloc[rng.integers(len(same))]
                    pm2 = rmin(r.nxt, pick.sym, minute)
                    if not np.isfinite(pm2):
                        continue
                    r_eff2 = pm2 / pick.close_d - 1
                    r_mix2 = split * pick.r0 + (1 - split) * r_eff2
                    all_.append((r_mix2 - pick.r0) * 1e4)
                if all_:
                    pr.append(float(np.mean(all_)))
            if pr:
                pr = np.array(pr)
                pct = 100 * (pr < m).mean()
                log(f"{'':22s} placebo: mean {pr.mean():+7.2f}bp p95 {np.percentile(pr, 95):+7.2f}bp "
                    f"| actual {m:+7.2f} -> pct {pct:.0f}")
            else:
                log(f"{'':22s} placebo: no draws")

            # book replay
            by_day = {}
            for r in qq.itertuples():
                by_day.setdefault(r.d, {})[r.sym] = r.diff / 1e4
            adj = dict(N0)
            nch = 0
            for d, dd in by_day.items():
                nd1 = adj.get(d)
                if nd1 is None:
                    continue
                ret = np.array(nd1.ret, float).copy()
                ix = {sy_: i for i, sy_ in enumerate(nd1.syms)}
                for sy_, diff_ in dd.items():
                    i = ix.get(sy_)
                    if i is not None and np.isfinite(ret[i]):
                        ret[i] += diff_
                        nch += 1
                adj[d] = B.NightDay(nd1.syms, nd1.price, nd1.close, ret, nd1.adv, nd1.vol20,
                                    nd1.ret20, nd1.day_ret, nd1.frac, nd1.n_raw)
            s.N = adj
            ralt = s.replay(B.Params(**kw))
            rbt = ralt["r"] - base[cost]["r"].reindex(ralt.index).fillna(0)
            log(f"{'':22s}  alt book ({nch} picks patched): {B.summary(ralt)}")
            log(f"{'':22s}  book increments: {half_str(rbt)}   NW t {nw_t(rbt):+5.2f}\n")
        log("---")
    fs.close()


if __name__ == "__main__":
    main()
