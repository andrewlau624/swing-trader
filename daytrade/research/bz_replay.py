"""Study Lab-BZ: industry momentum (top 5 of 49) with a 10-month market-SMA filter (round1_prose.md Lab Round 48).

  python -m daytrade.research.bz_replay
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .bt_replay import OUT as BT, first_block
from .by_replay import stats


def run():
    ind = first_block(BT / "49_Industry_Portfolios.csv")
    ind = ind.where(ind > -0.99)
    ff = first_block(BT / "F-F_Research_Data_Factors.csv")
    mkt, rf = ff["Mkt-RF"] + ff["RF"], ff["RF"]
    mom = np.log1p(ind).shift(2).rolling(11, min_periods=11).sum()
    port = {}
    for m in ind.index:
        sc = mom.loc[m].dropna()
        sc = sc[ind.loc[m].reindex(sc.index).notna()]
        if len(sc) >= 10:
            port[m] = float(ind.loc[m, sc.sort_values(ascending=False).index[:5]].mean())
    d = pd.DataFrame({"ind": pd.Series(port), "mkt": mkt, "rf": rf}).dropna()
    level = (1 + d.mkt).cumprod()
    on = (level > level.rolling(10).mean()).shift(1).fillna(False).astype(bool)
    switch = on.astype(int).diff().abs().fillna(0)
    res = {}
    P = (("judged", "196307", "201512"), ("h1", "196307", "198912"), ("h2", "199001", "201512"),
         ("ref 1927-63", "192711", "196306"), ("ref 2016-26", "201601", "202608"))
    for tier, c in (("1x", 0.0010), ("2x", 0.0020)):
        sleeve = pd.Series(np.where(on, d.ind - c, d.rf) - switch * 0.0010, index=d.index)
        res[tier] = {n: {"sleeve": stats(sleeve[(d.index >= a) & (d.index <= b)]),
                         "market": stats(d.mkt[(d.index >= a) & (d.index <= b)])} for n, a, b in P}
    r2, r1 = res["2x"], res["1x"]
    ok = (r2["h1"]["sleeve"]["cagr"] >= r2["h1"]["market"]["cagr"] and r2["h2"]["sleeve"]["cagr"] >= r2["h2"]["market"]["cagr"]
          and r1["h1"]["sleeve"]["sharpe"] > r1["h1"]["market"]["sharpe"] and r1["h2"]["sleeve"]["sharpe"] > r1["h2"]["market"]["sharpe"]
          and r1["judged"]["sleeve"]["max_dd"] > r1["judged"]["market"]["max_dd"] and r1["judged"]["sleeve"]["worst12"] > -0.30)
    res["verdict"] = "PASS" if ok else "DEAD"
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    run()
