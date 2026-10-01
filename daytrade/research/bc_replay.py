"""Study Lab-BC: Lab-BB1 restricted to |imbalance / paired| >= 1.6742 (the H1 75th percentile), judged on the
H2 holdout only (round1_prose.md Lab Round 27). Uses Lab-BB's signals file (the same entries and exits).

  python -m daytrade.research.bc_replay
"""
from __future__ import annotations

import json
import random

import numpy as np
import pandas as pd

from ..settings import DATA
from . import as_replay as A
from . import az_replay as Z
from .bb_replay import OUT as BB

OUT = DATA / "research" / "bc"
CUT = 1.6742
H2_FROM = "2024-06-01"


def run():
    import pickle
    sig = pd.read_parquet(BB / "signals.parquet")
    sig = sig[sig.dev.abs() >= CUT]
    cal = pickle.loads((Z.OUT / "sessions.pkl").read_bytes())
    n2 = sum(1 for o, _ in cal if Z.SPLIT <= o.date() <= Z.END)
    n1 = sum(1 for o, _ in cal if Z.START <= o.date() < Z.SPLIT)
    res = {}
    for label, rows in (("H2 (holdout, judged)", sig[sig.day >= H2_FROM]), ("H1 (in-sample, reference)", sig[sig.day < H2_FROM])):
        n = n2 if label.startswith("H2") else n1
        t1, t2 = Z.trades(rows, 1, False), Z.trades(rows, 2, False)
        xs = np.sort(t1.net_bp.values)
        rng = random.Random(31)
        means = [np.mean([(g if rng.random() < 0.5 else -g) - c for g, c in zip(t1.gross_bp, t1.cost_bp)])
                 for _ in range(1000)]
        res[label] = {"n": len(t1), "per_day": len(t1) / n, "gross_bp": float(t1.gross_bp.mean()),
                      "1x": A.summary(t1.to_dict("records"), n), "2x": A.summary(t2.to_dict("records"), n),
                      "without_top20": float(xs[:-20].mean()) if len(xs) > 40 else None,
                      "placebo_pct": float(np.mean(np.array(means) < t1.net_bp.mean()) * 100),
                      "by_side_1x": {int(k): float(g.net_bp.mean()) for k, g in t1.groupby("side")},
                      "by_year_1x": {y: float(g.net_bp.mean()) for y, g in t1.groupby(t1.day.str[:4])}}
        if label.startswith("H2"):
            t1.to_csv(OUT / "trades_H2_1x.csv", index=False) if OUT.mkdir(parents=True, exist_ok=True) is None else None
    h = res["H2 (holdout, judged)"]
    res["verdict"] = ("PASS (to paper)" if h["2x"]["mean_bp"] > 0 and h["1x"]["t_day"] >= 2.0
                      and h["placebo_pct"] >= 95 and (h["without_top20"] or -1) > 0 else "DEAD")
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    run()
