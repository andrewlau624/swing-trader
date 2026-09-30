"""Round 16, Study AF: size the conviction trade by predicted magnitude (round1_prose.md Round 16 AF).

    PYTHONPATH=. .venv/bin/python -m research.sim.conviction_af        # ~2-4 min; reads minutes + intraday_bp_res.pkl

The conviction trade (book.breakout_days: TQQQ, the day's first noise-band breakout if strength >= 0.341σ, out on a
return inside the band / through VWAP, else 15:57) at 0.5 of equity is the baseline. Variants change only the day's
weight, from features known at 09:30 (regular-hours QQQ minutes, Cboe VIX close of d-1). The day's conviction allowance
is reserved at the open, so the QQQ/SMH noise cap that day is growth.cfg(1.0, w_conv, mult)['noise_cap'].
Book = cached intraday_bp B3 moderate10c (and B1 V7), M2 base, tier_hi, plus the additive daily increment.
"""
from __future__ import annotations

import pickle

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import data as D
from . import growth as G
from . import program_books as PB
from . import taxable_frontier as TF

SCR = TF.SCRATCH
BP_RES = SCR / "intraday_bp_res.pkl"
N_PROGRAM = 623
FIT = ("2016-02-01", "2023-12-31")
HALVES = (("2016-20", "2016-01-01", "2020-12-31"), ("2021-23", "2021-01-01", "2023-12-31"),
          ("2024-26", "2024-01-01", "2026-12-31"), ("2016-23", "2016-01-01", "2023-12-31"))
SIZES = (2300.0, 25e3, 100e3, 500e3)
CONV_SIDE = {"ship": 1.5, "th": 3.0}          # TQQQ bps per side (measured ~1.5; stressed 2x)
NOISE_FILL = {"ship": 0.5, "th": 1.5}         # QQQ/SMH bps per fill (sim 0.5; tier_hi 1.5)
VARIANTS = {  # label: (score, multipliers low / mid / high)
    "AF1 mhat .5/1/1.5": ("mhat", (0.5, 1.0, 1.5)),
    "AF2 mhat 0/1/2": ("mhat", (0.0, 1.0, 2.0)),
    "AF3 VIX .5/1/1.5": ("vix", (0.5, 1.0, 1.5)),
    "AF4 mhat inverse 1.5/1/.5": ("mhat", (1.5, 1.0, 0.5)),
}


# ------------------------------------------------------------------ trades with detail
def conv_trades(sym: str = "TQQQ", lookback: int = 14, strength_min: float = B.STRENGTH_MIN) -> pd.DataFrame:
    """book.breakout_days with the trade's detail: entry/exit minute, direction, strength, gross return,
    and the traded ETF's $ volume in the entry minute."""
    M = D.minutes(sym)
    C, V = M["close"].values, M["volume"].values
    O = M["open"].values[:, 0]
    days = M["close"].index
    move = np.abs(C / O[:, None] - 1)
    prevc = np.r_[np.nan, C[:-1, -1]]
    vwap = np.cumsum(C * V, axis=1) / np.maximum(np.cumsum(V, axis=1), 1)
    rows = []
    for i in range(lookback + 1, len(days)):
        sig = sg.noise_sigma(move[i - lookback:i])
        ub, lb = sg.noise_bounds(O[i], prevc[i], sig)
        pos, e, strength, x, m0, xm = 0, None, 0.0, None, None, 389
        for m in range(sg.NOISE_FIRST, 390, sg.NOISE_STEP):
            p = C[i, m]
            if pos == 0:
                pos, strength = sg.breakout_strength(p, ub[m], lb[m], sig[m])
                e, m0 = p, m
                if pos and strength < strength_min:
                    break
            elif (pos == 1 and p < max(ub[m], vwap[i, m])) or (pos == -1 and p > min(lb[m], vwap[i, m])):
                x, xm = p, m; break
        if pos == 0 or strength < strength_min:
            continue
        x = C[i, 389] if x is None else x
        rows.append((days[i], m0, xm, pos, strength, pos * (x / e - 1), V[i, m0] * C[i, m0]))
    return pd.DataFrame(rows, columns=["date", "m0", "xm", "dir", "strength", "gross", "dvol_m0"]).set_index("date")


