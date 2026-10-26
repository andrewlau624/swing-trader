"""NIGHT-LETF-TILT forward shadow (round1_prose.md "RESULT - LETF-REV (N 1065)", tilt read): logs, never orders.

Question: among the live night leg's OWN picks (day_ret <= -8% & IBS < 0.10 at 15:40, bought at the official close cross, sold
at the next official open cross), do the names a single-stock leveraged ETF had to sell at the close bounce harder at the open?
LETF-REV (Sharadar, 2022-07..2026-09): picks with pressure I >= 0.05 earned +99.6bp/night net (88 nights, 30 names, t 3.33) vs
+21.6 for picks with I = 0; paired nights +57.9 (median +62, t 1.66, 76 nights). 2024-26 only, 30 names: EDGE UNPROVEN. The
shape is a night-leg weight tilt (a size-up), which CLAUDE.md makes a user decision, so this is a log-only forward shadow.

Rule (FROZEN at registration 2026-10-26, no re-tuning): every 15:40 night-rule signal in state/night-candidates.jsonl (written by
the night leg via repeat_shadow.log_candidates, both accounts, before dedupe / vol / cash / wash filters) is tagged with the
day's LETF pressure
    I = sum over the name's single-stock LETFs f of  w_f x median($vol_f over the 20 prior sessions, >= 5)  /  median($vol_name over
        the 20 prior sessions, >= 15),      w_f = L(L-1)/2 (L = +2 -> 1, L = -2 -> 3, L = 1.5 -> 0.375),  I = 0 when undefined,
exactly research/sim/ss_letf.panel() (a fund counts only on sessions where it printed a bar, as the panel's (fund, date) merge
does). tilt = I >= 0.05; rest = everything else (I = 0 and 0 < I < 0.05 are reported apart, never selected on).
Return per pick: the same official-cross score repeat_shadow writes on the candidate row (close cross of T -> open cross of the
next session), copied, never re-priced; net = ret - 10bp (5bp/side, the LETF-REV convention).
Gate (module scale): NEED forward nights with >= 1 scored tilt pick. At the gate, PASS = night-paired (tilt EW - rest EW)
>= +30bp, t >= 2, paired median > 0 -> propose a night-leg weight tilt (user decision); FAIL = paired <= 0; else HOLD.

Data: LETF -> underlying map data/letf_map.csv (Sharadar tickers.parquet via ss_letf.fund_map; the server has no Sharadar, so it is
regenerated monthly on the Mac with `make letf-map` and committed); SIP daily bars (marketdata.sip_daily, adjustment "all": $vol is
split-neutral) for the fund and name $ volumes.
Backfill rows (--backfill N candidate sessions before START_T) are look-alikes: logged, labelled, excluded from the gate.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import statistics as st
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

LOG_NAME = "night-letf-tilt.jsonl"
MAP = Path(__file__).resolve().parents[2] / "data" / "letf_map.csv"
START_T = "2026-10-27"           # first forward candidate session (shadow registered 2026-10-26)
NEED = 40                        # forward nights with a scored tilt pick
I_MIN = 0.05
RT_BP = 10.0                     # 5bp/side, as LETF-REV
FUND_MIN, UND_MIN = 5, 15        # min prior sessions in the two 20d medians (ss_letf.panel)
HIST_DAYS = 45
CHUNK = 200


def _read(path: Path) -> list[dict]:
    from .repeat_shadow import _read as r
    return r(path)


def build_map(path: Path = MAP) -> int:
    """Mac only: data/letf_map.csv from Sharadar tickers.parquet with ss_letf.fund_map (same PATS, same leverage rule)."""
    from research.sim.ss_letf import fund_map
    f = fund_map().sort_values(["u", "ticker"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        fh.write(f"# built {dt.date.today().isoformat()} from Sharadar tickers.parquet by research/sim/ss_letf.fund_map; "
                 "regenerate monthly on the Mac (make letf-map) and commit\n")
        w = csv.writer(fh)
        w.writerow(["fund", "underlying", "lev", "w", "sign", "name"])
        for r in f.itertuples():
            w.writerow([r.ticker, r.u, r.lev, r.w, int(np.sign(r.lev)), r.name])
    return len(f)


def load_map(path: Path = MAP) -> dict[str, dict[str, float]]:
    """underlying -> {fund: w} (w = L(L-1)/2, the leverage demand weight of ss_letf.fund_map)."""
    out: dict[str, dict[str, float]] = {}
    if not Path(path).exists():
        return out
    with Path(path).open() as fh:
        for r in csv.DictReader(ln for ln in fh if not ln.startswith("#")):
            out.setdefault(r["underlying"], {})[r["fund"]] = float(r["w"])
    return out


def _dv20(b: pd.DataFrame | None, d: pd.Timestamp, n_min: int) -> float | None:
    """Median $vol of the (up to) 20 sessions before d, None with fewer than n_min; the ss_letf shift(1).rolling(20) median."""
    if b is None or b.empty:
        return None
    p = b[b.index < d].iloc[-20:]
    if len(p) < n_min:
        return None
    v = float((p["close"] * p["volume"]).median())
    return v if np.isfinite(v) else None


def pressure(T: str, sym: str, bars: dict[str, pd.DataFrame], fmap: dict[str, dict[str, float]]) -> dict:
    """I for (T, sym) as ss_letf.panel(): sum_f w_f x fund dv20 / name udv20; 0.0 when undefined; funds without a bar on T skip."""
    d = pd.Timestamp(T)
    b = bars.get(sym)
    out = dict(I=0.0, udv20=None, fdv=None, n_funds=0)
    if b is None or d not in b.index:
        return out
    udv20 = _dv20(b, d, UND_MIN)
    fdv, n = 0.0, 0
    for f in sorted(fmap.get(sym, {})):
        fb = bars.get(f)
        if fb is None or d not in fb.index:
            continue
        v = _dv20(fb, d, FUND_MIN)
        if v is None:
            continue
        fdv += fmap[sym][f] * v
        n += 1
    out.update(udv20=None if udv20 is None else round(udv20), fdv=round(fdv) if n else None, n_funds=n)
    if udv20 and n:
        out["I"] = round(fdv / udv20, 5)
    return out


def _tt(v: list[float]) -> float | None:
    return float(np.mean(v) / np.std(v, ddof=1) * np.sqrt(len(v))) if len(v) >= 3 and np.std(v, ddof=1) > 0 else None


def _grp(rs: list[dict]) -> dict:
    by: dict[str, list[float]] = {}
    for r in rs:
        by.setdefault(r["T"], []).append(r["ret"])
    if not rs:
        return dict(n=0, nights=0, mean_bp=None, median_bp=None, hit=None, ew_bp=None, net_bp=None, t=None)
    x = [r["ret"] for r in rs]
    ew = [st.mean(v) for v in by.values()]
    return dict(n=len(x), nights=len(by), mean_bp=round(1e4 * st.mean(x), 1), median_bp=round(1e4 * st.median(x), 1),
                hit=round(sum(1 for v in x if v > 0) / len(x), 2), ew_bp=round(1e4 * st.mean(ew), 1),
                net_bp=round(1e4 * st.mean(ew) - RT_BP, 1), t=None if _tt(ew) is None else round(_tt(ew), 2))


def summary(rows: list[dict], backfill: bool = False) -> dict:
    """tilt (I >= 0.05) vs rest over the scored picks; paired = per night (tilt EW - rest EW) where both exist; gate = tilt nights."""
    sc = [r for r in rows if r.get("status") == "scored" and bool(r.get("backfill")) == backfill and r.get("ret") is not None]
    tilt = [r for r in sc if r.get("tilt")]
    rest = [r for r in sc if not r.get("tilt")]
    zero = [r for r in rest if not r.get("I")]
    low = [r for r in rest if r.get("I")]
    by: dict[str, dict[str, list[float]]] = {}
    for r in sc:
        by.setdefault(r["T"], {}).setdefault("tilt" if r.get("tilt") else "rest", []).append(r["ret"])
    diff = [st.mean(v["tilt"]) - st.mean(v["rest"]) for T, v in sorted(by.items()) if "tilt" in v and "rest" in v]
    pend = sum(1 for r in rows if r.get("status") == "pending" and bool(r.get("backfill")) == backfill)
    paired = dict(nights=len(diff), mean_bp=round(1e4 * st.mean(diff), 1) if diff else None,
                  median_bp=round(1e4 * st.median(diff), 1) if diff else None,
                  hit=round(sum(1 for v in diff if v > 0) / len(diff), 2) if diff else None,
                  t=None if _tt(diff) is None else round(_tt(diff), 2))
    return dict(backfill=backfill, picks=len(sc), pending=pend, tilt_nights=len({r["T"] for r in tilt}),
                tilt=_grp(tilt), rest=_grp(rest), zero=_grp(zero), low=_grp(low), paired=paired)


def verdict(s: dict) -> str:
    if s["tilt_nights"] < NEED:
        return f" ({s['tilt_nights']}/{NEED} tilt nights)"
    p = s["paired"]
    if (p["mean_bp"] or 0) >= 30 and (p["t"] or 0) >= 2 and (p["median_bp"] or 0) > 0:
        return " -> PASS at module gate (paired >= +30bp, t >= 2, median > 0): propose a night-leg weight tilt (user decision)"
    return " -> FAIL" if (p["mean_bp"] or 0) <= 0 else " -> HOLD"


def _g(g: dict) -> str:
    if not g["n"]:
        return "none"
    return f"{g['ew_bp']:+.1f}bp/night (n {g['n']}/{g['nights']}n, median {g['median_bp']:+.1f}, hit {g['hit']:.2f}, t {g['t']})"


def line(rows: list[dict]) -> str:
    s, b = summary(rows), summary(rows, True)
    if not s["picks"]:
        bf = f"; backfill {b['picks']} picks: tilt {_g(b['tilt'])} vs rest {_g(b['rest'])}, paired {b['paired']['mean_bp']}bp over {b['paired']['nights']}n (not gated)" if b["picks"] else ""
        return f"NIGHT-LETF-TILT: 0 forward picks scored yet ({s['pending']} pending){bf}"
    p = s["paired"]
    return (f"NIGHT-LETF-TILT: {s['picks']} picks: tilt {_g(s['tilt'])} vs rest {_g(s['rest'])} "
            f"[I=0 {s['zero']['ew_bp']}, 0<I<.05 {s['low']['ew_bp']}] | paired tilt-rest {p['mean_bp']}bp "
            f"(median {p['median_bp']}, hit {p['hit']}, t {p['t']}, {p['nights']}n) | net at 10bp RT{verdict(s)}")


def _score_from(r: dict, c: dict | None) -> dict:
    """Copy repeat_shadow's official-cross score off the candidate row; a candidate that never printed closes the row the same way."""
    if not c or c.get("status") == "pending":
        return r
    if c.get("status") == "scored" and c.get("ret") is not None:
        ret = float(c["ret"])
        return dict(r, status="scored", exit=c.get("exit"), c0=c.get("close_cross"), o1=c.get("open_cross"), ret=round(ret, 6),
                    net=round(ret - RT_BP / 1e4, 6))
    return dict(r, status=c.get("status"))


