"""SEQ-TILT-FWD forward shadow (round1_prose.md "Study SEQ-TILT-FWD", N 1196): logs, never orders.

Question: does the frozen SEQ-NIGHT Ridge (N 1038: 105 indicator-sequence features, fit 1999-2015; judge 2016-26 top-minus-
bottom +31.6bp t 2.1, GBM walk-forward tilt +1.4 bp/night t 1.5, 2023-25 negative) still rank the live night picks forward?

Pick set (rebuilt independently of account size and cash, so a $2.3k account's zero-share skips do not thin it):
  every 15:40 rule signal the night leg logged (state/night-candidates.jsonl, repeat_shadow.log_candidates, both accounts)
  -> funds dropped (the research pool is Sharadar SEP common stock) -> vol20 >= 0.60 (live floor) -> the live duplicate-bet
  check (signals.dedupe_correlated, most-beaten first, 20d log-return corr > 0.7) = the night's picks.
Features: research.sim.seq_night.features() itself, on a per-night wide frame:
  * sessions BEFORE T: Alpaca SIP daily bars, adjustment=split (Sharadar SEP is split-adjusted, not dividend-adjusted).
    Regular-hours: the 09:15 marketdata.daily_bar_check canary asserts these bars equal regular-hours minutes 09:30-16:00.
  * session T (the decision row): marketdata.rth_minutes(T, 1540) = SIP 1-minute bars 09:30-15:40, regular hours by
    construction: open = 09:30 minute open, high/low through 15:40, close = the 15:40 price the leg decides on, volume
    09:30-15:40 (the research row used the full day: volume features read ~10% low, a constant across picks), raw prices
    (no split on T: the leg skips prev-close mismatches).
  vol20 / log_adv / day_ret / log_px follow the SEL-NIGHT pool definitions (prior-20 sessions; log of the raw 15:40 price).
  Sector from the committed Sharadar map (seq_tilt_sectors.json); ssr; repeat = picked in the previous 5 pick-nights here.
  Night-constant inputs (SPY state, breadth, weekday, n_picks) shift every score of a night equally: they cannot change a
  rank, z or tilt, so they are left out and `score` is the within-night score.
Tilt (research night_replays): z = (s - mean) / std over the night, m = clip(1 + 0.25 z, 0.25, 2) / mean.
Scoring: the official closing cross of T -> the official opening cross of T+1 (the leg's two auctions), r = o1 / c0 - 1.
Readout per night: delta_ew = mean(m r) - mean(r) (n >= 2; the gate), delta_v1 = same on the live tilt-v1 weights, tmb = top
half minus bottom half by score (n >= 4).
Gate (frozen 2026-11-09): at NEED gate nights, PASS = delta_ew > 0 with night t >= 2 AND tmb > 0; KILL = delta_ew <= 0;
otherwise HOLD to NEED2 nights, then PASS by the same rule or KILL. PASS means "propose the Ridge tilt" (user decision).
Rows for signal dates before START_T are backfill (seed the repeat flag; logged, excluded from the gate).
"""
from __future__ import annotations

import datetime as dt
import json
import statistics as st
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

LOG_NAME = "seq-tilt.jsonl"
CAND_LOG = "night-candidates.jsonl"          # repeat_shadow.LOG_NAME, written by the night leg at 15:40
START_T = "2026-11-10"                        # first forward signal session (registered 2026-11-09)
NEED, NEED2 = 60, 120
VOL_MIN, MAX_CORR = 0.60, 0.7                 # config daily.night_vol_min / night_max_corr (2026-11-09)
TILT_K, M_LO, M_HI = 0.25, 0.25, 2.0          # seq_night.night_replays
REPEAT = 5
HIST_DAYS = 1100                              # calendar days of prior bars (252-bar windows + EMA warm-up)
HERE = Path(__file__).resolve().parent
MODEL_PATH, SECTOR_PATH = HERE / "seq_tilt_ridge.json", HERE / "seq_tilt_sectors.json"
ET = "America/New_York"


def _read(path: Path) -> list[dict]:
    from .ovn_mom_shadow import _read as r
    return r(path)


def load_model(path: Path = MODEL_PATH) -> dict:
    return json.loads(Path(path).read_text())


def load_sectors(path: Path = SECTOR_PATH) -> dict[str, str]:
    if not Path(path).exists():
        return {}
    return {t: s for s, ts in json.loads(Path(path).read_text()).items() for t in ts}


