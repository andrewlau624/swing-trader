"""The strategy interface. A strategy turns market events into orders; it never knows whether it is
in replay, paper or live, never sizes (the risk layer does), and never touches a broker.

Every entry carries a protective `stop` and a `ref_price`; an optional `target` becomes a resting
limit. Exits are orders with entry=False (the engine sends the whole position)."""
from __future__ import annotations

from pathlib import Path


class Strategy:
    name = ""
    plan = ""        # daytrade/plans/<name>.md, written and committed before the first trade

    def plan_path(self) -> Path:
        return Path(__file__).resolve().parent.parent / "plans" / f"{self.name}.md"

    def on_session_start(self, ctx) -> list:
        return []

    def on_bar(self, ctx, bar) -> list:
        return []

    def on_quote(self, ctx, quote) -> list:
        return []

    def on_trade(self, ctx, trade) -> list:
        return []

    def on_fill(self, ctx, fill) -> list:
        return []

    def on_clock(self, ctx) -> list:
        """Called after every event, for rules that fire at a time of day."""
        return []
