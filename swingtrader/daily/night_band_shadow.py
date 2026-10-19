"""NIGHT-BAND-FWD forward shadow (round1_prose.md "Amendment - Study NIGHT-BAND", N 1040): logs, never orders.

Question: does the live night rule still pay between -4% and -8% (the live cutoff), at the exact 15:40 state and official
auction prints? The daily-close proxy (research/sim/night_band.py, Sharadar 1999-2026) says the band earns ~1/3 of the -8%
pool (+17.9bp gross, +7.6bp in 2013-26) and lifts the leg on the ~26% of nights where the -8% pool has nothing; the proxy is
~1.7x optimistic and the answer is inside the live auction cost, so only forward prints can settle it.

Rule (FROZEN 2026-10-19, no re-tuning): the live night universe (state/daily-universe-*.json), common stock (not a fund);
state at 15:40 ET from SIP regular-hours minutes 09:30-15:40 (p40 = last minute close, H/L through 15:40 incl. p40);
prev close = the prior session's last regular-hours minute close (raw); day_ret = p40/prev - 1; IBS = (p40-L)/(H-L) < 0.10;
p40 in [$5, $2000]; vol20 >= 0.60 (20 prior sessions, adjusted daily bars, annualised); ADV20 >= $10M.
  cls "band": -8% < day_ret <= -4%          cls "pool": day_ret <= -8% (the live leg, logged for the paired comparison)
Buy the official CLOSE cross of T, sell the official OPEN cross of T+1, equal weight per name; r = o1/c0 - 1; spy = SPY same window.
Net is reported at 0bp (live auction fills measure ~0bp) and at 15bp round trip.
Gate (module scale): NEED forward band nights, band EW-night mean >= +5bp gross, night-clustered t >= 2, median > 0; the
registered read (band alone on no-pool nights, union-leg delta vs pool) is taken from the same log by hand. No live change
without the user's OK; a PASS means "propose lowering the cutoff", nothing more.

Backfill rows (--backfill N sessions before START) are look-alikes: logged, labelled, excluded from the gate.
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

LOG_NAME = "night-band.jsonl"
START_T = "2026-10-20"          # first forward signal session (registered 2026-10-19)
NEED = 60
BAND_LO, LIVE = -0.08, -0.04    # band = (BAND_LO, LIVE]; pool = <= BAND_LO
IBS_MAX = 0.10
PX_MIN, PX_MAX = 5.0, 2000.0
VOL_MIN = 0.60
ADV_MIN = 1e7
SCREEN_LO, SCREEN_HI = -0.12, -0.03     # adjusted daily-bar screen, looser than the rule; the 15:40 minutes decide
RT_BP = 15.0
BENCH = "SPY"
HIST_DAYS = 45
CHUNK = 200
SYM = re.compile(r"[A-Z]{1,5}")


def _read(path: Path) -> list[dict]:
    from .ovn_mom_shadow import _read as r
    return r(path)


def _wide(bars: dict[str, pd.DataFrame]):
    """Date x symbol: R (adjusted close / prior close - 1), ADV20 (mean $vol of the 20 prior sessions), VOL20 (annualised)."""
    close, usd = {}, {}
    for s, b in bars.items():
        if b is None or len(b) < 3:
            continue
        close[s], usd[s] = b["close"], b["close"] * b["volume"]
    close, usd = (pd.DataFrame(x).sort_index() for x in (close, usd))
    R = close / close.shift(1) - 1
    adv = usd.rolling(20, min_periods=15).mean().shift(1)
    vol20 = np.log(close / close.shift(1)).rolling(20, min_periods=19).std().shift(1) * np.sqrt(252)
    return R, adv, vol20


def candidates(T: str, R: pd.DataFrame, adv: pd.DataFrame, vol20: pd.DataFrame, fund=lambda s: False) -> list[str]:
    d = pd.Timestamp(T)
    if d not in R.index:
        return []
    x, a, v = R.loc[d], adv.loc[d], vol20.loc[d]
    ok = (x <= SCREEN_HI) & (x >= SCREEN_LO) & (a >= ADV_MIN * 0.9) & (v >= VOL_MIN * 0.9)
    return [s for s in x.index[ok.fillna(False).to_numpy(bool)] if SYM.fullmatch(s) and not fund(s)]


def state_1540(T: str, prev: str, syms: list[str], adv: pd.DataFrame, vol20: pd.DataFrame, rth_fn) -> list[dict]:
    """Exact-rule rows at 15:40 for T: band and pool names with their day_ret / ibs / p40."""
    out = []
    d = pd.Timestamp(T)
    for i in range(0, len(syms), 50):
        ch = syms[i:i + 50]
        t, p = rth_fn(ch, d, 1540), rth_fn(ch, pd.Timestamp(prev))
        for s in ch:
            if s not in t.index or s not in p.index:
                continue
            pc, p40 = float(p.loc[s, "close"]), float(t.loc[s, "close"])
            H, L = max(float(t.loc[s, "high"]), p40), min(float(t.loc[s, "low"]), p40)
            if not (pc > 0 and H > L and PX_MIN <= p40 <= PX_MAX):
                continue
            dr, ibs = p40 / pc - 1, (p40 - L) / (H - L)
            a, v = float(adv.loc[d, s]) if s in adv.columns else np.nan, float(vol20.loc[d, s]) if s in vol20.columns else np.nan
            if not (ibs < IBS_MAX and dr <= LIVE and np.isfinite(a) and a >= ADV_MIN and np.isfinite(v) and v >= VOL_MIN):
                continue
            out.append(dict(sym=s, cls="pool" if dr <= BAND_LO else "band", p40=round(p40, 4), prev=round(pc, 4),
                            day_ret=round(dr, 5), ibs=round(ibs, 4), adv=round(a), vol20=round(v, 3)))
    return out


def score(r: dict, X: dict) -> dict | None:
    """Buy T close cross -> sell T+1 open cross; None until T+1's open has printed."""
    p, sp = X.get(r["sym"], {}), X.get(BENCH, {})
    c0 = (p.get(r["T"]) or (None,) * 4)[2]
    later = sorted(d for d in p if d > r["T"])
    if not c0 or not later:
        return None
    d1 = later[0]
    o1, os1 = p[d1][0], p[d1][1]
    sc0, so1 = (sp.get(r["T"]) or (None,) * 4)[2], (sp.get(d1) or (None,) * 4)[0]
    if not (o1 and sc0 and so1):
        return None
    raw = float(np.clip(o1 / c0 - 1, -0.9, 0.9))
    return dict(r, status="scored", d1=d1, c0=c0, o1=o1, open_usd=round(o1 * (os1 or 0)), r=round(raw, 6),
                spy=round(so1 / sc0 - 1, 6), net15=round(raw - RT_BP / 1e4, 6))


