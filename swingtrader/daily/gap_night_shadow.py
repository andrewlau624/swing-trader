"""GAP-NIGHT-FWD forward shadow (round1_prose.md "Amendment - Study GAP-NIGHT", N 1050): logs, never orders.

Question: do today's gap names, bought at the official CLOSE cross and sold at the next official OPEN cross, still earn a premium over
the universe's own overnight return? The Sharadar study (research/sim/gap_night.py) says +8.6bp/night over the EW universe in 2016-21
(t 3.0, up-gaps +13.0, down-gaps 0) and +5.4 (t 1.6) in 2022-26: an overnight-attention clientele effect (Lou-Polk-Skouras; the
OVN-MOM family), decaying, measured on daily opens/closes rather than the cross prints. Only forward prints at the two crosses settle it.

Rule (FROZEN 2026-10-19, no re-tuning): the live night universe (state/daily-universe-*.json), common stock (not a fund), SIP daily
bars: gap = open(T) / close(T-1) - 1 with |gap| >= 3%; close(T-1) >= $5; ADV20 (median $vol of the 20 prior sessions) >= $50M.
  cls "up": gap > 0        cls "down": gap < 0        (the registered arm is ALL gaps; up/down are reported, never selected on)
Buy the official CLOSE cross of T, sell the official OPEN cross of T+1, equal weight per name; r = o1/c0 - 1; spy = SPY same window.
Comparator per night (from the same daily bars): the EW overnight open(T+1)/close(T) - 1 of every eligible universe name (ADV20 >=
$50M, prev close >= $5, not a fund) = `univ`, and the same with the night leg's own picks (day_ret <= -8% and IBS < 0.10) excluded =
`univ_x`, so the read is not the night leg in disguise. Net is reported at 0bp (two auctions) and at 5bp round trip.
Gate (module scale): NEED forward gap nights, EW-night excess over `univ` >= +5bp, night-clustered t >= 2, median night excess > 0;
the registered read (up/down arms, excess vs univ_x, SPY beta) is taken from the same log by hand. No live change without the
user's OK; a PASS means "propose a live pilot", nothing more.

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

LOG_NAME = "gap-night.jsonl"
ASSETS = "ovn-mom-assets.json"   # shared sym -> is_fund cache (same lookup as ovn_mom_shadow / exdate_open_shadow.is_fund)
START_T = "2026-10-20"           # first forward gap session (shadow registered 2026-10-19)
NEED = 60
GAP_MIN = 0.03
PX_MIN = 5.0
ADV_MIN = 5e7
NIGHT_DR, NIGHT_IBS = -0.08, 0.10   # the live night leg's picks, excluded from univ_x
RT_BP = 5.0
BENCH = "SPY"
HIST_DAYS = 45
CHUNK = 200
SYM = re.compile(r"[A-Z]{1,5}")


def _read(path: Path) -> list[dict]:
    from .ovn_mom_shadow import _read as r
    return r(path)


def universe(state_dir: Path) -> list[str]:
    """Night-universe symbols whose file ADV20 is near the rule's floor (the bars decide); keeps the pull to the eligible names."""
    files = sorted(Path(state_dir).glob("daily-universe-*.json"))
    if not files:
        return []
    rows = json.loads(files[-1].read_text())
    return sorted({r["symbol"] for r in rows if isinstance(r, dict) and "symbol" in r
                   and float(r.get("adv20") or 0) >= ADV_MIN * 0.8 and SYM.fullmatch(r["symbol"])})


