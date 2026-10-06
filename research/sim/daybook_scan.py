"""Broad discovery scan on a CONSISTENT full-SIP daily panel (bars_pre2021 + sipd).

Features are all known at 09:30 (pre-open). Targets are intraday (open->close) and
overnight (close->next open). Cross-sectional dollar-neutral rank portfolios.
Discovery 2016-2020; validation 2021-2023 and 2024-2026.

Run: PYTHONPATH=. .venv/bin/python -m research.sim.daybook_scan
"""
from __future__ import annotations

import glob
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PRE = ROOT / "data" / "cache" / "bars_pre2021"
SIPD = ROOT / "data" / "research" / "night" / "sipd"
CACHE = ROOT / "data" / "research" / "program" / "daybook_panel.pkl"
FIELDS = ["open", "high", "low", "close", "volume"]


def build_panel():
    if CACHE.exists():
        return pickle.load(open(CACHE, "rb"))
    # pre-2021 (SIP full) from bars_pre2021
    frames = {f: {} for f in FIELDS}
    for p in sorted(glob.glob(str(PRE / "*.parquet"))):
        s = Path(p).stem
        df = pd.read_parquet(p)
        for f in FIELDS:
            frames[f][s] = df[f].astype("float32")
    P1 = {f: pd.DataFrame(frames[f]) for f in FIELDS}
    # sipd (SIP full) long -> pivot
    parts = []
    for p in sorted(glob.glob(str(SIPD / "*.parquet"))):
        parts.append(pd.read_parquet(p, columns=["symbol", "timestamp"] + FIELDS))
    df = pd.concat(parts, ignore_index=True)
    df["date"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None).dt.normalize()
    P2 = {}
    for f in FIELDS:
        P2[f] = df.pivot_table(index="date", columns="symbol", values=f, aggfunc="last").astype("float32")
    # combine: pre-2021 then sipd (sipd 2020-10+; drop overlap <2020-10 from P1 kept)
    out = {}
    for f in FIELDS:
        a = P1[f]; b = P2[f]
        a = a[a.index < b.index.min()]
        out[f] = pd.concat([a, b]).sort_index()
    pickle.dump(out, open(CACHE, "wb"), protocol=4)
    return out


def rankw(sig, valid):
    r = sig.where(valid).rank(axis=1, pct=True) - 0.5
    r = r.where(valid)
    return r.div(r.abs().sum(axis=1), axis=0)


def report(name, daily, cost_bps=3.0):
    out = []
    for lo, hi, lbl in [("2016", "2020", "16-20"), ("2021", "2023", "21-23"), ("2024", "2026", "24-26")]:
        m = (daily.index >= f"{lo}-01-01") & (daily.index <= f"{hi}-12-31")
        x = daily[m].dropna()
        if len(x) < 50:
            out.append(f"{lbl}:n/a"); continue
        t = x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))
        cagr = x.mean() * 252
        sh = x.mean() / x.std() * np.sqrt(252)
        eq = (1 + x).cumprod(); dd = (eq / eq.cummax() - 1).min()
        out.append(f"{lbl}: mean{x.mean()*1e4:+6.1f} t{t:+5.2f} Sh{sh:+4.2f} DD{dd*100:4.0f} n3{(x.mean()-cost_bps*1e-4)*1e4:+5.1f}")
    print(f"{name:40s} " + " | ".join(out))


def main():
    P = build_panel()
    O, H, L, C, V = (P[f] for f in FIELDS)
    adv = (C * V).rolling(20).mean().shift(1)
    valid = (C >= 5) & (adv >= 1e7) & O.notna() & C.shift(1).notna()
    intr = (C / O - 1.0).where(valid)                 # open -> close
    on = (O.shift(-1) / C - 1.0).where(valid)         # close -> next open
    print("panel", O.shape, O.index.min().date(), O.index.max().date())
    print("valid/day", valid.sum(axis=1).mean().round(0), " by yr:",
          valid.sum(axis=1).groupby(valid.index.year).mean().round(0).to_dict())

    feats = {
        "gap=O/pc-1": O / C.shift(1) - 1.0,
        "r1=pc/pc1-1": C.shift(1) / C.shift(2) - 1.0,
        "r5": C.shift(1) / C.shift(6) - 1.0,
        "r20": C.shift(1) / C.shift(21) - 1.0,
        "ibs_prev": (C.shift(1) - L.shift(1)) / (H.shift(1) - L.shift(1) + 1e-9),
        "relvol_prev": V.shift(1) / V.rolling(20).mean().shift(2),
        "range_prev": (H.shift(1) - L.shift(1)) / C.shift(2),
    }
    for nm, feat in feats.items():
        for tgt, tl in [(intr, "OC"), (on, "CO")]:
            for sgn, sl in [(-1.0, "REV"), (1.0, "MOM")]:
                w = rankw(sgn * feat, valid)
                daily = (w * tgt).sum(axis=1)
                report(f"{nm} -> {tl} {sl}", daily)


if __name__ == "__main__":
    main()
