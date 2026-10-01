"""Study Lab-BW: industry momentum on French's 49 industries (round1_prose.md Lab Round 45).

  python -m daytrade.research.bw_replay
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

from .bt_replay import OUT as BT, first_block


def run():
    ind = first_block(BT / "49_Industry_Portfolios.csv")
    ind = ind.where(ind > -0.99)                           # -99.99 (percent) = missing
    ff = first_block(BT / "F-F_Research_Data_Factors.csv")
    mkt = ff["Mkt-RF"] + ff["RF"]
    logr = np.log1p(ind)
    mom = logr.shift(2).rolling(11, min_periods=11).sum()  # months m-12..m-2
    rows = []
    for i, m in enumerate(ind.index):
        sc = mom.loc[m].dropna()
        r = ind.loc[m]
        sc = sc[r.reindex(sc.index).notna()]
        if len(sc) < 10 or m not in mkt.index:
            continue
        top = sc.sort_values(ascending=False).index[:5]
        rows.append((m, float(r[top].mean()), float(mkt[m])))
    d = pd.DataFrame(rows, columns=["ym", "port", "mkt"]).set_index("ym")
    P = (("judged", "196307", "201512"), ("h1", "196307", "198912"), ("h2", "199001", "201512"),
         ("ref 1927-63", "192701", "196306"), ("ref 2016-26", "201601", "202608"))
    res = {}
    for tier, c in (("1x", 0.0010), ("2x", 0.0020)):
        ex = d.port - d.mkt - c
        res[tier] = {n: float(ex[(ex.index >= a) & (ex.index <= b)].mean() * 1e4) for n, a, b in P}
    ex1 = d.port - d.mkt - 0.0010
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
