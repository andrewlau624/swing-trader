"""Study Lab-AS: gap + premarket volume, pullback to VWAP, reclaim (daytrade/plans/gap_vwap_reclaim.md,
round1_prose.md Round 18). Replays the lab's strategy code through the lab's engine on SIP minute
history, 2022-01-03 .. 2026-09-30.

Data, and why each read is regular-hours or not:
- SIP daily bars (raw): previous REGULAR close and the 20-day dollar volume, from completed daily
  bars before the trade date (before 2026-12-06 a vendor daily bar is the regular session). The
  daily OPEN is used only as a loose prefilter (|gap| >= 3%); the decision uses the 09:30 minute.
- SIP minute bars 04:00-09:29 ET: premarket volume, the plan's one pre-session input.
- SIP minute bars inside the calendar's regular session (09:30 to the close, half days included):
  every price the strategy and the fill model see.
Universe: Alpaca US equities on major exchanges, active AND inactive (fewer survivors-only names),
common stock by symbol and name filter. Cached under data/daytrade/research/.

  python -m daytrade.research.as_replay fetch     # data (~30-60 min, resumable)
  python -m daytrade.research.as_replay run       # the registered test + reports
"""
from __future__ import annotations

import datetime as dt
import json
import math
import pickle
import random
import re
import sys
import time
from collections import defaultdict
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from ..engine import Engine
from ..events import TICK, Bar, DayInfo
from ..fills import SimBroker
from ..risk import AccountModel
from ..session import session_times
from ..settings import DATA, ET, Limits
from ..strategies import gap_vwap_reclaim as G

OUT = DATA / "research" / "as"
START, END = dt.date(2022, 1, 3), dt.date(2026, 9, 30)
SPLIT = dt.date(2024, 6, 1)
PREFILTER_GAP = 0.03
NOT_COMMON = re.compile(r"\b(ETF|ETN|ETP|FUND|TRUST|ISHARES|PROSHARES|DIREXION|SPDR|INVESCO|VANGUARD|"
                        r"WISDOMTREE|GLOBAL X|NOTES?|WARRANTS?|UNITS?|RIGHTS?|2X|3X|LEVERAGED|INVERSE|"
                        r"ACQUISITION CORP|DEPOSITARY SHARES REPRESENTING)\b", re.I)
TZ = ZoneInfo(ET)


def log(msg):
    print(f"{dt.datetime.now():%H:%M:%S} {msg}", flush=True)


def _clients():
    from swingtrader.data import _clients as c
    return c()


# ------------------------------------------------------------------ data
def universe() -> list[str]:
    p = OUT / "universe.json"
    if p.exists():
        return json.loads(p.read_text())
    from alpaca.trading.enums import AssetClass, AssetStatus
    from alpaca.trading.requests import GetAssetsRequest
    from swingtrader.universe import MAJOR, valid_symbol
    _, tc = _clients()
    keep = set()
    for status in (AssetStatus.ACTIVE, AssetStatus.INACTIVE):
        for a in tc.get_all_assets(GetAssetsRequest(asset_class=AssetClass.US_EQUITY, status=status)):
            ex = str(getattr(a, "exchange", "")).split(".")[-1]
            name = str(getattr(a, "name", "") or "")
            if ex in MAJOR and valid_symbol(a.symbol) and "." not in a.symbol and not NOT_COMMON.search(name):
                keep.add(a.symbol)
    OUT.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(sorted(keep)))
    return sorted(keep)


def daily(symbols: list[str]) -> pd.DataFrame:
    p = OUT / "daily.parquet"
    if p.exists():
        return pd.read_parquet(p)
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    data, _ = _clients()
    parts = []
    for i in range(0, len(symbols), 400):
        chunk = symbols[i:i + 400]
        for attempt in range(4):
            try:
                df = data.get_stock_bars(StockBarsRequest(
                    symbol_or_symbols=chunk, timeframe=TimeFrame.Day,
                    start=pd.Timestamp(START - dt.timedelta(days=45), tz="UTC"),
                    end=pd.Timestamp(END + dt.timedelta(days=1), tz="UTC"),
                    feed="sip", adjustment="raw")).df
                break
            except Exception as exc:
                log(f"daily chunk {i} retry {attempt}: {type(exc).__name__}"); time.sleep(10)
        else:
            continue
        if df is not None and len(df):
            df = df.reset_index()[["symbol", "timestamp", "open", "close", "volume"]]
            parts.append(df)
        log(f"daily {i + len(chunk)}/{len(symbols)}")
    d = pd.concat(parts)
    from swingtrader.daily.marketdata import trade_date
    d["date"] = trade_date(d["timestamp"])
    d = d.drop(columns="timestamp").sort_values(["symbol", "date"])
    d.to_parquet(p)
    return d


