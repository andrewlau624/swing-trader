"""Discovery: cross-sectional intraday (open->close) reversal on the broad US panel.

Signal formed at the open (known at 09:30, executable via MOO), exit at the close
auction (MOC) -> round-trip spread cost is the auction slippage only, not the quoted spread.

Exploratory. Judge 2016-2020 vs 2021-2023 vs 2024-2026. No adoption.

Run: PYTHONPATH=. .venv/bin/python -m research.sim.xsec_intraday
"""
from __future__ import annotations

import glob
import os
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BARS = ROOT / "data" / "cache" / "bars"
PRE = ROOT / "data" / "cache" / "bars_pre2021"
CACHE = ROOT / "data" / "research" / "program" / "xsec_intraday_panel.pkl"

FIELDS = ["open", "high", "low", "close", "volume"]


def build_panel():
    if CACHE.exists():
        return pickle.load(open(CACHE, "rb"))
    syms = [os.path.basename(p)[:-8] for p in sorted(glob.glob(str(BARS / "*.parquet")))]
    data = {f: {} for f in FIELDS}
    n = 0
    for s in syms:
        frames = []
        for d in (PRE, BARS):
            p = d / f"{s}.parquet"
            if p.exists():
                frames.append(pd.read_parquet(p))
        if not frames:
            continue
        df = pd.concat(frames)
        df = df[~df.index.duplicated(keep="last")]
        for f in FIELDS:
            data[f][s] = df[f].astype("float32")
        n += 1
        if n % 1000 == 0:
            print("loaded", n, flush=True)
    P = {f: pd.DataFrame(data[f]) for f in FIELDS}
    out = {f: P[f] for f in FIELDS}
    pickle.dump(out, open(CACHE, "wb"), protocol=4)
    return out


def zs_rank(df):
    # cross-sectional rank -> [-0.5,0.5], then demean by construction
    r = df.rank(axis=1, pct=True)
    return r - 0.5


def evaluate(gap, intraday, valid, label, cost_bps=(1.0, 2.0, 3.0)):
    print(f"\n=== {label} ===")
    # reversal: short high gap, long low gap
    for sgn, nm in [(-1.0, "REV(-gap)"), (1.0, "MOM(+gap)")]:
        sig = sgn * zs_rank(gap.where(valid))
        # dollar-neutral weights: normalize abs to 1 -> gross 1x
        w = sig.div(sig.abs().sum(axis=1), axis=0)
        gross = (w * intraday.where(valid)).sum(axis=1)
        for lo, hi, per in [("2016", "2020", "16-20"), ("2021", "2023", "21-23"), ("2024", "2026", "24-26")]:
            m = (gross.index >= f"{lo}-01-01") & (gross.index <= f"{hi}-12-31")
            x = gross[m].dropna()
            if len(x) < 50:
                continue
            t = x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))
            sh = x.mean() / x.std() * np.sqrt(252)
            line = f"  {nm} {per}: n{len(x):4d} gross {x.mean()*1e4:+6.2f}bp t{t:+5.2f} Sh{sh:+5.2f}"
            for c in cost_bps:
                line += f" | net{c:.0f}bp {(x.mean()-c*1e-4)*1e4:+6.2f}"
            print(line)


def main():
    P = build_panel()
    O, C, V = P["open"], P["close"], P["volume"]
    dv = (C * V).rolling(20).mean().shift(1)
    valid = (C >= 5) & (dv >= 1e7) & O.notna() & C.shift(1).notna()
    gap = O / C.shift(1) - 1.0
    intraday = C / O - 1.0
    print("panel", O.shape, "days", O.index.min().date(), "..", O.index.max().date())
    print("avg names/day", valid.sum(axis=1).mean().round(0))

    evaluate(gap, intraday, valid, "ALL: cross-sectional gap -> open->close")

    # conditioned on large gaps (|gap| in top decile), full cross-section weights
    big = gap.abs() >= gap.abs().where(valid).quantile(0.9, axis=1).values[:, None]
    evaluate(gap, intraday, valid & big, "BIG-GAP decile: gap -> open->close")

    # signal = prior-day return instead
    pr = C.shift(1) / C.shift(2) - 1.0
    evaluate(pr, intraday, valid, "PRIOR-DAY return -> open->close")


if __name__ == "__main__":
    main()
