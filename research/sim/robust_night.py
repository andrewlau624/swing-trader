"""ROBUST-MAP, night leg (registered research/drafts/round1_prose.md, 2026-10-10; descriptive, no N).
Random-settings map around the LIVE night rule on a wide candidate table.
  build (Mac, needs Sharadar):  PYTHONPATH=. .venv/bin/python -m research.sim.robust_night --build
  run (standalone, pandas/numpy only, server-safe):  python research/sim/robust_night.py
Metric per setting: nightly equal-weight mean net return of the picks (0 on no-pick nights), 5bp/side, x night_weight 0.5
-> bp/day of account, and annualised Sharpe of that series; eras 1999-2015 and 2016-2026.
Not a search: the best cell is not a candidate."""
import sys, pathlib, itertools
import numpy as np, pandas as pd
ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/robust"
OUT = ROOT / "data/research/program/robust_night_out.txt"
COST, NW = 5e-4, 0.5
LIVE = dict(dr=-0.08, ibs=0.10, vol=0.60, adv=1e7, px=5.0)
STEP = dict(dr=0.01, ibs=0.025, vol=0.1, adv=1.5, px=1.0)
ERAS = {"1999-2015": ("1999-01-01", "2015-12-31"), "2016-2026": ("2016-01-01", "2026-12-31")}

def build():
    sys.path.insert(0, str(ROOT))
    from research.sim import shar_surv as ss, nx
    M = ss.load_master(); act = ss.load_actions()
    a = act.copy(); a["action"] = a["action"].str.lower()
    dprice = {}
    for tk, g in a[a["action"].isin(nx.DELIST_ACTIONS)].groupby("ticker"):
        g = g.sort_values("date"); v = pd.to_numeric(g["value"], errors="coerce")
        dprice[tk] = float(v.iloc[-1]) if np.isfinite(v.iloc[-1]) and v.iloc[-1] > 0 else None
    divs = {}
    dv = a[a["action"] == "dividend"]
    for tk, d_, v in zip(dv["ticker"], dv["date"], pd.to_numeric(dv["value"], errors="coerce")):
        if np.isfinite(v): divs[(tk, np.datetime64(d_, "ns"))] = float(v)
    mt = nx.master_by_ticker(M)
    out, sess_all = [], []
    for lo, hi in [("1999-01-04", "2015-12-31"), ("2016-01-04", "2026-09-18")]:
        lo, hi = pd.Timestamp(lo), pd.Timestamp(hi)
        bars = ss.load_bars(lo - pd.Timedelta(days=400), hi + pd.Timedelta(days=10))
        pn = nx.build_panel(bars); del bars
        sec = nx._sector_arrays(pn, M); prim = nx.universe_mask(pn, M, "primary")
        sess = pn["sessions"]; sess_all.append(pd.DatetimeIndex(sess[(sess >= np.datetime64(lo)) & (sess <= np.datetime64(hi))]))
        date = pn["date"]; inwin = (date >= np.datetime64(lo)) & (date <= np.datetime64(hi))
        with np.errstate(invalid="ignore", divide="ignore"):
            dayret = pn["c"] / pn["c_prev"] - 1
            price = pn["cu"]; fa = pn["f"]
            high = np.maximum(pn["h"] * fa, price); low = np.minimum(pn["l"] * fa, price)
            rng = np.where(high - low > 0, high - low, np.nan); ibs = (price - low) / rng
            m = (prim & inwin & (pn["pos"] >= 20) & (pn["cu_prev"] >= 3) & (pn["adv"] >= 3e6) & (pn["vol20"] >= 0.30)
                 & np.isfinite(dayret) & (dayret <= -0.05) & np.isfinite(ibs) & (ibs < 0.30) & (price >= 3) & (price <= 2000))
        rows = []
        for i in np.flatnonzero(m):
            dd = pn["date"][i]; tk = pn["tickers"][i]
            si = int(np.searchsorted(sess, dd))
            if si + 1 >= len(sess): continue
            nxt = pd.Timestamp(sess[si + 1])
            if pn["has_next"][i]:
                ret = pn["o_next"][i] / pn["c"][i] - 1.0
                dvd = divs.get((tk, np.datetime64(nxt, "ns")))
                if dvd and 0 < dvd / pn["cu"][i] < 0.25: ret += dvd / pn["cu"][i]
            else:
                lastbar = mt.at[tk, "lastpricedate"] if tk in mt.index else pd.NaT
                gone = bool(mt.at[tk, "delisted"]) if tk in mt.index else False
                if pd.isna(lastbar):
                    lastbar = pd.Timestamp(pn["date"][pn["start"][i]:][pn["tickers"][pn["start"][i]:] == tk][-1])
                ended = gone and pd.Timestamp(lastbar) <= pd.Timestamp(dd)
                px = dprice.get(tk) if ended else None
                if ended and px is not None and 0 < px / pn["cu"][i] <= 5: ret = px / pn["cu"][i] - 1.0
                else: ret = -1.0
            rows.append((dd, tk, dayret[i], ibs[i], price[i], pn["cu_prev"][i], pn["vol20"][i], pn["adv"][i], ret, sec[i]))
        df = pd.DataFrame(rows, columns=["date", "ticker", "day_ret", "ibs", "price", "pprev", "vol20", "adv", "ret", "sector"])
        out.append(df); print(lo.date(), hi.date(), len(df), flush=True); del pn
    df = pd.concat(out, ignore_index=True)
    for c in ["day_ret", "ibs", "price", "pprev", "vol20", "adv", "ret"]: df[c] = df[c].astype("float32")
    df["date"] = pd.to_datetime(df["date"]); df["sector"] = df["sector"].fillna("NA").astype("category")
    df["ticker"] = df["ticker"].astype("category")
    df.to_parquet(D / "night_cands.parquet", index=False)
    pd.DataFrame({"date": pd.DatetimeIndex(sess_all[0].append(sess_all[1]))}).to_parquet(D / "night_sessions.parquet", index=False)
    print("saved", len(df))

