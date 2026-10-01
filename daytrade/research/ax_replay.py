"""Study Lab-AX: late-day continuation of +25% movers (daytrade/plans/late_mover.md, round1_prose.md Lab Round 22).

Reads: SIP daily bars (raw, cached by Study Lab-AU) only as a PREFILTER. The previous REGULAR close comes from
completed sessions before the trade date. Today's daily HIGH >= 1.25 x prev close is a necessary
condition for being +25% at 15:00, and losers use LOW <= 0.75 x prev close for the diagnostic. Every
decision and fill uses SIP minute bars inside the calendar's regular session.

  python -m daytrade.research.ax_replay fetch
  python -m daytrade.research.ax_replay run
"""
from __future__ import annotations

import datetime as dt
import json
import pickle
import random
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

from ..engine import Engine
from ..events import DayInfo
from ..fills import SimBroker
from ..risk import AccountModel
from ..session import session_times
from ..settings import DATA, Limits
from ..strategies import late_mover as L
from . import as_replay as A
from . import au_replay as U

OUT = DATA / "research" / "ax"
START, END, SPLIT = A.START, A.END, A.SPLIT
log = A.log


def candidates():
    d = pd.read_parquet(U.OUT / "daily_ohlc.parquet")
    keep = set(A.universe())
    d = d[d.symbol.isin(keep)]
    out = defaultdict(dict)
    for sym, g in d.groupby("symbol", sort=False):
        g = g.reset_index(drop=True)
        pc = g["close"].shift(1)
        m = (pc >= L.PRICE_MIN) & ((g["high"] >= 1.25 * pc) | (g["low"] <= 0.75 * pc))
        m &= (g["date"] >= pd.Timestamp(START)) & (g["date"] <= pd.Timestamp(END))
        for i in np.flatnonzero(m.values):
            out[g["date"].iat[i].date()][sym] = float(pc.iat[i])
    return out


def fetch() -> None:
    cand = candidates()
    log(f"candidate stock-days {sum(map(len, cand.values()))} on {len(cand)} days")
    from swingtrader.daily.brokers import regular_sessions
    cal = regular_sessions(START, END + dt.timedelta(days=7))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sessions.pkl").write_bytes(pickle.dumps(cal))
    (OUT / "days").mkdir(exist_ok=True)
    data, _ = A._clients()
    for o, c in cal:
        day = o.date()
        f = OUT / "days" / f"{day}.pkl"
        if day > END or f.exists():
            continue
        names = sorted(cand.get(day, {}))
        bars = A._minutes(data, names, o, c) if names else pd.DataFrame()
        f.write_bytes(pickle.dumps({"info": {s: DayInfo(s, cand[day][s]) for s in names}, "bars": bars,
                                    "open": o, "close": c}))
        if names:
            log(f"{day}: {len(names)} candidates")


def load_days():
    cal = pickle.loads((OUT / "sessions.pkl").read_bytes())
    for o, c in cal:
        f = OUT / "days" / f"{o.date()}.pkl"
        if START <= o.date() <= END and f.exists():
            yield o.date(), pickle.loads(f.read_bytes()), cal


def replay(cost_bp, latency=1.0, equity=1e6, limits=None, kind="margin"):
    stats = limits is None
    lim = limits or Limits(max_positions=99, daily_loss_pct=1e9)
    acct = AccountModel(equity, kind, lim.intraday_mult)
    trades, keep = [], {}
    days = list(load_days())
    for i, (day, rec, cal) in enumerate(days):
        if stats:
            acct = AccountModel(equity, "margin", lim.intraday_mult)
        st = session_times(day, cal, lim)
        evs = A.day_events(rec)
        nxt = days[i + 1][0] if i + 1 < len(days) else day + dt.timedelta(days=1)
        eng = Engine([L.LateMover()], SimBroker(latency_s=latency, cost_bp=cost_bp), equity=acct.equity,
                     session=st, day_info=rec["info"], limits=lim, account=acct, settle_day=nxt,
                     halt_path=OUT / "HALT-never")
        eng.run(evs)
        trades += eng.trades
        if stats and eng.trades:
            keep[day] = (evs, st)
    return trades, keep, len(days)


