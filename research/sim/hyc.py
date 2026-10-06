"""Study HYC: high-yield non-qualified common dividends (REIT 6798 / BDC proxy 6799) ex-night (pre-reg round1_prose.md,
N 871). Sharadar SEP daily (vendor opens). Excess = minus the name's own mean non-ex CO/CC over the prior 60 sessions.
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

S = pathlib.Path.home() / "data" / "sharadar"
OUT = pathlib.Path(__file__).resolve().parents[2] / "data" / "research" / "program" / "hyc_out.txt"


def load() -> pd.DataFrame:
    t = ds.dataset(S / "tickers.parquet").to_table(columns=["table", "ticker", "category", "siccode"]).to_pandas()
    t = t[(t.table == "SEP") & t.category.str.contains("Common Stock", na=False) & t.siccode.isin([6798, 6799])]
    t = t.drop_duplicates("ticker")
    cls = dict(zip(t.ticker, t.siccode.map({6798: "REIT", 6799: "BDC~6799"})))
    b = ds.dataset(S / "stocks.parquet").to_table(
        columns=["ticker", "date", "open", "close", "volume", "closeadj", "closeunadj"],
        filter=ds.field("ticker").isin(list(cls))).to_pandas()
    b["date"] = pd.to_datetime(b.date)
    b = b.sort_values(["ticker", "date"]).reset_index(drop=True)
    b["open"] = b.open * b.closeunadj / b.close
    g = b.groupby("ticker", sort=False)
    b["pc"] = g.closeunadj.shift(1)
    b["y_adj"] = 1 - (b.close / g.close.shift(1)) / (b.closeadj / g.closeadj.shift(1))
    b["dv"] = (b.closeunadj * b.volume).groupby(b.ticker).transform(lambda s: s.shift(1).rolling(20, min_periods=10).median())
    a = ds.dataset(S / "actions.parquet").to_table(columns=["date", "action", "ticker", "value"]).to_pandas()
    a = a[(a.action == "dividend") & a.ticker.isin(cls)].copy()
    a["date"] = pd.to_datetime(a.date)
    a = a.groupby(["ticker", "date"], as_index=False).value.sum().rename(columns={"value": "div"})
    m = b.merge(a, on=["ticker", "date"], how="left")
    m["ex"] = m["div"].notna()
    m["div"] = m["div"].fillna(0.0)
    m["co"] = (m.open + m["div"]) / m.pc - 1
    m["cc"] = (m.closeunadj + m["div"]) / m.pc - 1
    for c in ["co", "cc"]:
        r = m[c].where(~m.ex)
        m["x" + c] = m[c] - r.groupby(m.ticker).transform(lambda s: s.shift(1).rolling(60, min_periods=30).mean())
    m["y"] = m["div"] / m.pc
    m["drop"] = (m.pc - m.closeunadj) / m["div"].where(m.ex)
    m["cls"] = m.ticker.map(cls)
    ok = (m.ex & (m.pc >= 5) & (m.dv >= 1e6) & m.y.between(0.01, 0.06) & ((m.y / m.y_adj - 1).abs() < 0.10)
          & m.open.gt(0) & m.xco.notna() & (m.date >= "1998"))
    return m[ok].copy()


def stat(x: pd.DataFrame, c: str) -> str:
    if len(x) < 20:
        return f"n {len(x)}"
    day = x.groupby("date")[c].mean()
    t = day.mean() / day.std() * np.sqrt(len(day))
    yrs = x.groupby(x.date.dt.year)[c].mean()
    return (f"n {len(x):5d} mean {x[c].mean()*1e4:+6.1f} med {x[c].median()*1e4:+6.1f} t {t:+5.2f} ex-top5 "
            f"{np.sort(x[c].values)[:-5].mean()*1e4:+6.1f} hit {(x[c] > 0).mean():.2f} yrs>0 {(yrs > 0).sum()}/{len(yrs)} "
            f"2021-26 {x.loc[x.date >= '2021', c].mean()*1e4:+6.1f} drop/div {x['drop'].median():.2f}")


def main():
    e = load()
    L = [f"HYC: {len(e)} ex-events, {e.ticker.nunique()} names, {e.date.min().date()}..{e.date.max().date()}", ""]
    for k, x in e.groupby("cls"):
        L.append(f"== {k} ==")
        for c in ["xco", "xcc", "co", "cc"]:
            L.append(f"  {c:4s} {stat(x, c)}")
        for lab, q in [("y 1-2%", x.y < 0.02), ("y 2-4%", x.y.between(0.02, 0.04)), ("y 4-6%", x.y > 0.04),
                       ("dv $1-10M", x.dv < 1e7), ("dv >= $10M", x.dv >= 1e7)]:
            L.append(f"  {lab:10s} xCO {stat(x[q], 'xco')}")
        yr = x.groupby(x.date.dt.year).agg(n=("xco", "size"), co=("xco", "mean"), cc=("xcc", "mean"))
        L.append("  by year xCO/xCC: " + " ".join(f"{y}:{r.co*1e4:+.0f}/{r.cc*1e4:+.0f}({r.n})" for y, r in yr.iterrows()))
        L.append("")
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
