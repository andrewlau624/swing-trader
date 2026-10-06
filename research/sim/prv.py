"""Study PRV: liquidity-provision reversal in thin $25-par paper (pre-reg round1_prose.md, N 873).

Sharadar SEP preferreds + SFP ETD/CEF Preferred. Idio move m = close/prev close - 1 minus the day's cross-sectional
median; signal m <= -2%, excluding T-1..T+2 around the name's ex-dates and closes < $15. Buy close(T), sell open(T+1)
(CO) or close(T+1) (CC). Writes the signal list for the official-cross check (J3).
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

S = pathlib.Path.home() / "data" / "sharadar"
ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/prv_out.txt"


def panel() -> pd.DataFrame:
    t = ds.dataset(S / "tickers.parquet").to_table(columns=["table", "ticker", "category"]).to_pandas()
    parts = []
    for table, file, cats in [("SEP", "stocks.parquet", ["Domestic Preferred Stock"]),
                              ("SFP", "funds.parquet", ["ETD", "CEF Preferred"])]:
        tk = set(t[(t.table == table) & t.category.isin(cats)].ticker)
        b = ds.dataset(S / file).to_table(columns=["ticker", "date", "open", "close", "volume", "closeunadj"],
                                          filter=ds.field("ticker").isin(list(tk))).to_pandas()
        b["cls"] = "pref" if table == "SEP" else "etd"
        parts.append(b)
    b = pd.concat(parts, ignore_index=True)
    b["date"] = pd.to_datetime(b.date)
    b = b.drop_duplicates(["ticker", "date"]).sort_values(["ticker", "date"]).reset_index(drop=True)
    b["open"] = b.open * b.closeunadj / b.close
    a = ds.dataset(S / "actions.parquet").to_table(columns=["date", "action", "ticker", "value"]).to_pandas()
    a = a[(a.action == "dividend") & a.ticker.isin(set(b.ticker))]
    ex = set(zip(a.ticker, pd.to_datetime(a.date)))
    b["isex"] = [(k, d) in ex for k, d in zip(b.ticker, b.date)]
    g = b.groupby("ticker", sort=False)
    b["near_ex"] = (b.isex | g.isex.shift(-1, fill_value=False) | g.isex.shift(1, fill_value=False)
                    | g.isex.shift(2, fill_value=False) | g.isex.shift(-2, fill_value=False))
    b["pc"] = g.closeunadj.shift(1)
    b["r"] = b.closeunadj / b.pc - 1
    b["dv"] = (b.closeunadj * b.volume).groupby(b.ticker).transform(lambda s: s.shift(1).rolling(20, min_periods=10).median())
    b["co"] = g.open.shift(-1) / b.closeunadj - 1
    b["cc"] = g.closeunadj.shift(-1) / b.closeunadj - 1
    b["nx_ex"] = g.near_ex.shift(-1, fill_value=False)
    u = b[(b.pc.between(10, 60)) & (b.closeunadj >= 15) & (b.dv >= 1e5) & ~b.near_ex & ~b.nx_ex
          & b.r.notna() & b.co.notna() & b.cc.notna()].copy()
    u["m"] = u.r - u.groupby("date").r.transform("median")
    return u[(u.co.abs() < 0.3) & (u.cc.abs() < 0.3)]


def stat(x: pd.DataFrame, c: str) -> str:
    if len(x) < 20:
        return f"n {len(x)}"
    day = x.groupby("date")[c].mean()
    t = day.mean() / day.std() * np.sqrt(len(day))
    yrs = x.groupby(x.date.dt.year)[c].mean()
    return (f"n {len(x):6d} mean {x[c].mean()*1e4:+6.1f} med {x[c].median()*1e4:+6.1f} t {t:+5.2f} "
            f"ex-top5 {np.sort(x[c].values)[:-5].mean()*1e4:+6.1f} hit {(x[c] > 0).mean():.2f} yrs>0 {(yrs > 0).sum()}/{len(yrs)}")


def main():
    u = panel()
    L = [f"PRV: universe {len(u)} name-days, {u.ticker.nunique()} names, {u.date.min().date()}..{u.date.max().date()}"]
    for era, lo, hi in [("J1 1998-2015", "1998", "2015-12-31"), ("J2 2016-2026", "2016", "2026-12-31")]:
        x0 = u[(u.date >= lo) & (u.date <= hi)]
        L.append(f"\n== {era} ==")
        for lab, q in [("SIGNAL m<=-2%", x0.m <= -0.02), ("mirror m>=+2%", x0.m >= 0.02), ("control |m|<0.5%", x0.m.abs() < 0.005),
                       ("m<=-4%", x0.m <= -0.04)]:
            for c in ["cc", "co"]:
                L.append(f"{lab:17s} {c}: {stat(x0[q], c)}")
        s = x0[x0.m <= -0.02]
        for k, g in s.groupby("cls"):
            L.append(f"  signal {k:4s} cc: {stat(g, 'cc')}")
    s = u[u.m <= -0.02]
    L.append("\nsignal by year CC/CO: " + " ".join(f"{y}:{g.cc.mean()*1e4:+.0f}/{g.co.mean()*1e4:+.0f}({len(g)})"
                                                  for y, g in s.groupby(s.date.dt.year)))
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))
    s[s.date >= "2021"][["ticker", "date", "cls", "m", "closeunadj", "dv"]].to_parquet(ROOT / "data/research/prv_signals.parquet")


if __name__ == "__main__":
    main()
