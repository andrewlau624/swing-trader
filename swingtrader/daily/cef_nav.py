"""Server-side refresh of the CEF-RV weekly NAV panel from the Nasdaq Fund Network (api.nasdaq.com).

CEFConnect (the panel's original source) blocks the server's datacenter IP, so until 2026-10-19 the panel had to be fetched on
the Mac and scp'd over (make cef-rv-panel). Every listed CEF also publishes its daily NAV as a quoted Nasdaq Fund Network symbol
(GAB -> XGABX, PDI -> XPDIX, ADX -> XADEX), and api.nasdaq.com serves those from the server. This module appends new weekly rows to
the stored panel from that source: NAV = the NAV symbol's Friday close (assetclass mutualfunds), price = the fund's own Friday close
(assetclass stocks), row = [friday, price / nav - 1, nav], the same shape and dating CEFConnect uses (a holiday Friday has no row).
Checked 2026-10-19: GAB 10-16 close $5.15 / NAV 5.55 -> -7.21%, identical to the CEFConnect row.

The NAV symbol map (state/cef-rv-navmap.json) is built here too: X{sym}X first, else a Nasdaq name lookup; funds with no NAV
symbol (ASA, the Sprott physical trusts) keep their stored rows and are re-checked monthly. The universe itself (which funds) still
comes from CEFConnect, so `make cef-rv-panel` from the Mac remains the way to seed the panel or add new funds; the weekly
refresh no longer depends on it. cef_rv_shadow.panel() calls refresh() whenever CEFConnect is unreachable.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

NASDAQ = "https://api.nasdaq.com/api"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
      "Accept": "application/json"}
MAP_NAME = "cef-rv-navmap.json"   # state/: sym -> {"nav": navsym | None, "checked": date}
THREADS = 6
RECHECK_DAYS = 30                 # unmapped funds are looked up again after this long
NAVSYM = re.compile(r"^X[A-Z]{1,5}X$")
DRIFT = 0.005                     # overlap check: NAV on the stored last week must agree within this


def _get(path: str, params: dict | None = None) -> dict | None:
    """Nasdaq API `data` object, or None; retries 429/5xx/non-JSON with backoff."""
    import requests
    for k in range(3):
        try:
            r = requests.get(f"{NASDAQ}/{path}", params=params, headers=UA, timeout=30)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("application/json"):
                return r.json().get("data") or None
        except Exception:  # noqa: BLE001
            pass
        time.sleep(2 * (k + 1))
    return None


def _num(s) -> float | None:
    try:
        v = float(str(s).replace("$", "").replace(",", ""))
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def hist(sym: str, assetclass: str, since: str, get=None) -> dict[str, float]:
    """ISO date -> close for `sym` from `since` (daily rows; NAV symbols carry the NAV as the close)."""
    get = get or _get
    d = get(f"quote/{sym}/historical", dict(assetclass=assetclass, fromdate=since, limit=5000)) or {}
    out = {}
    for r in ((d.get("tradesTable") or {}).get("rows") or []):
        try:
            day = dt.datetime.strptime(r.get("date", ""), "%m/%d/%Y").date().isoformat()
        except ValueError:
            continue
        v = _num(r.get("close"))
        if v:
            out[day] = v
    return out


def fridays(nav: dict[str, float], px: dict[str, float]) -> list[list]:
    """[friday, price / nav - 1, nav] for every Friday both series have (CEFConnect's shape; holiday Fridays have no row)."""
    rows = []
    for day in sorted(nav):
        if dt.date.fromisoformat(day).weekday() == 4 and day in px:
            rows.append([day, px[day] / nav[day] - 1, nav[day]])
    return rows


def nav_symbol(sym: str, get=None) -> str | None:
    """The fund's Nasdaq Fund Network NAV symbol: X{sym}X if it exists, else a name lookup (ADX -> XADEX)."""
    get = get or _get
    cand = f"X{sym}X"
    if get(f"quote/{cand}/info", dict(assetclass="mutualfunds")):
        return cand
    info = get(f"quote/{sym}/info", dict(assetclass="stocks")) or {}
    name = re.sub(r"\(The\)|Common Stock|Common Shares|,|\.", " ", info.get("companyName") or "").split()
    if len(name) < 2:
        return None
    hits = (get(f"autocomplete/slookup/10", dict(search=" ".join(name[:3]))) or [])
    key = " ".join(name[:2]).lower()
    for h in hits if isinstance(hits, list) else []:
        s = str(h.get("symbol") or "")
        if h.get("asset") == "MUTUALFUNDS" and NAVSYM.match(s) and str(h.get("name") or "").lower().startswith(key):
            return s
    return None


def navmap(state_dir: Path, syms: list[str], today: dt.date, log=print, get=None, threads: int = THREADS) -> dict:
    """Load state/cef-rv-navmap.json, resolve new (or stale-unmapped) funds, save."""
    get = get or _get
    p = Path(state_dir) / MAP_NAME
    m = json.loads(p.read_text()) if p.exists() else {}
    cutoff = (today - dt.timedelta(days=RECHECK_DAYS)).isoformat()
    need = [s for s in syms if s not in m or (not m[s].get("nav") and (m[s].get("checked") or "") < cutoff)]
    if need:
        with ThreadPoolExecutor(threads) as ex:
            for s, ns in zip(need, ex.map(lambda s: nav_symbol(s, get), need)):
                m[s] = {"nav": ns, "checked": today.isoformat()}
        Path(state_dir).mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(m, indent=0, sort_keys=True))
    mapped = sum(1 for s in syms if (m.get(s) or {}).get("nav"))
    log(f"[cef-nav] NAV symbols: {mapped}/{len(syms)} funds mapped ({len(need)} looked up this run)")
    return m


def refresh(pan: dict[str, list], state_dir: Path, today: dt.date, log=print, keep: int = 160, get=None,
            threads: int = THREADS) -> dict[str, list]:
    """Append the weekly rows after each fund's stored last week; rows are never rewritten, only extended."""
    get = get or _get
    syms = sorted(pan)
    m = navmap(state_dir, syms, today, log, get, threads)
    todo = [s for s in syms if (m.get(s) or {}).get("nav")]
    far = (today - dt.timedelta(days=7 * keep + 7)).isoformat()

    def one(s: str) -> tuple[str, list[list]]:
        last = pan[s][-1][0] if pan[s] else far
        return s, fridays(hist(m[s]["nav"], "mutualfunds", last, get), hist(s, "stocks", last, get))

    new, added, drift, empty, weeks = dict(pan), 0, [], 0, set()
    with ThreadPoolExecutor(threads) as ex:
        for s, rows in ex.map(one, todo):
            old = pan[s]
            if not rows:
                empty += 1
                continue
            last = old[-1][0] if old else ""
            ov = [r for r in rows if r[0] == last]
            if ov and old and len(old[-1]) >= 3 and old[-1][2] and abs(ov[0][2] / old[-1][2] - 1) > DRIFT:
                drift.append(s)
            add = [r for r in rows if r[0] > last]
            if add:
                added += 1
                weeks.update(r[0] for r in add)
                new[s] = (list(old) + add)[-keep:]
    weeks = sorted(weeks)
    log(f"[cef-nav] Nasdaq refresh: {added}/{len(todo)} mapped funds extended ({empty} returned nothing, "
        f"{len(syms) - len(todo)} unmapped kept as stored); new weeks {weeks[0] if weeks else '-'}..{weeks[-1] if weeks else '-'}"
        + (f"; NAV DRIFT vs the stored last week on {len(drift)}: {drift[:6]}" if drift else ""))
    return new
