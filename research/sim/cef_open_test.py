"""CEF-RV execution test (user-approved 2026-10-07): does a pre-open Schwab order on a CEF fill at the official opening cross?

One share, Roth, through the live book's own open-order path (SchwabAdapter.submit, tif "opg": a market DAY order placed
before 09:30, directed to the listing exchange, Schwab routing as fallback). Run on the server:

    .venv/bin/python -m research.sim.cef_open_test check  JRI
    .venv/bin/python -m research.sim.cef_open_test buy    JRI      # before 09:30 ET
    .venv/bin/python -m research.sim.cef_open_test sell   JRI      # before 09:30 ET, a later session
    .venv/bin/python -m research.sim.cef_open_test report JRI      # after 09:31 ET: fills vs the official SIP open cross

Every action appends to logs/cef-open-test.jsonl. Never sells more than the Roth holds (no short in a Roth).
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

from swingtrader.daily.brokers import make_adapter
from swingtrader.daily.exdate_open_shadow import _headers
from swingtrader.daily.pref_ex_shadow import crosses

LOG = Path(__file__).resolve().parents[2] / "logs" / "cef-open-test.jsonl"
ET = ZoneInfo("America/New_York")


def log(row: dict) -> None:
    row = {"ts": dt.datetime.now(ET).isoformat(timespec="seconds"), **row}
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps(row) + "\n")
    print(json.dumps(row))


def held(ad, sym: str) -> float:
    return float(getattr(ad.positions().get(sym), "qty", 0.0) or 0.0)


def main(argv: list[str]) -> int:
    cmd, sym = argv[0], argv[1].upper()
    ad = make_adapter("roth")
    now = dt.datetime.now(ET)
    if cmd == "check":
        a = ad.account()
        log(dict(cmd=cmd, sym=sym, cash=a.cash, held=held(ad, sym)))
        return 0
    if cmd in ("buy", "sell"):
        if not (now.time() < dt.time(9, 28)):
            raise SystemExit("open-cross test orders must be placed before 09:28 ET")
        if cmd == "sell" and held(ad, sym) < 1:
            raise SystemExit(f"Roth holds no {sym}: refusing (a sell would become a short)")
        oid = ad.submit(sym, cmd, "opg", f"cef-open-test-{cmd}", qty=1)
        log(dict(cmd=cmd, sym=sym, order_id=oid, route=ad.last_route, route_note=ad.route_note, refusal=ad.refusal))
        return 0
    if cmd == "report":
        rows = [json.loads(x) for x in LOG.read_text().splitlines()] if LOG.exists() else []
        day = now.date().isoformat()
        X = crosses([sym], day, day, _headers()).get(sym, {}).get(day)
        for r in rows:
            if r.get("sym") != sym or r.get("cmd") not in ("buy", "sell") or r["ts"][:10] != day:
                continue
            o = ad.c.get_order(r["order_id"], ad.hash).json()
            fills = [e for a in o.get("orderActivityCollection", []) or [] for e in a.get("executionLegs", []) or []]
            px = [float(e["price"]) for e in fills]
            fill = sum(px) / len(px) if px else None
            cross = X[0] if X else None
            log(dict(cmd="report", sym=sym, side=r["cmd"], order_id=r["order_id"], status=o.get("status"),
                     fill=fill, fill_times=[e.get("time") for e in fills], route=r.get("route"),
                     open_cross=cross, open_cross_size=X[1] if X else None,
                     diff_bp=round((fill / cross - 1) * 1e4, 1) if fill and cross else None))
        return 0
    raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
