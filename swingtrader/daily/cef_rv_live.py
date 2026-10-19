"""CEF-RV LIVE module (Roth, OO form): buy a closed-end fund at the opening cross of the first session after its discount
hits its own trailing-52-week 10th percentile, sell at the opening cross of the first session after it recovers to its
median (or 260 days). Pre-registered CEF-RV (CEF-OOS N 890: +333bp/trade on untouched 1999-2014), CEF-ALPHA (N 892: +125bp
vs the EW CEF universe 2016-26, t 5.6), CEF-PEER (N 933: +114bp vs same-category peers, every category positive);
CEF-SURV99 caveat: the 1999-2014 pass is survivorship-flattered, the forward gate (CEF-RV-FWD, 60 closed trades) decides.
~+4.8pp/yr excess on deployed capital: a Roth upgrade over holding beta, below the +8pp stand-alone gate. Standalone systemd
timer (deploy/cef-rv-live.*), weekdays 09:05 ET, Roth only.

    daily.cef_rv_mode: off | dry | live   (config.yaml; default off = one log line and exit)

Signals come from the CEF-RV forward shadow (cef_rv_shadow.py, research-shadows 08:20 ET): state/cef-rv.jsonl rows
{sym, signal, exit_signal, ...} where `signal` / `exit_signal` are weekly (Friday) CEFConnect dates and the execution
session is the FIRST SESSION AFTER that date. Each run: (1) score yesterday's live fills against the official opening
cross, (2) SELL (pre-open market, AUTO route -> 09:30 cross) every held fund whose exit session is today or earlier,
(3) BUY the forward (not backfill) entries whose execution session is exactly today, deepest discount vs its own median
first, equal slots of max($500, min($1,000, equity/10)), whole shares, funded ONLY from settled Roth cash minus today's
PREF-EX reservation (BIL/SGOV never sold; GFV-safe), at most floor(0.5 x equity / slot) positions. Entries whose session
has already passed are logged as missed, never chased. Holdings: state/cef-rv-live.json; their market value is written to
state/cef-rv-held.json {"usd"} for a future executor reservation hook (NOT wired: the Roth night leg's cash is the bot's
virtual book, not broker cash; see deploy_loop_2026-10-10.md). `dry` does everything but submit. Never shorts.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import statistics
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
LOG_NAME = "cef-rv-live.jsonl"            # logs/: every action + scores (the REGISTRY reader)
STATE_NAME = "cef-rv-live.json"           # state/: {"open": {sym: {qty, entry_px, entry_date, signal_week, ...}}}
HELD_NAME = "cef-rv-held.json"            # state/: {"date", "usd"} market value of the live holdings
SIGNALS_NAME = "cef-rv.jsonl"             # state/: the CEF-RV shadow's trade rows
PANEL_NAME = "cef-rv-panel.json"          # state/: sym -> [[week, discount], ...] (for the priority order)
RESERVED_NAME = "pref-ex-reserved.json"   # state/: PREF-EX live's {"date", "usd"} (same-day dollars already spoken for)
ET = ZoneInfo("America/New_York")
WINDOW = (dt.time(8, 0), dt.time(9, 28))  # pre-open orders only: after that the open cross is not reachable
SLOT_MIN, SLOT_MAX, SLOT_DIV = 500.0, 1000.0, 10.0
MAX_EQUITY_FRAC = 0.50
FORWARD_FROM = "2026-10-08"               # = cef_rv_shadow.FORWARD_FROM: earlier signal weeks are backfill, never traded
NEED = 30                                 # live round trips before the cost readout counts
CASH_LIKE = ("BIL", "SGOV")


def _jsonl(p: Path) -> list[dict]:
    out = []
    for x in (p.read_text().splitlines() if p.exists() else []):
        try:
            out.append(json.loads(x))
        except ValueError:
            continue
    return out


def is_session(d: dt.date) -> bool:
    from .cpc_ledger import is_session as s
    return s(d)


def exec_session(signal: str) -> dt.date:
    """The first session strictly after a weekly signal date."""
    from .cpc_ledger import next_session
    return next_session(dt.date.fromisoformat(signal) + dt.timedelta(days=1))


def slot_usd(equity: float) -> float:
    return max(SLOT_MIN, min(SLOT_MAX, equity / SLOT_DIV))


def max_positions(equity: float) -> int:
    return int(math.floor(MAX_EQUITY_FRAC * equity / slot_usd(equity)))


def entries(rows: list[dict], today: dt.date, held: dict) -> tuple[list[dict], list[dict]]:
    """(buy today, missed): forward signal rows with no exit signal, not already held, whose execution session is today
    (missed = session already passed; logged, never chased)."""
    buy, missed, seen = [], [], set()
    for r in rows:
        sym, sig = r.get("sym"), r.get("signal")
        if not sym or not sig or sig < FORWARD_FROM or r.get("exit_signal") or sym in held or (sym, sig) in seen:
            continue
        seen.add((sym, sig))
        es = exec_session(sig)
        if es == today:
            buy.append(r)
        elif es < today:
            missed.append(r)
    return buy, missed


def exits(rows: list[dict], today: dt.date, held: dict) -> list[dict]:
    """Held funds whose shadow row (same signal week) carries an exit signal with execution session <= today."""
    out = []
    for r in rows:
        h = held.get(r.get("sym"))
        if not h or h.get("signal_week") != r.get("signal") or not r.get("exit_signal"):
            continue
        if exec_session(r["exit_signal"]) <= today:
            out.append(dict(r, exit_session=exec_session(r["exit_signal"]).isoformat()))
    return out


def depth(panel: dict, sym: str, signal: str) -> float:
    """Discount at the signal week minus the fund's trailing-52-week median: more negative = deeper. 0 if unknown."""
    rows = panel.get(sym) or []
    hist = [(d, x) for d, x in rows if d <= signal and x is not None and math.isfinite(x)]
    if not hist:
        return 0.0
    win = [x for _, x in hist[-52:]]
    return float(hist[-1][1] - statistics.median(win))


