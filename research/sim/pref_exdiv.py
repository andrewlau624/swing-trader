"""Probe PREF-EX: ex-dividend under-adjustment in retail-dominated preferred stocks (Roth-friendly: dividends untaxed).

Participant: retail/income holders of exchange-listed preferreds ($25 par). Constraint: taxable holders value the
dividend below cash (and some funds avoid ex-date churn); thin dealer inventory. Flow: price drops by less than the
dividend on the ex-date. Trade: buy the T-1 close, sell the ex-date open or close, collect the dividend.

Data: Sharadar SEP preferreds (category 'Domestic Preferred Stock') + ACTIONS dividends (date = ex-date), 2005-2026.
P&L in raw prices (closeunadj; preferreds rarely split). Placebo: same names' non-ex-date close->close / close->open.
Exploratory probe, no N.
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

S = pathlib.Path.home() / "data" / "sharadar"
OUT = pathlib.Path(__file__).with_name("pref_exdiv_out.txt")


def main():
    t = ds.dataset(S / "tickers.parquet").to_table(columns=["table", "ticker", "category"]).to_pandas()
    pref = set(t.loc[(t.table == "SEP") & (t.category == "Domestic Preferred Stock"), "ticker"])
    b = ds.dataset(S / "stocks.parquet").to_table(
        columns=["ticker", "date", "open", "high", "low", "close", "volume", "closeunadj"],
        filter=ds.field("ticker").isin(list(pref))).to_pandas()
    b["date"] = pd.to_datetime(b.date)
    b = b.sort_values(["ticker", "date"]).reset_index(drop=True)
    f = b.closeunadj / b.close                                   # raw/adj factor for O/H/L
    for c in ["open", "high", "low"]:
        b[c] = b[c] * f
    g = b.groupby("ticker", sort=False)
    b["pc"] = g.closeunadj.shift(1)
    b["dv"] = (b.closeunadj * b.volume).groupby(b.ticker).transform(lambda s: s.shift(1).rolling(20, min_periods=10).median())
    b["hl"] = ((b.high - b.low) / b.closeunadj).groupby(b.ticker).transform(lambda s: s.shift(1).rolling(20, min_periods=10).median())
    a = ds.dataset(S / "actions.parquet").to_table(columns=["date", "action", "ticker", "value"]).to_pandas()
    a = a[(a.action == "dividend") & a.ticker.isin(pref)].copy()
    a["date"] = pd.to_datetime(a.date)
    a = a.groupby(["ticker", "date"], as_index=False).value.sum().rename(columns={"value": "div"})
    m = b.merge(a, on=["ticker", "date"], how="left")
    m["ex"] = m["div"].notna()
    m["div"] = m["div"].fillna(0)
    m = m[(m.pc >= 10) & (m.pc <= 60) & (m.date >= "2005-01-01")].dropna(subset=["pc", "dv"])
    m["yld"] = m["div"] / m.pc
    m = m[(~m.ex) | m.yld.between(0.002, 0.04)]                  # drop special/suspended oddities
    m["cc"] = (m.closeunadj + m["div"]) / m.pc - 1               # buy T-1 close, sell T close (+div on ex-days)
    m["co"] = (m.open + m["div"]) / m.pc - 1                     # sell at T open
    m["drop_ratio"] = (m.pc - m.closeunadj) / m["div"].where(m.ex)
    lines = [f"PREF-EX probe: {m.ex.sum()} ex-dates, {m[m.ex].ticker.nunique()} preferreds, 2005-{m.date.max().year}", ""]
    for lab, x in [("all", m), ("dv>=$200k", m[m.dv >= 2e5]), ("dv>=$1M", m[m.dv >= 1e6])]:
        e, n = x[x.ex], x[~x.ex]
        for c in ["cc", "co"]:
            day = e.groupby("date")[c].mean()
            tt = day.mean() / day.std() * np.sqrt(len(day))
            yrs = e.groupby(e.date.dt.year)[c].mean() * 1e4
            lines.append(f"{lab:10s} {c}: ex n {len(e):6d} mean {e[c].mean()*1e4:+6.1f}bp med {e[c].median()*1e4:+6.1f} "
                         f"t(day) {tt:+5.2f} | non-ex mean {n[c].mean()*1e4:+5.1f} med {n[c].median()*1e4:+5.1f} | "
                         f"drop/div med {e.drop_ratio.median():.2f} | hl20 med {e.hl.median()*1e4:.0f}bp | yrs>0 {(yrs > 0).sum()}/{len(yrs)}")
        lines.append("")
    yr = m[m.ex & (m.dv >= 2e5)].groupby(m.date.dt.year).agg(n=("cc", "size"), cc=("cc", "mean"), co=("co", "mean"))
    lines.append("by year (dv>=$200k): " + " ".join(f"{y}:{r.cc*1e4:+.0f}/{r.co*1e4:+.0f}(n{r.n})" for y, r in yr.iterrows()))
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
