#!/usr/bin/env python3
"""Day-trading lab CLI. Separate from scripts/daily.py: its own account, state and logs.

  record [--smoke SECONDS]        run the market-data recorder for today (the systemd unit runs this)
  replay --day YYYY-MM-DD [...]   replay a recorded day through the engine
  run --mode paper|live           the live loop (paper needs the lab's own Alpaca paper keys)
  halt | unhalt                   create / remove state/daytrade/HALT
  review [--days 7]               weekly review per strategy (writes daytrade/reviews/)
  table                           the $/day table
  momentum [--industry]           monthly momentum PAPER SHADOW: stocks (Lab-BR/BT) or industry ETFs (Lab-BW/BX); no orders
  status                          recordings, HALT, journal counts
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record"); r.add_argument("--smoke", type=int, default=0)
    r.add_argument("--root", default=None)
    rp = sub.add_parser("replay"); rp.add_argument("--day", required=True)
    rp.add_argument("--strategy", default="all"); rp.add_argument("--equity", type=float, default=2300.0)
    rp.add_argument("--latency", type=float, default=1.0)
    rn = sub.add_parser("run"); rn.add_argument("--mode", choices=("paper", "live"), required=True)
    rn.add_argument("--strategy", default="all")
    sub.add_parser("halt"); sub.add_parser("unhalt")
    rv = sub.add_parser("review"); rv.add_argument("--days", type=int, default=7)
    sub.add_parser("table"); sub.add_parser("status")
    mo = sub.add_parser("momentum"); mo.add_argument("--industry", action="store_true")
    a = ap.parse_args()

    if a.cmd == "record":
        from daytrade.recorder import run
        from daytrade.settings import DATA
        return run(smoke_s=a.smoke, root=Path(a.root) if a.root else DATA)
    if a.cmd == "replay":
        from daytrade.runner import replay_recorded
        return replay_recorded(dt.date.fromisoformat(a.day), a.strategy, a.equity, a.latency)
    if a.cmd == "run":
        from daytrade.runner import run_live
        return run_live(a.mode, a.strategy)
    if a.cmd in ("halt", "unhalt"):
        from daytrade.settings import HALT
        HALT.parent.mkdir(parents=True, exist_ok=True)
        if a.cmd == "halt":
            HALT.write_text(f"halted {dt.datetime.now().isoformat()}\n")
            print(f"HALT set ({HALT}): the engine cancels all orders, flattens and stops on its next loop")
        else:
            HALT.unlink(missing_ok=True)
            print("HALT removed")
        return 0
    if a.cmd == "review":
        from daytrade.review import main as review
        return review(a.days)
    if a.cmd == "table":
        from daytrade.table import markdown
        print(markdown())
        return 0
    if a.cmd == "momentum":
        from daytrade.momentum import run as momentum, run_industry
        return run_industry() if a.industry else momentum()
    if a.cmd == "status":
        from daytrade.runner import status
        return status()
    return 1


if __name__ == "__main__":
    sys.exit(main())
