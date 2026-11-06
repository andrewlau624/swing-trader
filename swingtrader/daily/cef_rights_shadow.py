"""CEF-RIGHTS-FWD forward shadow (round1_prose.md, N 1085) + CEF-RV rights-window hygiene watch (N 1086): logs, never orders.

Rule (frozen at registration 2026-11-06, amended the same day before any forward event): a seasoned closed-end fund in the
CEF-RV list announces a rights offering on EDGAR: a 497AD press release or a final prospectus (497 / 424B*), classified and dated
by research/sim/cef_rights_fetch.classify (the N 1084 code); the final prospectus's expiry replaces a 497AD's when it arrives.
E = the first regular session on or after the expiry date. Would-be trade: SHORT the official close cross of session E-10, COVER the official close cross of E+25
(35 sessions), taxable margin account only. Return = -(fund total return - EW CEF universe return, same sessions); net = that -
2 x 20bp - borrow (logged annual rate x 35/252). The pricing-window excess E-10 -> E (the mechanism) is logged beside it.

Borrow: the binding unknown. Each run up to the entry session snapshots, read-only, Alpaca's asset `shortable` /
`easy_to_borrow` (the ssr_lift_shadow pattern) and, when a Schwab client is available, the quote's `reference` isShortable /
isHardToBorrow / htbRate. brokers.py exposes nothing else about borrow; a missing field is logged as None (unknown).

Gate (n >= 15 gate events = scored, single ticker, first seen on/before entry): mean net > +200bp, median net > 0, borrow
available (shortable at the last snapshot on/before entry) on >= 70% -> PASS (propose; user decision); mean net <= 0 -> KILL.

Regular hours: sessions come from the exchange calendar (brokers.regular_sessions) checked by signals.regular_clock and labelled by
marketdata.trade_date; prices are the official auction prints (pref_ex_shadow.crosses), never a daily bar.

Files: state/cef-rights.jsonl (one row per offering), state/cef-rights-rv.jsonl (hygiene rows, rewritten each run),
state/cef-rights-cache/ (SEC downloads: untrusted, parsed as text only; submissions refreshed daily, documents kept).
"""
from __future__ import annotations

import datetime as dt
import json
import statistics as st
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

LOG_NAME = "cef-rights.jsonl"
HYGIENE_NAME = "cef-rights-rv.jsonl"
CACHE = "cef-rights-cache"
SIDE = 0.0020
PRE, POST, PW_POST = 10, 25, 5          # entry E-10, exit E+25; pricing window for the hygiene watch [E-10, E+5]
LOOKBACK_DAYS = 120                     # prospectuses filed in the last 120 days (expiry <= filed + 120 in classify)
SEASONED_DAYS = 365
DEDUPE_DAYS = 45
NEED = 15
FINAL = 30
GATE_MEAN_BP = 200.0
GATE_BORROW = 0.70
HYG_NEED = 10
ANNOUNCE = "497AD"                      # fund press release under Rule 482: the earliest EDGAR trace of most offerings
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUB_URL = "https://data.sec.gov/submissions/CIK{:010d}.json"
DOC_URL = "https://www.sec.gov/Archives/edgar/data/{}/{}/{}"


def _read(path: Path) -> list[dict]:
    from .ovn_mom_shadow import _read as r
    return r(path)


# ------------------------------------------------------------------ calendar (pure)

def session_days(sessions: list) -> list[str]:
    """[(open, close)] tz-aware ET regular sessions -> trade dates. Raises ValueError unless every session is 09:30 -> 16:00/13:00."""
    from .marketdata import trade_date
    from .signals import regular_clock
    ss = sorted(sessions)
    if not ss:
        return []
    regular_clock(ss[0][0] - dt.timedelta(minutes=1), ss)
    return [str(trade_date(pd.Timestamp(c)).date()) for _, c in ss]


def window(days: list[str], expiry: str) -> dict | None:
    """E = first session >= expiry; entry E-10, exit E+25, pricing window [E-10, E+5]. None if the calendar does not cover it."""
    i = next((k for k, d in enumerate(days) if d >= expiry), None)
    if i is None or i - PRE < 0 or i + POST >= len(days):
        return None
    return dict(E=days[i], entry=days[i - PRE], exit=days[i + POST], pw_lo=days[i - PRE], pw_hi=days[i + PW_POST])


# ------------------------------------------------------------------ scanner (SEC, rate-limited, cached)

def _fetch():
    from research.sim.cef_rights_fetch import get        # generic SEC User-Agent, ~0.12s sleep, retries, cached by path
    return get


