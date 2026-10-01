"""Market-data recorder for the lab: Schwab level-one stream for the core ETFs plus the morning's top
gappers, saved as daily Parquet partitions under data/daytrade/l1/trade_date=YYYY-MM-DD/.

Session: from the exchange's regular-hours calendar (`signals.regular_clock`), never a broker
clock. Rows are kept for [09:30, 16:00) of the regular session, plus each symbol's last pre-open
row (stamped as received) so the first regular volume delta has a baseline. Labelled by
`marketdata.trade_date`.

What the feed is (see README "What the feeds give"): Schwab's LEVELONE_EQUITIES is conflated
(changes only, batched by Schwab, not every print or quote). It has bid/ask/sizes, last price/size,
day volume and quote/trade times. There is NO time-and-sales service in the Schwab streamer, so
"trades" here are last-trade updates; one row can stand for several prints.

Isolation: it runs as its own systemd unit, uses its own COPY of the Schwab token (so it never
writes the live bot's token file), places no orders and reads no account.

Gaps: a reconnect, or more than SILENCE_S seconds with no message at all during the session, is
logged with its start and end in data/daytrade/meta/<date>.json, and the day is flagged.
A flagged day is excluded from studies, not patched.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import shutil
import time
from pathlib import Path
from zoneinfo import ZoneInfo

from .settings import CORE, DATA, ET, GAPPER_CAP, STATE

FIELDS = ("BID_PRICE", "ASK_PRICE", "LAST_PRICE", "BID_SIZE", "ASK_SIZE", "LAST_SIZE", "TOTAL_VOLUME",
          "QUOTE_TIME_MILLIS", "TRADE_TIME_MILLIS")
COLS = {"BID_PRICE": "bid", "ASK_PRICE": "ask", "LAST_PRICE": "last", "BID_SIZE": "bid_size",
        "ASK_SIZE": "ask_size", "LAST_SIZE": "last_size", "TOTAL_VOLUME": "volume",
        "QUOTE_TIME_MILLIS": "quote_ms", "TRADE_TIME_MILLIS": "trade_ms"}
SCHEMA_COLS = ("ts", "recv_ts", "sym", "bid", "ask", "bid_size", "ask_size", "last", "last_size",
               "volume", "quote_ms", "trade_ms")
FLUSH_S = 60
SILENCE_S = 30          # no message from ANY symbol for this long in the session = a gap
GAP_FLAG_S = 5          # a reconnect gap longer than this flags the day
GAPPER_MIN_PRICE = 5.0
GAPPER_MIN_ABS_GAP = 0.03
TOKEN_COPY = STATE / "schwab-token.json"


def log(msg: str) -> None:
    print(f"{dt.datetime.now(ZoneInfo(ET)):%H:%M:%S} {msg}", flush=True)


# ------------------------------------------------------------------ token (own copy)
def token_copy(dest: Path = TOKEN_COPY) -> Path:
    """Copy the live bot's Schwab token to state/daytrade/ when the copy is missing or older.
    The recorder refreshes ITS copy; the live bot's file is only ever read."""
    from swingtrader.daily.brokers import schwab_token_path
    src = schwab_token_path()
    if not src.exists():
        raise RuntimeError("no Schwab token yet - run: make schwab-login")
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        src_created = json.loads(src.read_text())["creation_timestamp"]
        dst_created = json.loads(dest.read_text())["creation_timestamp"] if dest.exists() else -1
    except Exception:
        src_created, dst_created = 1, -1
    if src_created != dst_created:
        shutil.copy2(src, dest)
        dest.chmod(0o600)
    return dest


def client(asyncio_: bool, dest: Path = TOKEN_COPY):
    from schwab.auth import client_from_token_file
    from swingtrader.daily.brokers import TOKEN_MAX_AGE_S, schwab_credentials, schwab_token_age_s
    k, s, _ = schwab_credentials()
    path = token_copy(dest)
    age = schwab_token_age_s(path)
    if age is None or age > TOKEN_MAX_AGE_S:
        raise RuntimeError("Schwab token missing or past 7 days - run: make schwab-login")
    return client_from_token_file(str(path), k, s, asyncio=asyncio_)