def candidates(d: pd.DataFrame) -> dict:
    """{date: [(sym, prev_close, adv20)]} from bars BEFORE each date, prefiltered by the daily open."""
    p = OUT / "candidates.pkl"
    if p.exists():
        return pickle.loads(p.read_bytes())
    out = defaultdict(list)
    for sym, g in d.groupby("symbol", sort=False):
        g = g.reset_index(drop=True)
        pc = g["close"].shift(1)
        adv = (g["close"] * g["volume"]).shift(1).rolling(20, min_periods=20).mean()
        gap = g["open"] / pc - 1
        m = (pc >= G.PRICE_MIN) & (pc <= G.PRICE_MAX) & (adv >= G.ADV_MIN) & (gap.abs() >= PREFILTER_GAP)
        m &= (g["date"] >= pd.Timestamp(START)) & (g["date"] <= pd.Timestamp(END))
        for i in np.flatnonzero(m.values):
            out[g["date"].iat[i].date()].append((sym, float(pc.iat[i]), float(adv.iat[i])))
    p.write_bytes(pickle.dumps(dict(out)))
    return dict(out)


def _minutes(data, syms, start, end) -> pd.DataFrame:
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    for attempt in range(5):
        try:
            df = data.get_stock_bars(StockBarsRequest(
                symbol_or_symbols=syms, timeframe=TimeFrame.Minute, start=start.astimezone(dt.timezone.utc),
                end=end.astimezone(dt.timezone.utc), feed="sip", adjustment="raw")).df
            return df.reset_index() if df is not None and len(df) else pd.DataFrame()
        except Exception as exc:
            log(f"minutes retry {attempt}: {type(exc).__name__} {str(exc)[:80]}"); time.sleep(5 * (attempt + 1))
    raise RuntimeError("minute bars unavailable")


def fetch() -> None:
    syms = universe(); log(f"universe {len(syms)} common stocks (active + inactive)")
    d = daily(syms); log(f"daily rows {len(d):,}")
    cand = candidates(d); log(f"candidate days {len(cand)}, symbol-days {sum(map(len, cand.values())):,}")
    from swingtrader.daily.brokers import regular_sessions
    cal = regular_sessions(START, END + dt.timedelta(days=7))
    (OUT / "sessions.pkl").write_bytes(pickle.dumps(cal))
    sel_dir = OUT / "days"; sel_dir.mkdir(parents=True, exist_ok=True)
    data, _ = _clients()
    for o, c in cal:
        day = o.date()
        f = sel_dir / f"{day}.pkl"
        if day > END or f.exists():
            continue
        rows = cand.get(day, [])
        info, bars = {}, pd.DataFrame()
        if rows:
            names = [r[0] for r in rows]
            pre = pd.concat([_minutes(data, names[i:i + 200], o.replace(hour=4, minute=0),
                                      o + dt.timedelta(minutes=1)) for i in range(0, len(names), 200)])
            if len(pre):
                t = pre["timestamp"].dt.tz_convert(ET)
                pm = pre[t < o].groupby("symbol")["volume"].sum()
                first = pre[(t >= o) & (t < o + dt.timedelta(minutes=1))].set_index("symbol")["open"]
                for s, pc, adv in rows:
                    if s in first.index:
                        info[s] = DayInfo(s, pc, adv, float(pm.get(s, 0.0)))
                # the strategy's own selection, applied here only to limit what is downloaded
                ok = [(info[s].premarket_volume, s) for s in info
                      if first[s] / info[s].prev_close - 1 >= G.GAP_MIN and info[s].premarket_volume >= G.PREMARKET_MIN]
                top = [s for _, s in sorted(ok, reverse=True)[:G.CAP]]
                if top:
                    bars = _minutes(data, top, o, c)
        f.write_bytes(pickle.dumps({"info": info, "bars": bars, "open": o, "close": c}))
        log(f"{day}: {len(rows)} prefiltered, {len(info)} with a 09:30 bar, bars for "
            f"{bars['symbol'].nunique() if len(bars) else 0}")


