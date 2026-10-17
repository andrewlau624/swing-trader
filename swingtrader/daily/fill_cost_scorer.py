"""Fill-cost scorer (audit_execution_1002.md item 1, describe-only there; LOG-ONLY, no orders).

The executor's `slippage_bps` is fill-vs-DECISION-reference drift, not cost (audit 2026-10-02:
true cost ~0bp on auction fills, 213/216 at the official SIP print). This module supplies the
missing cost field for every fill row without touching live code:

  state/fill-costs.jsonl, one row per unscored fill:
    {coid, sym, leg, side, qty, fill_px, filled_at, official_px, print_size, cost_bp, kind}

Cost definition: auction legs (fill time 09:30 or 16:00 ET) score fill_px vs the official SIP
auction print of the SAME session (largest-size 'O' open / '6' close print via the Alpaca
auctions endpoint); non-auction fills (noise intraday) are marked cost_kind='mid_unclosed' and
skipped for the headline numbers (their NBBO check lives in the execution audit, not a per-fill
cron). Rows are keyed by (coid, filled_at, fill_px) so re-runs are idempotent.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import time as tmod
import urllib.parse
import urllib.request
from pathlib import Path

import requests

LOG_NAME = "fill-costs.jsonl"        # state/
AU_URL = "https://data.alpaca.markets/v2/stocks/auctions"
ROOT = Path(__file__).resolve().parents[2]
LATER = dt.timedelta(minutes=30)     # wait for the auction print to be published on the tape


def _headers() -> dict:
    if "ALPACA_API_KEY" not in os.environ:
        env = ROOT / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    os.environ.setdefault(k, v.strip().strip('"').strip("'"))
    return {"APCA-API-KEY-ID": os.environ["ALPACA_API_KEY"], "APCA-API-SECRET-KEY": os.environ["ALPACA_SECRET_KEY"]}


def _get(url: str, params: dict, H: dict) -> dict:
    for k in range(4):
        try:
            r = requests.get(url, params=params, headers=H, timeout=30)
            if r.status_code == 429:
                tmod.sleep(5 * (k + 1))
                continue
            r.raise_for_status()
            return r.json()
        except Exception:
            if k == 3:
                return {}
            tmod.sleep(3)
    return {}


def _et():
    import zoneinfo
    return zoneinfo.ZoneInfo("America/New_York")


def _leg_kind(filled_at: str) -> str:
    """'open' / 'close' by the fill's ET wall-clock; anything else = 'mid_unclosed'."""
    try:
        t = dt.datetime.fromisoformat(str(filled_at).replace("+0000", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=dt.timezone.utc)
        t = t.astimezone(_et())
        hh, mm = t.hour, t.minute
        if hh == 9 and 25 <= mm < 45:
            return "open"
        if hh == 16:
            return "close"
        return "mid_unclosed"
    except Exception:
        return "mid_unclosed"


def _trade_date(filled_at: str) -> str:
    t = dt.datetime.fromisoformat(str(filled_at).replace("+0000", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    return t.astimezone(_et()).date().isoformat()


def official(H: dict, sym: str, date: str, kind: str):
    """(official_px, print_size) of the largest auction print for that session; None if not on tape.
    kind: 'open' -> the 'O'-flag auction in the 'o' array, 'close' -> the auction after 15:00 in the 'c' array."""
    tbl = auction_table(H, sym, date)
    if tbl is None:
        return None, None
    key = "o" if kind == "open" else "c"
    arr = [q for q in tbl[key] if (kind == "open" and str(q.get("c")) == "O")]
    p = max(arr or tbl[key], key=lambda q: q.get("s", 0))
    return p.get("p"), p.get("s", 0)


def auction_table(H: dict, sym: str, date: str) -> dict | None:
    """The one auction row for (sym, date); cached file state/fill-costs-auctions.json to survive restarts."""
    cache = state_dir_cache(H)
    if date in cache and sym in cache[date]:
        return cache[date][sym]
    j = _get(AU_URL, dict(symbols=sym, start=date, end=date, feed="sip", limit=10000), H)
    rows = ((j or {}).get("auctions") or {}).get(sym) or []
    row = None
    for x in rows:
        if str(x.get("d", "")).startswith(date):
            row = x
    cache.setdefault(date, {})[sym] = row
    path = ROOT / "state" / "fill-costs-auctions.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache))
    return row


def state_dir_cache(H) -> dict:
    p = ROOT / "state" / "fill-costs-auctions.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except ValueError:
            return {}
    return {}


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


def run(state_dir: Path, logs_dir: Path) -> int:
    H = _headers()
    spat = Path(state_dir, LOG_NAME)
    done = {(r["coid"], r["filled_at"], r["fill_px"]) for r in _read(spat)}
    now = dt.datetime.now(dt.timezone.utc)
    scored = 0
    rows = []
    # prefetch: one call per missing trade DATE over the distinct symbols of that date (~17 calls, not 183)
    todo_all = []
    for fn in ("daily-fills-live.jsonl", "daily-fills-roth.jsonl"):
        p = Path(logs_dir, fn)
        if not p.exists():
            continue
        for ln in p.read_text().splitlines():
            try:
                f = json.loads(ln)
            except ValueError:
                continue
            if (f.get("coid"), f.get("filled_at"), f.get("fill_px")) in done:
                continue
            kind = _leg_kind(str(f.get("filled_at", "")))
            if kind != "mid_unclosed" and f.get("fill_px") and f.get("coid"):
                try:
                    t = dt.datetime.fromisoformat(str(f["filled_at"]).replace("+0000", "+00:00").replace("Z", "+00:00"))
                    if t.tzinfo is None:
                        t = t.replace(tzinfo=dt.timezone.utc)
                except Exception:
                    continue
                if now - t >= LATER:
                    todo_all.append((f, kind))
    by_date: dict[str, set[str]] = {}
    for f, _k in todo_all:
        by_date.setdefault(_trade_date(f["filled_at"]), set()).add(f["sym"])
    cache = state_dir_cache(H)
    for d, syms in by_date.items():
        missing = [s for s in sorted(syms) if s not in cache.get(d, {})]
        for i in range(0, len(missing), 100):
            j = _get(AU_URL, dict(symbols=",".join(missing[i:i + 100]), start=d, end=d, feed="sip", limit=10000), H)
            got = (j or {}).get("auctions") or {}
            for s, rs in got.items():
                row = next((x for x in rs if str(x.get("d", "")).startswith(d)), None)
                cache.setdefault(d, {})[s] = row
            for s in missing[i:i + 100]:
                cache.setdefault(d, {}).setdefault(s, None)
        (ROOT / "state" / "fill-costs-auctions.json").write_text(json.dumps(cache))
    for f, kind in todo_all:
        fa = str(f.get("filled_at", ""))
        row = dict(coid=f["coid"], sym=f["sym"], leg=f.get("leg"), side=f.get("side"), qty=f.get("qty"),
                   fill_px=f["fill_px"], filled_at=fa, cost_kind=kind, src="alpaca_auctions")
        if kind == "mid_unclosed":
            row.update(official_px=None, print_size=None, cost_bp=None,
                       note="intraday fill; NBBO mid check not per-fill")
        else:
            td = _trade_date(fa)
            tbl = auction_table(H, f["sym"], td)
            px, size = (None, None) if tbl is None else (None, None)
            if tbl:
                key = "o" if kind == "open" else "c"
                arr = [q for q in (tbl.get(key) or []) if not (kind == "open" and str(q.get("c")) != "O")]
                if arr:
                    p = max(arr, key=lambda q: q.get("s", 0))
                    px, size = p.get("p"), p.get("s", 0)
            if px:
                row.update(official_px=px, print_size=size,
                           cost_bp=round((f["fill_px"] / px - 1) * 1e4 * (1 if f.get("side") == "buy" else -1), 2))
            else:
                row.update(official_px=None, print_size=None, cost_bp=None, note="print not on tape")
        rows.append(row)
        done.add((f.get("coid"), f.get("filled_at"), f.get("fill_px")))
        scored += 1
    if rows:
        spat.parent.mkdir(parents=True, exist_ok=True)
        with spat.open("a") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
    return scored


def line(state_dir: Path) -> str:
    import statistics as st
    rows = _read(Path(state_dir, LOG_NAME))
    vals = [r["cost_bp"] for r in rows if r.get("cost_bp") is not None]
    if not vals:
        return "no scored auction fills yet"
    by_leg = {}
    for leg in sorted({r.get("leg") for r in rows if r.get("cost_bp") is not None}):
        v = [r["cost_bp"] for r in rows if r.get("cost_bp") is not None and r.get("leg") == leg]
        by_leg[leg] = f"{leg} {st.mean(v):+.1f}bp (n={len(v)}, med {st.median(v):+.1f})"
    return f"n={len(vals)} scored fills, true cost mean {st.mean(vals):+.1f}bp median {st.median(vals):+.1f}bp; " + " | ".join(by_leg.values())


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    n = run(root / "state", root / "logs")
    print(f"[fill-costs] scored {n} new; " + line(root / "state"), flush=True)