# ------------------------------------------------------------------ gappers (pre-session selection)
SPLIT_RATIOS = (2, 3, 4, 5, 10, 20)


def looks_like_corporate_action(ratio: float) -> bool:
    """A premarket last / previous close of +-50% or more, or within 3% of 1/k or k for a common split ratio k: on
    2026-10-01 the sweep picked CTVA at -81% (a separation priced against Schwab's unadjusted previous close)."""
    if ratio <= 0:
        return True
    if ratio >= 1.5 or ratio <= 0.5:
        return True
    return any(abs(ratio * k - 1) <= 0.03 or abs(ratio / k - 1) <= 0.03 for k in SPLIT_RATIOS)


def select_gappers(quotes: dict, cap: int = GAPPER_CAP, exclude=CORE) -> list[dict]:
    """quotes: Schwab get_quotes JSON. A gapper: premarket last vs previous close >= 3% either way,
    price >= $5; ranked by premarket volume (the quote's day volume before 09:30). This is the one
    pre-session read and it only picks what to RECORD; strategies apply their own rules."""
    rows = []
    for sym, d in (quotes or {}).items():
        q = d.get("quote") or {}
        last, prev, vol = q.get("lastPrice"), q.get("closePrice"), q.get("totalVolume")
        if sym in exclude or not (last and prev and vol) or last < GAPPER_MIN_PRICE:
            continue
        gap = last / prev - 1
        if looks_like_corporate_action(last / prev):
            continue                          # split/spin-off against an unadjusted previous close, not a move
        if abs(gap) >= GAPPER_MIN_ABS_GAP:
            rows.append({"sym": sym, "gap": round(gap, 4), "premarket_volume": int(vol),
                         "last": last, "prev_close": prev})
    rows.sort(key=lambda r: -r["premarket_volume"])
    return rows[:cap]


def candidate_symbols(today: dt.date, c) -> list[str]:
    """Liquid names to sweep for gappers: the live book's cached daily universe for today (read
    only) plus Schwab's movers lists."""
    from swingtrader.config import ROOT
    syms: set[str] = set()
    uni = ROOT / "state" / f"daily-universe-{today.isoformat()}.json"
    if uni.exists():
        try:
            syms |= {r["symbol"] for r in json.loads(uni.read_text())}
        except Exception as exc:
            log(f"universe file unreadable ({exc}); movers only")
    for index in ("$COMPX", "$DJI", "$SPX", "NYSE", "NASDAQ", "EQUITY_ALL"):
        for sort in ("VOLUME", "PERCENT_CHANGE_UP", "PERCENT_CHANGE_DOWN"):
            try:
                r = c.get_movers(index, sort_order=sort)
                if r.status_code == 200:
                    syms |= {x.get("symbol") for x in (r.json() or {}).get("screeners", []) if x.get("symbol")}
            except Exception:
                pass
    return sorted(s for s in syms if s and s.isalpha() and s not in CORE)


def morning_gappers(today: dt.date) -> list[dict]:
    c = client(asyncio_=False)
    syms = candidate_symbols(today, c)
    quotes = {}
    for i in range(0, len(syms), 200):
        r = c.get_quotes(syms[i:i + 200])
        if r.status_code == 200:
            quotes.update(r.json() or {})
    picks = select_gappers(quotes)
    log(f"gapper sweep: {len(syms)} candidates, {len(quotes)} quotes -> {[p['sym'] for p in picks]}")
    return picks


