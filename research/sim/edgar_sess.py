"""Study EDGAR-SESS (round1_prose.md "## Study EDGAR-SESS", N 1096-1097): filings ACCEPTED on EDGAR during the regular session,
traded from acceptance minute + L to the close cross / next open cross. Events: EDGAR submissions JSON (acceptanceDateTime, items);
bars: Alpaca SIP raw 1-min per symbol-day (halt_reopen.py pattern); daily: Sharadar SEP.
usage: PYTHONPATH=. python3 -m research.sim.edgar_sess edgar | events | bars | run
"""
from __future__ import annotations

import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data/research/edgar_sess"
SUB = D / "submissions"
BD = D / "bars"
OUT = ROOT / "data/research/program/edgar_sess_out.txt"
SH = Path.home() / "data/sharadar"
ET = "America/New_York"
UA = {"User-Agent": "swing-trader research research@example.com"}
START, CHOOSE_END, END = "2019-01-01", "2022-12-31", "2026-10-05"
TYPES = {"T101": "1.01", "T201": "2.01", "T502": "5.02", "T103": "1.03", "T301": "3.01"}
FIX = {"T103": -1, "T301": -1, "T424": -1, "T25": -1, "TTO": 1}


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    with OUT.open("a") as f:
        f.write(s + "\n")


def universe() -> pd.DataFrame:
    t = pd.read_parquet(SH / "tickers.parquet")
    t = t[(t.table == "SEP") & t.category.str.startswith("Domestic Common", na=False)]
    t = t[pd.to_datetime(t.lastpricedate) >= START].copy()
    t["cik"] = t.secfilings.str.extract(r"CIK=(\d+)")[0]
    return t.dropna(subset=["cik"])[["ticker", "permaticker", "cik", "isdelisted"]]


def _get(url):
    for k in range(5):
        try:
            r = requests.get(url, headers=UA, timeout=30)
        except requests.RequestException:
            time.sleep(3 * (k + 1))
            continue
        if r.status_code == 200:
            return r.json()
        if r.status_code == 404:
            return None
        time.sleep(3 * (k + 1))
    return None


def edgar() -> None:
    """Download submissions JSON (recent + older pages back to 2019) per CIK."""
    SUB.mkdir(parents=True, exist_ok=True)
    ciks = sorted(set(universe().cik))
    print(len(ciks), "ciks", flush=True)
    from concurrent.futures import ThreadPoolExecutor

    def one(c):
        f = SUB / f"{c}.json"
        if f.exists():
            return
        j = _get(f"https://data.sec.gov/submissions/CIK{c}.json")
        time.sleep(0.6)
        if j is None:
            f.write_text("{}")
            return
        parts = [j["filings"]["recent"]]
        for p in j["filings"].get("files", []):
            if p.get("filingTo", "") >= START:
                q = _get(f"https://data.sec.gov/submissions/{p['name']}")
                time.sleep(0.6)
                if q:
                    parts.append(q)
        keep = {k: [] for k in ("form", "items", "acceptanceDateTime", "accessionNumber")}
        for p in parts:
            for k in keep:
                keep[k] += p.get(k, [])
        f.write_text(json.dumps(keep))

    with ThreadPoolExecutor(5) as ex:
        for i, _ in enumerate(ex.map(one, ciks)):
            if i % 500 == 0:
                print(f"  {i}/{len(ciks)}", flush=True)


