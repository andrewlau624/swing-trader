"""Study Lab-BV: long-only long-term reversal (Lo PRIOR 60-13 decile) vs the market (round1_prose.md Lab Round 44).

  python -m daytrade.research.bv_replay
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

from .bt_replay import OUT as BT, first_block


def run():
    lt = first_block(BT / "10_Portfolios_Prior_60_13.csv")
    ff = first_block(BT / "F-F_Research_Data_Factors.csv")
    d = pd.DataFrame({"lo": lt["Lo PRIOR"], "mkt": ff["Mkt-RF"] + ff["RF"]}).dropna()
    res = {}
    P = (("judged", "196307", "201512"), ("h1", "196307", "198912"), ("h2", "199001", "201512"),
         ("ref 1927-63", "192701", "196306"), ("ref 2016-26", "201601", "202608"))
    for tier, c in (("1x", 0.0010), ("2x", 0.0020)):
        ex = d.lo - d.mkt - c
        res[tier] = {n: float(ex[(ex.index >= a) & (ex.index <= b)].mean() * 1e4) for n, a, b in P}
    ex1 = d.lo - d.mkt - 0.0010
    j = ex1[(ex1.index >= "196307") & (ex1.index <= "201512")]
    res["t"] = float(j.mean() / (j.std(ddof=1) / math.sqrt(len(j))))
    res["without_best5"] = float(np.sort(j.values)[:-5].mean() * 1e4)
    roll = (1 + ex1).rolling(12).apply(np.prod, raw=True) - 1
    res["worst12"] = [float(roll.min()), str(roll.idxmin())]
    res["by_decade"] = {k: float(g.mean() * 1e4) for k, g in ex1.groupby(ex1.index.str[:3] + "0s")}
    a2 = res["2x"]
    res["verdict"] = "PASS" if a2["h1"] > 0 and a2["h2"] > 0 and res["t"] >= 2 and res["without_best5"] > 0 else "DEAD"
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    run()