def size(cands: list[dict], last: dict[str, float], panel: dict, settled: float, equity: float, n_held: int) -> list[dict]:
    """Whole-share slot buys, deepest discount first, <= max_positions - n_held names, total <= settled cash. A fund whose
    slot does not fit the remaining budget gets a smaller lot; zero-share lots are skipped."""
    slot = slot_usd(equity)
    room = max(0, max_positions(equity) - n_held)
    budget = max(0.0, min(settled, MAX_EQUITY_FRAC * equity - n_held * slot))
    order = sorted(cands, key=lambda r: depth(panel, r["sym"], r["signal"]))
    out, spent = [], 0.0
    for r in order:
        if len(out) >= room:
            break
        px = last.get(r["sym"])
        if not px or px <= 0:
            continue
        usd_target = min(slot, budget - spent)
        qty = math.floor(usd_target / px)
        if qty < 1:
            continue
        usd = qty * px
        out.append(dict(sym=r["sym"], qty=int(qty), px=float(px), usd=round(usd, 2), signal=r["signal"],
                        depth=round(depth(panel, r["sym"], r["signal"]), 4)))
        spent += usd
    return out


def _quotes(ad, syms: list[str]) -> dict[str, float]:
    """Schwab last price per symbol (pre-open: last, else mark, else prior close)."""
    if not syms:
        return {}
    j = ad.c.get_quotes(syms).json() or {}
    out = {}
    for s in syms:
        q = (j.get(s) or {}).get("quote") or {}
        px = q.get("lastPrice") or q.get("mark") or q.get("closePrice")
        if px:
            out[s] = float(px)
    return out


def _settled_cash(acct) -> float:
    sc = getattr(acct, "settled_cash", None)
    return float(sc if sc is not None else acct.cash)


def _reserved(state_dir: Path, today: dt.date) -> float:
    try:
        j = json.loads((state_dir / RESERVED_NAME).read_text())
        return max(0.0, float(j.get("usd") or 0.0)) if j.get("date") == today.isoformat() else 0.0
    except Exception:  # noqa: BLE001
        return 0.0


def _fills(ad, order_id: str) -> tuple[float | None, int]:
    legs = []
    for oid in str(order_id).split(","):
        if not oid:
            continue
        o = ad.c.get_order(int(oid), ad.hash).json()
        legs += [e for a in o.get("orderActivityCollection", []) or [] for e in a.get("executionLegs", []) or []]
    q = sum(float(e.get("quantity") or 0) for e in legs)
    if not q:
        return None, 0
    return sum(float(e["price"]) * float(e.get("quantity") or 0) for e in legs) / q, int(q)


