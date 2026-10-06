"""Ex-date open shadow (SPLIT-T0 + SPIN-T0, golden-egg loop 2026-10-06): logs, never orders.

Rule (research/drafts/golden_egg_2026-10-06.md; round1_prose.md SPLIT-T0 / SPIN-T0): buy the official closing cross on
the session before a forward-split or spin-off ex-date E, sell the official opening cross on E (spin-off: the parent at
its open plus `new_rate / source_rate` child shares at the child's open). Judged count: common stock (asset name not a
fund/ETF/ETN), close cross(E-1) >= $5 (the research $1M daily $vol screen is not re-applied; the close-cross $ is logged). Backtest: splits official 2016-20 median +57bp, 2021-26 +17bp (raw-SPY);
spins official 2021-26 median +54bp.

Each run: pull Alpaca corporate actions (forward_split, spin_off) from BACKFILL to today + 14 days, log upcoming events,
score every event whose E session has printed (official crosses from /v2/stocks/auctions, largest-size print = the
cross; SPY's overnight from the same source). Rows with E < FORWARD_FROM are backfill (in the touched period), shown
separately; the gate counts forward rows only.
Gate: NEED forward common-stock events. Pass = median raw-SPY > 0 and mean > 10bp; kill = median <= 0.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import statistics as st
from pathlib import Path

LOG_NAME = "exdate-open.jsonl"
BACKFILL = "2026-01-01"
FORWARD_FROM = "2026-10-07"
NEED = 40
MIN_PX = 5.0
CA_URL = "https://data.alpaca.markets/v1/corporate-actions"
AU_URL = "https://data.alpaca.markets/v2/stocks/auctions"
ASSET_URL = "https://paper-api.alpaca.markets/v2/assets/{}"  # asset metadata; the data keys authorize here
SYM = re.compile(r"[A-Z]{1,5}")
FUND = re.compile(r"\b(ETF|ETN|FUND|ISHARES|PROSHARES|DIREXION|2X|3X|LEVERAGED)\b", re.I)


def _headers() -> dict:
    if "ALPACA_API_KEY" not in os.environ:
        env = Path(__file__).resolve().parents[2] / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    os.environ.setdefault(k, v.strip().strip('"').strip("'"))
    return {"APCA-API-KEY-ID": os.environ["ALPACA_API_KEY"], "APCA-API-SECRET-KEY": os.environ["ALPACA_SECRET_KEY"]}


def _get(url: str, params: dict, H: dict) -> dict:
    import time
    import requests
    for k in range(5):
        r = requests.get(url, params=params, headers=H, timeout=30)
        if r.status_code == 429:
            time.sleep(5 * (k + 1))
            continue
        r.raise_for_status()
        return r.json()
    return {}


def events(start: str, end: str, H: dict) -> list[dict]:
    """Forward splits and spin-offs with ex_date in [start, end] whose symbols are plain listed tickers."""
    out, tok = [], None
    while True:
        q = {"types": "forward_split,spin_off", "start": start, "end": end, "limit": 1000}
        if tok:
            q["page_token"] = tok
        j = _get(CA_URL, q, H)
        ca = j.get("corporate_actions") or {}
        for x in ca.get("forward_splits", []):
            if SYM.fullmatch(x.get("symbol", "")) and x.get("new_rate", 0) > x.get("old_rate", 1):
                out.append(dict(kind="split", sym=x["symbol"], ex=x["ex_date"], ratio=x["new_rate"] / x["old_rate"]))
        for x in ca.get("spin_offs", []):
            s, c = x.get("source_symbol", ""), x.get("new_symbol", "")
            if SYM.fullmatch(s) and SYM.fullmatch(c) and x.get("source_rate"):
                out.append(dict(kind="spin", sym=s, child=c, ex=x["ex_date"], ratio=x["new_rate"] / x["source_rate"]))
        tok = j.get("next_page_token")
        if not tok:
            return out


def crosses(syms: list[str], start: str, end: str, H: dict) -> dict[str, dict[str, tuple]]:
    """sym -> date -> (open cross price, close cross price, close cross size), largest-size print per auction."""
    out: dict[str, dict[str, tuple]] = {}
    tok = None
    while True:
        q = {"symbols": ",".join(syms), "start": start, "end": end, "feed": "sip", "limit": 10000}
        if tok:
            q["page_token"] = tok
        j = _get(AU_URL, q, H)
        for s, rows in (j.get("auctions") or {}).items():
            for x in rows:
                o = max(x["o"], key=lambda p: p.get("s", 0)) if x.get("o") else None
                c = max(x["c"], key=lambda p: p.get("s", 0)) if x.get("c") else None
                out.setdefault(s, {})[x["d"]] = (o["p"] if o else None, c["p"] if c else None, c["s"] if c else None)
        tok = j.get("next_page_token")
        if not tok:
            return out


def is_fund(sym: str, H: dict, cache: dict) -> bool:
    if sym not in cache:
        try:
            a = _get(ASSET_URL.format(sym), {}, H)
        except Exception:  # noqa: BLE001 - unknown asset: treat as stock, keep the row
            a = {}
        cache[sym] = bool(FUND.search(a.get("name", ""))) or a.get("exchange") == "ARCA"
    return cache[sym]


def score(ev: dict, X: dict, spy: dict) -> dict | None:
    """P&L of close cross E-1 -> open cross E, raw and minus SPY's official overnight; None until E has printed."""
    p = X.get(ev["sym"], {})
    if ev["ex"] not in p or not p[ev["ex"]][0]:
        return None
    prev = [d for d in sorted(p) if d < ev["ex"] and p[d][1]]
    if not prev:
        return None
    d0 = prev[-1]
    c0, cs0 = p[d0][1], p[d0][2] or 0
    o1 = p[ev["ex"]][0]
    if ev["kind"] == "split":
        pnl = o1 * ev["ratio"] / c0 - 1
    else:
        co = X.get(ev["child"], {}).get(ev["ex"], (None,))[0]
        if not co:
            return None
        pnl = (o1 + ev["ratio"] * co) / c0 - 1
    if abs(pnl) > 0.5:  # tape and corporate-action ratio disagree: not scoreable
        return dict(ev, status="mismatch", pnl=pnl)
    s0, s1 = spy.get(d0), spy.get(ev["ex"])
    spy_on = s1[0] / s0[1] - 1 if (s0 and s1 and s0[1] and s1[0]) else None
    return dict(ev, status="scored", d0=d0, close_px=c0, close_dollars=c0 * cs0, open_px=o1, pnl=pnl,
                x=None if spy_on is None else pnl - spy_on, eligible=c0 >= MIN_PX)


