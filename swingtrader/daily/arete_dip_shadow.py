"""ARETE-DIP-FWD forward shadow (round1_prose.md "Watch -- ARETE-DIP-FWD", N 946): logs, never orders.

Origin: ../alpha-chasers (a Discord alert service, arete1061). His picks are liquid high-momentum, high-volatility names
bought AFTER a run, which loses; the same kind of name bought on a down day beat the market in 2021-24 and 2025-26 but
LOST on untouched 2016-20 (alpha-chasers PREREG3/PREREG4: KILL on the frozen bar; no market-state gate fixed it). This
watch therefore tests one narrow claim forward: does the post-2020 regime that pays for it persist?

Rule (FROZEN at registration, 2026-10-13): on session d, eligible = close >= $5 and 20d mean $vol >= $20M (sessions up to
and including d). Profile: 60d return >= +20 %, close > 50d average, 20d return > SPY's, 20d log-return vol in the top
third of the eligible names that day. Dip: IBS = (close-low)/(high-low) < 0.2 and 1d return <= -2 %. Every profile+dip
name is logged at d's close. Score: close d -> close d+3 and d+5, minus the equal-weight return of all names eligible on
d over the same holding, minus 20bp round trip. Gate (primary = d+5, per signal day, NEED days): mean > 0 with t >= 2 and
median day > 0 -> PASS (user decision). Mean <= 0 -> FAIL, class closed. Otherwise HOLD.

Data path: SIP daily bars (marketdata.sip_daily, adjusted) for the night leg's eligibility universe
(state/daily-universe-*.json), cached in state/arete-dip-panel.parquet. Caveats: bar close stands in for the official
closing cross; the research universe included ETFs and so does this one (whatever the daily universe holds).
"""
from __future__ import annotations

import datetime as dt
import json
import statistics as st
from pathlib import Path

import numpy as np
import pandas as pd

from .ovn_mom_shadow import _read, universe

LOG_NAME = "arete-dip.jsonl"
PANEL = "arete-dip-panel.parquet"
START = "2026-10-14"       # first forward session (watch registered 2026-10-13)
NEED = 60                  # signal days with a scored d+5
HOLDS = (3, 5)
PRIMARY = 5
COST = 0.002
PX_MIN = 5.0
USD_MIN = 20e6
BENCH = "SPY"
HIST_DAYS = 150
COLS = ("high", "low", "close", "volume")