def events() -> None:
    """In-session filings of the registered types, joined to ticker / ADV / price (Sharadar) on the event day."""
    u = universe()
    rows = []
    for c, g in u.groupby("cik"):
        f = SUB / f"{c}.json"
        if not f.exists():
            continue
        j = json.loads(f.read_text())
        if not j:
            continue
        x = pd.DataFrame(j)
        x["acc"] = pd.to_datetime(x.acceptanceDateTime, utc=True, errors="coerce").dt.tz_convert(ET)
        x = x[(x.acc >= pd.Timestamp(START, tz=ET)) & (x.acc <= pd.Timestamp(END, tz=ET) + pd.Timedelta(hours=23))]
        hm = x.acc.dt.hour * 60 + x.acc.dt.minute
        x = x[(hm >= 9 * 60 + 35) & (hm < 15 * 60 + 30) & (x.acc.dt.weekday < 5)]
        for r in x.itertuples():
            ty = []
            if r.form in ("8-K", "8-K/A") and r.form == "8-K":
                its = set(str(r.items).split(","))
                ty = [k for k, v in TYPES.items() if v in its]
            elif r.form in ("SC TO-I", "SC TO-T"):
                ty = ["TTO"]
            elif r.form in ("424B4", "424B5"):
                ty = ["T424"]
            elif r.form in ("25-NSE", "25"):
                ty = ["T25"]
            for t in ty:
                rows.append((c, r.accessionNumber, t, r.acc))
    e = pd.DataFrame(rows, columns=["cik", "acc_no", "type", "acc"]).drop_duplicates(["cik", "acc_no", "type"])
    e["date"] = e.acc.dt.tz_localize(None).dt.normalize()
    # map cik -> ticker valid on that date via Sharadar prices (a CIK can have several tickers over time)
    tick = u.groupby("cik").ticker.apply(list).to_dict()
    allt = sorted(set(u.ticker))
    sep = pd.read_parquet(SH / "stocks.parquet", columns=["ticker", "date", "open", "close", "closeunadj", "volume"],
                          filters=[("ticker", "in", allt), ("date", ">=", pd.Timestamp("2018-11-01").date())])
    sep["date"] = pd.to_datetime(sep.date)
    sep = sep.sort_values(["ticker", "date"])
    # SEP open/close are split-adjusted; minute bars are raw -> work in raw prices (closeunadj = official close print)
    f = sep.closeunadj / sep.close
    sep["open"] = sep.open * f
    sep["close"] = sep.closeunadj
    sep["dv"] = sep.close * sep.volume / f
    sep["adv"] = sep.groupby("ticker").dv.transform(lambda s: s.rolling(20).mean().shift(1))
    sep["nxo"] = sep.groupby("ticker").open.shift(-1)
    sep["pclose"] = sep.groupby("ticker").close.shift(1)
    key = sep.set_index(["ticker", "date"])[["close", "adv", "nxo", "pclose", "open"]]
    out = []
    for r in e.itertuples():
        for tk in tick.get(r.cik, []):
            if (tk, r.date) in key.index:
                v = key.loc[(tk, r.date)]
                out.append((r.cik, r.acc_no, r.type, r.acc, r.date, tk, v.close, v.adv, v.nxo, v.pclose, v.open))
                break
    ev = pd.DataFrame(out, columns=["cik", "acc_no", "type", "acc", "date", "ticker", "close", "adv", "nxo", "pclose", "open"])
    ev = ev[(ev.pclose >= 5) & (ev.adv >= 5e6)]
    ev["acc"] = ev.acc.astype(str)
    ev.to_parquet(D / "events.parquet")
    print(ev.groupby([ev.date.dt.year, "type"]).size().unstack(fill_value=0), flush=True)


def bars() -> None:
    """Alpaca SIP raw 1-min bars, one request (paged) per day for all of that day's event symbols."""
    from .auction_fetch import _env
    BD.mkdir(parents=True, exist_ok=True)
    H = _env()
    ev = pd.read_parquet(D / "events.parquet")
    need = {(s, d.date()) for s, d in zip(ev.ticker, ev.date)}
    todo = sorted(x for x in need if not (BD / f"{x[0]}_{x[1]}.parquet").exists())
    days = pd.Series([s for s, _ in todo]).groupby([d for _, d in todo]).apply(list)
    print(len(todo), "symbol-days on", len(days), "days", flush=True)
    for i, (day, syms) in enumerate(days.items()):
        got = {s: [] for s in syms}
        p = dict(symbols=",".join(syms), timeframe="1Min", start=f"{day}T13:00:00Z", end=f"{day}T21:30:00Z",
                 feed="sip", adjustment="raw", limit=10000)
        ok = True
        while True:
            r = None
            for k in range(5):
                try:
                    r = requests.get("https://data.alpaca.markets/v2/stocks/bars", headers=H, params=p, timeout=60)
                except requests.RequestException:
                    time.sleep(5 * (k + 1))
                    r = None
                    continue
                if r.status_code == 429:
                    time.sleep(3 * (k + 1))
                    continue
                break
            if r is None or r.status_code != 200:
                print("  fail", day, getattr(r, "status_code", None), flush=True)
                ok = False
                break
            j = r.json()
            for s, b in (j.get("bars") or {}).items():
                got.setdefault(s, []).extend(b or [])
            tok = j.get("next_page_token")
            if not tok:
                break
            p["page_token"] = tok
        if not ok:
            continue
        for s in syms:
            x = pd.DataFrame(got.get(s) or [])
            if x.empty:
                x = pd.DataFrame(columns=["t", "o", "h", "l", "c", "v"])
            x.to_parquet(BD / f"{s}_{day}.parquet")
        if i % 200 == 0:
            print(f"  {i}/{len(days)}", flush=True)
        time.sleep(0.2)


# ---------------------------------------------------------------- analysis
def _cost(adv):
    return np.where(adv >= 1e8, 5.0, np.where(adv >= 2e7, 10.0, 20.0))


def _load_bars(sym, day):
    f = BD / f"{sym}_{day.date()}.parquet"
    if not f.exists():
        return None
    x = pd.read_parquet(f)
    if x.empty:
        return None
    t = pd.to_datetime(x.t, utc=True).dt.tz_convert(ET)
    x["mos"] = t.dt.hour * 60 + t.dt.minute - 570
    x = x[(x.mos >= 0) & (x.mos < 390)]
    return x.set_index("mos")


