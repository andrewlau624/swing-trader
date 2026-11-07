"""UPRO-GATE-FWD: log-only daily signal for the user's manually held Roth UPRO core (round1_prose.md Study UPRO-GATE, the
secondary rule N 1107, which the user picked). Never places orders; it tells the user when to switch UPRO <-> SGOV.

Rule (copied from research/sim/upro_gate.py dec_200, lines 89-97; do not change it here):
  sma = simple mean of the last 200 session closes INCLUDING today's (pandas rolling(200).mean()), on PRICE closes (the study
  used the ^GSPC price index, not total return: upro_gate.py line 67; so SPY bars are fetched unadjusted, adjustment="raw").
  close > 1.01 x sma -> ON (hold UPRO); close < 0.99 x sma -> OFF (hold SGOV); inside the band keep the previous state; with
  no previous state inside the band, ON iff close > sma. Execution: the NEXT session's official 16:00 closing cross.

State persists in state/upro-gate.jsonl (one row per regular session). The first run has no previous state, so it seeds the
state by replaying the same rule over every fetched SPY bar from the first session with a full 200-session SMA (the study's
own path start), and logs only the latest session. Later runs append every completed session after the last logged one, in
order (catch-up after a missed run); a session already logged is never appended again.

Regular hours: session dates come from the exchange calendar (brokers.regular_sessions, validated by signals.regular_clock
through cef_rights_shadow.session_days) and bars are labelled by marketdata.trade_date. The close is the SIP daily bar's,
whose prices are regular-session prices (signals.bar_semantics_issues canary: bar open/high/low equal the 09:30-16:00 SIP
minutes, stamp 00:00 ET); a session counts only once its 16:00 (or 13:00) close is more than 16 minutes old (the SIP delay),
so a partial in-session bar is never used. The timer runs 08:20 ET, so a row is the previous session's close.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pandas as pd

LOG_NAME = "upro-gate.jsonl"
SYM = "SPY"
N_SMA = 200
BAND = 0.01
NEED = 63                      # one quarter of sessions logged (plumbing + the user acting on switches); 2.46 switches/yr
HISTORY_DAYS = 3 * 366         # bars fetched each run: ~750 sessions, so a seed replay runs ~550 sessions past the warm-up
SIP_DELAY = dt.timedelta(minutes=16)


def _read(path: Path) -> list[dict]:
    from .ovn_mom_shadow import _read as r
    return r(path)


# ------------------------------------------------------------------ rule (pure; upro_gate.py dec_200)

def step(prev: float | None, c: float, m: float) -> float:
    """1.0 = ON (UPRO), 0.0 = OFF (SGOV). Same comparisons and order as upro_gate.dec_200."""
    if c > 1.01 * m:
        return 1.0
    if c < 0.99 * m:
        return 0.0
    if prev is None:
        return 1.0 if c > m else 0.0
    return prev


def replay(closes: pd.Series) -> pd.DataFrame:
    """closes (session-date index, ascending) -> sma, state, days_in_state per session (NaN state before the SMA exists)."""
    sma = closes.rolling(N_SMA).mean()
    s, n, st, nd = None, 0, [], []
    for c, m in zip(closes.to_numpy(), sma.to_numpy()):
        if m == m:
            new = step(s, float(c), float(m))
            n = n + 1 if new == s else 1
            s = new
        st.append(s)
        nd.append(n if s is not None else None)
    return pd.DataFrame({"close": closes, "sma": sma, "state": st, "days": nd}, index=closes.index)


def _name(s: float) -> str:
    return "ON" if s == 1.0 else "OFF"


def row(date: str, c: float, m: float, prev: dict | None, act_on: str | None, seed_state: float | None = None,
        seed_days: int | None = None) -> dict:
    """One session's row. prev = the previous logged row (None on the first run: seed_state/seed_days from replay)."""
    if prev is None:
        s, days, switched, ps = seed_state, seed_days, False, None
    else:
        p = 1.0 if prev["state"] == "ON" else 0.0
        s = step(p, c, m)
        switched = s != p
        days = 1 if switched else int(prev.get("days_in_state") or 0) + 1
        ps = prev["state"]
    lo, hi = 0.99 * m, 1.01 * m
    edge = lo if s == 1.0 else hi       # the edge whose crossing flips the state
    return dict(date=date, spy_close=round(c, 4), sma200=round(m, 4), band_lo=round(lo, 4), band_hi=round(hi, 4),
                state=_name(s), hold="UPRO" if s == 1.0 else "SGOV", prev_state=ps, switched=bool(switched),
                days_in_state=days, dist_to_flip=round(edge / c - 1, 5), act_on=act_on)


# ------------------------------------------------------------------ reader (weekly digest)

