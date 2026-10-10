"""ROBUST-MAP, noise (intraday) leg on QQQ+SMH (registered round1_prose.md "ROBUST-MAP", 2026-10-10; descriptive).
Replays the daybook PROD rule (swingtrader/daybook/shadow.replay_instrument; band = max/min(open, prev close)*(1+/-vm*sigma_m), sigma_m = mean over
the last L sessions of |close_m/open-1| at minute m, exit on band/VWAP loss, flat at minute 387 = 15:57, weight 0.5 per symbol, leverage = min(3.5, tv/sd of last
vlb daily returns)) over random settings, vectorised across days. Standalone: numpy+pandas only.
  build (needs repo + data/research/night/m1):  .venv/bin/python research/sim/robust_noise.py build
  run   (only data/research/robust/noise_*.npz): python research/sim/robust_noise.py [run]
Params: vm band multiplier [.5,1.5] (live 1), L lookback days [7,21] (14), bar = decision cadence in minutes {15,30,60} (30; sigma stays per-minute, so
this changes sampling only, not aggregated bars), vlb vol-target lookback [7,21] (14), tv target vol [.01,.03] (.02; pure sizing scale, so shown as a
profile but EXCLUDED from the neighbourhood: -50% tv halves bp/day by construction). Cost = bp per ROUND TRIP on the unit position (1 and 4).
Metric: net bp/day of account (both symbols, no-trade days 0) and annualised Sharpe of that daily series. Lag 0 (decision print = fill print) is the map default.
Sizing leverage uses closes through the PRIOR day (live-correct); the research replay (shadow.replay_instrument/noise_recent) includes TODAY's close: both are reported.
"""
import sys, os, time, glob
import numpy as np, pandas as pd
REPO = "/Users/andrewlau/Documents/Code/Projects/swing-trader"
RD = f"{REPO}/data/research/robust"; OUT = f"{REPO}/data/research/program/robust_noise_out.txt"
SYMS = ["QQQ", "SMH"]; W = 0.5; CLOSE_M = 387; MAXLEV = 3.5
LIVE = dict(vm=1.0, L=14, bar=30, vlb=14, tv=0.02)
GRID = dict(vm=[.5, .75, 1.0, 1.25, 1.5], L=[7, 10, 14, 18, 21], bar=[15, 30, 60], vlb=[7, 10, 14, 18, 21], tv=[.01, .015, .02, .025, .03])
NB_EXCL = {"tv"}

def build():
    os.makedirs(RD, exist_ok=True)
    for s in SYMS:
        df = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f"{REPO}/data/research/night/m1/{s}_*.parquet"))])
        t = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert("America/New_York")
        df = df.assign(date=t.dt.tz_localize(None).dt.normalize(), m=t.dt.hour * 60 + t.dt.minute - 570)
        df = df[(df.m >= 0) & (df.m < 390)].sort_values(["date", "m"])
        dates = sorted(df.date.unique()); n = len(dates)
        C = np.full((n, 390), np.nan, np.float32); V = np.zeros((n, 390), np.float32); O = np.zeros(n)
        idx = {d: i for i, d in enumerate(dates)}
        i = df.date.map(idx).values
        C[i, df.m.values] = df.close.values; V[i, df.m.values] = df.volume.values
        O[:] = df.groupby("date").open.first().reindex(dates).values
        C = pd.DataFrame(C).ffill(axis=1).values.astype(np.float32)
        np.savez_compressed(f"{RD}/noise_{s}.npz", dates=np.array(dates, "datetime64[ns]"), C=C, V=V, O=O)
        print(s, n, "days", C.shape)

def load():
    D = {}
    for s in SYMS:
        z = np.load(f"{RD}/noise_{s}.npz"); D[s] = dict(dates=pd.DatetimeIndex(z["dates"]), C=z["C"].astype(np.float64), V=z["V"].astype(np.float64), O=z["O"])
    return D

def prep(d):
    """per-symbol pieces independent of settings (VWAP, |close/open-1|, daily closes)."""
    C, V, O = d["C"], d["V"], d["O"]
    mv = np.abs(C / O[:, None] - 1.0)
    ok = np.isfinite(mv); mv0 = np.where(ok, mv, 0.0)
    pv = np.cumsum(np.where(np.isfinite(C), C, 0) * V, 1) / np.maximum(np.cumsum(V, 1), 1)
    pv = np.where(np.isfinite(pv), pv, C)
    dc = C[:, 389]
    pc = np.r_[np.nan, dc[:-1]]
    return dict(mv0=np.r_[np.zeros((1, 390)), np.cumsum(mv0, 0)], cnt=np.r_[np.zeros((1, 390)), np.cumsum(ok, 0)], pv=pv, dc=dc, pc=pc,
                ret=pd.Series(dc).pct_change().values)

