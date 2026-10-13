"""Coinbase US perp-style futures funding logger (deep loop iter 8, `research/drafts/crypto_access_2026-10-12.md`): logs, never orders.

Coinbase Derivatives (US, CDE) lists perp-style futures (e.g. BIP-20DEC30-CDE = BTC, ETP = ETH) that pay hourly funding.
No one publishes that funding history, so this records it: each hourly run GETs the PUBLIC product list (no key) and appends
one row per CDE product that quotes a funding rate. INTX (non-US) products are skipped: the user cannot trade them.
The question it answers later: is US perp funding large and persistent enough (hourly rate x 8760) to carry a spot-vs-perp
basis trade at $2-25k after fees? Decided on >= 90 days of rows, not before.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import requests

LOG_NAME = "cb-funding.jsonl"
URL = "https://api.coinbase.com/api/v3/brokerage/market/products"
START = "2026-10-13"
NEED = 90          # days of hourly rows before any economics is read
KEEP = ("BIP", "ETP")   # the majors the user can trade; all CDE perps are logged, these are summarized


def fetch() -> list[dict]:
    r = requests.get(URL, params={"product_type": "FUTURE"}, timeout=20)
    r.raise_for_status()
    return r.json().get("products", [])


def rows(products: list[dict], now: str) -> list[dict]:
    out = []
    for p in products:
        pid = p.get("product_id", "")
        if not pid.endswith("-CDE"):
            continue
        f = p.get("future_product_details") or {}
        rate = f.get("funding_rate") or (f.get("perpetual_details") or {}).get("funding_rate")
        if rate in (None, ""):
            continue
        out.append(dict(ts=now, sym=pid, price=_f(p.get("price")), rate=_f(rate), funding_time=f.get("funding_time"),
                        interval=f.get("funding_interval"), oi=_f(f.get("open_interest")), vol24=_f(p.get("volume_24h"))))
    return out


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def summary(log: list[dict]) -> dict:
    days = sorted({r["ts"][:10] for r in log})
    by = {}
    for r in log:
        root = r["sym"].split("-")[0]
        if root in KEEP and r.get("rate") is not None:
            by.setdefault(root, []).append(r["rate"])
    ann = {k: sum(v) / len(v) * 8760 for k, v in by.items()}
    return dict(days=len(days), rows=len(log), ann=ann)


def line(log: list[dict]) -> str:
    s = summary(log)
    a = ", ".join(f"{k} {v:+.1%}/yr" for k, v in sorted(s["ann"].items())) or "no BIP/ETP rows"
    return f"{s['days']}/{NEED} days, {s['rows']} rows; mean funding annualized: {a}"


def run(state: Path, now: str | None = None, products: list[dict] | None = None) -> int:
    now = now or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new = rows(products if products is not None else fetch(), now)
    state.mkdir(parents=True, exist_ok=True)
    with open(state / LOG_NAME, "a") as fh:
        for r in new:
            fh.write(json.dumps(r) + "\n")
    return len(new)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(f"cb_funding_log: {run(root / 'state')} rows")