class Eval:
    def __init__(self):
        df = pd.read_parquet(D / "night_cands.parquet")
        self.s = pd.read_parquet(D / "night_sessions.parquet")["date"]
        df["di"] = np.searchsorted(self.s.values, df["date"].values)
        self.di = df["di"].to_numpy(); self.dr = df["day_ret"].to_numpy(); self.ibs = df["ibs"].to_numpy()
        self.vol = df["vol20"].to_numpy(); self.adv = df["adv"].to_numpy(); self.px = df["price"].to_numpy()
        self.pp = df["pprev"].to_numpy(); self.r = (df["ret"].to_numpy(np.float64) - 2 * COST)
        n = len(self.s); self.n = n; self.sv = self.s.values
        self.era = {k: (np.searchsorted(self.sv, np.datetime64(a)), np.searchsorted(self.sv, np.datetime64(b), side="right")) for k, (a, b) in ERAS.items()}
    def series(self, p):
        m = ((self.dr <= p["dr"]) & (self.ibs < p["ibs"]) & (self.vol >= p["vol"]) & (self.adv >= p["adv"])
             & (self.px >= p["px"]) & (self.pp >= p["px"]))
        s = np.bincount(self.di[m], weights=self.r[m], minlength=self.n); c = np.bincount(self.di[m], minlength=self.n)
        return np.where(c > 0, s / np.maximum(c, 1), 0.0) * NW
    def metric(self, p):
        x = self.series(p); o = {}
        for k, (a, b) in self.era.items():
            y = x[a:b]; sd = y.std()
            o[k] = (y.mean() * 1e4, y.mean() / sd * np.sqrt(252) if sd > 0 else 0.0)
        return o