def cik_map(cache: Path, syms: list[str], today: dt.date, fetch=None) -> dict[str, int]:
    fetch = fetch or _fetch()
    p = cache / "company_tickers.json"
    if p.exists() and (today - dt.date.fromtimestamp(p.stat().st_mtime)).days > 7:
        p.unlink()
    b = fetch(TICKERS_URL, p)
    j = json.loads(b) if b else {}
    m = {v["ticker"].upper(): int(v["cik_str"]) for v in j.values()}
    return {s: m[s] for s in syms if s in m}


def scan_cik(cik: int, cache: Path, today: dt.date, fetch=None) -> list[dict]:
    """Rights-offering prospectuses of one registrant filed in the last LOOKBACK_DAYS (the N 1084 classifier)."""
    from research.sim.cef_rights_fetch import FORMS, classify, clean
    fetch = fetch or _fetch()
    b = fetch(SUB_URL.format(cik), cache / f"sub_{cik}_{today}.json")
    if not b:
        return []
    r = json.loads(b)["filings"]["recent"]
    dates = r.get("filingDate") or []
    if not dates:
        return []
    oldest, full = min(dates), len(dates) >= 1000
    out = []
    for acc, fd, form, doc in zip(r["accessionNumber"], dates, r["form"], r["primaryDocument"]):
        if form not in FORMS | {ANNOUNCE} or fd < str(today - dt.timedelta(days=LOOKBACK_DAYS)):
            continue
        if not full and oldest > str(dt.date.fromisoformat(fd) - dt.timedelta(days=SEASONED_DAYS)):
            continue                                       # not seasoned: an IPO prospectus
        a = acc.replace("-", "")
        c = classify(clean(fetch(DOC_URL.format(cik, a, doc), cache / f"doc_{cik}_{a}.bin", 120_000)), pd.Timestamp(fd))
        if not c or c["preferred"] or pd.isna(c["expiry"]):
            continue
        out.append(dict(cik=cik, filed=fd, form=form, acc=acc, expiry=str(c["expiry"].date()),
                        transferable=bool(c["transferable"]), final=form != ANNOUNCE))
    return out


def merge(events: list[dict], found: list[dict], cik_syms: dict[int, list[str]], today: dt.date) -> list[dict]:
    """One event per (CIK, expiry within DEDUPE_DAYS). `announced` = the earliest matching filing (a 497AD press release is
    usually 2-3 weeks before the final prospectus). The expiry is the earliest FINAL prospectus's (497/424B*); a 497AD expiry
    is provisional until one arrives. Other parsed dates go to alt_expiries."""
    for f in sorted(found, key=lambda x: (x["filed"], x["acc"])):
        ex = dt.date.fromisoformat(f["expiry"])
        same = next((e for e in events if e["cik"] == f["cik"]
                     and abs((dt.date.fromisoformat(e["expiry"]) - ex).days) <= DEDUPE_DAYS), None)
        if same is not None:
            same["announced"] = min(same.get("announced", same["filed"]), f["filed"])
            alt = same.setdefault("alt_expiries", [])
            if f["final"] and not same.get("final") and same["status"] not in ("scored", "no_cross"):
                if same["expiry"] not in alt:
                    alt.append(same["expiry"])
                same.update(expiry=f["expiry"], final=True, filed=f["filed"], form=f["form"], acc=f["acc"],
                            transferable=f["transferable"])
            elif f["expiry"] != same["expiry"] and f["expiry"] not in alt:
                alt.append(f["expiry"])
            continue
        syms = sorted(cik_syms.get(f["cik"], []))
        events.append(dict(f, announced=f["filed"], syms=syms, sym=syms[0] if len(syms) == 1 else None, first_seen=str(today),
                           status="ambiguous" if len(syms) != 1 else "upcoming", borrow=[]))
    return events


# ------------------------------------------------------------------ borrow (read-only)

def borrow_snapshot(sym: str, H: dict | None, schwab=None) -> dict:
    out = dict(alpaca_shortable=None, alpaca_etb=None, schwab_shortable=None, schwab_htb=None, schwab_htb_rate=None,
               schwab_htb_qty=None)
    try:
        from .exdate_open_shadow import ASSET_URL, _get
        a = _get(ASSET_URL.format(sym), {}, H or {})
        out.update(alpaca_shortable=a.get("shortable"), alpaca_etb=a.get("easy_to_borrow"))
    except Exception:  # noqa: BLE001
        pass
    if schwab is not None:
        try:
            ref = (schwab.get_quote(sym).json().get(sym) or {}).get("reference") or {}
            out.update(schwab_shortable=ref.get("isShortable"), schwab_htb=ref.get("isHardToBorrow"),
                       schwab_htb_rate=ref.get("htbRate"), schwab_htb_qty=ref.get("htbQuantity"))
        except Exception:  # noqa: BLE001
            pass
    return out