# ------------------------------------------------------------------ the recording
class Recording:
    def __init__(self, day: dt.date, open_: dt.datetime, close: dt.datetime, root: Path = DATA):
        self.day, self.open, self.close = day, open_, close
        self.dir = Path(root) / "l1" / f"trade_date={day.isoformat()}"
        self.meta_path = Path(root) / "meta" / f"{day.isoformat()}.json"
        self.state: dict[str, dict] = {}
        self.buf: list[tuple] = []
        self.preopen: dict[str, tuple] = {}
        self.rows = 0
        self.dropped_outside = 0
        self.last_msg: float | None = None
        self.gaps: list[dict] = []
        self.reconnects: list[str] = []
        self.symbols: list[str] = []
        self.gappers: list[dict] = []

    def on_message(self, msg: dict) -> None:
        recv = time.time()
        self.last_msg = recv
        server_ms = msg.get("timestamp")
        ts = dt.datetime.fromtimestamp((server_ms / 1000) if server_ms else recv, dt.timezone.utc)
        for c in msg.get("content", []) or []:
            sym = c.get("key")
            if not sym:
                continue
            st = self.state.setdefault(sym, {})
            for f, col in COLS.items():
                if f in c and c[f] is not None:
                    st[col] = c[f]
            row = (ts, dt.datetime.fromtimestamp(recv, dt.timezone.utc), sym,
                   *(st.get(k) for k in SCHEMA_COLS[3:]))
            if ts < self.open:
                self.preopen[sym] = row          # only the last pre-open row is kept
            elif ts < self.close:
                if self.preopen:
                    self.buf.extend(self.preopen.values())
                    self.preopen = {}
                self.buf.append(row)
            else:
                self.dropped_outside += 1

    def flush(self) -> None:
        if not self.buf:
            return
        import pyarrow as pa
        import pyarrow.parquet as pq
        cols = list(zip(*self.buf))
        types = [pa.timestamp("ns", tz="UTC"), pa.timestamp("ns", tz="UTC"), pa.string()] + \
                [pa.float64()] * 7 + [pa.int64()] * 2
        arrays = []
        for i, (name, typ) in enumerate(zip(SCHEMA_COLS, types)):
            vals = cols[i]
            if typ == pa.int64():
                vals = [int(v) if v is not None else None for v in vals]
            elif typ == pa.float64():
                vals = [float(v) if v is not None else None for v in vals]
            arrays.append(pa.array(vals, type=typ))
        t = pa.table(dict(zip(SCHEMA_COLS, arrays)))
        self.dir.mkdir(parents=True, exist_ok=True)
        pq.write_table(t, self.dir / f"part-{dt.datetime.now(dt.timezone.utc):%H%M%S%f}.parquet",
                       compression="zstd")
        self.rows += len(self.buf)
        self.buf = []

    def gap(self, start: float, end: float, why: str) -> None:
        s = dt.datetime.fromtimestamp(start, dt.timezone.utc)
        e = dt.datetime.fromtimestamp(end, dt.timezone.utc)
        if e <= self.open or s >= self.close:
            return
        self.gaps.append({"start": s.isoformat(), "end": e.isoformat(), "secs": round(end - start, 1),
                          "why": why})
        log(f"GAP {end - start:.1f}s ({why})")

    def write_meta(self, final: bool = False) -> None:
        self.meta_path.parent.mkdir(parents=True, exist_ok=True)
        in_session = [r for r in self.reconnects
                      if self.open <= dt.datetime.fromisoformat(r) < self.close]
        flagged = any(g["secs"] > GAP_FLAG_S for g in self.gaps) or bool(in_session)
        self.meta_path.write_text(json.dumps({
            "trade_date": self.day.isoformat(), "open": self.open.isoformat(),
            "close": self.close.isoformat(), "symbols": self.symbols, "gappers": self.gappers,
            "gapper_cap": GAPPER_CAP, "rows": self.rows, "dropped_outside_session": self.dropped_outside,
            "reconnects": self.reconnects, "gaps": self.gaps, "flagged": flagged, "complete": final,
            "feed": "schwab LEVELONE_EQUITIES (conflated; no time-and-sales)"}, indent=1))


