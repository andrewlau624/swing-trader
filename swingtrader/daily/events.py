"""Scheduled macro-event calendar for the live daily book (addendum 33).

Only SCHEDULED FOMC decision days (the second day of each meeting, statement
at 14:00 ET). Unscheduled actions are never known in advance and never count.
Copied from research/sim/event_calendar.py (2026) plus the 2027 schedule and
the first 2028 meeting from federalreserve.gov/monetarypolicy/fomccalendars.htm
(fetched 2026-09-28; the Fed marks each date tentative until the meeting
before it confirms it).

The calendar is hard-coded, so it goes stale. `days_left()` says how far it
reaches; the executor and `make daily-status` warn loudly once fewer than
STALE_DAYS of future dates remain. To extend it, append the next year's
decision days to FOMC_SCHEDULED.
"""
from __future__ import annotations

import datetime as dt
import math

FOMC_SCHEDULED = """
2026-01-28 2026-03-18 2026-04-29 2026-06-17 2026-07-29 2026-09-16 2026-10-28 2026-12-09
2027-01-27 2027-03-17 2027-04-28 2027-06-09 2027-07-28 2027-09-15 2027-10-27 2027-12-08
2028-01-26
"""
STALE_DAYS = 60

# F3 (addendum 33): QQQ close -> next open with the night leg's unused money on
# the eve of a scheduled FOMC decision. Taxable only (a Roth QQQ buy within 30
# days of a taxable QQQ intraday loss sale disallows that loss for good).
FOMC_FILLER_SYMBOL = "QQQ"
FOMC_COST_BPS = 3.0          # per side, shadow scoring (the study's pass bar cost)
FOMC_DISABLE_N = 16          # pre-registered: switch off if mean net < 0 after 16 events


def fomc_dates() -> list[dt.date]:
    return sorted(dt.date.fromisoformat(s) for s in FOMC_SCHEDULED.split())


def is_fomc_eve(next_session: dt.date) -> bool:
    """True when the NEXT trading session is a scheduled FOMC decision day,
    i.e. tonight's close -> next open spans the pre-FOMC night."""
    return next_session in set(fomc_dates())


def next_fomc(today: dt.date) -> dt.date | None:
    return next((d for d in fomc_dates() if d >= today), None)


def days_left(today: dt.date) -> int:
    """Calendar days from today to the last date in the calendar (negative = run out)."""
    return (fomc_dates()[-1] - today).days


def stale_warning(today: dt.date) -> str | None:
    left = days_left(today)
    if left >= STALE_DAYS:
        return None
    return (f"FOMC calendar in swingtrader/daily/events.py runs out {fomc_dates()[-1]} "
            f"({left} days left, < {STALE_DAYS}): add next year's scheduled decision days "
            "from federalreserve.gov/monetarypolicy/fomccalendars.htm, or the FOMC-eve shadow "
            "silently stops firing")


def filler_spare(budget: float, planned: float, cash_left: float | None = None,
                 floor: float = 0.0) -> float:
    """Spare night money = night budget - planned night notional (research
    book.day_pnl filler), never more than the book cash left above its floor."""
    spare = max(0.0, budget - planned)
    if cash_left is not None:
        spare = min(spare, max(0.0, cash_left - floor))
    return spare


def filler_shares(spare: float, price: float) -> int:
    """Whole shares: the close/open auctions take whole shares only."""
    if not (price and price > 0 and math.isfinite(price)):
        return 0
    return int(math.floor(spare / price))


def fomc_score(history: list[dict]) -> tuple[int, float, bool]:
    """(n events, mean net bp, auto-disable proposed?) over scored events."""
    r = [float(h["ret"]) for h in history if h.get("ret") is not None]
    if not r:
        return 0, float("nan"), False
    m = sum(r) / len(r) * 1e4
    return len(r), m, (len(r) >= FOMC_DISABLE_N and m < 0)
