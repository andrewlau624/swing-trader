"""Round 24, Study BB: forward test of the 15:40 quote-imbalance tilt on night picks (pre-registered).

    PYTHONPATH=. .venv/bin/python -m research.sim.quote_imbalance_eval [logs/daily-decisions*.jsonl ...]
    (make qi-eval)

QI = (bid_size - ask_size) / (bid_size + ask_size) from the Schwab quote the night leg used at 15:40
(logged since 2026-10-01). Scored on the official crosses (close cross d -> next open cross, Study AW), net
2 x 2.5bp, one row per (date, symbol) across books. BB1 = weight clip(1 + 0.5 QI, 0.5, 1.5), renormalised
within the night. Read once at >= 300 picks with QI; same bars as Study BA.
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .news_judge_eval import COST, MIN_N, crosses, nw_t

ROOT = Path(__file__).resolve().parents[2]


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    files = args or glob.glob(str(ROOT / "logs" / "daily-decisions*.jsonl"))
    rows = [json.loads(x) for f in files for x in Path(f).read_text().splitlines() if x.strip()]
    T = pd.DataFrame(rows)
    if T.empty or "bid_size" not in T:
        print("no decisions with a book snapshot yet"); return 0
    T = T.dropna(subset=["bid_size", "ask_size"]).drop_duplicates(["date", "sym"])
    T = T[(T.bid_size + T.ask_size) > 0]
    T["qi"] = (T.bid_size - T.ask_size) / (T.bid_size + T.ask_size)
    print(f"picks with a 15:40 book snapshot: {len(T)} / {MIN_N} needed")
    if T.empty:
        return 0
    T = T.merge(crosses(T[["date", "sym"]]), on=["date", "sym"], how="left")
    T = T[T.ret.notna() & (T.ret.abs() < 1)]
    T["net"] = T.ret - 2 * COST
    q = T.qi.quantile([1 / 3, 2 / 3]).values
    b = np.digitize(T.qi, q)
    print("  QI terciles (sell-heavy -> buy-heavy): "
          + "  ".join(f"T{k+1} {T.net[b == k].mean()*1e4:+.1f}bp n{(b == k).sum()}" for k in range(3)))
    if len(T) < MIN_N:
        print(f"BB1 not judged yet: {len(T)} of {MIN_N} scored picks."); return 0

    def inc(df):
        w = np.clip(1 + 0.5 * df.qi, 0.5, 1.5)
        w = w / df.assign(w=w).groupby("date").w.transform("mean")
        return df.assign(x=(w - 1) * df.net).groupby("date").x.mean()

    d = inc(T)
    mid = sorted(d.index)[len(d) // 2]
    h = [d[d.index < mid].mean() * 1e4, d[d.index >= mid].mean() * 1e4]
    t = nw_t(d.values)
    rng = np.random.default_rng(24)
    p1 = (np.array([(d.values * rng.choice([-1, 1], len(d))).mean() for _ in range(1000)]) < d.mean()).mean() * 100
    sh = [inc(T.assign(qi=T.groupby("date").qi.transform(lambda v: rng.permutation(v.values)))).mean() for _ in range(1000)]
    p2 = (np.array(sh) < d.mean()).mean() * 100
    ok = h[0] > 0 and h[1] > 0 and t >= 2 and p1 >= 95 and p2 >= 95
    print(f"BB1: increment {d.mean()*1e4:+.2f}bp/night (halves {h[0]:+.2f} / {h[1]:+.2f}), NW t {t:+.2f}, "
          f"sign-flip {p1:.0f}%, shuffle {p2:.0f}% -> {'PASS (SHADOW)' if ok else 'DEAD'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
