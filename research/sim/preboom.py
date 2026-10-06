"""Study PB — pre-boom predictability (tail-probability). Pre-registered in
research/drafts/round1_prose.md (N 825 -> 826) BEFORE any conditional outcome was read.

Question: does an observable condition at close t raise P(a stock enters the extreme
right tail of future returns), not P(positive mean return)? The already-killed momentum
family is not re-run. One look. No deployment.
"""
from __future__ import annotations

import pickle

import numpy as np
import pandas as pd

ROOT = "/Users/andrewlau/Documents/Code/Projects/swing-trader"
PANEL = f"{ROOT}/data/research/night/panel.pkl"
OUT = f"{ROOT}/data/research/program/preboom_out.txt"

DISC = ("2021-01-01", "2023-12-31")
OOS = ("2024-01-01", "2026-06-30")
BOOM20, BOOM60, DOWN20, ZBOOM = 0.30, 0.50, -0.30, 6.0
QD = 0.10  # extreme decile

LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def load():
    from research.sim.theme_explosion import stock_mask
    P = pickle.load(open(PANEL, "rb"))
    C = P["close"].astype("float32")
    O = P["open"].astype("float32")
    H = P["high"].astype("float32")
    L = P["low"].astype("float32")
    V = P["volume"].astype("float32")
    R = C.pct_change(fill_method=None)
    dv = C * V
    adv = dv.rolling(20, min_periods=15).median()
    nbars = C.notna().rolling(120, min_periods=1).sum()
    sm = stock_mask(C.columns)
    E = (C >= 3) & (adv >= 5e6) & (nbars >= 120) & sm[None, :]
    spy = R["SPY"].fillna(0)
    return dict(C=C, O=O, H=H, L=L, V=V, R=R, dv=dv, adv=adv, E=E, spy=spy)


def win_mask(idx, span):
    return (idx >= pd.Timestamp(span[0])) & (idx <= pd.Timestamp(span[1]))


def cond_bottom(score, E, q=QD):
    return score.where(E).rank(axis=1, pct=True).le(q)


def cond_top(score, E, q=QD):
    return score.where(E).rank(axis=1, pct=True).ge(1 - q)


def build_conditions(D):
    C, O, H, L, V, R, dv, E, spy = (D[k] for k in ("C", "O", "H", "L", "V", "R", "dv", "E", "spy"))
    out = {}
    vol20 = R.rolling(20, min_periods=15).std()
    vol60 = R.rolling(60, min_periods=30).std()
    out["volcomp"] = cond_bottom(vol20 / vol60, E)
    hl = (H - L) / C
    out["rngcomp"] = cond_bottom(hl.rolling(5, min_periods=3).mean() / hl.rolling(60, min_periods=30).mean(), E)
    out["voldry"] = cond_bottom(dv.rolling(5, min_periods=3).mean() / dv.rolling(60, min_periods=30).mean(), E)
    upV = V.where(R > 0, 0.0)
    dnV = V.where(R < 0, 0.0)
    out["accumbias"] = cond_top((upV.rolling(20, min_periods=15).sum() - dnV.rolling(20, min_periods=15).sum())
                                / V.rolling(20, min_periods=15).sum(), E)
    am = (R.abs() / dv.replace(0, np.nan))
    out["amihudrise"] = cond_top(am.rolling(10, min_periods=8).mean() / am.rolling(60, min_periods=30).mean(), E)
    resid = R.sub(spy, axis=0)
    out["ivolrise"] = cond_top(resid.rolling(10, min_periods=8).std() / resid.rolling(60, min_periods=30).std(), E)
    mR = R.rolling(20, min_periods=15).mean()
    mS = spy.rolling(20, min_periods=15).mean()
    cov = R.mul(spy, axis=0).rolling(20, min_periods=15).mean() - mR.mul(mS, axis=0)
    corr = cov / (R.rolling(20, min_periods=15).std().mul(spy.rolling(20, min_periods=15).std(), axis=0))
    out["corrbreak"] = cond_bottom(corr, E)
    gap = (O / C.shift(1) - 1).abs().gt(0.02)
    out["gapfreq"] = cond_top(gap.rolling(20, min_periods=15).mean(), E)
    out["ret20top"] = cond_top(C / C.shift(20) - 1, E)          # benchmark (momentum disguise)
    out["nearhigh"] = cond_top(C / C.rolling(252, min_periods=120).max(), E)  # benchmark
    return out, vol20


def _ffill_matrix(events, values, dates, cols):
    m = events.pivot_table(index="pub", columns="sym", values=values, aggfunc="last")
    return m.reindex(index=dates, columns=cols).ffill()


