"""Study Lab-AU: 5-minute ORB on Stocks in Play (daytrade/plans/orb_in_play.md, round1_prose.md Lab Round 19).
The lab's strategy code through the lab's engine on SIP minute history, 2022-01-03 .. 2026-09-30.

Reads, and why each is regular-hours:
- SIP daily bars (raw), completed sessions BEFORE the trade date (regular sessions before 2026-12-06):
  ATR(14), 14-day average volume, previous close. Never today's daily bar.
- SIP minute bars 09:30-09:34 for every loosely eligible stock (the opening range and its volume,
  and the 14-session RVOL history), then the full regular session (from the calendar) for the day's
  top 20. All inside the regular session.

  python -m daytrade.research.au_replay fetch     # resumable
  python -m daytrade.research.au_replay run
"""
from __future__ import annotations

import datetime as dt
import json
import math
import pickle
import random
import sys
import time
from collections import defaultdict, deque

import numpy as np
import pandas as pd

from ..engine import Engine
from ..events import DayInfo
from ..fills import SimBroker
from ..risk import AccountModel
from ..session import session_times
from ..settings import DATA, Limits
from ..strategies import orb_in_play as S
from . import as_replay as A

OUT = DATA / "research" / "au"
START, END, SPLIT = A.START, A.END, A.SPLIT
WARMUP = dt.date(2021, 11, 15)
LOOSE = dict(price=4.0, vol=700_000, atr=0.35)     # superset kept for the RVOL history
log = A.log


def daily_ohlc(symbols) -> pd.DataFrame:
    p = OUT / "daily_ohlc.parquet"
    if p.exists():
        return pd.read_parquet(p)
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.daily.marketdata import trade_date
    data, _ = A._clients()
    parts = []
    for i in range(0, len(symbols), 400):
        for attempt in range(4):
            try:
                df = data.get_stock_bars(StockBarsRequest(
                    symbol_or_symbols=symbols[i:i + 400], timeframe=TimeFrame.Day,
                    start=pd.Timestamp(WARMUP - dt.timedelta(days=40), tz="UTC"),
                    end=pd.Timestamp(END + dt.timedelta(days=1), tz="UTC"), feed="sip", adjustment="raw")).df
                break
            except Exception as exc:
                log(f"daily retry {attempt}: {type(exc).__name__}"); time.sleep(10)
        else:
            continue
        if df is not None and len(df):
            parts.append(df.reset_index()[["symbol", "timestamp", "open", "high", "low", "close", "volume"]])
        log(f"daily {min(i + 400, len(symbols))}/{len(symbols)}")
    d = pd.concat(parts)
    d["date"] = trade_date(d["timestamp"])
    d = d.drop(columns="timestamp").sort_values(["symbol", "date"]).reset_index(drop=True)
    OUT.mkdir(parents=True, exist_ok=True)
    d.to_parquet(p)
    return d


