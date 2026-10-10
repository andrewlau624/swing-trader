"""ROBUST-MAP, IBS leg (registered round1_prose.md "ROBUST-MAP", 2026-10-10; descriptive, best cell is NOT a candidate).
Live rule (swingtrader/daily/signals.py ibs_targets + momentum_top; replay = research/sim/recent_ibs.py): on session d, rank EQ18 by momentum (close[-skip]/close[-lb]-1)
at the last trading day of the PRIOR month (relative to entry day d+1), keep top-k, hold names with IBS(d) < ibs_max; buy open(d+1), sell open(d+2) on DIVIDEND-ADJUSTED bars,
equal weight over the triggered names, leg weight 0.5, no trigger = 0 bp that day. Net = trade return - 2*5bp (every trip pays both sides, as in recent_ibs; live
holds consecutive days without re-trading, so this is conservative). Rows with |ret|>50% dropped (recent_ibs). Sessions before index 260 skipped (as recent_ibs).
  build (repo venv + ~/data/sharadar): .venv/bin/python research/sim/robust_ibs.py build
  run (numpy+pandas only, data/research/robust/ibs_*.npz): python research/sim/robust_ibs.py [run]
Eras: 2004-15 (Sharadar SFP, adjust=total, delisted incl.; XBI from 2006, EEM from 2003-04), 2016-20 (data/research/night/etf_daily.parquet), 2021-26 (data/research/recent/etfd/etf_adj.parquet).
Entry-date eras. Params: ibs_max [.05,.35] step .05 (live .2), top_k 1..6 (3), momentum {6-1,9-1,12-1,12-0} = (lb,skip) (126,21),(189,21),(252,21),(252,0) (live 12-1).
Neighbourhood = +-1 step on every param (ibs_max .15/.2/.25, k 2/3/4, mom 9-1/12-1/12-0 -> 26 others); single-move set = one param moved, others live.
"""
import sys, os, time, itertools
import numpy as np, pandas as pd
REPO = "/Users/andrewlau/Documents/Code/Projects/swing-trader"
RD = f"{REPO}/data/research/robust"; OUT = f"{REPO}/data/research/program/robust_ibs_out.txt"
EQ18 = ["SPY","QQQ","IWM","DIA","MDY","XLK","XLF","XLE","XLV","XLI","XLY","XLP","XLU","XLB","SMH","XBI","EEM","EFA"]
LEGW = 0.5; COST = 5.0
MOMS = [("6-1", 126, 21), ("9-1", 189, 21), ("12-1", 252, 21), ("12-0", 252, 0)]
GI = [.05, .10, .15, .20, .25, .30, .35]; GK = [1, 2, 3, 4, 5, 6]
LIVE = dict(ibs=.20, k=3, mom="12-1")
ERAS = [("2004-15", "2004-01-01", "2015-12-31"), ("2016-20", "2016-01-01", "2020-12-31"), ("2021-26", "2021-01-01", "2026-12-31")]

def _save(name, df, cols=("open", "high", "low", "close")):
    d = df.index.get_level_values(0) if False else None
    dates = sorted(df.date.unique()); P = {f: df.pivot(index="date", columns="symbol", values=f).reindex(index=dates, columns=EQ18) for f in cols}
    np.savez_compressed(f"{RD}/ibs_{name}.npz", dates=np.array(dates, "datetime64[ns]"), **{f: P[f].values for f in cols})
    print(name, len(dates), "sessions", P["close"].notna().sum().min(), "min bars/sym")

def build():
    os.makedirs(RD, exist_ok=True)
    from sharadar import prices
    p = prices(EQ18, "2003-01-01", "2016-01-31", adjust="total", source="funds").rename(columns={"ticker": "symbol"})
    p["date"] = pd.to_datetime(p["date"]); _save("2004_15", p)
    e = pd.read_parquet(f"{REPO}/data/research/night/etf_daily.parquet"); e = e[e.symbol.isin(EQ18)]
    e["date"] = e.timestamp.dt.tz_convert("America/New_York").dt.normalize().dt.tz_localize(None); _save("2016_20", e)
    a = pd.read_parquet(f"{REPO}/data/research/recent/etfd/etf_adj.parquet"); a = a[a.symbol.isin(EQ18)]
    a["date"] = a.timestamp.dt.tz_convert("America/New_York").dt.normalize().dt.tz_localize(None); _save("2021_26", a)