def summary(rows: list[dict]) -> dict:
    out = {}
    for tag, fwd in (("forward", True), ("backfill", False)):
        x = [r["x"] for r in rows if r.get("status") == "scored" and r.get("eligible") and not r.get("fund")
             and r.get("x") is not None and (r["ex"] >= FORWARD_FROM) == fwd]
        out[tag] = dict(n=len(x), mean_bp=st.mean(x) * 1e4 if x else None, median_bp=st.median(x) * 1e4 if x else None,
                        hit=sum(v > 0 for v in x) / len(x) if x else None)
    out["upcoming"] = sorted({(r["ex"], r["kind"], r["sym"]) for r in rows if r.get("status") == "upcoming"})
    return out


def line(rows: list[dict]) -> str:
    s = summary(rows)
    parts = []
    for tag in ("forward", "backfill"):
        v = s[tag]
        parts.append(f"{tag} n {v['n']}" + (f", raw-SPY mean {v['mean_bp']:+.0f}bp median {v['median_bp']:+.0f}bp "
                                             f"hit {v['hit']*100:.0f}%" if v["n"] else ""))
    nxt = ", ".join(f"{k} {s_} {e}" for e, k, s_ in s["upcoming"][:6])
    verdict = ""
    f = s["forward"]
    if f["n"] >= NEED:
        verdict = (" -> PASS (median > 0, mean > 10bp)" if f["median_bp"] > 0 and f["mean_bp"] > 10
                   else " -> KILL (median <= 0)" if f["median_bp"] <= 0 else " -> HOLD")
    return "; ".join(parts) + (f"; next: {nxt}" if nxt else "") + verdict


def run(state_dir: Path, logs_dir: Path, log=print, today: dt.date | None = None, H: dict | None = None) -> dict:
    state_dir = Path(state_dir)
    path = state_dir / LOG_NAME
    H = H or _headers()
    today = today or dt.date.today()
    old = {}
    if path.exists():
        for ln in path.read_text().splitlines():
            try:
                r = json.loads(ln)
                old[(r["kind"], r["sym"], r["ex"])] = r
            except (ValueError, KeyError):
                continue
    evs = [e for e in events(BACKFILL, str(today + dt.timedelta(days=14)), H) if e["ex"] >= BACKFILL]
    todo = [e for e in evs if old.get((e["kind"], e["sym"], e["ex"]), {}).get("status")
            not in ("scored", "mismatch", "no_cross")]
    printed = [e for e in todo if e["ex"] <= str(today)]
    fund_cache: dict = {}
    X: dict = {}
    if printed:
        syms = sorted({e["sym"] for e in printed} | {e["child"] for e in printed if e["kind"] == "spin"} | {"SPY"})
        start = str(dt.date.fromisoformat(min(e["ex"] for e in printed)) - dt.timedelta(days=10))
        # the free SIP feed refuses the most recent 15 minutes
        end = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for i in range(0, len(syms), 40):
            X.update(crosses(syms[i:i + 40], start, end, H))
    spy = X.get("SPY", {})
    for e in todo:
        k = (e["kind"], e["sym"], e["ex"])
        r = score(e, X, spy) if e["ex"] <= str(today) else None
        if r is None:
            stale = e["ex"] <= str(today - dt.timedelta(days=5))  # no official cross by now (OTC/foreign line)
            r = dict(e, status="upcoming" if e["ex"] > str(today) else ("no_cross" if stale else "pending"))
        r["fund"] = is_fund(e["sym"], H, fund_cache)
        r["logged"] = str(today)
        old[k] = r
    rows = sorted(old.values(), key=lambda r: (r["ex"], r["kind"], r["sym"]))
    state_dir.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    log(f"[exdate-open] {line(rows)}")
    return summary(rows)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    run(root / "state", root / "logs")
