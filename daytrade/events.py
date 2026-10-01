"""Market events and order/fill records shared by every mode."""
from __future__ import annotations

import datetime as dt
import itertools
from dataclasses import dataclass, field

TICK = 0.01
_ids = itertools.count(1)


@dataclass(frozen=True)
class Quote:
    ts: dt.datetime
    sym: str
    bid: float
    ask: float
    bid_size: float
    ask_size: float


@dataclass(frozen=True)
class Trade:
    ts: dt.datetime
    sym: str
    price: float
    size: float


@dataclass(frozen=True)
class Bar:
    """A regular-session minute bar. `start` is the minute it opens, `ts` the moment it closes."""
    ts: dt.datetime
    sym: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    start: dt.datetime


@dataclass(frozen=True)
class Clock:
    """A heartbeat with no market data (lets time-based rules and limits run on quiet seconds)."""
    ts: dt.datetime
    sym: str = ""


@dataclass(frozen=True)
class DayInfo:
    """Selection inputs known at the open. premarket_volume is the one pre-session field."""
    sym: str
    prev_close: float
    adv20_usd: float = 0.0
    premarket_volume: float = 0.0
    atr14: float = 0.0                 # true range average, prior 14 sessions
    avg_volume14: float = 0.0          # shares/day, prior 14 sessions
    or_volume_avg14: float = 0.0       # 09:30-09:34 volume, average of prior sessions


@dataclass
class Order:
    sym: str
    side: str                      # "buy" | "sell"
    kind: str = "market"           # "market" | "limit" | "stop"
    limit: float | None = None
    stop_px: float | None = None   # trigger for kind == "stop"
    entry: bool = True             # opens/extends a position; exits set False
    stop: float | None = None      # protective stop for an entry (required; used for sizing)
    stop_pct: float | None = None  # if set, the resting stop is placed this far from the actual FILL
    target: float | None = None    # resting limit exit for an entry (optional)
    ref_price: float | None = None # the decision price (sizing and the 0s-latency fill)
    qty: int | None = None         # set by the risk layer for entries
    reason: str = ""
    strategy: str = ""
    oco: str | None = None
    id: int = field(default_factory=lambda: next(_ids))
    ts: dt.datetime | None = None  # submit time, set by the engine


@dataclass
class Fill:
    order_id: int
    sym: str
    side: str
    qty: int
    price: float
    ts: dt.datetime
    reason: str = ""
