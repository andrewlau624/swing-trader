"""Daily bars from Alpaca, cached to parquet.

Two things here are correctness-critical rather than conveniences:

1. adjustment="all". Alpaca defaults to raw bars. On five years of beaten-down
   small caps a reverse split appears as a bar where price rises 10x and a
   forward split as a -50% overnight crash. A dip-buying backtest would happily
   "buy" those phantom crashes and book phantom reversions. Never use raw here.

2. The trading calendar comes from Alpaca, not from weekday(). Treating market
   holidays as trading days corrupts both half-life estimates and time-stop
   counting, because the bar index silently stops meaning "trading day".
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd

from .config import ROOT, require_alpaca_keys

CACHE = ROOT / "data" / "cache" / "bars"
BATCH = 200  # symbols per API request; ~0.9s each

_ADJ = {"raw": "raw", "split": "split", "dividend": "dividend", "all": "all"}


def _clients():
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.trading.client import TradingClient

    k, s = require_alpaca_keys()
    return StockHistoricalDataClient(k, s), TradingClient(k, s, paper=True)


def trading_days(start: str | dt.date, end: str | dt.date) -> pd.DatetimeIndex:
    """Authoritative NYSE session dates from Alpaca's calendar endpoint."""
    from alpaca.trading.requests import GetCalendarRequest

    _, trading = _clients()
    cal = trading.get_calendar(GetCalendarRequest(start=pd.Timestamp(start).date(),
                                                 end=pd.Timestamp(end).date()))
    return pd.DatetimeIndex(sorted(pd.Timestamp(c.date) for c in cal))


def _cache_path(symbol: str) -> Path:
    # ':' and '/' appear in some Alpaca symbols (warrants/units)
    safe = symbol.replace("/", "_").replace(":", "_")
    return CACHE / f"{safe}.parquet"


def _read_cache(symbol: str) -> pd.DataFrame | None:
    p = _cache_path(symbol)
    if not p.exists():
        return None
    try:
        return pd.read_parquet(p)
    except Exception:
        return None


def _covers(df: pd.DataFrame | None, start: pd.Timestamp, end: pd.Timestamp) -> bool:
    if df is None or df.empty:
        return False
    # Cached range must reach back far enough and forward far enough. A symbol
    # that IPO'd mid-range legitimately starts late, so allow a start later than
    # requested only if the cache was built from a request that began earlier.
    meta_start = df.attrs.get("req_start")
    meta_end = df.attrs.get("req_end")
    if meta_start is None or meta_end is None:
        return False
    return pd.Timestamp(meta_start) <= start and pd.Timestamp(meta_end) >= end


