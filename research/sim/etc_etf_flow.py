"""Study ETC runner (pre-reg research/drafts/study_etc_etf_flow.md).

SPY daily creation/redemption (shares-outstanding change) as a signal for next-day pressure.

Run: PYTHONPATH=. .venv/bin/python -m research.sim.etc_etf_flow
"""
from __future__ import annotations

import pathlib
import urllib.request

import numpy as np
import pandas as pd

from . import data as D

ROOT = pathlib.Path(__file__).resolve().parents[2]
CACHE = ROOT / "data/research/program/etc_spy_nav.parquet"
OUT = ROOT / "data/research/program/etc_etf_flow_out.txt"
URL = "https://www.ssga.com/library-content/products/fund-data/etfs/us/navhist-us-en-spy.xlsx"


def nav() -> pd.DataFrame:
    if CACHE.exists():
        return pd.read_parquet(CACHE)
    raw = urllib.request.urlopen(URL, timeout=60).read()
    tmp = ROOT / "data/research/program/_spy_nav.xlsx"
    tmp.write_bytes(raw)
    x = pd.read_excel(tmp, sheet_name=0, header=3)
    x = x.rename(columns={x.columns[0]: "Date", x.columns[1]: "NAV",
                          x.columns[2]: "Shares", x.columns[3]: "TNA"})
    x = x[["Date", "NAV", "Shares", "TNA"]]
    x["Date"] = pd.to_datetime(x["Date"], errors="coerce")
    for c in ["NAV", "Shares", "TNA"]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x = x.dropna(subset=["Date", "NAV", "Shares"]).sort_values("Date")
    x.to_parquet(CACHE)
    return x


def main():
    nv = nav()
    P = D.etf()
    C = P["close"]
    # Use the DAILY CHANGE of shares-outstanding (scale-free, adjustment-proof) AND build the
    # true discount from RAW closes (etf_daily is split/DIV-adjusted -> a fake -15% "discount").
    import os
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.data import _clients
    k, _s = _clients()
    c = _clients()[0]
    rawf = ROOT / "data/research/program/etc_spy_raw.parquet"
    if rawf.exists():
        raw = pd.read_parquet(rawf)
    else:
        df = c.get_stock_bars(StockBarsRequest(symbol_or_symbols=["SPY"], timeframe=TimeFrame.Day,
                              start="2016-01-01", end="2026-09-22", feed="sip",
                              adjustment="raw")).df.reset_index()
        df["t"] = (pd.to_datetime(df.timestamp, utc=True).dt.tz_convert("America/New_York")
                   .dt.normalize().dt.tz_localize(None))
        raw = df.pivot_table(index="t", columns="symbol", values="close")
        raw.to_parquet(rawf)
    spy_raw = raw["SPY"]
    spy_adj = C["SPY"]
    df = nv.set_index("Date")
    df["flow"] = df["Shares"].pct_change()
    df["disc"] = (spy_raw.reindex(df.index) - df["NAV"]) / df["NAV"]
    df["r1"] = spy_raw.reindex(df.index).pct_change().shift(-1)     # next close->close (raw)
    df = df.dropna(subset=["flow", "r1", "disc"])
    df = df[df.index >= "2016-01-01"]
    b = 1e4
    lines = ["Study ETC: SPY shares-outstanding flow -> next-day return",
             f"days={len(df)}  span {df.index.min().date()}..{df.index.max().date()}", ""]
    df["q"] = pd.qcut(df["flow"].rank(method="first"), 5, labels=["redeem2", "redeem1", "flat", "create1", "create2"])
    lines.append("next-day (t close -> t+1 close) return by flow quintile, bp:")
    for q, g in df.groupby("q", observed=True):
        t = g["r1"].mean() / g["r1"].std() * np.sqrt(len(g))
        lines.append(f"  {q:8s} n={len(g):4d} mean={g['r1'].mean()*b:6.2f}bp t={t:5.2f} "
                     f"hit={(g['r1']>0).mean()*100:3.0f}% flow_med={g['flow'].median()*100:5.2f}%")
    # top-|flow| bucket (unusual creations/redemptions)
    df["absq"] = pd.qcut(df["flow"].abs().rank(method="first"), 5, labels=False)
    big = df[df.absq == 4]
    lines += ["", f"largest-|flow| quintile: n={len(big)} next-day mean={big['r1'].mean()*b:.2f}bp "
                  f"t={big['r1'].mean()/big['r1'].std()*np.sqrt(len(big)):.2f}"]
    # sign of big flows
    for s, lab in [(1, "big creation"), (-1, "big redemption")]:
        g = big[np.sign(big["flow"]) == s]
        if len(g) > 10:
            lines.append(f"  {lab}: n={len(g)} next-day mean={g['r1'].mean()*b:.2f}bp "
                         f"t={g['r1'].mean()/g['r1'].std()*np.sqrt(len(g)):.2f}")
    # discount reversion
    df["dbq"] = pd.qcut(df["disc"], 5, labels=["deep disc", "d2", "d3", "d4", "premium"])
    lines += ["", "discount quintile -> next-day return (bp):"]
    for q, g in df.groupby("dbq", observed=True):
        lines.append(f"  {q:10s} n={len(g):4d} mean={g['r1'].mean()*b:6.2f}bp disc_med={g['disc'].median()*100:5.3f}%")
    # by year of the big-flow effect
    lines += ["", "big-flow next-day by year:"]
    for y, g in big.groupby(big.index.year):
        if len(g) >= 20:
            lines.append(f"  {y}: n={len(g)} mean={g['r1'].mean()*b:6.2f}bp t={g['r1'].mean()/g['r1'].std()*np.sqrt(len(g)):5.2f}")
    # net after 2bp/day cost (SPY)
    lines += ["", f"SPY round-trip cost ~1-2bp; any |mean| < ~3bp/day is not tradable."]
    text = "\n".join(lines) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