# ------------------------------------------------------------------ replay
def day_events(rec) -> list[Bar]:
    b = rec["bars"]
    if b is None or not len(b):
        return []
    o, c = rec["open"], rec["close"]
    out = []
    for r in b.itertuples(index=False):
        s = r.timestamp.tz_convert(TZ).to_pydatetime()
        if o <= s < c:                       # regular session only, from the calendar
            out.append(Bar(s + dt.timedelta(minutes=1), r.symbol, float(r.open), float(r.high), float(r.low),
                           float(r.close), float(r.volume), s))
    out.sort(key=lambda x: (x.ts, x.sym))
    return out


def load_days():
    cal = pickle.loads((OUT / "sessions.pkl").read_bytes())
    for o, c in cal:
        f = OUT / "days" / f"{o.date()}.pkl"
        if o.date() <= END and f.exists():
            yield o.date(), pickle.loads(f.read_bytes()), cal


def replay(latency: float, cost_bp: float, equity: float = 1e7, kind: str = "margin",
           limits: Limits | None = None, keep_bars: bool = False):
    """Every day through the engine. Default: a huge margin account and no position cap, so the
    per-trade statistics are not shaped by sizing. Pass a small equity for the $/day runs."""
    # per-trade statistics: no position cap and no daily loss limit (a sizing rule, applied in the
    # $/day runs, which use the lab's default limits)
    stats = limits is None
    lim = limits or Limits(max_positions=99, daily_loss_pct=1e9)
    acct = AccountModel(equity, kind, lim.intraday_mult)
    trades, events, bars_by = [], [], {}
    days = list(load_days())
    for i, (day, rec, cal) in enumerate(days):
        st = session_times(day, cal, lim)
        if stats:   # per-trade statistics: a fresh account each day, so losses never shrink later trades
            acct = AccountModel(equity, kind, lim.intraday_mult)
        evs = day_events(rec)
        nxt = days[i + 1][0] if i + 1 < len(days) else day + dt.timedelta(days=1)
        eng = Engine([G.GapVwapReclaim()], SimBroker(latency_s=latency, cost_bp=cost_bp), equity=acct.equity,
                     session=st, day_info=rec["info"], limits=lim, account=acct, settle_day=nxt,
                     halt_path=OUT / "HALT-never")
        eng.run(evs)
        trades += eng.trades
        events += eng.events
        if keep_bars and eng.trades:
            bars_by[day] = (evs, st.flat_by)
    return trades, events, bars_by, len(days)


# ------------------------------------------------------------------ stats
def clustered_t(trades) -> float:
    x = np.array([t["net_bp"] for t in trades])
    if len(x) < 3:
        return float("nan")
    m = x.mean()
    by = defaultdict(float)
    for t in trades:
        by[t["day"]] += t["net_bp"] - m
    se = math.sqrt(sum(v * v for v in by.values())) / len(x)
    return m / se if se > 0 else float("nan")


def half(trades, h):
    return [t for t in trades if (dt.date.fromisoformat(t["day"]) < SPLIT) == (h == 1)]


def summary(trades, n_days) -> dict:
    x = [t["net_bp"] for t in trades]
    return {"n": len(x), "per_day": len(x) / n_days if n_days else 0,
            "mean_bp": float(np.mean(x)) if x else float("nan"),
            "median_bp": float(np.median(x)) if x else float("nan"),
            "win": float(np.mean([v > 0 for v in x])) if x else float("nan"),
            "mean_r": float(np.mean([t.get("r", 0) for t in trades])) if x else float("nan"),
            "t_day": clustered_t(trades),
            "exits": dict(pd.Series([t.get("exit_reason", "") for t in trades]).value_counts()) if x else {}}


def sim_one(bars: list[Bar], i0: int, stop_pct: float, cost: float, flat_by,
            stop: float | None = None, target: float | None = None) -> float | None:
    """Placebo trade: market buy at bar i0's open (the 1s fill), stop at stop_pct below, 2R target,
    same fill rules as SimBroker (stop first; gap-through; target through by a tick; flat by)."""
    entry = bars[i0].open * (1 + cost)
    if stop is None:
        stop = round(bars[i0].open * (1 - stop_pct) - TICK, 2)
        target = round(bars[i0].open + G.TARGET_R * (bars[i0].open - stop), 2)
    for b in bars[i0:]:
        if b.ts > flat_by:
            # the engine's flatten fills at the next bar's open; approximate with this bar's open
            return (b.open * (1 - cost) / entry - 1) * 1e4
        if b.low <= stop:
            px = b.open if b.open <= stop else stop
            return (px * (1 - cost) / entry - 1) * 1e4
        if b.high >= target + TICK:
            return (target / entry - 1) * 1e4
    return (bars[-1].close * (1 - cost) / entry - 1) * 1e4