def wide(bars: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Date x symbol frames: O, C, H, L, PC (prior close), ADV (median $vol of the 20 prior sessions), ON (open(T+1)/close(T) - 1)."""
    o, c, h, lo, usd = {}, {}, {}, {}, {}
    for s, b in bars.items():
        if b is None or len(b) < 3:
            continue
        o[s], c[s], h[s], lo[s], usd[s] = b["open"], b["close"], b["high"], b["low"], b["close"] * b["volume"]
    O, C, H, L, U = (pd.DataFrame(x).sort_index() for x in (o, c, h, lo, usd))
    return dict(O=O, C=C, H=H, L=L, PC=C.shift(1), ADV=U.rolling(20, min_periods=15).median().shift(1), ON=O.shift(-1) / C - 1)


def eligible(T: str, F: dict, fund=lambda s: False) -> pd.Series:
    """Boolean per symbol: ADV20 >= $50M, prev close >= $5, common stock, with bars on T."""
    d = pd.Timestamp(T)
    if d not in F["C"].index:
        return pd.Series(dtype=bool)
    ok = (F["ADV"].loc[d] >= ADV_MIN) & (F["PC"].loc[d] >= PX_MIN) & F["O"].loc[d].notna() & F["C"].loc[d].notna()
    ok = ok.fillna(False)
    return pd.Series({s: bool(v) and not fund(s) for s, v in ok.items()})


def gaps(T: str, F: dict, fund=lambda s: False) -> list[dict]:
    """The gap names of T (|open/prev close - 1| >= 3%) among the eligible names."""
    el = eligible(T, F, fund)
    if el.empty:
        return []
    d = pd.Timestamp(T)
    out = []
    for s in el.index[el.to_numpy(bool)]:
        pc, o0 = float(F["PC"].loc[d, s]), float(F["O"].loc[d, s])
        g = o0 / pc - 1
        if abs(g) < GAP_MIN:
            continue
        c0, hi, lo = float(F["C"].loc[d, s]), float(F["H"].loc[d, s]), float(F["L"].loc[d, s])
        out.append(dict(sym=s, cls="up" if g > 0 else "down", gap=round(g, 5), prev=round(pc, 4), open0=round(o0, 4),
                        day_ret=round(c0 / pc - 1, 5), ibs=round((c0 - lo) / (hi - lo), 4) if hi > lo else None,
                        adv=round(float(F["ADV"].loc[d, s]))))
    return out


def night_bench(T: str, F: dict, fund=lambda s: False) -> dict | None:
    """EW overnight of all eligible names (univ) and of those that are not night-leg picks (univ_x); None until T+1's open prints."""
    d = pd.Timestamp(T)
    if d not in F["ON"].index or F["ON"].loc[d].notna().sum() == 0:
        return None
    el = eligible(T, F, fund)
    syms = [s for s in el.index[el.to_numpy(bool)] if np.isfinite(F["ON"].loc[d, s])]
    if not syms:
        return None
    on = F["ON"].loc[d, syms].astype(float)
    c, h, lo, pc = (F[k].loc[d, syms].astype(float) for k in ("C", "H", "L", "PC"))
    night = ((c / pc - 1) <= NIGHT_DR) & (((c - lo) / (h - lo).replace(0, np.nan)) < NIGHT_IBS)
    ux = on[~night.fillna(False).to_numpy(bool)]
    return dict(n_univ=len(syms), univ=round(float(on.mean()), 6), n_night=int(night.sum()),
                univ_x=round(float(ux.mean()), 6) if len(ux) else None)


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
                spy=round(so1 / sc0 - 1, 6), net5=round(raw - RT_BP / 1e4, 6))


def _tt(v: list[float]) -> float | None:
    return float(np.mean(v) / np.std(v, ddof=1) * np.sqrt(len(v))) if len(v) >= 3 and np.std(v, ddof=1) > 0 else None


def summary(rows: list[dict], backfill: bool = False) -> dict:
    """Per-night EW of the scored gap names; excess = night mean minus that night's univ (nights without a bench are not gated)."""
    bench = {r["T"]: r for r in rows if r.get("status") == "night" and bool(r.get("backfill")) == backfill and r.get("univ") is not None}
    sc = [r for r in rows if r.get("status") == "scored" and bool(r.get("backfill")) == backfill]
    by: dict[str, list[dict]] = {}
    for r in sc:
        by.setdefault(r["T"], []).append(r)
    nights = sorted(T for T in by if T in bench)
    out = dict(nights=len(nights), names=sum(len(by[T]) for T in nights), backfill=backfill, unbenched=len(set(by) - set(bench)))
    if not nights:
        return dict(out, raw_bp=None, excess_bp=None, excess_x_bp=None, net5_bp=None, t=None, median_bp=None, spy_bp=None,
                    up_excess_bp=None, down_excess_bp=None, up_nights=0, down_nights=0)
    raw = [st.mean(x["r"] for x in by[T]) for T in nights]
    exc = [st.mean(x["r"] for x in by[T]) - bench[T]["univ"] for T in nights]
    excx = [st.mean(x["r"] for x in by[T]) - bench[T]["univ_x"] for T in nights if bench[T].get("univ_x") is not None]
    spy = [st.mean(x["spy"] for x in by[T]) for T in nights]

    def arm(cls):
        v = [st.mean(x["r"] for x in by[T] if x["cls"] == cls) - bench[T]["univ"] for T in nights if any(x["cls"] == cls for x in by[T])]
        return (round(1e4 * st.mean(v), 1) if v else None), len(v)

    up, dn = arm("up"), arm("down")
    return dict(out, raw_bp=round(1e4 * st.mean(raw), 1), excess_bp=round(1e4 * st.mean(exc), 1),
                excess_x_bp=round(1e4 * st.mean(excx), 1) if excx else None, net5_bp=round(1e4 * (st.mean(exc) - RT_BP / 1e4), 1),
                t=None if _tt(exc) is None else round(_tt(exc), 2), median_bp=round(1e4 * st.median(exc), 1),
                spy_bp=round(1e4 * st.mean(spy), 1), up_excess_bp=up[0], up_nights=up[1], down_excess_bp=dn[0], down_nights=dn[1])


