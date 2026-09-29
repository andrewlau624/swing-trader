"""Ex-ante-known event calendars (reusable). All dates are ET calendar dates.

    from research.sim import event_calendar as EC
    EC.fomc_dates()             # scheduled FOMC decision days (statement 14:00 ET)
    EC.cpi_dates()              # CPI release days (08:30 ET)
    EC.nfp_dates()              # Employment Situation release days (08:30 ET)
    EC.claims_dates()           # weekly jobless claims (Thursdays 08:30; Wed if Thu is a holiday)
    EC.opex_dates()             # monthly equity option expiration (3rd Friday; Thu if holiday)
    EC.triple_witching_dates()  # quarterly (Mar/Jun/Sep/Dec) opex
    EC.nyse_holidays(y0, y1)    # full-day NYSE closures by rule (no ad-hoc closures)

Every function returns a sorted list of pd.Timestamp (normalized, tz-naive).
All of these dates were public well before the decision times the book uses
(the Fed publishes its meeting calendar a year ahead; BLS publishes release
schedules each autumn for the next year; 2025 shutdown reschedules were
announced days-to-weeks before the new date).
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
from dateutil.easter import easter

# Source: federalreserve.gov/monetarypolicy/fomccalendars.htm (2021-2026) and
# fomchistoricalYYYY.htm (2016-2020), fetched 2026-09-28. Second (decision) day of
# each SCHEDULED meeting. 2020: the scheduled Mar 17-18 meeting was replaced by the
# unscheduled Sunday Mar 15 action, so no scheduled decision on Mar 18 (excluded).
FOMC_SCHEDULED = """
2016-01-27 2016-03-16 2016-04-27 2016-06-15 2016-07-27 2016-09-21 2016-11-02 2016-12-14
2017-02-01 2017-03-15 2017-05-03 2017-06-14 2017-07-26 2017-09-20 2017-11-01 2017-12-13
2018-01-31 2018-03-21 2018-05-02 2018-06-13 2018-08-01 2018-09-26 2018-11-08 2018-12-19
2019-01-30 2019-03-20 2019-05-01 2019-06-19 2019-07-31 2019-09-18 2019-10-30 2019-12-11
2020-01-29 2020-04-29 2020-06-10 2020-07-29 2020-09-16 2020-11-05 2020-12-16
2021-01-27 2021-03-17 2021-04-28 2021-06-16 2021-07-28 2021-09-22 2021-11-03 2021-12-15
2022-01-26 2022-03-16 2022-05-04 2022-06-15 2022-07-27 2022-09-21 2022-11-02 2022-12-14
2023-02-01 2023-03-22 2023-05-03 2023-06-14 2023-07-26 2023-09-20 2023-11-01 2023-12-13
2024-01-31 2024-03-20 2024-05-01 2024-06-12 2024-07-31 2024-09-18 2024-11-07 2024-12-18
2025-01-29 2025-03-19 2025-05-07 2025-06-18 2025-07-30 2025-09-17 2025-10-29 2025-12-10
2026-01-28 2026-03-18 2026-04-29 2026-06-17 2026-07-29 2026-09-16 2026-10-28 2026-12-09
"""
# NOT ex-ante (never use for pre-event positioning): unscheduled actions.
FOMC_UNSCHEDULED = "2020-03-03 2020-03-15 2020-03-23"

# Source: bls.gov/bls/news-release/cpi.htm (release archive), fetched 2026-09-28.
# 2025-10-24 = delayed Sept CPI (shutdown); Oct 2025 CPI was never released;
# 2025-12-18 = Nov CPI. 2026-02-13 = Jan CPI (rescheduled).
CPI = """
2015-01-16 2015-02-26 2015-03-24 2015-04-17 2015-05-22 2015-06-18 2015-07-17 2015-08-19
2015-09-16 2015-10-15 2015-11-17 2015-12-15
2016-01-20 2016-02-19 2016-03-16 2016-04-14 2016-05-17 2016-06-16 2016-07-15 2016-08-16
2016-09-16 2016-10-18 2016-11-17 2016-12-15
2017-01-18 2017-02-15 2017-03-15 2017-04-14 2017-05-12 2017-06-14 2017-07-14 2017-08-11
2017-09-14 2017-10-13 2017-11-15 2017-12-13
2018-01-12 2018-02-14 2018-03-13 2018-04-11 2018-05-10 2018-06-12 2018-07-12 2018-08-10
2018-09-13 2018-10-11 2018-11-14 2018-12-12
2019-01-11 2019-02-13 2019-03-12 2019-04-10 2019-05-10 2019-06-12 2019-07-11 2019-08-13
2019-09-12 2019-10-10 2019-11-13 2019-12-11
2020-01-14 2020-02-13 2020-03-11 2020-04-10 2020-05-12 2020-06-10 2020-07-14 2020-08-12
2020-09-11 2020-10-13 2020-11-12 2020-12-10
2021-01-13 2021-02-10 2021-03-10 2021-04-13 2021-05-12 2021-06-10 2021-07-13 2021-08-11
2021-09-14 2021-10-13 2021-11-10 2021-12-10
2022-01-12 2022-02-10 2022-03-10 2022-04-12 2022-05-11 2022-06-10 2022-07-13 2022-08-10
2022-09-13 2022-10-13 2022-11-10 2022-12-13
2023-01-12 2023-02-14 2023-03-14 2023-04-12 2023-05-10 2023-06-13 2023-07-12 2023-08-10
2023-09-13 2023-10-12 2023-11-14 2023-12-12
2024-01-11 2024-02-13 2024-03-12 2024-04-10 2024-05-15 2024-06-12 2024-07-11 2024-08-14
2024-09-11 2024-10-10 2024-11-13 2024-12-11
2025-01-15 2025-02-12 2025-03-12 2025-04-10 2025-05-13 2025-06-11 2025-07-15 2025-08-12
2025-09-11 2025-10-24 2025-12-18
2026-01-13 2026-02-13 2026-03-11 2026-04-10 2026-05-12 2026-06-10 2026-07-14 2026-08-12
2026-09-11
"""

# Source: bls.gov/bls/news-release/empsit.htm (release archive), fetched 2026-09-28.
# 2025-11-20 = delayed Sept report; Oct 2025 household survey cancelled, Oct/Nov
# establishment data released 2025-12-16. 2026-02-11 = Jan report (rescheduled).
NFP = """
2015-02-06 2015-03-06 2015-04-03 2015-05-08 2015-06-05 2015-07-02 2015-08-07 2015-09-04
2015-10-02 2015-11-06 2015-12-04
2016-01-08 2016-02-05 2016-03-04 2016-04-01 2016-05-06 2016-06-03 2016-07-08 2016-08-05
2016-09-02 2016-10-07 2016-11-04 2016-12-02
2017-01-06 2017-02-03 2017-03-10 2017-04-07 2017-05-05 2017-06-02 2017-07-07 2017-08-04
2017-09-01 2017-10-06 2017-11-03 2017-12-08
2018-01-05 2018-02-02 2018-03-09 2018-04-06 2018-05-04 2018-06-01 2018-07-06 2018-08-03
2018-09-07 2018-10-05 2018-11-02 2018-12-07
2019-01-04 2019-02-01 2019-03-08 2019-04-05 2019-05-03 2019-06-07 2019-07-05 2019-08-02
2019-09-06 2019-10-04 2019-11-01 2019-12-06
2020-01-10 2020-02-07 2020-03-06 2020-04-03 2020-05-08 2020-06-05 2020-07-02 2020-08-07
2020-09-04 2020-10-02 2020-11-06 2020-12-04
2021-01-08 2021-02-05 2021-03-05 2021-04-02 2021-05-07 2021-06-04 2021-07-02 2021-08-06
2021-09-03 2021-10-08 2021-11-05 2021-12-03
2022-01-07 2022-02-04 2022-03-04 2022-04-01 2022-05-06 2022-06-03 2022-07-08 2022-08-05
2022-09-02 2022-10-07 2022-11-04 2022-12-02
2023-01-06 2023-02-03 2023-03-10 2023-04-07 2023-05-05 2023-06-02 2023-07-07 2023-08-04
2023-09-01 2023-10-06 2023-11-03 2023-12-08
2024-01-05 2024-02-02 2024-03-08 2024-04-05 2024-05-03 2024-06-07 2024-07-05 2024-08-02
2024-09-06 2024-10-04 2024-11-01 2024-12-06
2025-01-10 2025-02-07 2025-03-07 2025-04-04 2025-05-02 2025-06-06 2025-07-03 2025-08-01
2025-09-05 2025-11-20 2025-12-16
2026-01-09 2026-02-11 2026-03-06 2026-04-03 2026-05-08 2026-06-05 2026-07-02 2026-08-07
2026-09-04
"""


def _parse(s: str) -> list[pd.Timestamp]:
    return sorted(pd.Timestamp(x) for x in s.split())


def fomc_dates(include_unscheduled: bool = False) -> list[pd.Timestamp]:
    d = _parse(FOMC_SCHEDULED)
    return sorted(d + _parse(FOMC_UNSCHEDULED)) if include_unscheduled else d


def cpi_dates() -> list[pd.Timestamp]:
    return _parse(CPI)


def nfp_dates() -> list[pd.Timestamp]:
    return _parse(NFP)


def _observed(d: date) -> date:
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def _nth_weekday(y: int, m: int, wd: int, n: int) -> date:
    d = date(y, m, 1)
    d += timedelta(days=(wd - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def _last_weekday(y: int, m: int, wd: int) -> date:
    d = date(y, m + 1, 1) - timedelta(days=1) if m < 12 else date(y, 12, 31)
    return d - timedelta(days=(d.weekday() - wd) % 7)


def nyse_holidays(y0: int = 2014, y1: int = 2027) -> set[pd.Timestamp]:
    """Rule-based full-day NYSE closures (ignores one-offs like 2018-12-05 Bush funeral)."""
    out = set()
    for y in range(y0, y1 + 1):
        nyd = date(y, 1, 1)
        if nyd.weekday() != 5:          # Sat New Year: no Friday closure (NYSE rule)
            out.add(_observed(nyd))
        out.add(_nth_weekday(y, 1, 0, 3))   # MLK
        out.add(_nth_weekday(y, 2, 0, 3))   # Presidents
        out.add(easter(y) - timedelta(days=2))  # Good Friday
        out.add(_last_weekday(y, 5, 0))     # Memorial
        if y >= 2022:
            out.add(_observed(date(y, 6, 19)))  # Juneteenth
        out.add(_observed(date(y, 7, 4)))
        out.add(_nth_weekday(y, 9, 0, 1))   # Labor
        out.add(_nth_weekday(y, 11, 3, 4))  # Thanksgiving
        out.add(_observed(date(y, 12, 25)))
    out.add(date(2018, 12, 5))  # national day of mourning (announced 2018-12-01)
    return {pd.Timestamp(d) for d in out}


def claims_dates(y0: int = 2015, y1: int = 2026) -> list[pd.Timestamp]:
    """DOL weekly UI claims, 08:30 ET. Thursday; if Thursday is a federal holiday
    (Thanksgiving, July 4, Christmas, New Year, Juneteenth, Veterans Day) it is
    released the Wednesday before. Rule-based (DOL publishes the shifts ahead)."""
    hol = nyse_holidays(y0, y1 + 1)
    fed = {pd.Timestamp(date(y, 11, 11)) for y in range(y0, y1 + 1)}
    fed |= {pd.Timestamp(date(y, 6, 19)) for y in range(2021, y1 + 1)}
    out = []
    for t in pd.date_range(f"{y0}-01-01", f"{y1}-12-31", freq="W-THU"):
        out.append(t - pd.Timedelta(days=1) if (t in hol or t in fed) else t)
    return out


def opex_dates(y0: int = 2015, y1: int = 2026) -> list[pd.Timestamp]:
    """Monthly equity option expiration: 3rd Friday; Thursday before if it is an NYSE holiday."""
    hol = nyse_holidays(y0, y1)
    out = []
    for y in range(y0, y1 + 1):
        for m in range(1, 13):
            t = pd.Timestamp(_nth_weekday(y, m, 4, 3))
            out.append(t - pd.Timedelta(days=1) if t in hol else t)
    return out


def triple_witching_dates(y0: int = 2015, y1: int = 2026) -> list[pd.Timestamp]:
    return [t for t in opex_dates(y0, y1) if t.month in (3, 6, 9, 12)]


if __name__ == "__main__":
    for f in (fomc_dates, cpi_dates, nfp_dates, claims_dates, opex_dates, triple_witching_dates):
        d = f()
        print(f"{f.__name__:24s} n={len(d):4d}  {d[0].date()} .. {d[-1].date()}")
    bad = [t for t in fomc_dates() + cpi_dates() + nfp_dates() if t.weekday() > 4 or t in nyse_holidays()]
    print("event dates on weekend/holiday:", bad)