async def _stream(rec: Recording, symbols: list[str], until: dt.datetime) -> None:
    from schwab.streaming import StreamClient
    fields = [getattr(StreamClient.LevelOneEquityFields, f) for f in ("SYMBOL",) + FIELDS]
    backoff = 1.0
    last_flush = time.time()
    while dt.datetime.now(dt.timezone.utc) < until:
        lost_at = rec.last_msg or time.time()
        try:
            sc = StreamClient(client(asyncio_=True))
            await sc.login()
            sc.add_level_one_equity_handler(rec.on_message)
            await sc.level_one_equity_subs(symbols, fields=fields)
            if rec.reconnects or rec.last_msg:
                rec.gap(lost_at, time.time(), "reconnect")
            log(f"streaming {len(symbols)} symbols")
            backoff = 1.0
            while dt.datetime.now(dt.timezone.utc) < until:
                try:
                    await asyncio.wait_for(sc.handle_message(), timeout=SILENCE_S)
                except asyncio.TimeoutError:
                    now = time.time()
                    rec.gap(rec.last_msg or now - SILENCE_S, now, f"silence > {SILENCE_S}s")
                    rec.last_msg = now
                if time.time() - last_flush >= FLUSH_S:
                    rec.flush(); rec.write_meta(); last_flush = time.time()
            await sc.logout()
        except Exception as exc:
            rec.reconnects.append(dt.datetime.now(dt.timezone.utc).isoformat())
            log(f"stream error {type(exc).__name__}: {str(exc)[:120]} - reconnect in {backoff:.0f}s")
            rec.flush()
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30.0)


def run(today: dt.date | None = None, smoke_s: int = 0, root: Path = DATA) -> int:
    from .session import calendar, session_times
    tz = ZoneInfo(ET)
    today = today or dt.datetime.now(tz).date()
    if smoke_s:
        # connectivity check outside the session: record `smoke_s` seconds into a scratch dir
        now = dt.datetime.now(dt.timezone.utc)
        rec = Recording(today, now - dt.timedelta(seconds=1), now + dt.timedelta(seconds=smoke_s), root)
        rec.symbols = list(CORE)
        asyncio.run(_stream(rec, rec.symbols, rec.close))
        rec.flush(); rec.write_meta(final=True)
        log(f"smoke: {rec.rows} rows, {len(rec.gaps)} gaps, {len(rec.reconnects)} reconnects -> {rec.dir}")
        return 0 if rec.rows else 1
    st = session_times(today, calendar(today, today))
    if st is None:
        log(f"{today}: no regular session - nothing to record")
        return 0
    if dt.datetime.now(tz) >= st.close:
        log(f"{today}: session already closed")
        return 0
    rec = Recording(today, st.open, st.close, root)
    # the gapper sweep runs at ~09:25 so premarket volume is nearly complete
    sweep_at = st.open - dt.timedelta(minutes=5)
    wait = (sweep_at - dt.datetime.now(tz)).total_seconds()
    if wait > 0:
        log(f"waiting {wait/60:.0f} min for the 09:25 gapper sweep")
        time.sleep(wait)
    try:
        rec.gappers = morning_gappers(today)
    except Exception as exc:
        log(f"gapper sweep failed ({type(exc).__name__}: {str(exc)[:120]}); core only")
    rec.symbols = list(CORE) + [g["sym"] for g in rec.gappers]
    rec.write_meta()
    asyncio.run(_stream(rec, rec.symbols, st.close + dt.timedelta(seconds=30)))
    rec.flush()
    rec.write_meta(final=True)
    log(f"done: {rec.rows} rows, {len(rec.gaps)} gaps, {len(rec.reconnects)} reconnects, "
        f"flagged={json.loads(rec.meta_path.read_text())['flagged']}")
    return 0
