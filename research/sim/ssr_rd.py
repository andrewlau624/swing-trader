"""Probe SSR-RD: does Rule 201 (short-sale restriction) create a discontinuity at a -10% intraday low?

Mechanism: once a stock trades 10% below the prior close, short sales may only print above the
national best bid for the rest of day T and all of T+1. Aggressive shorting is blocked, so if
short sellers move price, names just past -10% should do better on T+1 (and maybe worse on T+2
when the restriction lifts) than names that stopped just short of -10%.

Design: diff-in-discontinuity in the running variable L = low/prev_close - 1, cutoff -10%.
  post = 2011-11-10 .. (Rule 201 in force), pre = 2003-01 .. 2011-11-09 (no -10% rule).
  Local linear, bandwidth +/-3pp, controls for the day's close return R; SE clustered by date.
Daily bars only (Sharadar SEP, delisted included): the trigger is the trade low, a proxy for
the NBB trigger; extended-hours prints are not in the bar, so the RD is fuzzy, not sharp.
Exploratory probe, no N (cheap kill test before any registration).
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

STORE = pathlib.Path.home() / "data" / "sharadar"
POST = pd.Timestamp("2011-11-10")
OUT = pathlib.Path(__file__).with_name("ssr_rd_out.txt")
BW = 0.03


def load() -> pd.DataFrame:
    t = ds.dataset(STORE / "tickers.parquet").to_table(
        columns=["table", "ticker", "category"]).to_pandas()
    common = set(t.loc[(t.table == "SEP") & t.category.fillna("").str.contains("Common Stock")
                       & ~t.category.fillna("").str.contains("ADR|Warrant|Preferred"), "ticker"])
    b = ds.dataset(STORE / "stocks.parquet").to_table(
        columns=["ticker", "date", "open", "low", "close", "volume", "closeunadj"],
        filter=ds.field("date") >= pd.Timestamp("2002-11-01").date()).to_pandas()
    b = b[b.ticker.isin(common)]
    b["date"] = pd.to_datetime(b.date)
    return b.sort_values(["ticker", "date"]).reset_index(drop=True)


def panel(b: pd.DataFrame) -> pd.DataFrame:
    g = b.groupby("ticker", sort=False)
    pc = g.close.shift(1)
    b["L"] = b.low / pc - 1
    b["R"] = b.close / pc - 1
    b["praw"] = g.closeunadj.shift(1)
    dv = b.close * b.volume
    b["adv"] = dv.groupby(b.ticker).transform(lambda s: s.shift(1).rolling(20, min_periods=15).mean())
    o1, c1, c2 = g.open.shift(-1), g.close.shift(-1), g.close.shift(-2)
    b["night"] = o1 / b.close - 1
    b["day1"] = c1 / o1 - 1
    b["cc1"] = c1 / b.close - 1
    b["cc2"] = c2 / c1 - 1
    # market: equal-weight universe mean of the same outcome on the same date (all liquid names)
    liq = (b.praw >= 5) & (b.adv >= 5e6)
    for k in ["night", "day1", "cc1", "cc2"]:
        b[k] = b[k].clip(-0.9, 2.0)
        mk = b[k].where(liq).groupby(b.date).transform("mean")
        b[k + "_x"] = b[k] - mk
    s = b[liq & b.L.between(-0.10 - BW, -0.10 + BW) & (b.date >= "2003-01-01")].copy()
    return s.dropna(subset=["L", "R", "night", "day1", "cc2"])


def rd(s: pd.DataFrame, y: str) -> tuple[float, float, int]:
    """Discontinuity at L=-10% (treated = L <= -10%), local linear with R control, date-clustered."""
    x = s.L.values + 0.10
    d = (x <= 0).astype(float)
    X = np.column_stack([np.ones_like(x), d, x, x * d, s.R.values])
    Y = s[y].values
    beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
    e = Y - X @ beta
    XtX_inv = np.linalg.inv(X.T @ X)
    codes = pd.factorize(s.date)[0]
    G = np.zeros((codes.max() + 1, X.shape[1]))
    np.add.at(G, codes, X * e[:, None])
    V = XtX_inv @ (G.T @ G) @ XtX_inv
    return beta[1] * 1e4, beta[1] / np.sqrt(V[1, 1]), len(s)


def main():
    s = panel(load())
    lines = ["SSR-RD probe: discontinuity at intraday low = -10% (treated minus control, bp), BW +/-3pp, R control",
             f"rows {len(s)}  pre {int((s.date < POST).sum())}  post {int((s.date >= POST).sum())}", ""]
    eras = {"pre 2003-11/2011": s[s.date < POST], "post 2011-11..": s[s.date >= POST],
            "post 2011-18": s[(s.date >= POST) & (s.date < "2019-01-01")],
            "post 2019-26": s[s.date >= "2019-01-01"]}
    for y in ["night", "day1", "cc1", "cc2", "night_x", "day1_x", "cc1_x", "cc2_x"]:
        row = [f"{y:8s}"]
        for k, e in eras.items():
            b, t, n = rd(e, y)
            row.append(f"{k}: {b:+7.1f} (t {t:+5.2f}, n {n})")
        lines.append("  ".join(row))
    # raw means either side within 1pp (sanity, no model)
    lines.append("")
    for k, e in [("pre", s[s.date < POST]), ("post", s[s.date >= POST])]:
        near = e[e.L.between(-0.11, -0.09)]
        tr, co = near[near.L <= -0.10], near[near.L > -0.10]
        lines.append(f"{k} +/-1pp raw means (bp): treated n {len(tr)} night {tr.night.mean()*1e4:+.1f} day1 "
                     f"{tr.day1.mean()*1e4:+.1f} cc2 {tr.cc2.mean()*1e4:+.1f} | control n {len(co)} night "
                     f"{co.night.mean()*1e4:+.1f} day1 {co.day1.mean()*1e4:+.1f} cc2 {co.cc2.mean()*1e4:+.1f}")
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