def _tt(v: list[float]) -> float | None:
    return float(np.mean(v) / np.std(v, ddof=1) * np.sqrt(len(v))) if len(v) >= 3 and np.std(v, ddof=1) > 0 else None


def summary(rows: list[dict], backfill: bool = False) -> dict:
    sc = [r for r in rows if r.get("status") == "scored" and bool(r.get("backfill")) == backfill]
    by: dict[str, dict[str, list[dict]]] = {}
    for r in sc:
        by.setdefault(r["T"], {}).setdefault(r["cls"], []).append(r)
    band_nights = sorted(T for T in by if "band" in by[T])
    out = dict(nights=len(band_nights), names=sum(len(by[T]["band"]) for T in band_nights), backfill=backfill,
               pool_nights=sum(1 for T in by if "pool" in by[T]), added_nights=sum(1 for T in band_nights if "pool" not in by[T]))
    if not band_nights:
        return dict(out, band_bp=None, band_net15_bp=None, t=None, median_bp=None, pool_bp=None, paired_bp=None)
    bm = [st.mean(x["r"] for x in by[T]["band"]) for T in band_nights]
    both = [T for T in band_nights if "pool" in by[T]]
    paired = [st.mean(x["r"] for x in by[T]["band"]) - st.mean(x["r"] for x in by[T]["pool"]) for T in both]
    pool = [st.mean(x["r"] for x in by[T]["pool"]) for T in by if "pool" in by[T]]
    return dict(out, band_bp=round(1e4 * st.mean(bm), 1), band_net15_bp=round(1e4 * (st.mean(bm) - RT_BP / 1e4), 1),
                t=None if _tt(bm) is None else round(_tt(bm), 2), median_bp=round(1e4 * st.median(x["r"] for T in band_nights for x in by[T]["band"]), 1),
                pool_bp=round(1e4 * st.mean(pool), 1) if pool else None,
                paired_bp=round(1e4 * st.mean(paired), 1) if paired else None, paired_n=len(paired))


