"""OVN-23/5 recorder (proposes from mega_research 2026-10-15; LOG-ONLY, never orders).

The official 23/5 overnight session starts 2026-12-06 (FR 2026-20799, Joint Industry Plan
Twenty-Ninth Amendment about the overnight 21:00-04:00 session, LULD overnight +-20% bands,
7:30 p.m. consolidated-price snapshot). This recorder, at 09:35 ET AFTER the 09:30 open prints,
logs for the night book's current names: the overnight-session best bid/ask + last print nearest
04:00 ET (Alpaca SIP quotes/bars with timestamps inside [03:55, 04:05]) and the official 09:30
opening-cross print. Row: state/ovn-235.jsonl. Purpose: is the 21:00-04:00 book a better EXIT for
the night leg (sell overnight vs selling the 09:30 cross)? Gate = 60 trade dates (prose Watch
OVN-23/5). Before 2026-12-06 the module exits without logging (the session does not exist).
Data-coverage flags are logged honestly per name: alpaca overnight availability is UNVERIFIED
until the session exists (registered caveat).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import time as tmod
from pathlib import Path

import urllib.request
import urllib.parse

LOG_NAME = "ovn-235.jsonl"
START = dt.date(2026, 12, 6)     # first day of the 23/5 session
NEED = 60
Q_URL = "https://data.alpaca.markets/v2/stocks/quotes"
B_URL = "https://data.alpaca.markets/v2/stocks/bars"
AU_URL = "https://data.alpaca.markets/v2/stocks/auctions"
ROOT = Path(__file__).resolve().parents[2]


def _headers() -> dict:
    if "ALPACA_API_KEY" not in os.environ:
        env = ROOT / ".env"
        if env.exists():
            for ln in env.read_text().splitlines():
                if "=" in ln and not ln.lstrip().startswith("#"):
                    k, v = ln.strip().split("=", 1)
                    os.environ.setdefault(k, v.strip().strip('"').strip("'"))
    return {"APCA-API-KEY-ID": os.environ["ALPACA_API_KEY"], "APCA-API-SECRET-KEY": os.environ["ALPACA_SECRET_KEY"]}


def _get(url: str, params: dict, H: dict) -> dict:
    for k in range(4):
        r = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers=H)
        try:
            with urllib.request.urlopen(r, timeout=30) as resp:
                if resp.status == 429:
                    tmod.sleep(5 * (k + 1))
                    continue
                return json.load(resp)
        except Exception:
            if k == 3:
                return {}
            tmod.sleep(3)
    return {}


def night_buys_yesterday(logs_dir: Path, d_yesterday: str) -> list[str]:
    def rows(date_str: str) -> list[str]:
        out = []
        p = Path(logs_dir, "daily-fills-live.jsonl")
        if p.exists():
            for line in p.read_text().splitlines():
                try:
                    x = json.loads(line)
                except ValueError:
                    continue
                if x.get("coid", "").startswith("dlv.") and x.get("leg") == "night" and x.get("side") == "buy" \
                        and str(x.get("filled_at", "")).startswith(date_str):
                    out.append(x["sym"])
        return out
    syms = rows(d_yesterday) or rows(d_yesterday.replace("-", "_"))
    return sorted(set(syms))


def overnight_quotes(H: dict, syms: list[str], d: dt.date) -> dict[str, dict]:
    """Name -> bid/ask/last nearest 04:00 ET from the trade date's overnight-window prints."""
    et0 = dt.datetime(d.year, d.month, d.day, 4, 0, tzinfo=_et())
    def win(a, b):
        return [et0 + dt.timedelta(minutes=a), et0 + dt.timedelta(minutes=b)]
    out = {}
    lo, hi = win(-5, 5)
    j = _get(Q_URL, dict(symbols=",".join(syms), start=lo.isoformat(), end=hi.isoformat(),
                         feed="sip", limit=10000), H)
    bars = _get(B_URL, dict(symbols=",".join(syms), timeframe="1Min",
                            start=lo.isoformat(), end=hi.isoformat(), feed="sip", limit=10000), H)
    last_by_ts = {}
    for s, rows in (bars.get("bars") or {}).items():
        for x in rows:
            last_by_ts[s] = x
    for s in syms:
        qs = (j.get("quotes") or {}).get(s) or []
        q4 = None
        target = et0.timestamp()
        for x in qs:
            ts = _ts(x.get("t"))
            if ts is None:
                continue
            if q4 is None or abs(ts - target) < abs(_ts(q4["t"]) - target):
                q4 = x
        b4 = a4 = ts4 = None
        if q4:
            b4 = q4.get("bp") or q4.get("bid_price")
            a4 = q4.get("ap") or q4.get("ask_price")
            ts4 = q4.get("t")
            if ts4 and (abs(_ts(ts4) - target) > 900):
                b4 = a4 = ts4 = None
        lb = last_by_ts.get(s)
        last4 = lb.get("c") if lb else None
        out[s] = dict(b4=b4, a4=a4, ts4=ts4, last4=last4,
                      flat=bool(qs), covered=(q4 is not None))
    return out


