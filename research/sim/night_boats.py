"""Study NIGHT-BOATS (round1_prose.md "## Amendment - Study NIGHT-BOATS", N 1066): do the night leg's picks (bought at the close
cross) print above the next 09:30 open cross in the 20:00-04:00 Blue Ocean (BOATS) overnight session, and is there volume at $2-25k?
EXIT read on a live leg. usage: PYTHONPATH=. .venv/bin/python -m research.sim.night_boats fetch|run
  fetch: Sharadar daily-bar proxy picks (day_ret <= -8%, IBS < 0.10, prev closeunadj >= $5, $ADV20 >= $10M, domestic common) for nights
         2024-09-16..2026-09-30 plus the live decision logs (scratchpad copies of logs/daily-decisions*.jsonl); Alpaca BOATS minute bars
         per night (20:00 ET of the evening before the exit date .. 04:00 ET of the exit date; DST via zoneinfo), cached per night to
         data/research/night_boats/{exit_date}.parquet. AAPL+SPY ride along in every night's request as a venue-liveness control.
  run:   reads A-D vs the opening cross, capacity, coverage, live-pick table (not judged), verdict vs the registered bars."""
from __future__ import annotations
import datetime as dt
import json
import os
import sys
import time
import warnings
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
SH = Path.home() / "data/sharadar"
CACHE = ROOT / "data/research/night_boats"
OUT = ROOT / "data/research/program/night_boats_out.txt"
ET = ZoneInfo("America/New_York")
START, END = "2024-09-16", "2026-09-30"           # pick nights (registered)
H1_END = "2025-09-30"                               # halves: 2024-09..2025-09 / 2025-10..2026-09
CONTROL = ["AAPL", "SPY"]
LIVE_DIR = Path(os.environ.get("NIGHT_BOATS_LIVE_DIR", "/private/tmp/claude-501/-Users-andrewlau-Documents-Code-Projects-swing-trader/"
                                                      "63b38356-9810-4c15-a1fe-4de065e66488/scratchpad/live"))
KS = (0.01, 0.02, 0.03)


def log(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True)
    with OUT.open("a") as f: f.write(s + "\n")