def build_structural(D):
    C, E = D["C"], D["E"]
    dates, cols = C.index, C.columns
    out = {}
    try:
        from research.sim.jump_reddit import si
        S = si()
        short = _ffill_matrix(S, "short", dates, cols)
        out["sincrease"] = cond_top(short / short.shift(1).replace(0, np.nan) - 1, E)
        out["dtchigh"] = cond_top(_ffill_matrix(S, "dtc", dates, cols), E)
    except Exception as e:  # noqa
        log("  [si] skipped:", e)
    try:
        from research.sim.jump_ftd import ftd
        out["ftdspike"] = cond_top(_ffill_matrix(ftd(), "frac", dates, cols), E)
    except Exception as e:  # noqa
        log("  [ftd] skipped:", e)
    try:
        from research.sim.jump_insider import buys
        B = buys()
        B = B[B.sym.isin(cols)]
        ev = B.assign(one=1.0).pivot_table(index="fd", columns="sym", values="one", aggfunc="max")
        ev = ev.reindex(index=dates, columns=cols).fillna(0.0)
        out["insiderbuy"] = (ev.rolling(10, min_periods=1).max() > 0) & E
    except Exception as e:  # noqa
        log("  [insider] skipped:", e)
    try:
        from research.sim.deep_search import earn_events
        ev = earn_events()
        ev = ev[ev.sym.isin(cols)]
        m = ev.assign(one=1.0).pivot_table(index="d", columns="sym", values="one", aggfunc="max")
        m = m.reindex(index=dates, columns=cols).fillna(0.0)
        fut = m.iloc[::-1].rolling(5, min_periods=1).max().iloc[::-1].shift(-1)
        out["earnprox"] = (fut > 0) & E
    except Exception as e:  # noqa
        log("  [earn] skipped:", e)
    return out


def metrics(cond, boom, F, valid, mae_mat):
    c = cond & valid
    b = boom & valid
    n = int(c.values.sum())
    if n < 200:
        return None
    base = float(b.values[valid.values].mean())
    pc = float(b.values[c.values].mean())
    pnc = float(b.values[(valid & ~cond).values].mean())
    rec = float((b & c).values.sum()) / max(1, int(b.values.sum()))
    return dict(n=n, base=base, pc=pc, pnc=pnc, lift=pc / base if base else np.nan, recall=rec,
                fpr=1 - pc, med_fwd=float(np.nanmedian(F.values[c.values])),
                p_down=float(np.mean(F.values[c.values] <= DOWN20)),
                mae=float(np.nanmedian(mae_mat.values[c.values])))


def volmatched(cond, boom, valid, vol20, q=10):
    """P(boom) expected for cond cells, matched on (date, sigma20 decile)."""
    dec = np.ceil(vol20.where(valid).rank(axis=1, pct=True).values * q)
    vv = valid.values
    bb = boom.values & vv
    cc = cond.values & vv
    exp = np.full(bb.shape, np.nan, "float32")
    for k in range(1, q + 1):
        m = (dec == k) & vv
        cnt = m.sum(axis=1)
        rate = np.divide((bb & m).sum(axis=1), cnt, out=np.full(len(cnt), np.nan), where=cnt > 0)
        for i in np.flatnonzero(cnt > 0):
            exp[i, m[i]] = rate[i]
    return float(np.nanmean(exp[cc]))


def run():
    log("Study PB — pre-boom predictability. Base rates calibrated on unconditional only.")
    D = load()
    C, L, E = D["C"], D["L"], D["E"]
    idx = C.index
    F20 = (C.shift(-20) / C - 1).astype("float32")
    F60 = (C.shift(-60) / C - 1).astype("float32")
    boom20 = F20.ge(BOOM20)
    boom60 = F60.ge(BOOM60)
    down20 = F20.le(DOWN20)
    vol20 = D["R"].rolling(20, min_periods=15).std()
    zboom = (F20 / vol20).ge(ZBOOM)
    targets = {"boom20(+30%)": (boom20, F20), "boom60(+50%)": (boom60, F60),
               "down20(-30%)": (down20, F20), "z20(>=6sig)": (zboom, F20)}
    mae_mat = (L.iloc[::-1].rolling(20, min_periods=1).min().iloc[::-1] / C - 1)
    conds, vol20 = build_conditions(D)
    log("building structural conditions ...")
    conds.update(build_structural(D))
    names = list(conds.keys())
    log(f"conditions: {names}")

    for span, tag in ((DISC, "DISCOVERY 2021-2023"), (OOS, "OOS 2024-2026H1")):
        wm = win_mask(idx, span)
        log("\n" + "=" * 104)
        log(f"{tag}   ({span[0]}..{span[1]})")
        log("=" * 104)
        valid0 = E & wm[:, None]
        for tname, (boom, F) in targets.items():
            valid = valid0 & F.notna()
            base = float(boom.values[valid.values].mean())
            log(f"\n--- target {tname}  base={base:.3%}  n_valid={int(valid.values.sum()):,}")
            log(f"{'condition':12s} {'n':>9s} {'P|cond':>8s} {'P|~c':>8s} {'lift':>6s} {'recall':>7s} "
                f"{'volmatch':>9s} {'medFwd':>8s} {'Pdown':>7s} {'MAE':>7s}")
            for nm in names:
                m = metrics(conds[nm], boom, F, valid, mae_mat)
                if not m:
                    continue
                vm = volmatched(conds[nm], boom, valid, vol20)
                log(f"{nm:12s} {m['n']:9,d} {m['pc']:8.2%} {m['pnc']:8.2%} {m['lift']:6.2f} "
                    f"{m['recall']:7.2%} {vm:9.2%} {m['med_fwd']:8.2%} {m['p_down']:7.2%} {m['mae']:7.1%}")
    open(OUT, "w").write("\n".join(LOG) + "\n")
    log(f"\nwrote {OUT}")


if __name__ == "__main__":
    run()