def score(rows: list[dict], ad, today: dt.date, crosses_fn, H: dict | None, log_row) -> int:
    """Score every live buy/sell from a past session that has no score row yet: fill vs the official OPENING cross."""
    done = {r.get("order_id") for r in rows if r.get("cmd") == "score"}
    n = 0
    for r in list(rows):
        if r.get("cmd") not in ("buy", "sell") or r.get("dry_run") or not r.get("order_id") or r["order_id"] in done:
            continue
        day = r["ts"][:10]
        if day >= today.isoformat():
            continue
        try:
            fill, q = _fills(ad, r["order_id"])
            X = crosses_fn([r["sym"]], day, day, H).get(r["sym"], {}).get(day)
        except Exception as exc:  # noqa: BLE001
            log_row(dict(cmd="score-skip", sym=r["sym"], order_id=r["order_id"], err=str(exc)[:80]))
            continue
        cross = X[0] if X else None
        log_row(dict(cmd="score", sym=r["sym"], side=r["cmd"], order_id=r["order_id"], day=day, qty=q, fill=fill,
                     open_cross=cross, open_cross_size=X[1] if X else None,
                     diff_bp=round((fill / cross - 1) * 1e4, 1) if fill and cross else None))
        n += 1
    return n


def summary(rows: list[dict]) -> dict:
    sc = [r for r in rows if r.get("cmd") == "score" and r.get("diff_bp") is not None]
    buys = [r["diff_bp"] for r in sc if r["side"] == "buy"]
    sells = [r["diff_bp"] for r in sc if r["side"] == "sell"]
    live = [r for r in rows if r.get("cmd") in ("buy", "sell") and not r.get("dry_run") and r.get("order_id")]
    dry = [r for r in rows if r.get("cmd") in ("buy", "sell") and r.get("dry_run")]
    return dict(round_trips=len(sells), buys=len(buys), sells=len(sells), live_orders=len(live), dry_orders=len(dry),
                buy_cost_bp=statistics.fmean(buys) if buys else None,       # + = paid above the open cross
                sell_cost_bp=-statistics.fmean(sells) if sells else None)   # + = sold below the open cross


def line(rows: list[dict]) -> str:
    s = summary(rows)
    f = lambda v: "n/a" if v is None else f"{v:+.1f}bp"  # noqa: E731
    return (f"{s['round_trips']}/{NEED} live round trips; cost vs opening cross buy {f(s['buy_cost_bp'])} (n {s['buys']}), "
            f"sell {f(s['sell_cost_bp'])} (n {s['sells']}); {s['live_orders']} live / {s['dry_orders']} dry orders")