def _px(b, m, col):
    """Price of minute m; if the minute has no trade, the last earlier close (for p0) / next later open (for entry)."""
    if m in b.index:
        return float(b.at[m, col])
    if col == "c":
        e = b[b.index < m]
        return float(e.c.iloc[-1]) if len(e) else np.nan
    e = b[b.index > m]
    return float(e.o.iloc[0]) if len(e) and e.index[0] <= m + 2 else np.nan


def panel() -> pd.DataFrame:
    ev = pd.read_parquet(D / "events.parquet")
    ev["acc"] = pd.to_datetime(ev.acc)
    rows = []
    cache = {}
    for r in ev.itertuples():
        k = (r.ticker, r.date)
        if k not in cache:
            cache[k] = _load_bars(r.ticker, r.date)
        b = cache[k]
        if b is None:
            continue
        m = r.acc.hour * 60 + r.acc.minute - 570
        p0 = _px(b, m - 1, "c")
        pm30 = _px(b, m - 30, "c")
        e = {L: _px(b, m + L, "o") for L in (1, 2, 5)}
        c1 = _px(b, m + 1, "c")
        vol = b.loc[(b.index >= m + 2) & (b.index <= m + 6)]
        dv5 = float((vol.c * vol.v).sum() / 5) if len(vol) else 0.0
        rows.append(dict(type=r.type, ticker=r.ticker, date=r.date, m=m, adv=r.adv, p0=p0, pm30=pm30, e1=e[1], e2=e[2], e5=e[5],
                         c1=c1, close=r.close, nxo=r.nxo, dv1=dv5, cik=r.cik, acc_no=r.acc_no))
    return pd.DataFrame(rows)


def nw_t_day(x, d):
    """t of the mean with day-clustered sums (events on the same day are one cluster)."""
    s = pd.Series(x).groupby(np.asarray(d)).sum()
    n = pd.Series(x).groupby(np.asarray(d)).size()
    mu = s.sum() / n.sum()
    res = (pd.Series(x) - mu).groupby(np.asarray(d)).sum()
    se = np.sqrt((res ** 2).sum()) / n.sum()
    return mu / se if se > 0 else np.nan


def trades(p, rule, L=2, exit_="EOD"):
    ent = p[f"e{L}"]
    pre = (ent / p.p0 - 1) * 1e4
    ex = p.close if exit_ == "EOD" else p.nxo
    post = (ex / ent - 1) * 1e4
    if rule == "CONT":
        sgn = np.sign(pre).where(pre.abs() >= 50, 0)
    elif rule == "REV":
        sgn = -np.sign(pre).where(pre.abs() >= 50, 0)
    else:
        sgn = p.type.map(FIX).fillna(0)
    g = sgn * post
    c = _cost(p.adv) * (2 if exit_ else 2)
    ok = (sgn != 0) & ent.notna() & ex.notna() & p.p0.notna()
    return pd.DataFrame({"gross": g[ok], "net": (g - c)[ok], "net2": (g - 2 * c)[ok], "date": p.date[ok], "type": p.type[ok],
                         "dv1": p.dv1[ok], "adv": p.adv[ok]})


def summ(t):
    if len(t) == 0:
        return dict(n=0)
    x = t.net.values
    srt = np.sort(x)
    return dict(n=len(x), gross=t.gross.mean(), net=x.mean(), t=nw_t_day(x, t.date.values), med=np.median(x), hit=(x > 0).mean(),
                ex5=srt[:-5].mean() if len(x) > 10 else np.nan, net2=t.net2.mean(), yrs=len(set(t.date.dt.year)))


def fmt(d):
    if d.get("n", 0) == 0:
        return "n 0"
    return (f"n {d['n']:5d} gross {d['gross']:+7.1f} net {d['net']:+7.1f} t {d['t']:+5.2f} med {d['med']:+6.1f} hit {d['hit']:.2f} "
            f"ex5 {d['ex5']:+6.1f} 2x {d['net2']:+7.1f}")