def clus_t(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else float("nan")


def nstats(s: pd.Series) -> str:
    """per-night series (already EW within the night)."""
    x = s.dropna().to_numpy(float)
    if len(x) < 3: return f"n {len(x)}"
    top = np.sort(x)[-5:].sum()
    return (f"nights {len(x)} mean {x.mean():+.1f} med {np.median(x):+.1f} hit {np.mean(x > 0):.2f} t {clus_t(x):.2f} "
            f"ex-top5 {(x.sum() - top) / (len(x) - 5):+.1f}")


# ----------------------------------------------------------------------------------------------------------------- picks
def calendar() -> pd.DatetimeIndex:
    spy = pd.read_parquet(SH / "funds.parquet", columns=["date"], filters=[("ticker", "==", "SPY")])
    return pd.DatetimeIndex(sorted(pd.to_datetime(spy.date).unique()))


def proxy_picks() -> pd.DataFrame:
    tk = pd.read_parquet(SH / "tickers.parquet", columns=["table", "ticker", "category"])
    ok = set(tk[(tk.table == "SEP") & tk.category.fillna("").str.startswith("Domestic Common Stock")].ticker)
    st = pd.read_parquet(SH / "stocks.parquet", columns=["ticker", "date", "open", "high", "low", "close", "closeunadj", "volume"],
                         filters=[("date", ">=", dt.date(2024, 7, 1))])
    st = st[st.ticker.isin(ok)]; st["date"] = pd.to_datetime(st.date)
    st = st.sort_values(["ticker", "date"]); g = st.groupby("ticker")
    st["pc"] = g.close.shift(1); st["pcu"] = g.closeunadj.shift(1)
    st["adv"] = (st.closeunadj * st.volume).groupby(st.ticker).transform(lambda x: x.shift(1).rolling(20, min_periods=15).median())
    st["dr"] = st.close / st.pc - 1
    st["ibs"] = (st.close - st.low) / (st.high - st.low).replace(0, np.nan)
    fac = st.closeunadj / st.close                                   # unadjusted scale (BOATS prices are unadjusted)
    st["open_u_next"] = (g.open.shift(-1) * fac.groupby(st.ticker).shift(-1)).round(4)
    st["next_date"] = g.date.shift(-1)
    p = st[(st.dr <= -0.08) & (st.ibs < 0.10) & (st.pcu >= 5) & (st.adv >= 1e7) & (st.date >= START) & (st.date <= END)
           & st.open_u_next.notna()].copy()
    cal = calendar()
    p["exit_date"] = [cal[cal > d][0] for d in p.date]
    skipped = p[p.next_date != p.exit_date]
    p = p[p.next_date == p.exit_date]
    p = p.rename(columns={"closeunadj": "close_u"})[["date", "ticker", "exit_date", "close_u", "open_u_next", "dr", "ibs", "adv"]]
    p["src"] = "proxy"
    return p.reset_index(drop=True), len(skipped)


def live_picks() -> pd.DataFrame:
    rows = []
    for f, acct in [("daily-decisions-live.jsonl", "live"), ("daily-decisions-roth.jsonl", "roth"), ("daily-decisions.jsonl", "paper")]:
        pth = LIVE_DIR / f
        if not pth.exists(): continue
        for line in pth.read_text().splitlines():
            if line.strip():
                r = json.loads(line); rows.append(dict(date=pd.Timestamp(r["date"]), ticker=r["sym"], acct=acct, px1540=r["price"]))
    if not rows: return pd.DataFrame()
    d = pd.DataFrame(rows)
    d = d.groupby(["date", "ticker"]).agg(acct=("acct", lambda s: "+".join(sorted(set(s)))), px1540=("px1540", "first")).reset_index()
    cal = calendar()
    # calendar beyond Sharadar's last date: weekdays (holidays after that date are not in any file on disk; disclosed)
    ext = pd.bdate_range(cal[-1] + pd.Timedelta(days=1), pd.Timestamp.today() + pd.Timedelta(days=5))
    cal = cal.append(ext)
    d["exit_date"] = [cal[cal > x][0] for x in d.date]
    # close cross and next open, unadjusted, from Alpaca SIP daily (raw)
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    c = client()
    syms = sorted(d.ticker.unique())
    df = c.get_stock_bars(StockBarsRequest(symbol_or_symbols=syms, timeframe=TimeFrame.Day, start=d.date.min() - pd.Timedelta(days=3),
                                           end=pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=16), feed="sip", adjustment="raw")).df
    df = df.reset_index(); df["day"] = pd.to_datetime(df.timestamp).dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    cl = df.set_index(["symbol", "day"]).close; op = df.set_index(["symbol", "day"]).open
    d["close_u"] = [cl.get((t, x), np.nan) for t, x in zip(d.ticker, d.date)]
    d["open_u_next"] = [op.get((t, x), np.nan) for t, x in zip(d.ticker, d.exit_date)]
    d["src"] = "live"
    return d


# ----------------------------------------------------------------------------------------------------------------- fetch
def client():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    from alpaca.data.historical import StockHistoricalDataClient
    k = os.environ.get("ALPACA_API_KEY") or next(os.environ[e] for e in os.environ if "ALPACA" in e and "KEY" in e and "SECRET" not in e)
    s = os.environ.get("ALPACA_SECRET_KEY") or next(os.environ[e] for e in os.environ if "ALPACA" in e and "SECRET" in e)
    return StockHistoricalDataClient(k, s)


def window(exit_date: pd.Timestamp) -> tuple[dt.datetime, dt.datetime]:
    """20:00 ET the evening before the exit date .. 04:00 ET on the exit date, as UTC (DST by zoneinfo)."""
    e = exit_date.to_pydatetime().date()
    lo = dt.datetime.combine(e - dt.timedelta(days=1), dt.time(20, 0), tzinfo=ET)
    hi = dt.datetime.combine(e, dt.time(4, 0), tzinfo=ET)
    return lo.astimezone(dt.timezone.utc), hi.astimezone(dt.timezone.utc)


