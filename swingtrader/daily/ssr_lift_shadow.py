"""SSR-LIFT-FWD forward shadow (round1_prose.md "Amendment -- Study SSR-LIFT", N 860): logs, never orders.

Rule (FROZEN at registration 2026-10-06, no re-tuning; SSR-T1 N 1013 kept the T+2 window): common stock (symbol A-Z{1,5}, not a
fund/ETF), prior RAW close >= $10, 20d mean $volume >= $20M (the registration's ADV>=$20M; SSR-T1 reported the same cut), whose
REGULAR-HOURS low on trigger day T is <= -10% vs the prior session's close (Rule 201 trigger), and which is NOT re-triggered on
T+1 (T+1 regular-hours low > -10% vs T's close). Short at the official OPEN cross of T+2, cover at the official CLOSE cross of
T+2, equal weight, hedge = +1.5 x SPY's same-window official open->close return. Hedged = -(c2/o2-1) + 1.5*(spy_c/spy_o-1).
Net = hedged - 2*SIDE_BP - BORROW_BP (5bp/side + 2bp borrow: the cost level at which the registration found the edge dead).
Gate (module scale): NEED forward event-days, hedged net EW-day mean > 0, day-clustered t >= 2. The registered PASS/KILL
(120 lift sessions after 2026-12-06, mean > +8bp net of borrow, ETB-only > 0, ex-top-5) is read from the same log by hand.

Regular hours: trigger lows come from marketdata.rth_minutes (09:30-16:00 ET raw SIP minutes), never the daily bar (a 23/5 daily
bar may start the evening before). Daily adjusted bars only SCREEN candidates (low <= -9%) and give ADV. Dates are trade dates.
Easy-to-borrow: Alpaca asset `easy_to_borrow` / `shortable` read at detection time (forward rows only; backfill rows = None,
today's flag is not history). Not a fee; the broker's fee/ETB at the open is still unmeasured.

Rows in state/ssr-lift.jsonl: status scanned (one per scanned T) | pending | scored | retrigger | no_cross. `backfill` rows were
discovered after the fact (look-alike, labelled, excluded from the gate).
"""
from __future__ import annotations

import datetime as dt
import json
import re
import statistics as st
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

LOG_NAME = "ssr-lift.jsonl"
START_T = "2026-10-15"      # first forward trigger day: its T+2 is 2026-10-19, the first session after registration here
NEED = 60
SIDE_BP = 5.0
BORROW_BP = 2.0
HEDGE = 1.5
TRIG = -0.10
SCREEN = -0.09              # adjusted-bar screen, looser than TRIG; the regular-hours raw minutes decide
PX_MIN = 10.0
ADV_MIN = 20e6
BENCH = "SPY"
HIST_DAYS = 45
CHUNK = 200
SYM = re.compile(r"[A-Z]{1,5}")


def _read(path: Path) -> list[dict]:
    from .ovn_mom_shadow import _read as r
    return r(path)


def _wide(bars: dict[str, pd.DataFrame]):
    """Date x symbol: L (adjusted low / prior close - 1), ADV (mean $vol of the 20 sessions before)."""
    low, close, usd = {}, {}, {}
    for s, b in bars.items():
        if b is None or len(b) < 3:
            continue
        low[s], close[s], usd[s] = b["low"], b["close"], b["close"] * b["volume"]
    low, close, usd = (pd.DataFrame(x).sort_index() for x in (low, close, usd))
    L = low / close.shift(1) - 1
    adv = usd.rolling(20, min_periods=15).mean().shift(1)
    return L, adv


def candidates(T: str, L: pd.DataFrame, adv: pd.DataFrame, fund=lambda s: False) -> list[str]:
    d = pd.Timestamp(T)
    if d not in L.index:
        return []
    x, a = L.loc[d], adv.loc[d]
    ok = (x <= SCREEN) & (a >= ADV_MIN)
    return [s for s in x.index[ok.fillna(False).to_numpy(bool)] if SYM.fullmatch(s) and not fund(s)]


