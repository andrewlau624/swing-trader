"""Late-day continuation of +25% movers, long only. Plan: daytrade/plans/late_mover.md (Study Lab-AX).
The 15:55 exit is the engine's flat-by-close."""
from __future__ import annotations

from ..events import Order
from .base import Strategy

UP_MIN = 0.25
DOLLAR_VOL_MIN = 10e6
PRICE_MIN = 5.0
DECIDE_AT = "15:00"         # the 14:59 bar's close
STOP_PCT = 0.10


class LateMover(Strategy):
    name = "late_mover"

    def on_session_start(self, ctx) -> list:
        self.dvol: dict[str, float] = {}
        self.done: set[str] = set()
        return []

    def on_bar(self, ctx, bar) -> list:
        if bar.start < ctx.session.open:
            return []
        s = bar.sym
        if bar.ts <= ctx.session.at(DECIDE_AT):
            self.dvol[s] = self.dvol.get(s, 0.0) + (bar.high + bar.low + bar.close) / 3 * bar.volume
        if s in self.done or bar.ts < ctx.session.at(DECIDE_AT):
            return []
        self.done.add(s)                     # one decision per name: its first bar ending at/after 15:00
        d = ctx.day_info(s)
        if bar.ts != ctx.session.at(DECIDE_AT) or d is None or d.prev_close < PRICE_MIN:
            return []
        if bar.close / d.prev_close - 1 >= UP_MIN and self.dvol.get(s, 0.0) >= DOLLAR_VOL_MIN:
            return [Order(s, "buy", ref_price=bar.close, stop=round(bar.close * (1 - STOP_PCT), 2), stop_pct=STOP_PCT,
                          reason=f"up {bar.close / d.prev_close - 1:+.0%} at 15:00")]
        return []