def load(name):
    z = np.load(f"{RD}/ibs_{name}.npz")
    return pd.DatetimeIndex(z["dates"]), {f: z[f] for f in ("open", "high", "low", "close")}

def prep(dates, B):
    """per entry-day arrays aligned on j+1: ibs(d), ret(d+1 open -> d+2 open), momentum rank per mom at prior month end."""
    O, H, L, C = B["open"], B["high"], B["low"], B["close"]; n = len(dates)
    rngp = H - L
    with np.errstate(divide="ignore", invalid="ignore"):
        ibs = np.where(rngp > 0, (C - L) / rngp, np.nan)   # signals.ibs: NaN on zero range
    ret = np.full_like(C, np.nan); ret[:-2] = O[2:] / O[1:-1] - 1.0     # row j: signal day d=j, entry j+1, exit j+2
    ret[np.abs(ret) >= 0.5] = np.nan
    per = dates.to_period("M"); Cdf = pd.DataFrame(C, index=dates)
    ranks = {}
    for nm, lb, sk in MOMS:
        mom = (Cdf.shift(sk) / Cdf.shift(lb) - 1).values
        # prior-month-end row for entry day t=dates[j+1]: last session of the month before t's month
        last_of_month = {}
        for i, pp in enumerate(per): last_of_month[pp] = i
        R = np.full(C.shape, 99.0)
        for j in range(n - 1):
            pm = per[j + 1] - 1
            if pm not in last_of_month: continue
            row = mom[last_of_month[pm]]
            ok = np.isfinite(row)
            if not ok.any(): continue
            order = np.argsort(-np.where(ok, row, -np.inf), kind="stable")
            rk = np.full(C.shape[1], 99.0); rk[order[:ok.sum()]] = np.arange(ok.sum()); R[j] = rk
        ranks[nm] = R
    return dict(dates=dates, ibs=ibs, ret=ret, ranks=ranks, n=n)

def evaluate(Pr, ibs_max, k, mom, cost=COST):
    """-> per-entry-day account series (bp), and trade list stats."""
    R = Pr["ranks"][mom]; ibs, ret = Pr["ibs"], Pr["ret"]
    trig = (R < k) & (ibs < ibs_max) & np.isfinite(ret)
    cnt = trig.sum(1); sm = np.where(trig, ret * 1e4 - 2 * cost, 0).sum(1)
    leg = np.where(cnt > 0, sm / np.maximum(cnt, 1), 0.0) * LEGW
    j = np.arange(Pr["n"]); idx = Pr["dates"][np.minimum(j + 1, Pr["n"] - 1)]
    valid = (j >= 260) & (j < Pr["n"] - 2)
    s = pd.Series(leg, index=idx)[valid]
    tr = np.where(trig, ret * 1e4, np.nan)[valid]
    return s, tr, cnt[valid]

def stats(s, a, b):
    y = s[(s.index >= a) & (s.index <= b)]
    if len(y) < 50: return np.nan, np.nan
    sd = y.std(); return y.mean(), (y.mean() / sd * np.sqrt(252) if sd > 0 else np.nan)

def verdict(live, nb, moves):
    if not live > 0: return "NO EDGE (live <= 0)"
    fr = live > 1.5 * np.median(nb) or any(m < 0.5 * live for m in moves)
    pl = np.mean([m >= 0.5 * live for m in nb]) >= 0.7
    return "FRAGILE" if fr else ("PLATEAU" if pl else "MIXED")