def verdict(s: dict) -> str:
    if s["nights"] < NEED:
        return f" ({s['nights']}/{NEED} band nights)"
    if s["band_bp"] >= 5 and (s.get("t") or 0) >= 2 and (s.get("median_bp") or 0) > 0:
        return " -> PASS at module gate (band >= +5bp, t >= 2, median > 0): propose lowering the cutoff (user decision)"
    return " -> FAIL" if s["band_bp"] <= 0 else " -> HOLD"


def line(rows: list[dict]) -> str:
    s, b = summary(rows), summary(rows, True)
    if not s["nights"]:
        return f"NIGHT-BAND-FWD: 0 forward band nights yet (backfill {b['nights']}n/{b['names']} names, band {b['band_bp']}bp, pool {b['pool_bp']}bp; not gated)"
    return (f"NIGHT-BAND-FWD: {s['nights']}n/{s['names']} names band {s['band_bp']:+.1f}bp (net15 {s['band_net15_bp']:+.1f}) "
            f"t {s['t']} median {s['median_bp']:+.1f} | pool {s['pool_bp']}bp paired {s['paired_bp']}bp (n {s.get('paired_n')}) "
            f"| added nights {s['added_nights']}{verdict(s)}")


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
        bf = [T for T in sess[:-1] if T < START_T][-backfill:]      # T+1's open must already be complete
        todo = [(T, True) for T in bf if T not in scanned] + todo
    if todo and syms:
        H = H or _headers()
        cache: dict = {}
        fund_fn = fund_fn or (lambda s: is_fund(s, H, cache))
        d0 = (pd.Timestamp(min(T for T, _ in todo)) - pd.DateOffset(days=HIST_DAYS)).strftime("%Y-%m-%d")
        bars = {}
        for i in range(0, len(syms), CHUNK):
            bars.update(bars_fn(syms[i:i + CHUNK], d0))
        R, adv, vol20 = _wide(bars)
        for T, bf_flag in todo:
            i = sess.index(T)
            hit = state_1540(T, sess[i - 1], candidates(T, R, adv, vol20, fund_fn), adv, vol20, rth_fn) if i else []
            for h in hit:
                rows.append(dict(T=T, backfill=bf_flag, status="pending", **h))
            nb, npool = sum(1 for h in hit if h["cls"] == "band"), sum(1 for h in hit if h["cls"] == "pool")
            rows.append(dict(T=T, status="scanned", n_band=nb, n_pool=npool, backfill=bf_flag))
            log(f"[night-band] T {T}{' (backfill)' if bf_flag else ''}: band {nb} pool {npool}")
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
                s = score(r, X)
                if s:
                    r = s
                elif r["T"] <= str(today - dt.timedelta(days=10)):
                    r = dict(r, status="no_cross")
            new.append(r)
        rows = new
    rows = sorted(rows, key=lambda r: (r["T"], r.get("status") != "scanned", r.get("cls", ""), r.get("sym", "")))
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    log(f"[night-band] {line(rows)}")
    return summary(rows)


if __name__ == "__main__":
    import sys
    root = Path(__file__).resolve().parents[2]
    n = int(sys.argv[sys.argv.index("--backfill") + 1]) if "--backfill" in sys.argv else 0
    run(root / "state", root / "logs", backfill=n)
