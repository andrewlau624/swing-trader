"""Probe MBS-CVX: mortgage convexity hedging -> Treasury momentum when the refinance incentive is near the money.

Participant: MBS holders/servicers (GSEs, banks, REITs) who hedge duration. Constraint: MBS duration shortens as rates
fall (refi) and extends as rates rise, most sharply when the market mortgage rate is near the outstanding stock's coupon.
Flow: they buy duration into rallies and sell into sell-offs (pro-cyclical). Effect: Treasury returns autocorrelate more
in the near-the-money state. Trade: follow yesterday's (or 5-day) TLT/IEF direction only in that state.

State (lagged one week, no look-ahead): stock-coupon proxy = 5-year mean of FRED MORTGAGE30US; incentive I = proxy - rate.
NEAR = -0.25 <= I <= +0.75pp. Data: Sharadar SFP TLT/IEF/SPY 2002-26. Exploratory probe, no N.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

STORE = pathlib.Path.home() / "data" / "sharadar"
OUT = pathlib.Path(__file__).with_name("mbs_convexity_out.txt")


def main(mort_csv: str):
    m = pd.read_csv(mort_csv, parse_dates=["observation_date"]).set_index("observation_date").MORTGAGE30US
    m = m.astype(float)
    stock = m.rolling(260, min_periods=200).mean()
    inc = (stock - m).shift(1)                                  # known one week later
    f = ds.dataset(STORE / "funds.parquet").to_table(
        columns=["ticker", "date", "close"], filter=ds.field("ticker").isin(["TLT", "IEF", "SPY"])).to_pandas()
    f["date"] = pd.to_datetime(f.date)
    px = f.pivot(index="date", columns="ticker", values="close").sort_index()
    px = px[px.index >= "2002-08-01"]
    st = inc.reindex(px.index, method="ffill")
    near = st.between(-0.25, 0.75)
    lines = [f"MBS-CVX probe 2002-08..{px.index.max().date()}: NEAR share {near.mean():.2f}", ""]
    for t in ["TLT", "IEF", "SPY"]:
        r = px[t].pct_change()
        for lb, hz in [(1, 1), (5, 1), (5, 5), (20, 5)]:
            sig = np.sign(px[t] / px[t].shift(lb) - 1)
            fwd = px[t].shift(-hz) / px[t] - 1
            pnl = sig * fwd
            row = []
            for lab, mask in [("NEAR", near), ("FAR", ~near & st.notna())]:
                x = pnl[mask].dropna()
                if hz > 1:   # non-overlapping
                    x = x.iloc[::hz]
                t_ = x.mean() / x.std() * np.sqrt(len(x))
                c = np.corrcoef(r[mask].dropna().iloc[:-1], r[mask].dropna().shift(-1).dropna())[0, 1] if lb == 1 and hz == 1 else np.nan
                row.append(f"{lab} {x.mean()*1e4:+6.1f}bp t {t_:+.2f} n {len(x)}" + (f" ac1 {c:+.3f}" if lb == 1 and hz == 1 else ""))
            lines.append(f"{t} mom{lb:2d}->h{hz}: " + " | ".join(row))
        for era in [("2002", "2013"), ("2013", "2027")]:
            sig = np.sign(px[t] / px[t].shift(5) - 1); fwd = px[t].shift(-1) / px[t] - 1
            sel = (px.index >= era[0]) & (px.index < era[1])
            a = (sig * fwd)[near & sel].dropna(); b = (sig * fwd)[~near & st.notna() & sel].dropna()
            lines.append(f"   {t} mom5->h1 {era[0]}-{int(era[1])-1}: NEAR {a.mean()*1e4:+.1f} (n {len(a)}) FAR {b.mean()*1e4:+.1f} (n {len(b)})")
        lines.append("")
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1])
