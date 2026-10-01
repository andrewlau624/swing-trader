"""The replay fill model (also the shadow fill for every paper/live order: the drift report).

- Market orders wait `latency_s`. On quotes they fill at the ask (buy) / bid (sell), worse by
  `extra_bp`. On minute bars (no quotes) they fill at the open of the first bar starting at or
  after submit + latency - 1s (1s = the next minute's open, 60s = the one after) worse by `cost_bp`;
  latency 0 fills at the decision price worse by `cost_bp`.
- Limit orders are passive (no cost). On bars they fill only if the price trades THROUGH the limit
  by a tick. On trades they fill on a print through the limit, or at the limit once the size
  queued ahead (the displayed size at the limit when placed) has traded.
- Stop orders trigger on the bar's low/high (or the bid/ask) and fill at the stop, or at the bar's
  open when it opens through the stop (only if the order was resting at the open), worse by the cost.
- Orders sharing an `oco` group: the first fill cancels the rest. Within one bar the stop is
  checked before the limit (same bar hits both = the stop, conservatively).
"""
from __future__ import annotations

import datetime as dt

from .events import TICK, Bar, Fill, Order, Quote, Trade

ONE_S = dt.timedelta(seconds=1)


class SimBroker:
    def __init__(self, latency_s: float = 1.0, cost_bp: float = 10.0, extra_bp: float = 0.5):
        self.latency = dt.timedelta(seconds=latency_s)
        self.cost = cost_bp / 1e4
        self.extra = extra_bp / 1e4
        self.open: dict[int, Order] = {}
        self.qty: dict[int, int] = {}
        self.queue: dict[int, float] = {}
        self.quotes: dict[str, Quote] = {}
        self.immediate: list[Fill] = []

    # ------------------------------------------------------------------ orders
    def submit(self, o: Order, qty: int, now: dt.datetime) -> int:
        o.ts = o.ts or now
        if o.kind == "market" and self.latency.total_seconds() == 0 and o.ref_price:
            self.immediate.append(self._fill(o, qty, self._worse(o.ref_price, o.side, self.cost), now,
                                             "latency 0"))
            return o.id
        self.open[o.id], self.qty[o.id] = o, qty
        if o.kind == "limit":
            q = self.quotes.get(o.sym)
            at_limit = q and ((o.side == "sell" and abs(q.ask - o.limit) < TICK / 2)
                              or (o.side == "buy" and abs(q.bid - o.limit) < TICK / 2))
            self.queue[o.id] = (q.ask_size if o.side == "sell" else q.bid_size) if at_limit else 0.0
        return o.id

    def cancel(self, oid: int) -> None:
        self.open.pop(oid, None)

    def open_orders(self) -> list[Order]:
        return list(self.open.values())

    # ------------------------------------------------------------------ events
    def on_event(self, ev) -> list[Fill]:
        out, self.immediate = self.immediate, []
        if isinstance(ev, Quote):
            self.quotes[ev.sym] = ev
        mine = [o for o in self.open.values() if o.sym == getattr(ev, "sym", None)]
        mine.sort(key=lambda o: {"stop": 0, "market": 1, "limit": 2}[o.kind])
        filled_groups = set()
        for o in mine:
            if o.id not in self.open or (o.oco and o.oco in filled_groups):
                continue
            f = self._try(o, ev)
            if f is None:
                continue
            out.append(f)
            self.open.pop(o.id, None)
            if o.oco:
                filled_groups.add(o.oco)
                for other in [x for x in self.open.values() if x.oco == o.oco]:
                    self.open.pop(other.id, None)
        return out

    def _try(self, o: Order, ev) -> Fill | None:
        qty = self.qty[o.id]
        if o.kind == "market":
            due = o.ts + self.latency
            if isinstance(ev, Quote) and ev.ts >= due:
                px = ev.ask if o.side == "buy" else ev.bid
                return self._fill(o, qty, self._worse(px, o.side, self.extra), ev.ts, "quote")
            if isinstance(ev, Bar) and ev.start >= due - ONE_S:
                return self._fill(o, qty, self._worse(ev.open, o.side, self.cost), ev.start, "bar open")
            return None
        if o.kind == "stop":
            if isinstance(ev, Bar):
                hit = ev.low <= o.stop_px if o.side == "sell" else ev.high >= o.stop_px
                if hit:
                    # a gap fills at the open only if the order was resting when the bar opened;
                    # one placed inside this bar (a stop after an entry fill) fills at its price
                    gap = (ev.open <= o.stop_px if o.side == "sell" else ev.open >= o.stop_px) \
                        and o.ts <= ev.start
                    px = ev.open if gap else o.stop_px
                    return self._fill(o, qty, self._worse(px, o.side, self.cost), ev.ts, "stop")
            if isinstance(ev, Quote):
                hit = ev.bid <= o.stop_px if o.side == "sell" else ev.ask >= o.stop_px
                if hit:
                    px = ev.bid if o.side == "sell" else ev.ask
                    return self._fill(o, qty, self._worse(px, o.side, self.extra), ev.ts, "stop")
            return None
        # limit
        if isinstance(ev, Bar):
            through = ev.high >= o.limit + TICK if o.side == "sell" else ev.low <= o.limit - TICK
            return self._fill(o, qty, o.limit, ev.ts, "limit") if through else None
        if isinstance(ev, Trade):
            if (o.side == "sell" and ev.price > o.limit) or (o.side == "buy" and ev.price < o.limit):
                return self._fill(o, qty, o.limit, ev.ts, "limit")
            if abs(ev.price - o.limit) < TICK / 2:
                self.queue[o.id] = self.queue.get(o.id, 0.0) - ev.size
                if self.queue[o.id] < 0:
                    return self._fill(o, qty, o.limit, ev.ts, "limit (queue)")
        return None

    @staticmethod
    def _worse(px: float, side: str, c: float) -> float:
        return px * (1 + c) if side == "buy" else px * (1 - c)

    @staticmethod
    def _fill(o: Order, qty: int, px: float, ts, how: str) -> Fill:
        return Fill(o.id, o.sym, o.side, qty, px, ts, how)