def fetch_bars(
    symbols: list[str],
    start: str | dt.date,
    end: str | dt.date,
    feed: str = "iex",
    adjustment: str = "all",
    use_cache: bool = True,
    verbose: bool = True,
) -> dict[str, pd.DataFrame]:
    """Daily OHLCV per symbol, indexed by tz-naive date, split/div adjusted."""
    from alpaca.data.enums import Adjustment, DataFeed
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame

    if adjustment not in _ADJ:
        raise ValueError(f"adjustment must be one of {sorted(_ADJ)}, got {adjustment!r}")
    if adjustment == "raw":
        raise ValueError(
            "adjustment='raw' makes splits look like crashes; use 'all' for backtests"
        )

    CACHE.mkdir(parents=True, exist_ok=True)
    s_ts, e_ts = pd.Timestamp(start), pd.Timestamp(end)
    out: dict[str, pd.DataFrame] = {}
    todo: list[str] = []

    for sym in symbols:
        cached = _read_cache(sym) if use_cache else None
        if _covers(cached, s_ts, e_ts):
            out[sym] = cached.loc[(cached.index >= s_ts) & (cached.index <= e_ts)]
        else:
            todo.append(sym)

    if not todo:
        return out

    data, _ = _clients()
    feed_enum = DataFeed.IEX if feed == "iex" else DataFeed.SIP
    adj_enum = Adjustment(adjustment)

    def request(chunk: list[str]):
        return data.get_stock_bars(
            StockBarsRequest(
                symbol_or_symbols=chunk,
                timeframe=TimeFrame.Day,
                start=s_ts.to_pydatetime(),
                end=e_ts.to_pydatetime(),
                feed=feed_enum,
                adjustment=adj_enum,
            )
        ).df

    def fetch_chunk(chunk: list[str], depth: int = 0):
        """Fetch a chunk; on failure bisect to isolate the bad symbol(s).

        Alpaca rejects the WHOLE request if any one symbol is invalid, so a
        single junk ticker would otherwise silently cost 200 symbols of data.
        """
        try:
            return request(chunk)
        except Exception as exc:
            if len(chunk) == 1:
                if verbose:
                    print(f"  skip {chunk[0]}: {type(exc).__name__}: {str(exc)[:80]}")
                return None
            mid = len(chunk) // 2
            frames = [fetch_chunk(chunk[:mid], depth + 1), fetch_chunk(chunk[mid:], depth + 1)]
            frames = [f for f in frames if f is not None and not f.empty]
            return pd.concat(frames) if frames else None

    for i in range(0, len(todo), BATCH):
        chunk = todo[i : i + BATCH]
        df = fetch_chunk(chunk)

        if df is None or df.empty:
            continue
        df = df.reset_index()
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(
            "America/New_York"
        ).dt.normalize().dt.tz_localize(None)

        for sym, g in df.groupby("symbol", sort=False):
            g = (
                g.set_index("timestamp")[["open", "high", "low", "close", "volume"]]
                .sort_index()
                .astype("float64")
            )
            g = g[~g.index.duplicated(keep="last")]
            g.attrs["req_start"] = str(s_ts.date())
            g.attrs["req_end"] = str(e_ts.date())
            g.attrs["adjustment"] = adjustment
            g.attrs["feed"] = feed
            if use_cache:
                g.to_parquet(_cache_path(sym))
            out[sym] = g

        # symbols the API returned nothing for: cache an empty marker so we
        # don't re-request dead tickers on every run
        if use_cache:
            for sym in set(chunk) - set(out):
                empty = pd.DataFrame(columns=["open", "high", "low", "close", "volume"],
                                     index=pd.DatetimeIndex([], name="timestamp"))
                empty.attrs["req_start"] = str(s_ts.date())
                empty.attrs["req_end"] = str(e_ts.date())
                empty.to_parquet(_cache_path(sym))

        if verbose and (i // BATCH) % 10 == 0:
            print(f"  fetched {min(i+BATCH, len(todo))}/{len(todo)} symbols")

    return out


def to_panel(bars: dict[str, pd.DataFrame], field: str = "close") -> pd.DataFrame:
    """dict of per-symbol frames -> one date x symbol frame."""
    if not bars:
        return pd.DataFrame()
    return pd.DataFrame({s: d[field] for s, d in bars.items() if not d.empty}).sort_index()


def refresh_bars(symbols: list[str], end: str | dt.date, lookback_days: int = 10,
                 feed: str = "iex", adjustment: str = "all",
                 verbose: bool = False) -> dict[str, pd.DataFrame]:
    """Append recent bars to the cache instead of refetching all history.

    A live daily run needs bars through today, which the coverage check treats
    as a cache miss -- refetching ~6 minutes of history every day. This pulls
    only the tail and merges it, so a daily run costs seconds.
    """
    from alpaca.data.enums import Adjustment, DataFeed
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame

    CACHE.mkdir(parents=True, exist_ok=True)
    e_ts = pd.Timestamp(end)
    s_ts = e_ts - pd.Timedelta(days=lookback_days)
    data, _ = _clients()
    feed_enum = DataFeed.IEX if feed == "iex" else DataFeed.SIP
    out: dict[str, pd.DataFrame] = {}

    import time as _time
    t0 = _time.time()
    nbatch = (len(symbols) + BATCH - 1) // BATCH
    for i in range(0, len(symbols), BATCH):
        chunk = symbols[i : i + BATCH]
        if verbose and (i // BATCH) % 10 == 0 and i:
            done = i / len(symbols)
            el = _time.time() - t0
            eta = el / done - el if done > 0 else 0
            print(f"    refresh {i}/{len(symbols)} ({100*done:.0f}%) "
                  f"{el:.0f}s elapsed, ~{eta:.0f}s left", flush=True)
        try:
            df = data.get_stock_bars(StockBarsRequest(
                symbol_or_symbols=chunk, timeframe=TimeFrame.Day,
                start=s_ts.to_pydatetime(), end=e_ts.to_pydatetime(),
                feed=feed_enum, adjustment=Adjustment(adjustment))).df
        except Exception as exc:
            if verbose:
                print(f"  refresh batch {i//BATCH} failed: {type(exc).__name__}")
            continue
        if df is None or df.empty:
            continue
        df = df.reset_index()
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(
            "America/New_York").dt.normalize().dt.tz_localize(None)
        for sym, g in df.groupby("symbol", sort=False):
            g = (g.set_index("timestamp")[["open", "high", "low", "close", "volume"]]
                   .sort_index().astype("float64"))
            old = _read_cache(sym)
            if old is not None and not old.empty:
                merged = pd.concat([old, g])
                merged = merged[~merged.index.duplicated(keep="last")].sort_index()
                merged.attrs.update(old.attrs)
                merged.attrs["req_end"] = str(e_ts.date())
            else:
                merged = g
                merged.attrs["req_start"] = str(s_ts.date())
                merged.attrs["req_end"] = str(e_ts.date())
            merged.attrs["adjustment"] = adjustment
            merged.attrs["feed"] = feed
            merged.to_parquet(_cache_path(sym))
            out[sym] = merged
    return out
