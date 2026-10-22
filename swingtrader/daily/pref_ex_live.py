"""PREF-EX + ETDX LIVE module (Roth, CC form): buy $25-par preferreds / baby bonds at the closing cross the session BEFORE
the ex-date, sell at the ex-date's closing cross, keep the dividend. Pre-registered PREF-EX (N 861, +38bp/event official
crosses 2021-26), ETDX (N 869, +44bp), ROTH-STACK (N 897: +8.4pp/yr at $3k, +5.4 at $10k from idle Roth cash; 3x cost leaves
+1.6 / +0.9). Standalone systemd timer (deploy/pref-ex-live.*), weekdays 15:25 ET, Roth only.

    daily.pref_ex_mode: off | dry | live   (config.yaml; default off = one log line and exit)

Each run: (1) score yesterday's live fills against the official closing cross, (2) SELL (MOC) the names bought yesterday
whose ex-date is today, (3) BUY (MOC) tomorrow's ex-date names from the PREF-EX shadow's event list, whole shares, 5% of the
name's trailing-10-session median closing-cross $ (10% once 30 scored round trips cost <= 10bp vs the cross), at most 3 names, largest dividend yield first, funded ONLY from settled
Roth cash (BIL/SGOV are never sold; GFV-safe) and at most 50% of Roth equity. Before placing buys it writes
state/pref-ex-reserved.json so the Roth night leg (executor, 15:40) does not spend the same dollars. `dry` does everything
but submit. Never shorts: a sell is capped at the shares the account holds.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import re
import statistics
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
LOG_NAME = "pref-ex-live.jsonl"          # logs/: every action + scores (the REGISTRY reader)
STATE_NAME = "pref-ex-live.json"         # state/: open holdings bought yesterday
RESERVED_NAME = "pref-ex-reserved.json"  # state/: {"date", "usd"} read by the executor's Roth night leg
EVENTS_NAME = "pref-ex.jsonl"            # state/: the PREF-EX shadow's event rows (sym, ex, div, cls, status)
ET = ZoneInfo("America/New_York")
CUTOFF = dt.time(15, 43)                 # Schwab MOC cutoff 15:45
PART = 0.05                              # of the trailing median closing-cross $
PART_UP = 0.10                           # after the NEED-trip cost gate passes (user OK 2026-10-18)
STEP_MAX_RT_BP = 10.0                    # measured buy + sell cost vs the cross that allows PART_UP (the research model's RT)
LOOKBACK = 10                            # sessions for that median
MAX_NAMES = 3
MAX_EQUITY_FRAC = 0.50
CLASSES = ("pref", "etd")
NEED = 30                                # live round trips before the cost readout counts


def _jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def schwab_symbol(sym: str) -> str:
    """Alpaca BAC.PRP -> Schwab BAC/PRP (quotes and, with the cusip the adapter adds, orders). Others unchanged."""
    m = re.fullmatch(r"([A-Z]+)\.PR([A-Z]?)", sym)
    return f"{m.group(1)}/PR{m.group(2)}" if m else sym


def position_symbol(schwab: str) -> str:
    """Schwab's positions endpoint lists a preferred as BAC-P / PSEC-A, not the BAC/PRP order symbol
    (seen 2026-10-21: the first live sell was skipped as "account holds 0" while 10 PSEC-A sat in the
    account). Baby bonds and commons keep their symbol."""
    m = re.fullmatch(r"([A-Z]+)/PR([A-Z]?)", schwab)
    return f"{m.group(1)}-{m.group(2)}" if m else schwab


def held_qty(held: dict, schwab: str) -> float:
    """Shares the account holds under the order symbol or Schwab's position form of it."""
    for k in (schwab, position_symbol(schwab)):
        q = float(getattr(held.get(k), "qty", 0.0) or 0.0)
        if q:
            return q
    return 0.0


def next_session(d: dt.date) -> dt.date:
    from .cpc_ledger import next_session as ns
    return ns(d + dt.timedelta(days=1))


