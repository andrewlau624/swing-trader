"""Forward shadow for the Systematic Intraday Day Book. NO ORDERS — post-close replay.

Each session it reads the same SIP minute source the live executor uses
(swingtrader.daily.marketdata.minute_history), replays the three configurations, and appends
one record per hypothetical round-trip trade to state/daybook-shadow.jsonl. A daily record per
config is appended too. `report` reads the ledger and prints the forward validation.

Configs shadowed (all no-order):
  PROD  production-equivalent noise leg: QQQ+SMH, live values (lookback 14, step 30, vm 1.0,
        target_vol 0.02, max_lev 3.5, close-weighted VWAP, flat at 15:59)
  B     moderate day book: core QQQ/SMH 0.4 each + conviction TQQQ/SOXL 0.25 each (2x on a
        strong first breakout), same vol/lev/cost as live
  C     high-risk day book: as B but target_vol 0.04, max_lev 7.0 (research-only)

Run:  PYTHONPATH=. python -m swingtrader.daybook.shadow forward [YYYY-MM-DD]
      PYTHONPATH=. python -m swingtrader.daybook.shadow report
      PYTHONPATH=. python -m swingtrader.daybook.shadow forward --source cache --date 2026-06-02
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .signals import DaybookConfig, breakout_strength, noise_bounds, noise_decide, vol_leverage

ROOT = Path(__file__).resolve().parents[2]
LOG_NAME = "daybook-shadow.jsonl"
LEDGER = ROOT / "state" / LOG_NAME
RESEARCH_M1 = ROOT / "data" / "research" / "night" / "m1"

DEC = list(range(30, 361, 30))     # 10:00 .. 15:30
CLOSE_M = 389                      # flatten at the 15:59 print (live flattens 15:57)

CFGS = {
    "PROD": DaybookConfig(core={"QQQ": 0.5, "SMH": 0.5}, conviction={},
                          target_vol=0.02, max_lev=3.5, cost_bps=0.5, close_min=CLOSE_M),
    "B": DaybookConfig(core={"QQQ": 0.4, "SMH": 0.4}, conviction={"TQQQ": 0.25, "SOXL": 0.25},
                       target_vol=0.02, max_lev=3.5, conviction_strength=0.341,
                       conviction_mult=2.0, cost_bps=0.5, close_min=CLOSE_M),
    "C": DaybookConfig(core={"QQQ": 0.4, "SMH": 0.4}, conviction={"TQQQ": 0.25, "SOXL": 0.25},
                       target_vol=0.04, max_lev=7.0, conviction_strength=0.341,
                       conviction_mult=2.0, cost_bps=0.5, close_min=CLOSE_M),
}
SLIP_BPS = 0.5          # assumed adverse fill vs the decision print (measured live ~0)
UNFILL_BP = 5.0         # next-minute adverse move above which the price is "not realistically fillable"


# ---------------------------------------------------------------- data
def _sessions_cache(sym: str, lookback: int, day: pd.Timestamp | None) -> dict:
    """Build {date: {close(390), volume(390), open}} from the research SIP m1 parquets."""
    import glob
    frames = [pd.read_parquet(f) for f in sorted(glob.glob(str(RESEARCH_M1 / f"{sym}_*.parquet")))]
    if not frames:
        return {}
    df = pd.concat(frames)
    t = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert("America/New_York")
    df = df.assign(date=t.dt.tz_localize(None).dt.normalize(), m=t.dt.hour * 60 + t.dt.minute - 570)
    df = df[(df.m >= 0) & (df.m < 390)]
    out = {}
    for d, g in df.groupby("date"):
        if day is not None and d > pd.Timestamp(day):
            continue
        c = np.full(390, np.nan); v = np.zeros(390)
        c[g.m.values] = g.close.values; v[g.m.values] = g.volume.values
        c = pd.Series(c).ffill().values
        out[d] = {"close": c, "volume": v, "open": float(g.sort_values("m").open.iloc[0])}
    return out


def _sessions_alpaca(sym: str, lookback: int) -> dict:
    from swingtrader.daily import marketdata as md
    S = md.minute_history(sym, lookback + 3)
    return {d: dict(close=s["close"], volume=s["volume"], open=s["open"]) for d, s in S.items()}


def sessions_for(sym: str, day: pd.Timestamp, lookback: int, source: str) -> dict:
    S = _sessions_cache(sym, lookback, day) if source == "cache" else _sessions_alpaca(sym, lookback)
    return dict(sorted((d, s) for d, s in S.items() if d <= day))


# ---------------------------------------------------------------- one-instrument replay
def replay_instrument(S: dict, cfg: DaybookConfig, sym: str, w: float, day: pd.Timestamp) -> list[dict]:
    days = [d for d in S if d < day]
    if day not in S or len(days) < 5:
        return []
    hist = days[-cfg.lookback:]
    today = S[day]
    C, V = today["close"], today["volume"]
    openp = today["open"]
    prev_close = S[days[-1]]["close"][-1]
    moves = np.array([np.abs(S[d]["close"] / S[d]["open"] - 1.0) for d in hist])
    sigma = np.nanmean(moves, axis=0)
    ub, lb = noise_bounds(openp, prev_close, sigma)
    pv = np.cumsum(C * V) / np.maximum(np.cumsum(V), 1)
    pv = np.where(np.isfinite(pv), pv, C)
    closes_all = np.array([S[d]["close"][-1] for d in sorted(S) if d <= day])
    lev = vol_leverage(closes_all, cfg.target_vol, cfg.max_lev)
    if lev <= 0:
        return []

    mult = lev * w
    pos, entry_p, entry_m, taken = 0, 0.0, 0, False
    entry_strength = 0.0
    trades: list[dict] = []

    def rec(m_exit, reason):
        sgn = pos
        eff = mult * (cfg.conviction_mult if taken else 1.0)
        e_obs, x_obs = entry_p, float(C[m_exit])
        e_fill = e_obs * (1 + SLIP_BPS * 1e-4) if sgn == 1 else e_obs * (1 - SLIP_BPS * 1e-4)
        x_fill = x_obs * (1 - SLIP_BPS * 1e-4) if sgn == 1 else x_obs * (1 + SLIP_BPS * 1e-4)
        gross = sgn * (x_obs / e_obs - 1)
        net = sgn * (x_fill / e_fill - 1)
        nxt = next_m_price(m_exit)
        unfill = nxt is not None and abs(nxt / x_obs - 1) * 1e4 > UNFILL_BP
        alt = None
        if nxt is not None:
            alt = sgn * (nxt * (1 - SLIP_BPS * 1e-4) / e_fill - 1)
        trades.append(dict(
            entry_ts=str(pd.Timestamp(day) + pd.Timedelta(minutes=570 + entry_m)),
            exit_ts=str(pd.Timestamp(day) + pd.Timedelta(minutes=570 + m_exit)),
            instrument=sym, direction=sgn, entry_minute=entry_m, exit_minute=m_exit,
            intended_entry=round(e_obs, 4), observed_entry=round(e_obs, 4),
            assumed_fill_entry=round(e_fill, 4), intended_exit=round(x_obs, 4),
            observed_exit=round(x_obs, 4), assumed_fill_exit=round(x_fill, 4),
            gross_bp=round(gross * 1e4, 2), slip_bp=SLIP_BPS, net_bp=round(net * 1e4, 2),
            leverage=round(eff, 3), exit_reason=reason,
            strength=entry_strength, vol_state=round(float(np.nanstd(moves[-1])), 5),
            unfillable=bool(unfill), next_min_price=None if nxt is None else round(nxt, 4),
            alt_net_bp=None if alt is None else round(alt * 1e4, 2),
        ))

    def next_m_price(m):
        return float(C[m + 1]) if m + 1 < 390 else None

    for m in DEC:
        p = float(C[m])
        # exits (mirror noise_decide)
        if pos == 1 and p < max(ub[m], pv[m]):
            rec(m, "band/VWAP exit"); pos = 0
        elif pos == -1 and p > min(lb[m], pv[m]):
            rec(m, "band/VWAP exit"); pos = 0
        # entries
        if pos == 0:
            d, stg = breakout_strength(p, ub[m], lb[m], sigma[m])
            if d == 1:
                pos, entry_p, entry_m, entry_strength = 1, p, m, stg
            elif d == -1:
                pos, entry_p, entry_m, entry_strength = -1, p, m, stg
            if d != 0 and sym in cfg.conviction and not taken and stg >= cfg.conviction_strength:
                taken = True
    if pos != 0:
        rec(CLOSE_M, "close flatten")
    return trades


# ---------------------------------------------------------------- day / forward
def replay_day(day: pd.Timestamp, source: str = "cache") -> list[dict]:
    records = []
    for name, cfg in CFGS.items():
        w = {**cfg.core, **cfg.conviction}
        syms = [s for s, x in w.items() if x > 0]
        per: dict[str, list] = {}
        for s in syms:
            S = sessions_for(s, day, cfg.lookback, source)
            per[s] = replay_instrument(S, cfg, s, w[s], day)
        daily_net = 0.0
        for s in syms:
            for t in per[s]:
                daily_net += t["net_bp"] * 1e-4 * t["leverage"]
                records.append({"kind": "trade", "config": name, "date": str(day.date()), **t})
        records.append({"kind": "daily", "config": name, "date": str(day.date()),
                        "net_return": round(daily_net, 6), "trades": sum(len(v) for v in per.values())})
    return records


def append(records: list[dict]) -> int:
    if not records:
        return 0
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as f:
        for r in records:
            f.write(json.dumps(r, default=str) + "\n")
    return len(records)


def forward(day: pd.Timestamp | None = None, source: str | None = None) -> list[dict]:
    source = source or "alpaca"
    if day is None:
        # the timer fires pre-open: replay the latest COMPLETE session, never "today"
        S = sessions_for("QQQ", pd.Timestamp(dt.date.today()), 14, source)
        if not S:
            print("daybook-shadow: no QQQ sessions available"); return []
        day = max(S)
    day = pd.Timestamp(day)
    if day not in sessions_for("QQQ", day, 14, source):
        print(f"daybook-shadow: no complete QQQ session for {day.date()}, nothing logged"); return []
    recs = replay_day(day, source=source)
    # idempotent: skip if this date+config already logged
    seen = {(r.get("date"), r.get("config")) for r in _read() if r.get("kind") == "daily"}
    fresh = [r for r in recs if (r.get("date"), r.get("config")) not in seen]
    n = append(fresh)
    print(f"daybook-shadow: {day.date()} source={source} appended {n} records "
          f"({sum(1 for r in fresh if r['kind']=='trade')} trades)")
    return fresh


def _read() -> list[dict]:
    if not LEDGER.exists():
        return []
    out = []
    for ln in LEDGER.read_text().splitlines():
        try:
            out.append(json.loads(ln))
        except ValueError:
            pass
    return out


# ---------------------------------------------------------------- report
def report() -> str:
    rows = _read()
    trades = [r for r in rows if r.get("kind") == "trade"]
    dailies = [r for r in rows if r.get("kind") == "daily"]
    lines = [f"DAYBOOK FORWARD SHADOW — {len(dailies)} config-days, {len(trades)} hypothetical trades"]
    if not trades:
        print("\n".join(lines)); return "\n".join(lines)
    df = pd.DataFrame(trades)
    dd = pd.DataFrame(dailies)
    for name in CFGS:
        t = df[df["config"] == name]
        d = dd[dd["config"] == name]
        if len(d) == 0:
            continue
        d = d.copy(); d["date"] = pd.to_datetime(d["date"]); d = d.sort_values("date")
        r = d["net_return"]
        eq = (1 + r).cumprod()
        dd_ = (eq / eq.cummax() - 1).min()
        be = r[r != 0]
        lines.append(
            f"\n[{name}] days {len(d)} active {(r != 0).sum()}  "
            f"mean {r.mean()*1e4:+.2f}bp/day  t {r.mean()/(r.std(ddof=1)/np.sqrt(len(r))):+.2f}  "
            f"cum {eq.iloc[-1]-1:+.2%}  maxDD {dd_:.1%}  win {(be>0).mean()*100 if len(be) else float('nan'):.0f}%")
        if len(t):
            lines.append(
                f"     trades {len(t)}  gross {t['gross_bp'].mean():+.1f}bp  net {t['net_bp'].mean():+.1f}bp  "
                f"win {(t['net_bp']>0).mean()*100:.0f}%  unfillable {int(t['unfillable'].sum())}")
    print("\n".join(lines)); return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["forward", "report"])
    ap.add_argument("date", nargs="?", default=None)
    ap.add_argument("--source", default=None, choices=[None, "alpaca", "cache"])
    a = ap.parse_args()
    if a.cmd == "forward":
        forward(a.date, a.source)
    else:
        report()
