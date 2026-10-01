"""Study Lab-AW: VWAP trend on QQQ / TQQQ (daytrade/plans/vwap_trend.md, round1_prose.md Lab Round 21). The lab's
VwapTrend code through the lab's engine on SIP minute bars, regular session only (calendar), 2022-26.

  python -m daytrade.research.aw_replay run      # fetches (cached) then runs
"""
from __future__ import annotations

import datetime as dt
import json
import random
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from ..engine import Engine
from ..events import Bar
from ..fills import SimBroker
from ..session import session_times
from ..settings import DATA, Limits
from ..strategies.vwap_trend import VwapTrend
from . import as_replay as A

OUT = DATA / "research" / "aw"
START, END, SPLIT = A.START, A.END, A.SPLIT
COSTS = {"QQQ": (0.5, 1.0), "TQQQ": (1.5, 3.0)}
log = A.log


def bars() -> pd.DataFrame:
    p = OUT / "bars.parquet"
    if p.exists():
        return pd.read_parquet(p)
    data, _ = A._clients()
    parts = []
    m = pd.Timestamp(START).replace(day=1)
    while m <= pd.Timestamp(END):
        nxt = m + pd.offsets.MonthBegin(1)
        parts.append(A._minutes(data, ["QQQ", "TQQQ"], m.tz_localize(A.ET).to_pydatetime(),
                                nxt.tz_localize(A.ET).to_pydatetime()))
        log(f"bars {m:%Y-%m}")
        m = nxt
    df = pd.concat(parts)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_parquet(p)
    return df


def day_events(g, o, c):
    tz = ZoneInfo(A.ET)
    ev = []
    for r in g.itertuples(index=False):
        s = r.timestamp.tz_convert(tz).to_pydatetime()
        if o <= s < c:
            ev.append(Bar(s + dt.timedelta(minutes=1), r.symbol, float(r.open), float(r.high), float(r.low),
                          float(r.close), float(r.volume), s))
    ev.sort(key=lambda x: (x.ts, x.sym))
    return ev


def run_variant(trade: str, cost_bp: float, days, equity=1e6, limits=None, stats=True):
    lim = limits or Limits(max_positions=99, daily_loss_pct=1e9)
    from ..risk import AccountModel
    acct = AccountModel(equity, "margin", lim.intraday_mult)
    out = []
    for i, (day, st, ev) in enumerate(days):
        if stats:
            acct = AccountModel(equity, "margin", lim.intraday_mult)
        nxt = days[i + 1][0] if i + 1 < len(days) else day + dt.timedelta(days=1)
        eng = Engine([VwapTrend(trade=trade)], SimBroker(latency_s=1.0, cost_bp=cost_bp), equity=acct.equity,
                     session=st, limits=lim, account=acct, settle_day=nxt, halt_path=OUT / "HALT-never")
        eng.run(ev)
        out.append((day, eng.trades))
    return out


def day_rows(res):
    return [{"day": str(d), "net_bp": float(sum(t["net_bp"] for t in tr)), "n": len(tr)} for d, tr in res]


def placebo(res, cost_bp, draws=1000, seed=3):
    rng = random.Random(seed)
    segs = [[(t["net_bp"] + 2 * cost_bp) for t in tr] for _, tr in res]   # gross per segment
    actual = np.mean([sum(t["net_bp"] for t in tr) for _, tr in res])
    means = [np.mean([sum((g if rng.random() < 0.5 else -g) - 2 * cost_bp for g in s) for s in segs])
             for _ in range(draws)]
    return float(np.mean(np.array(means) < actual) * 100), float(np.mean(means))


def run() -> None:
    df = bars()
    from swingtrader.daily.brokers import regular_sessions
    cal = regular_sessions(START, END + dt.timedelta(days=7))
    df["d"] = df["timestamp"].dt.tz_convert(A.ET).dt.date
    groups = dict(tuple(df.groupby("d")))
    days = []
    for o, c in cal:
        if o.date() > END or o.date() not in groups:
            continue
        days.append((o.date(), session_times(o.date(), cal, Limits()), day_events(groups[o.date()], o, c)))
    n1 = sum(1 for d, _, _ in days if d < SPLIT)
    out = {"n_days": len(days), "n_h1": n1}
    for name, trade in (("Lab-AW1", "QQQ"), ("Lab-AW2", "TQQQ")):
        c1, c2 = COSTS[trade]
        r1, r2 = run_variant(trade, c1, days), run_variant(trade, c2, days)
        d1, d2 = day_rows(r1), day_rows(r2)
        v = {"1x": {h: A.summary(x, len(x)) for h, x in (("all", d1), ("h1", A.half(d1, 1)), ("h2", A.half(d1, 2)))},
             "2x": {h: A.summary(x, len(x)) for h, x in (("all", d2), ("h1", A.half(d2, 1)), ("h2", A.half(d2, 2)))},
             "switches_per_day": float(np.mean([r["n"] for r in d1])),
             "gross_bp_day": float(np.mean([r["net_bp"] + 2 * c1 * r["n"] for r in d1]))}
        v["placebo_pct"], v["placebo_mean_bp"] = placebo(r1, c1)
        a2 = v["2x"]
        v["verdict"] = ("PASS (to paper)" if a2["h1"]["mean_bp"] > 0 and a2["h2"]["mean_bp"] > 0
                        and v["1x"]["all"]["t_day"] >= 2.0 and v["placebo_pct"] >= 95 else "DEAD")
        # $/day: the whole equity in the position (risk 2% of equity on the 2% stop = 1x notional)
        dol = {}
        for label, eq in (("$2.3k", 2_300), ("$10k", 10_000), ("$25k", 25_000)):
            rr = run_variant(trade, c1, days, equity=eq, stats=False,
                             limits=Limits(risk_per_trade_pct=0.02, daily_loss_pct=0.02))
            pnl = sum(t["pnl"] for _, tr in rr for t in tr)
            dol[label] = {"per_day": pnl / len(days), "end": eq + pnl,
                          "cagr": ((eq + pnl) / eq) ** (252 / len(days)) - 1 if eq + pnl > 0 else -1}
        v["dollars_1x_full_notional"] = dol
        out[name] = v
        pd.DataFrame(d1).to_csv(OUT / f"days_{name}_1x.csv", index=False)
        print(name, v["verdict"], json.dumps({k: v[k] for k in ("switches_per_day", "gross_bp_day", "placebo_pct")}),
              flush=True)
    (OUT / "results.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    run()
