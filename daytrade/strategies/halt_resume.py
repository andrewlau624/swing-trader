"""Buy the reopening auction after a LULD-style halt in a big mover. Plan: daytrade/plans/halt_resume.md
(Study Lab-AY). The halt is inferred from silence: no bar for 5+ minutes while the clock moves on."""
from __future__ import annotations

import datetime as dt

from ..events import Order
from .base import Strategy

GAP = dt.timedelta(minutes=5)
MOVE = 0.05
ACTIVE_MIN = 8                 # bars in the 10 minutes before the gap
FROM, UNTIL = "09:45", "15:00"
HOLD = dt.timedelta(minutes=30)
STOP_PCT = 0.10


class HaltResume(Strategy):
    name = "halt_resume"

    def __init__(self, direction: str = "up"):
        self.direction = direction            # "up": buy after a halt up; "down": after a halt down

    def on_session_start(self, ctx) -> list:
        self.bars: dict[str, list] = {}
        self.done: set[str] = set()
        self.filled_at: dict[str, dt.datetime] = {}
        self.exited: set[str] = set()
        return []

    def on_bar(self, ctx, bar) -> list:
        if bar.start >= ctx.session.open:
            self.bars.setdefault(bar.sym, []).append(bar)
        return []

    def on_fill(self, ctx, fill) -> list:
        if fill.side == "buy":
            self.filled_at.setdefault(fill.sym, fill.ts)
        return []

    def on_clock(self, ctx) -> list:
        out = []
        now = ctx.now
        if ctx.session.at(FROM) <= now <= ctx.session.at(UNTIL):
            for s, bs in self.bars.items():
                if s in self.done or len(bs) < 6 or now - bs[-1].ts < GAP:
                    continue
                last = bs[-1]
                recent = [b for b in bs if b.ts > last.ts - dt.timedelta(minutes=10)]
                move = last.close / bs[-6].close - 1
                hit = move >= MOVE if self.direction == "up" else move <= -MOVE
                if hit and len(recent) >= ACTIVE_MIN:
                    self.done.add(s)
                    out.append(Order(s, "buy", ref_price=last.close, stop=round(last.close * (1 - STOP_PCT), 2),
                                     stop_pct=STOP_PCT, reason=f"halt {self.direction} ({move:+.1%} in 5 min)"))
        for s, t0 in self.filled_at.items():
            if s not in self.exited and now >= t0 + HOLD and ctx.position(s) > 0:
                self.exited.add(s)
                out.append(Order(s, "sell", entry=False, reason="30-minute exit"))
        return out
