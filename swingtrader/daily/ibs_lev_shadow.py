"""Study ACC (N 833 -> 834) log-only shadow: the IBS leg at a non-callable partial-3x 1.25x overlay.

SHADOW ONLY, NO ORDERS, NO LIVE SWITCH. Each session it logs the live IBS picks, the 1x leg's
open->open return, the 1.25x overlay return (f = 1.25/3 of each pick's capital in its actual 3x
proxy, the rest idle in `ibs_cash_symbol`; no-proxy names express 1x), the running delta vs 1x,
the overlay's running strategy maxDD, realized exposure and the DAILY_ROTH state. The economics
(the proxy map and the letf sizing) are imported from research/sim/account_struct.py verbatim
(Study ACC; do not fork).

A row is appended for each session from START; its return is scored once the next session's open
exists (forward-only, never backfilled before START).

KILL RULE (read here and by swingtrader/daily/testing.py): retire the shadow if the overlay's
running strategy maxDD > 25%, or at the gate (60 scored sessions) if the running delta vs 1x <= 0.
Promotion would be a new switch with its own registry entry; it is NOT deployed.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from swingtrader.config import get_env
from swingtrader.daily import signals as sg

from research.sim.account_struct import IBS_BPS, LEV, PROXY, letf_fraction

LOG_NAME = "ibs-lev.jsonl"
START = dt.date(2026, 10, 5)          # forward-only: never seed a row before this date
NEED = 60                              # scored sessions at which the gate is read
MAX_DD = 0.25                          # retire if the overlay's running strategy maxDD > 25%
ROTH_VAR = "DAILY_ROTH"


def _read(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def _ret(op: pd.DataFrame, sym: str, entry: pd.Timestamp, exit_: pd.Timestamp):
    """open(exit)/open(entry) - 1 for `sym`, or None when a print is missing."""
    if sym is None or sym not in op.columns:
        return None
    try:
        a, b = float(op.at[entry, sym]), float(op.at[exit_, sym])
    except KeyError:
        return None
    return b / a - 1.0 if (np.isfinite(a) and np.isfinite(b) and a > 0) else None


def picks_for(entry, closes, high, low, close, top_k, ibs_max) -> list[str]:
    """The live IBS picks for the session entered at `entry` (mirrors executor's pre-open step):
    top-k of the 18 by 12-1 momentum at the prior month-end, kept while IBS(prior bar) < ibs_max."""
    c = closes[closes.index < entry]
    universe = sg.momentum_top(c, pd.Timestamp(entry), top_k) if top_k else list(closes.columns)
    prior = close.index[close.index < entry]
    if len(prior) == 0 or not universe:
        return []
    p = prior[-1]
    last = {s: {"high": high.at[p, s], "low": low.at[p, s], "close": close.at[p, s]}
            for s in universe if s in close.columns}
    return sg.ibs_targets(last, ibs_max)


def score(entry, exit_, picks, op, cash):
    """(1x return, 1.25x overlay return, realized exposure) for one pick's open->open hold, net of
    3bp/side on the capital deployed (as research/sim/account_struct.leg_pnl)."""
    f = letf_fraction(LEV)
    cash_r = _ret(op, cash, entry, exit_) if cash else 0.0
    cash_r = cash_r if cash_r is not None else 0.0
    if not picks:
        return cash_r, cash_r, 0.0                      # idle: both sleeves hold the cash symbol
    base_r, lev_r, mult = [], [], []
    for s in picks:
        r = _ret(op, s, entry, exit_)
        if r is None:
            continue
        base_r.append(r)
        px = PROXY.get(s)
        x = _ret(op, px, entry, exit_) if px else None
        if x is None:
            lev_r.append(r)
            mult.append(1.0)                            # no liquid 3x: express 1x
        else:
            lev_r.append(x)
            mult.append(3.0)                            # actual 3x proxy
    if not base_r:
        return None, None, None
    base = float(np.mean(base_r)) - 2 * IBS_BPS / 1e4
    lev = f * float(np.mean(lev_r)) + (1 - f) * cash_r - 2 * IBS_BPS / 1e4 * f
    return base, lev, f * float(np.mean(mult))


def _rerun(rows: list[dict]) -> None:
    """Running delta vs 1x, overlay maxDD and cumulative returns over the scored rows, in order."""
    cum1 = cuml = peak = 1.0
    mdd = 0.0
    for r in sorted(rows, key=lambda x: x["date"]):
        if r.get("ret_1x") is not None:
            cum1 *= 1 + r["ret_1x"]
            cuml *= 1 + r["ret_lev"]
            peak = max(peak, cuml)
            mdd = min(mdd, cuml / peak - 1)
        r["cum_1x"], r["cum_lev"] = cum1 - 1, cuml - 1
        r["delta"], r["mdd_lev"] = cuml - cum1, mdd


def line(rows: list[dict]) -> str:
    scored = [r for r in rows if r.get("ret_1x") is not None]
    if not scored:
        return f"{len(rows)} session(s) pending, none scored yet"
    r = scored[-1]
    kill = ("KILL: maxDD>25%" if r["mdd_lev"] < -MAX_DD
            else "KILL: delta<=0 at gate" if len(scored) >= NEED and r["delta"] <= 0
            else "running")
    return (f"{len(scored)} scored (+{len(rows) - len(scored)} pending): delta vs 1x "
            f"{r['delta'] * 100:+.2f}pp, maxDD {r['mdd_lev'] * 100:+.1f}%, "
            f"exposure {r['exposure']:.2f}x, roth {r['roth']} [{kill}]")


def run(state_dir: Path, today: dt.date | None = None, log=print, bars=None,
        cfg=None, write=True) -> dict:
    """Append/score one row per session from START. `bars` (tests) = {sym: DataFrame(close/open/...)}."""
    state_dir = Path(state_dir)
    if cfg is None:
        from swingtrader.config import Config
        d = Config.load().daily
        cfg = (list(d.ibs_symbols), d.ibs_cash_symbol, d.ibs_top_k or 3, d.ibs_max)
    symbols, cash, top_k, ibs_max = cfg
    today = pd.Timestamp(today or dt.date.today())

    if bars is None:
        from . import marketdata as md
        syms = list(dict.fromkeys(list(symbols) + list(PROXY.values()) + ([cash] if cash else [])))
        bars = md.sip_daily(syms, today - pd.Timedelta(days=500), today + pd.Timedelta(days=1))
    fram = {f: pd.DataFrame({s: bars[s][f] for s in bars if f in bars[s].columns}).sort_index()
            for f in ("open", "high", "low", "close")}
    op = fram["open"]
    sessions = list(fram["close"][[s for s in symbols if s in fram["close"].columns]].dropna(how="all").index)
    rows = _read(state_dir / LOG_NAME)
    have = {r["date"] for r in rows}

    # score any row whose exit session's open now exists
    for r in rows:
        if r.get("ret_1x") is not None:
            continue
        e = pd.Timestamp(r["date"])
        nxt = next((d for d in sessions if d > e), None)
        if nxt is None:
            continue
        a, b, x = score(e, nxt, r["syms"], op, cash)
        if a is not None:
            r["ret_1x"], r["ret_lev"], r["exposure"] = a, b, x

    # log a (pending) row for every session from START not already present
    for d in sessions:
        if not (pd.Timestamp(START) <= d <= today) or str(d.date()) in have:
            continue
        rows.append(dict(date=str(d.date()), syms=picks_for(
            d, fram["close"][[s for s in symbols if s in fram["close"].columns]],
            fram["high"], fram["low"], fram["close"], top_k, ibs_max),
            ret_1x=None, ret_lev=None, exposure=None,
            roth=(get_env(ROTH_VAR, "off") or "off").strip().lower()))
        have.add(str(d.date()))

    _rerun(rows)
    rows.sort(key=lambda r: r["date"])
    if write:
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / LOG_NAME).write_text("".join(json.dumps(r) + "\n" for r in rows))
    log(f"[ibs-lev] {line(rows)}")
    return dict(n=sum(1 for r in rows if r.get("ret_1x") is not None), rows=rows)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    day = dt.date.fromisoformat(args[0]) if args else None
    run(Path(__file__).resolve().parents[2] / "state", day, write="--dry" not in sys.argv)