def prior_stats(d: pd.DataFrame) -> dict:
    """{date: {sym: (prev_close, atr14, avgvol14)}} from sessions strictly before each date."""
    p = OUT / "prior.pkl"
    if p.exists():
        return pickle.loads(p.read_bytes())
    out = defaultdict(dict)
    for sym, g in d.groupby("symbol", sort=False):
        g = g.reset_index(drop=True)
        pc = g["close"].shift(1)
        tr = pd.concat([g["high"] - g["low"], (g["high"] - pc).abs(), (g["low"] - pc).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14, min_periods=14).mean().shift(1)
        vol = g["volume"].rolling(14, min_periods=14).mean().shift(1)
        m = (pc > LOOSE["price"]) & (vol >= LOOSE["vol"]) & (atr > LOOSE["atr"])
        m &= (g["date"] >= pd.Timestamp(WARMUP)) & (g["date"] <= pd.Timestamp(END))
        for i in np.flatnonzero(m.values):
            out[g["date"].iat[i].date()][sym] = (float(pc.iat[i]), float(atr.iat[i]), float(vol.iat[i]))
    p.write_bytes(pickle.dumps(dict(out)))
    return dict(out)


def fetch() -> None:
    syms = A.universe(); log(f"universe {len(syms)}")
    d = daily_ohlc(syms); log(f"daily rows {len(d):,}")
    prior = prior_stats(d); log(f"days with loose-eligible names: {len(prior)}")
    from swingtrader.daily.brokers import regular_sessions
    cal = regular_sessions(WARMUP, END + dt.timedelta(days=7))
    (OUT / "sessions.pkl").write_bytes(pickle.dumps(cal))
    (OUT / "or").mkdir(parents=True, exist_ok=True); (OUT / "days").mkdir(parents=True, exist_ok=True)
    data, _ = A._clients()
    hist: dict[str, deque] = defaultdict(lambda: deque(maxlen=14))
    for o, c in cal:
        day = o.date()
        if day > END:
            break
        names = sorted(prior.get(day, {}))
        fo = OUT / "or" / f"{day}.pkl"
        if fo.exists():
            orr = pickle.loads(fo.read_bytes())
        else:
            parts = [A._minutes(data, names[i:i + 1000], o, o + dt.timedelta(minutes=5))
                     for i in range(0, len(names), 1000)] if names else []
            pre = pd.concat([p for p in parts if len(p)]) if any(len(p) for p in parts) else pd.DataFrame()
            orr = {}
            if len(pre):
                pre["m"] = (pre["timestamp"].dt.tz_convert(A.ET) - o).dt.total_seconds() // 60
                for sym, g in pre[(pre.m >= 0) & (pre.m < 5)].groupby("symbol"):
                    g = g.sort_values("m")
                    orr[sym] = (int(len(g)), float(g.volume.sum()), float(g.open.iat[0]) if g.m.iat[0] == 0 else 0.0)
            fo.write_bytes(pickle.dumps(orr))
        fd = OUT / "days" / f"{day}.pkl"
        if day >= START and not fd.exists():
            info, ranked = {}, []
            for sym, (pc, atr, vol) in prior.get(day, {}).items():
                h = hist.get(sym)
                if sym not in orr or not h or len(h) < 10:
                    continue
                nbar, orv, op = orr[sym]
                avg = sum(h) / len(h)
                info[sym] = DayInfo(sym, pc, 0.0, 0.0, atr14=atr, avg_volume14=vol, or_volume_avg14=avg)
                # the strategy's selection, applied here only to limit the download
                if nbar == 5 and op > S.OPEN_MIN and vol >= S.AVG_VOL_MIN and atr > S.ATR_MIN and avg > 0 \
                        and orv / avg >= S.RVOL_MIN:
                    ranked.append((orv / avg, sym))
            top = [s for _, s in sorted(ranked, reverse=True)[:S.TOP_N]]
            bars = A._minutes(data, top, o, c) if top else pd.DataFrame()
            fd.write_bytes(pickle.dumps({"info": {s: info[s] for s in top}, "bars": bars, "open": o, "close": c}))
            log(f"{day}: {len(names)} loose, {len(orr)} with OR bars, {len(ranked)} in play, top {len(top)}")
        for sym, (nbar, orv, _) in orr.items():
            hist[sym].append(orv)


# ------------------------------------------------------------------ replay
def load_days():
    cal = pickle.loads((OUT / "sessions.pkl").read_bytes())
    for o, c in cal:
        f = OUT / "days" / f"{o.date()}.pkl"
        if START <= o.date() <= END and f.exists():
            yield o.date(), pickle.loads(f.read_bytes()), cal


def replay(long_only: bool, cost_bp: float, equity=1e7, kind="margin", limits=None, keep=False):
    stats = limits is None
    lim = limits or Limits(max_positions=99, daily_loss_pct=1e9, max_position_pct=1e9, intraday_mult=1e9)
    acct = AccountModel(equity, kind, lim.intraday_mult)
    trades, events, keep_by = [], [], {}
    days = list(load_days())
    for i, (day, rec, cal) in enumerate(days):
        st = session_times(day, cal, lim)
        if stats:   # per-trade statistics: a fresh account each day, so losses never shrink later trades
            acct = AccountModel(equity, kind, lim.intraday_mult)
        evs = A.day_events(rec)
        nxt = days[i + 1][0] if i + 1 < len(days) else day + dt.timedelta(days=1)
        eng = Engine([S.OrbInPlay(long_only=long_only)], SimBroker(latency_s=1.0, cost_bp=cost_bp),
                     equity=acct.equity, session=st, day_info=rec["info"], limits=lim, account=acct,
                     settle_day=nxt, halt_path=OUT / "HALT-never")
        eng.run(evs)
        trades += eng.trades; events += eng.events
        if keep:
            keep_by[day] = (evs, st, rec["info"])
    return trades, events, keep_by, len(days)


def sim_dir(bars, hi, lo, atr, direction: int, cost: float, st) -> float | None:
    """One ORB trade with the SimBroker's rules: stop entry at hi/lo (open if it gaps through),
    stop 10% ATR from the trigger (same bar after entry: at the stop price), flat by close-5."""
    trig = hi if direction > 0 else lo
    stop = round(trig - direction * S.STOP_ATR * atr, 2)
    entry = None
    after = [b for b in bars if b.start >= st.at("09:35")]
    for j, b in enumerate(after):
        if entry is None:
            if b.ts > st.entry_cutoff:
                return None
            hit = b.high >= trig if direction > 0 else b.low <= trig
            if not hit:
                continue
            gap = b.open >= trig if direction > 0 else b.open <= trig
            px = b.open if gap else trig
            entry = px * (1 + direction * cost)
            if (b.low <= stop if direction > 0 else b.high >= stop):
                return direction * (stop * (1 - direction * cost) / entry - 1) * 1e4
            continue
        if b.ts > st.flat_by:
            return direction * (b.open * (1 - direction * cost) / entry - 1) * 1e4
        if (b.low <= stop if direction > 0 else b.high >= stop):
            gp = b.open <= stop if direction > 0 else b.open >= stop
            px = b.open if gp else stop
            return direction * (px * (1 - direction * cost) / entry - 1) * 1e4
    if entry is None:
        return None
    return direction * (after[-1].close * (1 - direction * cost) / entry - 1) * 1e4


def picks_outcomes(keep_by, cost_bp):
    """Per top-20 stock-day with a non-flat candle: (rule direction, long outcome, short outcome)."""
    cost = cost_bp / 1e4
    rows = []
    for day, (evs, st, info) in keep_by.items():
        by = defaultdict(list)
        for b in evs:
            by[b.sym].append(b)
        for sym, bs in by.items():
            orb = [b for b in bs if b.start < st.at("09:35")]
            if len(orb) < 5 or sym not in info:
                continue
            o, c = orb[0].open, orb[4].close
            if c == o:
                continue
            hi, lo = max(b.high for b in orb[:5]), min(b.low for b in orb[:5])
            atr = info[sym].atr14
            rows.append((day, sym, 1 if c > o else -1, sim_dir(bs, hi, lo, atr, 1, cost, st),
                         sim_dir(bs, hi, lo, atr, -1, cost, st)))
    return rows


def placebo(rows, actual_mean, long_only, draws=1000, seed=11):
    rng = random.Random(seed)
    means = []
    for _ in range(draws):
        xs = []
        for _, _, _, lo_, sh in rows:
            if long_only:
                if rng.random() < 0.5 and lo_ is not None:
                    xs.append(lo_)
            else:
                v = lo_ if rng.random() < 0.5 else sh
                if v is not None:
                    xs.append(v)
        means.append(np.mean(xs))
    return float(np.mean(np.array(means) < actual_mean) * 100), float(np.mean(means))


def dollars(long_only, cost_bp):
    out = {}
    runs = [("$2.3k cash", 2_300, "cash", Limits()), ("$2.3k margin", 2_300, "margin", Limits()),
            ("$10k margin", 10_000, "margin", Limits()), ("$25k margin", 25_000, "margin", Limits()),
            ("$25k paper sizing", 25_000, "margin",
             Limits(risk_per_trade_pct=0.01, max_positions=20, max_position_pct=4.0, daily_loss_pct=1e9))]
    for label, eq, kind, lim in runs:
        tr, ev, _, n = replay(long_only, cost_bp, equity=eq, kind=kind, limits=lim)
        pnl = sum(t["pnl"] for t in tr)
        out[label] = {"trades": len(tr), "per_day": pnl / n, "end_equity": eq + pnl,
                      "cagr": ((eq + pnl) / eq) ** (252 / n) - 1 if eq + pnl > 0 else -1.0}
    return out


def run(dollars_too: bool = True) -> None:
    res = {}
    n1 = sum(1 for d, _, _ in load_days() if d < SPLIT)
    for name, lo in (("Lab-AU1", False), ("Lab-AU2", True)):
        base, _, keep_by, n = replay(lo, 5.0, keep=True)
        two, _, _, _ = replay(lo, 10.0)
        r = {"1x": {h: A.summary(x, m) for h, x, m in (("all", base, n), ("h1", A.half(base, 1), n1),
                                                        ("h2", A.half(base, 2), n - n1))},
             "2x": {h: A.summary(x, m) for h, x, m in (("all", two, n), ("h1", A.half(two, 1), n1),
                                                        ("h2", A.half(two, 2), n - n1))}}
        rows = picks_outcomes(keep_by, 5.0)
        actual = float(np.mean([t["net_bp"] for t in base])) if base else float("nan")
        # consistency: the simulator in the rule's direction vs the engine
        sim_rule = [lo_ if d > 0 else sh for _, _, d, lo_, sh in rows if (d > 0 or not lo)]
        sim_rule = [x for x in sim_rule if x is not None]
        r["sim_rule_mean_bp"] = float(np.mean(sim_rule)) if sim_rule else None
        r["placebo_pct"], r["placebo_mean_bp"] = placebo(rows, actual, lo)
        r["by_side_1x"] = {s: float(np.mean([t["net_bp"] for t in base if t["side"] == s]))
                           for s in ("long", "short") if any(t["side"] == s for t in base)}
        a2 = r["2x"]
        r["verdict"] = ("PASS (to paper)" if a2["h1"]["mean_bp"] > 0 and a2["h2"]["mean_bp"] > 0
                        and r["1x"]["all"]["t_day"] >= 2.0 and r["placebo_pct"] >= 95 else "DEAD")
        if dollars_too:
            r["dollars_1x"] = dollars(lo, 5.0)
            r["dollars_2x"] = dollars(lo, 10.0)
        res[name] = r
        pd.DataFrame(base).to_csv(OUT / f"trades_{name}_1x.csv", index=False)
        print(name, json.dumps({k: r[k] for k in ("verdict", "placebo_pct", "sim_rule_mean_bp", "by_side_1x")}),
              flush=True)
    res["n_days"], res["n_h1"] = n, n1
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    {"fetch": fetch, "run": run}[sys.argv[1]]()
