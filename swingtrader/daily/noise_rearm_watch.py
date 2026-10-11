"""Intraday (noise) leg re-arm watch: logs, never orders, never flips a switch.

`daily.daytrade_mode` is "off" (user 2026-10-11: 2026 YTD Sharpe -0.7..-1.0, live 7 trips -14bp; NOISE-GATE N 934 found no
fix, NOISE-DIAG closed the fix space). The accepted re-arm rule is "only on a positive 60-session replay". This module reads
that rule weekly so it is not forgotten: the PROD daybook rule (swingtrader.daybook.shadow.replay_instrument, the live
code's own replay) on the last WINDOW complete sessions of SIP minute bars for QQQ + SMH (weights .5/.5), fills one 30-min
bar late (as live does), 0.5bp per fill (measured live ~0). One row per week to state/noise-rearm.jsonl.

POSITIVE (frozen 2026-10-11, no tuning): >= MIN_TRADES trades in the window, annualised daily-P&L Sharpe >= SHARPE_MIN at
COST_BP per fill, and mean net per trade > 0 at SHOCK_BP per fill (the cost shock). A positive row is a re-arm CANDIDATE
for the user; switching daytrade_mode back to auto is never automatic. Not a study (no N): it is the agreed decision rule
applied forward, on the same replay that produced the off decision (research/sim/noise_recent.py).
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

LOG_NAME = "noise-rearm.jsonl"
WINDOW = 60              # complete sessions
LAG = 30                 # minutes from decision print to fill (live is one bar late)
COST_BP = 0.5            # per fill
SHOCK_BP = 2.0           # per fill, the cost shock the mean must survive
MIN_TRADES = 30
SHARPE_MIN = 0.5
EVERY_DAYS = 6           # at most one row a week


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for ln in path.read_text().splitlines():
        try:
            out.append(json.loads(ln))
        except ValueError:
            continue
    return out


def replay(S: dict[str, dict], cfg, window: int = WINDOW, lag: int = LAG) -> tuple[pd.DataFrame, list]:
    """Trades (bp gross per trade, leverage) over the last `window` sessions common to every core instrument."""
    from swingtrader.daybook import shadow as sh
    days = sorted(set.intersection(*[set(S[s]) for s in cfg.core]))
    use = days[-window:]
    rows = []
    for sym, w in cfg.core.items():
        for d in use:
            for t in sh.replay_instrument(S[sym], cfg, sym, w, d, lag=lag):
                rows.append(dict(date=pd.Timestamp(d), sym=sym, dir=t["direction"], gross=t["gross_bp"], lev=t["leverage"]))
    return pd.DataFrame(rows, columns=["date", "sym", "dir", "gross", "lev"]), use


def stats(df: pd.DataFrame, days: list, cost_bp: float) -> dict:
    """Per-trade net (2 fills) and the daily-P&L Sharpe over ALL sessions in the window (flat days count as 0)."""
    if df.empty:
        return dict(n=0, mean=None, med=None, t=None, hit=None, sharpe=None, ann=None)
    net = df.gross - 2 * cost_bp
    n = len(net)
    t = float(net.mean() / (net.std() / np.sqrt(n))) if n > 2 and net.std() > 0 else None
    dp = (net * 1e-4 * df.lev).groupby(df.date).sum().reindex(pd.DatetimeIndex(days)).fillna(0.0)
    sh_ = float(dp.mean() / dp.std() * np.sqrt(252)) if dp.std() > 0 else None
    return dict(n=int(n), mean=round(float(net.mean()), 2), med=round(float(net.median()), 2),
                t=None if t is None else round(t, 2), hit=round(float((net > 0).mean()), 3),
                sharpe=None if sh_ is None else round(sh_, 2), ann=round(float(dp.mean() * 252 * 100), 2))


def positive(base: dict, shock: dict) -> bool:
    return bool(base["n"] >= MIN_TRADES and (base["sharpe"] or -9) >= SHARPE_MIN and (shock["mean"] or -9) > 0)


def line(rows: list[dict]) -> str:
    if not rows:
        return f"noise re-arm watch: no replay yet (weekly, {WINDOW} sessions, lag {LAG}m, {COST_BP}bp/fill); leg OFF"
    r = rows[-1]
    b, s = r["base"], r["shock"]
    verdict = "POSITIVE: re-arm candidate (user decision)" if r["positive"] else "negative: leg stays OFF"
    return (f"noise re-arm watch {r['start']}..{r['end']} ({r['sessions']} sessions): n {b['n']}, mean {b['mean']}bp, "
            f"median {b['med']}, Sharpe {b['sharpe']}, ann {b['ann']}%; at {SHOCK_BP}bp/fill mean {s['mean']}bp -> {verdict}")


def run(state_dir: Path, logs_dir: Path, log=print, today: dt.date | None = None, S: dict | None = None,
        force: bool = False) -> dict | None:
    from swingtrader.daybook import shadow as sh
    state_dir = Path(state_dir)
    path = state_dir / LOG_NAME
    today = today or dt.date.today()
    rows = _read(path)
    if rows and not force:
        age = (today - dt.date.fromisoformat(rows[-1]["date"])).days
        if age < EVERY_DAYS:
            log(f"[noise-rearm] last replay {rows[-1]['date']} ({age}d ago); weekly, skip")
            return None
    cfg = sh.CFGS["PROD"]
    if S is None:
        from swingtrader.daily import marketdata as md
        S = {s: md.minute_history(s, WINDOW + cfg.lookback + 20) for s in cfg.core}
    df, days = replay(S, cfg)
    if not days:
        log("[noise-rearm] no sessions; skip")
        return None
    base, shock = stats(df, days, COST_BP), stats(df, days, SHOCK_BP)
    row = dict(date=today.isoformat(), start=str(pd.Timestamp(days[0]).date()), end=str(pd.Timestamp(days[-1]).date()),
               sessions=len(days), window=WINDOW, lag=LAG, cost_bp=COST_BP, shock_bp=SHOCK_BP,
               base=base, shock=shock, positive=positive(base, shock),
               by_sym={s: stats(df[df.sym == s], days, COST_BP)["mean"] for s in cfg.core})
    state_dir.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(row) + "\n")
    rows.append(row)
    log(f"[noise-rearm] {line(rows)}")
    return row


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    run(root / "state", root / "logs")
