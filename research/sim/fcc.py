"""Study FCC - commodity futures curve carry (frozen experiment).

    PYTHONPATH=. .venv/bin/python -m research.sim.fcc > data/research/program/fcc_out.txt

Frozen spec (user, 2026-10-05): RY=(F2/F1-1)*12/months predicts the front contract's excess
return over the next roll period for physically hedged commodities; ES/NQ are the null. Universe
CL/NG/ES/NQ, glbx_*_daily.parquet, 2011-2025; roll-date definition from fut_roll.py (unchanged:
F1/F2 = two nearest by expiration, roll boundary = the date the front symbol changes). Costs one
tick per leg per roll (CL/NG $10, ES $12.50, NQ $5). Fit 2011-2017, OOS judge 2018-2025.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

ROOT = "data/research/program"
MON = {"F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6, "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12}
TICKV = {"CL": 10.0, "NG": 10.0, "ES": 12.50, "NQ": 5.00}      # $ per tick
TICK = {"CL": 0.01, "NG": 0.001, "ES": 0.25, "NQ": 0.25}        # price per tick
FIT = ("2011-01-01", "2017-12-31")
OOS = ("2018-01-01", "2025-12-31")


def load(root):
    d = pd.read_parquet(f"{ROOT}/glbx_{root}_daily.parquet")
    d["date"] = pd.to_datetime(d["ts_event"], utc=True).dt.tz_convert("America/New_York").dt.normalize().dt.tz_localize(None)
    pat = re.compile(rf"^{root}([FGHJKMNQUVXZ])(\d)$")
    d["code"] = d["symbol"].astype(str).str.extract(pat)[0]
    d = d[d["code"].notna()].copy()
    d = d.sort_values(["symbol", "date"])
    # Databento uses single-digit years -> a symbol string repeats every decade (CLN5 = Jul-2015 AND
    # Jul-2025). Split each symbol into contract instances at >400-day gaps, one per actual contract.
    seg = d.groupby("symbol")["date"].diff().dt.days.fillna(0).gt(400).groupby(d["symbol"]).cumsum()
    d["cid"] = d["symbol"] + "#" + seg.astype(int).astype(str)
    exp = d.groupby("cid")["date"].max().rename("exp")     # expiry proxy = last trade date
    d = d.merge(exp, left_on="cid", right_index=True)
    return d[["date", "cid", "close", "volume", "exp"]]


def build(root):
    d = load(root)
    wide_c = d.pivot_table(index="date", columns="cid", values="close")
    rows = []
    for date, g in d.groupby("date"):
        g = g[(g.close > 0) & (g["exp"] >= date)].copy()      # still trading
        g = g.sort_values("exp")
        if len(g) < 2:
            continue
        f1, f2 = g.iloc[0], g.iloc[1]
        rows.append(dict(date=date, f1=f1.cid, f2=f2.cid, f1c=f1.close, f2c=f2.close,
                         f1v=f1.volume, f2v=f2.volume, e1=f1["exp"], e2=f2["exp"]))
    R = pd.DataFrame(rows).set_index("date").sort_index()
    # roll boundaries = dates the front symbol changes
    b = R.index[(R["f1"] != R["f1"].shift(1)).values]
    b = b[1:] if len(b) else b
    periods = []
    for k in range(len(b) - 1):
        t0, t1 = b[k], b[k + 1]
        held = R.at[t0, "f1"]
        p0 = R.at[t0, "f1c"]
        s = wide_c[held].loc[t0:t1].dropna()
        p1 = s.iloc[-1] if len(s) else np.nan
        months = max(1, int(round((R.at[t0, "e2"] - R.at[t0, "e1"]).days / 30.44)))
        ry = (R.at[t0, "f2c"] / R.at[t0, "f1c"] - 1) * 12 / months
        periods.append(dict(t0=t0, t1=t1, root=root, ry=ry, ret=p1 / p0 - 1,
                            cost_frac=2 * TICK[root] / p0, f1v=R.at[t0, "f1v"], f2v=R.at[t0, "f2v"]))
    return pd.DataFrame(periods)


def ppv(root):
    # $ per price point per contract (to convert tick $ into price fraction is not needed; we use cost_frac in price)
    return 1.0


def stats(x, ann):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) == 0:
        return "n 0"
    eq = np.cumprod(1 + x); dd = (eq / np.maximum.accumulate(eq) - 1).min()
    sh = x.mean() / x.std() * np.sqrt(ann) if x.std() > 0 else np.nan
    se = x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else np.nan
    return (f"n {len(x):3d} mean {x.mean()*1e4:+6.1f}bp med {np.median(x)*1e4:+6.1f}bp hit {(x>0).mean()*100:3.0f}% "
            f"sd {x.std()*1e4:5.0f} ann {x.mean()*ann*100:+6.2f}% Sharpe {sh:+.2f} t {x.mean()/se:+.2f} "
            f"cum {(eq[-1]-1)*100:+7.1f}% maxDD {dd*100:6.1f}%")


def main():
    frames = {r: build(r) for r in ("CL", "NG", "ES", "NQ")}
    for x in frames.values():
        x["net_ls"] = np.sign(x["ry"]) * x["ret"] - x["cost_frac"]
        x["net_lo"] = np.where(x["ry"] > 0, x["ret"] - x["cost_frac"], 0.0)
        x["excess"] = x["ret"] - x["cost_frac"]
    A = pd.concat(frames.values(), ignore_index=True)
    ppy = {"CL": 12, "NG": 12, "ES": 4, "NQ": 4}

    print("STUDY FCC - commodity futures curve carry (frozen; research only)")
    print(f"periods per root: " + ", ".join(f"{r} {len(frames[r])}" for r in frames))
    print(f"median F1 volume at roll: " + ", ".join(f"{r} {frames[r]['f1v'].median():.0f}" for r in frames))

    for win, lab in [(FIT, "FIT 2011-2017"), (OOS, "OOS 2018-2025")]:
        print(f"\n== {lab} ==")
        for r in ("CL", "NG", "ES", "NQ"):
            x = frames[r]; x = x[(x.t0 >= win[0]) & (x.t0 <= win[1])]
            print(f"  {r}: RY->ret corr {_corr(x.ry, x.ret):+.2f}")
            print(f"     L/S net  {stats(x.net_ls, ppy[r])}")
            print(f"     L-only   {stats(x.net_lo, ppy[r])}")
        phys = A[(A.root.isin(["CL", "NG"])) & (A.t0 >= win[0]) & (A.t0 <= win[1])]
        fin = A[(A.root.isin(["ES", "NQ"])) & (A.t0 >= win[0]) & (A.t0 <= win[1])]
        print(f"  POOLED physical CL/NG: corr {_corr(phys.ry, phys.ret):+.2f}")
        print(f"     L/S net  {stats(phys.net_ls, 12)}")
        print(f"  POOLED financial ES/NQ: corr {_corr(fin.ry, fin.ret):+.2f}")
        print(f"     L/S net  {stats(fin.net_ls, 4)}")

    print("\n== RY quintile monotonicity (subsequent excess return, per-period bp) ==")
    for lab, sub in [("CL", frames["CL"]), ("NG", frames["NG"]), ("ES", frames["ES"]), ("NQ", frames["NQ"]),
                     ("CL+NG", A[A.root.isin(["CL", "NG"])]), ("ES+NQ", A[A.root.isin(["ES", "NQ"])])]:
        x = sub.copy()
        if len(x) < 25:
            print(f"  {lab:6s} n {len(x)} too few"); continue
        x["q"] = pd.qcut(x["ry"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
        m = x.groupby("q")["excess"].mean() * 1e4
        print(f"  {lab:6s} " + " ".join(f"Q{int(q)} {v:+6.1f}" for q, v in m.items()) +
              f"   (spearman {x['ry'].corr(x['excess'], method='spearman'):+.2f})")

    print("\n== MECHANISM: physical vs financial (OOS excess, per period) ==")
    o = A[(A.t0 >= OOS[0]) & (A.t0 <= OOS[1])]
    for lab, sub in [("CL", o[o.root == "CL"]), ("ES", o[o.root == "ES"]), ("NG", o[o.root == "NG"]),
                     ("NQ", o[o.root == "NQ"])]:
        print(f"  {lab}: n {len(sub)} excess mean {sub.excess.mean()*1e4:+.1f}bp  corr(RY,excess) {_corr(sub.ry, sub.excess):+.2f}")

    # ---- verdict
    print("\n== KILL CRITERIA (OOS) ==")
    op = o[o.root.isin(["CL", "NG"])]; of = o[o.root.isin(["ES", "NQ"])]
    c1 = op.net_ls.mean() <= 0
    per = {r: o[o.root == r].net_ls.mean() for r in ("CL", "NG")}
    c2 = not (per["CL"] > 0 and per["NG"] > 0)
    sp = op["ry"].corr(op["excess"], method="spearman")
    c3 = not (sp > 0)
    c4 = abs(of.net_ls.mean()) >= abs(op.net_ls.mean())
    c5 = op.net_ls.mean() <= 0
    print(f"  1 OOS pooled physical net L/S <= 0 : {'FIRES' if c1 else 'no'} ({op.net_ls.mean()*1e4:+.1f}bp)")
    print(f"  2 sign carried by one commodity    : {'FIRES' if c2 else 'no'} (CL {per['CL']*1e4:+.1f}bp, NG {per['NG']*1e4:+.1f}bp)")
    print(f"  3 no RY-quintile monotonicity      : {'FIRES' if c3 else 'no'} (spearman {sp:+.2f})")
    print(f"  4 ES/NQ magnitude >= CL/NG         : {'FIRES' if c4 else 'no'} (fin {of.net_ls.mean()*1e4:+.1f}bp vs phys {op.net_ls.mean()*1e4:+.1f}bp)")
    fired = c1 or c2 or c3 or c4
    print(f"  -> {'REJECTED' if fired else 'survives frozen gates'}")


def _corr(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    m = np.isfinite(a) & np.isfinite(b)
    return np.corrcoef(a[m], b[m])[0, 1] if m.sum() > 3 else np.nan


if __name__ == "__main__":
    main()