_sig = {}
def sigma(sym, P, L):
    """sigma[k] = nanmean over sessions k-L..k-1 (fewer early), rows with <5 prior sessions are invalid."""
    key = (sym, L)
    if key not in _sig:
        n = len(P["dc"]); k = np.arange(n); lo = np.maximum(k - L, 0)
        s = (P["mv0"][k] - P["mv0"][lo]); c = (P["cnt"][k] - P["cnt"][lo])
        _sig[key] = np.where(c > 0, s / np.maximum(c, 1), np.nan)
    return _sig[key]

def lev_for(P, vlb, tv, lookahead):
    r = pd.Series(P["ret"])
    if not lookahead: r = r.shift(1)   # returns known before today's open
    sd = r.rolling(vlb, min_periods=5).std().values
    with np.errstate(divide="ignore", invalid="ignore"):
        lev = np.minimum(MAXLEV, tv / sd)
    return np.where(np.isfinite(lev) & (sd > 0), lev, 0.0)

def run_sym(sym, d, P, vm, L, bar, vlb, tv, lag=0, lookahead=False):
    """returns per-day arrays: G (sum gross bp * lev*w), Lw (sum lev*w over trades), Gu (unweighted gross bp), N trades."""
    C = d["C"]; n = len(C); sg = sigma(sym, P, L)
    o = d["O"]; pc = P["pc"]
    hi = np.maximum(o, pc)[:, None]; lo = np.minimum(o, pc)[:, None]
    ub = hi * (1 + vm * sg); lb = lo * (1 - vm * sg)
    lev = lev_for(P, vlb, tv, lookahead)
    valid = (np.arange(n) >= 5) & (lev > 0) & np.isfinite(pc)
    mult = np.where(valid, lev * W, 0.0)
    pos = np.zeros(n, int); ep = np.zeros(n)
    G = np.zeros(n); Lw = np.zeros(n); Gu = np.zeros(n); N = np.zeros(n)
    def close_trade(mask, fm):
        nonlocal G, Lw, Gu, N
        g = pos * (C[:, fm] / ep - 1.0) * 1e4
        mask = mask & np.isfinite(g)
        G += np.where(mask, g * mult, 0.0); Lw += np.where(mask, mult, 0.0); Gu += np.where(mask, g, 0.0); N += mask
    for m in range(bar, 361, bar):
        p = C[:, m]; fm = min(m + lag, CLOSE_M)
        exl = (pos == 1) & (p < np.maximum(ub[:, m], P["pv"][:, m])); exs = (pos == -1) & (p > np.minimum(lb[:, m], P["pv"][:, m]))
        ex = (exl | exs) & valid
        if ex.any(): close_trade(ex, fm); pos[ex] = 0
        flat = (pos == 0) & valid & np.isfinite(p) & (sg[:, m] > 0)
        lg = flat & (p > ub[:, m]); st = flat & (p < lb[:, m])
        ent = lg | st
        pos[lg] = 1; pos[st] = -1; ep[ent] = C[ent, fm]
    close_trade((pos != 0) & valid, CLOSE_M)
    return G, Lw, Gu, N

def leg(D, Ps, setting, lag=0, lookahead=False):
    out = {}
    for s in SYMS:
        out[s] = run_sym(s, D[s], Ps[s], lag=lag, lookahead=lookahead, **setting)
    return out

def series(D, res, c):
    """daily account series in bp (net of cost c bp RT), indexed by common dates."""
    ad = D["QQQ"]["dates"].intersection(D["SMH"]["dates"])
    tot = None
    for s in SYMS:
        G, Lw, _, _ = res[s]
        x = pd.Series(G - c * Lw, index=D[s]["dates"]).reindex(ad).fillna(0.0)
        tot = x if tot is None else tot + x
    return tot

def era_stats(x, a, b):
    y = x[(x.index >= a) & (x.index <= b)]
    sd = y.std()
    return y.mean(), (y.mean() / sd * np.sqrt(252) if sd > 0 else np.nan)

ERAS = [("2016-20", "2016-01-01", "2020-12-31"), ("2021-26", "2021-01-01", "2026-12-31")]

def verdict(live, nb, moves):
    """live: metric; nb: list of neighbourhood metrics (excluding live); moves: single +-1 moves."""
    if not live > 0: return "NO EDGE (live <= 0)"
    med = np.median(nb)
    fr = live > 1.5 * med or any(m < 0.5 * live for m in moves)
    pl = np.mean([m >= 0.5 * live for m in nb]) >= 0.7
    return "FRAGILE" if fr else ("PLATEAU" if pl else "MIXED")

