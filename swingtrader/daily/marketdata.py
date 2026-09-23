"""Market data for the daily book. SIP (consolidated tape) wherever it is
allowed, because IEX-only bars have the wrong opens and ~5% of real volume.

The free data plan refuses SIP newer than 15 minutes, so at decision time:
  - history (yesterday and before): SIP
  - right now: IEX latest trade, with the day's range taken as the wider of
    the IEX range and the 15-minute-delayed SIP range.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..data import _clients

ET = "America/New_York"
SNAP_BATCH = 1000
BAR_BATCH = 1000


def _sip_end() -> pd.Timestamp:
    # the plan refuses SIP newer than 15 minutes
    return pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=16)


def sip_daily(symbols: list[str], start, end=None) -> dict[str, pd.DataFrame]:
    """Completed SIP daily bars, indexed by ET session date."""
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    data, _ = _clients()
    end = min(pd.Timestamp(end, tz="UTC") if end is not None else _sip_end(), _sip_end())
    out: dict[str, pd.DataFrame] = {}
    for i in range(0, len(symbols), BAR_BATCH):
        chunk = symbols[i:i + BAR_BATCH]
        try:
            df = data.get_stock_bars(StockBarsRequest(
                symbol_or_symbols=chunk, timeframe=TimeFrame.Day,
                start=pd.Timestamp(start, tz="UTC"), end=end,
                feed="sip", adjustment="all")).df
        except Exception:
            # one bad symbol can reject a whole batch; fall back per symbol
            df = _per_symbol(data, chunk, start, end)
        if df is None or df.empty:
            continue
        df = df.reset_index()
        df["date"] = (df["timestamp"].dt.tz_convert(ET).dt.tz_localize(None)
                      .dt.normalize())
        for sym, g in df.groupby("symbol"):
            out[sym] = g.set_index("date")[["open", "high", "low", "close", "volume"]]
    return out


def _per_symbol(data, chunk, start, end):
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    parts = []
    for s in chunk:
        try:
            parts.append(data.get_stock_bars(StockBarsRequest(
                symbol_or_symbols=[s], timeframe=TimeFrame.Day,
                start=pd.Timestamp(start, tz="UTC"), end=end,
                feed="sip", adjustment="all")).df)
        except Exception:
            pass
    parts = [p for p in parts if p is not None and len(p)]
    return pd.concat(parts) if parts else None


def eligibility(symbols: list[str], today: dt.date, *, price_min: float,
                adv_min: float, cache_dir: Path) -> pd.DataFrame:
    """Names the night leg may trade today, from bars BEFORE today only:
    yesterday's close >= price_min and 20-day SIP dollar volume >= adv_min.
    Cached per day -- the morning run pays ~30s, the 15:40 run reads it."""
    path = cache_dir / f"daily-universe-{today.isoformat()}.json"
    if path.exists():
        d = json.loads(path.read_text())
        if d and "vol20" in d[0]:          # older cache files lack vol20: rebuild
            return pd.DataFrame(d).set_index("symbol")
    bars = sip_daily(symbols, pd.Timestamp(today) - pd.Timedelta(days=45),
                     pd.Timestamp(today))
    rows = []
    for sym, b in bars.items():
        b = b[b.index < pd.Timestamp(today)]
        if len(b) < 20:
            continue
        adv = float((b["close"] * b["volume"]).iloc[-20:].mean())
        pc = float(b["close"].iloc[-1])
        lr = np.log(b["close"] / b["close"].shift(1)).iloc[-20:]
        vol20 = float(lr.std() * np.sqrt(252))
        if pc >= price_min and adv >= adv_min:
            rows.append({"symbol": sym, "prev_close": pc, "adv20": adv,
                         "vol20": vol20 if np.isfinite(vol20) else 0.0,
                         "prev_date": str(b.index[-1].date())})
    cache_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows))
    for old in cache_dir.glob("daily-universe-*.json"):
        if old != path:
            old.unlink(missing_ok=True)
    return pd.DataFrame(rows).set_index("symbol") if rows else pd.DataFrame(
        columns=["prev_close", "adv20", "vol20", "prev_date"])


QUOTE_BATCH = 200


def schwab_rows(symbols: list[str], max_age_min: float = 10.0, client=None) -> pd.DataFrame:
    """Decision-time rows from Schwab real-time consolidated quotes: regular-
    session last price and the day's high/low. Closer to the research's SIP
    data than IEX, whose range misses most of the tape."""
    if client is None:
        from .brokers import schwab_client
        client = schwab_client()
    now_ms = pd.Timestamp.now(tz="UTC").value / 1e6
    rows = {}
    for i in range(0, len(symbols), QUOTE_BATCH):
        chunk = symbols[i:i + QUOTE_BATCH]
        r = client.get_quotes(chunk)
        r.raise_for_status()
        for sym, d in (r.json() or {}).items():
            q, reg = d.get("quote") or {}, d.get("regular") or {}
            px = reg.get("regularMarketLastPrice") or q.get("lastPrice")
            t = reg.get("regularMarketTradeTime") or q.get("tradeTime")
            hi, lo = q.get("highPrice"), q.get("lowPrice")
            if not (px and t and hi and lo):
                continue
            age = (now_ms - float(t)) / 60000
            if age > max_age_min:
                continue
            rows[sym] = {"price": float(px), "high": float(hi), "low": float(lo),
                         "trade_age_min": age}
    return pd.DataFrame.from_dict(rows, orient="index")


def decision_rows(symbols: list[str], source: str = "auto", max_age_min: float = 10.0,
                  log=print) -> tuple[pd.DataFrame, str]:
    """Pick the data source. auto: Schwab when a valid login exists, else
    Alpaca. Any Schwab failure falls back to Alpaca rather than skipping the day."""
    if source in ("auto", "schwab"):
        try:
            rows = schwab_rows(symbols, max_age_min)
            if not rows.empty:
                return rows, "schwab"
            log("  Schwab quotes returned nothing fresh - falling back to Alpaca")
        except Exception as exc:
            if source == "schwab":
                log(f"  Schwab quotes failed ({str(exc)[:90]}) - falling back to Alpaca")
    return live_rows(symbols, max_age_min), "alpaca"


def live_rows(symbols: list[str], max_age_min: float = 10.0) -> pd.DataFrame:
    """Decision-time price and day range for each symbol.
    price = IEX latest trade (real time); range = union of IEX and delayed-SIP
    daily bars. Symbols whose latest IEX trade is stale are dropped rather
    than traded on an old price."""
    from alpaca.data.enums import DataFeed
    from alpaca.data.requests import StockSnapshotRequest
    data, _ = _clients()
    now = pd.Timestamp.now(tz="UTC")
    rows = {}
    for i in range(0, len(symbols), SNAP_BATCH):
        chunk = symbols[i:i + SNAP_BATCH]
        iex = data.get_stock_snapshot(StockSnapshotRequest(
            symbol_or_symbols=chunk, feed=DataFeed.IEX))
        try:
            dsip = data.get_stock_snapshot(StockSnapshotRequest(
                symbol_or_symbols=chunk, feed=DataFeed.DELAYED_SIP))
        except Exception:
            dsip = {}
        for sym, s in iex.items():
            if s is None or s.latest_trade is None or s.daily_bar is None:
                continue
            age = (now - pd.Timestamp(s.latest_trade.timestamp)).total_seconds() / 60
            if age > max_age_min:
                continue
            hi, lo = float(s.daily_bar.high), float(s.daily_bar.low)
            d = dsip.get(sym)
            if d is not None and d.daily_bar is not None:
                db_day = pd.Timestamp(d.daily_bar.timestamp).tz_convert(ET).date()
                if db_day == now.tz_convert(ET).date():
                    hi, lo = max(hi, float(d.daily_bar.high)), min(lo, float(d.daily_bar.low))
            rows[sym] = {"price": float(s.latest_trade.price), "high": hi, "low": lo,
                         "trade_age_min": age}
    return pd.DataFrame.from_dict(rows, orient="index")


def minute_history(symbol: str, sessions: int) -> dict:
    """Prior `sessions` complete RTH sessions of SIP 1-minute bars, as
    {date: (390,) close array, "open": ...}. Used for the noise-area sigma."""
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    data, _ = _clients()
    start = pd.Timestamp.now(tz=ET).normalize() - pd.Timedelta(days=int(sessions * 1.6) + 7)
    df = data.get_stock_bars(StockBarsRequest(
        symbol_or_symbols=[symbol], timeframe=TimeFrame.Minute,
        start=start.tz_convert("UTC"), end=_sip_end(),
        feed="sip", adjustment="all")).df.reset_index()
    return _to_sessions(df)


def minute_today(symbol: str) -> dict:
    """Today's RTH minutes so far, IEX (real time)."""
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    data, _ = _clients()
    start = pd.Timestamp.now(tz=ET).normalize() + pd.Timedelta(hours=9, minutes=30)
    df = data.get_stock_bars(StockBarsRequest(
        symbol_or_symbols=[symbol], timeframe=TimeFrame.Minute,
        start=start.tz_convert("UTC"), feed="iex")).df.reset_index()
    return _to_sessions(df, full_only=False)


def _to_sessions(df: pd.DataFrame, full_only: bool = True) -> dict:
    """{date: {"close": (390,), "volume": (390,), "open": first open}}"""
    out = {}
    if df.empty:
        return out
    t = df["timestamp"].dt.tz_convert(ET)
    df = df.assign(date=t.dt.tz_localize(None).dt.normalize(),
                   m=t.dt.hour * 60 + t.dt.minute - 570)
    df = df[(df.m >= 0) & (df.m < 390)]
    for d, g in df.groupby("date"):
        c = np.full(390, np.nan); v = np.zeros(390)
        c[g.m.values] = g.close.values; v[g.m.values] = g.volume.values
        if full_only and np.isnan(c[300:]).all():
            continue            # half day or missing data
        last = int(np.nanmax(np.where(np.isfinite(c), np.arange(390), -1)))
        c = pd.Series(c).ffill().values
        out[d] = {"close": c, "volume": v, "open": float(g.sort_values("m").open.iloc[0]),
                  "last_minute": last}
    return out
