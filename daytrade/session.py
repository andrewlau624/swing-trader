"""Regular-session times for one trade date, from the exchange's regular-hours calendar via
`signals.regular_clock` (never a broker clock or a vendor 'day', which may start at 21:00 the
evening before under 23/5 trading)."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from swingtrader.daily.signals import regular_clock

from .settings import ET, Limits


@dataclass(frozen=True)
class SessionTimes:
    day: dt.date
    open: dt.datetime
    close: dt.datetime
    entry_cutoff: dt.datetime      # no new entries at or after this
    flat_by: dt.datetime           # every position is flat by this

    def at(self, hhmm: str) -> dt.datetime:
        h, m = map(int, hhmm.split(":")[:2])
        s = int(hhmm.split(":")[2]) if hhmm.count(":") == 2 else 0
        return self.open.replace(hour=h, minute=m, second=s)


def session_times(day: dt.date, sessions, limits: Limits | None = None) -> SessionTimes | None:
    """sessions: [(open, close)] tz-aware ET from the calendar (brokers.regular_sessions).
    None when `day` has no regular session."""
    lim = limits or Limits()
    midnight = dt.datetime.combine(day, dt.time(0, 0), tzinfo=ZoneInfo(ET))
    clk = regular_clock(midnight, sessions)
    if clk.next_open.date() != day:
        return None
    o, c = clk.next_open, clk.next_close
    return SessionTimes(day, o, c, c - dt.timedelta(minutes=lim.entry_cutoff_min),
                        c - dt.timedelta(minutes=lim.flat_min))


def calendar(start: dt.date, end: dt.date):
    """Regular sessions from Alpaca's exchange calendar (holidays and 13:00 half days)."""
    from swingtrader.daily.brokers import regular_sessions
    return regular_sessions(start, end + dt.timedelta(days=7))
