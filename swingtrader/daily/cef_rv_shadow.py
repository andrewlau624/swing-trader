"""CEF-RV forward shadow (CEF-ALPHA, round1_prose.md, 2026-10-07): logs, never orders.

Rule (frozen, research/sim/cef_rv.py build_trades): per CEF, weekly discount d = price/NAV - 1 (CEFConnect). ENTRY when
d <= its own trailing-52-week 10th percentile, EXIT when d >= its own trailing-52-week median or after 260 days. One
position per fund. Executed at official SIP auction prints: OO = opening cross of the first session after the entry
signal week -> opening cross of the first session after the exit signal week (the capacity route: the open is ~10x
deeper than the close for CEFs); CC = the closing crosses of those sessions. Cash distributions with an ex-date inside
the hold are added. 50bp round trip.

The question forward is alpha, not raw return: each closed trade is compared with the equal-weight CEF universe (every
fund in the CEFConnect list with closing crosses on both sessions, distributions included) over the same sessions.
Research: +125bp/trade excess 2016-26 (t 5.6), raw ~2/3 market.
Gate (NEED closed forward trades spanning >= 10 entry weeks): PASS = mean OO excess >= +60bp, entry-week-clustered
t >= 2, median > 0; KILL = mean OO excess <= 0. CC reported alongside. Rows with a signal week before FORWARD_FROM are
backfill, shown separately and never gated.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import statistics as st
import time
from pathlib import Path

from .exdate_open_shadow import CA_URL, _get, _headers
from .pref_ex_shadow import crosses

LOG_NAME = "cef-rv.jsonl"
PANEL_NAME = "cef-rv-panel.json"
BACKFILL = "2026-09-01"
FORWARD_FROM = "2026-10-08"     # first forward signal week: Fri 2026-10-09
NEED = 60
MIN_WEEKS = 10
COST = 0.005
KEEP_WEEKS = 160
MAX_HOLD_DAYS = 260
CEFC = "https://www.cefconnect.com/api/v3"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) research-personal"}


# ------------------------------------------------------------------ rule (pure)

def _pct(xs: list[float], q: float) -> float:
    """numpy.percentile(..., method='linear') on finite values."""
    v = sorted(x for x in xs if x is not None and math.isfinite(x))
    if not v:
        return float("nan")
    k = (len(v) - 1) * q / 100
    lo, hi = math.floor(k), math.ceil(k)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def signals(dates: list[str], disc: list[float]) -> list[dict]:
    """Entry/exit signal weeks of the frozen CEF-RV rule over one fund's weekly series (oldest first).

    Mirrors research/sim/cef_rv.build_trades, without prices: returns [{signal, exit_signal|None}], the last one
    open when the fund is still held.
    """
    out, cur = [], None
    for i in range(56, len(disc)):
        win = disc[max(0, i - 51): i + 1]
        q10, med = _pct(win, 10), _pct(win, 50)
        x = disc[i]
        if x is None or not math.isfinite(x):
            continue
        if cur is None:
            if x <= q10:
                cur = dict(signal=dates[i], exit_signal=None)
                out.append(cur)
        else:
            held = (dt.date.fromisoformat(dates[i]) - dt.date.fromisoformat(cur["signal"])).days
            if x >= med or held > MAX_HOLD_DAYS:
                cur["exit_signal"] = dates[i]
                cur = None
    return out


# ------------------------------------------------------------------ data

def _cefc(path: str):
    import requests
    for k in range(3):
        try:
            r = requests.get(f"{CEFC}/{path}", headers=UA, timeout=30)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        time.sleep(2 * (k + 1))
    return None


def panel(state_dir: Path, today: dt.date, log=print) -> dict[str, list[tuple[str, float]]]:
    """sym -> [(week date, discount)] oldest first, from CEFConnect; refetched when a newer weekly point is due."""
    p = state_dir / PANEL_NAME
    old = json.loads(p.read_text()) if p.exists() else {}
    last = max((r[-1][0] for r in old.values() if r), default="")
    due = str(today - dt.timedelta(days=(today.weekday() - 4) % 7 or 7))     # the latest Friday before today
    if old and last >= due:
        return old
    funds = _cefc("funds") or []
    if not funds:     # CEFConnect blocks datacenter IPs (the server): the panel is pushed from a clean IP instead
        log(f"[cef-rv] CEFConnect unreachable; using the stored panel (latest week {last or '-'}); "
            f"refresh it from a clean IP: make cef-rv-panel")
        return old
    new, bad = {}, 0
    for f in funds:
        sym = f.get("Ticker")
        j = _cefc(f"pricinghistory/{sym}/All") if sym else None
        hist = ((j or {}).get("Data") or {}).get("PriceHistory") if isinstance((j or {}).get("Data"), dict) else None
        if not hist:
            bad += 1
            if sym in old:
                new[sym] = old[sym]
            continue
        rows = sorted((r["DataDate"][:10], (r["Data"] / r["NAVData"] - 1) if r.get("Data") and r.get("NAVData")
                       else None) for r in hist)
        new[sym] = rows[-KEEP_WEEKS:]
        time.sleep(0.3)
    if new:
        state_dir.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(new))
    log(f"[cef-rv] panel refreshed: {len(new)} funds ({bad} failed), latest week "
        f"{max((r[-1][0] for r in new.values() if r), default='-')}")
    return new or old


def dividends(syms: list[str], start: str, end: str, H: dict) -> dict[str, list[tuple[str, float]]]:
    out: dict[str, list[tuple[str, float]]] = {}
    for i in range(0, len(syms), 50):
        tok = None
        while True:
            q = {"types": "cash_dividend", "symbols": ",".join(syms[i:i + 50]), "start": start, "end": end,
                 "limit": 1000}
            if tok:
                q["page_token"] = tok
            j = _get(CA_URL, q, H)
            for x in (j.get("corporate_actions") or {}).get("cash_dividends", []):
                if (x.get("rate") or 0) > 0 and not x.get("foreign"):
                    out.setdefault(x["symbol"], []).append((x["ex_date"], float(x["rate"])))
            tok = j.get("next_page_token")
            if not tok:
                break
    return out


def _after(days: dict, d: str) -> str | None:
    return next((x for x in sorted(days) if x > d), None)


def _div(divs: dict, sym: str, a: str, b: str) -> float:
    return sum(r for ex, r in divs.get(sym, []) if a < ex <= b)


# ------------------------------------------------------------------ score + summary

def score(t: dict, X: dict, divs: dict) -> dict:
    """Fill entry/exit sessions, prices and gross OO / CC returns of one trade from the official crosses."""
    p = X.get(t["sym"], {})
    e = _after(p, t["signal"])
    t = dict(t, entry=e)
    if not e or not p[e][0] or not p[e][2]:
        return dict(t, status="pending")
    t.update(entry_open=p[e][0], entry_close=p[e][2])
    if not t.get("exit_signal"):
        return dict(t, status="open")
    x = _after(p, t["exit_signal"])
    if not x or not p[x][0] or not p[x][2]:
        return dict(t, status="exiting", exit=x)
    d = _div(divs, t["sym"], e, x)
    return dict(t, status="closed", exit=x, exit_open=p[x][0], exit_close=p[x][2], div=d,
                oo=(p[x][0] + d) / p[e][0] - 1, cc=(p[x][2] + d) / p[e][2] - 1)


def ew(X: dict, divs: dict, e: str, x: str) -> tuple[float | None, int]:
    """Equal-weight CEF universe close-to-close total return from session e to session x."""
    rs = []
    for s, p in X.items():
        a, b = p.get(e), p.get(x)
        if a and b and a[2] and b[2]:
            r = (b[2] + _div(divs, s, e, x)) / a[2] - 1
            if abs(r) < 0.5:
                rs.append(r)
    return (st.mean(rs) if rs else None), len(rs)


def _stats(rows: list[dict], key: str) -> dict:
    v = [r[key] for r in rows]
    if not v:
        return dict(n=0)
    weeks: dict[str, list[float]] = {}
    for r in rows:
        weeks.setdefault(r["signal"], []).append(r[key])
    m = st.mean(v)
    # entry-week clustered t: sum of residuals per cluster
    s = [sum(x - m for x in g) for g in weeks.values()]
    k = len(s)
    se = math.sqrt(sum(z * z for z in s) * k / (k - 1)) / len(v) if k > 1 else 0.0
    return dict(n=len(v), weeks=k, mean_bp=m * 1e4, median_bp=st.median(v) * 1e4,
                hit=sum(x > 0 for x in v) / len(v), t=(m / se) if se > 0 else None)


def summary(rows: list[dict]) -> dict:
    out = {}
    for tag, fwd in (("forward", True), ("backfill", False)):
        c = [r for r in rows if r.get("status") == "closed" and "x_oo" in r and (r["signal"] >= FORWARD_FROM) == fwd]
        out[tag] = {k: _stats(c, k) for k in ("x_oo", "x_cc", "net_oo")}
        out[tag]["open"] = sum(1 for r in rows if r.get("status") in ("open", "exiting")
                               and (r["signal"] >= FORWARD_FROM) == fwd)
    return out


def line(rows: list[dict]) -> str:
    s = summary(rows)
    parts = []
    for tag in ("forward", "backfill"):
        v = s[tag]
        if not v["x_oo"]["n"]:
            parts.append(f"{tag}: 0 closed, {v['open']} open")
            continue
        a, c, n = v["x_oo"], v["x_cc"], v["net_oo"]
        parts.append(f"{tag}: {a['n']} closed / {a['weeks']} entry weeks, {v['open']} open; excess vs EW CEF OO "
                     f"{a['mean_bp']:+.0f}bp (median {a['median_bp']:+.0f}, hit {a['hit']*100:.0f}%, t "
                     f"{a['t'] if a['t'] is None else round(a['t'], 2)}), CC {c['mean_bp']:+.0f}bp; raw net OO "
                     f"{n['mean_bp']:+.0f}bp")
    f = s["forward"]["x_oo"]
    verdict = ""
    if f["n"] >= NEED and f.get("weeks", 0) >= MIN_WEEKS:
        verdict = (" -> PASS (excess >= +60bp, t >= 2, median > 0)" if f["mean_bp"] >= 60 and (f["t"] or 0) >= 2
                   and f["median_bp"] > 0 else " -> KILL (excess <= 0)" if f["mean_bp"] <= 0 else " -> HOLD")
    return "; ".join(parts) + verdict


def run(state_dir: Path, logs_dir: Path, log=print, today: dt.date | None = None, H: dict | None = None) -> dict:
    state_dir = Path(state_dir)
    today = today or dt.date.today()
    H = H or _headers()
    pan = panel(state_dir, today, log)
    path = state_dir / LOG_NAME
    old = {}
    if path.exists():
        for ln in path.read_text().splitlines():
            try:
                r = json.loads(ln)
                old[(r["sym"], r["signal"])] = r
            except (ValueError, KeyError):
                continue
    for sym, rows in pan.items():
        for sg in signals([d for d, _ in rows], [x if x is not None else float("nan") for _, x in rows]):
            if sg["signal"] < BACKFILL:
                continue
            k = (sym, sg["signal"])
            if old.get(k, {}).get("status") != "closed":
                old[k] = {**old.get(k, {}), "sym": sym, "signal": sg["signal"], "exit_signal": sg["exit_signal"]}
    todo = [r for r in old.values() if r.get("status") != "closed"]
    if todo:
        start = min(r["signal"] for r in todo)
        end = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
        universe = sorted(pan)
        X: dict = {}
        for i in range(0, len(universe), 40):
            X.update(crosses(universe[i:i + 40], start, end, H))
        divs = dividends(universe, start, str(today), H)
        for r in todo:
            new = score(r, X, divs)
            if new["status"] == "closed":
                m, nn = ew(X, divs, new["entry"], new["exit"])
                if m is not None:
                    new.update(ew=m, ew_n=nn, net_oo=new["oo"] - COST, x_oo=new["oo"] - COST - m,
                               x_cc=new["cc"] - COST - m)
            new["logged"] = str(today)
            old[(r["sym"], r["signal"])] = new
    rows = sorted(old.values(), key=lambda r: (r["signal"], r["sym"]))
    state_dir.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    log(f"[cef-rv] {line(rows)}")
    return summary(rows)


if __name__ == "__main__":
    import sys
    root = Path(__file__).resolve().parents[2]
    if sys.argv[1:2] == ["panel"]:            # refresh only, into the given dir (make cef-rv-panel)
        panel(Path(sys.argv[2]), dt.date.today())
    else:
        run(root / "state", root / "logs")