def verdict(s: dict) -> str:
    if s["nights"] < NEED:
        return f" ({s['nights']}/{NEED} gap nights)"
    if s["excess_bp"] >= 5 and (s.get("t") or 0) >= 2 and (s.get("median_bp") or 0) > 0:
        return " -> PASS at module gate (excess >= +5bp, t >= 2, median > 0): propose a live pilot (user decision)"
    return " -> FAIL" if s["excess_bp"] <= 0 else " -> HOLD"


def line(rows: list[dict]) -> str:
    s, b = summary(rows), summary(rows, True)
    if not s["nights"]:
        return (f"GAP-NIGHT-FWD: 0 forward gap nights yet (backfill {b['nights']}n/{b['names']} names raw {b['raw_bp']}bp, "
                f"excess vs univ {b['excess_bp']}bp, up {b['up_excess_bp']} / down {b['down_excess_bp']}; not gated)")
    return (f"GAP-NIGHT-FWD: {s['nights']}n/{s['names']} names raw {s['raw_bp']:+.1f}bp, excess vs univ {s['excess_bp']:+.1f} "
            f"(net5 {s['net5_bp']:+.1f}, vs univ-ex-night {s['excess_x_bp']}) t {s['t']} median {s['median_bp']:+.1f} | SPY {s['spy_bp']:+.1f} "
            f"| up {s['up_excess_bp']} (n {s['up_nights']}) down {s['down_excess_bp']} (n {s['down_nights']}){verdict(s)}")


def run(state_dir: Path, logs_dir: Path, log=print, today: dt.date | None = None, H: dict | None = None,
        bars_fn=None, crosses_fn=None, fund_fn=None, backfill: int = 0) -> dict:
    from . import marketdata as md
    from .exdate_open_shadow import _headers, is_fund
    from .pref_ex_shadow import crosses as _crosses
    bars_fn, crosses_fn = bars_fn or md.sip_daily, crosses_fn or _crosses
    today = today or dt.datetime.now(dt.timezone.utc).astimezone(ZoneInfo(md.ET)).date()
    state_dir = Path(state_dir)
    path = state_dir / LOG_NAME
    rows = _read(path)
    scanned = {r["T"] for r in rows if r.get("status") == "night"}
    syms = universe(state_dir)
    bench = bars_fn([BENCH], str(today - dt.timedelta(days=HIST_DAYS + 40)))[BENCH]
    sess = [str(d.date()) for d in bench.index if d.date() < today]
    todo = [(T, False) for T in sess if T >= START_T and T not in scanned]
    if backfill:
        bf = [T for T in sess[:-1] if T < START_T][-backfill:]      # T+1's open must already be complete
        todo = [(T, True) for T in bf if T not in scanned] + todo
    unbenched = [r for r in rows if r.get("status") == "night" and r.get("univ") is None]
    cache = None
    if (todo or unbenched) and syms:
        H = H or _headers()
        if fund_fn is None:
            apath = state_dir / ASSETS
            cache = json.loads(apath.read_text()) if apath.exists() else {}
            fund_fn = lambda s: is_fund(s, H, cache)  # noqa: E731
        d0 = (pd.Timestamp(min([T for T, _ in todo] + [r["T"] for r in unbenched])) - pd.DateOffset(days=HIST_DAYS)).strftime("%Y-%m-%d")
        bars = {}
        for i in range(0, len(syms), CHUNK):
            bars.update(bars_fn(syms[i:i + CHUNK], d0))
        F = wide(bars)
        for T, bf_flag in todo:
            hit = gaps(T, F, fund_fn)
            for h in hit:
                rows.append(dict(T=T, backfill=bf_flag, status="pending", **h))
            nb = night_bench(T, F, fund_fn) or {}
            rows.append(dict(dict(T=T, status="night", backfill=bf_flag, n_gap=len(hit), n_up=sum(1 for h in hit if h["cls"] == "up"),
                                  n_down=sum(1 for h in hit if h["cls"] == "down"), univ=None, univ_x=None), **nb))
            log(f"[gap-night] T {T}{' (backfill)' if bf_flag else ''}: gaps {len(hit)} (up {rows[-1]['n_up']} / down {rows[-1]['n_down']})"
                + (f", univ {1e4 * nb['univ']:+.1f}bp over {nb['n_univ']} names" if nb else ""))
        for r in unbenched:
            nb = night_bench(r["T"], F, fund_fn)
            if nb:
                r.update(nb)
        if cache is not None:
            (state_dir / ASSETS).write_text(json.dumps(cache))
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
    rows = sorted(rows, key=lambda r: (r["T"], r.get("status") != "night", r.get("cls", ""), r.get("sym", "")))
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    log(f"[gap-night] {line(rows)}")
    return summary(rows)


if __name__ == "__main__":
    import sys
    root = Path(__file__).resolve().parents[2]
    n = int(sys.argv[sys.argv.index("--backfill") + 1]) if "--backfill" in sys.argv else 0
    run(root / "state", root / "logs", backfill=n)