def confirm(T: str, prev: str, syms: list[str], rth_fn) -> list[dict]:
    """Regular-hours trigger: min 09:30-16:00 low on T vs the prior session's last regular-hours close (raw)."""
    out = []
    for i in range(0, len(syms), 50):
        ch = syms[i:i + 50]
        t, p = rth_fn(ch, pd.Timestamp(T)), rth_fn(ch, pd.Timestamp(prev))
        for s in ch:
            if s not in t.index or s not in p.index:
                continue
            pc, lo = float(p.loc[s, "close"]), float(t.loc[s, "low"])
            if pc >= PX_MIN and lo / pc - 1 <= TRIG:
                out.append(dict(sym=s, L=round(lo / pc - 1, 5), praw=round(pc, 4)))
    return out


def score(r: dict, X: dict, rth_fn=None) -> dict | None:
    """Short T+2 open cross -> cover T+2 close cross, SPY-hedged; None until T+2 has printed."""
    p, sp = X.get(r["sym"], {}), X.get(BENCH, {})
    later = sorted(d for d in p if d > r["T"])
    c0 = (p.get(r["T"]) or (None,) * 4)[2]
    if len(later) < 2 or not c0:
        return None
    d1, d2 = later[0], later[1]
    o2, c2, os2 = p[d2][0], p[d2][2], p[d2][1]
    so, sc = (sp.get(d2) or (None,) * 4)[0], (sp.get(d2) or (None,) * 4)[2]
    if not (o2 and c2 and so and sc):
        return None
    if rth_fn is not None:                      # re-trigger on T+1 (known before the T+2 open): drop
        t1 = rth_fn([r["sym"]], pd.Timestamp(d1))
        if r["sym"] in t1.index and float(t1.loc[r["sym"], "low"]) / c0 - 1 <= TRIG:
            return dict(r, status="retrigger", d1=d1, d2=d2)
    raw = float(np.clip(-(c2 / o2 - 1), -0.9, 0.9))
    hedged = float(np.clip(raw + HEDGE * (sc / so - 1), -0.9, 0.9))
    net = hedged - (2 * SIDE_BP + BORROW_BP) / 1e4
    return dict(r, status="scored", d1=d1, d2=d2, o2=o2, c2=c2, open_usd=round(o2 * (os2 or 0)),
                raw=round(raw, 6), hedged=round(hedged, 6), net=round(net, 6))


def _tt(v: list[float]) -> float | None:
    return float(np.mean(v) / np.std(v, ddof=1) * np.sqrt(len(v))) if len(v) >= 3 and np.std(v, ddof=1) > 0 else None


def summary(rows: list[dict], backfill: bool = False) -> dict:
    sc = [r for r in rows if r.get("status") == "scored" and bool(r.get("backfill")) == backfill]
    by: dict[str, list[dict]] = {}
    for r in sc:
        by.setdefault(r["d2"], []).append(r)
    out = dict(days=len(by), events=len(sc), backfill=backfill)
    if not by:
        return dict(out, net_bp=None, hedged_bp=None, raw_bp=None, t=None, median_bp=None, etb_bp=None)
    ds = sorted(by)
    mean = lambda k: [st.mean(x[k] for x in by[d]) for d in ds]  # noqa: E731
    net = mean("net")
    etb = [x["net"] for x in sc if x.get("etb")]
    return dict(out, net_bp=round(1e4 * st.mean(net), 1), hedged_bp=round(1e4 * st.mean(mean("hedged")), 1),
                raw_bp=round(1e4 * st.mean(mean("raw")), 1), t=None if _tt(net) is None else round(_tt(net), 2),
                median_bp=round(1e4 * st.median(x["hedged"] for x in sc), 1),
                etb_bp=round(1e4 * st.mean(etb), 1) if etb else None, n_etb=len(etb))


def verdict(s: dict) -> str:
    if s["days"] < NEED:
        return f" ({s['days']}/{NEED} event-days)"
    if s["net_bp"] > 0 and (s.get("t") or 0) >= 2:
        return " -> PASS at module gate (net > 0, t >= 2); registered gate read by hand"
    return " -> FAIL (net <= 0)" if s["net_bp"] <= 0 else " -> HOLD"


def line(rows: list[dict]) -> str:
    s, b = summary(rows), summary(rows, True)
    if not s["days"]:
        return f"SSR-LIFT-FWD: 0 forward event-days yet (backfill {b['days']}d/{b['events']}ev, not gated)"
    return (f"SSR-LIFT-FWD: {s['days']}d/{s['events']}ev hedged {s['hedged_bp']:+.1f}bp net {s['net_bp']:+.1f}bp "
            f"t {s['t']} median {s['median_bp']:+.1f}bp ETB-only {s['etb_bp']}{verdict(s)}")


