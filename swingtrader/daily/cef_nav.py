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
import statistics
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
DRIFT = 0.005                     # overlap check: the NAV symbol's history must agree with the stored rows within this (median)
OVERLAP_DAYS = 21                 # weeks before the stored last week fetched for that check


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


def nav_candidates(sym: str, get=None) -> list[str]:
    """Possible Nasdaq Fund Network NAV symbols for the fund: X{sym}X if it exists, then every name-lookup hit (ADX -> XADEX).
    A term trust and its sibling share a truncated autocomplete name (BMEZ / BME), so the caller must verify a candidate
    against the fund's stored NAV history (navmap) before using it."""
    get = get or _get
    out = []
    cand = f"X{sym}X"
    if get(f"quote/{cand}/info", dict(assetclass="mutualfunds")):
        out.append(cand)
    info = get(f"quote/{sym}/info", dict(assetclass="stocks")) or {}
    name = re.sub(r"\(The\)|Common Stock|Common Shares|,|\.", " ", info.get("companyName") or "").split()
    if len(name) < 2:
        return out
    hits = (get("autocomplete/slookup/10", dict(search=" ".join(name[:4]))) or [])
    full = " ".join(name).lower()
    for h in hits if isinstance(hits, list) else []:
        s, hn = str(h.get("symbol") or ""), " ".join(str(h.get("name") or "").split()).lower()
        # autocomplete truncates names (~30 chars): a hit matches when it is a prefix of the full name
        if h.get("asset") == "MUTUALFUNDS" and NAVSYM.match(s) and hn and full.startswith(hn[:28]) and s not in out:
            out.append(s)
    return out


def nav_symbol(sym: str, get=None) -> str | None:
    """First candidate when it is the only one (no history to verify against); None when ambiguous."""
    c = nav_candidates(sym, get)
    return c[0] if len(c) == 1 else None


def agrees(navsym: str, stored: list, get=None) -> bool | None:
    """Does the NAV symbol's history match the stored rows (median |diff| <= DRIFT over the weeks both have)? None = no overlap."""
    nav_at = {r[0]: r[2] for r in stored if len(r) >= 3 and r[2]}
    if not nav_at:
        return None
    last = max(nav_at)
    since = (dt.date.fromisoformat(last) - dt.timedelta(days=OVERLAP_DAYS)).isoformat()
    h = hist(navsym, "mutualfunds", since, get)
    ov = [abs(h[d] / nav_at[d] - 1) for d in h if d in nav_at]
    return statistics.median(ov) <= DRIFT if ov else None


def resolve(sym: str, stored: list, get=None) -> dict:
    """{"nav": navsym | None, "tried": [...]}: the first candidate whose history agrees with the stored rows; without any
    overlap only an unambiguous candidate is accepted."""
    cands = nav_candidates(sym, get)
    for c in cands:
        ok = agrees(c, stored, get)
        if ok or (ok is None and len(cands) == 1):
            return {"nav": c, "tried": cands}
    return {"nav": None, "tried": cands}


def navmap(state_dir: Path, syms: list[str], today: dt.date, log=print, get=None, threads: int = THREADS,
           pan: dict | None = None) -> dict:
    """Load state/cef-rv-navmap.json, resolve new (or stale-unmapped) funds against their stored rows, save."""
    get = get or _get
    pan = pan or {}
    p = Path(state_dir) / MAP_NAME
    m = json.loads(p.read_text()) if p.exists() else {}
    cutoff = (today - dt.timedelta(days=RECHECK_DAYS)).isoformat()
    need = [s for s in syms if s not in m or (not m[s].get("nav") and (m[s].get("checked") or "") < cutoff)]
    if need:
        with ThreadPoolExecutor(threads) as ex:
            for s, r in zip(need, ex.map(lambda s: resolve(s, pan.get(s) or [], get), need)):
                m[s] = {**r, "checked": today.isoformat()}
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
    m = navmap(state_dir, syms, today, log, get, threads, pan)
    todo = [s for s in syms if (m.get(s) or {}).get("nav")]
    far = (today - dt.timedelta(days=7 * keep + 7)).isoformat()

    def one(s: str) -> tuple[str, list[list]]:
        last = pan[s][-1][0] if pan[s] else far
        since = (dt.date.fromisoformat(last) - dt.timedelta(days=OVERLAP_DAYS)).isoformat()   # overlap for the NAV check
        return s, fridays(hist(m[s]["nav"], "mutualfunds", since, get), hist(s, "stocks", since, get))

    new, added, mismap, empty, weeks = dict(pan), 0, [], 0, set()
    with ThreadPoolExecutor(threads) as ex:
        for s, rows in ex.map(one, todo):
            old = pan[s]
            if not rows:
                empty += 1
                continue
            last = old[-1][0] if old else ""
            stored = {r[0]: r[2] for r in old if len(r) >= 3 and r[2]}
            ov = [abs(r[2] / stored[r[0]] - 1) for r in rows if r[0] in stored]
            if ov and statistics.median(ov) > DRIFT:
                # the NAV symbol tracks a different fund (a term trust mapped to its sibling): unmap it, keep the stored rows
                mismap.append(s)
                m[s] = {"nav": None, "checked": today.isoformat(), "mismap": m[s]["nav"]}
                continue
            add = [r for r in rows if r[0] > last]
            if add:
                added += 1
                weeks.update(r[0] for r in add)
                new[s] = (list(old) + add)[-keep:]
    if mismap:
        (Path(state_dir) / MAP_NAME).write_text(json.dumps(m, indent=0, sort_keys=True))
    weeks = sorted(weeks)
    log(f"[cef-nav] Nasdaq refresh: {added}/{len(todo)} mapped funds extended ({empty} returned nothing, "
        f"{len(syms) - len(todo)} unmapped kept as stored); new weeks {weeks[0] if weeks else '-'}..{weeks[-1] if weeks else '-'}"
        + (f"; {len(mismap)} NAV symbols REJECTED (history disagrees with the stored rows), now unmapped: {mismap[:8]}" if mismap else ""))
    return new
