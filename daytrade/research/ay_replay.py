"""Study Lab-AY: buy LULD-halt reopenings (daytrade/plans/halt_resume.md, round1_prose.md Lab Round 23). The lab's
HaltResume code through the engine on Lab-AX's SIP minute data (regular session, calendar), plus a Clock event
each minute so a halt is seen while the symbol is silent.

  python -m daytrade.research.ay_replay
"""
from __future__ import annotations

import datetime as dt
import json
import random

import numpy as np
import pandas as pd

from ..engine import Engine
from ..events import Bar, Clock
from ..fills import SimBroker
from ..risk import AccountModel
from ..session import session_times
from ..settings import DATA, Limits
from ..strategies.halt_resume import HaltResume
from . import as_replay as A
from . import ax_replay as X

OUT = DATA / "research" / "ay"


def events(rec, st):
    ev = A.day_events(rec)
    clocks = [Clock(st.open + dt.timedelta(minutes=m)) for m in range(int((st.close - st.open).total_seconds() // 60) + 1)]
    return sorted(ev + clocks, key=lambda e: (e.ts, 0 if isinstance(e, Bar) else 1))


def replay(direction, cost_bp, equity=1e6, limits=None, kind="margin"):
    stats = limits is None
    lim = limits or Limits(max_positions=99, daily_loss_pct=1e9)
    acct = AccountModel(equity, kind, lim.intraday_mult)
    trades, keep = [], {}
    days = list(X.load_days())
    for i, (day, rec, cal) in enumerate(days):
        if stats:
            acct = AccountModel(equity, kind, lim.intraday_mult)
        st = session_times(day, cal, lim)
        ev = events(rec, st)
        nxt = days[i + 1][0] if i + 1 < len(days) else day + dt.timedelta(days=1)
        eng = Engine([HaltResume(direction)], SimBroker(latency_s=1.0, cost_bp=cost_bp), equity=acct.equity,
                     session=st, day_info=rec["info"], limits=lim, account=acct, settle_day=nxt,
                     halt_path=OUT / "HALT-never")
        eng.run(ev)
        trades += eng.trades
        if stats and eng.trades:
            keep[day] = ([e for e in ev if isinstance(e, Bar)], st)
    return trades, keep, len(days)


def placebo(trades, keep, cost_bp, draws=1000, seed=17):
    rng = random.Random(seed)
    opts = []
    for t in trades:
        bars_all, st = keep[dt.date.fromisoformat(t["day"])]
        bars = [b for b in bars_all if b.sym == t["sym"]]
        idx = [i for i, b in enumerate(bars) if st.at("09:45") <= b.start <= st.at("15:00")]
        opts.append([X.window(bars, i, 30, cost_bp / 1e4) for i in idx] or [0.0])
    actual = np.mean([t["net_bp"] for t in trades])
    means = [np.mean([rng.choice(o) for o in opts]) for _ in range(draws)]
    return float(np.mean(np.array(means) < actual) * 100), float(np.mean(means))


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    n1 = sum(1 for d, _, _ in X.load_days() if d < A.SPLIT)
    for name, direction in (("Lab-AY1", "up"), ("Lab-AY2", "down")):
        base, keep, n = replay(direction, 20.0)
        two, _, _ = replay(direction, 40.0)
        r = {k: {h: A.summary(x, m) for h, x, m in (("all", tr, n), ("h1", A.half(tr, 1), n1), ("h2", A.half(tr, 2), n - n1))}
             for k, tr in (("1x", base), ("2x", two))}
        r["gross_bp"] = float(np.mean([t["net_bp"] for t in base]) + 40) if base else None
        r["placebo_pct"], r["placebo_mean_bp"] = placebo(base, keep, 20.0) if base else (float("nan"),) * 2
        a2 = r["2x"]
        r["verdict"] = ("PASS (to paper)" if base and a2["h1"]["mean_bp"] > 0 and a2["h2"]["mean_bp"] > 0
                        and r["1x"]["all"]["t_day"] >= 2.0 and r["placebo_pct"] >= 95 else "DEAD")
        dol = {}
        for label, eq, kind in (("$2.3k cash", 2_300, "cash"), ("$10k margin", 10_000, "margin"),
                                ("$25k margin", 25_000, "margin")):
            tr, _, m = replay(direction, 20.0, equity=eq, limits=Limits(), kind=kind)
            pnl = sum(t["pnl"] for t in tr)
            dol[label] = {"trades": len(tr), "per_day": pnl / m, "end": eq + pnl}
        r["dollars_1x"] = dol
        res[name] = r
        pd.DataFrame(base).to_csv(OUT / f"trades_{name}_1x.csv", index=False)
        print(name, r["verdict"], json.dumps({"n": r["1x"]["all"]["n"], "net": r["1x"]["all"]["mean_bp"],
                                              "gross": r["gross_bp"], "placebo": r["placebo_pct"]}), flush=True)
    res["n_days"], res["n_h1"] = n, n1
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    run()