def is_session(d: dt.date) -> bool:
    from .cpc_ledger import is_session as s
    return s(d)


def candidates(rows: list[dict], today: dt.date) -> list[dict]:
    """Shadow event rows whose ex-date is the next session: buy at today's close."""
    ex = next_session(today).isoformat()
    out = {}
    for r in rows:
        if r.get("ex") == ex and r.get("cls") in CLASSES and r.get("status", "upcoming") == "upcoming" and r.get("div"):
            out[r["sym"]] = r
    return list(out.values())


def auction_usd(sym: str, today: dt.date, crosses_fn, H: dict | None) -> float:
    """Median closing-cross $ (px x size) over the last LOOKBACK sessions; 0 if unknown."""
    start = (today - dt.timedelta(days=LOOKBACK * 2)).isoformat()
    end = (today - dt.timedelta(days=1)).isoformat()
    try:
        X = crosses_fn([sym], start, end, H).get(sym, {})
    except Exception:  # noqa: BLE001
        return 0.0
    usd = [x[2] * x[3] for x in X.values() if x and x[2] and x[3]]
    usd = sorted(usd)[-LOOKBACK:]
    return float(statistics.median(usd)) if usd else 0.0


def screen_reason(r: dict, px: float | None, auction_usd: float) -> str | None:
    """The shadow's eligibility screen (pref_ex_shadow: price $10-60, yield 0.2-4%, 20-session median cross >= $1,400),
    applied before sizing so live buys the same set the research judged. None = eligible."""
    from .pref_ex_shadow import MAX_PX, MAX_YLD, MIN_CROSS, MIN_PX, MIN_YLD
    if not px or px <= 0:
        return "no quote"
    if not MIN_PX <= px <= MAX_PX:
        return f"price ${px:.2f} outside ${MIN_PX:.0f}-{MAX_PX:.0f}"
    yld = float(r["div"]) / px
    if not MIN_YLD <= yld <= MAX_YLD:
        return f"yield {yld:.2%} outside {MIN_YLD:.1%}-{MAX_YLD:.0%}"
    if auction_usd < MIN_CROSS:
        return f"median cross ${auction_usd:,.0f} < ${MIN_CROSS:,.0f}"
    return None


def size(cands: list[dict], last: dict[str, float], auction: dict[str, float], settled: float, equity: float,
         part: float = PART) -> list[dict]:
    """Whole-share MOC buys: `part` of the name's median cross $, largest yield first, <= MAX_NAMES, total <= settled cash
    and <= MAX_EQUITY_FRAC x equity. Names failing `screen_reason` are skipped; zero-share names are skipped, never
    forced to 1 share."""
    budget = max(0.0, min(settled, MAX_EQUITY_FRAC * equity))
    order = sorted(cands, key=lambda r: -(float(r["div"]) / last.get(r["sym"], float("inf")) if last.get(r["sym"]) else 0.0))
    out, spent = [], 0.0
    for r in order:
        if len(out) >= MAX_NAMES:
            break
        px = last.get(r["sym"])
        if screen_reason(r, px, auction.get(r["sym"], 0.0)):
            continue
        qty = math.floor(part * auction.get(r["sym"], 0.0) / px)
        if qty < 1:
            continue
        usd = qty * px
        if spent + usd > budget:
            qty = math.floor((budget - spent) / px)       # fill the rest of the budget with a smaller lot
            if qty < 1:
                continue
            usd = qty * px
        out.append(dict(sym=r["sym"], schwab=schwab_symbol(r["sym"]), qty=int(qty), px=float(px), usd=round(usd, 2),
                        ex=r["ex"], div=float(r["div"]), cls=r.get("cls"), auction_usd=round(auction.get(r["sym"], 0.0))))
        spent += usd
    return out


def _quotes(ad, bsyms: list[str]) -> dict[str, float]:
    """Schwab last price per Schwab symbol."""
    if not bsyms:
        return {}
    j = ad.c.get_quotes(bsyms).json() or {}
    out = {}
    for b in bsyms:
        q = (j.get(b) or {}).get("quote") or {}
        px = q.get("lastPrice") or q.get("mark") or q.get("closePrice")
        if px:
            out[b] = float(px)
    return out


