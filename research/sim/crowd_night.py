"""Study CROWD-NIGHT (N 1043): the crowd rule (exposure x 30/n above 30 signals) re-judged on Sharadar 1999-2026.
Run: PYTHONPATH=. .venv/bin/python research/sim/crowd_night.py"""
from __future__ import annotations
import pathlib
import numpy as np
import pandas as pd

PROG = pathlib.Path(__file__).resolve().parents[2] / "data" / "research" / "program"
CAP, CROWD = 0.15, 30
BUCKETS = [(1, 5), (6, 10), (11, 20), (21, 30), (31, 60), (61, 10**6)]


def clus_t(x):
    x = np.asarray(x, float); return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 and x.std(ddof=1) > 0 else np.nan


def maxdd(x):
    c = np.cumprod(1 + x / 1e4); return (c / np.maximum.accumulate(c) - 1).min() * 100


def main():
    x = pd.read_parquet(PROG / "night_band_rows.parquet"); x["date"] = pd.to_datetime(x.date)
    sessions = pd.DatetimeIndex(np.sort(x.date.unique()))
    pool = x[x.day_ret <= -0.08].copy()
    by = pool.groupby("date").r.agg(["mean", "median", "size"])
    pool = pool.merge(by["size"].rename("n"), left_on="date", right_index=True)
    L = [f"CROWD-NIGHT: crowd rule on the Sharadar daily proxy; pool picks {len(pool):,}, nights {len(by)}, sessions {len(sessions)}", ""]
    for era, lo, hi in [("judge 1999-2015", "1999-01-01", "2015-12-31"), ("report 2016-2026", "2016-01-01", "2026-12-31")]:
        p = pool[(pool.date >= lo) & (pool.date <= hi)]
        L.append(f"== {era}: per-name r by names-per-night bucket ==")
        for a, b in BUCKETS:
            s = p[(p.n >= a) & (p.n <= b)]
            if len(s) < 50:
                continue
            dm = s.groupby("date").r.mean()
            L.append(f"  n {a:>3}-{min(b, 999):<3}: picks {len(s):6,} nights {len(dm):4} mean {s.r.mean():+6.1f} med {s.r.median():+6.1f} "
                     f"hit {(s.r > 0).mean():.3f} t(day) {clus_t(dm.to_numpy()):5.2f}")
        L.append("")
    legs = {}
    n = by["size"].reindex(sessions).fillna(0); m = by["mean"].reindex(sessions).fillna(0)
    legs["a_live"] = np.minimum(1, CAP * n) * np.minimum(1, CROWD / n.replace(0, 1)) * m
    legs["b_nocrowd"] = np.minimum(1, CAP * n) * m
    legs["c_crowd60"] = np.minimum(1, CAP * n) * np.minimum(1, 60 / n.replace(0, 1)) * m
    for era, lo, hi in [("judge 1999-2015", "1999-01-01", "2015-12-31"), ("report 2016-2026", "2016-01-01", "2026-12-31")]:
        idx = (sessions >= lo) & (sessions <= hi)
        yr = sessions[idx].year; mid = int(np.median(yr))
        L.append(f"== {era}: leg per night (bp), crowded nights (n > 30) {int((n[idx] > 30).sum())} of {int((n[idx] > 0).sum())} active ==")
        a = legs["a_live"][idx].to_numpy()
        L.append(f"  a_live      {a.mean():+6.2f} bp/night maxDD {maxdd(a):6.1f}%")
        for k in ("b_nocrowd", "c_crowd60"):
            v = legs[k][idx].to_numpy(); d = v - a; s = np.sort(d)
            L.append(f"  {k:11s} {v.mean():+6.2f} bp/night maxDD {maxdd(v):6.1f}% | delta vs live {d.mean():+5.2f} t {clus_t(d):5.2f} "
                     f"h1 {d[yr <= mid].mean():+5.2f} h2 {d[yr > mid].mean():+5.2f} ex-top-5 {s[:-5].mean():+5.2f} med {np.median(d):+5.2f} "
                     f"= {d.mean()*250/100*0.65:+.2f}pp/yr at w .65")
        L.append("")
    txt = "\n".join(L) + "\n"; (PROG / "crowd_night_out.txt").write_text(txt); print(txt)


if __name__ == "__main__":
    main()
