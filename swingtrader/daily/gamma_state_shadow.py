"""GAMMA-FREE forward shadow (round1_prose.md "Amendment -- Study GAMMA-FREE", N 931 -> 932): logs, never orders.

Mechanism (research/drafts/shadow_dealer_gamma.md): when option dealers are net SHORT gamma they must buy rallies and sell
declines to stay hedged, so the day's move continues into the close; long gamma leans against it. Free proxy for the sign:
SqueezeMetrics' model-signed SPX GEX (DIX.csv, published after each close, free). Rule (FROZEN): on session D use GEX of
D-1 (known before D's open); short_gamma = GEX(D-1) < 0. Trade logged: SPY, enter at 15:30 in the direction of the 09:30 ->
15:30 move, exit at the official closing cross; cont = sign(move) x (close / p1530 - 1); net at 1bp/side. Long-gamma days are
the control. Long-only half (move > 0 only) reported for the Roth. Gate: NEED short-gamma days. KILL = mean net <= 0 at NEED;
PASS = mean net >= +5bp and t >= 2 (that is also the bar for ever buying OPRA strike-level data). Rows before FORWARD_FROM are
backfill (the first run's lookback), reported separately. The free GEX proxy already failed the untouched 2016-20 window as a
night-leg gate (prior lowered); this shadow is the $0 forward falsification the data-buy rule asks for before any purchase.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import statistics as st
from pathlib import Path

import pandas as pd

LOG_NAME = "gamma-state.jsonl"
DIX_URL = "https://squeezemetrics.com/monitor/static/DIX.csv"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) research-personal"}
SYM = "SPY"
COST = 1e-4               # per side, SPY
NEED = 120                # short-gamma days
GATE_BP = 5.0
FORWARD_FROM = "2026-10-13"
LOOKBACK_DAYS = 12
ZWIN = 21


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


def fetch_gex(text: str | None = None) -> dict[str, tuple[float, float]]:
    """date -> (gex, dix) from the DIX.csv text (fetched when not given)."""
    if text is None:
        import requests
        r = requests.get(DIX_URL, headers=UA, timeout=30)
        r.raise_for_status()
        text = r.text
    out = {}
    for row in csv.DictReader(io.StringIO(text)):
        try:
            out[row["date"]] = (float(row["gex"]), float(row["dix"]))
        except (KeyError, ValueError):
            continue
    return out


def state(day: str, gex: dict[str, tuple[float, float]]) -> dict | None:
    """GEX / DIX of the last published session BEFORE `day`, its sign and its z vs the prior ZWIN sessions (median / MAD)."""
    prior = sorted(d for d in gex if d < day)
    if not prior:
        return None
    d1 = prior[-1]
    g, dix = gex[d1]
    hist = [gex[d][0] for d in prior[-ZWIN - 1:-1]]
    z = None
    if len(hist) >= 10:
        med = st.median(hist)
        mad = st.median(abs(h - med) for h in hist)
        z = (g - med) / (1.4826 * mad) if mad > 0 else None
    return dict(gex_date=d1, gex=g, dix=dix, short_gamma=g < 0, z=None if z is None else round(z, 2))


def score(day: str, s: dict, open_px: float | None, p1530: float | None, close: float | None) -> dict:
    r = dict(date=day, **s, open=open_px, p1530=p1530, close=close, status="pending")
    if not (open_px and p1530 and close):
        return r
    move = p1530 / open_px - 1
    sign = 1 if move > 0 else (-1 if move < 0 else 0)
    cont = sign * (close / p1530 - 1)
    r.update(status="scored", move=round(move, 6), cont=round(cont, 6), net=round(cont - 2 * COST, 6),
             long_only=round(close / p1530 - 1 - 2 * COST, 6) if move > 0 else None)
    return r


def summary(rows: list[dict], fwd: bool = True) -> dict:
    sc = [r for r in rows if r.get("status") == "scored" and (r["date"] >= FORWARD_FROM) == fwd]
    sg = [r for r in sc if r.get("short_gamma")]
    lg = [r for r in sc if not r.get("short_gamma")]

    def _m(xs):
        xs = [x for x in xs if x is not None]
        if not xs:
            return dict(n=0, mean_bp=None, median_bp=None, hit=None, t=None)
        sd = st.pstdev(xs) if len(xs) > 1 else 0.0
        return dict(n=len(xs), mean_bp=round(1e4 * st.mean(xs), 1), median_bp=round(1e4 * st.median(xs), 1),
                    hit=round(sum(x > 0 for x in xs) / len(xs), 2), t=round(st.mean(xs) / (sd / len(xs) ** 0.5), 2) if sd > 0 and len(xs) > 1 else None)
    return dict(short=_m([r["net"] for r in sg]), long_gamma=_m([r["net"] for r in lg]),
                short_long_only=_m([r.get("long_only") for r in sg]), days=len(sc))


def verdict(s: dict) -> str:
    sh = s["short"]
    if sh["n"] < NEED or sh["mean_bp"] is None:
        return ""
    if sh["mean_bp"] <= 0:
        return " -> KILL (short-gamma continuation <= 0 net)"
    if sh["mean_bp"] >= GATE_BP and (sh["t"] or 0) >= 2:
        return " -> PASS (>= +5bp net, t >= 2: the bar for considering OPRA data)"
    return " -> HOLD"


def line(rows: list[dict]) -> str:
    f, b = summary(rows, True), summary(rows, False)

    def _p(tag, s):
        sh, lg, lo = s["short"], s["long_gamma"], s["short_long_only"]
        if not s["days"]:
            return f"{tag} 0 days"
        txt = f"{tag} {s['days']} days: short-gamma {sh['n']}/{NEED}"
        if sh["n"]:
            txt += f" net {sh['mean_bp']:+.1f}bp (median {sh['median_bp']:+.1f}, hit {sh['hit']:.0%}" + (f", t {sh['t']}" if sh["t"] is not None else "") + ")"
            if lo["n"]:
                txt += f", long-only {lo['mean_bp']:+.1f}bp (n {lo['n']})"
        if lg["n"]:
            txt += f"; long-gamma control {lg['n']} days {lg['mean_bp']:+.1f}bp"
        return txt
    return _p("forward", f) + "; " + _p("backfill", b) + verdict(f)


def run(state_dir: Path, logs_dir: Path, log=print, today: dt.date | None = None, H: dict | None = None,
        gex: dict | None = None, minutes_fn=None, crosses_fn=None) -> dict:
    from . import marketdata as md
    from .exdate_open_shadow import _headers
    from .pref_ex_shadow import crosses as _crosses
    minutes_fn = minutes_fn or md.rth_minutes
    crosses_fn = crosses_fn or _crosses
    state_dir = Path(state_dir)
    path = state_dir / LOG_NAME
    rows = _read(path)
    today = today or dt.date.today()
    gex = gex if gex is not None else fetch_gex()
    done = {r["date"] for r in rows if r.get("status") == "scored"}
    H = H or _headers()
    start = (today - dt.timedelta(days=LOOKBACK_DAYS)).isoformat()
    end = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
    X = crosses_fn([SYM], start, end, H).get(SYM, {})          # SPY sessions and closing crosses in the window
    todo = sorted(d for d in X if d < str(today) and d not in done)
    new = {r["date"]: r for r in rows}
    for d in todo:
        s = state(d, gex)
        if s is None:
            continue
        close = X[d][2]
        m = minutes_fn([SYM], pd.Timestamp(d), 1530)
        open_px = float(m.loc[SYM, "open"]) if SYM in m.index else None
        p1530 = float(m.loc[SYM, "close"]) if SYM in m.index else None
        r = score(d, s, open_px, p1530, close)
        if r["status"] != "scored" and d <= str(today - dt.timedelta(days=6)):
            r["status"] = "no_data"
        new[d] = r
        if r["status"] == "scored":
            log(f"[gamma-state] {d}: GEX({r['gex_date']}) {r['gex']/1e9:+.1f}B z {r['z']} {'SHORT' if r['short_gamma'] else 'long'} gamma; "
                f"move {r['move']*1e4:+.0f}bp -> cont {r['cont']*1e4:+.1f}bp")
    rows = sorted(new.values(), key=lambda r: r["date"])
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    log(f"[gamma-state] {line(rows)}")
    return summary(rows)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    run(root / "state", root / "logs")
