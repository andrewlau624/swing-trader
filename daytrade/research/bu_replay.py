"""Study Lab-BU: volatility-scaled top-decile momentum (round1_prose.md Lab Round 43). French data from Lab-BT.

  python -m daytrade.research.bu_replay
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

from .bt_replay import OUT as BT, first_block
from ..settings import DATA

OUT = DATA / "research" / "bu"
TARGET = 0.12


def run():
    mom = first_block(BT / "10_Portfolios_Prior_12_2.csv")
    ff = first_block(BT / "F-F_Research_Data_Factors.csv")
    d = pd.DataFrame({"hi": mom["Hi PRIOR"], "mkt": ff["Mkt-RF"] + ff["RF"]}).dropna()
    gross = d.hi - d.mkt
    vol = gross.rolling(6).std().shift(1) * math.sqrt(12)
    w = (TARGET / vol).clip(upper=1.0)
    res = {}
    periods = (("judged", "196307", "201512"), ("h1", "196307", "198912"), ("h2", "199001", "201512"),
               ("ref 1927-63", "192707", "196306"), ("ref 2016-26", "201601", "202608"))
    for tier, c in (("1x", 0.0020), ("2x", 0.0040)):
        un = gross - c
        sc = w * (gross - c)
        out = {}
        for name, a, b in periods:
            m = (d.index >= a) & (d.index <= b) & w.notna()
            sh = lambda x: float(x[m].mean() / x[m].std(ddof=1) * math.sqrt(12))  # noqa: E731
            r12 = lambda x: float(((1 + x[m]).rolling(12).apply(np.prod, raw=True) - 1).min())  # noqa: E731
            out[name] = {"scaled_bp": float(sc[m].mean() * 1e4), "unscaled_bp": float(un[m].mean() * 1e4),
                         "sharpe_scaled": sh(sc), "sharpe_unscaled": sh(un), "worst12_scaled": r12(sc), "worst12_unscaled": r12(un),
                         "mean_weight": float(w[m].mean())}
        res[tier] = out
    m = (d.index >= "196307") & (d.index <= "201512") & w.notna()
    x = (w * (gross - 0.002))[m]
    res["t_judged"] = float(x.mean() / (x.std(ddof=1) / math.sqrt(len(x))))
    r1, r2 = res["1x"], res["2x"]
    ok = (r1["h1"]["sharpe_scaled"] > r1["h1"]["sharpe_unscaled"] and r1["h2"]["sharpe_scaled"] > r1["h2"]["sharpe_unscaled"]
          and r1["judged"]["worst12_scaled"] > r1["judged"]["worst12_unscaled"]
          and r2["h1"]["scaled_bp"] > 0 and r2["h2"]["scaled_bp"] > 0 and res["t_judged"] >= 2)
    res["verdict"] = "PASS" if ok else "DEAD"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    run()