def main():
    t0 = time.time(); D = load(); Ps = {s: prep(D[s]) for s in SYMS}
    out = []; P = out.append
    # ---- reproduction
    P("== REPRODUCTION (live setting, per-trade net bp unweighted, both symbols, 1bp RT) ==")
    for lag in (0, 30):
        for la in (True, False):
            r = leg(D, Ps, LIVE, lag=lag, lookahead=la)
            for nm, a, b in [("post-2024-06", "2024-06-01", "2027-01-01"), ("pre-2024-06", "2016-01-01", "2024-05-31")]:
                n = 0; gs = []
                for s in SYMS:
                    # per-trade values are not stored; use daily sums: mean = sum gross / n
                    dd = D[s]["dates"]; m = (dd >= a) & (dd <= b)
                    n += r[s][3][m].sum(); gs.append(r[s][2][m].sum())
                P(f"lag {lag:2d} lookahead-lev {la!s:5} {nm}: n={int(n)} mean net {(sum(gs) - 1.0 * n) / n:+.2f}bp/trade (gross {sum(gs) / n:+.2f})")
    P("reference (noise_recent_2026-10-08.md): post-2024-05 +3.65bp/trade lag0, +3.14 lag30 at 1bp RT (research code uses lookahead-lev=True)")
    # ---- map
    rng = np.random.default_rng(20261010)
    cells = []
    import itertools
    names = ["vm", "L", "bar", "vlb", "tv"]
    for vals in itertools.product(*[GRID[k] for k in names]): cells.append(dict(zip(names, vals)))
    rand = [dict(vm=float(rng.uniform(.5, 1.5)), L=int(rng.integers(7, 22)), bar=int(rng.choice([15, 30, 60])), vlb=int(rng.integers(7, 22)), tv=float(rng.uniform(.01, .03))) for _ in range(900)]
    # cache by (setting) -> metric dict
    cache = {}
    def metric(st):
        key = tuple(st[k] for k in names)
        if key not in cache:
            r = leg(D, Ps, st); res = {}
            for c in (1.0, 4.0):
                x = series(D, r, c)
                for en, a, b in ERAS: res[(c, en)] = era_stats(x, a, b)
            cache[key] = res
        return cache[key]
    # evaluate live + random + grid lazily (grid only live-centred: neighbourhood, profiles) plus the full grid minus tv-axis duplicates
    for st in rand: metric(st)
    for st in cells:
        if st["tv"] == LIVE["tv"]: metric(st)
    P(f"\nsettings evaluated: {len(cache)} ({len(rand)} random + grid at live tv); build time {time.time() - t0:.0f}s")
    live_res = metric(LIVE)
    for c in (1.0, 4.0):
        for en, a, b in ERAS:
            P(f"\n===== cost {c:g}bp RT | era {en} =====")
            lv_bp, lv_sh = live_res[(c, en)]
            rb = np.array([metric(s)[(c, en)][0] for s in rand]); rs = np.array([metric(s)[(c, en)][1] for s in rand])
            P(f"LIVE net {lv_bp:+.2f} bp/day, Sharpe {lv_sh:+.2f} | random settings n={len(rand)}: bp/day median {np.median(rb):+.2f} p10 {np.percentile(rb, 10):+.2f} p90 {np.percentile(rb, 90):+.2f}; "
              f"live percentile bp {np.mean(rb <= lv_bp) * 100:.0f} / Sharpe {np.mean(rs <= lv_sh) * 100:.0f}; share of random settings > 0: {np.mean(rb > 0) * 100:.0f}%")
            for k in ["vm", "L", "bar", "vlb", "tv"]:
                row = []
                for v in GRID[k]:
                    st = dict(LIVE); st[k] = v; bp, sh = metric(st)[(c, en)]; row.append(f"{v}:{bp:+.2f}/{sh:+.2f}")
                P(f"profile {k:3s} (bp/day / Sharpe): " + "  ".join(row))
            # neighbourhood: +-1 grid step on each non-excluded param
            def steps(k):
                g = GRID[k]; i = g.index(LIVE[k]); return [g[j] for j in (i - 1, i, i + 1) if 0 <= j < len(g)]
            nbk = [k for k in names if k not in NB_EXCL]
            nb = []
            for vals in itertools.product(*[steps(k) for k in nbk]):
                st = dict(LIVE); st.update(dict(zip(nbk, vals)))
                if st == LIVE: continue
                nb.append(metric(st)[(c, en)])
            moves = []
            for k in nbk:
                for v in steps(k):
                    if v == LIVE[k]: continue
                    st = dict(LIVE); st[k] = v; moves.append(metric(st)[(c, en)])
            for mi, nm in ((0, "bp/day"), (1, "Sharpe")):
                lv = live_res[(c, en)][mi]; nbv = [m[mi] for m in nb]; mv = [m[mi] for m in moves]
                P(f"neighbourhood n={len(nbv)} ({nm}): median {np.median(nbv):+.2f} min {min(nbv):+.2f} max {max(nbv):+.2f}; keep>=50% of live: {np.mean([x >= .5 * lv for x in nbv]) * 100:.0f}%; "
                  f"worst single move {min(mv):+.2f} ({min(mv) / lv * 100 if lv else float('nan'):.0f}% of live) -> {verdict(lv, nbv, mv)}")
    open(OUT, "w").write("\n".join(out)); print("\n".join(out)); print(f"total {time.time() - t0:.0f}s")

if __name__ == "__main__":
    build() if len(sys.argv) > 1 and sys.argv[1] == "build" else main()