def run() -> None:
    OUT.write_text("")
    p = panel()
    p.to_parquet(D / "panel.parquet")
    p = p.dropna(subset=["p0", "e2"])
    bad = ((p.p0 / p.close - 1).abs() > 0.5) | ((p.nxo / p.close - 1).abs() > 0.5)
    log(f"dropped {int(bad.sum())} events whose minute price and official close/next open differ > 50% (ticker/split mismatch)")
    p = p[~bad]
    ch = p[p.date <= CHOOSE_END]
    ju = p[p.date > CHOOSE_END]
    log(f"EDGAR-SESS panel: {len(p)} events with bars (choose {len(ch)}, judge {len(ju)}); events/yr by type:")
    log((p.groupby([p.date.dt.year, "type"]).size().unstack(fill_value=0)).to_string())
    # diagnostics: move timing (all events, both periods)
    tot = (p.close / p.p0 - 1) * 1e4
    a1 = (p.c1 / p.p0 - 1) * 1e4
    a2 = (p.e2 / p.p0 - 1) * 1e4
    big = tot.abs() >= 100
    log("\nDiagnostics (not gates). Share of the m-1 -> close move already done by m+1 close / m+2 open, events with |move| >= 100bp:")
    for ty, g in p[big].groupby("type"):
        i = g.index
        sh1 = (np.sign(tot[i]) * a1[i] / tot[i].abs()).median()
        sh2 = (np.sign(tot[i]) * a2[i] / tot[i].abs()).median()
        sh2m = (np.sign(tot[i]) * a2[i]).sum() / tot[i].abs().sum()
        pre = (g.p0 / g.pm30 - 1) * 1e4
        log(f"  {ty:5s} n {len(g):5d}  median share done by m+1 {sh1:+.2f}, by m+2 open {sh2:+.2f} (bp-weighted {sh2m:+.2f}); median |m-1->close| "
            f"{tot[i].abs().median():.0f}bp; median |m-30->m-1| {pre.abs().median():.0f}bp vs all-event median "
            f"{((p.p0 / p.pm30 - 1) * 1e4).abs().median():.0f}bp")
    log("  all types: |m-1 -> m+2 open| median", f"{a2.abs().median():.0f}bp;", "share of events with |m-1->m+2| >= 50bp",
        f"{(a2.abs() >= 50).mean():.2f}")
    cells = []
    log("\nCHOOSE 2019-2022 (L=2), net of tier costs:")
    for ty in sorted(p.type.unique()):
        for rule in ("CONT", "REV", "FIX"):
            if rule == "FIX" and ty not in FIX:
                continue
            for ex in ("EOD", "NXO"):
                d = summ(trades(ch[ch.type == ty], rule, 2, ex))
                sel = d.get("n", 0) >= 30 and d["net"] > 0 and d["t"] >= 2
                cells.append((ty, rule, ex, sel))
                log(f"  {ty:5s} {rule:4s} {ex}: {fmt(d)}{'  SELECTED' if sel else ''}")
    n_grid = len(cells)
    sel = [c for c in cells if c[3]]
    log(f"\nGrid {n_grid} cells; selected {len(sel)}")
    log("\nJUDGE 2023-01..2026-10-05 (selected cells; L=2 primary, L=1/5 shown):")
    allj = []
    for ty, rule, ex, _ in sel:
        q = ju[ju.type == ty]
        t2 = trades(q, rule, 2, ex)
        allj.append(t2)
        d = summ(t2)
        d5 = summ(trades(q.dropna(subset=["e5"]), rule, 5, ex))
        d1 = summ(trades(q.dropna(subset=["e1"]), rule, 1, ex))
        h1 = summ(t2[t2.date <= "2024-12-31"])
        h2 = summ(t2[t2.date > "2024-12-31"])
        log(f"  {ty} {rule} {ex}: {fmt(d)}")
        log(f"     L=1 net {d1.get('net', np.nan):+.1f} | L=5 net {d5.get('net', np.nan):+.1f} | 2023-24 {h1.get('net', np.nan):+.1f} "
            f"(n {h1.get('n', 0)}) | 2025-26 {h2.get('net', np.nan):+.1f} (n {h2.get('n', 0)}) | median 1-min $vol at entry "
            f"${t2.dv1.median():,.0f}")
    if allj:
        a = pd.concat(allj)
        d = summ(a)
        yrs = (pd.Timestamp(END) - pd.Timestamp("2023-01-01")).days / 365.25
        log(f"\n  POOLED selected judge: {fmt(d)}; events/yr {len(a) / yrs:.0f}")
        # ceiling at $10k: events/yr x net x 50% deployed x 50% capture
        log(f"  ceiling-style %/yr at 50% deployed x 50% capture: {len(a) / yrs * d['net'] / 1e4 * 0.5 * 0.5 * 100:+.1f}pp")
    # unconditional CONT on all types pooled (descriptive, both periods)
    log("\nDescriptive (all types pooled, CONT, L=2): choose", fmt(summ(trades(ch, "CONT", 2, "EOD"))))
    log("                                               judge ", fmt(summ(trades(ju, "CONT", 2, "EOD"))))
    log("Descriptive (all types pooled, REV, L=2):  choose", fmt(summ(trades(ch, "REV", 2, "EOD"))))
    log("                                               judge ", fmt(summ(trades(ju, "REV", 2, "EOD"))))


if __name__ == "__main__":
    {"edgar": edgar, "events": events, "bars": bars, "run": run}[sys.argv[1]]()
