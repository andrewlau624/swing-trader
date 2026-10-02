"""Study Lab-AT's registered first look (daytrade/plans/open_imbalance.md; round1_prose.md Round 18): the lab's
OpenImbalance strategy on the recorder's own Schwab L1 sessions. Refuses to run before 40 UNFLAGGED recorded sessions
(a flagged day is excluded, not patched). Run once; the result is final (no re-tuning).

Costs as registered:
- 1x: the recorded spread (buy at the ask / sell at the bid) + 0.5bp per side.
- 2x: twice (half-spread + 0.5bp) per side.
Halves: the first and last 20 sessions. Placebo: random side on the same trades (1,000 draws).

  python -m daytrade.research.at_firstlook [DATA_ROOT]
"""
from __future__ import annotations

import datetime as dt
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

from ..engine import Engine
from ..feeds import day_flagged, read_recorded, rows_to_events
from ..fills import SimBroker
from ..session import calendar, session_times
from ..settings import DATA, Limits
from ..strategies.open_imbalance import OpenImbalance

NEED = 40


class Sim2x(SimBroker):
    def _try(self, o, ev):
        from ..events import Quote
        f = super()._try(o, ev)
        if f is not None and isinstance(ev, Quote) and o.kind == "market":
            half = (ev.ask - ev.bid) / 2
            f.price = f.price + half if o.side == "buy" else f.price - half
        return f


def clean_days(root: Path) -> list[dt.date]:
    meta = sorted((root / "meta").glob("*.json")) if (root / "meta").exists() else []
    out = []
    for p in meta:
        d = dt.date.fromisoformat(p.stem)
        m = json.loads(p.read_text())
        if m.get("complete") and day_flagged(d, root) is False:
            out.append(d)
    return out


def run(root: Path = DATA, need: int = NEED) -> dict:
    days = clean_days(root)
    if len(days) < need:
        return {"status": "waiting", "clean_sessions": len(days), "need": need,
                "message": f"Lab-AT first look needs {need} unflagged recorded sessions; have {len(days)}. Not run."}
    days = days[:need]                     # the registered look uses the FIRST 40 clean sessions, once
    trades = {"1x": [], "2x": []}
    for d in days:
        st = session_times(d, calendar(d, d), Limits())
        rows = read_recorded(d, root)
        for label, broker in (("1x", SimBroker(latency_s=1, cost_bp=1.0, extra_bp=0.5)),
                              ("2x", Sim2x(latency_s=1, cost_bp=2.0, extra_bp=1.0))):
            eng = Engine([OpenImbalance()], broker, equity=1e6, session=st, limits=Limits(max_positions=99, daily_loss_pct=1e9),
                         halt_path=root / "HALT-never")
            eng.run(rows_to_events(rows, st, clock_every_s=1))
            trades[label] += eng.trades
    half = {d: (1 if i < need // 2 else 2) for i, d in enumerate(days)}
    res = {"status": "done", "sessions": [str(d) for d in days]}
    for label, tr in trades.items():
        by = {h: [t["net_bp"] for t in tr if half[dt.date.fromisoformat(t["day"])] == h] for h in (1, 2)}
        res[label] = {"n": len(tr), "mean_bp": float(np.mean([t["net_bp"] for t in tr])) if tr else None,
                      "h1": float(np.mean(by[1])) if by[1] else None, "h2": float(np.mean(by[2])) if by[2] else None}
    x = [t["net_bp"] for t in trades["1x"]]
    if len(x) >= 3:
        m = float(np.mean(x)); cl = defaultdict(float)
        for t in trades["1x"]:
            cl[t["day"]] += t["net_bp"] - m
        res["t_day"] = float(m / (math.sqrt(sum(v * v for v in cl.values())) / len(x)))
        rng = random.Random(83)
        gross = [t["net_bp"] + 2 * 0.5 for t in trades["1x"]]
        means = [np.mean([(g if rng.random() < 0.5 else -g) - 1.0 for g in gross]) for _ in range(1000)]
        res["placebo_pct"] = float(np.mean(np.array(means) < m) * 100)
    a2 = res["2x"]
    res["verdict"] = ("PASS (to paper)" if a2["h1"] is not None and a2["h2"] is not None and a2["h1"] > 0 and a2["h2"] > 0
                      and res.get("t_day", 0) >= 2 and res.get("placebo_pct", 0) >= 95 else "DEAD")
    return res


if __name__ == "__main__":
    print(json.dumps(run(Path(sys.argv[1]) if len(sys.argv) > 1 else DATA), indent=1, default=str))