def wide(bars: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Date x symbol frames for high, low, close, volume."""
    out = {}
    for k in COLS:
        out[k] = pd.DataFrame({s: b[k] for s, b in bars.items() if b is not None and len(b)}).sort_index()
    return out


def eligible(i: int, W: dict[str, pd.DataFrame]) -> pd.Index:
    C, V = W["close"], W["volume"]
    if i < 19:
        return pd.Index([])
    usd = (C.iloc[i - 19:i + 1] * V.iloc[i - 19:i + 1]).mean()
    ok = (C.iloc[i] >= PX_MIN) & (usd >= USD_MIN)
    return C.columns[ok.fillna(False).to_numpy(bool)]


def pick_day(day: str, W: dict[str, pd.DataFrame]) -> dict:
    C, H, L = W["close"], W["high"], W["low"]
    d = pd.Timestamp(day)
    if d not in C.index:
        return dict(n_elig=0, rows=[])
    i = C.index.get_loc(d)
    if i < 60 or BENCH not in C.columns:
        return dict(n_elig=0, rows=[])
    el = eligible(i, W)
    if not len(el):
        return dict(n_elig=0, rows=[])
    c = C.iloc[i]
    r1 = c / C.iloc[i - 1] - 1
    r20 = c / C.iloc[i - 20] - 1
    r60 = c / C.iloc[i - 60] - 1
    sma50 = C.iloc[i - 49:i + 1].mean()
    vol20 = np.log(C.iloc[i - 20:i + 1]).diff().std()
    rng = (H.iloc[i] - L.iloc[i]).where(lambda x: x > 0)
    ibs = (c - L.iloc[i]) / rng
    vol_hi = vol20[el].rank(pct=True) >= 2 / 3
    spy_r20 = r20.get(BENCH)
    prof = (r60[el] >= 0.20) & (c[el] > sma50[el]) & (r20[el] - spy_r20 > 0) & vol_hi
    dip = (ibs[el] < 0.2) & (r1[el] <= -0.02)
    picks = [s for s in el[(prof & dip).fillna(False).to_numpy(bool)] if s != BENCH]
    rows = [dict(date=day, sym=s, close=round(float(c[s]), 4), r1=round(float(r1[s]), 4), ibs=round(float(ibs[s]), 3),
                 r60=round(float(r60[s]), 3), n_elig=len(el), status="pending") for s in sorted(picks)]
    return dict(n_elig=len(el), rows=rows)


def score(r: dict, W: dict[str, pd.DataFrame]) -> dict | None:
    """Close d -> close d+h for h in HOLDS, minus the eligible-universe EW return and COST; None until d+PRIMARY prints."""
    C = W["close"]
    d = pd.Timestamp(r["date"])
    if d not in C.index or r["sym"] not in C.columns:
        return None
    i = C.index.get_loc(d)
    if i + PRIMARY >= len(C.index):
        return None
    el = eligible(i, W)
    out = dict(r, status="scored")
    for h in HOLDS:
        ret = C[r["sym"]].iloc[i + h] / C[r["sym"]].iloc[i] - 1
        bench = (C[el].iloc[i + h] / C[el].iloc[i] - 1).mean()
        out[f"xs{h}"] = None if pd.isna(ret) or pd.isna(bench) else round(float(ret - bench - COST), 6)
    return out


def _day_means(rows: list[dict], key: str) -> list[float]:
    by: dict[str, list[float]] = {}
    for r in rows:
        if r.get("status") == "scored" and r.get(key) is not None:
            by.setdefault(r["date"], []).append(float(r[key]))
    return [st.mean(v) for _, v in sorted(by.items())]


def summary(rows: list[dict]) -> dict:
    out = dict(picks=sum(1 for r in rows if "sym" in r), pending=sum(1 for r in rows if r.get("status") == "pending"))
    for h in HOLDS:
        x = _day_means(rows, f"xs{h}")
        s = dict(n=len(x), mean_bp=round(1e4 * st.mean(x), 1) if x else None,
                 median_bp=round(1e4 * st.median(x), 1) if x else None,
                 hit=round(sum(v > 0 for v in x) / len(x), 2) if x else None, t=None)
        if len(x) >= 2:
            sd = st.stdev(x)
            s["t"] = round(st.mean(x) / (sd / len(x) ** 0.5), 2) if sd > 0 else None
        out[f"d{h}"] = s
    out["days"] = out[f"d{PRIMARY}"]["n"]
    return out


def verdict(s: dict) -> str:
    p = s[f"d{PRIMARY}"]
    if p["n"] < NEED or p["mean_bp"] is None:
        return ""
    if p["mean_bp"] > 0 and (p["t"] or 0) >= 2 and (p["median_bp"] or 0) > 0:
        return " -> PASS (mean > 0, t >= 2, median > 0)"
    return " -> FAIL (class closed)" if p["mean_bp"] <= 0 else " -> HOLD"


def line(rows: list[dict]) -> str:
    s = summary(rows)
    p, q = s[f"d{PRIMARY}"], s["d3"]
    if not p["n"]:
        return f"0/{NEED} signal days scored ({s['pending']} picks pending)"
    body = (f"{p['n']}/{NEED} signal days: d+5 excess vs EW universe {p['mean_bp']:+.1f}bp (median {p['median_bp']:+.1f}, "
            f"hit {p['hit']:.0%}" + (f", t {p['t']}" if p["t"] is not None else "") + ")"
            + (f"; d+3 {q['mean_bp']:+.1f}bp" if q["mean_bp"] is not None else "") + f"; picks {s['picks']}")
    return body + verdict(s)


def update_panel(state_dir: Path, uni: list[str], today: dt.date, bars_fn) -> dict[str, pd.DataFrame]:
    """Incrementally cached long panel (date, sym, high, low, close, volume) of completed sessions."""
    path = Path(state_dir) / PANEL
    cols = ["date", "sym", *COLS]
    old = pd.read_parquet(path) if path.exists() else pd.DataFrame(columns=cols)
    old["date"] = pd.to_datetime(old["date"])
    have = set(old["sym"])
    cut = pd.Timestamp(today)
    syms = sorted(set(uni) | {BENCH})
    parts = [old]

    def _long(bars, after):
        W = wide(bars)
        df = pd.DataFrame({k: W[k].stack(future_stack=True) for k in COLS}).dropna(subset=["close"])
        df = df.rename_axis(["date", "sym"]).reset_index()
        df = df[df["date"] < cut]
        return df[df["date"] > after] if after is not None else df

    if len(old):
        last = old["date"].max()
        fresh = [s for s in syms if s in have]
        new = [s for s in syms if s not in have]
        if fresh:
            parts.append(_long(bars_fn(fresh, last - pd.Timedelta(days=7), today), after=last))
        if new:
            parts.append(_long(bars_fn(new, cut - pd.Timedelta(days=HIST_DAYS), today), after=None))
    else:
        parts.append(_long(bars_fn(syms, cut - pd.Timedelta(days=HIST_DAYS), today), after=None))
    df = pd.concat([p for p in parts if len(p)], ignore_index=True).drop_duplicates(["date", "sym"], keep="first")
    df = df[df["date"] >= cut - pd.Timedelta(days=HIST_DAYS + 30)]
    Path(state_dir).mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return {k: df.pivot(index="date", columns="sym", values=k).sort_index() for k in COLS}


def run(state_dir: Path, logs_dir: Path, log=print, today: dt.date | None = None, bars_fn=None) -> dict:
    from . import marketdata as md
    bars_fn = bars_fn or md.sip_daily
    state_dir = Path(state_dir)
    path = state_dir / LOG_NAME
    rows = _read(path)
    today = today or dt.date.today()
    uni = universe(state_dir)
    done = {r["date"] for r in rows if r.get("status") == "scanned"}
    pend = [r for r in rows if r.get("status") == "pending"]
    W = None
    if uni:
        bench = bars_fn([BENCH], today - dt.timedelta(days=10), today).get(BENCH)
        todo = sorted(str(d.date()) for d in (bench.index if bench is not None else [])
                      if START <= str(d.date()) and d.date() < today and str(d.date()) not in done)
        if todo or pend:
            W = update_panel(state_dir, uni, today, bars_fn)
        for d in todo:
            res = pick_day(d, W)
            rows += res["rows"]
            rows.append(dict(date=d, status="scanned", n_elig=res["n_elig"], n_picks=len(res["rows"])))
            log(f"[arete-dip] {d}: {res['n_elig']} eligible, {len(res['rows'])} picks "
                f"({', '.join(r['sym'] for r in res['rows'][:10])})")
    if W is not None:
        rows = [(score(r, W) or r) if r.get("status") == "pending" else r for r in rows]
    rows = sorted(rows, key=lambda r: (r["date"], r.get("sym", "")))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    log(f"[arete-dip] {line(rows)}")
    return summary(rows)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    run(root / "state", root / "logs")
