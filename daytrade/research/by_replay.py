"""Study Lab-BY: top-decile momentum with a 10-month market-SMA filter (round1_prose.md Lab Round 47). French data.

  python -m daytrade.research.by_replay
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

from .bt_replay import OUT as BT, first_block


def stats(r):
    eq = (1 + r).cumprod()
    return {"cagr": float(eq.iloc[-1] ** (12 / len(r)) - 1), "sharpe": float(r.mean() / r.std(ddof=1) * math.sqrt(12)),
            "max_dd": float((eq / eq.cummax() - 1).min()),
            "worst12": float(((1 + r).rolling(12).apply(np.prod, raw=True) - 1).min())}


def run():
    mom = first_block(BT / "10_Portfolios_Prior_12_2.csv")
    ff = first_block(BT / "F-F_Research_Data_Factors.csv")
    d = pd.DataFrame({"hi": mom["Hi PRIOR"], "mkt": ff["Mkt-RF"] + ff["RF"], "rf": ff["RF"]}).dropna()
    level = (1 + d.mkt).cumprod()
    on = (level > level.rolling(10).mean()).shift(1).fillna(False).astype(bool)
    switch = on.astype(int).diff().abs().fillna(0)
    res = {}
    P = (("judged", "196307", "201512"), ("h1", "196307", "198912"), ("h2", "199001", "201512"),
         ("ref 1927-63", "192711", "196306"), ("ref 2016-26", "201601", "202608"))
    for tier, c in (("1x", 0.0020), ("2x", 0.0040)):
        sleeve = np.where(on, d.hi - c, d.rf) - switch * 0.0010
        sleeve = pd.Series(sleeve, index=d.index)
        res[tier] = {}
        for n, a, b in P:
            m = (d.index >= a) & (d.index <= b)
            res[tier][n] = {"sleeve": stats(sleeve[m]), "market": stats(d.mkt[m]),
                            "in_market": float(on[m].mean()), "switches_per_yr": float(switch[m].sum() / (m.sum() / 12))}
    r2, r1 = res["2x"], res["1x"]
    ok = (r2["h1"]["sleeve"]["cagr"] >= r2["h1"]["market"]["cagr"] and r2["h2"]["sleeve"]["cagr"] >= r2["h2"]["market"]["cagr"]
          and r1["h1"]["sleeve"]["sharpe"] > r1["h1"]["market"]["sharpe"] and r1["h2"]["sleeve"]["sharpe"] > r1["h2"]["market"]["sharpe"]
          and r1["judged"]["sleeve"]["max_dd"] > r1["judged"]["market"]["max_dd"] and r1["judged"]["sleeve"]["worst12"] > -0.30)
    res["verdict"] = "PASS" if ok else "DEAD"
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    run()