# ----------------------------------------------------------------------------- features
def features_at(T: str, bars: dict[str, pd.DataFrame], today_rows: pd.DataFrame) -> pd.DataFrame:
    """Per-symbol feature row for decision day T: seq_night.features() on daily bars dated < T plus T's 15:40 row.
    bars: sym -> split-adjusted daily OHLCV (any rows dated >= T are dropped here); today_rows: sym -> open/high/low/close/
    volume through 15:40 (raw). Adds the SEL-NIGHT pool columns vol20, day_ret, log_adv, log_px."""
    from research.sim.seq_night import features
    d = pd.Timestamp(T)
    frames = {}
    for s, b in bars.items():
        if s not in today_rows.index or b is None:
            continue
        b = b[b.index < d][["open", "high", "low", "close", "volume"]].astype(float)
        t = today_rows.loc[s]
        row = pd.DataFrame([[float(t["open"]), max(float(t["high"]), float(t["close"])), min(float(t["low"]), float(t["close"])),
                             float(t["close"]), float(t["volume"])]], index=[d], columns=b.columns)
        frames[s] = pd.concat([b, row])
    if not frames:
        return pd.DataFrame()
    W = {k: pd.DataFrame({s: f[k] for s, f in frames.items()}).sort_index() for k in ("open", "high", "low", "close", "volume")}
    o, h, l, c, v = (W[k] for k in ("open", "high", "low", "close", "volume"))
    F = features(o, h, l, c, v, c)                       # cu feeds only log_px, read at T where the row is raw
    out = pd.DataFrame({k: F[k].loc[d] for k in F})
    lr = np.log(c / c.shift(1))
    out["vol20"] = lr.shift(1).rolling(20, min_periods=19).std().loc[d] * np.sqrt(252)   # nx: prior 20 sessions
    out["day_ret"] = (c / c.shift(1) - 1).loc[d]
    out["log_adv"] = np.log((c * v).shift(1).rolling(20).mean().loc[d])
    out["log_px"] = np.log(c.loc[d])
    out["rets"] = pd.Series({s: [float(x) for x in lr[s].loc[:d].iloc[-21:-1].fillna(0.0)] for s in c.columns})
    return out


def score(F: pd.DataFrame, model: dict) -> pd.Series:
    """Within-night Ridge score: intercept + sum(coef * nan_to_num((x - mu) / sd)) over active per-pick features."""
    s = pd.Series(model["intercept"], index=F.index, dtype=float)
    for f in model["features"]:
        if not f["active"] or f["night_const"]:
            continue
        x = pd.to_numeric(F[f["name"]], errors="coerce") if f["name"] in F else pd.Series(np.nan, index=F.index)
        z = ((x.astype(float) - f["mu"]) / f["sd"]).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        s = s + f["coef"] * z
    return s


def tilt(scores) -> np.ndarray:
    p = np.asarray(scores, float)
    z = p - p.mean()
    z = z / (z.std() if z.std() > 0 else 1)
    m = np.clip(1 + TILT_K * z, M_LO, M_HI)
    return m / m.mean()


def add_context(F: pd.DataFrame, sectors: dict[str, str], recent: set[str]) -> pd.DataFrame:
    from research.sim.seq_night import SECTORS
    F = F.copy()
    for s_ in SECTORS:
        F[f"sec_{s_[:6]}"] = [float(sectors.get(t) == s_) for t in F.index]
    F["ssr"] = ((F["low_ret"] <= -0.10) | (F["prev_low_ret"] <= -0.10)).astype(float)
    F["repeat"] = [float(t in recent) for t in F.index]
    return F


# ----------------------------------------------------------------------------- one night
def night_rows(T: str, cands: list[str], bars: dict, today_rows: pd.DataFrame, model: dict, sectors: dict,
               recent: set[str], fund=lambda s: False) -> list[dict]:
    """The night's picks (funds out -> vol20 floor -> live dedupe, most-beaten first) with score, rank, z-tilt and v1 weight."""
    from . import signals as sg
    stocks = [s for s in dict.fromkeys(cands) if not fund(s)]
    F = features_at(T, {s: bars.get(s) for s in stocks}, today_rows)
    if F.empty:
        return []
    F = F[np.isfinite(F["day_ret"].astype(float)) & (F["vol20"].astype(float) >= VOL_MIN)]
    F = F.sort_values("day_ret", kind="mergesort")
    if F.empty:
        return []
    kept, _ = sg.dedupe_correlated(F, F["rets"].to_dict(), MAX_CORR)
    F = add_context(kept.drop(columns=["rets"]), sectors, recent)
    s = score(F, model)
    m = tilt(s.to_numpy())
    w = sg.night_tilt(F["vol20"].to_numpy(float), F["day_ret"].to_numpy(float), TILT_K)
    rank = s.rank(ascending=False, method="first").astype(int)
    out = []
    for i, sym in enumerate(F.index):
        out.append(dict(T=T, sym=sym, status="pending", n=len(F), score=round(float(s.iloc[i]), 6), rank=int(rank.iloc[i]),
                        m=round(float(m[i]), 4), w_v1=round(float(w[i]), 4), day_ret=round(float(F["day_ret"].iloc[i]), 5),
                        vol20=round(float(F["vol20"].iloc[i]), 3), repeat=bool(F["repeat"].iloc[i]),
                        sector=sectors.get(sym)))
    return out