def run(mode: str, state_dir: Path, logs_dir: Path, log=print, today: dt.date | None = None, now: dt.datetime | None = None,
        ad=None, crosses_fn=None, quotes_fn=None, H: dict | None = None) -> dict:
    mode = (mode or "off").lower()
    if mode == "off":
        log("[cef-rv-live] off (daily.cef_rv_mode); nothing to do")
        return dict(mode=mode, skipped="off")
    if mode not in ("dry", "live"):
        raise ValueError(f"daily.cef_rv_mode must be off|dry|live, got {mode!r}")
    now = now or dt.datetime.now(ET)
    today = today or now.date()
    state_dir, logs_dir = Path(state_dir), Path(logs_dir)
    logp, statep = logs_dir / LOG_NAME, state_dir / STATE_NAME
    rows = _jsonl(logp)

    def log_row(r: dict) -> None:
        r = {"ts": dt.datetime.now(ET).isoformat(timespec="seconds"), "mode": mode, **r}
        logs_dir.mkdir(exist_ok=True)
        with logp.open("a") as f:
            f.write(json.dumps(r) + "\n")
        rows.append(r)
        log("[cef-rv-live] " + json.dumps({k: v for k, v in r.items() if k not in ("ts", "mode")}))

    if ad is None:
        from .brokers import make_adapter
        ad = make_adapter("roth")
    if crosses_fn is None or H is None:
        from .exdate_open_shadow import _headers
        from .pref_ex_shadow import crosses
        crosses_fn, H = crosses_fn or crosses, H or _headers()
    quotes_fn = quotes_fn or _quotes
    out = dict(mode=mode, scored=0, sold=[], bought=[], missed=[], held_usd=0.0)

    out["scored"] = score(rows, ad, today, crosses_fn, H, log_row)
    if not is_session(today):
        log(f"[cef-rv-live] {today} is not a session; scored {out['scored']}, no orders")
        return out
    if not (WINDOW[0] <= now.time() <= WINDOW[1]):
        log(f"[cef-rv-live] outside the {WINDOW[0]:%H:%M}-{WINDOW[1]:%H:%M} ET pre-open window; scored {out['scored']}, no orders")
        return out

    state = json.loads(statep.read_text()) if statep.exists() else {"open": {}}
    sig_rows = _jsonl(state_dir / SIGNALS_NAME)
    held = ad.positions()

    # --- sell leg: held funds whose exit session is today (or earlier, if a run was missed)
    for r in exits(sig_rows, today, state["open"]):
        sym, h = r["sym"], state["open"][r["sym"]]
        have = float(getattr(held.get(sym), "qty", 0.0) or 0.0)
        qty = int(min(have, float(h["qty"])))
        if qty < 1:
            log_row(dict(cmd="sell-skip", sym=sym, reason=f"account holds {have:g}"))
            state["open"].pop(sym)
            continue
        late = r["exit_session"] < today.isoformat()
        if mode == "live":
            oid = ad.submit(sym, "sell", "opg", f"cef-rv-live.sell.{sym}.{today}", qty=qty)
            log_row(dict(cmd="sell", sym=sym, qty=qty, signal=r["signal"], exit_signal=r["exit_signal"], late=late, order_id=oid))
        else:
            log_row(dict(cmd="sell", sym=sym, qty=qty, signal=r["signal"], exit_signal=r["exit_signal"], late=late, dry_run=True))
        out["sold"].append(sym)
        state["open"].pop(sym)

    # --- buy leg: forward entries whose execution session is today
    buy, missed = entries(sig_rows, today, state["open"])
    for r in missed:
        key = (r["sym"], r["signal"])
        if not any(x.get("cmd") == "missed" and (x.get("sym"), x.get("signal")) == key for x in rows):
            log_row(dict(cmd="missed", sym=r["sym"], signal=r["signal"], session=exec_session(r["signal"]).isoformat(),
                         reason="entry session already passed; not chased"))
        out["missed"].append(r["sym"])
    acct = ad.account()
    settled, equity = _settled_cash(acct), float(acct.equity)
    reserved = _reserved(state_dir, today)
    avail = max(0.0, settled - reserved)
    if not buy:
        log(f"[cef-rv-live] no forward entries for {today}; {len(state['open'])} held, settled ${settled:,.0f}")
    else:
        panel = json.loads((state_dir / PANEL_NAME).read_text()) if (state_dir / PANEL_NAME).exists() else {}
        last = quotes_fn(ad, sorted({r["sym"] for r in buy}))
        orders = size(buy, last, panel, avail, equity, len(state["open"]))
        total = round(sum(o["usd"] for o in orders), 2)
        log(f"[cef-rv-live] {len(buy)} entries for {today}, {len(orders)} sized, ${total:,.0f} of available "
            f"${avail:,.0f} (settled ${settled:,.0f} - PREF-EX ${reserved:,.0f}; equity ${equity:,.0f}, "
            f"slot ${slot_usd(equity):,.0f}, max {max_positions(equity)} positions)")
        for r in buy:
            if r["sym"] not in {o["sym"] for o in orders}:
                log_row(dict(cmd="buy-skip", sym=r["sym"], signal=r["signal"], last=last.get(r["sym"]),
                             reason="no budget / position room or 0 shares"))
        for o in orders:
            if mode == "live":
                oid = ad.submit(o["sym"], "buy", "opg", f"cef-rv-live.buy.{o['sym']}.{today}", qty=o["qty"])
                log_row(dict(cmd="buy", **o, order_id=oid))
            else:
                log_row(dict(cmd="buy", **o, dry_run=True))
            state["open"][o["sym"]] = dict(qty=o["qty"], entry_px=o["px"], entry_date=today.isoformat(),
                                           signal_week=o["signal"], dry_run=mode != "live")
            out["bought"].append(o["sym"])

    # --- holdings value, for a future executor reservation hook (not wired)
    px_now = {}
    if state["open"]:
        try:
            px_now = quotes_fn(ad, sorted(state["open"]))
        except Exception:  # noqa: BLE001
            px_now = {}
    out["held_usd"] = round(sum(h["qty"] * px_now.get(s, h["entry_px"]) for s, h in state["open"].items()), 2)
    real = {s: h for s, h in state["open"].items() if not h.get("dry_run")}     # dry holdings are not broker cash spent
    state_dir.mkdir(exist_ok=True)
    statep.write_text(json.dumps(state, indent=1))
    (state_dir / HELD_NAME).write_text(json.dumps({"date": today.isoformat(), "n": len(real), "mode": mode,
                                                   "usd": round(sum(h["qty"] * px_now.get(s, h["entry_px"])
                                                                    for s, h in real.items()), 2)}))
    return out


def main() -> int:
    from ..config import Config
    cfg = Config.load()
    run(getattr(cfg.daily, "cef_rv_mode", "off"), ROOT / "state", ROOT / "logs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
