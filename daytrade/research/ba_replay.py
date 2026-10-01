"""Study Lab-BA: short the reopening after a halt (daytrade/plans/halt_short.md, round1_prose.md Lab Round 25).
The same data and engine path as Lab-AY (ay_replay), with HaltResume(side="sell").

  python -m daytrade.research.ba_replay
"""
from __future__ import annotations

import datetime as dt
import json
import random

import numpy as np
import pandas as pd

from ..engine import Engine
from ..events import Bar
from ..fills import SimBroker
from ..risk import AccountModel
from ..session import session_times
from ..settings import DATA, Limits
from ..strategies.halt_resume import HaltResume
from . import as_replay as A
from . import ax_replay as X
from .ay_replay import events

OUT = DATA / "research" / "ba"


def etb_symbols() -> set[str]:
    p = OUT / "etb.json"
    if p.exists():
        return set(json.loads(p.read_text()))
    from alpaca.trading.enums import AssetClass, AssetStatus
    from alpaca.trading.requests import GetAssetsRequest
    _, tc = A._clients()
    ok = {a.symbol for a in tc.get_all_assets(GetAssetsRequest(asset_class=AssetClass.US_EQUITY, status=AssetStatus.ACTIVE))
          if getattr(a, "easy_to_borrow", False) and getattr(a, "shortable", False)}
    OUT.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(sorted(ok)))
    return ok


def replay(make, cost_bp, keep_syms=None, equity=1e6, limits=None, kind="margin"):
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
        if keep_syms is not None:
            ev = [e for e in ev if not isinstance(e, Bar) or e.sym in keep_syms]
        nxt = days[i + 1][0] if i + 1 < len(days) else day + dt.timedelta(days=1)
        eng = Engine([make()], SimBroker(latency_s=1.0, cost_bp=cost_bp), equity=acct.equity, session=st,
                     day_info=rec["info"], limits=lim, account=acct, settle_day=nxt, halt_path=OUT / "HALT-never")
        eng.run(ev)
        trades += eng.trades
        if stats and eng.trades:
            keep[day] = ([e for e in ev if isinstance(e, Bar)], st)
    return trades, keep, len(days)


def short_window(bars, i0, n, cost, stop_pct=0.10):
    """Short at bar i0's open, cover n minutes later (bar open) or at a stop 10% above the fill."""
    entry = bars[i0].open * (1 - cost)
    stop = round(bars[i0].open * (1 + stop_pct), 2)
    end = min(i0 + n, len(bars) - 1)
    for b in bars[i0:end]:
        if b.high >= stop:
            px = b.open if (b.open >= stop and b is not bars[i0]) else stop
            return -(px * (1 + cost) / entry - 1) * 1e4
    return -(bars[end].open * (1 + cost) / entry - 1) * 1e4


def placebo(trades, keep, cost_bp, draws=1000, seed=19):
    rng = random.Random(seed)
    opts = []
    for t in trades:
        bars_all, st = keep[dt.date.fromisoformat(t["day"])]
        bars = [b for b in bars_all if b.sym == t["sym"]]
        idx = [i for i, b in enumerate(bars) if st.at("09:45") <= b.start <= st.at("15:00")]
        opts.append([short_window(bars, i, 30, cost_bp / 1e4) for i in idx] or [0.0])
    actual = np.mean([t["net_bp"] for t in trades])
    means = [np.mean([rng.choice(o) for o in opts]) for _ in range(draws)]
    return float(np.mean(np.array(means) < actual) * 100), float(np.mean(means))


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    etb = etb_symbols()
    res = {}
    n1 = sum(1 for d, _, _ in X.load_days() if d < A.SPLIT)
    variants = (("Lab-BA1", lambda: HaltResume("up", side="sell"), None),
                ("Lab-BA2", lambda: HaltResume("up", side="sell"), etb),
                ("Lab-BA3", lambda: HaltResume("down", side="sell", no_ssr=True), None))
    for name, make, syms in variants:
        base, keep, n = replay(make, 20.0, syms)
        two, _, _ = replay(make, 40.0, syms)
        r = {k: {h: A.summary(x, m) for h, x, m in (("all", tr, n), ("h1", A.half(tr, 1), n1), ("h2", A.half(tr, 2), n - n1))}
             for k, tr in (("1x", base), ("2x", two))}
        xs = np.sort([t["net_bp"] for t in base]) if base else np.array([])
        r["gross_bp"] = float(xs.mean() + 40) if len(xs) else None
        r["mean_without_top20"] = float(xs[:-20].mean()) if len(xs) > 40 else None
        r["winsor_1_99"] = float(np.clip(xs, *np.percentile(xs, [1, 99])).mean()) if len(xs) else None
        r["placebo_pct"], r["placebo_mean_bp"] = placebo(base, keep, 20.0) if base else (float("nan"),) * 2
        a2 = r["2x"]
        r["verdict"] = ("PASS (to paper)" if base and a2["h1"]["mean_bp"] > 0 and a2["h2"]["mean_bp"] > 0
                        and r["1x"]["all"]["t_day"] >= 2.0 and r["placebo_pct"] >= 95
                        and (r["mean_without_top20"] or -1) > 0 else "DEAD")
        dol = {}
        for label, eq in (("$10k margin", 10_000), ("$25k margin", 25_000)):
            tr, _, m = replay(make, 20.0, syms, equity=eq, limits=Limits())
            pnl = sum(t["pnl"] for t in tr)
            dol[label] = {"trades": len(tr), "per_day": pnl / m, "end": eq + pnl}
        r["dollars_1x"] = dol
        r["dollars_note"] = "shorts need margin: a cash account (any account under $2k) cannot trade this"
        res[name] = r
        pd.DataFrame(base).to_csv(OUT / f"trades_{name}_1x.csv", index=False)
        print(name, r["verdict"], json.dumps({"n": r["1x"]["all"]["n"], "net": r["1x"]["all"]["mean_bp"],
                                              "gross": r["gross_bp"], "no_top20": r["mean_without_top20"],
                                              "placebo": r["placebo_pct"]}), flush=True)
    res["n_days"], res["n_h1"], res["etb_names_today"] = n, n1, len(etb)
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    run()
