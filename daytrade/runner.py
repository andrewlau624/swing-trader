"""Wiring: which feed and which broker go into the one engine. The strategies are the same objects in
every mode; only this file knows the mode."""
from __future__ import annotations

import datetime as dt
import json
import time
from zoneinfo import ZoneInfo

from .engine import Engine
from .events import DayInfo
from .feeds import day_flagged, read_recorded, rows_to_events
from .fills import SimBroker
from .guard import check_mode
from .journal import Journal, load
from .settings import DATA, ET, HALT, STATE, env
from .strategies import REGISTRY

ENGINE_TOKEN = STATE / "schwab-token-engine.json"


def strategies(name: str):
    return [cls() for n, cls in REGISTRY.items() if name in ("all", n)]


def recorded_day_info(day: dt.date) -> dict:
    """Selection inputs for a recorded day from the recorder's morning sweep (prev close and
    premarket volume). ADV is not in the sweep; it is filled from SIP daily bars when available."""
    p = DATA / "meta" / f"{day.isoformat()}.json"
    info = {}
    if p.exists():
        for g in json.loads(p.read_text()).get("gappers", []):
            info[g["sym"]] = DayInfo(g["sym"], float(g["prev_close"]), 0.0, float(g["premarket_volume"]))
    if info:
        try:
            import pandas as pd
            from swingtrader.daily.marketdata import sip_daily
            bars = sip_daily(list(info), pd.Timestamp(day) - pd.Timedelta(days=40), pd.Timestamp(day))
            for s, b in bars.items():
                b = b[b.index < pd.Timestamp(day)].iloc[-20:]
                if len(b):
                    d = info[s]
                    info[s] = DayInfo(s, d.prev_close, float((b.close * b.volume).mean()), d.premarket_volume)
        except Exception as exc:
            print(f"  ADV unavailable ({type(exc).__name__}); gap strategy will skip these names")
    return info


def replay_recorded(day: dt.date, strategy: str = "all", equity: float = 2300.0,
                    latency: float = 1.0) -> int:
    from .session import calendar, session_times
    st = session_times(day, calendar(day, day))
    if st is None:
        print(f"{day}: no regular session"); return 1
    flagged = day_flagged(day)
    if flagged is None:
        print(f"{day}: no recording"); return 1
    if flagged:
        print(f"{day}: FLAGGED (recorder gap) - replayed for inspection only, excluded from studies")
    rows = read_recorded(day)
    eng = Engine(strategies(strategy), SimBroker(latency_s=latency, extra_bp=0.5), equity=equity,
                 session=st, day_info=recorded_day_info(day), halt_path=STATE / "HALT-replay-never",
                 journal=Journal("replay"), log=print)
    eng.run(rows_to_events(rows, st, clock_every_s=1))
    for t in eng.trades:
        print(f"  {t['strategy']:18} {t['sym']:5} {t['side']:5} {t['qty']:4} "
              f"{t['entry_px']:.2f} -> {t['exit_px']:.2f} ({t['exit_reason']}) {t['net_bp']:+.1f}bp")
    print(f"{day}: {len(eng.trades)} trades, {len(eng.events)} rule events, {len(rows)} rows")
    return 0


# ------------------------------------------------------------------ paper / live loop
def poll_rows(c, symbols: list[str]) -> list[dict]:
    r = c.get_quotes(symbols)
    if r.status_code != 200:
        return []
    now = dt.datetime.now(dt.timezone.utc)
    out = []
    for sym, d in (r.json() or {}).items():
        q = d.get("quote") or {}
        out.append({"ts": now, "sym": sym, "bid": q.get("bidPrice"), "ask": q.get("askPrice"),
                    "bid_size": q.get("bidSize"), "ask_size": q.get("askSize"),
                    "last": q.get("lastPrice"), "last_size": q.get("lastSize"),
                    "volume": q.get("totalVolume"), "trade_ms": q.get("tradeTime")})
    return out


