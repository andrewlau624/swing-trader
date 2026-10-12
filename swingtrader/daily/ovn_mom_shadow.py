"""OVN-MOM-FWD forward shadow (round1_prose.md "Study OVN-MOM" + "Watch -- OVN-MOM-FWD", N 939): logs, never orders.

Rule (FROZEN at registration, 2026-10-12): on session d, rank the universe (close >= $5, 20d median $vol >= $20M over the
sessions BEFORE d, not a fund/ETF) by the mean overnight return open_s/close_{s-1}-1 over the last 252 nights ENDING WITH
d's OPEN (known before the 15:50 MOC cutoff; >= 200 valid nights, |night| > 50% dropped). Log the top decile (registered
arm) and the top 10 by score (executable at $2-25k). Buy the 16:00 official close of d, sell the next session's official
opening cross; excess = close->open of the pick minus SPY close->open on the same legs. Gate (decile, NEED nights): mean
gross excess >= +5bp/night, day-clustered t >= 2, median night > 0. Reported, not gated: top-10 arm, cross coverage.

Data path: SIP daily bars (marketdata.sip_daily, adjustment=all, so splits/dividends do not create false nights) for the night
leg's eligibility universe (state/daily-universe-*.json, close >= $5 and 20d $vol >= $10M; the $20M bar is re-applied here).
The overnight panel is cached incrementally in state/ovn-mom-panel.parquet (long: date, sym, r, close, usd); the first run
pulls ~400 calendar days for the whole universe, later runs only the new sessions (plus whole history for new names).
Official prints: pref_ex_shadow.crosses. Fund/ETF names are dropped via the Alpaca asset name (cached in
state/ovn-mom-assets.json). Caveats: the panel's close is the dividend/split-adjusted bar close (the research used raw close
for the $5 screen); the research dropped ex-action nights explicitly, here the adjusted bars neutralize them.
"""
from __future__ import annotations

import datetime as dt
import json
import statistics as st
from pathlib import Path

import numpy as np
import pandas as pd

LOG_NAME = "ovn-mom.jsonl"
PANEL = "ovn-mom-panel.parquet"
ASSETS = "ovn-mom-assets.json"
START = "2026-10-13"       # first forward session (watch registered 2026-10-12)
NEED = 120
GATE_BP = 5.0
WINDOW = 252
MIN_VALID = 200
PX_MIN = 5.0
USD_MIN = 20e6
BIG = 0.5
TOP_N = 10
BENCH = "SPY"
HIST_DAYS = 400
LOOKBACK_DAYS = 10


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


def universe(state_dir: Path) -> list[str]:
    files = sorted(Path(state_dir).glob("daily-universe-*.json"))
    if not files:
        return []
    rows = json.loads(files[-1].read_text())
    return sorted({r["symbol"] for r in rows if isinstance(r, dict) and "symbol" in r})


