"""Entrypoint for the daily-cadence book (RESULTS.md addendum 6).

  python scripts/daily.py                 # run the phase for the current ET time
  python scripts/daily.py --dry-run       # decide and log, submit nothing, save nothing
  python scripts/daily.py --phase close   # force a phase (open|reconcile|intraday|close)
  python scripts/daily.py --status        # book equity, positions, legs, history
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from swingtrader.config import Config, ROOT
from swingtrader.daily.book import DailyBook


def status():
    cfg = Config.load()
    b = DailyBook.load(ROOT / "state", cfg.daily.start_equity)
    eq = b.equity_log[-1]["equity"] if b.equity_log else b.cash
    print(f"daily book  equity ${eq:,.2f}  start ${b.start_equity:,.0f}  "
          f"({(eq/b.start_equity-1)*100:+.1f}%)  cash ${b.cash:,.2f}  last run {b.last_run or '-'}")
    print(f"day-trade leg {'LIVE' if b.daytrade_live else 'shadow'} "
          f"(switches on at ${cfg.daily.daytrade_min_equity:,.0f})")
    for s, p in sorted(b.positions.items()):
        print(f"   {p['leg']:6} {s:6} {float(p['qty']):10.4f} @ {float(p['avg_px']):9.2f}  since {p['entry_date']}")
    op = b.open_orders()
    if op:
        print(f"open orders {len(op)}")
        for k, o in op.items():
            print(f"   {o['leg']:6} {o['side']:4} {o['sym']:6} {o.get('tif','')}  {k}")
    for leg in ("ibs", "night", "noise"):
        r = [c["ret"] for c in b.closed if c["leg"] == leg]
        pnl = sum(c["pnl"] for c in b.closed if c["leg"] == leg)
        if r:
            print(f"{leg:6} trades {len(r):4}  win {100*np.mean(np.array(r)>0):4.0f}%  "
                  f"avg {np.mean(r)*100:+.2f}%  P&L ${pnl:+,.2f}")
    n = b.noise
    if n.get("history"):
        h = [x["ret"] for x in n["history"]]
        print(f"noise (shadow) days {len(h)}  equity ${n.get('shadow_equity', 0):,.2f}  "
              f"avg/day {np.mean(h)*100:+.3f}%  up-days {100*np.mean(np.array(h)>0):.0f}%")
    f = ROOT / "logs" / "daily-fills.jsonl"
    if f.exists():
        rows = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
        for leg in ("ibs", "night"):
            v = [r["slippage_bps"] for r in rows if r["leg"] == leg]
            if v:
                print(f"slippage {leg:6} n={len(v)} mean {np.mean(v):+.1f} bps (vs ref price at decision)")
    if len(b.equity_log) > 1:
        print("equity by day: " + "  ".join(f"{e['date'][5:]} {e['equity']:,.0f}" for e in b.equity_log[-10:]))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--phase", choices=["open", "reconcile", "intraday", "close"])
    a = ap.parse_args(argv)
    if a.status:
        status(); return 0
    from swingtrader.daily.executor import DailyExecutor
    return DailyExecutor(Config.load(), dry_run=a.dry_run).run(phase=a.phase)


if __name__ == "__main__":
    sys.exit(main())