def placebo(trades, bars_by, cost_bp: float, draws: int = 1000, seed: int = 7) -> tuple[float, float]:
    """Same symbol-days, random entry minute (signal bar ending 09:36-11:30), same % stop and 2R."""
    rng = random.Random(seed)
    cost = cost_bp / 1e4
    outcomes = []
    for t in trades:
        day = dt.date.fromisoformat(t["day"])
        evs, flat_by = bars_by[day]
        bars = [b for b in evs if b.sym == t["sym"]]
        st_open = bars[0].start.replace(hour=9, minute=30)
        stop_pct = (t["entry_px"] / (1 + cost) - t["stop"]) / (t["entry_px"] / (1 + cost))
        lo, hi = st_open.replace(minute=36), st_open.replace(hour=11, minute=30)
        idx = [i + 1 for i, b in enumerate(bars[:-1]) if lo <= b.ts <= hi]
        outcomes.append([sim_one(bars, i, max(stop_pct, 0.001), cost, flat_by) for i in idx] or [0.0])
    means = [np.mean([rng.choice(o) for o in outcomes]) for _ in range(draws)]
    actual = np.mean([t["net_bp"] for t in trades])
    return float(np.mean(np.array(means) < actual) * 100), float(np.mean(means))


def dollars(latency=1.0, cost_bp=10.0) -> dict:
    """$/day through the risk layer, carrying the account across days (default lab limits)."""
    out = {}
    for label, eq, kind in (("$2.3k cash", 2_300, "cash"), ("$2.3k margin", 2_300, "margin"),
                            ("$10k margin", 10_000, "margin"), ("$25k margin", 25_000, "margin")):
        tr, ev, _, n = replay(latency, cost_bp, equity=eq, kind=kind, limits=Limits())
        pnl = sum(t["pnl"] for t in tr)
        out[label] = {"trades": len(tr), "pnl": pnl, "per_day": pnl / n, "end_equity": eq + pnl,
                      "cagr": ((eq + pnl) / eq) ** (252 / n) - 1 if eq + pnl > 0 else -1.0,
                      "refused": sum(1 for e in ev if e["kind"] == "rejected")}
    return out


def run() -> None:
    res = {}
    base, _, bars_by, n_days = replay(1.0, 10.0, keep_bars=True)
    n1 = sum(1 for d, _, _ in load_days() if d < SPLIT); n2 = n_days - n1
    res["1x_1s"] = {"all": summary(base, n_days), "h1": summary(half(base, 1), n1), "h2": summary(half(base, 2), n2)}
    for name, lat, cost in (("2x_1s", 1.0, 20.0), ("1x_0s", 0.0, 10.0), ("1x_60s", 60.0, 10.0)):
        tr, _, _, _ = replay(lat, cost)
        res[name] = {"all": summary(tr, n_days), "h1": summary(half(tr, 1), n1), "h2": summary(half(tr, 2), n2)}
    pct, pmean = placebo(base, bars_by, 10.0) if base else (float("nan"), float("nan"))
    res["placebo"] = {"pct": pct, "mean_bp": pmean}
    # consistency: the placebo simulator on the rule's own entries should reproduce the engine
    chk = []
    for t in base[:300]:
        day = dt.date.fromisoformat(t["day"])
        evs, flat_by = bars_by[day]
        bars = [b for b in evs if b.sym == t["sym"]]
        i0 = next((i for i, b in enumerate(bars) if b.start >= dt.datetime.fromisoformat(t["entry_ts"])), None)
        if i0 is not None:
            chk.append(sim_one(bars, i0, 0.0, 0.001, flat_by, t["stop"], t["target"]) - t["net_bp"])
    res["sim_vs_engine_bp"] = {"n": len(chk), "mean_abs": float(np.mean(np.abs(chk))) if chk else None}
    res["dollars_1x"] = dollars(1.0, 10.0)
    res["dollars_2x"] = dollars(1.0, 20.0)
    a2 = res["2x_1s"]
    passed = (a2["h1"]["mean_bp"] > 0 and a2["h2"]["mean_bp"] > 0 and res["1x_1s"]["all"]["t_day"] >= 2.0
              and pct >= 95)
    res["verdict"] = "PASS (to paper)" if passed else "DEAD"
    res["n_days"], res["n_h1"], res["n_h2"] = n_days, n1, n2
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))
    pd.DataFrame(base).to_csv(OUT / "trades_1x_1s.csv", index=False)
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    {"fetch": fetch, "run": run}[sys.argv[1]]()