def borrow_at_entry(e: dict) -> dict | None:
    snaps = [b for b in e.get("borrow", []) if e.get("entry") and b["date"] <= e["entry"]]
    return snaps[-1] if snaps else None


def borrow_read(b: dict | None) -> tuple[bool, float | None]:
    """(available, annual rate or None=unknown). Available = shortable at Alpaca or Schwab; rate = Schwab htbRate when HTB,
    0 when ETB/not HTB, else unknown."""
    if not b:
        return False, None
    ok = bool(b.get("alpaca_shortable")) or bool(b.get("schwab_shortable"))
    if b.get("schwab_htb") and b.get("schwab_htb_rate") is not None:
        return ok, float(b["schwab_htb_rate"]) / 100.0
    if b.get("schwab_htb") is False or b.get("alpaca_etb"):
        return ok, 0.0
    return ok, None


# ------------------------------------------------------------------ scoring (official close crosses)

def score(e: dict, X: dict, divs: dict, today: dt.date) -> dict:
    from .cef_rv_shadow import _div, ew
    p = X.get(e["sym"], {})
    out = dict(e)
    c = lambda d: (p.get(d) or (None,) * 4)[2]  # noqa: E731
    if c(e["entry"]):
        out["entry_close"] = c(e["entry"])
    if c(e["entry"]) and c(e["E"]) and "x_pw" not in e:
        m, _ = ew(X, divs, e["entry"], e["E"])
        if m is not None:
            out["x_pw"] = round((c(e["E"]) + _div(divs, e["sym"], e["entry"], e["E"])) / c(e["entry"]) - 1 - m, 6)
    if str(today) <= e["exit"]:
        out["status"] = "upcoming" if str(today) <= e["entry"] else "live"
        return out
    if not (c(e["entry"]) and c(e["exit"])):
        if str(today) > str(dt.date.fromisoformat(e["exit"]) + dt.timedelta(days=10)):
            out["status"] = "no_cross"
        return out
    m, n = ew(X, divs, e["entry"], e["exit"])
    if m is None:
        return out
    raw = (c(e["exit"]) + _div(divs, e["sym"], e["entry"], e["exit"])) / c(e["entry"]) - 1
    short_x = -(raw - m)
    ok, rate = borrow_read(borrow_at_entry(e))
    bor = rate * (PRE + POST) / 252 if rate is not None else None
    out.update(status="scored", exit_close=c(e["exit"]), raw=round(raw, 6), ew=round(m, 6), ew_n=n, short_x=round(short_x, 6),
               net0=round(short_x - 2 * SIDE, 6), borrow_ok=ok, borrow_rate=rate,
               net=round(short_x - 2 * SIDE - (bor or 0.0), 6), borrow_unknown=rate is None)
    return out


def summary(rows: list[dict]) -> dict:
    g = [r for r in rows if r.get("status") == "scored" and not r.get("late") and r.get("sym")]
    late = [r for r in rows if r.get("status") == "scored" and r.get("late")]
    out = dict(n=len(g), late=len(late), upcoming=sum(r.get("status") == "upcoming" for r in rows),
               live=sum(r.get("status") == "live" for r in rows))
    if not g:
        return out
    v = [r["net"] for r in g]
    pw = [r["x_pw"] for r in g if r.get("x_pw") is not None]
    out.update(mean_bp=1e4 * st.mean(v), median_bp=1e4 * st.median(v), hit=sum(x > 0 for x in v) / len(v),
               borrow_ok=sum(bool(r.get("borrow_ok")) for r in g) / len(g), unknown=sum(bool(r.get("borrow_unknown")) for r in g),
               pw_bp=1e4 * st.mean(pw) if pw else None)
    return out


def verdict(s: dict) -> str:
    if s["n"] < NEED:
        return f" ({s['n']}/{NEED} events)"
    if s["mean_bp"] <= 0:
        return " -> KILL (mean net <= 0)"
    if s["mean_bp"] > GATE_MEAN_BP and s["median_bp"] > 0 and s["borrow_ok"] >= GATE_BORROW:
        return " -> PASS (propose a small taxable short; user decision)"
    return " -> FAIL (final)" if s["n"] >= FINAL else " -> HOLD"


