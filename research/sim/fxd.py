"""Study FXD: fund (CEF/ETF/ETN) ex-dividend under-adjustment by yield per payment (pre-reg round1_prose.md, N 868).

Buy close(T-1), sell open(T) (CO) or close(T) (CC), + distribution. Excess = minus the same fund's mean non-ex return of
the same kind over the prior 60 sessions. J1 = 1998-2004 (untouched), J2 = 2005-2026 partitions. Vendor daily opens.
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

S = pathlib.Path.home() / "data" / "sharadar"
OUT = pathlib.Path(__file__).resolve().parents[2] / "data" / "research" / "program" / "fxd_out.txt"
BINS = [0, 0.005, 0.01, 0.02, 0.05, 1.0]
LAB = ["<0.5%", "0.5-1%", "1-2%", "2-5%", ">5%"]


def load():
    t = ds.dataset(S / "tickers.parquet").to_table(columns=["table", "ticker", "category"]).to_pandas()
    t = t[(t.table == "SFP") & t.category.isin(["CEF", "ETF", "ETN"])].drop_duplicates("ticker")
    cat = dict(zip(t.ticker, t.category))
    b = ds.dataset(S / "funds.parquet").to_table(
        columns=["ticker", "date", "open", "close", "volume", "closeadj", "closeunadj"],
        filter=ds.field("ticker").isin(list(cat))).to_pandas()
    b["date"] = pd.to_datetime(b.date)
    b = b.sort_values(["ticker", "date"]).reset_index(drop=True)
    b["open"] = b.open * b.closeunadj / b.close                  # raw open
    b["cat"] = b.ticker.map(cat)
    g = b.groupby("ticker", sort=False)
    b["pc"] = g.closeunadj.shift(1)
    b["dv"] = (b.closeunadj * b.volume).groupby(b.ticker).transform(lambda s: s.shift(1).rolling(20, min_periods=10).median())
    a = ds.dataset(S / "actions.parquet").to_table(columns=["date", "action", "ticker", "value"]).to_pandas()
    a = a[(a.action == "dividend") & a.ticker.isin(cat)].copy()
    a["date"] = pd.to_datetime(a.date)
    a = a.groupby(["ticker", "date"], as_index=False).value.sum().rename(columns={"value": "div"})
    m = b.merge(a, on=["ticker", "date"], how="left")
    m["ex"] = m["div"].notna()
    m["div"] = m["div"].fillna(0.0)
    m["co"] = (m.open + m["div"]) / m.pc - 1
    m["cc"] = (m.closeunadj + m["div"]) / m.pc - 1
    for c in ["co", "cc"]:                                       # own non-ex baseline, prior 60 sessions
        r = m[c].where(~m.ex)
        m[c + "_base"] = r.groupby(m.ticker).transform(lambda s: s.shift(1).rolling(60, min_periods=30).mean())
        m["x" + c] = m[c] - m[c + "_base"]
    m["y"] = m["div"] / m.pc
    # data guard: the vendor dividend must match the yield implied by the dividend-adjusted series (catches
    # split-adjusted dividends against raw prices, e.g. funds that reverse-split later)
    gc = m.groupby("ticker", sort=False)
    r_adj = m.closeadj / gc.closeadj.shift(1)
    r_px = m.close / gc.close.shift(1)
    m["y_adj"] = 1 - r_px / r_adj
    m["yok"] = (m.y / m.y_adj - 1).abs() < 0.10
    m["drop"] = (m.pc - m.closeunadj) / m["div"].where(m.ex)
    ex = m.ex & (m.pc >= 5) & (m.dv >= 2e5)
    print(f"dividend/adjusted-yield agreement on eligible ex-days: {m.loc[ex, 'yok'].mean():.3f}; by y>2%: "
          f"{m.loc[ex & (m.y > 0.02), 'yok'].mean():.3f}")
    ok = m.yok & m.ex & (m.pc >= 5) & (m.dv >= 2e5) & m.y.gt(0) & m.open.gt(0) & m.xco.notna()
    e = m[ok].copy()
    e = e[e.co.abs() < 0.5]                                      # data-error guard (|CO| >= 50%)
    e["bin"] = pd.cut(e.y, BINS, labels=LAB, right=False)
    return e


def stat(x, c):
    if len(x) < 20:
        return f"n {len(x):5d} (too few)"
    day = x.groupby("date")[c].mean()
    t = day.mean() / day.std() * np.sqrt(len(day)) if len(day) > 1 else np.nan
    srt = x[c].sort_values()
    ex5 = srt.iloc[:-5].mean()
    return (f"n {len(x):5d} mean {x[c].mean()*1e4:+6.1f} med {x[c].median()*1e4:+6.1f} t(day) {t:+5.2f} "
            f"ex-top5 {ex5*1e4:+6.1f} hit {(x[c] > 0).mean():.2f} drop/div {x['drop'].median():.2f}")


def main():
    e = load()
    L = [f"FXD: {len(e)} fund ex-events, {e.ticker.nunique()} funds, {e.date.min().date()}..{e.date.max().date()}", ""]
    for era, lo, hi in [("J1 1998-2004", "1998", "2004-12-31"), ("J2 2005-2026", "2005", "2026-12-31")]:
        L.append(f"== {era} ==")
        x0 = e[(e.date >= lo) & (e.date <= hi)]
        for cat in ["CEF", "ETF", "ETN"]:
            x1 = x0[x0.cat == cat]
            for b in LAB:
                x = x1[x1.bin == b]
                if len(x) == 0:
                    continue
                L.append(f"{cat} {b:7s} xCO {stat(x, 'xco')}")
                L.append(f"{cat} {b:7s} xCC {stat(x, 'xcc')}")
        L.append("")
    L.append("== J2 5-yr blocks, xCO mean bp (n) ==")
    e["blk"] = (e.date.dt.year - 2005) // 5 * 5 + 2005
    j2 = e[e.date >= "2005"]
    tab = j2.groupby(["cat", "bin", "blk"], observed=True).xco.agg(["mean", "size"])
    for (cat, b), g in tab.groupby(level=[0, 1], observed=True):
        L.append(f"{cat} {b:7s} " + " ".join(f"{k[2]}:{r['mean']*1e4:+.0f}({int(r['size'])})" for k, r in g.iterrows()))
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
