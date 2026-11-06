"""Studies BOATS-PREM (N 1088) and BOATS-LETF (N 1089), round1_prose.md "## Amendment - Overnight-session structure".

BOATS-PREM: does the Blue Ocean (BOATS) bid at 23:00 ET (Korean midday) in Asian-retail favourites beat the next 09:30 open cross,
            more than in low-Asian-interest controls, and does close cross -> BOATS bid earn a hedged excess?
BOATS-LETF: when an LETF's BOATS ask sits >= 15bp below L x its underlying's BOATS move since the close, does buying it and selling
            at the open cross earn the convergence?
usage: PYTHONPATH=. python3 -m research.sim.boats_asia fetch|run
Data: Alpaca official auctions (SIP), BOATS NBBO quotes (feed=boats), SIP daily bars (beta). Cache data/research/boats_asia/."""
from __future__ import annotations
import datetime as dt
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd
from swingtrader.daily.ovn_235_recorder import _headers, _get, Q_URL, B_URL, AU_URL

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data/research/boats_asia"
OUT = ROOT / "data/research/program/boats_asia_out.txt"
ET = ZoneInfo("America/New_York")
START, END, H1_END = "2024-09-16", "2026-10-30", "2025-09-30"
ASIA = "TSLA NVDA PLTR AAPL MSFT GOOGL AMZN META AMD MSTR IONQ TQQQ SOXL TSLL NVDL QQQ SPY SQQQ SOXS".split()
CONTROL = "JPM XOM JNJ PG KO WMT V UNH HD PEP".split()
PAIRS = [("TQQQ", "QQQ", 3), ("SQQQ", "QQQ", -3), ("QLD", "QQQ", 2), ("UPRO", "SPY", 3), ("SPXL", "SPY", 3), ("SOXL", "SOXX", 3),
         ("SOXS", "SOXX", -3), ("TNA", "IWM", 3), ("TSLL", "TSLA", 2), ("NVDL", "NVDA", 2)]
SYMS = sorted(set(ASIA) | set(CONTROL) | {s for p in PAIRS for s in p[:2]})
TIMES = {"2300": (23, 0, 0), "0345": (3, 45, 1)}     # (hour, minute, day offset from evening E); 2300 registered, 0345 report-only
X_LETF = 15e-4


def log(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True)
    with OUT.open("a") as f: f.write(s + "\n")


def paged(url, q, key, H):
    rows, tok = {}, None
    while True:
        j = _get(url, dict(q, **({"page_token": tok} if tok else {})), H)
        for s, v in (j.get(key) or {}).items(): rows.setdefault(s, []).extend(v)
        tok = j.get("next_page_token")
        if not tok: return rows


# --------------------------------------------------------------------------------------------------------------------- fetch
def fetch():
    CACHE.mkdir(parents=True, exist_ok=True); H = _headers()
    fd = CACHE / "daily.json"
    if not fd.exists():
        rows = {}
        for i in range(0, len(SYMS), 20):
            rows.update(paged(B_URL, dict(symbols=",".join(SYMS[i:i + 20]), timeframe="1Day", start="2024-05-01", end=END,
                                          feed="sip", adjustment="all", limit=10000), "bars", H))
        json.dump(rows, open(fd, "w")); print("daily bars", {k: len(v) for k, v in rows.items()})
    fa = CACHE / "auctions.json"
    if not fa.exists():
        rows = {}
        for s in SYMS:                                             # per symbol: the endpoint pages by symbol
            rows.update(paged(AU_URL, dict(symbols=s, start=START, end="2026-11-02", feed="sip", limit=10000), "auctions", H))
        json.dump(rows, open(fa, "w")); print("auctions", {k: len(v) for k, v in rows.items()})
    cal = calendar()
    (CACHE / "q").mkdir(exist_ok=True)
    todo = []
    for d, n in zip(cal[:-1], cal[1:]):
        E = (n - pd.Timedelta(days=1)).date()
        for k, (h, m, off) in TIMES.items():
            f = CACHE / "q" / f"{n.date()}_{k}.json"
            if not f.exists(): todo.append((f, dt.datetime.combine(E + dt.timedelta(days=off), dt.time(h, m), tzinfo=ET)))
    print(f"quote windows to fetch: {len(todo)}")

    def one(a):
        f, T = a
        rows = paged(Q_URL, dict(symbols=",".join(SYMS), start=(T - dt.timedelta(seconds=60)).isoformat(), end=T.isoformat(),
                                 feed="boats", limit=10000), "quotes", H)
        json.dump({s: v[-1] for s, v in rows.items() if v}, open(f, "w"))   # last quote per symbol before T
    t0 = time.time()
    with ThreadPoolExecutor(3) as ex:
        for j, _ in enumerate(ex.map(one, todo)):
            if j % 100 == 0: print(f"  {j}/{len(todo)} {time.time() - t0:.0f}s", flush=True)