def line(rows: list[dict]) -> str:
    s = summary(rows)
    head = f"CEF-RIGHTS-FWD: {s['upcoming']} upcoming, {s['live']} live, {s['n']} scored (+{s['late']} late, not gated)"
    if not s["n"]:
        return head + verdict(s)
    pw = "-" if s["pw_bp"] is None else f"{s['pw_bp']:+.0f}bp"
    return (head + f"; short net {s['mean_bp']:+.0f}bp (median {s['median_bp']:+.0f}, hit {s['hit']:.0%}), borrow available "
            f"{s['borrow_ok']:.0%} ({s['unknown']} rate unknown), pricing-window excess {pw}" + verdict(s))


# ------------------------------------------------------------------ hygiene (N 1086)

def hygiene(events: list[dict], rv_rows: list[dict], live_open: dict) -> list[dict]:
    """CEF-RV signals / live positions entering or held inside an offering's pricing window [E-10, E+5]."""
    out = []
    for e in events:
        if not e.get("sym") or not e.get("pw_lo"):
            continue
        lo, hi = e["pw_lo"], e["pw_hi"]
        for r in rv_rows:
            if r.get("sym") != e["sym"] or not r.get("entry"):
                continue
            x = r.get("exit")
            if r["entry"] <= hi and (x is None or x >= lo):
                out.append(dict(sym=e["sym"], cik=e["cik"], E=e["E"], pw_lo=lo, pw_hi=hi, src="shadow", signal=r.get("signal"),
                                entry=r["entry"], exit=x, rv_status=r.get("status"), x_oo=r.get("x_oo"), x_cc=r.get("x_cc"),
                                rel="entered_in_window" if r["entry"] >= lo else "held_through"))
        pos = live_open.get(e["sym"])
        if pos and str(pos.get("entry_date", "")) <= hi:
            out.append(dict(sym=e["sym"], cik=e["cik"], E=e["E"], pw_lo=lo, pw_hi=hi, src="live",
                            entry=str(pos.get("entry_date")), rel="held_live"))
    return out


def hygiene_line(rows: list[dict], rv_rows: list[dict]) -> str:
    f = [r for r in rows if r.get("src") == "shadow" and r.get("x_oo") is not None]
    keys = {(r["sym"], r["signal"]) for r in f}
    u = [r["x_oo"] for r in rv_rows if r.get("x_oo") is not None and (r.get("sym"), r.get("signal")) not in keys]
    s = f"CEF-RV rights hygiene: {len(rows)} flagged ({sum(r['src'] == 'live' for r in rows)} live), {len(f)} closed"
    if f:
        s += f", flagged OO excess {1e4 * st.mean(r['x_oo'] for r in f):+.0f}bp"
        if u:
            s += f" vs unflagged {1e4 * st.mean(u):+.0f}bp"
    return s + ("" if len(f) >= HYG_NEED else f" ({len(f)}/{HYG_NEED})")


# ------------------------------------------------------------------ run

def universe(state_dir: Path) -> list[str]:
    p = Path(state_dir) / "cef-rv-panel.json"
    return sorted(json.loads(p.read_text())) if p.exists() else []


