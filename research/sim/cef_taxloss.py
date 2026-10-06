"""Study CEF-TL - closed-end fund year-end tax-loss forced selling -> January reversion.

    PYTHONPATH=. .venv/bin/python -m research.sim.cef_taxloss > data/research/program/cef_taxloss_out.txt

Pre-registered: research/drafts/study_cef_taxloss.md (N 823 -> 824). One look; research only.
Distribution-adjusted CEF total returns (ib/cef/all); ranks by YTD through Nov; Dec and Jan legs.
"""
from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd

ALL = "data/research/program/ib/cef/all"
COST = 0.0030            # 30bp round trip (stress); base 15bp = 0.0015
YEARS = list(range(2016, 2026))


def panel():
    frames = {}
    for f in sorted(glob.glob(f"{ALL}/*.parquet")):
        s = os.path.basename(f)[:-8]
        d = pd.read_parquet(f)
        if "close" in d.columns:
            frames[s] = d["close"]
    P = pd.DataFrame(frames).sort_index()
    return P


def last_on(idx, ts):
    j = idx[idx <= pd.Timestamp(ts)]
    return j[-1] if len(j) else None


def main():
    P = panel()
    idx = P.index
    print("STUDY CEF-TL (year-end tax-loss forced selling -> January reversion; research only)")
    print(f"CEFs {P.shape[1]}  {idx.min().date()}..{idx.max().date()}  cost {COST*1e4:.0f}bp round trip")
    spy = pd.read_parquet("data/research/night/etf_daily.parquet", columns=["symbol", "timestamp", "close"])
    spy = spy[spy.symbol == "SPY"].copy()
    spy["date"] = pd.to_datetime(spy["timestamp"]).dt.normalize()
    spy = spy.set_index("date")["close"].sort_index()

    per_year = []
    for Y in YEARS:
        nv, dp, de, je = (last_on(idx, f"{Y}-11-30"), last_on(idx, f"{Y-1}-12-31"),
                          last_on(idx, f"{Y}-12-31"), last_on(idx, f"{Y+1}-01-31"))
        if any(x is None for x in (nv, dp, de, je)):
            continue
        a = P.loc[[nv, dp, de, je]].T
        a.columns = ["nv", "dp", "de", "je"]
        a = a.dropna()
        if len(a) < 40:
            continue
        a["ytd"] = a["nv"] / a["dp"] - 1
        a["dec"] = a["de"] / a["nv"] - 1
        a["jan"] = a["je"] / a["de"] - 1
        a["q"] = pd.qcut(a["ytd"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
        row = {"Y": Y}
        for q in range(1, 6):
            g = a[a.q == q]
            row[f"dec_q{q}"] = g["dec"].mean(); row[f"jan_q{q}"] = g["jan"].mean(); row[f"n{q}"] = len(g)
        row["uni_dec"] = a["dec"].mean(); row["uni_jan"] = a["jan"].mean()
        row["spy_dec"] = spy.get(de, np.nan) / spy.get(nv, np.nan) - 1 if nv in spy and de in spy else np.nan
        row["spy_jan"] = spy.get(je, np.nan) / spy.get(de, np.nan) - 1 if de in spy and je in spy else np.nan
        row["n"] = len(a)
        per_year.append(row)
        # collect Q1 fund-years for ex-best-5
        row["_q1jan"] = list(a[a.q == 1]["jan"].values)
    R = pd.DataFrame(per_year).set_index("Y")
    if R.empty:
        print("no years"); return

    print("\n-- per year: universe, Dec/Jan by quintile (Q1 = worst YTD = tax-loss candidates) --")
    print(f"  {'Y':>4} {'n':>4} {'uniDec':>7} {'uniJan':>7} {'Q1dec':>7} {'Q1jan':>7} {'Q5jan':>7} "
          f"{'SPYjan':>7}")
    for Y, r in R.iterrows():
        print(f"  {Y:>4} {int(r['n']):>4} {r['uni_dec']*100:6.1f}% {r['uni_jan']*100:6.1f}% "
              f"{r['dec_q1']*100:6.1f}% {r['jan_q1']*100:6.1f}% {r['jan_q5']*100:6.1f}% "
              f"{r['spy_jan']*100:6.1f}%")

    def tstat(x):
        x = np.asarray(x, float); x = x[np.isfinite(x)]
        return x.mean(), x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 1 else (x.mean() if len(x) else np.nan, np.nan)

    print("\n-- aggregates (each year = one observation; 10 December events) --")
    for lab, col in [("Dec: Q1 - universe (forced selling)", "dec_q1"), ("Jan: Q1 - universe (reversion)", "jan_q1"),
                     ("Jan: Q1 - Q5 (loser-winner)", "jan_q1"), ("Dec: Q1 - Q5", "dec_q1")]:
        if "universe" in lab:
            x = R[col] - R["uni_" + ("dec" if col.startswith("dec") else "jan")]
        else:
            x = R[col] - R["jan_q5" if col.startswith("jan") else "dec_q5"]
        m, t = tstat(x)
        print(f"  {lab:<38} mean {m*100:+6.2f}%  t {t:+.2f}  years>0 {int((x>0).sum())}/{len(x)}")
    # net tradable: long Q1 Dec_end->Jan_end vs universe, after 30bp
    net = R["jan_q1"] - COST
    mnet, tnet = tstat(net)
    print(f"  {'Jan Q1 long-only net of 30bp':<38} mean {mnet*100:+6.2f}%  t {tnet:+.2f}")
    print(f"  {'Jan Q1 - universe net of 30bp':<38} mean {(R['jan_q1']-R['uni_jan']).mean()*100-0.30:+.2f}%  "
          f"t {tstat(R['jan_q1']-R['uni_jan'])[1]:+.2f}")
    # halves
    h1, h2 = R.loc[2016:2020], R.loc[2021:2025]
    print(f"  halves: Q1-universe Jan 2016-20 {(h1['jan_q1']-h1['uni_jan']).mean()*100:+.2f}%  "
          f"2021-25 {(h2['jan_q1']-h2['uni_jan']).mean()*100:+.2f}%")
    # ex-best-5 fund-years
    q1 = np.concatenate([np.asarray(v) for v in R["_q1jan"]]); q1 = q1[np.isfinite(q1)]
    q1s = np.sort(q1)[:-5]
    print(f"  Q1 Jan ex-best-5 fund-years: mean {q1s.mean()*100:+.2f}% (all {q1.mean()*100:+.2f}%, n {len(q1)})")
    # monotonicity
    print("  quintile Jan means (D1..D5): " + " ".join(f"{(R[f'jan_q{q}']-R['uni_jan']).mean()*100:+.2f}%" for q in range(1, 6)))
    print("  quintile Dec means (D1..D5): " + " ".join(f"{(R[f'dec_q{q}']-R['uni_dec']).mean()*100:+.2f}%" for q in range(1, 6)))

    # verdict
    prim = (R["jan_q1"] - R["uni_jan"]).mean() - COST
    both = (h1["jan_q1"] - h1["uni_jan"]).mean() > 0 and (h2["jan_q1"] - h2["uni_jan"]).mean() > 0
    decsign = (R["dec_q1"] - R["uni_dec"]).mean() < 0
    ex5 = q1s.mean() > 0
    print("\nGATES:")
    for k, v in [("Jan Q1-u >= +1.0% net", prim >= 0.01), ("positive both halves", both),
                 ("ex-best-5 > 0", ex5), ("Dec forced sign (Q1<uni)", decsign)]:
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    print(f"  VERDICT: {'PASS' if all([prim>=0.01,both,ex5,decsign]) else ('PROMISING' if prim>0 and both else 'REJECTED')}")

    print("\n-- per-$1,000 economics (if traded once/yr, after 30bp) --")
    print(f"  Jan Q1 long-only net expected ${mnet*1000:.0f}/yr on a 100%-deployed sleeve; "
          f"only ~1 month deployed -> ${mnet*1000:.0f} per $1k of the sleeve, ~{mnet*1000/12:.0f}/yr blended.")


if __name__ == "__main__":
    main()
