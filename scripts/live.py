"""Entrypoint for the autonomous paper loop.

  python scripts/live.py --dry-run     # decide and log, submit nothing
  python scripts/live.py               # live (paper) orders
  python scripts/live.py --status      # show books and recent slippage

Run it twice a day via cron: once after the close (~16:15 ET) and once before
the open (~09:00 ET). Both runs reconcile and re-arm stops; whichever runs
while the market is shut submits the market-on-open orders.
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from swingtrader.config import Config, ROOT
from swingtrader.live.broker import PaperBroker
from swingtrader.live.executor import Executor


def status():
    b = PaperBroker()
    a = b.account()
    print(f"account   equity ${float(a.equity):,.2f}  cash ${float(a.cash):,.2f}")
    pos = b.positions()
    print(f"positions {len(pos)}")
    for s, p in pos.items():
        print(f"   {s:6} {float(p.qty):8.0f} sh @ {float(p.avg_entry_price):8.2f}  "
              f"mkt {float(p.market_value):10.2f}  P&L {float(p.unrealized_pl):+9.2f} "
              f"({float(p.unrealized_plpc)*100:+.1f}%)")
    stops = b.stops_by_symbol()
    unprot = [s for s in pos if s not in stops]
    print(f"stops     {len(stops)} armed" + (f"  UNPROTECTED: {unprot}" if unprot else ""))
    for name in ("reversion", "momentum"):
        p = ROOT / "state" / f"book-{name}.json"
        if p.exists():
            d = json.loads(p.read_text())
            print(f"book {name:10} holding {len(d.get('positions',{})):2}  "
                  f"closed {len(d.get('closed',[])):3}  last run {d.get('last_run','-')}")
    sl = ROOT / "logs" / "slippage.jsonl"
    if sl.exists():
        rows = [json.loads(l) for l in sl.read_text().splitlines() if l.strip()]
        if rows:
            v = np.array([r["slippage_bps"] for r in rows])
            print(f"\nslippage  n={len(v)}  mean {v.mean():+.1f} bps  "
                  f"median {np.median(v):+.1f}  p90 {np.percentile(v,90):+.1f}")
            print(f"          backtest assumed +20.0 bps per side -> "
                  f"{'HOLDING UP' if v.mean() <= 25 else 'WORSE THAN MODELLED'}")
        else:
            print("\nslippage  no fills recorded yet")
    else:
        print("\nslippage  no fills recorded yet")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="decide and log, submit nothing")
    ap.add_argument("--status", action="store_true", help="print books and exit")
    ap.add_argument("--digest", action="store_true", help="force a status email even if quiet")
    a = ap.parse_args(argv)
    if a.status:
        status(); return 0
    return Executor(Config.load(), dry_run=a.dry_run, always_notify=a.digest).run()


if __name__ == "__main__":
    sys.exit(main())
