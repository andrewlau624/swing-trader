"""State for the daily book: virtual cash, positions, orders, history.

The paper account is shared with the swing book and holds ~$98k, but this
experiment asks what a $3k account does. So the book keeps its OWN cash,
starting at `start_equity`, and it changes only through this book's fills.
Broker fills are the only source of truth for quantities and prices.
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

BOOK_FILE = "book-daily.json"          # paper account (shared with the swing book)
LIVE_BOOK_FILE = "book-daily-live.json"  # real-money account (dedicated)


def book_file(account: str) -> str:
    return LIVE_BOOK_FILE if account == "live" else BOOK_FILE
TERMINAL = {"filled", "canceled", "expired", "rejected", "done_for_day", "replaced"}


@dataclass
class DailyBook:
    cash: float
    start_equity: float
    positions: dict = field(default_factory=dict)   # sym -> {qty, avg_px, leg, entry_date}
    orders: dict = field(default_factory=dict)      # coid -> {sym, side, leg, ref_px, status, ...}
    closed: list = field(default_factory=list)      # round trips
    equity_log: list = field(default_factory=list)  # [{date, equity}]
    noise: dict = field(default_factory=dict)       # shadow/live intraday leg state (primary: QQQ)
    noise_more: dict = field(default_factory=dict)  # further intraday instruments: signal sym -> state
    conviction: dict = field(default_factory=dict)  # TQQQ strong-first-breakout trade (shadow or live)
    daytrade_live: bool = False
    noise_lev_cap: float = 0.0                      # set each morning from the broker's multiplier
    route_refused: str = ""                         # date Schwab last refused a directed open sell
    killed: dict = field(default_factory=dict)      # leg (or "all") -> {date, reason}: no new entries
    levered: bool = False                           # overnight leverage gate (signals.lever_ok) is open
    last_run: str = ""

    # ------------------------------------------------------------ persist
    @classmethod
    def load(cls, state_dir: Path, start_equity: float,
             fname: str = BOOK_FILE) -> "DailyBook":
        p = state_dir / fname
        if p.exists():
            return cls(**json.loads(p.read_text()))
        return cls(cash=start_equity, start_equity=start_equity)

    def save(self, state_dir: Path, fname: str = BOOK_FILE) -> None:
        state_dir.mkdir(parents=True, exist_ok=True)
        p = state_dir / fname
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2, default=str))
        tmp.replace(p)

    # ------------------------------------------------------------ queries
    def open_orders(self) -> dict:
        return {k: o for k, o in self.orders.items() if o.get("status") not in TERMINAL}

    def owned_symbols(self) -> set[str]:
        return set(self.positions) | {o["sym"] for o in self.open_orders().values()}

    def leg_positions(self, leg: str) -> dict:
        return {s: p for s, p in self.positions.items() if p.get("leg") == leg}

    def equity(self, marks: dict[str, float]) -> float:
        v = self.cash
        for s, p in self.positions.items():
            v += float(p["qty"]) * float(marks.get(s, p["avg_px"]))
        return v

    # ------------------------------------------------------------ updates
    def register(self, coid: str, **info) -> None:
        self.orders[coid] = {"status": "new", "filled_qty": 0.0, **info}

    def apply_fill(self, coid: str, filled_qty: float, avg_px: float,
                   status: str, when: str) -> float | None:
        """Book any NEW filled quantity on this order. Returns the newly booked
        qty (so the caller can log slippage), or None if nothing new."""
        o = self.orders[coid]
        new = float(filled_qty) - float(o.get("filled_qty", 0.0))
        o["status"] = status
        if new <= 1e-9:
            return None
        o["filled_qty"] = float(filled_qty)
        o["fill_px"] = float(avg_px)
        sym, leg = o["sym"], o["leg"]
        d = new if o["side"] == "buy" else -new      # signed: shorts go negative
        self.cash -= d * avg_px
        p = self.positions.get(sym)
        old = float(p["qty"]) if p else 0.0
        q = old + d
        if p is not None and old * d < 0:
            # reducing (or flipping) an existing position: book the round trip
            closed = min(abs(d), abs(old))
            sign = 1.0 if old > 0 else -1.0
            self.closed.append({"sym": sym, "leg": p["leg"], "qty": closed * sign,
                                "entry_px": float(p["avg_px"]), "exit_px": avg_px,
                                "entry_date": p["entry_date"], "exit_date": when[:10],
                                "pnl": closed * sign * (avg_px - float(p["avg_px"])),
                                "ret": sign * (avg_px / float(p["avg_px"]) - 1.0)})
        if abs(q) <= 1e-6:
            self.positions.pop(sym, None)
        elif p is None or old * q <= 0:
            # new position, or flipped through zero: fresh basis
            self.positions[sym] = {"qty": q, "avg_px": avg_px, "leg": leg,
                                   "entry_date": when[:10]}
        elif old * d > 0:
            p["avg_px"] = (old * float(p["avg_px"]) + d * avg_px) / q
            p["qty"] = q
        else:
            p["qty"] = q
        return new

    def is_killed(self, leg: str) -> bool:
        return leg in self.killed or "all" in self.killed

    def log_equity(self, day: str, equity: float) -> None:
        if self.equity_log and self.equity_log[-1]["date"] == day:
            self.equity_log[-1]["equity"] = round(equity, 2)
        else:
            self.equity_log.append({"date": day, "equity": round(equity, 2)})


def owned_by_daily(state_dir: Path) -> set[str]:
    """For the swing executor: symbols it must neither adopt nor trade.
    Paper book only -- the live book trades a different account."""
    p = state_dir / BOOK_FILE
    if not p.exists():
        return set()
    try:
        d = json.loads(p.read_text())
    except Exception:
        return set()
    syms = set(d.get("positions", {}))
    syms |= {o["sym"] for o in d.get("orders", {}).values()
             if o.get("status") not in TERMINAL}
    return syms