def window(bars, i0, n, cost, stop_pct=L.STOP_PCT):
    """Buy at bar i0's open, hold n minutes (or the stop), the SimBroker's rules."""
    entry = bars[i0].open * (1 + cost)
    stop = round(bars[i0].open * (1 - stop_pct), 2)
    end = min(i0 + n, len(bars) - 1)
    for b in bars[i0:end]:
        if b.low <= stop:
            px = b.open if (b.open <= stop and b is not bars[i0]) else stop
            return (px * (1 - cost) / entry - 1) * 1e4
    return (bars[end].open * (1 - cost) / entry - 1) * 1e4


def placebo(trades, keep, cost_bp, draws=1000, seed=13):
    rng = random.Random(seed)
    cost = cost_bp / 1e4
    opts = []
    for t in trades:
        evs, st = keep[dt.date.fromisoformat(t["day"])]
        bars = [b for b in evs if b.sym == t["sym"]]
        idx = [i for i, b in enumerate(bars) if st.at("11:00") <= b.start <= st.at("14:30")]
        opts.append([window(bars, i, 55, cost) for i in idx] or [0.0])
    actual = np.mean([t["net_bp"] for t in trades])
    means = [np.mean([rng.choice(o) for o in opts]) for _ in range(draws)]
    return float(np.mean(np.array(means) < actual) * 100), float(np.mean(means))


def losers_diag():
    """RESULTS.md's mirror: <= -25% at 15:00, gross 15:00 open -> 15:55 open (no costs)."""
    out = []
    for day, rec, cal in load_days():
        st = session_times(day, cal)
        by = defaultdict(list)
        for b in A.day_events(rec):
            by[b.sym].append(b)
        for s, bs in by.items():
            i = next((k for k, b in enumerate(bs) if b.ts == st.at("15:00")), None)
            j = next((k for k, b in enumerate(bs) if b.start >= st.at("15:55")), None)
            if i is None or j is None or i + 1 >= len(bs):
                continue
            if bs[i].close / rec["info"][s].prev_close - 1 <= -0.25:
                out.append((bs[j].open / bs[i + 1].open - 1) * 1e4)
    return {"n": len(out), "gross_bp": float(np.mean(out)) if out else None}


def run() -> None:
    base, keep, n = replay(20.0)
    two, _, _ = replay(40.0)
    late, _, _ = replay(20.0, latency=60.0)
    n1 = sum(1 for d, _, _ in load_days() if d < SPLIT)
    res = {k: {h: A.summary(x, m) for h, x, m in (("all", tr, n), ("h1", A.half(tr, 1), n1), ("h2", A.half(tr, 2), n - n1))}
           for k, tr in (("1x", base), ("2x", two), ("1x_60s", late))}
    res["gross_bp"] = float(np.mean([t["net_bp"] for t in base]) + 40) if base else None
    res["placebo_pct"], res["placebo_mean_bp"] = placebo(base, keep, 20.0) if base else (float("nan"),) * 2
    res["losers_diag"] = losers_diag()
    a2 = res["2x"]
    res["verdict"] = ("PASS (to paper)" if a2["h1"]["mean_bp"] > 0 and a2["h2"]["mean_bp"] > 0
                      and res["1x"]["all"]["t_day"] >= 2.0 and res["placebo_pct"] >= 95 else "DEAD")
    dol = {}
    for label, eq, kind in (("$2.3k cash", 2_300, "cash"), ("$10k margin", 10_000, "margin"),
                            ("$25k margin", 25_000, "margin")):
        tr, _, m = replay(20.0, equity=eq, limits=Limits(), kind=kind)
        pnl = sum(t["pnl"] for t in tr)
        dol[label] = {"trades": len(tr), "per_day": pnl / m, "end": eq + pnl}
    res["dollars_1x"] = dol
    res["n_days"], res["n_h1"] = n, n1
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))
    pd.DataFrame(base).to_csv(OUT / "trades_1x.csv", index=False)
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    {"fetch": fetch, "run": run}[sys.argv[1]]()