def _etb(sym: str, H: dict) -> bool | None:
    from .exdate_open_shadow import ASSET_URL, _get
    try:
        a = _get(ASSET_URL.format(sym), {}, H)
        return bool(a.get("easy_to_borrow")) and bool(a.get("shortable"))
    except Exception:  # noqa: BLE001
        return None


def run(state_dir: Path, logs_dir: Path, log=print, today: dt.date | None = None, H: dict | None = None,
        bars_fn=None, crosses_fn=None, rth_fn=None, fund_fn=None, backfill: int = 0) -> dict:
    from . import marketdata as md
    from .exdate_open_shadow import _headers, is_fund
    from .ovn_mom_shadow import universe
    from .pref_ex_shadow import crosses as _crosses
    bars_fn, crosses_fn, rth_fn = bars_fn or md.sip_daily, crosses_fn or _crosses, rth_fn or md.rth_minutes
    today = today or dt.datetime.now(dt.timezone.utc).astimezone(ZoneInfo(md.ET)).date()
    state_dir = Path(state_dir)
    path = state_dir / LOG_NAME
    rows = _read(path)
    scanned = {r["T"] for r in rows if r.get("status") == "scanned"}
    syms = universe(state_dir) or []
    bench = bars_fn([BENCH], str(today - dt.timedelta(days=HIST_DAYS + 40)))[BENCH]
    sess = [str(d.date()) for d in bench.index if d.date() < today]
    todo = [(T, False) for T in sess if T >= START_T and T not in scanned]
    if backfill:
        bf = [T for T in sess[:-2] if T < START_T][-backfill:]      # T+2 must already be complete
        todo = [(T, True) for T in bf if T not in scanned] + todo
    if todo:
        H = H or _headers()
        cache: dict = {}
        fund_fn = fund_fn or (lambda s: is_fund(s, H, cache))
        d0 = (pd.Timestamp(min(T for T, _ in todo)) - pd.Timedelta(days=HIST_DAYS)).strftime("%Y-%m-%d")
        bars = {}
        for i in range(0, len(syms), CHUNK):
            bars.update(bars_fn(syms[i:i + CHUNK], d0))
        L, adv = _wide(bars)
        for T, bf_flag in todo:
            i = sess.index(T)
            hit = confirm(T, sess[i - 1], candidates(T, L, adv, fund_fn), rth_fn) if i else []
            for h in hit:
                rows.append(dict(T=T, sym=h["sym"], L=h["L"], praw=h["praw"], adv=round(float(adv.loc[pd.Timestamp(T), h["sym"]])),
                                 etb=None if bf_flag else _etb(h["sym"], H), etb_asof=None if bf_flag else str(today),
                                 backfill=bf_flag, status="pending"))
            rows.append(dict(T=T, status="scanned", n=len(hit), backfill=bf_flag))
            log(f"[ssr-lift] T {T}{' (backfill)' if bf_flag else ''}: {len(hit)} triggers")
    pend = [r for r in rows if r.get("status") == "pending"]
    if pend:
        H = H or _headers()
        end = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
        syms_p = sorted({r["sym"] for r in pend} | {BENCH})
        d0 = min(r["T"] for r in pend)
        X: dict = {}
        for i in range(0, len(syms_p), 40):
            X.update(crosses_fn(syms_p[i:i + 40], d0, end, H))
        new = []
        for r in rows:
            if r.get("status") == "pending":
                s = score(r, X, rth_fn)
                if s:
                    r = s
                elif r["T"] <= str(today - dt.timedelta(days=10)):
                    r = dict(r, status="no_cross")
            new.append(r)
        rows = new
    rows = sorted(rows, key=lambda r: (r["T"], r.get("status") != "scanned", r.get("sym", "")))
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    log(f"[ssr-lift] {line(rows)}")
    return summary(rows)


if __name__ == "__main__":
    import sys
    root = Path(__file__).resolve().parents[2]
    n = int(sys.argv[sys.argv.index("--backfill") + 1]) if "--backfill" in sys.argv else 0
    run(root / "state", root / "logs", backfill=n)