def main():
    E = Eval(); L = []
    def P(s=""): print(s, flush=True); L.append(s)
    live = E.metric(LIVE)
    P(f"LIVE setting on wide table (no dedupe/crowd/tilt; equal-weight picks x 0.5, 5bp/side): " + "  ".join(f"{k} {v[0]:+.2f}bp/day Sharpe {v[1]:.2f}" for k, v in live.items()))
    # per-trade check vs nx base (catmom_depth_out: +57.6 / +30.3 bp per trade-night at full budget)
    x = E.series(LIVE) / NW
    for k, (a, b) in E.era.items():
        y = x[a:b]; pos = y != 0
        P(f"  {k}: nights with picks {pos.sum()}, mean net per pick-night {y[pos].mean()*1e4:+.1f}bp (nx catmom base: {'+57.6' if k=='1999-2015' else '+30.3'})")
    rng = np.random.default_rng(20261010)
    N = 1500
    R = []
    for _ in range(N):
        R.append(dict(dr=rng.uniform(-0.12, -0.06), ibs=rng.uniform(0.05, 0.20), vol=rng.uniform(0.3, 1.0),
                      adv=float(np.exp(rng.uniform(np.log(3e6), np.log(3e7)))), px=rng.uniform(3, 10)))
    mets = [E.metric(p) for p in R]
    P(f"\nRANDOM settings n={N}: day_ret_max U[-12,-6]%, ibs_max U[.05,.20], vol_min U[.3,1], adv_min logU[3e6,3e7], price_min U[3,10]")
    for k in ERAS:
        arr = np.array([m[k][0] for m in mets]); sh = np.array([m[k][1] for m in mets]); lv = live[k][0]
        P(f"  {k}: live {lv:+.2f}bp/day = percentile {100*(arr<lv).mean():.0f} of random; random median {np.median(arr):+.2f}, p10 {np.percentile(arr,10):+.2f}, p90 {np.percentile(arr,90):+.2f}, "
          f"share>0 {100*(arr>0).mean():.0f}%; Sharpe live {live[k][1]:.2f} (pct {100*(sh<live[k][1]).mean():.0f}), random median {np.median(sh):.2f}")
    # 1-D profiles
    P("\n1-D PROFILES (others at live): bp/day [Sharpe] per era 1999-2015 | 2016-2026")
    grids = dict(dr=[-0.12, -0.11, -0.10, -0.09, -0.08, -0.07, -0.06], ibs=[0.05, 0.075, 0.10, 0.125, 0.15, 0.175, 0.20],
                 vol=[0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0], adv=[3e6, 5e6, 7e6, 1e7, 1.5e7, 2.2e7, 3e7], px=[3, 4, 5, 6, 7, 8, 10])
    for k, g in grids.items():
        P(f"  {k}:")
        for v in g:
            p = dict(LIVE); p[k] = v; m = E.metric(p)
            P(f"    {v:>10g}{'*' if v == LIVE[k] else ' '} " + " | ".join(f"{m[e][0]:+6.2f} [{m[e][1]:4.2f}]" for e in ERAS))
    # neighbourhood: +-1 step on every param (3^5 grid, step multiplicative for adv)
    def vals(k):
        l = LIVE[k]
        if k == "adv": return [l / STEP[k], l, l * STEP[k]]
        return [l - STEP[k], l, l + STEP[k]]
    nb = []
    for combo in itertools.product(*[vals(k) for k in LIVE]):
        p = dict(zip(LIVE, combo)); nb.append((p, E.metric(p)))
    P(f"\nNEIGHBOURHOOD: {len(nb)} settings within +-1 step on every param (dr 1pp, ibs .025, vol .1, adv x1.5, px $1)")
    P("VERDICT RULE: FRAGILE if live > 1.5x neighbourhood median OR any single +-1-step move loses >50% of live; PLATEAU if >=70% of neighbourhood keeps >=50% of live; else MIXED")
    for e in ERAS:
        arr = np.array([m[e][0] for _, m in nb]); lv = live[e][0]; med = np.median(arr)
        single = []
        for k in LIVE:
            for v in (vals(k)[0], vals(k)[2]):
                p = dict(LIVE); p[k] = v; single.append((k, v, E.metric(p)[e][0]))
        worst = min(single, key=lambda t: t[2]); losers = [t for t in single if t[2] < 0.5 * lv]
        keep = (arr >= 0.5 * lv).mean() if lv > 0 else float("nan")
        c1 = lv > 1.5 * med if lv > 0 else False; c2 = len(losers) > 0
        if lv <= 0: verd = "n/a (live <= 0 in era)"
        elif c1 or c2: verd = "FRAGILE"
        elif keep >= 0.70: verd = "PLATEAU"
        else: verd = "MIXED"
        P(f"  {e}: live {lv:+.2f}; neighbourhood median {med:+.2f} (live/median {lv/med if med>0 else float('nan'):.2f}x), p10 {np.percentile(arr,10):+.2f}, min {arr.min():+.2f}; "
          f"{100*keep:.0f}% keep >=50% of live; single-step moves losing >50%: {[(k, round(v,3), round(r,2)) for k,v,r in losers] or 'none'}; worst single {worst[0]}={worst[1]:.3g} -> {worst[2]:+.2f}  => {verd}")
    OUT.write_text("\n".join(L))

if __name__ == "__main__":
    if "--build" in sys.argv: build()
    else: main()