def line(rows: list[dict]) -> str:
    if not rows:
        return "UPRO-GATE-FWD: no sessions logged yet"
    r = rows[-1]
    sw = [x for x in rows if x.get("switched")]
    last = f", last switch {sw[-1]['date']} -> {sw[-1]['state']}" if sw else ""
    return (f"UPRO-GATE-FWD {r['date']}: {r['state']} (hold {r['hold']}) for {r['days_in_state']} sessions; SPY "
            f"{r['spy_close']:.2f} vs SMA200 {r['sma200']:.2f} ({r['spy_close'] / r['sma200'] - 1:+.2%}), "
            f"{abs(r['dist_to_flip']):.2%} {'down' if r['state'] == 'ON' else 'up'} to flip "
            f"({r['band_lo'] if r['state'] == 'ON' else r['band_hi']:.2f}); {len(sw)} switches in {len(rows)} sessions{last}")


# ------------------------------------------------------------------ run

def run(state_dir: Path, log=print, now: dt.datetime | None = None, bars_fn=None, sessions_fn=None) -> list[dict]:
    from . import marketdata as md
    from .cef_rights_shadow import session_days
    from zoneinfo import ZoneInfo
    state_dir = Path(state_dir)
    now = now or dt.datetime.now(dt.timezone.utc)
    today = now.astimezone(ZoneInfo(md.ET)).date()
    path = state_dir / LOG_NAME
    rows = _read(path)
    if sessions_fn is None:
        from .brokers import regular_sessions as sessions_fn
    if bars_fn is None:
        bars_fn = lambda start: md.sip_daily([SYM], start, adjustment="raw").get(SYM)  # noqa: E731 - price, not TR
    start = today - dt.timedelta(days=HISTORY_DAYS)
    ss = sorted(sessions_fn(start, today + dt.timedelta(days=10)))
    done = [(o, c) for o, c in ss if c + SIP_DELAY <= now]
    days = session_days(done)                                         # regular-hours check + trade-date labels
    future = [str(md.trade_date(pd.Timestamp(c)).date()) for o, c in ss if c + SIP_DELAY > now]
    bars = bars_fn(start)
    if bars is None or bars.empty:
        log("[upro-gate] no SPY bars; nothing logged")
        return rows
    px = bars["close"].astype(float)
    px.index = pd.to_datetime(px.index).strftime("%Y-%m-%d")
    px = px[~px.index.duplicated(keep="last")]
    miss = [d for d in days if d not in px.index and d >= px.index.min()]
    keep = [d for d in days if d in px.index]
    if miss:
        cut = miss[0]
        log(f"[upro-gate] SPY bar missing for {', '.join(miss[:5])}; logging only sessions before {cut}")
        keep = [d for d in keep if d < cut]
    closes = px.reindex(keep)
    if len(closes) < N_SMA:
        log(f"[upro-gate] only {len(closes)} SPY sessions (< {N_SMA}); nothing logged")
        return rows
    rp = replay(closes)
    nxt = {d: (keep[i + 1] if i + 1 < len(keep) else None) for i, d in enumerate(keep)}
    allnext = sorted(set(days) | set(future))
    act = lambda d: nxt[d] or next((x for x in allnext if x > d), None)  # noqa: E731
    last = rows[-1]["date"] if rows else None
    new: list[dict] = []
    if last is None:
        d = keep[-1]
        r = row(d, float(closes[d]), float(rp.sma[d]), None, act(d), rp.state[d], int(rp.days[d]))
        r["seed"] = f"replay {rp.state.first_valid_index()}..{d} ({int(rp.state.notna().sum())} sessions)"
        new.append(r)
    else:
        prev = rows[-1]
        for d in keep:
            if d <= last:
                continue
            r = row(d, float(closes[d]), float(rp.sma[d]), prev, act(d))
            new.append(r)
            prev = r
    if new:
        state_dir.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.writelines(json.dumps(r) + "\n" for r in new)
        rows = rows + new
    for r in new:
        if r["switched"]:
            log(f"[upro-gate] SWITCH {r['prev_state']} -> {r['state']} on the {r['date']} close: switch the Roth UPRO core "
                f"{'SGOV -> UPRO' if r['state'] == 'ON' else 'UPRO -> SGOV'} at the {r['act_on']} 16:00 closing cross "
                f"(log-only, no order placed)")
    if not new:
        log(f"[upro-gate] {last} already logged; nothing new")
    log(f"[upro-gate] {line(rows)}")
    return rows


if __name__ == "__main__":
    import sys
    from ..config import Config
    cfg = Config.load()
    if getattr(cfg.daily, "upro_gate_fwd", "shadow") == "off":
        print("[upro-gate] daily.upro_gate_fwd is off")
        sys.exit(0)
    root = Path(__file__).resolve().parents[2]
    st_dir = Path(sys.argv[sys.argv.index("--state") + 1]) if "--state" in sys.argv else root / "state"
    run(st_dir)
