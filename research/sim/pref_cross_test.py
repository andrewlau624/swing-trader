"""PREF-EX execution test (USER-RUN; Claude never places real orders): does a Schwab market-on-close order on a
$25-par preferred / baby bond fill at the official closing cross, in the Roth?

The CC form of PREF-EX: buy at the close the session BEFORE the ex-date, sell at the ex-date's close. One share by
default, Roth, through the live book's own MOC path (SchwabAdapter.submit, tif "cls"). Run on the server:

    .venv/bin/python -m research.sim.pref_cross_test pick                 # tomorrow's ex-dates from state/pref-ex.jsonl
    .venv/bin/python -m research.sim.pref_cross_test resolve PSEC.PRA     # which Schwab symbol format quotes it
    .venv/bin/python -m research.sim.pref_cross_test buy  PSEC.PRA [--schwab PSEC/PRA] [--qty 1] [--go]
    .venv/bin/python -m research.sim.pref_cross_test sell PSEC.PRA [--schwab PSEC/PRA] [--go]   # on the ex-date
    .venv/bin/python -m research.sim.pref_cross_test report PSEC.PRA      # after ~16:15 ET: fill vs official cross

buy/sell are DRY RUNS unless --go is given. MOC orders must be in before 15:45 ET (Schwab cutoff); the script refuses
after 15:43. Never sells more than the Roth holds (no short in a Roth). Every action appends to
logs/pref-cross-test.jsonl. Symbols: the shadow uses Alpaca's format (PSEC.PRA); Schwab's format for preferreds is not
verified in this repo, so run `resolve` first and pass the format that quotes with --schwab.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / "logs" / "pref-cross-test.jsonl"
SHADOW = ROOT / "state" / "pref-ex.jsonl"
ET = ZoneInfo("America/New_York")
CUTOFF = dt.time(15, 43)


def log(row: dict) -> None:
    row = {"ts": dt.datetime.now(ET).isoformat(timespec="seconds"), **row}
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps(row) + "\n")
    print(json.dumps(row))


def candidates(sym: str) -> list[str]:
    """Plausible broker spellings of an Alpaca-format preferred symbol (PSEC.PRA). Order = most likely first."""
    if ".PR" not in sym:
        return [sym]
    base, ser = sym.split(".PR", 1)
    return [f"{base}/PR{ser}", f"{base}/P{ser}", f"{base}-{ser}", f"{base}-P{ser}", f"{base}.PR{ser}", f"{base}p{ser}"]


def opt(argv: list[str], flag: str, default=None):
    return argv[argv.index(flag) + 1] if flag in argv else default


def pick(today: dt.date) -> list[dict]:
    """Shadow rows whose ex-date is the next weekday after today: buy at today's close (CC form)."""
    nxt = today + dt.timedelta(days=3 if today.weekday() == 4 else 1)
    rows = [json.loads(x) for x in SHADOW.read_text().splitlines() if x.strip()] if SHADOW.exists() else []
    return [r for r in rows if r.get("ex") == nxt.isoformat()]


def held(ad, sym: str) -> float:
    return float(getattr(ad.positions().get(sym), "qty", 0.0) or 0.0)


def main(argv: list[str]) -> int:
    cmd = argv[0]
    now = dt.datetime.now(ET)
    if cmd == "pick":
        rows = pick(now.date())
        for r in sorted(rows, key=lambda r: -(r.get("div") or 0)):
            print(f"{r['sym']:12} ex {r['ex']} div {r.get('div')} cls {r.get('cls')} status {r.get('status')}")
        log(dict(cmd="pick", n=len(rows), syms=[r["sym"] for r in rows]))
        return 0
    sym = argv[1].upper()
    from swingtrader.daily.brokers import make_adapter
    ad = make_adapter("roth")
    bsym = opt(argv, "--schwab", sym)
    if cmd == "resolve":
        out = {}
        for c in candidates(sym):
            try:
                j = ad.c.get_quotes([c]).json()
                q = (j.get(c) or {}).get("quote") or {}
                out[c] = {"last": q.get("lastPrice"), "bid": q.get("bidPrice"), "ask": q.get("askPrice")} if q else None
            except Exception as exc:  # noqa: BLE001
                out[c] = f"err {str(exc)[:60]}"
        log(dict(cmd="resolve", sym=sym, formats=out))
        return 0
    if cmd in ("buy", "sell"):
        if now.weekday() >= 5:
            raise SystemExit("not a session day: a MOC order placed now would queue for the next close")
        if now.time() >= CUTOFF:
            raise SystemExit("MOC test orders must be placed before 15:43 ET (Schwab MOC cutoff 15:45)")
        qty = int(opt(argv, "--qty", 1))
        if cmd == "sell":
            h = held(ad, bsym)
            if h < 1:
                raise SystemExit(f"Roth holds no {bsym}: refusing (a sell would become a short)")
            qty = min(qty if "--qty" in argv else int(h), int(h))
        if "--go" not in argv:
            log(dict(cmd=cmd, sym=sym, schwab=bsym, qty=qty, dry_run=True))
            return 0
        oid = ad.submit(bsym, cmd, "cls", f"pref-cross-test-{cmd}", qty=qty)
        log(dict(cmd=cmd, sym=sym, schwab=bsym, qty=qty, order_id=oid))
        return 0
    if cmd == "report":
        from swingtrader.daily.exdate_open_shadow import _headers
        from swingtrader.daily.pref_ex_shadow import crosses
        rows = [json.loads(x) for x in LOG.read_text().splitlines()] if LOG.exists() else []
        day = opt(argv, "--day", now.date().isoformat())
        try:
            X = crosses([sym], day, day, _headers()).get(sym, {}).get(day)
        except Exception as exc:  # noqa: BLE001  (Alpaca 403s on non-session days)
            raise SystemExit(f"no official cross for {sym} on {day} ({str(exc)[:80]}); run on the trade date or pass --day")
        for r in rows:
            if r.get("sym") != sym or r.get("cmd") not in ("buy", "sell") or r.get("dry_run") or r["ts"][:10] != day:
                continue
            o = ad.c.get_order(int(str(r["order_id"]).split(",")[0]), ad.hash).json()
            legs = [e for a in o.get("orderActivityCollection", []) or [] for e in a.get("executionLegs", []) or []]
            px = [float(e["price"]) for e in legs]
            fill = sum(px) / len(px) if px else None
            cross = X[2] if X else None
            log(dict(cmd="report", sym=sym, side=r["cmd"], order_id=r["order_id"], status=o.get("status"),
                     fill=fill, fill_times=[e.get("time") for e in legs], close_cross=cross,
                     close_cross_size=X[3] if X else None,
                     diff_bp=round((fill / cross - 1) * 1e4, 1) if fill and cross else None))
        return 0
    raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