def calendar() -> list[pd.Timestamp]:
    d = json.load(open(CACHE / "daily.json"))["SPY"]
    c = sorted(pd.Timestamp(x["t"]).tz_convert(ET).normalize().tz_localize(None) for x in d)
    return [x for x in c if pd.Timestamp(START) <= x <= pd.Timestamp(END)]


# ----------------------------------------------------------------------------------------------------------------------- run
def crosses() -> tuple[pd.DataFrame, pd.DataFrame]:
    """official open / close cross per (date, sym): largest-size print stamped on that ET date (repo max-by-size rule)."""
    a = json.load(open(CACHE / "auctions.json")); o, c = {}, {}
    for s, days in a.items():
        for x in days:
            d = x["d"]
            for side, tgt in (("o", o), ("c", c)):
                lst = [(q.get("s", 0), q["p"]) for q in (x.get(side) or [])
                       if pd.Timestamp(q["t"]).tz_convert(ET).strftime("%Y-%m-%d") == d]
                if lst: tgt[(pd.Timestamp(d), s)] = max(lst)[1]
    f = lambda m: pd.Series(m).unstack()
    return f(o), f(c)


def daily_close() -> pd.DataFrame:
    d = json.load(open(CACHE / "daily.json"))
    return pd.DataFrame({s: pd.Series({pd.Timestamp(x["t"]).tz_convert(ET).normalize().tz_localize(None): x["c"] for x in v})
                         for s, v in d.items()}).sort_index()


def quotes(key: str, cal) -> tuple[pd.DataFrame, pd.DataFrame]:
    b, a = {}, {}
    for d, n in zip(cal[:-1], cal[1:]):
        f = CACHE / "q" / f"{n.date()}_{key}.json"
        if not f.exists(): continue
        for s, q in json.load(open(f)).items():
            bp, ap = q.get("bp") or 0, q.get("ap") or 0
            if bp > 0 and ap > bp and (ap - bp) / ((ap + bp) / 2) < 0.02: b[(d, s)] = bp; a[(d, s)] = ap
    f = lambda m: pd.Series(m, dtype=float).unstack() if m else pd.DataFrame()
    return f(b), f(a)


def nw_t(x, lag=5):
    x = np.asarray(x, float); x = x[np.isfinite(x)]; n = len(x)
    if n < 10: return float("nan")
    e = x - x.mean(); v = e @ e / n
    for k in range(1, lag + 1): v += 2 * (1 - k / (lag + 1)) * (e[k:] @ e[:-k]) / n
    return x.mean() / np.sqrt(v / n)


def stats(s: pd.Series, lab: str):
    x = s.dropna(); h1 = x[x.index <= H1_END]; h2 = x[x.index > H1_END]
    top = np.sort(x.to_numpy())[-5:].sum()
    log(f"  {lab:<34} n {len(x):4d} mean {x.mean():+7.1f} med {x.median():+7.1f} hit {(x > 0).mean():.2f} NWt {nw_t(x):+5.2f} "
        f"ex-top5 {(x.sum() - top) / max(len(x) - 5, 1):+7.1f} | H1 {h1.mean():+6.1f} H2 {h2.mean():+6.1f}")
    return dict(n=len(x), mean=x.mean(), med=x.median(), t=nw_t(x), ex5=(x.sum() - top) / max(len(x) - 5, 1), h1=h1.mean(), h2=h2.mean())