def score_row(r: dict, X: dict) -> dict | None:
    """Close cross of T -> open cross of the next session that printed one; None until it has."""
    p = X.get(r["sym"], {})
    c0 = (p.get(r["T"]) or (None,) * 4)[2]
    later = sorted(d for d in p if d > r["T"])
    if not c0 or not later or not p[later[0]][0]:
        return None
    o1 = p[later[0]][0]
    return dict(r, status="scored", d1=later[0], c0=c0, o1=o1, r=round(float(np.clip(o1 / c0 - 1, -0.9, 0.9)), 6))


# ----------------------------------------------------------------------------- readout
def _tt(v: list[float]) -> float | None:
    return float(np.mean(v) / np.std(v, ddof=1) * np.sqrt(len(v))) if len(v) >= 3 and np.std(v, ddof=1) > 0 else None


def nights(rows: list[dict], backfill: bool = False) -> list[dict]:
    """Per-night readout over nights whose picks are all settled (scored / no_cross) and >= 2 scored."""
    by: dict[str, list[dict]] = {}
    for r in rows:
        if r.get("sym") and bool(r.get("backfill")) == backfill:
            by.setdefault(r["T"], []).append(r)
    out = []
    for T in sorted(by):
        g = by[T]
        if any(x["status"] == "pending" for x in g):
            continue
        g = [x for x in g if x["status"] == "scored"]
        if len(g) < 2:
            continue
        r = np.array([x["r"] for x in g]); m = tilt([x["score"] for x in g]); w = np.array([x["w_v1"] for x in g])
        w = w / w.mean()
        o = np.argsort([x["score"] for x in g], kind="stable"); half = len(g) // 2
        out.append(dict(T=T, n=len(g), ew_bp=1e4 * r.mean(), delta_ew_bp=1e4 * ((m * r).mean() - r.mean()),
                        delta_v1_bp=1e4 * ((w * m * r).mean() - (w * r).mean()),
                        tmb_bp=1e4 * (r[o[-half:]].mean() - r[o[:half]].mean()) if len(g) >= 4 else None))
    return out


def summary(rows: list[dict], backfill: bool = False) -> dict:
    N = nights(rows, backfill)
    d = [x["delta_ew_bp"] for x in N]; v = [x["delta_v1_bp"] for x in N]; tm = [x["tmb_bp"] for x in N if x["tmb_bp"] is not None]
    rnd = lambda x: None if x is None else round(x, 2)  # noqa: E731
    return dict(nights=len(N), backfill=backfill, names=sum(x["n"] for x in N),
                delta_ew_bp=rnd(st.mean(d)) if d else None, t=rnd(_tt(d)),
                delta_v1_bp=rnd(st.mean(v)) if v else None, t_v1=rnd(_tt(v)),
                tmb_bp=rnd(st.mean(tm)) if tm else None, t_tmb=rnd(_tt(tm)), tmb_nights=len(tm),
                hit=rnd(float(np.mean([x > 0 for x in d]))) if d else None)


def verdict(s: dict) -> str:
    if s["nights"] < NEED:
        return f"({s['nights']}/{NEED} nights)"
    ok = s["delta_ew_bp"] > 0 and (s["t"] or 0) >= 2 and (s["tmb_bp"] or 0) > 0
    if ok:
        return "PASS (delta > 0, t >= 2, tmb > 0): propose the Ridge tilt, user decision"
    if s["delta_ew_bp"] <= 0 or s["nights"] >= NEED2:
        return "KILL"
    return f"HOLD to {NEED2} nights ({s['nights']}/{NEED2})"


def line(rows: list[dict]) -> str:
    s, b = summary(rows), summary(rows, True)
    if not s["nights"]:
        return (f"SEQ-TILT-FWD: 0 forward nights yet (backfill {b['nights']}n, delta {b['delta_ew_bp']}bp, "
                f"tmb {b['tmb_bp']}bp; not gated)")
    return (f"SEQ-TILT-FWD: {s['nights']}n/{s['names']} picks tilt-vs-EW {s['delta_ew_bp']:+.2f}bp/night t {s['t']} "
            f"(vs v1 {s['delta_v1_bp']:+.2f}) | top-minus-bottom {s['tmb_bp']}bp t {s['t_tmb']} ({s['tmb_nights']}n) "
            f"| {verdict(s)}")


