"""VIX futures panel + synthetic short-term VIX futures index (SPVXSP-style), 2004+.

Sources (free, downloaded 2026-11-06 into data/research/vrp/):
  cfe/CFE_{m}{yy}_VX.csv  Cboe CFE archive, contracts expiring 2004-2014 (pre-2007-03-26 prices are VBI = 10x VIX)
  vx/VX_{expiry}.csv      Cboe CFE per-contract history, monthly contracts expiring 2013+
  y_*.parquet             Yahoo daily closes (^VIX, ^VIX3M, SVXY, SVIX, VIXY, ^IRX ...) via research.sim.vts.yahoo
Read with `python3 -I` (downloaded data).
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/vrp"


def _read(f: pathlib.Path) -> pd.DataFrame:
    skip = 0 if open(f).readline().startswith("Trade Date") else 1  # some archive files carry a disclaimer line
    x = pd.read_csv(f, skiprows=skip, usecols=range(11), index_col=False)
    x.columns = [c.strip() for c in x.columns]
    x["date"] = pd.to_datetime(x["Trade Date"], format="mixed")
    x["settle"] = pd.to_numeric(x["Settle"], errors="coerce")
    x = x[x["settle"] > 0][["date", "settle"]].copy()
    if len(x) == 0:
        return x
    x["expiry"] = x["date"].max()  # last row with a settle = final settlement day
    return x


def futures() -> pd.DataFrame:
    """Long panel date, expiry, settle (VIX points). Archive used for expiries < 2013-06, per-contract after."""
    parts = []
    for f in sorted((D / "cfe").glob("CFE_*_VX.csv")):
        x = _read(f)
        if len(x) and x["expiry"].iloc[0] < pd.Timestamp("2013-06-01"):
            parts.append(x)
    for f in sorted((D / "vx").glob("VX_*.csv")):
        x = _read(f)
        if len(x) and x["expiry"].iloc[0] >= pd.Timestamp("2013-06-01"):
            x = x[x["expiry"] <= pd.Timestamp.now()]
            # contracts not yet expired: the last settle row is not the expiry; use the file-name date
            e = pd.Timestamp(f.stem.split("_")[1])
            x["expiry"] = e
            parts.append(x)
    P = pd.concat(parts, ignore_index=True)
    P.loc[P["date"] < pd.Timestamp("2007-03-26"), "settle"] /= 10.0  # VBI -> VIX points
    P = P.drop_duplicates(["date", "expiry"]).sort_values(["date", "expiry"])
    return P


def curve(P: pd.DataFrame | None = None) -> pd.DataFrame:
    """Per date: F1/F2 = first two contracts with expiry > date (F1 on its expiry day rolls to the next),
    e1/e2 their expiries; plus yesterday's same-contract settles for daily returns."""
    P = futures() if P is None else P
    P = P[P["expiry"] > P["date"]]
    g = P.groupby("date")
    F1 = g.nth(0).set_index("date"); F2 = g.nth(1).set_index("date")
    C = pd.DataFrame({"F1": F1["settle"], "e1": F1["expiry"], "F2": F2["settle"], "e2": F2["expiry"]}).dropna()
    key = P.set_index(["date", "expiry"])["settle"]
    dates = C.index
    prev = pd.Series(dates[:-1], index=dates[1:])
    C["pdate"] = prev
    C = C.iloc[1:]
    C["F1_prev"] = [key.get((d, e), np.nan) for d, e in zip(C["pdate"], C["e1"])]
    C["F2_prev"] = [key.get((d, e), np.nan) for d, e in zip(C["pdate"], C["e2"])]
    return C


def synthetic(C: pd.DataFrame | None = None) -> pd.DataFrame:
    """SPVXSP-style constant ~1-month long VIX futures daily return (excess, no collateral):
    weights set at t-1: w1 = business days from t-1 to e1 / business days from e0 (previous expiry) to e1."""
    C = curve() if C is None else C
    bd = pd.bdate_range("2003-01-01", "2028-12-31")
    pos = pd.Series(np.arange(len(bd)), index=bd)
    # previous expiry = e1 of the first date of this contract's front period: approximate by e1 - 1 month span
    w1 = []
    exps = sorted(C["e1"].unique())
    prev_exp = {e: (exps[i - 1] if i else e - pd.Timedelta(days=28)) for i, e in enumerate(exps)}
    for d, e in zip(C["pdate"], C["e1"]):
        e0 = prev_exp[e]
        tot = pos.get(pd.Timestamp(e), np.nan) - pos.get(pd.Timestamp(e0), np.nan)
        rem = pos.get(pd.Timestamp(e), np.nan) - pos.get(pd.Timestamp(d), np.nan)
        w1.append(min(max(rem / tot, 0.0), 1.0))
    C = C.copy()
    C["w1"] = w1
    # weights fixed at t-1 on t-1's front pair; if the front rolled between t-1 and t, F1_prev is NaN -> use the
    # t-1 pair explicitly via the panel
    num = C["w1"] * C["F1"] + (1 - C["w1"]) * C["F2"]
    den = C["w1"] * C["F1_prev"] + (1 - C["w1"]) * C["F2_prev"]
    C["r_long"] = num / den - 1
    return C


def yclose(sym: str) -> pd.Series:
    return pd.read_parquet(D / f"y_{sym.replace('^', '')}.parquet")["close"]


if __name__ == "__main__":
    C = synthetic()
    print(C[["F1", "F2", "w1", "r_long"]].describe())
    print("NaN r_long:", C["r_long"].isna().sum(), "of", len(C), C.index.min(), C.index.max())
    vixy = yclose("VIXY").pct_change(fill_method=None)
    svxy = yclose("SVXY").pct_change(fill_method=None)
    J = pd.DataFrame({"syn": C["r_long"], "vixy": vixy, "svxy": svxy}).dropna()
    for lo, hi in [("2011", "2017"), ("2018-03", "2026")]:
        x = J.loc[lo:hi]
        print(lo, hi, "corr syn~vixy %.4f syn~svxy %.4f" % (x.corr().loc["syn", "vixy"], x.corr().loc["syn", "svxy"]),
              "ann mean syn %.1f%% vixy %.1f%%" % (x["syn"].mean() * 252 * 100, x["vixy"].mean() * 252 * 100))
    print(C.loc["2018-02-01":"2018-02-09", ["F1", "F2", "w1", "r_long"]])
    print(C.loc["2008-10-01":"2008-10-10", ["F1", "F2", "w1", "r_long"]])
    print(C["r_long"].nlargest(8))
