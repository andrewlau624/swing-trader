"""CPC forward ledger (Study CPC, research/drafts/study_cpc.md + cpc_verification_2026-10-04.md). NEVER places orders.

Prospective tracking of the personal-scale contract-payoff opportunities (UMH plan optional cash, odd-lot tenders,
split-off odd-lot priority, reverse-split round-ups). PERSONAL-SCALE ECONOMICS (not scalable alpha).

state/cpc-ledger.jsonl is append-only. Line kinds (field "rec"):
  event       written once per event_id (version 1), only while now < deadline (prospective)
  change      a material change (deadline, maximum_position, estimated payoffs, eligibility) -> version + 1
  transition  a status change: from, to, outcome, realized_pnl, realized_costs, realized_return, completion_date, note
  alert       marker that the email for (event_id, version) went out
Current state = fold(rows). Earlier lines are never rewritten.

Run (`make cpc-ledger`): UMH generator + ingest of the watchers' own state files (their logic is untouched) + alerts.
Outcomes: `make cpc-done EVENT=<id> PNL=<$> COSTS=<$>` / `make cpc-failed EVENT=<id> STATUS=MISSED|INELIGIBLE|CANCELLED`.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import re
from pathlib import Path
from zoneinfo import ZoneInfo

LOG_NAME = "cpc-ledger.jsonl"
ET = ZoneInfo("America/New_York")
CLASSIFICATION = "PERSONAL-SCALE ECONOMICS (not scalable alpha)"
GATE_TEXT = ("Frozen gate: ~12 months forward, >= 2 independent events, >= +8pp annualized at $10k after costs and "
             "35% tax, not dependent on a single event.")
TAX = 0.35
BASE = 10_000.0

STATUSES = ("POTENTIAL", "KNOWN_AVAILABLE", "ACTION_REQUIRED", "COMPLETED", "MISSED", "INELIGIBLE", "CANCELLED", "UNKNOWN")
TERMINAL = {"COMPLETED", "MISSED", "INELIGIBLE", "CANCELLED"}
ALLOWED = {
    "POTENTIAL": {"KNOWN_AVAILABLE", "ACTION_REQUIRED", "MISSED", "INELIGIBLE", "CANCELLED", "UNKNOWN"},
    "UNKNOWN": {"POTENTIAL", "KNOWN_AVAILABLE", "ACTION_REQUIRED", "MISSED", "INELIGIBLE", "CANCELLED"},
    "KNOWN_AVAILABLE": {"ACTION_REQUIRED", "COMPLETED", "MISSED", "INELIGIBLE", "CANCELLED", "UNKNOWN"},
    "ACTION_REQUIRED": {"COMPLETED", "MISSED", "INELIGIBLE", "CANCELLED"},
    **{s: set() for s in TERMINAL},
}
EVENT_FIELDS = ("timestamp_known", "event_id", "family", "issuer", "security", "event_date", "deadline", "status",
                "eligibility", "maximum_position", "estimated_gross_payoff", "estimated_net_payoff", "required_action",
                "source", "source_date", "notes")
MATERIAL = ("deadline", "maximum_position", "estimated_gross_payoff", "estimated_net_payoff", "eligibility")

# ---- UMH plan terms: research/drafts/cpc_verification_2026-10-04.md (STEP 1)
UMH_AMOUNT, UMH_MIN, UMH_DISCOUNT = 1000.0, 500.0, 0.05
UMH_SOURCE = ("UMH DRIP prospectus supplement 424B3 acc. 0001493152-21-002238 (Q11, Q14, Q16); "
              "UMH 10-Q Q2 2026 acc. 0001493152-26-036177 (plan still issuing at ~5% discount)")
# User decision 2026-10-04: UMH is HOLD-ONLY and EXCLUDED from the clean CPC payoff. The plan may return cash from
# holders who short to earn the 5% differential and may cut the discount for immediate resale, so the discount cannot
# be locked in; what is left is a long UMH position. No monthly UMH events or alerts; never counted in the validation.
UMH_ENABLED = False
EXCLUDED_FAMILIES = {"UMH_OCP"}
PROMOTE_DAYS = 10          # an upcoming UMH event becomes ACTION_REQUIRED this many days before its deadline


# ------------------------------------------------------------------ calendar (offline; Alpaca's calendar needs network)
def _easter(y: int) -> dt.date:
    from dateutil.easter import easter
    return easter(y)


def _nth(y: int, m: int, wd: int, n: int) -> dt.date:
    d = dt.date(y, m, 1)
    d += dt.timedelta(days=(wd - d.weekday()) % 7 + 7 * (n - 1))
    return d


def _observed(d: dt.date) -> dt.date | None:
    if d.weekday() == 5:
        return d - dt.timedelta(days=1)
    if d.weekday() == 6:
        return d + dt.timedelta(days=1)
    return d


def nyse_holidays(y: int) -> set[dt.date]:
    last_mon_may = max(d for d in (dt.date(y, 5, k) for k in range(25, 32)) if d.weekday() == 0)
    h = {_nth(y, 1, 0, 3), _nth(y, 2, 0, 3), _easter(y) - dt.timedelta(days=2), last_mon_may,
         _nth(y, 9, 0, 1), _nth(y, 11, 3, 4)}
    for md in ((6, 19), (7, 4), (12, 25)):
        h.add(_observed(dt.date(y, *md)))
    ny = dt.date(y, 1, 1)
    if ny.weekday() != 5:                     # a Saturday Jan 1 is not observed on Dec 31
        h.add(_observed(ny))
    return {d for d in h if d}


def is_session(d: dt.date) -> bool:
    return d.weekday() < 5 and d not in nyse_holidays(d.year)


def next_session(d: dt.date) -> dt.date:
    while not is_session(d):
        d += dt.timedelta(days=1)
    return d


def is_business_day(d: dt.date) -> bool:
    """Agent (bank) business day: NYSE session and not Columbus / Veterans Day (conservative: earlier deadline)."""
    return is_session(d) and d != _nth(d.year, 10, 0, 2) and d != dt.date(d.year, 11, 11)


def prev_business_day(d: dt.date) -> dt.date:
    while not is_business_day(d):
        d -= dt.timedelta(days=1)
    return d


def close_et(d: dt.date) -> str:
    """16:00 ET on `d` (the regular-session close; used as the conservative end of a deadline day)."""
    return dt.datetime(d.year, d.month, d.day, 16, 0, tzinfo=ET).isoformat()


def _now(now=None) -> dt.datetime:
    n = now or dt.datetime.now(ET)
    return n if n.tzinfo else n.replace(tzinfo=ET)


# ------------------------------------------------------------------ ledger io, ids, fold
def slug(s: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "-", str(s).upper()).strip("-")


def event_id(family: str, issuer: str, event_date: str) -> str:
    return f"{slug(family)}:{slug(issuer)}:{event_date}"


def read(path: Path) -> list[dict]:
    out = []
    if Path(path).exists():
        for line in Path(path).read_text().splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def _append(path: Path, rec: dict) -> dict:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("a") as f:
        f.write(json.dumps(rec, sort_keys=False) + "\n")
    return rec


def fold(rows: list[dict]) -> dict[str, dict]:
    """event_id -> current state (event fields + status, version, realized fields, alerted versions, history)."""
    st: dict[str, dict] = {}
    for r in rows:
        eid = r.get("event_id")
        k = r.get("rec")
        if k == "event" and eid not in st:
            st[eid] = dict(r, version=1, alerted=set(), history=[], first_known=r["timestamp_known"])
        elif eid in st:
            s = st[eid]
            if k == "change":
                s.update(r["new"])
                s["version"] = r["version"]
                s["history"].append(r)
            elif k == "transition":
                s["status"] = r["to"]
                s["history"].append(r)
                if r["to"] in TERMINAL:
                    s.update({x: r.get(x) for x in ("outcome", "realized_pnl", "realized_costs", "realized_return",
                                                    "completion_date")})
                if r.get("material"):
                    s["version"] = r["version"]
            elif k == "alert":
                s["alerted"].add(r["version"])
    return st


class Refused(ValueError):
    pass


# ------------------------------------------------------------------ writes
def add_event(path: Path, ev: dict, now=None) -> tuple[str, dict]:
    """Write one event once. Returns ("new"|"duplicate"|"changed"|"unchanged", record). Refuses after the deadline.
    A second call with the same event_id and a different material field appends a change record instead."""
    n = _now(now)
    ev = dict(ev)
    bad = [k for k in ("family", "issuer", "security", "event_date", "status") if not ev.get(k)]
    if bad:
        raise Refused(f"missing {bad}")
    if ev["status"] not in STATUSES:
        raise Refused(f"bad status {ev['status']}")
    ev.setdefault("event_id", event_id(ev["family"], ev["issuer"], ev["event_date"]))
    dl = ev.get("deadline")
    if dl:
        if n >= dt.datetime.fromisoformat(dl):
            raise Refused(f"{ev['event_id']}: deadline {dl} has passed (now {n.isoformat()}); prospective events only")
    elif ev["status"] not in ("UNKNOWN", "POTENTIAL"):
        raise Refused(f"{ev['event_id']}: no deadline, so it cannot be shown to be prospective; use UNKNOWN or POTENTIAL")
    cur = fold(read(path)).get(ev["event_id"])
    if cur:
        new = {k: ev[k] for k in MATERIAL if k in ev and ev[k] != cur.get(k)}
        if not new:
            return "unchanged", cur
        if cur["status"] in TERMINAL:
            return "unchanged", cur
        rec = dict(rec="change", event_id=cur["event_id"], ts=n.isoformat(), version=cur["version"] + 1,
                   old={k: cur.get(k) for k in new}, new=new)
        return "changed", _append(path, rec)
    rec = {"rec": "event", **{k: ev.get(k) for k in EVENT_FIELDS}}
    rec["timestamp_known"] = n.isoformat()
    return "new", _append(path, rec)


def transition(path: Path, eid: str, to: str, now=None, outcome=None, realized_pnl=None, realized_costs=None,
               realized_return=None, completion_date=None, note="", material=False) -> dict:
    cur = fold(read(path)).get(eid)
    if not cur:
        raise Refused(f"unknown event {eid}")
    if to not in STATUSES:
        raise Refused(f"bad status {to}")
    if to not in ALLOWED[cur["status"]]:
        raise Refused(f"{eid}: {cur['status']} -> {to} is not allowed")
    n = _now(now)
    rec = dict(rec="transition", event_id=eid, ts=n.isoformat(), **{"from": cur["status"], "to": to}, outcome=outcome,
               realized_pnl=realized_pnl, realized_costs=realized_costs, realized_return=realized_return,
               completion_date=completion_date or (str(n.date()) if to in TERMINAL else None), note=note,
               material=bool(material))
    if material:
        rec["version"] = cur["version"] + 1
    return _append(path, rec)


def done(path: Path, eid: str, pnl: float, costs: float, note: str = "", now=None, base: float = BASE) -> dict:
    net = pnl - costs
    return transition(path, eid, "COMPLETED", now, outcome="done", realized_pnl=pnl, realized_costs=costs,
                      realized_return=net / base, note=note)


def failed(path: Path, eid: str, status: str, note: str = "", now=None) -> dict:
    if status not in ("MISSED", "INELIGIBLE", "CANCELLED"):
        raise Refused("STATUS must be MISSED, INELIGIBLE or CANCELLED")
    return transition(path, eid, status, now, outcome=status.lower(), realized_pnl=0.0, realized_costs=0.0,
                      realized_return=0.0, note=note)


def sweep(path: Path, now=None) -> list[str]:
    """Events nobody acted on (POTENTIAL / KNOWN_AVAILABLE / UNKNOWN) whose deadline passed -> MISSED.
    ACTION_REQUIRED events stay open (the payoff comes after the action deadline); the status report flags them."""
    n, out = _now(now), []
    for eid, s in fold(read(path)).items():
        if s["status"] in ("POTENTIAL", "KNOWN_AVAILABLE", "UNKNOWN") and s.get("deadline") \
                and n >= dt.datetime.fromisoformat(s["deadline"]):
            transition(path, eid, "MISSED", n, outcome="missed", realized_pnl=0.0, realized_costs=0.0,
                       realized_return=0.0, note="deadline passed with no action recorded")
            out.append(eid)
    return out


def promote(path: Path, now=None) -> list[str]:
    """UMH-style events within PROMOTE_DAYS of the deadline that are still KNOWN_AVAILABLE -> ACTION_REQUIRED (material)."""
    n, out = _now(now), []
    for eid, s in fold(read(path)).items():
        if s["status"] == "KNOWN_AVAILABLE" and s.get("deadline"):
            left = (dt.datetime.fromisoformat(s["deadline"]) - n).days
            if 0 <= left <= PROMOTE_DAYS:
                transition(path, eid, "ACTION_REQUIRED", n, note=f"{left}d to deadline", material=True)
                out.append(eid)
    return out


# ------------------------------------------------------------------ UMH monthly generator
def umh_investment_date(y: int, m: int) -> dt.date:
    """Dividend payment date (Mar/Jun/Sep/Dec) else the 15th; UMH pays dividends on the 15th. Next NYSE session."""
    return next_session(dt.date(y, m, 15))


def umh_deadline(inv: dt.date) -> dt.date:
    """Agent must RECEIVE the payment by the 10th of the month (preceding business day if not a business day)."""
    return prev_business_day(dt.date(inv.year, inv.month, 10))


def umh_event(y: int, m: int, now=None) -> dict:
    inv = umh_investment_date(y, m)
    dl = umh_deadline(inv)
    gross = UMH_AMOUNT * UMH_DISCOUNT
    net = gross * (1 - TAX)
    mail_by = prev_business_day(dl - dt.timedelta(days=5))
    return dict(
        family="UMH_OCP", issuer="UMH Properties", security="UMH", event_date=str(inv),
        deadline=close_et(dl), status="KNOWN_AVAILABLE",
        eligibility=("Must own UMH. Street-name (Schwab) holders send the plan Authorization Card certifying UMH "
                     "ownership with the first check (prospectus Q4). Min $500, max $1,000 per month per owner."),
        maximum_position=UMH_AMOUNT,
        estimated_gross_payoff=round(gross, 2), estimated_net_payoff=round(net, 2),
        required_action=(f"Mail a check or money order (payable to American Stock Transfer & Trust Company, now "
                         f"Equiniti; $500-$1,000) so the Agent RECEIVES it by {dl:%a %Y-%m-%d} (VERIFIED rule: by the "
                         f"10th; mail by about {mail_by:%Y-%m-%d}). Online/ACH for this plan is UNKNOWN. Investment "
                         f"date {inv:%Y-%m-%d}; price = 95% of the higher of the 4-day average and the investment-day "
                         f"(high+low)/2. Then sell or transfer the plan shares (process UNKNOWN), then run "
                         f"`make cpc-done EVENT=<id> PNL=<$> COSTS=<$>`."),
        source=UMH_SOURCE, source_date="2026-10-04",
        notes=("ECONOMIC DISCOUNT ~5% x $1,000 = ~$50 gross, NOT guaranteed profit. Net ~$32.50 after 35% tax, BEFORE "
               "sale/transfer cost (UNKNOWN; a $100 Medallion-waiver fee would exceed the gross). Deadline VERIFIED "
               "from the 2021 prospectus (not reconfirmed with the agent). HEDGE (taxable only; a Roth cannot short): "
               "short the same number of UMH shares at Schwab on the investment date, cover with the transferred plan "
               "shares. WARNING: the plan says it may return optional cash from holders who short on the NYSE to "
               "earn the 5% differential, and may cut the discount for immediate resale; an unhedged position carries "
               "~1.6%/day price risk (~5% sd over two weeks, as large as the discount) while the shares sit at the "
               "agent (transfer/sale lag UNKNOWN)."),
    )


def umh_events(now=None, horizon: int = 2) -> list[dict]:
    """The next `horizon` UMH events whose deadline has not passed."""
    n = _now(now)
    out, y, m = [], n.year, n.month
    for _ in range(14):
        ev = umh_event(y, m, n)
        if n < dt.datetime.fromisoformat(ev["deadline"]):
            out.append(ev)
        if len(out) >= horizon:
            break
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


# ------------------------------------------------------------------ ingest of the watchers' state files (read only)
def _jl(p: Path) -> list[dict]:
    return read(p)


def _usd(x) -> float | None:
    return None if x is None or (isinstance(x, float) and not math.isfinite(x)) else round(float(x), 2)


def from_tender(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        if not r.get("alert") or not r.get("ticker"):
            continue
        floor, close = r.get("floor"), r.get("last_close")
        gross = _usd((floor - close) * 99) if floor and close else None
        exp = r.get("expires")
        out.append(dict(
            family="ODD_LOT_TENDER", issuer=r.get("name") or r["ticker"], security=r["ticker"], event_date=r["date"],
            deadline=close_et(dt.date.fromisoformat(exp)) if exp else None,
            status="ACTION_REQUIRED" if exp else "UNKNOWN",
            eligibility="Fewer than 100 shares IN TOTAL across all accounts; odd-lot priority (tender_watch alert).",
            maximum_position=99, estimated_gross_payoff=gross,
            estimated_net_payoff=_usd(gross * (1 - TAX)) if gross is not None else None,
            required_action=f"make tender-buy ID={r['ticker']}-{r['date']}, then tender at Schwab one business day "
                            f"before expiry ({exp or 'expiry not parsed: read the offer'}).",
            source=f"SEC {r.get('path', '')}", source_date=r["date"],
            notes=f"tender_watch row: floor {floor}, last_close {close}, floor_gain {r.get('floor_gain')}. "
                  "Guaranteed floor gain is an estimate until the offer closes; tender deadline at Schwab is earlier."))
    return out


def from_splitoff(rows: list[dict]) -> list[dict]:
    offers = [r for r in rows if "parent" in r and "expires" in r and "entry" not in r]
    entries = {r["parent"]: r for r in rows if "entry" in r}
    out = []
    for o in offers:
        e = entries.get(o["parent"])
        pos = round(99 * e["parent_px"], 2) if e and e.get("parent_px") else None
        gross = _usd(pos * e["gain"]) if pos and e.get("gain") is not None else None
        out.append(dict(
            family="SPLIT_OFF", issuer=o["parent"], security=f"{o['parent']}->{o['recv']}", event_date=o["date"],
            deadline=close_et(dt.date.fromisoformat(o["expires"])),
            status="ACTION_REQUIRED" if e and e.get("alert") else "KNOWN_AVAILABLE",
            eligibility=f"Odd lot (< 100 {o['parent']} shares) accepted in full; odd_lot={o.get('odd_lot')}.",
            maximum_position=pos, estimated_gross_payoff=gross,
            estimated_net_payoff=_usd(gross * (1 - TAX)) if gross is not None else None,
            required_action=f"make splitoff-buy PARENT={o['parent']} after the entry alert; tender into the exchange "
                            f"offer before {o['expires']}.",
            source=o.get("url") or "splitoff-watch.jsonl", source_date=o["date"],
            notes=f"splitoff_watch: ${o['per100']} of {o['recv']} per $100 of {o['parent']}, upper limit {o['cap']}. "
                  + (f"Entry row {e['entry']}: gain {e.get('gain')}." if e else "No entry row yet.")))
    return out


def from_roundup(rows: list[dict], orders: dict | None = None) -> list[dict]:
    out = []
    for r in rows:
        if not r.get("alert") or not r.get("buy_by"):
            continue
        close, ratio = r.get("last_close"), r.get("ratio")
        gross = _usd(close * (ratio - 1)) if close and ratio else None
        od = {k: v for k, v in (orders or {}).items() if k.startswith(r["ticker"])}
        out.append(dict(
            family="REVERSE_SPLIT_ROUNDUP", issuer=r["ticker"], security=r["ticker"], event_date=r["trade_date"],
            deadline=close_et(dt.date.fromisoformat(r["buy_by"])), status="ACTION_REQUIRED",
            eligibility="Company states fractions are rounded UP; whether Schwab passes it to a 1-share holder is "
                        "what the first fills settle.",
            maximum_position=1, estimated_gross_payoff=gross,
            estimated_net_payoff=_usd(gross * (1 - TAX)) if gross is not None else None,
            required_action=f"Hold 1 share per account at the close of {r['buy_by']} (roundup_orders buys it only if "
                            "ROUNDUP_AUTO=1); keep it through the split.",
            source=r.get("url", ""), source_date=r.get("filed") or r["date"],
            notes=f"roundup_watch: 1-for-{ratio:g}, last_close {close}. {r.get('sentence', '')[:160]} "
                  + (f"roundup-orders: {json.dumps(od)[:200]}" if od else "")))
    return out


def ingest(state_dir: Path) -> list[dict]:
    s = Path(state_dir)
    orders = {}
    p = s / "roundup-orders.json"
    if p.exists():
        try:
            orders = json.loads(p.read_text())
        except ValueError:
            pass
    return (from_tender(_jl(s / "tender-watch.jsonl")) + from_splitoff(_jl(s / "splitoff-watch.jsonl"))
            + from_roundup(_jl(s / "roundup-watch.jsonl"), orders))


# ------------------------------------------------------------------ alerts
def alert_email(s: dict, kind: str) -> tuple[str, str]:
    from ..live import mail as M
    hedge = ("Taxable: short the same number of UMH shares at Schwab on the investment date and cover with the "
             "transferred plan shares (Roth cannot hedge). The plan reserves the right to return cash from short "
             "sellers.") if s["family"] == "UMH_OCP" else "None required; do not short (odd-lot / round-up logic)."
    dl = s.get("deadline") or "UNKNOWN"
    what = {"new": "New opportunity", "change": "Material change"}[kind]
    facts = [("What happened", f"{what}: {s['family']} {s['security']} ({s['event_date']})"),
             ("Why it qualifies", s["eligibility"]),
             ("Deadline", dl[:16].replace("T", " ") + " ET" if s.get("deadline") else dl),
             ("Maximum position", f"${s['maximum_position']:,.0f}" if s["family"] == "UMH_OCP" and s.get("maximum_position")
              else str(s.get("maximum_position"))),
             ("Estimated payoff", f"gross {s.get('estimated_gross_payoff')} / net {s.get('estimated_net_payoff')} "
                                  "(estimate of the economic discount, NOT guaranteed profit)"),
             ("Required action", s["required_action"]), ("Hedge", hedge),
             ("Source", f"{s['source']} ({s['source_date']})"), ("Status", s["status"])]
    blocks = [M.facts(facts), M.fine(s.get("notes") or ""), M.fine(CLASSIFICATION + ". Ledger only: no order is placed.")]
    subj = f"CPC {'update' if kind == 'change' else 'event'}: {s['security']} {s['event_date']} [{s['status']}]"
    return subj, M.page("CPC forward ledger", f"{s['family']} {s['security']}", f"{s['event_id']} v{s['version']}", blocks)


def send_alerts(path: Path, state_dir: Path, email: bool = True, now=None, log=print) -> list[tuple[str, int]]:
    """One email per (event_id, version) not yet marked alerted. Terminal events are not alerted."""
    n = _now(now)
    sent = []
    notifier = None
    for eid, s in fold(read(path)).items():
        if s["status"] in TERMINAL or s["version"] in s["alerted"]:
            continue
        kind = "new" if s["version"] == 1 else "change"
        subj, html = alert_email(s, kind)
        log(f"[cpc] ALERT {eid} v{s['version']} ({kind}): {subj}")
        if email:
            if notifier is None:
                from ..live.notify import Notifier
                notifier = Notifier(Path(state_dir))
            notifier.mail(subj, html, dedupe_key=f"cpc-{eid}-v{s['version']}")
        _append(path, dict(rec="alert", event_id=eid, version=s["version"], ts=n.isoformat(), kind=kind,
                           emailed=bool(email)))
        sent.append((eid, s["version"]))
    return sent


# ------------------------------------------------------------------ validation report
def _after_tax(net: float) -> float:
    return net * (1 - TAX) if net > 0 else net


def report(rows: list[dict], now=None, book_monthly: dict | None = None) -> dict:
    n = _now(now)
    st = fold(rows)
    ev = [e for e in st.values() if e["family"] not in EXCLUDED_FAMILIES]
    comp = [e for e in ev if e["status"] == "COMPLETED"]
    nets = {e["event_id"]: (e.get("realized_pnl") or 0.0) - (e.get("realized_costs") or 0.0) for e in comp}
    nets_at = {k: _after_tax(v) for k, v in nets.items()}
    first = min((dt.datetime.fromisoformat(e["first_known"]) for e in ev), default=None)
    days = (n - first).days if first else 0
    indep = len({(e["family"], e["issuer"]) for e in comp})
    total = sum(nets_at.values())
    ann = lambda x: (x / BASE) * 365.0 / days if days > 0 else None      # noqa: E731
    enough = indep >= 2 and days >= 91
    best_id = max(nets_at, key=nets_at.get) if nets_at else None
    best = nets_at[best_id] if best_id else 0.0
    count = lambda s: sum(1 for e in ev if e["status"] == s)             # noqa: E731
    actionable = len(comp) + count("MISSED") + count("INELIGIBLE")
    decided = actionable + count("CANCELLED")
    fam = {}
    for e in ev:
        f = fam.setdefault(e["family"], dict(events=0, completed=0, pnl_after_tax=0.0))
        f["events"] += 1
        if e["event_id"] in nets_at:
            f["completed"] += 1
            f["pnl_after_tax"] = round(f["pnl_after_tax"] + nets_at[e["event_id"]], 2)
    est = sum((e.get("estimated_net_payoff") or 0.0) for e in comp)
    corr = None
    if book_monthly and len(book_monthly) >= 12:
        by_m: dict = {}
        for e in comp:
            k = (e.get("completion_date") or "")[:7]
            by_m[k] = by_m.get(k, 0.0) + nets_at[e["event_id"]] / BASE
        ks = sorted(set(by_m) & set(book_monthly))
        if len(ks) >= 12:
            import numpy as np
            corr = float(np.corrcoef([by_m[k] for k in ks], [book_monthly[k] for k in ks])[0, 1])
    open_late = [e["event_id"] for e in ev if e["status"] == "ACTION_REQUIRED" and e.get("deadline")
                 and n >= dt.datetime.fromisoformat(e["deadline"])]
    return dict(
        classification=CLASSIFICATION, gate=GATE_TEXT, events=len(ev), completed=len(comp), independent_completed=indep,
        days_elapsed=days, total_pnl_net_of_costs=round(sum(nets.values()), 2), total_pnl_after_tax=round(total, 2),
        cumulative_return_at_10k=round(total / BASE, 5), annualized_at_10k=round(ann(total), 4) if enough else None,
        annualized_note="too early" if not enough else "ok",
        by_family=fam, best_event=best_id, best_event_share=round(best / total, 3) if total > 0 and best_id else None,
        annualized_ex_best=round(ann(total - best), 4) if enough and best_id else None,
        operational_failure_rate=round((count("MISSED") + count("INELIGIBLE")) / actionable, 3) if actionable else None,
        missed_opportunity_rate=round(count("MISSED") / decided, 3) if decided else None,
        estimated_vs_realized=(round(est, 2), round(total, 2)),
        open_past_deadline=open_late, correlation_with_book=corr,
        correlation_note="n/a" if corr is None else f"{corr:+.2f}" if corr == corr else "n/a",
        missed=count("MISSED"))


def format_report(r: dict) -> str:
    pct = lambda x: "too early" if x is None else f"{x:+.1%}"             # noqa: E731
    lines = [r["classification"], r["gate"],
             f"events {r['events']}  completed {r['completed']}  independent {r['independent_completed']}  "
             f"elapsed {r['days_elapsed']}d",
             f"P&L net of costs ${r['total_pnl_net_of_costs']:,.2f}, after 35% tax ${r['total_pnl_after_tax']:,.2f}  "
             f"(cumulative {r['cumulative_return_at_10k']:+.2%} at $10k)",
             f"annualized at $10k: {pct(r['annualized_at_10k'])}   ex-best-event: {pct(r['annualized_ex_best'])}   "
             f"best-event share {r['best_event_share']}",
             f"estimated vs realized (after tax): ${r['estimated_vs_realized'][0]:,.2f} est vs ${r['estimated_vs_realized'][1]:,.2f}",
             f"operational failure rate {r['operational_failure_rate']}  missed-opportunity rate {r['missed_opportunity_rate']}",
             f"correlation with the live book: {r['correlation_note']} (needs >= 12 monthly observations)"]
    lines += [f"  {k}: {v['events']} events, {v['completed']} completed, ${v['pnl_after_tax']:,.2f}"
              if "pnl_after_tax" in v else "" for k, v in r["by_family"].items()]
    if r["open_past_deadline"]:
        lines.append("ACTION_REQUIRED past deadline, close with cpc-done / cpc-failed: " + ", ".join(r["open_past_deadline"]))
    return "\n".join(x for x in lines if x)


def digest_read(state: Path, logs: Path) -> dict:
    """Weekly-digest reader (testing.REGISTRY)."""
    rows = read(Path(state) / LOG_NAME)
    if not rows:
        return dict(n=0, week=0, line="no events yet (make cpc-ledger)")
    n = _now()
    wk = str(n.date() - dt.timedelta(days=7))
    st = fold(rows)
    r = report(rows, n)
    new_wk = [e for e in st.values() if e["first_known"][:10] >= wk]
    upcoming = sorted((e for e in st.values() if e["status"] in ("KNOWN_AVAILABLE", "ACTION_REQUIRED") and e.get("deadline")),
                      key=lambda e: e["deadline"])[:3]
    up = ", ".join(f"{e['security']} {e['deadline'][5:10]}" for e in upcoming) or "none"
    ann = "too early" if r["annualized_at_10k"] is None else f"{r['annualized_at_10k']:+.1%}/yr at $10k"
    line = (f"{len(new_wk)} new this week; upcoming deadlines {up}; completed {r['completed']}, missed {r['missed']}; "
            f"realized ${r['total_pnl_after_tax']:+,.0f} after tax vs est ${r['estimated_vs_realized'][0]:,.0f}; "
            f"cumulative {r['cumulative_return_at_10k']:+.2%} at $10k; {r['independent_completed']} independent; "
            f"annualized {ann} (gate: 12m, >=2 indep, >=+8pp). {CLASSIFICATION}")
    return dict(n=r["completed"], week=len(new_wk), line=line)


# ------------------------------------------------------------------ run
def run(state_dir: Path, now=None, email: bool = True, log=print) -> dict:
    path = Path(state_dir) / LOG_NAME
    n = _now(now)
    res = dict(new=[], changed=[], refused=[])
    cands = (umh_events(n) if UMH_ENABLED else []) + ingest(state_dir)
    for ev in cands:
        try:
            kind, rec = add_event(path, ev, n)
        except Refused as exc:
            res["refused"].append(str(exc))
            log(f"[cpc] refused: {exc}")
            continue
        if kind in ("new", "changed"):
            res["new" if kind == "new" else "changed"].append(rec["event_id"])
    res["swept"] = sweep(path, n)
    res["promoted"] = promote(path, n)
    res["alerts"] = send_alerts(path, state_dir, email, n, log)
    log(f"[cpc] {len(res['new'])} new, {len(res['changed'])} changed, {len(res['refused'])} refused, "
        f"{len(res['promoted'])} promoted, {len(res['swept'])} missed")
    return res


def _cli(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", default="run", choices=("run", "dry", "done", "failed", "status"))
    ap.add_argument("--event")
    ap.add_argument("--pnl", type=float)
    ap.add_argument("--costs", type=float, default=0.0)
    ap.add_argument("--status")
    ap.add_argument("--note", default="")
    ap.add_argument("--state", default=str(Path(__file__).resolve().parents[2] / "state"))
    a = ap.parse_args(argv)
    path = Path(a.state) / LOG_NAME
    try:
        if a.cmd == "run":
            run(Path(a.state))
        elif a.cmd == "dry":                     # no write, no email: show what a run would do
            import tempfile
            with tempfile.TemporaryDirectory() as td:
                (Path(td) / LOG_NAME).write_text(path.read_text() if path.exists() else "")
                for f in Path(a.state).glob("*watch*.jsonl"):
                    (Path(td) / f.name).write_text(f.read_text())
                ro = Path(a.state) / "roundup-orders.json"
                if ro.exists():
                    (Path(td) / ro.name).write_text(ro.read_text())
                run(Path(td), email=False)
                for eid, s in fold(read(Path(td) / LOG_NAME)).items():
                    print(f"  {eid} [{s['status']}] deadline {s.get('deadline')} max {s.get('maximum_position')} "
                          f"gross {s.get('estimated_gross_payoff')} net {s.get('estimated_net_payoff')}")
        elif a.cmd == "done":
            if not a.event or a.pnl is None:
                raise Refused("usage: make cpc-done EVENT=<id> PNL=<$> COSTS=<$> [NOTE=...]")
            done(path, a.event, a.pnl, a.costs, a.note)
            print(f"[cpc] {a.event} COMPLETED pnl {a.pnl} costs {a.costs}")
        elif a.cmd == "failed":
            if not a.event or not a.status:
                raise Refused("usage: make cpc-failed EVENT=<id> STATUS=MISSED|INELIGIBLE|CANCELLED [NOTE=...]")
            failed(path, a.event, a.status, a.note)
            print(f"[cpc] {a.event} {a.status}")
        else:
            print(format_report(report(read(path))))
    except Refused as exc:
        print(f"[cpc] {exc}")
        return 2
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_cli(sys.argv[1:]))
