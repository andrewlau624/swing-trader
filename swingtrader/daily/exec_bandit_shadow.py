"""EXEC-ARMS (N 1197): log-only scoring of order-placement choices on the live auction legs.

Every PREF-EX buy (decided 15:25, sent as a market-on-close) logs Schwab's decision-time quote (quote_guard detail).
After the close this scores four ways the same order could have been placed, against the official closing cross C:

- cross:           the live choice, fill C (reward 0 by definition)
- take:            buy at the 15:25 ask
- bid_then_cross:  rest a limit at the 15:25 bid; filled at the bid if a 1-min low in 15:26-15:49 trades BELOW it
                   (strictly below, a queue haircut), else convert to market-on-close before the 15:50 cutoff: fill C
- mid_then_cross:  the same at the 15:25 mid

reward_bp = (C / fill - 1) x 1e4 (positive = cheaper than the cross). Every arm is scored on every order (full
information), so no exploration is needed: `would_choose` is the arm with the best lower bound (mean - 2 se),
cross by default. CEF-RV buys (decided 09:05 on the prior session's quote, filled at the opening cross) have no
in-session alternative; they are logged descriptively (open cross vs the prior mid / ask).

Gate (pre-registered, round1_prose.md EXEC-ARMS): at 60 scored PREF-EX buys, the best non-cross arm >= +3bp mean
with day-clustered t >= 2 -> propose switching (user decision). At 120 with none passing -> kill; the cross stays.
Never places orders.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import statistics as st
from pathlib import Path
from zoneinfo import ZoneInfo

LOG_NAME = "exec-arms.jsonl"            # state/
ARMS = ("cross", "take", "bid_then_cross", "mid_then_cross")
GATE_N, KILL_N, GATE_BP, GATE_T = 60, 120, 3.0, 2.0
ET = ZoneInfo("America/New_York")
BARS_URL = "https://data.alpaca.markets/v2/stocks/bars"


def _jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def window_low(sym: str, day: str, H: dict, start_hm=(15, 26), end_hm=(15, 50)) -> float | None:
    """Lowest 1-min SIP low in [start, end) ET of one regular session (in-session by construction)."""
    from .exdate_open_shadow import _get
    d = dt.date.fromisoformat(day)
    s = dt.datetime(d.year, d.month, d.day, *start_hm, tzinfo=ET).astimezone(dt.timezone.utc)
    e = dt.datetime(d.year, d.month, d.day, *end_hm, tzinfo=ET).astimezone(dt.timezone.utc)
    j = _get(BARS_URL, {"symbols": sym, "timeframe": "1Min", "start": s.isoformat().replace("+00:00", "Z"),
                        "end": e.isoformat().replace("+00:00", "Z"), "feed": "sip", "adjustment": "raw",
                        "limit": 10000}, H)
    lows = [b["l"] for b in (j.get("bars") or {}).get(sym, [])]
    return min(lows) if lows else None


def arms(q: dict, cross: float, low: float | None) -> dict[str, float | None]:
    """reward_bp per arm for a buy; None when the decision quote cannot price that arm."""
    bid, ask, mid = q.get("bid"), q.get("ask"), q.get("mid")
    rb = lambda fill: round((cross / fill - 1) * 1e4, 1)  # noqa: E731
    out = {"cross": 0.0, "take": rb(ask) if ask else None}
    for name, lim in (("bid_then_cross", bid), ("mid_then_cross", mid)):
        out[name] = None if not lim or low is None else rb(lim if low < lim else cross)
    return out


def _key(strategy: str, r: dict) -> str:
    return f"{strategy}|{r['sym']}|{r['ts'][:10]}"


def score(logs_dir: Path, done: set[str], today: dt.date, crosses_fn, low_fn, H) -> list[dict]:
    new = []
    for strategy, fname, idx in (("pref-ex", "pref-ex-live.jsonl", 2), ("cef-rv", "cef-rv-live.jsonl", 0)):
        for r in _jsonl(Path(logs_dir) / fname):
            if r.get("cmd") != "buy" or not r.get("quote") or not r.get("ts") or _key(strategy, r) in done:
                continue
            day = r["ts"][:10]                      # both legs fill the same session they decide (15:25 -> 16:00, 09:05 -> 09:30)
            if day > today.isoformat():
                continue
            X = (crosses_fn([r["sym"]], day, day, H).get(r["sym"]) or {}).get(day)
            px = X[idx] if X else None
            if not px:
                continue                            # cross not published yet: retry next run
            q = r["quote"]
            row = dict(key=_key(strategy, r), strategy=strategy, sym=r["sym"], day=day, dry_run=bool(r.get("dry_run")),
                       qty=r.get("qty"), cross=px, bid=q.get("bid"), ask=q.get("ask"), mid=q.get("mid"),
                       quote_age_s=q.get("age_s"))
            if strategy == "pref-ex":
                low = low_fn(r["sym"], day, H)
                row.update(window_low=low, reward_bp=arms(q, px, low))
            else:
                m, a = q.get("mid") or q.get("px"), q.get("ask")
                row.update(open_vs_prior_mid_bp=round((px / m - 1) * 1e4, 1) if m else None,
                           open_vs_prior_ask_bp=round((px / a - 1) * 1e4, 1) if a else None)
            new.append(row)
    return new


def _clustered(by_day: dict[str, list[float]]) -> tuple[float, float, int]:
    """Mean, day-clustered standard error (CR1), n."""
    xs = [x for v in by_day.values() for x in v]
    n, g = len(xs), len(by_day)
    if g < 2:
        return (sum(xs) / n if n else 0.0), math.inf, n
    m = sum(xs) / n
    var = sum(sum(x - m for x in v) ** 2 for v in by_day.values()) / n ** 2 * g / (g - 1)
    return m, math.sqrt(var) if var > 0 else math.inf, n


def stats(rows: list[dict]) -> dict:
    pe = [r for r in rows if r["strategy"] == "pref-ex"]
    out = {"n": len(pe), "arms": {}}
    lbs = {}
    for a in ARMS[1:]:
        by: dict[str, list[float]] = {}
        for r in pe:
            v = (r.get("reward_bp") or {}).get(a)
            if v is not None:
                by.setdefault(r["day"], []).append(v)
        m, se, n = _clustered(by)
        out["arms"][a] = dict(mean=round(m, 1), t=round(m / se, 2) if math.isfinite(se) else 0.0, n=n)
        lbs[a] = m - 2 * se
    best = max(lbs, key=lbs.get)
    out["would_choose"] = best if lbs[best] > 0 else "cross"
    passing = [a for a, s in out["arms"].items() if s["mean"] >= GATE_BP and s["t"] >= GATE_T]
    out["state"] = ("PROPOSE " + passing[0] if passing and len(pe) >= GATE_N else
                    "KILL (cross stays)" if len(pe) >= KILL_N else f"collecting ({len(pe)}/{GATE_N})")
    cr = [r["open_vs_prior_mid_bp"] for r in rows if r["strategy"] == "cef-rv" and r.get("open_vs_prior_mid_bp") is not None]
    out["cef_n"], out["cef_open_vs_mid_med"] = len(cr), (round(st.median(cr), 1) if cr else None)
    return out


def line(rows: list[dict]) -> str:
    s = stats(rows)
    arm = ", ".join(f"{a} {v['mean']:+.1f}bp (t {v['t']:.1f}, n {v['n']})" for a, v in s["arms"].items() if v["n"])
    cef = (f"; CEF-RV open vs prior mid median {s['cef_open_vs_mid_med']:+.1f}bp (n {s['cef_n']})" if s["cef_n"] else "")
    return (f"EXEC-ARMS: {s['n']} PREF-EX buys scored vs the close cross"
            + (f": {arm}" if arm else "") + f"; would choose {s['would_choose']}; {s['state']}" + cef)


def run(state_dir: Path, logs_dir: Path, log=print, today: dt.date | None = None, crosses_fn=None, low_fn=None,
        H: dict | None = None) -> list[dict]:
    state_dir, logs_dir = Path(state_dir), Path(logs_dir)
    today = today or dt.datetime.now(ET).date()
    if crosses_fn is None or low_fn is None:
        from .exdate_open_shadow import _headers
        from .pref_ex_shadow import crosses
        H = H or _headers()
        crosses_fn, low_fn = crosses_fn or crosses, low_fn or window_low
    path = state_dir / LOG_NAME
    rows = _jsonl(path)
    new = score(logs_dir, {r["key"] for r in rows}, today, crosses_fn, low_fn, H)
    if new:
        state_dir.mkdir(exist_ok=True)
        with path.open("a") as f:
            for r in new:
                f.write(json.dumps(r) + "\n")
    rows += new
    log(f"[exec-arms] {len(new)} new scored orders. " + line(rows))
    return rows


if __name__ == "__main__":
    import sys
    from ..config import Config
    cfg = Config.load()
    if getattr(cfg.daily, "exec_arms_fwd", "shadow") == "off":
        print("[exec-arms] daily.exec_arms_fwd is off")
        sys.exit(0)
    root = Path(__file__).resolve().parents[2]
    run(root / "state", root / "logs")
