"""One engine for replay, paper and live. The mode lives only in which broker and feed are plugged
in; strategies never see it.

Each event, in order:
  1. HALT file -> cancel everything, flatten, stop (checked on every event).
  2. Broker fills (replay: the SimBroker; paper/live: the real broker, polled) and, for paper/live,
     the shadow SimBroker's fill for the same order (the drift report).
  3. Marks, then the daily loss limit (flatten + stop for the day) and flat-by-close.
  4. The strategies, whose orders go through the risk layer before any broker sees them.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

from .events import Bar, Clock, Fill, Order, Quote, Trade
from .risk import AccountModel, Rejected, RiskLayer
from .settings import HALT, Limits


@dataclass
class Position:
    sym: str
    strategy: str
    qty: int = 0
    avg: float = 0.0
    entry_ts: dt.datetime | None = None
    entry_reason: str = ""
    entry_replay: float | None = None
    stop: float | None = None
    target: float | None = None
    exits: list = field(default_factory=list)      # resting stop/target order ids


class Ctx:
    """What a strategy may see: time, its session, prices, its positions, the day's selection
    inputs. Nothing about the mode, the broker or the account number."""

    def __init__(self, engine: "Engine"):
        self._e = engine

    @property
    def now(self) -> dt.datetime:
        return self._e.now

    @property
    def session(self):
        return self._e.session

    def position(self, sym: str) -> int:
        p = self._e.positions.get(sym)
        return p.qty if p else 0

    def mark(self, sym: str) -> float | None:
        return self._e.marks.get(sym)

    def quote(self, sym: str):
        return self._e.quotes.get(sym)

    def day_info(self, sym: str):
        return self._e.day_info.get(sym)

    def symbols(self) -> list[str]:
        return list(self._e.day_info)

    def is_cash_account(self) -> bool:
        return self._e.risk.account.is_cash


class Engine:
    def __init__(self, strategies, broker, *, equity: float, session, account_kind: str = "margin",
                 limits: Limits | None = None, day_info: dict | None = None, journal=None,
                 shadow=None, halt_path: Path = HALT, settle_day: dt.date | None = None, log=None,
                 account: AccountModel | None = None):
        self.strategies = list(strategies)
        self.broker = broker
        self.shadow = shadow                # SimBroker run beside a real broker (paper/live)
        self.limits = limits or Limits()
        # a multi-day replay passes one account through every day (cash settlement carries over)
        self.risk = RiskLayer(self.limits, account or AccountModel(equity, account_kind,
                                                                   self.limits.intraday_mult))
        self.session = session
        self.day_info = dict(day_info or {})
        self.journal = journal
        self.halt_path = Path(halt_path)
        self.settle_day = settle_day or (session.day + dt.timedelta(days=1))
        self.log = log or (lambda *_: None)
        self.positions: dict[str, Position] = {}
        self.marks: dict[str, float] = {}
        self.quotes: dict[str, Quote] = {}
        self.pending: dict[int, Order] = {}       # entries/exits sent, not yet filled
        self.cancelled: dict[int, Order] = {}     # a real broker can still fill these
        self.shadow_px: dict[int, float] = {}
        self.events: list[dict] = []              # rule events: rejections, limits, halts
        self.trades: list[dict] = []              # closed round trips
        self.halted = False
        self.flattened = False
        self.now = session.open
        self.ctx = Ctx(self)
        self.risk.new_day(session.day)
        self._started = False

    # ---------------------------------------------------------------- main step
    def process(self, ev) -> None:
        self.now = ev.ts
        if not self._started:
            self._started = True
            for s in self.strategies:
                self._send(s.on_session_start(self.ctx) or [], s)
        if not self.halted and self.halt_path.exists():
            self.halt("HALT file")
        for f in self.broker.on_event(ev):
            self._on_fill(f, ev)
        if self.shadow is not None:
            for f in self.shadow.on_event(ev):
                self.shadow_px[f.order_id] = f.price
        if isinstance(ev, Bar):
            # protective orders placed on a fill from this bar are live for the rest of it
            for f in self.broker.on_event(ev):
                self._on_fill(f, ev)
        self._mark(ev)
        if self.halted:
            return
        if not self.risk.stopped_for_day and self.positions and self.risk.loss_limit_hit(self._unrealized()):
            self.risk.stopped_for_day = True
            self._rule("daily loss limit", f"{self.limits.daily_loss_pct:.1%} of start equity")
            self.flatten("daily loss limit")
        if self.now >= self.session.flat_by:
            if not self.flattened:
                self.flattened = True
                self.flatten("flat by close")
            return
        for s in self.strategies:
            orders = []
            if isinstance(ev, Bar):
                orders = s.on_bar(self.ctx, ev)
            elif isinstance(ev, Quote):
                orders = s.on_quote(self.ctx, ev)
            elif isinstance(ev, Trade):
                orders = s.on_trade(self.ctx, ev)
            orders = (orders or []) + (s.on_clock(self.ctx) or [])
            self._send(orders, s)

    def run(self, events) -> "Engine":
        for ev in events:
            self.process(ev)
        self.end_of_data()
        return self

    # ---------------------------------------------------------------- orders
    def _send(self, orders, strategy) -> None:
        for o in orders:
            o.strategy = o.strategy or strategy.name
            if self.halted or (self.flattened and o.entry):
                self._rule("order after halt/flat", f"{o.sym} {o.side}", strategy=o.strategy)
                continue
            if o.entry:
                try:
                    qty = self.risk.size_entry(o, self.now, self.session, self.positions, self.marks)
                except Rejected as r:
                    self._rule("rejected", f"{o.sym} {o.side}: {r}", strategy=o.strategy)
                    continue
            else:
                p = self.positions.get(o.sym)
                if not p or p.qty == 0 or self._exit_pending(o.sym):
                    continue
                self._cancel_exits(p)
                qty = abs(p.qty)
            self._submit(o, qty)

    def _submit(self, o: Order, qty: int) -> None:
        o.ts = self.now
        o.qty = qty
        self.pending[o.id] = o
        self.broker.submit(o, qty, self.now)
        if self.shadow is not None:
            self.shadow.submit(o, qty, self.now)

    def _exit_pending(self, sym: str) -> bool:
        return any(o.sym == sym and not o.entry and o.kind == "market" for o in self.pending.values())

    def _cancel(self, oid: int) -> None:
        o = self.pending.pop(oid, None)
        if o is not None:
            self.cancelled[oid] = o
        self.broker.cancel(oid)
        if self.shadow is not None:
            self.shadow.cancel(oid)

    def _on_fill(self, f: Fill, ev) -> None:
        late = f.order_id not in self.pending and f.order_id in self.cancelled
        o = self.pending.pop(f.order_id, None) or self.cancelled.pop(f.order_id, None)
        if o is None:
            return
        p = self.positions.get(f.sym)
        signed = f.qty if f.side == "buy" else -f.qty
        if p is None or p.qty == 0:
            p = Position(f.sym, o.strategy, signed, f.price, f.ts, o.reason,
                         self.shadow_px.get(o.id), o.stop, o.target)
            self.positions[f.sym] = p
            self.risk.account.on_open(f.qty * f.price)
            self._place_exits(p, o)
        elif (p.qty > 0) == (signed > 0):                # add to a winner
            self.risk.account.on_open(f.qty * f.price)
            p.avg = (p.avg * abs(p.qty) + f.price * f.qty) / (abs(p.qty) + f.qty)
            p.qty += signed
            self._cancel_exits(p)
            self._place_exits(p, o)
        else:                                            # exit (full)
            self._close(p, f, o)
        if late and (self.halted or self.flattened or self.risk.stopped_for_day):
            # a real broker filled an order the engine had cancelled: close it at once
            self.flatten("late fill after cancel")
            return
        for s in self.strategies:
            if s.name == o.strategy:
                self._send(s.on_fill(self.ctx, f) or [], s)

    def _place_exits(self, p: Position, entry: Order) -> None:
        side = "sell" if p.qty > 0 else "buy"
        group = f"oco-{entry.id}"
        orders = []
        if p.stop is not None:
            orders.append(Order(p.sym, side, "stop", stop_px=p.stop, entry=False, reason="stop",
                                strategy=p.strategy, oco=group))
        if p.target is not None:
            orders.append(Order(p.sym, side, "limit", limit=p.target, entry=False, reason="target",
                                strategy=p.strategy, oco=group))
        for o in orders:
            self._submit(o, abs(p.qty))
            p.exits.append(o.id)

    def _cancel_exits(self, p: Position) -> None:
        for oid in p.exits:
            self._cancel(oid)
        p.exits = []

    def _close(self, p: Position, f: Fill, o: Order) -> None:
        self._cancel_exits(p)
        qty = abs(p.qty)
        sign = 1 if p.qty > 0 else -1
        entry_n, exit_n = qty * p.avg, qty * f.price
        pnl = sign * (exit_n - entry_n)
        # account: a long returns its exit notional; a short returns entry + P&L
        self.risk.account.on_close(entry_n, entry_n + pnl, self.settle_day)
        row = {"strategy": p.strategy, "sym": p.sym, "side": "long" if sign > 0 else "short",
               "qty": qty, "entry_ts": str(p.entry_ts), "entry_px": round(p.avg, 4),
               "entry_reason": p.entry_reason, "exit_ts": str(f.ts), "exit_px": round(f.price, 4),
               "exit_reason": o.reason or f.reason, "pnl": round(pnl, 2),
               "net_bp": round(sign * (f.price / p.avg - 1) * 1e4, 2),
               "stop": p.stop, "target": p.target,
               "replay_entry_px": p.entry_replay, "replay_exit_px": self.shadow_px.get(o.id),
               "day": str(self.session.day), "note": ""}
        if p.stop is not None and p.avg != p.stop:
            row["r"] = round(sign * (f.price - p.avg) / abs(p.avg - p.stop), 3)
        self.trades.append(row)
        if self.journal is not None:
            self.journal.trade(row)
        p.qty, p.exits = 0, []
        del self.positions[p.sym]

    # ---------------------------------------------------------------- limits
    def flatten(self, why: str) -> None:
        for oid, o in list(self.pending.items()):
            if o.entry or o.kind != "market":
                self._cancel(oid)
        for p in list(self.positions.values()):
            if p.qty == 0 or self._exit_pending(p.sym):
                continue
            self._cancel_exits(p)
            o = Order(p.sym, "sell" if p.qty > 0 else "buy", entry=False, reason=why,
                      strategy=p.strategy, ref_price=self.marks.get(p.sym))
            self._submit(o, abs(p.qty))

    def halt(self, why: str) -> None:
        self.halted = True
        self._rule("halt", why)
        cancel_all = getattr(self.broker, "cancel_all", None)
        if cancel_all is not None:          # a real broker: cancel everything it holds first
            cancel_all()
        self.flatten("halt")

    def end_of_data(self) -> None:
        """Replay ran out of data with something open: close at the last mark and flag it."""
        for p in list(self.positions.values()):
            px = self.marks.get(p.sym, p.avg)
            self._rule("held at end of data", p.sym, strategy=p.strategy)
            o = Order(p.sym, "sell" if p.qty > 0 else "buy", entry=False, reason="end of data",
                      strategy=p.strategy)
            self._close(p, Fill(o.id, p.sym, o.side, abs(p.qty), px, self.now, "end of data"), o)

    def _rule(self, kind: str, detail: str, strategy: str = "") -> None:
        row = {"ts": str(self.now), "kind": kind, "detail": detail, "strategy": strategy,
               "day": str(self.session.day)}
        self.events.append(row)
        self.log(f"  [rule] {kind}: {detail}")
        if self.journal is not None:
            self.journal.event(row)

    # ---------------------------------------------------------------- marks
    def _mark(self, ev) -> None:
        if isinstance(ev, Bar):
            self.marks[ev.sym] = ev.close
        elif isinstance(ev, Trade):
            self.marks[ev.sym] = ev.price
        elif isinstance(ev, Quote):
            self.quotes[ev.sym] = ev
            if ev.bid > 0 and ev.ask > 0:
                self.marks[ev.sym] = (ev.bid + ev.ask) / 2

    def _unrealized(self) -> float:
        return sum((self.marks.get(p.sym, p.avg) - p.avg) * p.qty for p in self.positions.values())


def clock_ticks(session, step_s: int = 1):
    """Heartbeat events for a live loop (Clock has no data; it only advances time)."""
    t = session.open
    while t <= session.close:
        yield Clock(t)
        t += dt.timedelta(seconds=step_s)
