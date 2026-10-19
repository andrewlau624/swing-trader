"""RARE-WATCH: log-only "rare-trigger watchtower" for US-listed, Schwab-tradable instruments (no orders, local prototype).

Each watch is a FROZEN trigger copied from its branch file. Nothing is tuned here. One jsonl row per watch per day is appended to
data/research/rare_watch/watch.jsonl: {ts, date, watch, fired, status, evidence}. status = ok | error | blocked | manual.
Deployed to the server 2026-10-18 (user OK): runs in research-shadows, REGISTRY "RARE-WATCH" in swingtrader/daily/testing.py.
The server has no Sharadar: the listing universe (preferreds, ETD, CEF preferreds, ADR names) comes from Sharadar when present, else
from the frozen RARE_UNIVERSE file next to this module (`universe` rebuilds it from Sharadar on the Mac).

Watches
  cef_pref_floor  research/drafts/branch_N_cef_pref_coverage_2026-10-18.md ("If the user wants a free option on the next crash"):
                  SPY close >= 25% below its trailing-252-session high AND the median close of the listed $25-par CEF-preferred
                  basket <= 80% of $25 (= $20.00). Fired = both. (Branch rule then buys at the next close cross; not done here.)
                  Basket = Sharadar SFP "CEF Preferred" not delisted; $25-par proxy = 1y median close >= $22 (drops the $10-par
                  muni/MLP issues branch N flags). Sharadar is a static 2026-10-05 snapshot, so listings after that are missed.
  crash_trend     CRASH-A R2 (research/drafts/crash_A_trend_2026-10-18.md): fired while SPY is in a risk-off spell (close < 0.99 x
                  200d SMA, back to risk-on > 1.01 x SMA). A regime flag, often fires in ordinary corrections; never a short signal.
  crash_reentry   CRASH-C R3 (crash_C_bottom_2026-10-18.md): fired when SPY has been >= 40% below its running peak (5y window) and
                  closes above its 210d SMA; evidence carries the 5%-below-SMA stop that did the work in 1929-32.
  crash_cef_blowout CRASH-C blowout: SPY >= 20% off its 252d high AND the EW-median CEF discount (state/cef-rv-panel.json) >= 3.0 pts
                  below its 52w median; fire lists the bottom-decile funds. WEAK-PASS (2008/2020 yes, 2022 no). Log only.
  pref_arrears    research/drafts/branch_G_pref_arrears_2026-10-17.md (G2 / G2-FWD): ex-dividend >= 3x median of the prior 4 payments,
                  yield 4-30% of the prior close, raw price $10-60, 20d median $vol >= $50k, ex-date within the last 14 days. Universe =
                  live Sharadar preferreds (SEP preferred categories + SFP ETD + CEF Preferred). Dividends/prices from the Yahoo chart
                  API (as intl_pref_shadow.py). EDGAR 8-K text confirmation ("accrued and unpaid|accumulated and unpaid|arrears") runs
                  only when SEC_USER_AGENT is set in .env, else the evidence says "edgar: blocked, no SEC_USER_AGENT".
  ofac_cmic       research/drafts/branch_P_ideation_2026-10-18.md (#1, 1260H / NS-CMIC follow-on): trigger = OFAC adds any entity to
                  the Chinese Military-Industrial Complex list (program tag containing "CMIC" in the OFAC consolidated non-SDN XML)
                  that maps to a US-listed ADR (watch names Alibaba, Baidu, BYD, Nio, WuXi AppTec + name match to Sharadar ADR names).
                  Any NEW CMIC uid vs the last snapshot (data/research/rare_watch/ofac_cmic_snapshot.json) = list change (reported);
                  fired only if a new entity maps to an ADR. First run saves the baseline and never fires.
  rating_equity   research/drafts/branch_L_event_calls_2026-10-18.md: MANUAL. A S&P/Moody's/Fitch hybrid-criteria publication that
                  REDUCES equity credit for preferreds -> check issues with a $25.50 "Rating Agency Event" call clause trading < ~$24
                  and read the issuer 8-Ks for 90 days. Prints the reminder and current prices of the named issues.

Usage (.venv/bin/python -m research.sim.rare_watch <cmd>; or `make rare-watch`):
  scan [--no-net-cache]   run all watches, append rows to watch.jsonl
  report                  last state per watch
  universe                write the frozen listing universe (needs ~/data/sharadar)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import statistics as st
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

D = Path(__file__).resolve().parents[2] / "data/research/rare_watch"
LOG = D / "watch.jsonl"
SNAP = D / "ofac_cmic_snapshot.json"
SHAR = Path.home() / "data" / "sharadar"
RARE_UNIVERSE = Path(__file__).with_name("rare_watch_universe.csv.gz")
UA = {"User-Agent": "Mozilla/5.0 (research)"}   # Yahoo / OFAC only: the contact email is for sec.gov alone
YCH = "https://query1.finance.yahoo.com/v8/finance/chart/{}?range=1y&interval=1d&events=div"
OFAC = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/CONSOLIDATED.XML"

# branch N
SPY_DD, BASKET_PCT, PAR, PAR_MIN_MEDIAN = 0.25, 0.80, 25.0, 22.0
# branch G
G_MULT, G_Y, G_PX, G_MINVOL, G_DAYS = 3.0, (0.04, 0.30), (10.0, 60.0), 50_000.0, 14
# branch P
CMIC_WATCH = ("ALIBABA", "BAIDU", "BYD", "NIO", "WUXI APPTEC")
# branch L: issuers named in the $25.50 Rating Agency Event clause map
L_ISSUERS = ("ALLSTATE", "BRIGHTHOUSE", "AMERICAN INTERNATIONAL GROUP", "ALABAMA POWER", "ATHENE", "AIR LEASE", "ARCH CAPITAL",
             "ARGO GROUP", "AMERICAN NATIONAL", "ENSTAR", "SIRIUSPOINT")
L_PX = 24.0
R2_BAND, R3_DD = 0.01, 0.40           # CRASH-A R2 (200d SMA, 1% band); CRASH-C R3 (>= 40% DD, then > 210d SMA, stop 5% below)
CEF_DD, CEF_WIDEN = 0.20, 3.0         # CRASH-C blowout: SPY <= -20% off 252d high AND EW-median discount 3.0 pts under its 52w median
STATE = Path(__file__).resolve().parents[2] / "state"


def yget(sym: str, rng: str = "1y"):
    """Yahoo daily chart (default 1y) -> dict(close=[...], vol=[...], dates=[...], div={date: amt}) or None. Raw prices."""
    url = YCH.format(urllib.parse.quote(sym)).replace("range=1y", f"range={rng}")
    for i in range(3):
        try:
            j = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30))
            r = j["chart"]["result"][0]
            q = r["indicators"]["quote"][0]
            off = r["meta"].get("gmtoffset", -14400)
            rows = [(dt.datetime.fromtimestamp(t + off, dt.UTC).date(), c, v) for t, c, v in
                    zip(r.get("timestamp", []), q["close"], q["volume"]) if c is not None]
            dv = {dt.datetime.fromtimestamp(v["date"] + off, dt.UTC).date(): v["amount"]
                  for v in (r.get("events", {}) or {}).get("dividends", {}).values()}
            return {"dates": [x[0] for x in rows], "close": [x[1] for x in rows], "vol": [x[2] or 0 for x in rows], "div": dv}
        except Exception:
            time.sleep(1 + i)
    return None


def fetch_all(syms):
    with ThreadPoolExecutor(8) as ex:
        return dict(zip(syms, ex.map(yget, syms)))


def sharadar_live():
    if not (SHAR / "tickers.parquet").exists():
        return pd.read_csv(RARE_UNIVERSE, dtype=str)
    t = pd.read_parquet(SHAR / "tickers.parquet", columns=["table", "ticker", "name", "category", "isdelisted", "lastpricedate", "location"])
    t = t[(t.isdelisted == "N")].drop_duplicates("ticker")
    return t


def universe(_a):
    t = sharadar_live()
    keep = t.category.isin(["Domestic Preferred Stock", "ADR Preferred Stock", "Canadian Preferred Stock", "ETD", "CEF Preferred"]) \
        | t.category.fillna("").str.contains("ADR")
    u = t[keep][["table", "ticker", "name", "category", "lastpricedate"]].astype(str)
    u.to_csv(RARE_UNIVERSE, index=False, compression="gzip")
    print(f"wrote {len(u)} rows to {RARE_UNIVERSE}")


def env_val(key: str):
    try:
        for line in (Path(__file__).resolve().parents[2] / ".env").read_text().splitlines():
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip("'\"") or None
    except OSError:
        pass
    return os.environ.get(key)


# ---------------------------------------------------------------- watches
def w_cef_pref_floor(t, px):
    b = t[(t.table == "SFP") & (t.category == "CEF Preferred")].ticker.tolist()
    spy = yget("SPY")
    if not spy:
        raise RuntimeError("SPY fetch failed")
    hi = max(spy["close"][-252:])
    dd = 1 - spy["close"][-1] / hi
    last, n_all = {}, 0
    for s in b:
        d = px.get(s)
        if not d or len(d["close"]) < 20 or d["dates"][-1] < dt.date.today() - dt.timedelta(days=10):
            continue
        n_all += 1
        if st.median(d["close"]) < PAR_MIN_MEDIAN:
            continue
        last[s] = d["close"][-1]
    med = st.median(last.values()) if last else None
    under = sorted(s for s, p in last.items() if p <= BASKET_PCT * PAR)
    fired = bool(med is not None and dd >= SPY_DD and med <= BASKET_PCT * PAR)
    ev = {"spy_drawdown_252d": round(dd, 4), "spy_trigger": SPY_DD, "basket_n": len(last), "basket_scanned": n_all,
          "basket_median_close": None if med is None else round(med, 2), "basket_trigger": BASKET_PCT * PAR,
          "n_issues_at_or_below_trigger": len(under), "issues_below": under[:10],
          "basket_min": None if not last else round(min(last.values()), 2)}
    return fired, "ok", ev


def _sma(x, n):
    return sum(x[-n:]) / n if len(x) >= n else None


def w_crash(spy):
    """CRASH-A R2 trend state + CRASH-C R3 trend-confirmed re-entry on SPY (5y raw closes). Frozen rules, log only."""
    c, d = spy["close"], spy["dates"]
    if len(c) < 400:
        raise RuntimeError(f"SPY history too short ({len(c)})")
    off, start = False, None                     # R2: out < 0.99 x 200d SMA, back in > 1.01 x SMA (walked for hysteresis)
    for i in range(200, len(c)):
        m = sum(c[i - 199:i + 1]) / 200
        if not off and c[i] < (1 - R2_BAND) * m:
            off, start = True, d[i]
        elif off and c[i] > (1 + R2_BAND) * m:
            off, start = False, None
    pk, seen40, ep_start = c[0], False, None     # R3: >= 40% below the running peak, then a close above the 210d SMA
    for i, x in enumerate(c):
        if x >= pk:
            pk, seen40, ep_start = x, False, None
        elif x <= (1 - R3_DD) * pk and not seen40:
            seen40, ep_start = True, d[i]
    m200, m210 = _sma(c, 200), _sma(c, 210)
    dd_pk = 1 - c[-1] / pk
    trend = {"spy_close": round(c[-1], 2), "sma200": round(m200, 2), "ratio_to_sma200": round(c[-1] / m200, 4),
             "band": R2_BAND, "risk_off_since": None if not off else str(start), "drawdown_from_peak": round(dd_pk, 4),
             "drawdown_252d": round(1 - c[-1] / max(c[-252:]), 4)}
    above = c[-1] > m210
    reentry = {"drawdown_from_peak": round(dd_pk, 4), "dd_trigger": R3_DD, "seen_40pct_since": None if not seen40 else str(ep_start),
               "sma210": round(m210, 2), "close_above_sma210": above, "stop_level_5pct_below_sma210": round(0.95 * m210, 2),
               "peak_window": f"{d[0]}..{d[-1]} (5y Yahoo; a peak older than that is missed)"}
    return (off, "ok", trend), (bool(seen40 and above), "ok", reentry)


def w_cef_blowout(spy, state_dir: Path):
    """CRASH-C blowout trigger on the CEF-RV panel: SPY <= -20% off its 252d high AND the EW-median CEF discount >= 3.0 pts
    below its own 52-week median (crash_c.py). Fire lists the bottom decile of (fund discount - own 52w median)."""
    try:
        pan = json.loads((state_dir / "cef-rv-panel.json").read_text())
    except (OSError, ValueError):
        return False, "blocked", {"error": "state/cef-rv-panel.json absent (make cef-rv-panel)"}
    by_date = {}
    for sym, rows in pan.items():
        for r in rows:
            if r[1] is not None:
                by_date.setdefault(r[0], {})[sym] = r[1] * 100
    full = max(len(v) for v in by_date.values()) if by_date else 0
    dates = sorted(x for x, v in by_date.items() if len(v) >= full // 2)     # drop a partially-refreshed latest week
    if len(dates) < 40:
        return False, "blocked", {"error": f"panel has {len(dates)} weeks"}
    med = [st.median(by_date[x].values()) for x in dates]
    widen = med[-1] - st.median(med[-52:])
    dd = 1 - spy["close"][-1] / max(spy["close"][-252:])
    fired = bool(dd >= CEF_DD and widen <= -CEF_WIDEN)
    ev = {"panel_week": dates[-1], "funds": len(by_date[dates[-1]]), "ew_median_disc_pct": round(med[-1], 2),
          "widen_vs_52w_pts": round(widen, 2), "widen_trigger": -CEF_WIDEN, "spy_drawdown_252d": round(dd, 4),
          "spy_trigger": CEF_DD, "lockout": "52 weeks after a fire (read the log)"}
    if fired:
        z = {}
        for sym in by_date[dates[-1]]:
            h = [by_date[x][sym] for x in dates[-52:] if sym in by_date[x]]
            if len(h) >= 40:
                z[sym] = round(by_date[dates[-1]][sym] - st.median(h), 2)
        ev["bottom_decile"] = sorted(z.items(), key=lambda kv: kv[1])[:max(1, len(z) // 10)]
    return fired, "ok", ev


def w_pref_arrears(t, px, syms):
    cut = dt.date.today() - dt.timedelta(days=G_DAYS)
    hits = []
    for s in syms:
        d = px.get(s)
        if not d or not d["div"]:
            continue
        dv = sorted(d["div"].items())
        for i in range(4, len(dv)):
            ex, amt = dv[i]
            if ex < cut:
                continue
            reg = st.median([a for _, a in dv[i - 4:i]])
            if reg <= 0 or amt < G_MULT * reg:
                continue
            idx = [k for k, x in enumerate(d["dates"]) if x < ex]
            if not idx:
                continue
            k = idx[-1]
            pc = d["close"][k]
            y = amt / pc if pc else 0
            v20 = st.median([d["close"][j] * d["vol"][j] for j in range(max(0, k - 19), k + 1)])
            ok = G_Y[0] <= y <= G_Y[1] and G_PX[0] <= pc <= G_PX[1] and v20 >= G_MINVOL
            hits.append({"ticker": s, "ex": str(ex), "div": round(amt, 4), "reg_median": round(reg, 4), "mult": round(amt / reg, 1),
                         "y": round(y, 4), "px": round(pc, 2), "med_dvol20": round(v20), "passes_spec": ok})
    fired = any(h["passes_spec"] for h in hits)
    ev = {"universe": len(syms), "with_data": sum(1 for s in syms if px.get(s)), "recent_ge3x_events": hits,
          "window_days": G_DAYS}
    ua = env_val("SEC_USER_AGENT")
    if not ua:
        ev["edgar"] = "blocked: no SEC_USER_AGENT"
        status = "ok"
    else:
        ev["edgar"] = "8-K text confirmation only when an event fires"
        status = "ok"
        if fired:
            for h in hits:
                if not h["passes_spec"]:
                    continue
                q = urllib.parse.quote('"accrued and unpaid" OR "accumulated and unpaid" OR "arrears"')
                u = (f"https://efts.sec.gov/LatestSearch/rest/search-index?q={q}&forms=8-K&dateRange=custom&startdt="
                     f"{(dt.date.today() - dt.timedelta(days=45)).isoformat()}&enddt={dt.date.today().isoformat()}")
                try:
                    j = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": ua}), timeout=30))
                    h["edgar_8k_hits_any_issuer_45d"] = j.get("hits", {}).get("total", {}).get("value")
                except Exception as e:
                    h["edgar_error"] = str(e)[:80]
    return fired, status, ev


def _norm(s: str) -> str:
    s = re.sub(r"[^A-Z0-9 ]", " ", s.upper())
    s = re.sub(r"\b(CO|CORP|CORPORATION|INC|LTD|LIMITED|HOLDINGS|HOLDING|GROUP|CO LTD|PLC|ADR|THE|SA|NV|AG|CLASS|[A-Z])\b", " ", s)
    return " ".join(s.split())


def w_ofac_cmic(t):
    raw = urllib.request.urlopen(urllib.request.Request(OFAC, headers=UA), timeout=120).read()
    root = ET.fromstring(raw)
    ns = {"n": root.tag.split("}")[0].strip("{")}
    ents = {}
    for e in root.findall("n:sdnEntry", ns):
        progs = [p.text or "" for p in e.findall("n:programList/n:program", ns)]
        if not any("CMIC" in p for p in progs):
            continue
        uid = e.findtext("n:uid", namespaces=ns)
        name = " ".join(x for x in (e.findtext("n:firstName", namespaces=ns), e.findtext("n:lastName", namespaces=ns)) if x)
        isins = [i.findtext("n:idNumber", namespaces=ns) for i in e.findall("n:idList/n:id", ns) if i.findtext("n:idType", namespaces=ns) == "ISIN"]
        ents[uid] = {"name": name, "programs": progs, "isins": isins}
    pub = root.findtext("n:publshInformation/n:Publish_Date", namespaces=ns)
    prev = json.loads(SNAP.read_text()) if SNAP.exists() else None
    new = [] if prev is None else [{**v, "uid": k} for k, v in ents.items() if k not in prev["entities"]]
    gone = [] if prev is None else [{**v, "uid": k} for k, v in prev["entities"].items() if k not in ents]
    adr = t[t.category.fillna("").str.contains("ADR")]
    adr_map = {(_norm(n)): tk for tk, n in zip(adr.ticker, adr.name) if _norm(n)}

    def to_adr(name):
        n = _norm(name)
        if not n:
            return None
        for k, tk in adr_map.items():
            if n == k or (len(n) >= 6 and (n in k or k in n)):
                return tk
        for w in CMIC_WATCH:
            if w in name.upper():
                return "watch:" + w
        return None

    for x in new:
        x["adr"] = to_adr(x["name"])
    fired = any(x["adr"] for x in new)
    D.mkdir(parents=True, exist_ok=True)
    SNAP.write_text(json.dumps({"publish_date": pub, "saved": dt.date.today().isoformat(), "entities": ents}))
    watch_hits = {w: [e["name"] for e in ents.values() if w in e["name"].upper()] for w in CMIC_WATCH}
    ev = {"publish_date": pub, "cmic_entities": len(ents), "baseline_run": prev is None,
          "prev_snapshot_publish": None if prev is None else prev["publish_date"], "new": new[:20], "removed": gone[:20],
          "watch_names_currently_listed": watch_hits}
    return fired, "ok", ev


def w_rating_equity(t, px_l):
    ev = {"manual": "Watch S&P/Moody's/Fitch hybrid-criteria publications that REDUCE equity credit for preferreds (branch L). If "
                    "one appears: list issues with a $25.50 Rating Agency Event clause trading under ~$24, read issuer 8-Ks for 90d.",
          "issues": px_l}
    return False, "manual", ev


# ---------------------------------------------------------------- driver
def append(rows):
    D.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        for r in rows:
            f.write(json.dumps(r, default=str) + "\n")


def scan(_a):
    now = dt.datetime.now().isoformat(timespec="seconds")
    today = dt.date.today().isoformat()
    rows = []

    def run(name, fn):
        try:
            fired, status, ev = fn()
        except Exception as e:
            fired, status, ev = False, "error", {"error": f"{type(e).__name__}: {str(e)[:200]}"}
        rows.append({"ts": now, "date": today, "watch": name, "fired": fired, "status": status, "evidence": ev})

    spy5 = yget("SPY", "5y")
    try:
        if not spy5:
            raise RuntimeError("SPY 5y fetch failed")
        crash = w_crash(spy5)
    except Exception as e:
        crash = None
        err = e
    run("crash_trend", lambda: crash[0] if crash else (_ for _ in ()).throw(err))
    run("crash_reentry", lambda: crash[1] if crash else (_ for _ in ()).throw(err))
    run("crash_cef_blowout", lambda: w_cef_blowout(spy5, STATE) if spy5 else (_ for _ in ()).throw(err))
    try:
        t = sharadar_live()
    except Exception as e:
        t = None
        for n in ("cef_pref_floor", "pref_arrears", "ofac_cmic", "rating_equity"):
            rows.append({"ts": now, "date": today, "watch": n, "fired": False, "status": "error",
                         "evidence": {"error": f"sharadar tickers: {e}"}})
    if t is not None:
        pref_cat = ["Domestic Preferred Stock", "ADR Preferred Stock", "Canadian Preferred Stock"]
        pref = t[((t.table == "SEP") & t.category.isin(pref_cat)) | ((t.table == "SFP") & t.category.isin(["ETD", "CEF Preferred"]))]
        pref = pref[pref.lastpricedate.astype(str) >= "2026-09-01"]
        l_tk = {r.ticker: r.name for r in pref.itertuples() if any(i in r.name.upper() for i in L_ISSUERS)}
        syms = sorted(set(pref.ticker))
        px = fetch_all(syms)
        nfail = sum(1 for d in px.values() if d is None)
        run("cef_pref_floor", lambda: w_cef_pref_floor(t, px))
        run("pref_arrears", lambda: w_pref_arrears(t, px, syms))
        run("ofac_cmic", lambda: w_ofac_cmic(t))
        lp = {}
        for s, n in l_tk.items():
            d = px.get(s)
            if d and d["close"]:
                lp[s] = {"name": n, "last": round(d["close"][-1], 2), "under_trigger": d["close"][-1] < L_PX}
        run("rating_equity", lambda: w_rating_equity(t, lp))
        rows[-1]["evidence"]["yahoo_failed_symbols"] = nfail
        rows[-1]["evidence"]["universe_fetched"] = len(syms)
    append(rows)
    report(_a)


def report(_a):
    if not LOG.exists():
        print("no log yet; run scan")
        return
    last = {}
    for line in LOG.read_text().splitlines():
        r = json.loads(line)
        last[r["watch"]] = r
    for w, r in last.items():
        e = r["evidence"]
        print(f"[{r['date']}] {w:15s} fired={r['fired']!s:5s} status={r['status']}")
        if w == "cef_pref_floor" and r["status"] == "ok":
            print(f"    SPY 252d drawdown {e['spy_drawdown_252d']:.1%} (trigger {e['spy_trigger']:.0%}); basket n={e['basket_n']} median "
                  f"${e['basket_median_close']} min ${e['basket_min']} (trigger <= ${e['basket_trigger']:.2f}); issues at/below: {e['n_issues_at_or_below_trigger']}")
        elif w == "pref_arrears" and r["status"] == "ok":
            print(f"    universe {e['universe']} ({e['with_data']} with data); >=3x events in last {e['window_days']}d: {len(e['recent_ge3x_events'])}; {e['edgar']}")
            for h in e["recent_ge3x_events"][:5]:
                print("     ", h)
        elif w == "ofac_cmic" and r["status"] == "ok":
            print(f"    OFAC publish {e['publish_date']}; CMIC entities {e['cmic_entities']}; baseline_run={e['baseline_run']}; new {len(e['new'])}, removed {len(e['removed'])}")
            for x in e["new"][:5]:
                print("      NEW", x["name"], "->", x["adr"])
            print("    watch names listed:", {k: v[:2] for k, v in e["watch_names_currently_listed"].items()})
        elif w.startswith("crash_") and r["status"] == "ok":
            print("    ", {k: v for k, v in e.items() if k != "bottom_decile"}, "| bottom decile:", e.get("bottom_decile", "-"))
        elif w == "rating_equity" and "manual" in e:
            print("    MANUAL:", e["manual"])
            for s, v in sorted(e["issues"].items()):
                print(f"      {s:10s} {v['last']:>7.2f} {'<24' if v['under_trigger'] else ''}  {v['name']}")
        elif r["status"] == "error":
            print("    ", e)


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("scan").set_defaults(f=scan)
    sp.add_parser("report").set_defaults(f=report)
    sp.add_parser("universe").set_defaults(f=universe)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