EMPTY = pd.DataFrame({"symbol": pd.Series(dtype=str), "timestamp": pd.Series(dtype="datetime64[ns, UTC]"),
                      **{c: pd.Series(dtype=float) for c in ["open", "high", "low", "close", "volume", "trade_count", "vwap"]}})


def fetch(picks: pd.DataFrame):
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from alpaca.data.enums import DataFeed
    CACHE.mkdir(parents=True, exist_ok=True)
    c = client(); n_req = 0; t0 = time.time()
    nights = picks.groupby("exit_date").ticker.apply(lambda s: sorted(set(s)))
    for ex, syms in nights.items():
        f = CACHE / f"{ex.date()}.parquet"
        if f.exists(): continue
        lo, hi = window(ex)
        syms = sorted(set(syms) | set(CONTROL))
        df = None
        for attempt in range(8):
            try:
                r = c.get_stock_bars(StockBarsRequest(symbol_or_symbols=syms, timeframe=TimeFrame.Minute, start=lo, end=hi, feed=DataFeed.BOATS))
                df = r.df.reset_index() if len(r.data) else EMPTY.copy()
                break
            except Exception as e:                           # noqa: BLE001
                msg = str(e)
                if "too many requests" in msg.lower() or "429" in msg:
                    time.sleep(10 * (attempt + 1)); continue
                if "invalid symbol" in msg:                  # Alpaca rejects the whole batch for one unknown ticker (e.g. WOLF2): drop it
                    bad = msg.split("invalid symbol:")[1].strip(' "}\n')
                    print(f"{ex.date()} dropping unknown symbol {bad}"); syms = [s for s in syms if s != bad]
                    if not syms: df = EMPTY.copy(); break
                    continue
                print(f"{ex.date()} ERR {msg[:200]}"); break
        if df is None: continue
        df = df[(df.timestamp >= lo) & (df.timestamp < hi)] if len(df) else df
        df.to_parquet(f, index=False)
        n_req += 1
        if n_req % 50 == 0: print(f"  {n_req} nights fetched ({time.time() - t0:.0f}s), last {ex.date()} rows {len(df)}", flush=True)
        time.sleep(0.35)                                     # ~170 req/min, under the 200/min plan limit
    print(f"fetch done: {n_req} new nights, {len(nights)} total")


# ------------------------------------------------------------------------------------------------------------------- run
def summarise(picks: pd.DataFrame) -> pd.DataFrame:
    """One row per pick with the overnight aggregates joined from the per-night cache."""
    rows = []
    bars_by_night = {}
    for ex in sorted(picks.exit_date.unique()):
        f = CACHE / f"{pd.Timestamp(ex).date()}.parquet"
        bars_by_night[ex] = pd.read_parquet(f) if f.exists() else None
    for i, p in picks.iterrows():
        b = bars_by_night.get(p.exit_date)
        rec = dict(idx=i, cached=b is not None, venue_live=False, n_bars=0, n_trades=0, dvol=0.0, vwap=np.nan, last=np.nan, high=np.nan,
                   first_t=pd.NaT, last_t=pd.NaT)
        if b is not None and len(b):
            rec["venue_live"] = bool(b.symbol.isin(CONTROL).any())
            s = b[b.symbol == p.ticker].sort_values("timestamp")
            if len(s):
                vol = s.volume.to_numpy(float); vw = s.vwap.fillna(s.close).to_numpy(float)
                rec.update(n_bars=len(s), n_trades=int(np.nansum(s.trade_count)) if "trade_count" in s else len(s),
                           dvol=float((vol * vw).sum()), vwap=float((vol * vw).sum() / vol.sum()) if vol.sum() > 0 else float(s.close.mean()),
                           last=float(s.close.iloc[-1]), high=float(s.high.max()),
                           first_t=pd.Timestamp(s.timestamp.iloc[0]).tz_convert(ET), last_t=pd.Timestamp(s.timestamp.iloc[-1]).tz_convert(ET))
        rows.append(rec)
    a = pd.DataFrame(rows).set_index("idx")
    d = picks.join(a)
    d["printed"] = d.n_bars > 0
    d["on_bp"] = (d.open_u_next / d.close_u - 1) * 1e4                  # live baseline: close cross -> open cross
    d["A_bp"] = (d.vwap / d.open_u_next - 1) * 1e4                      # overnight VWAP vs open cross
    d["B_bp"] = (d["last"] / d.open_u_next - 1) * 1e4                   # last overnight print vs open cross
    d["A_vs_close_bp"] = (d.vwap / d.close_u - 1) * 1e4
    for k in KS:
        lvl = d.close_u * (1 + k)
        filled = d.printed & (d.high > lvl + 0.01)
        d[f"fill{int(k*100)}"] = filled
        exit_px = np.where(filled, lvl, d.open_u_next)
        d[f"D{int(k*100)}_bp"] = (exit_px / d.close_u - 1) * 1e4 - d.on_bp   # improvement over exit-at-open, same pick
    return d


