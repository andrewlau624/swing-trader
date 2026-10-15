"""13F-state aggregation (regulatory-cap forced-sell discovery family).

Per (ticker, 13F-quarter): total/max reported shares, holder count, implied shares outstanding
(marketcap / closeunadj at quarter end), fund-flavor share by investor-name regex, total value.
Output: data/research/f13f/agg.parquet. No returns are read here.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

STORE = "/Users/andrewlau/data/sharadar"
OUT = "data/research/f13f/agg.parquet"

FUND_RE = ("fidelity|vanguard|blackrock|t\\. rowe|capital research|capital group|capital wor|dodge|"
           "voya|franklin|davis|putnam|lord abbett|invesco|wells fargo|morgan stanley|jpmorgan|"
           "goldman sachs|northern trust|schroder|neuberger|principal|empower|american century|"
           "mainstay|harris associates|ab (?:mun|small)|institutional funds|select fund|value fund|"
           "growth fund|equity fund|saturna|calvert|second half")


def main() -> None:
    h = pd.read_parquet(f"{STORE}/holdings.parquet", columns=["ticker", "date", "investorid", "units", "value", "securitytype"])
    h = h[h.securitytype == "SHR"]  # common shares only
    h["date"] = pd.to_datetime(h["date"])
    inv = pd.read_parquet(f"{STORE}/holdings_investor.parquet", columns=["investorid", "investorname"])
    fan = inv.sort_values("investorid").drop_duplicates("investorid").set_index("investorid")["investorname"]
    h["fund"] = h.investorid.map(fan).fillna("").str.contains(FUND_RE, case=False, regex=True)
    h["fu"] = h.units.where(h.fund)
    g = h.groupby(["ticker", "date"], sort=True)
    X = pd.DataFrame({"tot": g.units.sum(), "mx": g.units.max(), "n": g.units.size(), "tv": g.value.sum(),
                      "mxf": h[h.fund].groupby(["ticker", "date"]).units.max()})
    fu = h.groupby(["ticker", "date"], sort=True)["fu"].sum().rename("fu")
    A = X.join(fu, how="left").fillna({"fu": 0.0}).reset_index()
    A["date"] = pd.to_datetime(A["date"])
    qds = list(pd.to_datetime(sorted(A["date"].unique())))
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
    from lh_panel import Panel
    P = Panel.load()
    maskset = {int(np.searchsorted(P.dates, np.datetime64(np.datetime64(d))) - 1) for d in qds}
    rows = np.flatnonzero(np.isin(P.di, np.array(sorted(maskset))) & (P.src == 0))
    dl = pd.DataFrame({"ticker": P.tickers[P.tid[rows]], "qli": P.di[rows],
                       "cu": P.cu[rows].astype("float64")})
    A["qli"] = [int(np.searchsorted(P.dates, np.datetime64(np.datetime64(d))) - 1) for d in A["date"]]
    A = A.merge(dl, on=["ticker", "qli"], how="left").reset_index(drop=True)
    A = A.rename(columns={"cu": "closeunadj"})
    mc = pd.read_parquet(f"{STORE}/daily.parquet", columns=["ticker", "date", "marketcap"])
    mc = mc.assign(date=pd.to_datetime(mc["date"]))
    mc = mc[mc["date"].isin(qds)].rename(columns={"date": "date", "marketcap": "mcapM"})  # $M
    A = A.merge(mc, on=["ticker", "date"], how="left")
    A["sh6"] = A["mcapM"] / A.closeunadj.replace(0, np.nan)   # shares in MILLIONS
    A["mxp"] = A.mx * 1e3 / (A.sh6 * 1e6)   # units are shares in thousands                            # max holder as % of shares out
    A["opp"] = A.tot * 1e3 / (A.sh6 * 1e6)
    A["fxp"] = A.fu * 1e3 / (A.sh6 * 1e6)
    A["mfpx"] = A.mxf.fillna(0) * 1e3 / (A.sh6 * 1e6)
    print(A[["mxp", "opp", "fxp"]].describe(percentiles=[.25, .5, .75, .9, .99]).T)
    A.to_parquet(OUT, index=False)
    print("agg", len(A), "->", OUT)


if __name__ == "__main__":
    main()