def run(state_dir: Path, logs_dir: Path | None = None, log=print, today: dt.date | None = None, H: dict | None = None,
        syms: list[str] | None = None, fetch=None, sessions_fn=None, crosses_fn=None, divs_fn=None, borrow_fn=None,
        workers: int = 3) -> dict:
    from . import marketdata as md
    state_dir = Path(state_dir)
    today = today or dt.datetime.now(dt.timezone.utc).astimezone(ZoneInfo(md.ET)).date()
    path = state_dir / LOG_NAME
    events = _read(path)
    syms = syms if syms is not None else universe(state_dir)
    if not syms:
        log("[cef-rights] no CEF universe (state/cef-rv-panel.json missing); scan skipped")
    else:
        cache = state_dir / CACHE
        cache.mkdir(parents=True, exist_ok=True)
        for old in cache.glob("sub_*_*.json"):
            if not old.name.endswith(f"_{today}.json"):
                old.unlink()
        cm = cik_map(cache, syms, today, fetch)
        cik_syms: dict[int, list[str]] = {}
        for s, c in cm.items():
            cik_syms.setdefault(c, []).append(s)
        from concurrent.futures import ThreadPoolExecutor
        found: list[dict] = []
        with ThreadPoolExecutor(workers) as ex:                # 3 workers x 0.12s sleep: under SEC's 10 req/s
            for r in ex.map(lambda c: scan_cik(c, cache, today, fetch), sorted(cik_syms)):
                found += r
        n0 = len(events)
        events = merge(events, found, cik_syms, today)
        log(f"[cef-rights] scanned {len(cik_syms)} CIKs ({len(syms)} funds): {len(found)} rights prospectuses, "
            f"{len(events) - n0} new offerings")
    if events:
        if sessions_fn is None:
            from .brokers import regular_sessions as sessions_fn
        lo = min(min(e["expiry"] for e in events), str(today))
        hi = max(max(e["expiry"] for e in events), str(today))
        days = session_days(sessions_fn(dt.date.fromisoformat(lo) - dt.timedelta(days=30),
                                        dt.date.fromisoformat(hi) + dt.timedelta(days=60)))
        for e in events:
            if e["status"] in ("scored", "no_cross", "ambiguous"):
                continue
            w = window(days, e["expiry"])
            if w is None:
                e["status"] = "no_window"
                continue
            e.update(w, status=e["status"] if e["status"] != "no_window" else "upcoming")
            e["late"] = e["first_seen"] > e["entry"] or e.get("announced", e["filed"]) > e["entry"]
        snap = [e for e in events if e.get("sym") and e.get("entry") and str(today) <= e["entry"]
                and e["status"] not in ("scored", "no_cross")]
        if snap:
            if borrow_fn is None:
                from .exdate_open_shadow import _headers
                H = H or _headers()
                try:
                    from .brokers import schwab_client
                    sc = schwab_client()
                except Exception:  # noqa: BLE001 - no Schwab login here: Schwab borrow fields stay unknown
                    sc = None
                borrow_fn = lambda s: borrow_snapshot(s, H, sc)  # noqa: E731
            for e in snap:
                if not any(b["date"] == str(today) for b in e["borrow"]):
                    e["borrow"].append(dict(date=str(today), **borrow_fn(e["sym"])))
        todo = [e for e in events if e.get("sym") and e.get("entry") and e["status"] in ("upcoming", "live")
                and str(today) > e["entry"]]
        if todo:
            from .exdate_open_shadow import _headers
            from .pref_ex_shadow import crosses, dividends
            H = H or (_headers() if crosses_fn is None or divs_fn is None else {})
            crosses_fn = crosses_fn or crosses
            divs_fn = divs_fn or dividends
            uni = sorted(set(syms or []) | {e["sym"] for e in todo})
            start = min(e["entry"] for e in todo)
            end = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
            X: dict = {}
            for i in range(0, len(uni), 40):
                X.update(crosses_fn(uni[i:i + 40], start, end, H))
            divs = divs_fn(uni, start, str(today), H)
            ids = {id(e) for e in todo}
            events = [score(e, X, divs, today) if id(e) in ids else e for e in events]
    events = sorted(events, key=lambda e: (e["expiry"], e["cik"]))
    state_dir.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(e) + "\n" for e in events))
    rv = _read(state_dir / "cef-rv.jsonl")
    lp = state_dir / "cef-rv-live.json"
    live_open = (json.loads(lp.read_text()).get("open") or {}) if lp.exists() else {}
    hy = hygiene(events, rv, live_open)
    (state_dir / HYGIENE_NAME).write_text("".join(json.dumps(r) + "\n" for r in hy))
    for e in events:
        if e.get("status") in ("upcoming", "live"):
            b = (e.get("borrow") or [None])[-1]
            ok, rate = borrow_read(b)
            log(f"[cef-rights] {e.get('sym') or e['syms']} expiry {e['expiry']}{'' if e.get('final') else ' (497AD, provisional)'} "
                f"announced {e.get('announced')} E {e.get('E')} entry {e.get('entry')} exit {e.get('exit')} {e['status']}"
                f"{' late' if e.get('late') else ''} shortable {'no snapshot' if b is None else ok} rate "
                f"{'unknown' if rate is None else f'{rate:.2%}'}")
    log(f"[cef-rights] {line(events)}")
    log(f"[cef-rights] {hygiene_line(hy, rv)}")
    return summary(events)


if __name__ == "__main__":
    import sys
    from ..config import Config
    cfg = Config.load()
    if getattr(cfg.daily, "cef_rights_fwd", "shadow") == "off":
        print("[cef-rights] daily.cef_rights_fwd is off")
        sys.exit(0)
    root = Path(__file__).resolve().parents[2]
    u = None
    if "--universe" in sys.argv:              # a file of tickers, one per line or comma-separated (local runs without the panel)
        u = sorted({s.strip().upper() for s in Path(sys.argv[sys.argv.index("--universe") + 1]).read_text().replace(",", "\n")
                    .split() if s.strip()})
    st_dir = Path(sys.argv[sys.argv.index("--state") + 1]) if "--state" in sys.argv else root / "state"
    run(st_dir, root / "logs", syms=u)
