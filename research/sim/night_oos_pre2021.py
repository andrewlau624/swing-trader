"""PHASE 1a: night-leg OOS on pre-2021 stock data (2016-2020).

The night leg was selected on 2021-2026. Alpaca serves pre-2021 stock bars, so the
leg can finally be judged on a regime it never saw. This reconstructs the live rule
from daily bars (the live version uses the 15:40 price/H/L; the daily-bar version uses
the close, the standard approximation):
  day_ret = close/prev_close - 1 <= -8%,  IBS = (close-low)/(high-low) < 0.10,
  close in [$5, $2000], 20d vol >= 60%, 20d ADV >= $10M,
  outcome = next_open/close - 1   (buy the close auction, sell the open auction).

Universe = the 2021+ swing cache symbols (data/cache/bars/*.parquet). This is
SURVIVORSHIP-LIMITED (only names still tracked by Alpaca today), which FLATTERS a
loser-bounce leg (dead losers are missing). So: a negative result is decisive; a
positive result still needs a truly delisted-inclusive universe.

Run: PYTHONPATH=. .venv/bin/python research/sim/night_oos_pre2021.py [N_SYMBOLS]
Appends picks to data/research/program/night_pre2021_picks.parquet
"""
from __future__ import annotations

import glob
import os
import pathlib
import sys

import numpy as np
import pandas as pd

from swingtrader.data import fetch_bars

ROOT = pathlib.Path(__file__).resolve().parents[2]
PICKS = ROOT / "data/research/program/night_pre2021_picks.parquet"
START, END, B = "2016-01-01", "2020-12-31", 200

# IMPORTANT: fetch into a SEPARATE cache. The default cache holds 2021-2026 bars
# (req 2021-01-01..2026-09-22, feed=iex); writing 2016-2020 there would evict them.
import swingtrader.data as _sd  # noqa: E402
_sd.CACHE = ROOT / "data" / "cache" / "bars_pre2021"
_sd.CACHE.mkdir(parents=True, exist_ok=True)


def build(limit: int | None = None) -> pd.DataFrame:
    syms = sorted(os.path.basename(f)[:-8] for f in glob.glob(str(ROOT / "data/cache/bars/*.parquet")))
    if limit:
        syms = syms[:limit]
    rows = []
    for i in range(0, len(syms), B):
        chunk = syms[i:i + B]
        try:
            out = fetch_bars(chunk, START, END, feed="sip", verbose=False)
        except Exception as exc:  # noqa: BLE001
            print(f"  chunk {i} err {type(exc).__name__}: {str(exc)[:80]}", flush=True)
            continue
        for s, df in out.items():
            if df is None or len(df) < 80:
                continue
            c, o, h, l, v = (df[k].astype("float64") for k in ("close", "open", "high", "low", "volume"))
            ret = c / c.shift(1) - 1
            ibs = ((c - l) / (h - l)).where(h > l)
            adv = (c * v).rolling(20).mean().shift(1)
            vol = (ret.rolling(20).std().shift(1) * np.sqrt(252))
            nxt = o.shift(-1)
            m = ((ret <= -0.08) & (ibs < 0.10) & (c >= 5) & (c <= 2000)
                 & (vol >= 0.60) & (adv >= 1e7) & nxt.notna() & np.isfinite(ret - ibs))
            if m.any():
                rows.append(pd.DataFrame({"sym": s, "date": df.index[m], "day_ret": ret[m],
                                          "ibs": ibs[m], "close": c[m], "adv": adv[m],
                                          "ret": (nxt[m] / c[m] - 1.0)}))
        if i % 2000 == 0:
            print(f"  {i}/{len(syms)}", flush=True)
    return pd.concat(rows) if rows else pd.DataFrame()


def report(r: pd.DataFrame) -> str:
    r = r[r["ret"].abs() < 0.6].sort_values("date")
    b = 1e4
    lines = ["Night-leg OOS on 2016-2020 stock data (daily-bar reconstruction;",
             "universe = 2021+ swing cache -> SURVIVORSHIP-LIMITED, flatters the bounce)", ""]
    for lab, lo, hi in [("2016-20 OOS", "2016", "2020"), ("2021-26 live", "2021", "2026")]:
        x = r.loc[lo:hi, "ret"]
        if len(x) < 20:
            lines.append(f"{lab}: n/a"); continue
        t = x.mean() / x.std() * np.sqrt(len(x))
        ex5 = x.sort_values().iloc[:-5].mean()
        lines.append(f"{lab}: n={len(x):5d} mean={x.mean()*b:6.1f}bp median={x.median()*b:6.1f} "
                     f"t={t:5.2f} hit={(x>0).mean()*100:3.0f}% ex5={ex5*b:6.1f}")
    lines += ["", "by year: n mean_bp median_bp hit%"]
    for y, g in r.groupby(r["date"].dt.year):
        if len(g) >= 20:
            lines.append(f"  {y}: n={len(g):5d} mean={g['ret'].mean()*b:6.1f} "
                         f"med={g['ret'].median()*b:6.1f} hit={(g['ret']>0).mean()*100:3.0f}%")
    return "\n".join(lines)


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    df = build(limit)
    if PICKS.exists():
        old = pd.read_parquet(PICKS)
        df = pd.concat([old, df]).drop_duplicates(["sym", "date"])
    if len(df):
        PICKS.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(PICKS)
        print(report(df))
        print(f"\nwrote {len(df)} events to {PICKS}")