def main():
    t0 = time.time(); out = []; P = out.append
    PR = {}
    for nm, lab in (("2004_15", "2004-15"), ("2016_20", "2016-20"), ("2021_26", "2021-26")):
        d, B = load(nm); PR[lab] = prep(d, B)
    # reproduction: recent_ibs 2021-25 gross
    P("== REPRODUCTION (live setting, per-trade bp, entry 2021-01-01..2025-12-31, adjusted bars) ==")
    s, tr, cnt = evaluate(PR["2021-26"], .2, 3, "12-1", cost=0)
    idx = s.index; m = (idx >= "2021-01-01") & (idx <= "2025-12-31")
    x = tr[m]; x = x[np.isfinite(x)]
    P(f"gross mean {x.mean():+.2f}bp/trade n={len(x)} (reference recent_ibs_2026-10-08.md: +15.8bp t 1.9); net at 5bp/side {x.mean() - 10:+.2f}")
    s5, _, _ = evaluate(PR["2021-26"], .2, 3, "12-1"); P(f"leg bp/day of account net 5bp/side 2021-25 {s5[m].mean():+.3f}, fire-rate {np.mean(cnt[m] > 0) * 100:.0f}% of days")
    P("")
    rng = np.random.default_rng(20261010)
    rand = [(float(rng.uniform(.05, .35)), int(rng.integers(1, 7)), MOMS[int(rng.integers(0, 4))][0]) for _ in range(900)]
    grid = [(i, k, m[0]) for i in GI for k in GK for m in MOMS]
    cache = {}
    def met(era, st):
        key = (era, round(st[0], 6), st[1], st[2])
        if key not in cache:
            s, _, _ = evaluate(PR[era], *st); e = [e for e in ERAS if e[0] == era][0]
            cache[key] = stats(s, e[1], e[2])
        return cache[key]
    for era, _, _ in ERAS:
        P(f"===== era {era} (net 5bp/side; leg weight .5; bp/day of account / Sharpe) =====")
        lv = met(era, (LIVE["ibs"], LIVE["k"], LIVE["mom"]))
        rb = np.array([met(era, st)[0] for st in rand]); rs = np.array([met(era, st)[1] for st in rand])
        P(f"LIVE {lv[0]:+.3f} bp/day, Sharpe {lv[1]:+.2f} | random n={len(rand)}: median {np.median(rb):+.3f} p10 {np.percentile(rb, 10):+.3f} p90 {np.percentile(rb, 90):+.3f}; "
          f"live percentile bp {np.mean(rb <= lv[0]) * 100:.0f} / Sharpe {np.mean(rs <= lv[1]) * 100:.0f}; settings > 0: {np.mean(rb > 0) * 100:.0f}%")
        pr = lambda lab, vals, f: P(f"profile {lab}: " + "  ".join(f"{v}:{met(era, f(v))[0]:+.3f}/{met(era, f(v))[1]:+.2f}" for v in vals))
        pr("ibs_max", GI, lambda v: (v, LIVE["k"], LIVE["mom"]))
        pr("top_k  ", GK, lambda v: (LIVE["ibs"], v, LIVE["mom"]))
        pr("mom    ", [m[0] for m in MOMS], lambda v: (LIVE["ibs"], LIVE["k"], v))
        ni = [.15, .20, .25]; nk = [2, 3, 4]; nm_ = ["9-1", "12-1", "12-0"]
        nb = [met(era, (i, k, m)) for i, k, m in itertools.product(ni, nk, nm_) if (i, k, m) != (.2, 3, "12-1")]
        mv = [met(era, st) for st in [(.15, 3, "12-1"), (.25, 3, "12-1"), (.2, 2, "12-1"), (.2, 4, "12-1"), (.2, 3, "9-1"), (.2, 3, "12-0")]]
        for mi, nmn in ((0, "bp/day"), (1, "Sharpe")):
            l = lv[mi]; nbv = [q[mi] for q in nb]; mvv = [q[mi] for q in mv]
            P(f"neighbourhood n={len(nbv)} ({nmn}): median {np.median(nbv):+.3f} min {min(nbv):+.3f} max {max(nbv):+.3f}; keep>=50% of live {np.mean([x >= .5 * l for x in nbv]) * 100:.0f}%; "
              f"worst single move {min(mvv):+.3f} ({min(mvv) / l * 100 if l else float('nan'):.0f}% of live) -> {verdict(l, nbv, mvv)}")
        P("")
    P(f"settings: {len(rand)} random + {len(grid)} grid per era; runtime {time.time() - t0:.0f}s")
    open(OUT, "w").write("\n".join(out)); print("\n".join(out))

if __name__ == "__main__":
    build() if len(sys.argv) > 1 and sys.argv[1] == "build" else main()