def _settled_cash(acct) -> float:
    return float(getattr(acct, "settled_cash", None) if getattr(acct, "settled_cash", None) is not None else acct.cash)


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
    """Score every live buy/sell from a past session that has no score row yet: fill vs the official closing cross."""
    done = {r.get("order_id") for r in rows if r.get("cmd") == "score"}
    n = 0
    for r in rows:
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
        cross = X[2] if X else None
        log_row(dict(cmd="score", sym=r["sym"], side=r["cmd"], order_id=r["order_id"], day=day, qty=q, fill=fill,
                     close_cross=cross, close_cross_size=X[3] if X else None,
                     share=round(q / X[3], 4) if q and X and X[3] else None,     # our shares / the cross's shares
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
                buy_cost_bp=statistics.fmean(buys) if buys else None,       # + = paid above the cross
                sell_cost_bp=-statistics.fmean(sells) if sells else None)   # + = sold below the cross


def part(rows: list[dict]) -> float:
    """PART_UP once NEED live round trips are scored and the measured buy + sell cost vs the closing cross is <=
    STEP_MAX_RT_BP; PART otherwise. Re-read every run from all scored trips, so a cost drift above the bar steps back."""
    s = summary(rows)
    if s["round_trips"] < NEED or s["buy_cost_bp"] is None or s["sell_cost_bp"] is None:
        return PART
    return PART_UP if s["buy_cost_bp"] + s["sell_cost_bp"] <= STEP_MAX_RT_BP else PART


def line(rows: list[dict]) -> str:
    s = summary(rows)
    f = lambda v: "n/a" if v is None else f"{v:+.1f}bp"  # noqa: E731
    return (f"{s['round_trips']}/{NEED} live round trips; cost vs closing cross buy {f(s['buy_cost_bp'])} (n {s['buys']}), "
            f"sell {f(s['sell_cost_bp'])} (n {s['sells']}); {s['live_orders']} live / {s['dry_orders']} dry orders; "
            f"participation {part(rows):.0%}")


def run(mode: str, state_dir: Path, logs_dir: Path, log=print, today: dt.date | None = None, now: dt.datetime | None = None,
        ad=None, crosses_fn=None, quotes_fn=None, H: dict | None = None) -> dict:
    mode = (mode or "off").lower()
    if mode == "off":
        log("[pref-ex-live] off (daily.pref_ex_mode); nothing to do")
        return dict(mode=mode, skipped="off")
    if mode not in ("dry", "live"):
        raise ValueError(f"daily.pref_ex_mode must be off|dry|live, got {mode!r}")
    now = now or dt.datetime.now(ET)
    today = today or now.date()
    logp, statep, resp = logs_dir / LOG_NAME, state_dir / STATE_NAME, state_dir / RESERVED_NAME
    rows = _jsonl(logp)

    def log_row(r: dict) -> None:
        r = {"ts": dt.datetime.now(ET).isoformat(timespec="seconds"), "mode": mode, **r}
        logs_dir.mkdir(exist_ok=True)
        with logp.open("a") as f:
            f.write(json.dumps(r) + "\n")
        rows.append(r)
        log("[pref-ex-live] " + json.dumps({k: v for k, v in r.items() if k not in ("ts", "mode")}))

    if ad is None:
        from .brokers import make_adapter
        ad = make_adapter("roth")
    if crosses_fn is None or H is None:
        from .exdate_open_shadow import _headers
        from .pref_ex_shadow import crosses
        crosses_fn, H = crosses_fn or crosses, H or _headers()
    quotes_fn = quotes_fn or _quotes
    out = dict(mode=mode, scored=0, sold=[], bought=[], reserved=0.0)

    out["scored"] = score(rows, ad, today, crosses_fn, H, log_row)
    if not is_session(today):
        log(f"[pref-ex-live] {today} is not a session; scored {out['scored']}, no orders")
        return out
    if now.time() >= CUTOFF:
        log(f"[pref-ex-live] past the {CUTOFF:%H:%M} ET MOC cutoff; scored {out['scored']}, no orders")
        return out

    state = json.loads(statep.read_text()) if statep.exists() else {"open": {}}
    held = ad.positions()

    # --- sell leg: names bought for an ex-date that is today (or earlier, if a run was missed)
    for sym, h in list(state["open"].items()):
        if h.get("ex", "9999") > today.isoformat():
            continue
        have = held_qty(held, h["schwab"])
        qty = int(min(have, float(h["qty"])))
        if qty < 1:
            log_row(dict(cmd="sell-skip", sym=sym, schwab=h["schwab"], reason=f"account holds {have:g}"))
            state["open"].pop(sym)
            continue
        if mode == "live":
            oid = ad.submit(h["schwab"], "sell", "cls", f"pref-ex-live.sell.{sym}.{today}", qty=qty)
            log_row(dict(cmd="sell", sym=sym, schwab=h["schwab"], qty=qty, ex=h["ex"], order_id=oid))
        else:
            log_row(dict(cmd="sell", sym=sym, schwab=h["schwab"], qty=qty, ex=h["ex"], dry_run=True))
        out["sold"].append(sym)
        state["open"].pop(sym)

    # --- buy leg: tomorrow's ex-dates
    cands = [c for c in candidates(_jsonl(state_dir / EVENTS_NAME), today) if c["sym"] not in state["open"]]
    acct = ad.account()
    settled, equity = _settled_cash(acct), float(acct.equity)
    if not cands:
        log(f"[pref-ex-live] no {'/'.join(CLASSES)} ex-dates on {next_session(today)}; settled ${settled:,.0f}")
    else:
        bmap = {c["sym"]: schwab_symbol(c["sym"]) for c in cands}
        q = quotes_fn(ad, sorted(set(bmap.values())))
        last = {s: q[b] for s, b in bmap.items() if b in q}
        auction = {c["sym"]: auction_usd(c["sym"], today, crosses_fn, H) for c in cands}
        p = part(rows)
        orders = size(cands, last, auction, settled, equity, p)
        total = round(sum(o["usd"] for o in orders), 2)
        log(f"[pref-ex-live] {len(cands)} candidates for ex {next_session(today)}, {len(orders)} sized at {p:.0%} of the cross, "
            f"${total:,.0f} of settled ${settled:,.0f} (equity ${equity:,.0f})")
        for c in cands:
            if c["sym"] not in {o["sym"] for o in orders}:
                why = screen_reason(c, last.get(c["sym"]), auction.get(c["sym"], 0.0))
                log_row(dict(cmd="buy-skip", sym=c["sym"], ex=c["ex"], last=last.get(c["sym"]),
                             auction_usd=round(auction.get(c["sym"], 0.0)),
                             reason=why or f"0 shares at {p:.0%} of the cross or no budget"))
        if orders:
            resp.write_text(json.dumps({"date": today.isoformat(), "usd": total, "mode": mode}))
            out["reserved"] = total
        for o in orders:
            if mode == "live":
                oid = ad.submit(o["schwab"], "buy", "cls", f"pref-ex-live.buy.{o['sym']}.{today}", qty=o["qty"])
                log_row(dict(cmd="buy", **o, order_id=oid))
            else:
                log_row(dict(cmd="buy", **o, dry_run=True))
            state["open"][o["sym"]] = dict(schwab=o["schwab"], qty=o["qty"], ex=o["ex"], bought=today.isoformat(),
                                           px=o["px"], dry_run=mode != "live")
            out["bought"].append(o["sym"])
    state_dir.mkdir(exist_ok=True)
    statep.write_text(json.dumps(state, indent=1))
    return out


def main() -> int:
    from ..config import Config
    cfg = Config.load()
    run(getattr(cfg.daily, "pref_ex_mode", "off"), ROOT / "state", ROOT / "logs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
