"""Study ETDX: the frozen PREF-EX rule on $25-par exchange-traded debt and CEF preferreds (pre-reg round1_prose.md, N 869).

Buy close(T-1), sell open(T) (CO) or close(T) (CC), + distribution. Sharadar SFP daily (vendor opens). FXD dividend guard.
Also: overlap with SEP preferred ex-dates (capacity increment).
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

S = pathlib.Path.home() / "data" / "sharadar"
OUT = pathlib.Path(__file__).resolve().parents[2] / "data" / "research" / "program" / "etdx_out.txt"


def events(table, file, cats):
    t = ds.dataset(S / "tickers.parquet").to_table(columns=["table", "ticker", "category"]).to_pandas()
    t = t[(t.table == table) & t.category.isin(cats)].drop_duplicates("ticker")
    cat = dict(zip(t.ticker, t.category))
    b = ds.dataset(S / file).to_table(
        columns=["ticker", "date", "open", "close", "volume", "closeadj", "closeunadj"],
        filter=ds.field("ticker").isin(list(cat))).to_pandas()
    b["date"] = pd.to_datetime(b.date)
    b = b.sort_values(["ticker", "date"]).reset_index(drop=True)
    b["open"] = b.open * b.closeunadj / b.close
    b["cat"] = b.ticker.map(cat)
    g = b.groupby("ticker", sort=False)
    b["pc"] = g.closeunadj.shift(1)
    b["d0"] = g.date.shift(1)
    b["y_adj"] = 1 - (b.close / g.close.shift(1)) / (b.closeadj / g.closeadj.shift(1))
    b["dv"] = (b.closeunadj * b.volume).groupby(b.ticker).transform(lambda s: s.shift(1).rolling(20, min_periods=10).median())
    a = ds.dataset(S / "actions.parquet").to_table(columns=["date", "action", "ticker", "value"]).to_pandas()
    a = a[(a.action == "dividend") & a.ticker.isin(cat)].copy()
    a["date"] = pd.to_datetime(a.date)
    a = a.groupby(["ticker", "date"], as_index=False).value.sum().rename(columns={"value": "div"})
    m = b.merge(a, on=["ticker", "date"], how="left")
    m["ex"] = m["div"].notna()
    m["div"] = m["div"].fillna(0.0)
    m["y"] = m["div"] / m.pc
    m["co"] = (m.open + m["div"]) / m.pc - 1
    m["cc"] = (m.closeunadj + m["div"]) / m.pc - 1
    m["drop"] = (m.pc - m.closeunadj) / m["div"].where(m.ex)
    m = m[(m.pc >= 10) & (m.pc <= 60) & (m.dv >= 1e5) & m.open.gt(0)].dropna(subset=["pc"])
    guard = (m.y / m.y_adj - 1).abs() < 0.10
    exm = m.ex & m.y.between(0.002, 0.04)
    return m[exm & guard].copy(), m[~m.ex].copy(), (exm & ~guard).sum()


def line(e, c):
    day = e.groupby("date")[c].mean()
    t = day.mean() / day.std() * np.sqrt(len(day))
    yrs = e.groupby(e.date.dt.year)[c].mean()
    return (f"{c}: n {len(e):5d} mean {e[c].mean()*1e4:+6.1f} med {e[c].median()*1e4:+6.1f} t(day) {t:+5.2f} "
            f"ex-top5 {e[c].sort_values().iloc[:-5].mean()*1e4:+6.1f} hit {(e[c] > 0).mean():.2f} "
            f"yrs>0 {(yrs > 0).sum()}/{len(yrs)} 2021-26 {e.loc[e.date >= '2021', c].mean()*1e4:+6.1f}")


def main():
    L = []
    e, n, bad = events("SFP", "funds.parquet", ["ETD", "CEF Preferred"])
    L.append(f"ETDX: {len(e)} guarded ex-events ({bad} dropped by the dividend guard), {e.ticker.nunique()} names")
    pref, _, _ = events("SEP", "stocks.parquet", ["Domestic Preferred Stock"])
    pdates = set(pref.date)
    for cat in ["ETD", "CEF Preferred"]:
        x, nx = e[e.cat == cat], n[n.cat == cat]
        L.append(f"\n== {cat} == drop/div med {x['drop'].median():.2f} | yield/payment med {x.y.median()*1e4:.0f}bp | "
                 f"non-ex CO mean {nx.co.mean()*1e4:+.1f} med {nx.co.median()*1e4:+.1f} | non-ex CC mean {nx.cc.mean()*1e4:+.1f}")
        for c in ["co", "cc"]:
            L.append("  " + line(x, c))
        yr = x.groupby(x.date.dt.year).agg(n=("co", "size"), co=("co", "mean"), cc=("cc", "mean"))
        L.append("  by year CO/CC: " + " ".join(f"{y}:{r.co*1e4:+.0f}/{r.cc*1e4:+.0f}({r.n})" for y, r in yr.iterrows()))
        for lab, q in [("dv<$300k", x.dv < 3e5), ("dv $300k-1M", x.dv.between(3e5, 1e6)), ("dv>=$1M", x.dv >= 1e6)]:
            L.append(f"  {lab:12s} " + line(x[q], "co") if q.sum() > 20 else f"  {lab} n {q.sum()}")
        ed = set(x.date)
        new = len(ed - pdates)
        L.append(f"  ex-nights {len(ed)}, of which {new} ({new/len(ed):.0%}) have no SEP-preferred ex-event")
    L.append(f"\nreference SEP preferreds same filter: " + line(pref, "co"))
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