# ------------------------------------------------------------------ features at 09:30
def open_features() -> pd.DataFrame:
    """QQQ regular-hours daily bars built from RTH minutes (09:30-16:00 only), Cboe VIX close of d-1."""
    M = D.minutes("QQQ")
    O = M["open"].iloc[:, 0]; C = M["close"].iloc[:, -1]
    H = M["high"].max(axis=1); L = M["low"].min(axis=1); V = M["volume"].sum(axis=1)
    lr = np.log(C / C.shift(1))
    s20 = lr.rolling(20).std().shift(1)
    f = pd.DataFrame(index=C.index)
    f["absgap"] = (np.log(O / C.shift(1)) / s20).abs()
    f["range1"] = (np.log(H / L) / s20).shift(1)
    f["rvol1"] = (V / V.rolling(20).mean()).shift(1)
    vx = pd.read_csv(SCR / "cboe" / "VIX.csv")
    vx = pd.Series(vx["CLOSE"].values, index=pd.to_datetime(vx["DATE"], format="%m/%d/%Y"))
    f["vix"] = vx.reindex(vx.index.union(C.index)).ffill().reindex(C.index).shift(1) / 100
    f["absoc"] = np.log(C / O).abs()
    return f.dropna()


def fit_mhat(f: pd.DataFrame):
    X = f[["absgap", "range1", "rvol1", "vix"]]
    X = np.c_[np.ones(len(X)), X.values]
    fit = (f.index >= FIT[0]) & (f.index <= FIT[1])
    beta, *_ = np.linalg.lstsq(X[fit], f["absoc"].values[fit], rcond=None)
    mhat = pd.Series(X @ beta, index=f.index)
    return beta, mhat


def r2(y, yhat):
    y, yhat = np.asarray(y), np.asarray(yhat)
    return 1 - ((y - yhat) ** 2).sum() / ((y - y.mean()) ** 2).sum()


def terciles(score: pd.Series) -> tuple[pd.Series, np.ndarray]:
    ins = score[FIT[0]:FIT[1]]
    cuts = np.quantile(ins, [1 / 3, 2 / 3])
    return pd.Series(np.digitize(score.values, cuts), index=score.index), cuts


# ------------------------------------------------------------------ increments
def noise_legs(cost: str) -> dict:
    out = {}
    for s in G.S2:
        z = B.noise_days(s, cost=0.5).copy()
        z["ret"] = z["ret"] - z["trades"] * (NOISE_FILL[cost] - 0.5) / 1e4
        out[s] = z
    return out


def day_increment(w: pd.Series, conv_net: pd.Series, NZ: dict, mult: float, w0: float = 0.5) -> pd.Series:
    """Daily return increment vs the shipped flat w0: conviction (w - w0) x net, plus the noise-cap change."""
    idx = w.index
    cn = conv_net.reindex(idx).fillna(0.0)
    d = (w - w0) * cn
    cap0 = G.cfg(1.0, w0, mult)["noise_cap"]
    capv = w.map(lambda x: G.cfg(1.0, x, mult)["noise_cap"])
    for s, share in G.S2.items():
        z = NZ[s].reindex(idx)
        lev, ret = z["lev"].fillna(0.0), z["ret"].fillna(0.0)
        d = d + share * (np.minimum(lev, capv) - np.minimum(lev, cap0)) * ret
    return d


def per_half(x: pd.Series) -> str:
    return "  ".join(f"{lab} {x[a:b].mean()*252*100:+6.2f}pp (t {TF.nw_t(x[a:b]):+5.2f})" for lab, a, b in HALVES)