def run():
    OUT.write_text(f"BOATS-PREM (N 1088) / BOATS-LETF (N 1089) run {dt.datetime.now():%Y-%m-%d %H:%M}\n")
    cal = calendar(); O, C = crosses(); DC = daily_close()
    cal_i = pd.DatetimeIndex(cal); nxt = dict(zip(cal[:-1], cal[1:]))
    O = O.reindex(cal_i); C = C.reindex(cal_i)
    nO = O.shift(-1)                                              # next session's open cross, indexed by close date d
    log(f"nights {len(cal) - 1}; cross coverage close {C[SYMS].notna().mean().mean():.3f} open {O[SYMS].notna().mean().mean():.3f}")
    r = DC.pct_change()
    beta = (r.rolling(60).cov(r["QQQ"]).div(r["QQQ"].rolling(60).var(), axis=0)).shift(1).reindex(cal_i)
    res = {}
    for key in TIMES:
        Bq, Aq = quotes(key, cal); Bq = Bq.reindex(cal_i); Aq = Aq.reindex(cal_i); Mq = (Bq + Aq) / 2
        live = Bq["QQQ"].notna()
        log(f"\n=== T = {key} ET ({'REGISTERED' if key == '2300' else 'report-only'}): venue-live nights {live.sum()} / {len(cal) - 1}")
        hs = ((Aq - Bq) / Mq * 1e4 / 2)
        log("  median half-spread bp: " + " ".join(f"{s} {hs[s].median():.1f}" for s in ASIA + CONTROL if s in hs))
        # BOATS-PREM
        D = (Bq - nO) / C * 1e4 - 1                               # sell at bid_T vs sell at open cross (bp of close), 1bp extra
        net = (Bq / C - 1) * 1e4 - 2                              # close cross -> bid_T, 1bp/side
        hedge = beta.mul((Mq["QQQ"] / C["QQQ"] - 1) * 1e4, axis=0)
        exc = net - hedge
        sh = hs * 2                                               # two more half-spreads for 3x cost
        cols_a = [s for s in ASIA if s in D]; cols_c = [s for s in CONTROL if s in D]
        lv = live[live].index
        dA = D.loc[lv, cols_a].mean(axis=1); dC = D.loc[lv, cols_c].mean(axis=1)
        log(" BOATS-PREM: per-night EW, bp")
        k = {}
        k["D_A"] = stats(dA, "D ASIA (bid_T - open)")
        k["D_C"] = stats(dC, "D CONTROL")
        k["PX"] = stats(dA - dC, "PX = D_ASIA - D_CONTROL")
        k["net_A"] = stats(net.loc[lv, cols_a].mean(axis=1), "ASIA close->bid_T net (unhedged)")
        k["exc_A"] = stats(exc.loc[lv, cols_a].mean(axis=1), "ASIA hedged excess")
        k["exc_A3"] = stats((exc - sh).loc[lv, cols_a].mean(axis=1), "ASIA hedged excess 3x cost")
        k["exc_C"] = stats(exc.loc[lv, cols_c].mean(axis=1), "CONTROL hedged excess (placebo)")
        k["net_C"] = stats(net.loc[lv, cols_c].mean(axis=1), "CONTROL close->bid_T net")
        k["oo_A"] = stats(((nO / C - 1) * 1e4 - 2).loc[lv, cols_a].mean(axis=1), "ASIA close->open cross net (ref)")
        log("  per-name D (bid_T - open, bp) mean/med: " + " ".join(f"{s} {D.loc[lv, s].mean():+.0f}/{D.loc[lv, s].median():+.0f}" for s in cols_a))
        # BOATS-LETF
        log(" BOATS-LETF: events ask_LETF/fair - 1 <= -15bp; buy ask_T, sell open cross; excess vs L x underlying (mid_T -> open)")
        ev, rich = [], []
        for le, u, L in PAIRS:
            if le not in Mq or u not in Mq: continue
            fair = C[le] * (1 + L * (Mq[u] / C[u] - 1))
            da = Aq[le] / fair - 1; db = Bq[le] / fair - 1; dm = Mq[le] / fair - 1
            ex_l = (nO[le] / Aq[le] - 1) - L * (nO[u] / Mq[u] - 1)
            ex_r = (Bq[le] / nO[le] - 1) * 1 - 0                    # rich side: sell at bid_T vs at open (raw, not hedged)
            ex_rh = (Bq[le] - nO[le]) / nO[le] - L * (Mq[u] - nO[u]) / nO[u]
            for d in lv:
                if np.isfinite(da.get(d, np.nan)) and np.isfinite(ex_l.get(d, np.nan)) and da[d] <= -X_LETF:
                    ev.append(dict(d=d, pair=le, dis=da[d] * 1e4, exc=ex_l[d] * 1e4 - 2, raw=(nO[le][d] / Aq[le][d] - 1) * 1e4 - 2,
                                   spr=(Aq[le][d] - Bq[le][d]) / Mq[le][d] * 1e4))
                if np.isfinite(db.get(d, np.nan)) and np.isfinite(ex_rh.get(d, np.nan)) and db[d] >= X_LETF:
                    rich.append(dict(d=d, pair=le, dis=db[d] * 1e4, exc=ex_rh[d] * 1e4 - 1))
            log(f"  {le}/{u} L{L:+d}: dislocation mid bp median {dm[lv].median() * 1e4:+.1f} sd {dm[lv].std() * 1e4:.1f} "
                f"| half-spread {hs[le][lv].median():.1f} | cheap events {int((da[lv] <= -X_LETF).sum())} rich {int((db[lv] >= X_LETF).sum())}")
        E = pd.DataFrame(ev); R = pd.DataFrame(rich)
        if len(E):
            byd = E.groupby("d").exc.mean(); byd.index = pd.DatetimeIndex(byd.index)
            log(f"  cheap events {len(E)} on {E.d.nunique()} nights ({len(E) / ((len(lv)) / 252):.0f}/yr); per-pair counts {E.pair.value_counts().to_dict()}")
            k["L_exc"] = stats(byd, "LETF cheap excess (night-clustered)")
            k["L_ev"] = dict(n=len(E), mean=E.exc.mean(), med=E.exc.median(), ex5=np.sort(E.exc)[:-5].mean() if len(E) > 5 else np.nan)
            log(f"  event-level: mean {E.exc.mean():+.1f} med {E.exc.median():+.1f} hit {(E.exc > 0).mean():.2f} ex-top5 {k['L_ev']['ex5']:+.1f}; "
                f"2x cost (one more spread) {(E.exc - E.spr).mean():+.1f}; raw unhedged {E.raw.mean():+.1f}")
            byd2 = (E.assign(x=E.exc - E.spr)).groupby("d").x.mean(); byd2.index = pd.DatetimeIndex(byd2.index)
            k["L_exc2"] = stats(byd2, "LETF cheap excess 2x cost")
        if len(R):
            byr = R.groupby("d").exc.mean(); byr.index = pd.DatetimeIndex(byr.index)
            stats(byr, "LETF rich: sell bid_T vs open, hedged")
        res[key] = k
    json.dump({k: {a: {b: (float(c) if c is not None else None) for b, c in v.items()} for a, v in kk.items()} for k, kk in res.items()},
              open(CACHE / "summary.json", "w"), default=float, indent=1)


if __name__ == "__main__":
    {"fetch": fetch, "run": run}[sys.argv[1]]()
