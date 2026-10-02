"""Forward evidence for the lab's shadow signals, logged by the recorder at the end of each session (no orders).

- Daily: Cboe SKEW and its z-score vs the trailing 252 sessions (Lab-CC: z >= 1 preceded weaker 20-day markets), and
  SPY's month-end trend flag (Lab-BY's filter, SPY above its 10-month average).
- First session of a month: the stock and industry momentum shadows (daytrade/momentum.py).
Everything is wrapped: a failure here is logged and never touches the recording.
"""
from __future__ import annotations

import datetime as dt
import io
import json
from pathlib import Path

import pandas as pd

from .settings import DATA

LOG = DATA / "forward-signals.jsonl"


def skew_z(csv_text: str, asof: dt.date) -> dict | None:
    df = pd.read_csv(io.StringIO(csv_text))
    df["d"] = pd.to_datetime(df.DATE, format="mixed")
    s = df.set_index("d").SKEW.astype(float)
    s = s[s.index <= pd.Timestamp(asof)]
    if len(s) < 253:
        return None
    win = s.iloc[-253:-1]
    z = (s.iloc[-1] - win.mean()) / win.std()
    return {"skew_date": str(s.index[-1].date()), "skew": float(s.iloc[-1]), "skew_z": round(float(z), 3),
            "skew_high": bool(z >= 1.0)}


def first_session_of_month(day: dt.date, sessions) -> bool:
    days = sorted(o.date() for o, _ in sessions if o.date().year == day.year and o.date().month == day.month)
    return bool(days) and days[0] == day


def run(day: dt.date, sessions, fetch=None, log: Path = LOG, momentum=None) -> dict:
    row = {"day": day.isoformat(), "logged": dt.datetime.now(dt.timezone.utc).isoformat()}
    try:
        if fetch is None:
            import requests
            fetch = lambda u: requests.get(u, timeout=30).text  # noqa: E731
        row.update(skew_z(fetch("https://cdn.cboe.com/api/global/us_indices/daily_prices/SKEW_History.csv"), day) or {})
    except Exception as exc:
        row["skew_error"] = f"{type(exc).__name__}: {str(exc)[:80]}"
    if first_session_of_month(day, sessions):
        try:
            if momentum is None:
                from .momentum import run as m, run_industry, trend_on
                m(); run_industry()
                row["trend_filter_on"] = trend_on((pd.Period(day, "M") - 1).strftime("%Y-%m"))
            else:
                momentum()
            row["momentum_shadows"] = "updated"
        except Exception as exc:
            row["momentum_error"] = f"{type(exc).__name__}: {str(exc)[:80]}"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a") as f:
        f.write(json.dumps(row) + "\n")
    return row