# ----------------------------------------------------------------------------- daily run
def run(state_dir: Path, logs_dir: Path | None = None, log=print, today: dt.date | None = None, H: dict | None = None,
        bars_fn=None, rth_fn=None, crosses_fn=None, fund_fn=None) -> dict:
    """Log every unscanned candidate night < today, then score pending picks whose next open cross has printed."""
    from . import marketdata as md
    today = today or dt.datetime.now(dt.timezone.utc).astimezone(ZoneInfo(ET)).date()
    state_dir = Path(state_dir)
    path = state_dir / LOG_NAME
    rows = _read(path)
    scanned = {r["T"] for r in rows if r.get("status") == "scanned"}
    cand: dict[str, list[tuple[float, str]]] = {}
    for c in _read(state_dir / CAND_LOG):
        if c.get("date") and c.get("sym") and c["date"] < str(today):
            cand.setdefault(c["date"], []).append((float(c.get("day_ret") or 0.0), c["sym"]))
    todo = sorted(T for T in cand if T not in scanned)
    if todo:
        from .exdate_open_shadow import _headers, is_fund
        bars_fn = bars_fn or (lambda syms, start: md.sip_daily(syms, start, adjustment="split"))
        rth_fn = rth_fn or md.rth_minutes
        if fund_fn is None:
            H = H or _headers()
            cache: dict = {}
            fund_fn = lambda s: is_fund(s, H, cache)  # noqa: E731
        model, sectors = load_model(), load_sectors()
        pick_nights = sorted({r["T"] for r in rows if r.get("sym")})
        for T in todo:
            syms = [s for _, s in sorted(cand[T])]          # most-beaten first, as the leg walks them
            prior = [d for d in pick_nights if d < T][-REPEAT:]
            recent = {r["sym"] for r in rows if r.get("sym") and r["T"] in prior}
            start = (pd.Timestamp(T) - pd.Timedelta(days=HIST_DAYS)).strftime("%Y-%m-%d")
            try:
                bars = bars_fn(syms, start)
                tr = rth_fn(syms, pd.Timestamp(T), 1540)
                new = night_rows(T, syms, bars, tr, model, sectors, recent, fund_fn)
            except Exception as exc:  # noqa: BLE001 - a shadow never raises into the service; retried next run
                log(f"[seq-tilt] T {T}: skipped ({type(exc).__name__}: {str(exc)[:80]})")
                continue
            bf = T < START_T
            rows += [dict(x, backfill=bf) for x in new]
            rows.append(dict(T=T, status="scanned", n_cand=len(syms), n_picks=len(new), backfill=bf))
            if new:
                pick_nights = sorted(set(pick_nights) | {T})
            log(f"[seq-tilt] T {T}{' (backfill)' if bf else ''}: {len(syms)} signals -> {len(new)} picks; top "
                + ", ".join(f"{x['sym']} m {x['m']:.2f}" for x in sorted(new, key=lambda x: x["rank"])[:5]))
    pend = [r for r in rows if r.get("status") == "pending"]
    if pend:
        from .pref_ex_shadow import crosses as _crosses
        if crosses_fn is None:
            from .exdate_open_shadow import _headers
            H = H or _headers()
            crosses_fn = lambda s, a, b: _crosses(s, a, b, H)  # noqa: E731
        end = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
        syms_p = sorted({r["sym"] for r in pend})
        X: dict = {}
        for i in range(0, len(syms_p), 40):
            X.update(crosses_fn(syms_p[i:i + 40], min(r["T"] for r in pend), end))
        new_rows = []
        for r in rows:
            if r.get("status") == "pending":
                s = score_row(r, X)
                r = s or (dict(r, status="no_cross") if r["T"] <= str(today - dt.timedelta(days=10)) else r)
            new_rows.append(r)
        rows = new_rows
    rows = sorted(rows, key=lambda r: (r["T"], r.get("status") != "scanned", r.get("rank", 0)))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    log(f"[seq-tilt] {line(rows)}")
    return summary(rows)


if __name__ == "__main__":
    import sys
    from ..config import Config
    if getattr(Config.load().daily, "seq_tilt_fwd", "shadow") == "off":
        print("[seq-tilt] daily.seq_tilt_fwd is off")
        sys.exit(0)
    root = Path(__file__).resolve().parents[2]
    run(root / "state", root / "logs")
