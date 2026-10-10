"""TOP2-SIZE (registered research/drafts/round1_prose.md 2026-10-10; descriptive): account sim of the night leg at $2.3k/$10k/$25k/$100k.
Trades = nx live-rule trades (Sharadar, delisted-complete, daily-bar proxy) from nx.collect_trades; cached in data/research/robust/night_live_trades.parquet.
  PYTHONPATH=. .venv/bin/python -m research.sim.top2_size        (first run builds the cache, needs ~/data/sharadar)
Arms: (a) live all-picks, sizing = nx `per` (crowd x tilt x weekend, per-name cap .10 of the LEG, as size_shadow.py/night_sizing do);
 (b) TOP2 = 2 deepest day_ret, SAME leg budget split equally (crowd x weekend, no tilt, no cap); (b-cap) same with the live .10-of-leg cap;
 (c) all-picks (a) scaled by k = std(TOP2 frictionless nightly)/std(a frictionless nightly), Reg-T gross cap 2x equity;
 (d) TOP2 at the nightly LIVE gross of (a), split equally. Whole shares floor(alloc/price) (no 1-share probe), 5bp/side, 0.5 night weight, cash arms cap gross at 1x.
Crowd factor for (b) is approximated min(1,30/n_kept) (raw signal count is not in the trade table); this slightly overstates (b) on crowded nights."""
import sys, pathlib
import numpy as np, pandas as pd
ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/robust"
OUT = ROOT / "data/research/program/top2_size_out.txt"
COST, NW, CAP = 5e-4, 0.5, 0.10
ERAS = {"1999-2015": ("1999-01-04", "2015-12-31"), "2016-26": ("2016-01-04", "2026-09-18")}

def load_trades():
    f = D / "night_live_trades.parquet"
    if f.exists(): return pd.read_parquet(f)
    sys.path.insert(0, str(ROOT))
    from research.sim import shar_surv as ss, nx
    M = ss.load_master(); out = []
    for lo, hi in ERAS.values():
        lo, hi = pd.Timestamp(lo), pd.Timestamp(hi)
        bars = ss.load_bars(lo - pd.Timedelta(days=400), hi + pd.Timedelta(days=10))
        pn = nx.build_panel(bars); del bars
        tr = nx.collect_trades(pn, M, ss.load_actions(), "primary", lo - pd.Timedelta(days=380), hi)["trades"]
        out.append(tr[tr.date >= lo][["date", "ticker", "x", "per", "cu", "adv", "vol20", "day_ret", "ret", "gap", "kind"]])
    tr = pd.concat(out, ignore_index=True); tr.to_parquet(f, index=False); return tr

def sessions():
    s = pd.read_parquet(D / "night_sessions.parquet")["date"]; return pd.DatetimeIndex(s)

def arm_weights(g):
    """per-night fractions of EQUITY (night leg) for each arm, given that night's picks g (sorted most-beaten first)."""
    n = len(g); gap = g["gap"].iloc[0]; crowd = min(1.0, 30.0 / n)
    a = g["per"].to_numpy() * NW
    top = g.nsmallest(2, "day_ret").index; k = len(top)
    idx = {i: j for j, i in enumerate(g.index)}
    def sel(frac):
        w = np.zeros(n)
        for i in top: w[idx[i]] = frac
        return w
    b = sel(NW * crowd * gap / k); bcap = sel(min(NW * crowd * gap / k, CAP * NW)); d = sel(a.sum() / k)
    return dict(a=a, b=b, bcap=bcap, d=d)