def wide(bars: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Date x symbol frames: R (night ending at that session's open), C (close), U ($ volume)."""
    r, c, u = {}, {}, {}
    for s, b in bars.items():
        if b is None or len(b) < 2:
            continue
        r[s] = b["open"] / b["close"].shift(1) - 1
        c[s] = b["close"]
        u[s] = b["close"] * b["volume"]
    return pd.DataFrame(r).sort_index(), pd.DataFrame(c).sort_index(), pd.DataFrame(u).sort_index()


def pick_day(day: str, R: pd.DataFrame, C: pd.DataFrame, U: pd.DataFrame, fund=lambda s: False) -> dict:
    """Ranking for session `day`. Score = mean of the last WINDOW valid-or-NaN nights ending with day's open (R rows <= day
    only); needs >= MIN_VALID valid nights. Returns dict(n_elig, rows=[...]) with decile / top-10 flags."""
    d = pd.Timestamp(day)
    if d not in R.index:
        return dict(n_elig=0, rows=[])
    i = R.index.get_loc(d)
    win = R.iloc[max(0, i - WINDOW + 1):i + 1]
    win = win.where(win.abs() <= BIG)
    valid = win.notna().sum()
    score = win.mean()
    prior_u = U.loc[U.index < d].iloc[-20:]
    med = prior_u.median() if len(prior_u) >= 10 else pd.Series(dtype=float)
    close = C.loc[d]
    if len(win) < WINDOW:
        return dict(n_elig=0, rows=[])
    ok = (valid >= MIN_VALID) & (close.reindex(score.index) >= PX_MIN) & (med.reindex(score.index) >= USD_MIN) & score.notna()
    elig = [s for s in score.index[ok.fillna(False).to_numpy(bool)] if not fund(s)]
    if not elig:
        return dict(n_elig=0, rows=[])
    sc = score[elig].sort_values(ascending=False, kind="mergesort")
    k = max(1, len(sc) // 10)
    rows = []
    for rank, (s, v) in enumerate(sc.iloc[:k].items(), 1):
        rows.append(dict(date=day, sym=s, rank=rank, score=round(float(v), 6), close=round(float(close[s]), 4),
                         n_elig=len(sc), decile=True, top10=rank <= TOP_N, status="pending"))
    return dict(n_elig=len(sc), rows=rows)


def score(r: dict, X: dict) -> dict | None:
    """Closing cross on the signal day -> next session's opening cross, and SPY on the same legs; None until it prints."""
    p = X.get(r["sym"], {})
    c0 = (p.get(r["date"]) or (None,) * 4)[2]
    later = sorted(d for d in p if d > r["date"])
    if not c0 or not later:
        return None
    o1 = p[later[0]][0]
    if not o1:
        return None
    ret = o1 / c0 - 1
    sp = X.get(BENCH, {})
    b0, b1 = (sp.get(r["date"]) or (None,) * 4)[2], (sp.get(later[0]) or (None,) * 4)[0]
    bench = (b1 / b0 - 1) if (b0 and b1) else None
    return dict(r, status="scored", exit=later[0], c0=c0, o1=o1, ret=round(ret, 6),
                bench=None if bench is None else round(bench, 6), xs=None if bench is None else round(ret - bench, 6))


def _night_means(rows: list[dict], key: str, only: str | None = None) -> list[float]:
    by: dict[str, list[float]] = {}
    for r in rows:
        if r.get("status") == "scored" and r.get(key) is not None and (only is None or r.get(only)):
            by.setdefault(r["date"], []).append(float(r[key]))
    return [st.mean(v) for _, v in sorted(by.items())]


def _arm(rows: list[dict], only: str | None) -> dict:
    x = _night_means(rows, "xs", only)
    out = dict(n=len(x), mean_bp=round(1e4 * st.mean(x), 1) if x else None,
               median_bp=round(1e4 * st.median(x), 1) if x else None, hit=round(sum(v > 0 for v in x) / len(x), 2) if x else None)
    if len(x) >= 2:
        sd = st.pstdev(x) * (len(x) / (len(x) - 1)) ** 0.5
        out["t"] = round(st.mean(x) / (sd / len(x) ** 0.5), 2) if sd > 0 else None
    return out


def summary(rows: list[dict]) -> dict:
    """Gate summary: per-night EW means of excess vs SPY (decile = registered arm; top-10 = reported)."""
    dec = _arm(rows, None)
    top = _arm(rows, "top10")
    picks = [r for r in rows if "sym" in r]
    nocross = sum(1 for r in picks if r.get("status") == "no_cross")
    scored = sum(1 for r in picks if r.get("status") == "scored")
    out = dict(days=dec["n"], mean_bp=dec["mean_bp"], median_bp=dec["median_bp"], t=dec.get("t"), hit=dec["hit"],
               top10=top, picks=len(picks), scored=scored, no_cross=nocross,
               pending=sum(1 for r in picks if r.get("status") == "pending"))
    return out


def verdict(s: dict) -> str:
    if s["days"] < NEED or s["mean_bp"] is None:
        return ""
    if s["mean_bp"] >= GATE_BP and (s.get("t") or 0) >= 2 and (s["median_bp"] or 0) > 0:
        return " -> PASS (mean >= +5bp, t >= 2, median > 0)"
    return " -> FAIL (class closed)" if s["mean_bp"] <= 0 else " -> HOLD"


def line(rows: list[dict]) -> str:
    s = summary(rows)
    if not s["days"]:
        return f"0/{NEED} nights scored ({s['pending']} picks pending)"
    t10 = s["top10"]
    body = (f"{s['days']}/{NEED} nights: decile excess vs SPY {s['mean_bp']:+.1f}bp/night (median {s['median_bp']:+.1f}, "
            f"hit {s['hit']:.0%}" + (f", t {s['t']}" if s.get("t") is not None else "") + ")"
            + (f"; top-10 {t10['mean_bp']:+.1f}bp" if t10["mean_bp"] is not None else "")
            + f"; no cross {s['no_cross']}/{s['scored'] + s['no_cross']}")
    return body + verdict(s)


def update_panel(state_dir: Path, uni: list[str], today: dt.date, bars_fn) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Incrementally maintained long panel (date, sym, r, close, usd) of completed sessions; returns the wide frames."""
    path = Path(state_dir) / PANEL
    old = pd.read_parquet(path) if path.exists() else pd.DataFrame(columns=["date", "sym", "r", "close", "usd"])
    old["date"] = pd.to_datetime(old["date"])
    have = set(old["sym"])
    new_syms = [s for s in uni if s not in have]
    cut = pd.Timestamp(today)
    parts = [old]
    if len(old):
        last = old["date"].max()
        fresh = [s for s in uni if s in have]
        if fresh:
            parts.append(_long(*wide(bars_fn(fresh, last - pd.Timedelta(days=7), today)), after=last, today=cut))
        if new_syms:
            parts.append(_long(*wide(bars_fn(new_syms, cut - pd.Timedelta(days=HIST_DAYS), today)), after=None, today=cut))
    elif uni:
        parts.append(_long(*wide(bars_fn(uni, cut - pd.Timedelta(days=HIST_DAYS), today)), after=None, today=cut))
    df = pd.concat([p for p in parts if len(p)], ignore_index=True).drop_duplicates(["date", "sym"], keep="first")
    df = df[df["date"] >= cut - pd.Timedelta(days=HIST_DAYS + 30)]
    Path(state_dir).mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return tuple(df.pivot(index="date", columns="sym", values=v).sort_index() for v in ("r", "close", "usd"))


def _long(R, C, U, after, today: pd.Timestamp) -> pd.DataFrame:
    out = pd.DataFrame({"r": R.stack(future_stack=True), "close": C.stack(future_stack=True), "usd": U.stack(future_stack=True)}).dropna(subset=["close"])
    out = out.rename_axis(["date", "sym"]).reset_index()
    out = out[out["date"] < today]
    if after is not None:
        out = out[out["date"] > after]
    return out


def sessions_to_scan(bench_bars: pd.DataFrame, done: set[str], today: dt.date) -> list[str]:
    days = [str(d.date()) for d in bench_bars.index if START <= str(d.date()) and d.date() < today]
    return sorted(d for d in days if d not in done)


def run(state_dir: Path, logs_dir: Path, log=print, today: dt.date | None = None, H: dict | None = None,
        bars_fn=None, crosses_fn=None, fund_fn=None) -> dict:
    from . import marketdata as md
    from .exdate_open_shadow import _headers, is_fund
    from .pref_ex_shadow import crosses as _crosses
    bars_fn = bars_fn or md.sip_daily
    crosses_fn = crosses_fn or _crosses
    state_dir = Path(state_dir)
    path = state_dir / LOG_NAME
    rows = _read(path)
    today = today or dt.date.today()
    uni = universe(state_dir)
    done = {r["date"] for r in rows if r.get("status") == "scanned"}
    bench = bars_fn([BENCH], today - dt.timedelta(days=LOOKBACK_DAYS), today).get(BENCH)
    todo = sessions_to_scan(bench, done, today) if bench is not None and uni else []
    if todo:
        R, C, U = update_panel(state_dir, uni, today, bars_fn)
        if fund_fn is None:
            H = H or _headers()
            apath = state_dir / ASSETS
            cache = json.loads(apath.read_text()) if apath.exists() else {}
            fund_fn = lambda s: is_fund(s, H, cache)  # noqa: E731
        else:
            cache = None
        for d in todo:
            res = pick_day(d, R, C, U, fund_fn)
            rows += res["rows"]
            rows.append(dict(date=d, status="scanned", n_elig=res["n_elig"], n_picks=len(res["rows"])))
            log(f"[ovn-mom] {d}: {res['n_elig']} eligible, {len(res['rows'])} decile picks "
                f"(top: {', '.join(r['sym'] for r in res['rows'][:TOP_N])})")
        if cache is not None:
            (state_dir / ASSETS).write_text(json.dumps(cache))
    pend = [r for r in rows if r.get("status") == "pending" and r["date"] < str(today)]
    if pend:
        H = H or _headers()
        end = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
        syms = sorted({r["sym"] for r in pend} | {BENCH})
        d0 = min(r["date"] for r in pend)
        X: dict = {}
        for i in range(0, len(syms), 40):
            X.update(crosses_fn(syms[i:i + 40], d0, end, H))
        new = []
        for r in rows:
            if r.get("status") == "pending" and r["date"] < str(today):
                s = score(r, X)
                if s:
                    r = s
                elif r["date"] <= str(today - dt.timedelta(days=6)):
                    r = dict(r, status="no_cross")
            new.append(r)
        rows = new
    rows = sorted(rows, key=lambda r: (r["date"], r.get("rank", 0), r.get("sym", "")))
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    log(f"[ovn-mom] {line(rows)}")
    return summary(rows)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    run(root / "state", root / "logs")
