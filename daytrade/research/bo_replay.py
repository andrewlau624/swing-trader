"""Studies Lab-BO / BP / BQ: 52w-high, low-vol, 1-month reversal, monthly top 20 of the 500 most traded
(round1_prose.md Lab Round 39). Lab-BJ's monthly bars and frame.

  python -m daytrade.research.bo_replay
"""
from __future__ import annotations

import json
import math
import random

import numpy as np
import pandas as pd

from ..settings import DATA
from .bj_replay import monthly

OUT = DATA / "research" / "bo"
TOP, UNIV = 20, 500
TEST_FROM, SPLIT = "2017-01", "2022-01"


def run():
    adj, raw = monthly("all"), monthly("raw")
    C = adj.pivot_table(index="month", columns="symbol", values="close")
    V = adj.pivot_table(index="month", columns="symbol", values="volume")
    RAW = raw.pivot_table(index="month", columns="symbol", values="close").reindex(index=C.index, columns=C.columns)
    R = C / C.shift(1) - 1
    DV = (C * V).rolling(12, min_periods=10).mean()
    HI = C.rolling(12, min_periods=12).max()
    VOL = R.rolling(12, min_periods=10).std()
    scores = {"Lab-BO": C / HI, "Lab-BP": -VOL, "Lab-BQ": -R}
    res = {}
    for name, S in scores.items():
        rows = []
        for m in [m for m in C.index if m >= TEST_FROM]:
            k = C.index.get_loc(m); prev = C.index[k - 1]
            elig = RAW.loc[prev][RAW.loc[prev] >= 5].index
            univ = list(DV.loc[prev, elig].dropna().sort_values(ascending=False).index[:UNIV])
            sc = S.loc[prev, univ].dropna()
            picks = list(sc.sort_values(ascending=False).index[:TOP])
            ru = R.loc[m, univ]
            rows.append({"month": m, "port": float(ru[picks].fillna(0).mean()), "bench": float(ru.mean(skipna=True)),
                         "univ": ru.fillna(0).values})
        t = pd.DataFrame(rows)
        v = {"months": len(t)}
        for mult, c in (("1x", 10), ("2x", 20)):
            t[f"ex_{mult}"] = (t.port - t.bench) * 1e4 - 2 * c
            v[mult] = {h: float(p[f"ex_{mult}"].mean()) for h, p in (("all", t), ("h1", t[t.month < SPLIT]), ("h2", t[t.month >= SPLIT]))}
        x = t.ex_1x.values
        v["t"] = float(x.mean() / (x.std(ddof=1) / math.sqrt(len(x))))
        v["without_best5"] = float(np.sort(x)[:-5].mean())
        v["by_year_1x"] = {y: float(g.ex_1x.mean()) for y, g in t.groupby(t.month.str[:4])}
        net = t.port - 2 * 10 / 1e4
        v["cagr_port"] = float((1 + net).prod() ** (12 / len(t)) - 1)
        v["cagr_univ"] = float((1 + t.bench).prod() ** (12 / len(t)) - 1)
        sh = lambda s: float(s.mean() / s.std(ddof=1) * math.sqrt(12))  # noqa: E731
        v["sharpe"] = {h: [sh(net[msk]), sh(t.bench[msk])] for h, msk in (("h1", t.month < SPLIT), ("h2", t.month >= SPLIT))}
        rng = random.Random(73)
        means = [np.mean([(np.mean(rng.sample(list(u), TOP)) - b) * 1e4 - 20 for u, b in zip(t.univ, t.bench)]) for _ in range(1000)]
        v["placebo_pct"] = float(np.mean(np.array(means) < x.mean()) * 100)
        a2 = v["2x"]
        ok = a2["h1"] > 0 and a2["h2"] > 0 and v["t"] >= 2 and v["placebo_pct"] >= 95 and v["without_best5"] > 0
        if name == "Lab-BP":
            ok = ok and all(p > b for p, b in v["sharpe"].values())
        v["verdict"] = "PASS (to paper)" if ok else "DEAD"
        res[name] = v
        print(name, v["verdict"], json.dumps({k: v[k] for k in ("1x", "2x", "t", "without_best5", "placebo_pct", "cagr_port", "cagr_univ", "sharpe")}, default=float), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    run()