def nightly(d: pd.DataFrame, col: str) -> pd.Series:
    return d.groupby("exit_date")[col].mean()


def run():
    if OUT.exists(): OUT.unlink()
    picks = pd.read_parquet(CACHE / "picks.parquet"); picks["date"] = pd.to_datetime(picks.date); picks["exit_date"] = pd.to_datetime(picks.exit_date)
    live = pd.read_parquet(CACHE / "live_picks.parquet") if (CACHE / "live_picks.parquet").exists() else pd.DataFrame()
    d = summarise(picks)
    log(f"NIGHT-BOATS (N 1066): proxy picks {len(d):,} on {d.exit_date.nunique():,} nights {d.date.min().date()}..{d.date.max().date()} "
        f"(rule: day_ret<=-8%, IBS<0.10, prev closeunadj>=$5, $ADV20>=$10M median, domestic common; Sharadar); "
        f"nights cached {d.cached.sum():,}/{len(d):,} picks; BOATS venue live (AAPL/SPY printed) on {d.groupby('exit_date').venue_live.first().sum():,} "
        f"of {d.exit_date.nunique():,} nights")
    dark = d.groupby("exit_date").venue_live.first(); dark = dark[~dark]
    if len(dark): log(f"  venue-dark nights (no AAPL/SPY BOATS bar; coverage gap or outage): {', '.join(str(x.date()) for x in dark.index)}")
    log(f"  baseline close->open cross (live exit), per pick: mean {d.on_bp.mean():+.0f}bp med {d.on_bp.median():+.0f} ; per night {nstats(nightly(d, 'on_bp'))}")

    # ---- C: coverage / capacity
    log("\n=== C. coverage and capacity")
    pr = d[d.printed]
    log(f"  picks with any BOATS print: {d.printed.mean():.1%} ({d.printed.sum():,}/{len(d):,}); nights with >=1 printed pick: "
        f"{(d.groupby('exit_date').printed.any()).mean():.1%}; per-night share of picks printed (mean) {d.groupby('exit_date').printed.mean().mean():.1%}")
    for thr in (1e3, 5e3, 25e3, 1e5):
        log(f"  picks with overnight $vol >= ${thr:,.0f}: {(d.dvol >= thr).mean():.1%}; nights with >=1 such pick {(d.groupby('exit_date').dvol.max() >= thr).mean():.1%}")
    q = pr.dvol.quantile([.1, .25, .5, .75, .9])
    log(f"  overnight $vol per printed pick: p10 ${q[.1]:,.0f} p25 ${q[.25]:,.0f} med ${q[.5]:,.0f} p75 ${q[.75]:,.0f} p90 ${q[.9]:,.0f}; "
        f"all picks (zeros in): med ${d.dvol.median():,.0f} p75 ${d.dvol.quantile(.75):,.0f}")
    log(f"  prints per printed pick: med {pr.n_trades.median():.0f} trades / {pr.n_bars.median():.0f} minute bars; "
        f"share of ADV: med {(pr.dvol / pr.adv).median()*100:.3f}% p75 {(pr.dvol / pr.adv).quantile(.75)*100:.3f}%")
    ft = pr.first_t.dropna()
    hrs = ft.apply(lambda t: (t.hour - 20) % 24 + t.minute / 60)       # hours after 20:00 ET
    log(f"  first print (hours after 20:00 ET): p10 {hrs.quantile(.1):.1f} p25 {hrs.quantile(.25):.1f} med {hrs.median():.1f} p75 {hrs.quantile(.75):.1f}; "
        f"by hour ET: " + ", ".join(f"{h:02d}h {n}" for h, n in ft.apply(lambda t: t.hour).value_counts().sort_index().items()))
    lt = pr.last_t.dropna().apply(lambda t: (t.hour - 20) % 24 + t.minute / 60)
    log(f"  last print (hours after 20:00 ET): p25 {lt.quantile(.25):.1f} med {lt.median():.1f} p75 {lt.quantile(.75):.1f}")
    m = d.assign(m=d.date.dt.to_period("M")).groupby("m").agg(picks=("ticker", "size"), printed=("printed", "sum"), nights=("exit_date", "nunique"),
                                                               med_dvol=("dvol", "median"))
    log("  per month: picks / printed / nights / median $vol:\n    " + "\n    ".join(
        f"{i} {int(r.picks):3d} / {int(r.printed):3d} / {int(r.nights):2d} / ${r.med_dvol:,.0f}" for i, r in m.iterrows()))
    by_adv = d.assign(b=pd.cut(d.adv, [0, 2.5e7, 1e8, 5e8, np.inf], labels=["10-25M", "25-100M", "100-500M", ">500M"])).groupby("b")
    log("  by $ADV20: " + "; ".join(f"{b}: n {len(g)} printed {g.printed.mean():.0%} med $vol ${g.dvol.median():,.0f}" for b, g in by_adv))

    # ---- A, B
    log("\n=== A. overnight VWAP vs open cross (bp; printed picks only); B. last overnight print vs open cross")
    for col, nm in [("A_bp", "A vwap-open"), ("B_bp", "B last-open")]:
        x = pr[col].dropna()
        log(f"  {nm}: per pick n {len(x)} mean {x.mean():+.1f} med {x.median():+.1f} hit {(x > 0).mean():.2f}; per night {nstats(nightly(pr, col))}")
    x = pr.A_vs_close_bp
    log(f"  context: overnight VWAP vs CLOSE cross per pick mean {x.mean():+.0f} med {x.median():+.0f}; open cross vs close on the same picks "
        f"mean {pr.on_bp.mean():+.0f} med {pr.on_bp.median():+.0f} (unprinted picks: {d[~d.printed].on_bp.mean():+.0f} / {d[~d.printed].on_bp.median():+.0f})")
    w = pr[pr.dvol >= 5e3]
    log(f"  A on picks with $vol >= $5k: n {len(w)} mean {w.A_bp.mean():+.1f} med {w.A_bp.median():+.1f}; per night {nstats(nightly(w, 'A_bp'))}")

    # ---- D
    log("\n=== D. passive offer at close x (1+k), filled if any overnight minute high > level + $0.01, else exit at open; improvement vs exit-at-open, same nights")
    for k in KS:
        kk = int(k * 100); col = f"D{kk}_bp"; fc = f"fill{kk}"
        pn = nightly(d, col)
        log(f"  k={kk}%: fill rate per pick {d[fc].mean():.1%} (of printed {pr[fc].mean():.1%}); per pick improvement mean {d[col].mean():+.1f} "
            f"med {d[col].median():+.1f}; filled picks only: open-cross ret on them mean {d[d[fc]].on_bp.mean():+.0f}bp (fill at {kk*100:+d}bp)")
        log(f"    per night (EW over all picks, unfilled = 0): {nstats(pn)}")
        log(f"    halves: H1 {nstats(pn[pn.index <= H1_END])} | H2 {nstats(pn[pn.index > H1_END])}")
        log(f"    per night, nights with >=1 printed pick only: {nstats(nightly(d[d.groupby('exit_date').printed.transform('any')], col))}")
    # gates (k = 1% primary)
    pn = nightly(d, "D1_bp"); x = pn.dropna().to_numpy(float)
    g = dict(mean15=x.mean() >= 15, t2=clus_t(x) >= 2, median=np.median(x) > 0, h1=pn[pn.index <= H1_END].mean() > 0,
             h2=pn[pn.index > H1_END].mean() > 0, extop5=(x.sum() - np.sort(x)[-5:].sum()) / (len(x) - 5) > 0,
             C50=(d.groupby("exit_date").printed.any()).mean() >= 0.5)
    weak = 8 <= x.mean() < 15 and clus_t(x) >= 2
    verdict = "PASS" if all(g.values()) else ("WEAK" if weak else "KILL")
    log(f"\n  GATES (D, k=1%): {g} -> {verdict}")
    if verdict == "KILL":
        log("  KILL statement: the night leg's picks do not print materially above the next open cross in the Blue Ocean session, or do so on too few nights to matter.")
    # sizes: what a $2.3k / $10k / $25k night book could sell overnight at the printed $ volume (per-pick, 25% participation)
    for eq in (2300, 10000, 25000):
        per_pick = eq * 0.5 / max(1.0, d.groupby("exit_date").size().median())   # night leg ~50% of equity, EW over the night's picks
        cap = (pr.dvol * 0.25 >= per_pick).mean()
        log(f"  capacity: ${eq:,} book, ~${per_pick:,.0f} per pick: {cap:.0%} of printed picks have 4x that in overnight $vol (25% participation); "
            f"{(d.dvol * 0.25 >= per_pick).mean():.0%} of all picks")

    # ---- what the data volunteered (not gates)
    log("\n=== data volunteered (not gates)")
    top = pn.sort_values().tail(5)
    log("  top-5 D1 nights (carry the mean): " + "; ".join(
        f"{ex.date()} {'/'.join(d[d.exit_date == ex].ticker)} D1 {v:+.0f} open-cross {d[d.exit_date == ex].on_bp.mean():+.0f}bp" for ex, v in top.items()))
    log(f"  D1 per printed pick: mean {pr.D1_bp.mean():+.1f} med {pr.D1_bp.median():+.1f} better {(pr.D1_bp > 0).mean():.2f} worse {(pr.D1_bp < 0).mean():.2f}; "
        f"filled-at-1% picks whose open cross was above +1% anyway: {(d[d.fill1].on_bp > 100).mean():.0%}")
    log(f"  printed share by half: H1 {d[d.date <= H1_END].printed.mean():.0%} H2 {d[d.date > H1_END].printed.mean():.0%}; by weekday of pick (Mon..Fri): "
        + " ".join(f"{v:.0%}" for v in d.groupby(d.date.dt.dayofweek).printed.mean()))
    log(f"  A per night by year: " + "; ".join(f"{y} mean {g.mean():+.0f} med {g.median():+.0f} n {len(g)}" for y, g in nightly(pr, 'A_bp').groupby(lambda x: x.year)))
    log(f"  bad-print check, overnight high / close cross on printed picks: p99 {(pr.high / pr.close_u).quantile(.99):.3f} p99.9 {(pr.high / pr.close_u).quantile(.999):.3f} max {(pr.high / pr.close_u).max():.3f}")
    gaps = []
    for ex in sorted(set(d.exit_date.unique()) | set(pd.to_datetime(live.exit_date).unique() if len(live) else [])):
        f = CACHE / f"{pd.Timestamp(ex).date()}.parquet"
        if not f.exists(): continue
        b = pd.read_parquet(f); c = b[b.symbol.isin(CONTROL)].timestamp.sort_values()
        if len(c) and c.diff().max() >= pd.Timedelta(hours=2): gaps.append(f"{pd.Timestamp(ex).date()} ({c.diff().max().total_seconds()/3600:.1f}h)")
    log(f"  partial venue gaps (>= 2h with no AAPL/SPY bar inside the session, proxy + live nights): {len(gaps)} nights: {', '.join(gaps) if gaps else 'none'}")

    # ---- live picks (not judged)
    if len(live):
        live["date"] = pd.to_datetime(live.date); live["exit_date"] = pd.to_datetime(live.exit_date)
        L = summarise(live)
        log(f"\n=== LIVE picks (server decisions logs, {L.date.min().date()}..{L.date.max().date()}, {len(L)} picks, accounts live/roth/paper; NOT judged)")
        log(f"  printed {L.printed.mean():.0%}; venue-dark nights: {', '.join(str(x.date()) for x, v in L.groupby('exit_date').venue_live.first().items() if not v) or 'none'}")
        log(f"  per pick: open-cross ret mean {L.on_bp.mean():+.0f} med {L.on_bp.median():+.0f}; A mean {L.A_bp.mean():+.0f} med {L.A_bp.median():+.0f}; "
            f"D1 improvement mean {L.D1_bp.mean():+.0f} med {L.D1_bp.median():+.0f} fill {L.fill1.mean():.0%}; med $vol ${L.dvol.median():,.0f}")
        log("  date       sym    acct        close   open_nxt  on_bp  prints   $vol    vwap-open  last-open  fill1 fill2 fill3  first_print")
        for _, r in L.sort_values(["date", "ticker"]).iterrows():
            log(f"  {r.date.date()} {r.ticker:<6} {r.acct:<11} {r.close_u:8.2f} {r.open_u_next:8.2f} {r.on_bp:+6.0f} {r.n_trades:6d} {r.dvol:9,.0f} "
                f"{r.A_bp:+9.0f} {r.B_bp:+9.0f}   {'Y' if r.fill1 else '.'}     {'Y' if r.fill2 else '.'}     {'Y' if r.fill3 else '.'}   "
                f"{r.first_t.strftime('%H:%M') if pd.notna(r.first_t) else '-'}")
    log("\nDisclosed: picks = Sharadar daily-bar proxy of the live rule (not the live 15:40 screen); close cross = Sharadar closeunadj, open cross = "
        "Sharadar next-day open rescaled to unadjusted (closeunadj/close); BOATS bars are unadjusted; overnight window = 20:00 ET of the evening "
        "before the exit date to 04:00 ET of the exit date (Friday picks -> Sunday-night session); no costs on the overnight side; per-night EW; "
        "t = per-night. Live-pick closes/opens from Alpaca SIP daily (raw).")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "run"
    if mode == "fetch":
        CACHE.mkdir(parents=True, exist_ok=True)
        if not (CACHE / "picks.parquet").exists():
            p, skipped = proxy_picks(); p.to_parquet(CACHE / "picks.parquet", index=False)
            print(f"proxy picks {len(p)} on {p.exit_date.nunique()} nights; skipped (ticker's next bar != calendar next day) {skipped}")
        p = pd.read_parquet(CACHE / "picks.parquet")
        if not (CACHE / "live_picks.parquet").exists():
            lv = live_picks()
            if len(lv): lv.to_parquet(CACHE / "live_picks.parquet", index=False); print(f"live picks {len(lv)}")
        lv = pd.read_parquet(CACHE / "live_picks.parquet") if (CACHE / "live_picks.parquet").exists() else pd.DataFrame()
        allp = pd.concat([p[["exit_date", "ticker"]], lv[["exit_date", "ticker"]] if len(lv) else None])
        allp["exit_date"] = pd.to_datetime(allp.exit_date)
        fetch(allp)
    else:
        run()


if __name__ == "__main__":
    main()
