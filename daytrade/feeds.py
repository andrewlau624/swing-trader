"""Event feeds. One conversion (level-one rows -> Quote / Trade / minute Bar events) serves both the
replay of a recorded day and the live paper/live loop, so a strategy sees the same bar semantics in
both. Minute-history replay (SIP bars) is in daytrade/research/as_replay.py.

A level-one row: ts (tz-aware UTC), sym, bid, ask, bid_size, ask_size, last, last_size, volume
(cumulative day volume), trade_ms (the last trade's time). Schwab's stream is conflated: one row
can stand for several prints, so a Trade's size is the volume delta since the previous row.

Regular hours only: every event is inside [session.open, session.close) from regular_clock, and
bars are built from regular-session trades only (the day volume counter includes premarket, so
the first regular delta is taken against the last premarket value).
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from .events import Bar, Clock, Quote, Trade
from .settings import DATA

MIN = dt.timedelta(minutes=1)


class BarBuilder:
    def __init__(self):
        self.cur: dict[str, list] = {}       # sym -> [start, o, h, l, c, v]

    def add(self, sym: str, ts: dt.datetime, px: float, size: float) -> None:
        start = ts.replace(second=0, microsecond=0)
        b = self.cur.get(sym)
        if b is None or b[0] != start:
            self.cur[sym] = [start, px, px, px, px, size]
            return
        b[2], b[3], b[4], b[5] = max(b[2], px), min(b[3], px), px, b[5] + size

    def close_before(self, boundary: dt.datetime) -> list[Bar]:
        out = []
        for sym, b in list(self.cur.items()):
            if b[0] + MIN <= boundary:
                out.append(Bar(b[0] + MIN, sym, b[1], b[2], b[3], b[4], b[5], b[0]))
                del self.cur[sym]
        return sorted(out, key=lambda x: (x.ts, x.sym))


def rows_to_events(rows, session, clock_every_s: int = 0):
    """rows: an iterable of level-one dicts in time order (recorded or polled)."""
    bars = BarBuilder()
    last_vol: dict[str, float] = {}
    last_trade_ms: dict[str, float] = {}
    boundary = session.open + MIN
    next_clock = session.open
    for r in rows:
        ts = r["ts"]
        if ts >= session.close:
            break
        while ts >= boundary:
            yield from bars.close_before(boundary)
            boundary += MIN
        if clock_every_s and ts >= next_clock:
            yield Clock(ts)
            next_clock = ts + dt.timedelta(seconds=clock_every_s)
        sym = r.get("sym")
        if not sym:                                  # a heartbeat row from a live loop
            continue
        vol = float(r.get("volume") or 0)
        prev_vol = last_vol.get(sym)
        last_vol[sym] = vol
        if ts < session.open:
            last_trade_ms[sym] = r.get("trade_ms")
            continue
        bid, ask = float(r.get("bid") or 0), float(r.get("ask") or 0)
        if bid > 0 and ask > 0 and ask >= bid:
            yield Quote(ts, sym, bid, ask, float(r.get("bid_size") or 0), float(r.get("ask_size") or 0))
        tms = r.get("trade_ms")
        px = float(r.get("last") or 0)
        if tms and tms != last_trade_ms.get(sym) and px > 0:
            last_trade_ms[sym] = tms
            size = vol - prev_vol if prev_vol is not None and vol > prev_vol else float(r.get("last_size") or 0)
            if size > 0:
                bars.add(sym, ts, px, size)
                yield Trade(ts, sym, px, size)
    yield from bars.close_before(session.close + MIN)


def recorded_day(day: dt.date, root: Path = DATA) -> Path:
    return Path(root) / "l1" / f"trade_date={day.isoformat()}"


def read_recorded(day: dt.date, root: Path = DATA):
    """Rows of a recorded day, time-sorted, as dicts (pyarrow; no pandas needed)."""
    import pyarrow.parquet as pq
    d = recorded_day(day, root)
    files = sorted(d.glob("*.parquet")) if d.exists() else []
    if not files:
        return []
    import pyarrow as pa
    t = pa.concat_tables([pq.read_table(f) for f in files]).sort_by("ts")
    return t.to_pylist()


def day_flagged(day: dt.date, root: Path = DATA) -> bool | None:
    """True if the recorder logged a gap that day, None if the day has no meta file."""
    import json
    p = Path(root) / "meta" / f"{day.isoformat()}.json"
    if not p.exists():
        return None
    return bool(json.loads(p.read_text()).get("flagged"))