def main():
    f = open_features()
    beta, mhat = fit_mhat(f)
    print("m̂ = OLS |ln C/O| on [1, |gap_z|, range1_z, rvol1, VIX/100], QQQ 2016-02..2023-12:")
    print("  beta", np.round(beta, 5))
    for lab, a, b in HALVES:
        ff = f[a:b]
        print(f"  {lab}: R² of m̂ for QQQ |open->close| {r2(ff.absoc, mhat[a:b]):.3f}  (n {len(ff)})")
    tm, cuts_m = terciles(mhat)
    tv, cuts_v = terciles(f["vix"])
    print(f"  m̂ cuts {np.round(cuts_m*1e4, 1)} bp; VIX cuts {np.round(cuts_v*100, 2)}")

    T = conv_trades()
    bo_ship = B.breakout_days()
    chk = (T["gross"] - 2 * CONV_SIDE["ship"] / 1e4).reindex(bo_ship.index)
    print(f"\ncheck vs book.breakout_days: n {len(T)} vs {len(bo_ship)}, max |diff| {np.nanmax(np.abs(chk - bo_ship)):.2e}")
    T = T.join(pd.DataFrame({"mhat": mhat, "tm": tm, "tv": tv, "vix": f["vix"]}), how="left")
    print(f"trades with features: {T['tm'].notna().sum()} of {len(T)} (first {T.index[0].date()})")
    for lab, a, b in HALVES:
        t = T[a:b].dropna(subset=["mhat"])
        print(f"  {lab}: corr(m̂, the trade's |gross|) {np.corrcoef(t.gross.abs(), t.mhat)[0,1]:+.3f}")

    print("\n== conviction trade by m̂ tercile (net at 1.5bp/side): n | trades/yr | win | mean |gross| | EV/trade | t | EV/|gross|")
    for lab, a, b in HALVES:
        t = T[a:b].dropna(subset=["tm"])
        yrs = len(f[a:b]) / 252
        for k in range(3):
            u = t[t.tm == k]; net = u.gross - 3e-4
            print(f"  {lab} T{k+1}: n {len(u):4d} | {len(u)/yrs:5.1f}/yr | win {(net>0).mean():4.0%} | |g| {u.gross.abs().mean()*1e4:6.1f}bp | "
                  f"EV {net.mean()*1e4:+6.1f}bp | t {net.mean()/net.std(ddof=1)*np.sqrt(len(u)):+5.2f} | EV/|g| {net.mean()/u.gross.abs().mean():+.3f}")
    print("\n== same by VIX_{d-1} tercile")
    for lab, a, b in HALVES:
        t = T[a:b].dropna(subset=["tv"])
        for k in range(3):
            u = t[t.tv == k]; net = u.gross - 3e-4
            print(f"  {lab} V{k+1}: n {len(u):4d} | win {(net>0).mean():4.0%} | |g| {u.gross.abs().mean()*1e4:6.1f}bp | "
                  f"EV {net.mean()*1e4:+6.1f}bp | t {net.mean()/net.std(ddof=1)*np.sqrt(len(u)):+5.2f}")

    # ---------------- increments
    bp = pickle.load(open(BP_RES, "rb"))["res"]
    days = f.index[f.index >= "2016-02-01"]
    res = {}
    for cost in ("ship", "th"):
        NZ = noise_legs(cost)
        conv_net = T["gross"] - 2 * CONV_SIDE[cost] / 1e4
        for mult in (2.0, 4.0):
            for vl, (score, mults) in VARIANTS.items():
                tt = (tm if score == "mhat" else tv).reindex(days)
                w = 0.5 * tt.map(dict(enumerate(mults))).astype(float)
                inc = day_increment(w, conv_net, NZ, mult)
                # placebo: permute the day's multiplier across sessions
                cand = {m_: day_increment(pd.Series(0.5 * m_, index=days), conv_net, NZ, mult) for m_ in set(mults)}
                Cm = np.c_[[cand[m_].values for m_ in mults]].T         # days x 3
                lab_ = tt.values.astype(int)
                rng = np.random.default_rng(16)
                sims = np.array([Cm[np.arange(len(days)), rng.permutation(lab_)].mean() for _ in range(1000)])
                pct = float((sims < inc.mean()).mean() * 100)
                res[(cost, mult, vl)] = dict(inc=inc, pct=pct, w=w)
    # ---------------- report
    for mult in (2.0, 4.0):
        print(f"\n== increment vs flat 0.5, mult {mult:g} (noise cap base {G.cfg(1.0, 0.5, mult)['noise_cap']:.2f}), per year and NW t")
        for cost in ("ship", "th"):
            for vl in VARIANTS:
                x = res[(cost, mult, vl)]
                print(f"  {cost:4s} {vl:26s} {per_half(x['inc'])} | full t {TF.nw_t(x['inc']):+5.2f} | placebo {x['pct']:5.1f} "
                      f"| mean w {x['w'].mean():.3f}")

    print("\n== books (2021-26, tier_hi, mult 2): base vs variant  pre-tax halves | maxDD | MC P(DD>50%) (EH, after tax) | DSR")
    out = {}
    for bl in ("B3 moderate10c", "B1 V7"):
        b = bp[(bl, "M2 base", "tier_hi")]
        r0, e0 = b["r"], b["eh"]
        m0 = b["mc"]
        print(f"  {bl:15s} base {PB.halves(r0)} maxDD {B.stats(r0)[2]*100:5.1f}  P50 {m0['dd50']:.1%} P30 {m0['dd30']:.1%} med ${m0['med']:,.0f}")
        for vl in VARIANTS:
            inc = res[("th", 2.0, vl)]["inc"].reindex(r0.index).fillna(0.0)
            rv = r0 + inc
            ev = e0 + inc - 0.5 * inc.mean()
            mc = TF.mc_tax(ev, 0.35, start=3000, monthly=1000)
            ds = PB.dsr(inc, n_trials=N_PROGRAM)
            out[(bl, vl)] = dict(r=rv, mc=mc, dsr=ds)
            print(f"  {bl:15s} {vl:26s} {PB.halves(rv)} maxDD {B.stats(rv)[2]*100:5.1f} (d {100*(B.stats(rv)[2]-B.stats(r0)[2]):+4.1f}) "
                  f"P50 {mc['dd50']:.1%} P30 {mc['dd30']:.1%} med ${mc['med']:,.0f} | DSR {ds['dsr']:.2f}", flush=True)

    print("\n== money: mean increment x E, $/yr (tier_hi, mult 2; full 2016-26 and 2024-26), taxable after 35%")
    for vl in VARIANTS:
        inc = res[("th", 2.0, vl)]["inc"]
        a, b = inc.mean() * 252, inc["2024":].mean() * 252
        print(f"  {vl:26s} " + " | ".join(f"${E/1e3:g}k: {a*E:+8,.0f} ({b*E:+8,.0f}) AT {0.65*a*E:+8,.0f}" for E in SIZES))

    print("\n== capacity: TQQQ notional / TQQQ $ volume in the entry minute (2016-26 | 2024-26 only)")
    for E in SIZES:
        for mx in (1.0, 2.0):
            share = E * 0.5 * mx / T["dvol_m0"].replace(0, np.nan)
            s2 = share["2024":]
            print(f"  E ${E:>9,.0f} weight {0.5*mx:.1f}: median {share.median():6.2%}  p95 {share.quantile(.95):6.2%} | "
                  f"2024-26 median {s2.median():6.2%}  p95 {s2.quantile(.95):6.2%}  max {s2.max():6.2%}")
    pickle.dump(dict(res=res, out=out, T=T, beta=beta, cuts_m=cuts_m, cuts_v=cuts_v),
                open(SCR / "conviction_af_res.pkl", "wb"))


if __name__ == "__main__":
    main()