def simulate(groups, nights, arm, cap0, k=1.0, maxgross=1.0):
    E = cap0; eq = []; rets = np.zeros(len(nights)); pos = {d: i for i, d in enumerate(nights)}
    peak = E; mdd = 0.0
    for d, (cu, r, w) in groups.items():
        if E <= 0: break
        ww = w[arm] * k
        gross = ww.sum()
        if gross > maxgross: ww = ww * maxgross / gross
        sh = np.floor(ww * E / cu); notional = sh * cu
        pnl = (notional * (r - 2 * COST)).sum(); ret = max(pnl / E, -1.0)
        rets[pos[d]] = ret; E = E * (1 + ret)
    eqs = cap0 * np.cumprod(1 + rets); eqs = np.r_[cap0, eqs]
    dd = (eqs / np.maximum.accumulate(eqs) - 1).min()
    yrs = (nights[-1] - nights[0]).days / 365.25
    cagr = (eqs[-1] / cap0) ** (1 / yrs) - 1 if eqs[-1] > 0 else -1.0
    sd = rets.std()
    return dict(cagr=cagr, mdd=dd, sharpe=rets.mean() / sd * np.sqrt(252) if sd > 0 else 0.0, worst=rets.min(), final=eqs[-1], std=sd)

def main():
    tr = load_trades(); S = sessions(); L = []
    def P(s=""): print(s, flush=True); L.append(s)
    tr = tr.sort_values(["date", "day_ret"]).reset_index(drop=True)
    P("TOP2-SIZE: night leg, nx live-rule trades, 5bp/side, night weight 0.5, whole shares. Leg per-name cap .10 of the LEG (code), not of equity.")
    for era, (lo, hi) in ERAS.items():
        t = tr[(tr.date >= lo) & (tr.date <= hi)]; nights = S[(S >= lo) & (S <= hi)]
        groups = {}
        for d, g in t.groupby("date"):
            g = g.reset_index(drop=True); groups[d] = (g["cu"].to_numpy(), g["ret"].to_numpy(), arm_weights(g))
        # frictionless per-unit-equity nightly series for the vol match
        fr = {a: pd.Series({d: float((w[a] * (r - 2 * COST)).sum()) for d, (cu, r, w) in groups.items()}).reindex(nights, fill_value=0.0) for a in ("a", "b")}
        kk = fr["b"].std() / fr["a"].std()
        P(f"\n== {era}: {len(t)} picks, {len(groups)} pick-nights of {len(nights)}; frictionless nightly std a {fr['a'].std()*1e4:.0f}bp b {fr['b'].std()*1e4:.0f}bp -> k = {kk:.2f}; "
          f"mean a {fr['a'].mean()*1e4:+.1f} b {fr['b'].mean()*1e4:+.1f} bp/night of equity; mean gross a {np.mean([w['a'].sum() for _,(c,r,w) in groups.items()]):.2f} b {np.mean([w['b'].sum() for _,(c,r,w) in groups.items()]):.2f}; "
          f"(c) mean gross {np.mean([min(2.0, w['a'].sum()*kk) for _,(c,r,w) in groups.items()]):.2f}x")
        P(f"  {'capital':>8} {'arm':<22} {'CAGR':>8} {'maxDD':>8} {'Sharpe':>7} {'worst':>8} {'final$':>12}")
        for cap0 in (2300, 10000, 25000, 100000):
            for name, arm, k, mg in [("(a) live all-picks", "a", 1.0, 1.0), ("(b) TOP2", "b", 1.0, 1.0), ("(b-cap) TOP2 live cap", "bcap", 1.0, 1.0),
                                     ("(c) all-picks x k Reg-T", "a", kk, 2.0), ("(d) TOP2 @ live gross", "d", 1.0, 1.0)]:
                m = simulate(groups, nights, arm, cap0, k, mg)
                P(f"  {cap0:>8} {name:<22} {m['cagr']*100:+7.1f}% {m['mdd']*100:+7.1f}% {m['sharpe']:7.2f} {m['worst']*100:+7.1f}% {m['final']:12,.0f}")
            if cap0 == 100000: P("  (the $100k rows are the capacity line: whole-share rounding is negligible there)")
    OUT.write_text("\n".join(L))

if __name__ == "__main__":
    main()