def run(state_dir: Path, logs_dir: Path, log=print, today: dt.date | None = None, bars_fn=None, backfill: int = 0,
        map_path: Path = MAP) -> dict:
    from . import marketdata as md
    from .repeat_shadow import LOG_NAME as CAND
    bars_fn = bars_fn or md.sip_daily
    today = today or dt.datetime.now(dt.timezone.utc).astimezone(ZoneInfo(md.ET)).date()
    state_dir = Path(state_dir)
    path = state_dir / LOG_NAME
    rows = _read(path)
    cands = _read(state_dir / CAND)
    fmap = load_map(map_path)
    if not fmap:
        log(f"[night-letf-tilt] no LETF map at {map_path} (make letf-map on the Mac and commit); nothing tagged")
    by_date: dict[str, dict[str, dict]] = {}
    for c in cands:
        if c.get("date") and c.get("sym"):
            by_date.setdefault(c["date"], {}).setdefault(c["sym"], c)
    scanned = {r["T"] for r in rows if r.get("status") == "night"}
    sess = sorted(T for T in by_date if T < str(today))
    todo = [(T, False) for T in sess if T >= START_T and T not in scanned]
    if backfill:
        todo = [(T, True) for T in [T for T in sess if T < START_T][-backfill:] if T not in scanned] + todo
    if todo and fmap:
        syms = sorted({s for T, _ in todo for s in by_date[T]})
        funds = sorted({f for s in syms for f in fmap.get(s, {})})
        d0 = (pd.Timestamp(min(T for T, _ in todo)) - pd.DateOffset(days=HIST_DAYS)).strftime("%Y-%m-%d")
        bars: dict[str, pd.DataFrame] = {}
        pull = syms + funds
        for i in range(0, len(pull), CHUNK):
            bars.update(bars_fn(pull[i:i + CHUNK], d0))
        for T, bf in todo:
            n_t = 0
            for sym, c in sorted(by_date[T].items()):
                p = pressure(T, sym, bars, fmap)
                tilt = p["I"] >= I_MIN
                n_t += tilt
                rows.append(dict(T=T, sym=sym, account=c.get("account"), day_ret=c.get("day_ret"), ibs=c.get("ibs"), **p,
                                 tilt=tilt, backfill=bf, status="pending"))
            rows.append(dict(T=T, status="night", backfill=bf, n_picks=len(by_date[T]), n_tilt=n_t))
            log(f"[night-letf-tilt] T {T}{' (backfill)' if bf else ''}: {len(by_date[T])} picks, {n_t} with I >= {I_MIN}"
                + (": " + ", ".join(f"{r['sym']} {r['I']:.2f}" for r in rows if r.get("T") == T and r.get("tilt")) if n_t else ""))
    rows = [_score_from(r, by_date.get(r["T"], {}).get(r.get("sym"))) if r.get("status") == "pending" else r for r in rows]
    rows = sorted(rows, key=lambda r: (r["T"], r.get("status") != "night", r.get("sym", "")))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    log(f"[night-letf-tilt] {line(rows)}")
    return summary(rows)


if __name__ == "__main__":
    import sys
    root = Path(__file__).resolve().parents[2]
    if "--build-map" in sys.argv:
        print(f"{build_map()} single-stock LETFs -> {MAP}")
    else:
        n = int(sys.argv[sys.argv.index("--backfill") + 1]) if "--backfill" in sys.argv else 0
        run(root / "state", root / "logs", backfill=n)
