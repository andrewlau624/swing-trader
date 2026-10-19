"""Study BREADTH-GATE (N 1041): market breadth (share of stocks above 200d/50d SMA) as a leg-level gate on the night leg.
Run: PYTHONPATH=. .venv/bin/python research/sim/breadth_gate.py"""
from __future__ import annotations
import pathlib
import numpy as np
import pandas as pd

PROG = pathlib.Path(__file__).resolve().parents[2] / "data" / "research" / "program"
W, CAP = 0.65, 0.15


def clus_t(x):
    x = np.asarray(x, float); return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 and x.std(ddof=1) > 0 else np.nan


def maxdd(x):
    c = np.cumprod(1 + x / 1e4); return (c / np.maximum.accumulate(c) - 1).min() * 100


def main():
    x = pd.read_parquet(PROG / "night_band_rows.parquet"); x["date"] = pd.to_datetime(x.date)
    sessions = pd.DatetimeIndex(np.sort(x.date.unique()))
    pool = x[x.day_ret <= -0.08].groupby("date").r.agg(["mean", "size"])
    leg = pd.Series(0.0, index=sessions); leg.loc[pool.index] = np.minimum(1, CAP * pool["size"]) * pool["mean"]
    m = pd.read_parquet(PROG / "seq_market.parquet"); m["date"] = pd.to_datetime(m.date); m = m.set_index("date").sort_index()
    st = m[["breadth200", "breadth50", "spy_c_s200"]].shift(1).reindex(sessions)     # prior session's state
    d = pd.DataFrame({"leg": leg}).join(st).dropna()
    fit, jud = d[d.index <= "2015-12-31"], d[d.index >= "2016-01-01"]
    L = [f"BREADTH-GATE: night-leg proxy (daily, bp/night) vs prior-day market breadth; fit quintiles 1999-2015 (n {len(fit)}), judge 2016-26 (n {len(jud)})", ""]
    for col in ["breadth200", "breadth50"]:
        q = fit[col].quantile([.2, .4, .6, .8]).to_numpy()
        jq = np.searchsorted(q, jud[col].to_numpy())
        L.append(f"== {col}: breakpoints {np.round(q, 3).tolist()} ==")
        L.append("  judge 2016-26 leg by quintile: " + " ".join(f"Q{k+1} {jud.leg[jq == k].mean():+.1f} (n {int((jq == k).sum())})" for k in range(5)))
        fq = np.searchsorted(q, fit[col].to_numpy())
        L.append("  fit 1999-2015 leg by quintile:  " + " ".join(f"Q{k+1} {fit.leg[fq == k].mean():+.1f} (n {int((fq == k).sum())})" for k in range(5)))
        off = jq == 0
        on_leg = np.where(off, 0.0, jud.leg.to_numpy())
        diff = on_leg - jud.leg.to_numpy()
        yr = jud.index.year
        h1, h2 = diff[yr <= 2020], diff[yr >= 2021]
        s = np.sort(diff)
        L.append(f"  gate OFF in Q1 ({off.mean():.0%} of sessions): OFF-session leg {jud.leg[off].mean():+.1f} bp/night (t {clus_t(jud.leg[off]):.2f}); "
                 f"ON-only minus always-on {diff.mean():+.2f} bp/night t {clus_t(diff):.2f} h1 {h1.mean():+.2f} h2 {h2.mean():+.2f} ex-top-5 {s[:-5].mean():+.2f} "
                 f"= {diff.mean()*250/100*W:+.2f}pp/yr at w .65 | maxDD always-on {maxdd(jud.leg.to_numpy()):.1f}% vs ON-only {maxdd(on_leg):.1f}%")
        L.append("")
    neg = jud.spy_c_s200 < 0
    diff = np.where(neg, 0.0, jud.leg.to_numpy()) - jud.leg.to_numpy()
    L.append(f"== comparator SPY < 200d SMA (dead class): OFF {neg.mean():.0%} of sessions, OFF-session leg {jud.leg[neg].mean():+.1f} bp/night; "
             f"ON-only minus always-on {diff.mean():+.2f} bp/night t {clus_t(diff):.2f} | corr(breadth200, spy_c_s200) {jud.breadth200.corr(jud.spy_c_s200):.2f} ==")
    txt = "\n".join(L) + "\n"; (PROG / "breadth_gate_out.txt").write_text(txt); print(txt)


if __name__ == "__main__":
    main()
