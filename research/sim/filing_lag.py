"""FN-1 (observation stage, no judged arm; N unchanged): filing-lag map from SF1.

Lag = filingdate - calendardate per (ticker-quarter); a firm's own 8-quarter median lag as anchor.
Publishes the D+1..D+5 and D+1..D+63 abnormal (vs SPY, measured from the filing date's close) by
filing-delay quintile, and a late (>= +15d vs own median) vs on-time split. No trade rule. The 10-Q
filing date usually coincides with the earnings release: the map contains the earnings reaction and
is labelled as such; dm (days vs own cadence) is the clean state.

    PYTHONPATH=. .venv/bin/python -m research.sim.filing_lag
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from .lh_panel import Panel

OUT = pathlib.Path(__file__).resolve().parent / "filing_lag_out.txt"
lines: list[str] = []


def log(s: str) -> None:
    lines.append(s)
    print(s)


def reaction(P: Panel, spy: pd.Series, ticker: str, fdate: pd.Timestamp, k: int) -> float:
    i0 = P.row_at(ticker, fdate)
    if i0 < 0:
        return np.nan
    rows = P.rows(ticker)
    i5 = min(i0 + k, rows.stop - 1)
    if P.di[i5] == P.di[i0]:
        return np.nan
    raw = P.tr[i5] / P.tr[i0] - 1
    sp = spy.reindex([pd.Timestamp(P.dates[P.di[i0]]), pd.Timestamp(P.dates[P.di[i5]])])
    if not sp.notna().all():
        return np.nan
    return raw - float(sp.iloc[1] / sp.iloc[0] - 1)


def main() -> None:
    P = Panel.load()
    spy = P.series("SPY").set_index("date")["tr"]
    f = pd.read_parquet("/Users/andrewlau/data/sharadar/fundamentals.parquet",
                        columns=["ticker", "dimension", "calendardate", "date"])
    f = f[f.dimension.isin(["ART", "ARQ"])].dropna(subset=["date"])
    f["calendardate"] = pd.to_datetime(f["calendardate"])
    f["filingdate"] = pd.to_datetime(f["date"])  # publish date ~ filing date (SF1 proxy)
    f["dd"] = pd.to_datetime(f["date"])   # restatement rows carry a later publish date: keep the FIRST
    f = f.sort_values(["ticker", "calendardate", "dd"], kind="mergesort").drop_duplicates(["ticker", "calendardate"], keep="first")
    f = f.sort_values(["ticker", "calendardate"])
    f["lag"] = (f.filingdate - f.calendardate).dt.days
    f["lag0"] = f.groupby("ticker")["lag"].transform(lambda s: s.rolling(8, min_periods=4).median().shift(1))
    f["dm"] = f.lag - f.lag0
    f = f[f.lag0.notna() & (f.calendardate >= "1998-01-01")]
    log(f"rows {len(f)}, firms {f.ticker.nunique()}, {f.calendardate.min().date()}-{f.calendardate.max().date()}; "
        f"lag median {f.lag.median():.0f}d p75 {f.lag.quantile(.75):.0f} p95 {f.lag.quantile(.95):.0f}")
    f["r5"] = [reaction(P, spy, str(t), d, 5) for t, d in zip(f.ticker, f.filingdate)]
    f["r63"] = [reaction(P, spy, str(t), d, 63) for t, d in zip(f.ticker, f.filingdate)]
    f["b"] = pd.qcut(f.dm.rank(pct=True), q=5, labels=[1, 2, 3, 4, 5])
    tab = f.pivot_table(index="b", values=["r5", "r63"], aggfunc=["mean", "median", "count"]).round(4)
    log("reaction (D+1 close -> +k) by filing-delay quintile (1 = much EARLIER than own cadence):")
    log(tab.to_string())
    f["late"] = f.dm >= 15
    tab2 = f.pivot_table(index="late", values=["r5", "r63"], aggfunc=["mean", "median", "count"]).round(4)
    log("\nlate (>= +15d vs own cadence) vs on-time:")
    log(tab2.to_string())
    # era split for the late bucket (lit-timing: is there anything in 2016-26?)
    f["yr"] = f.calendardate.dt.year
    late = f[f.late]
    for lo, hi in ((1998, 2016), (2016, 2027)):
        s = late[(late.yr >= lo) & (late.yr < hi)]
        if len(s):
            log(f"  late {lo}-{hi}: r5 {s.r5.mean()*100:+.2f}% (n {len(s)}), r63 {s.r63.mean()*100:+.2f}%")
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
