"""The risk layer and the account model. Enforced by the engine for every strategy and every mode.

Account model (also used in replay):
- Under $2k, or a cash account: settled cash only. A buy spends settled cash; a sale's proceeds
  settle T+1 (the next session). Buys never use unsettled money, so a good-faith violation
  cannot happen; the cost is that a cash account can turn its money over about once a day.
- Margin, equity >= $2k: Schwab intraday buying power, up to `intraday_mult` x equity (add. 40),
  minus the notional already open.
"""
from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass, field

from .events import Order
from .settings import CASH_ONLY_BELOW, Limits


@dataclass
class AccountModel:
    equity: float
    kind: str = "margin"            # "cash" | "margin"; forced to cash below $2k
    intraday_mult: float = 4.0
    settled: float = field(init=False)
    unsettled: list = field(default_factory=list)   # [(settle_day, amount)]
    open_notional: float = 0.0

    def __post_init__(self):
        if self.equity < CASH_ONLY_BELOW:
            self.kind = "cash"
        self.settled = self.equity

    @property
    def is_cash(self) -> bool:
        return self.kind == "cash"

    def new_day(self, day: dt.date) -> None:
        keep = []
        for d, amt in self.unsettled:
            if d <= day:
                self.settled += amt
            else:
                keep.append((d, amt))
        self.unsettled = keep
        if self.equity < CASH_ONLY_BELOW:
            self.kind = "cash"

    def buying_power(self) -> float:
        if self.is_cash:
            return max(self.settled, 0.0)
        return max(self.equity * self.intraday_mult - self.open_notional, 0.0)

    def on_open(self, notional: float) -> None:
        self.open_notional += notional
        if self.is_cash:
            self.settled -= notional

    def on_close(self, entry_notional: float, exit_notional: float, settle_day: dt.date) -> None:
        self.open_notional = max(self.open_notional - entry_notional, 0.0)
        self.equity += exit_notional - entry_notional
        if self.is_cash:
            self.unsettled.append((settle_day, exit_notional))


class Rejected(Exception):
    """A strategy asked for something a hard limit forbids (logged as a rule event)."""


@dataclass
class RiskLayer:
    limits: Limits
    account: AccountModel
    day_start_equity: float = 0.0
    stopped_for_day: bool = False

    def new_day(self, day: dt.date) -> None:
        self.account.new_day(day)
        self.day_start_equity = self.account.equity
        self.stopped_for_day = False

    def loss_limit_hit(self, unrealized: float) -> bool:
        pnl = self.account.equity + unrealized - self.day_start_equity
        return pnl <= -self.limits.daily_loss_pct * self.day_start_equity

    def size_entry(self, o: Order, now: dt.datetime, session, positions: dict, marks: dict) -> int:
        """Shares for an entry order, or raise Rejected with the rule's name."""
        lim = self.limits
        if self.stopped_for_day:
            raise Rejected("stopped for the day")
        if now >= session.entry_cutoff:
            raise Rejected(f"entry after the cutoff {session.entry_cutoff:%H:%M}")
        if o.stop is None or o.ref_price is None:
            raise Rejected("entry without a stop or a reference price")
        long = o.side == "buy"
        if (long and o.stop >= o.ref_price) or (not long and o.stop <= o.ref_price):
            raise Rejected("stop on the wrong side of the entry")
        if not long and self.account.is_cash:
            raise Rejected("short in a cash account")
        p = positions.get(o.sym)
        if p is not None and p.qty != 0:
            same_side = (p.qty > 0) == long
            if not same_side:
                raise Rejected("entry against an open position")
            mark = marks.get(o.sym, o.ref_price)
            if (mark - p.avg) * (1 if long else -1) <= 0:
                raise Rejected("adding to a losing position / averaging down")
        elif sum(1 for q in positions.values() if q.qty != 0) >= lim.max_positions:
            raise Rejected(f"max {lim.max_positions} positions")
        eq = self.account.equity
        per_share = abs(o.ref_price - o.stop)
        qty = math.floor(lim.risk_per_trade_pct * eq / per_share)
        qty = min(qty, math.floor(lim.max_position_pct * eq / o.ref_price))
        qty = min(qty, math.floor(self.account.buying_power() / o.ref_price))
        if qty < 1:
            raise Rejected("rounds to 0 whole shares (risk, notional or buying power)")
        return qty