def _et():
    import zoneinfo
    return zoneinfo.ZoneInfo("America/New_York")


def _ts(x):
    if not x:
        return None
    try:
        return dt.datetime.fromisoformat(str(x).replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def official_opens(H: dict, syms: list[str], d: str) -> dict[str, float]:
    out = {}
    tok = None
    while True:
        q = dict(symbols=",".join(syms), start=d, end=d, feed="sip", limit=10000)
        if tok:
            q["page_token"] = tok
        j = _get(AU_URL, q, H)
        for s, rows in (j.get("auctions") or {}).items():
            for x in rows:
                if x.get("d", "").startswith(d) and x.get("o"):
                    o = max(x["o"], key=lambda p: p.get("s", 0))
                    out[s] = o["p"]
        tok = j.get("next_page_token")
        if not tok:
            return out


def run(state_dir: Path, logs_dir: Path) -> None:
    today = dt.date.today()
    if today < START:
        print(f"[ovn-235] {today} before session start {START}; skip")
        return
    d_y = today - dt.timedelta(days=1)
    # skip weekends/holidays cheaply: no night fills yesterday -> nothing to record
    syms = night_buys_yesterday(logs_dir, d_y.isoformat())
    if not syms:
        print(f"[ovn-235] no night buys on {d_y}; skip")
        return
    H = _headers()
    q = overnight_quotes(H, syms, today)
    op = official_opens(H, syms, today.isoformat())
    et = _et()
    row = dict(date=today.isoformat(), night_date=d_y.isoformat(),
               names={}, src="alpaca_sip", note="bid/ask/last nearest 04:00 vs official 09:30 open")
    for s in syms:
        o4 = op.get(s)
        b4, a4, last4 = q.get(s, {}).get("b4"), q.get(s, {}).get("a4"), q.get(s, {}).get("last4")
        mid = (b4 + a4) / 2 if (b4 and a4) else last4
        gap = (mid / o4 - 1) * 1e4 if (mid and o4) else None
        row["names"][s] = dict(o4=o4, b4=b4, a4=a4, last4=last4, ts4=q.get(s, {}).get("ts4"),
                               gap_bp=gap, covered=q.get(s, {}).get("covered", False))
    n_cov = sum(1 for v in row["names"].values() if v["covered"])
    row["n_names"] = len(syms)
    row["n_covered"] = n_cov
    state_dir.mkdir(parents=True, exist_ok=True)
    with (state_dir / LOG_NAME).open("a") as f:
        f.write(json.dumps(row) + "\n")
    print(f"[ovn-235] {len(syms)} names, {n_cov} with overnight prints; " + line(), flush=True)


def line() -> str:
    import statistics as st
    p = Path(ROOT, "state", LOG_NAME)
    if not p.exists():
        return "no sessions yet"
    rows = _read(p)
    dates = sorted({r["date"] for r in rows})
    gaps = []
    for r in rows:
        for s, nm in r.get("names", {}).items():
            if nm.get("gap_bp") is not None:
                gaps.append(nm["gap_bp"])
    if not gaps:
        return f"dates={len(dates)}/{NEED}; no overnight prints served yet"
    return (f"dates={len(dates)}/{NEED}; names-with-prints n={len(gaps)}; "
            f"median gap vs official open {st.median(gaps):+.1f}bp")


def _read(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for ln in p.read_text().splitlines():
        try:
            out.append(json.loads(ln))
        except ValueError:
            continue
    return out


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    run(root / "state", root / "logs")