def live_rows(c, symbols, until: dt.datetime, every_s: float = 1.0):
    """Schwab REST quotes once a second (60/min, inside the 120/min market-data limit), plus a
    heartbeat row so time-based rules and HALT run even when nothing changes."""
    while dt.datetime.now(dt.timezone.utc) < until:
        t0 = time.time()
        try:
            yield from poll_rows(c, symbols)
        except Exception as exc:
            print(f"  quote poll failed: {type(exc).__name__}")
        yield {"ts": dt.datetime.now(dt.timezone.utc), "sym": None}
        time.sleep(max(0.0, every_s - (time.time() - t0)))


def run_live(mode: str, strategy: str = "all") -> int:
    from .brokers import AlpacaLabPaper, SchwabLabLive
    from .recorder import client, morning_gappers
    from .session import calendar, session_times
    from .settings import CORE
    check_mode(mode)
    tz = ZoneInfo(ET)
    today = dt.datetime.now(tz).date()
    st = session_times(today, calendar(today, today))
    if st is None:
        print(f"{today}: no regular session"); return 0
    if mode == "paper":
        broker = AlpacaLabPaper()
        equity = float(env("DAYTRADE_PAPER_CAPITAL") or 2300)
    else:
        cap = float(env("DAYTRADE_LIVE_CAPITAL") or 0)
        broker = SchwabLabLive(cap)
        equity = broker.equity()
    kind = (env("DAYTRADE_ACCOUNT_KIND") or ("margin" if equity >= 2000 else "cash")).lower()
    meta = DATA / "meta" / f"{today.isoformat()}.json"
    while dt.datetime.now(tz) < st.open - dt.timedelta(minutes=4) and not meta.exists():
        time.sleep(10)
    info = recorded_day_info(today) if meta.exists() else {}
    if not info:
        from .events import DayInfo
        info = {g["sym"]: DayInfo(g["sym"], g["prev_close"], 0.0, g["premarket_volume"])
                for g in morning_gappers(today)}
    c = client(asyncio_=False, dest=ENGINE_TOKEN)
    symbols = sorted(set(CORE) | set(info))
    eng = Engine(strategies(strategy), broker, equity=equity, session=st, account_kind=kind,
                 day_info=info, journal=Journal(mode), shadow=SimBroker(latency_s=1.0, extra_bp=0.5),
                 log=print)
    print(f"{mode}: {today} equity ${equity:,.0f} ({kind}), {len(symbols)} symbols, "
          f"strategies {[s.name for s in eng.strategies]}")
    while dt.datetime.now(tz) < st.open:
        if HALT.exists():
            print("HALT set before the open: not starting"); return 0
        time.sleep(1)
    eng.run(rows_to_events(live_rows(c, symbols, st.close + dt.timedelta(minutes=1)), st, clock_every_s=1))
    print(f"{mode}: done, {len(eng.trades)} trades, {len(eng.events)} rule events")
    return 0


def status() -> int:
    print(f"HALT: {'SET' if HALT.exists() else 'off'} ({HALT})")
    days = sorted((DATA / "meta").glob("*.json")) if (DATA / "meta").exists() else []
    clean = 0
    for p in days[-10:]:
        m = json.loads(p.read_text())
        clean += 0 if m.get("flagged") else 1
        print(f"  {m['trade_date']}: {m['rows']:>9,} rows  {len(m['symbols']):2} symbols  "
              f"gaps {len(m['gaps'])}  reconnects {len(m['reconnects'])}  "
              f"{'FLAGGED' if m.get('flagged') else 'clean'}{'' if m.get('complete') else ' (incomplete)'}")
    allclean = sum(1 for p in days if not json.loads(p.read_text()).get("flagged"))
    print(f"recorded days: {len(days)}, unflagged: {allclean} (Study AT first look at 40)")
    for mode in ("replay", "paper", "live"):
        n = len(load(STATE / f"journal-{mode}.jsonl"))
        if n:
            print(f"journal {mode}: {n} trades")
    return 0
