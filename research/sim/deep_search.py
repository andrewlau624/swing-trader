"""Round 29 (deep search), pre-registered in round1_prose.md (commit d4df5d1): DS2/DS3 noise grid, DS5 seasonal
night size, DS4 days-to-cover tilt, DS1 earnings-announcement premium.

    PYTHONPATH=. .venv/bin/python -m research.sim.deep_search noise|season|dtc|earn

Output: data/research/program/deep_search_<part>_out.txt
"""
from __future__ import annotations

import dataclasses
import pathlib
import sys

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import data as D
from . import growth as G
from . import max_edge as M
from .auction_audit import with_rets
from .program_books import dsr
from .validate import load_sim

ROOT = pathlib.Path(__file__).resolve().parents[2]
N_PROG = 752
H1, H2 = ("2021-01-01", "2023-12-31"), ("2024-01-01", "2026-12-31")
LIVE = G.cfg(1.0, 0.0, 2.48)


def out(part):
    f = open(ROOT / f"data/research/program/deep_search_{part}_out.txt", "w")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); f.write(x + "\n"); f.flush()
    return log


def base_sim():
    s = load_sim(raw_price=True)
    T = pd.read_pickle(ROOT / "data/research/program/auction_audit_picks.pkl")
    s.N = with_rets(B.night_days(raw_price=True, max_corr=0.7), T, "ret_auc")
    s.I = B.ibs_days()
    return s


def params(cost=2.5, **kw):
    return B.Params(**{**G.V7, **LIVE, "night_cost": cost, **kw})


def signflip_pct(x, n=1000, seed=9):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    rng = np.random.default_rng(seed)
    sims = np.array([(x * rng.choice([-1, 1], size=len(x))).mean() for _ in range(n)])
    return float((sims < x.mean()).mean() * 100)


def half_inc(d):
    return [d[a:z].mean() * 252 * 100 for a, z in (H1, H2)]


def book_table(log, s, mk, lab, extra_pct=None):
    """mk(s) -> (Params, restore fn). Replays base vs variant at the three sizes and both costs; judges at 2.5bp."""
    res = {}
    for cost in (2.5, "tier_hi"):
        for E in M.SIZES:
            base = M.replay(s, E, params(cost))
            p, undo = mk(s, cost)
            r = M.replay(s, E, p)
            undo()
            res[(cost, E)] = (base, r)
            sb, sr = B.stats(base), B.stats(r)
            h = half_inc(r - base)
            log(f"  [{lab}] {cost}/side ${E/1e3:.1f}k  base {sb[0]*100:5.1f}%/{sb[1]:4.2f}/{sb[2]*100:4.0f}  "
                f"var {sr[0]*100:5.1f}%/{sr[1]:4.2f}/{sr[2]*100:4.0f}  inc {(sr[0]-sb[0])*100:+5.2f}pp "
                f"(${(sr[0]-sb[0])*E:+,.0f}/yr)  halves {h[0]:+5.2f}/{h[1]:+5.2f}pp  dDD {(sr[2]-sb[2])*100:+4.1f}")
    base, r = res[(2.5, 10000.0)]
    d = r - base
    t, pct = M.nw_t(d.values), signflip_pct(d.values)
    halves_ok = all(min(half_inc(res[(2.5, E)][1] - res[(2.5, E)][0])) > 0 for E in M.SIZES)
    ddd = (B.stats(r)[2] - B.stats(base)[2]) * 100
    pdd = M.p_dd50(r)
    q = dsr(d, n_trials=N_PROG)
    log(f"  [{lab}] $10k 2.5bp: NW t {t:+.2f}  sign-flip {pct:.0f}%  dDD {ddd:+.1f}pp  P(DD>50) {pdd:.1%}  "
        f"DSR(inc) {q['dsr']:.3f}" + ("" if extra_pct is None else f"  feature/matched placebo {extra_pct:.0f}%"))
    ok = halves_ok and t >= 2 and pct >= 95 and ddd >= -2 and pdd <= 0.05 and (extra_pct is None or extra_pct >= 95)
    return ok, d


# ------------------------------------------------------------------ DS2 / DS3: noise grid
MIDDAY = {150, 180, 210, 240}            # 12:00, 12:30, 13:00, 13:30 (minutes from the open)


def noise_grid(sym, slots, block=frozenset(), lookback=14, cost=0.5, target_vol=0.02):
    """B.noise_days with the decision slots as a parameter; at a blocked slot only exits to flat are allowed."""
    Mn = D.minutes(sym)
    C, V = Mn["close"].values, Mn["volume"].values
    O = Mn["open"].values[:, 0]
    days = Mn["close"].index
    move = np.abs(C / O[:, None] - 1)
    dclose = pd.Series(C[:, -1], index=days)
    prevc = np.r_[np.nan, C[:-1, -1]]
    vwap = np.cumsum(C * V, axis=1) / np.maximum(np.cumsum(V, axis=1), 1)
    rows = []
    for i in range(lookback + 1, len(days)):
        sigma = sg.noise_sigma(move[i - lookback:i])
        ub, lb = sg.noise_bounds(O[i], prevc[i], sigma)
        lev = sg.noise_leverage(dclose.iloc[:i], target_vol, 1e9)
        pos, entry, pnl, trades = 0, None, 0.0, 0
        for m in slots:
            p = C[i, m]
            new = sg.noise_decide(pos, p, ub[m], lb[m], vwap[i, m])
            if m in block and new != 0 and new != pos:
                new = 0
            if new != pos:
                if pos != 0:
                    pnl += pos * (p / entry - 1); trades += 1
                if new != 0:
                    entry = p; trades += 1
                pos = new
        if pos != 0:
            pnl += pos * (C[i, 389] / entry - 1); trades += 1
        rows.append((days[i], pnl - trades * cost / 1e4, lev, trades))
    return pd.DataFrame(rows, columns=["date", "ret", "lev", "trades"]).set_index("date")


def noise_unit(NZ, cap):
    parts = [share * np.minimum(NZ[s]["lev"], cap) * NZ[s]["ret"] for s, share in G.S2.items()]
    return pd.concat(parts, axis=1).sum(axis=1, min_count=1).fillna(0)


def run_noise():
    log = out("noise")
    s = base_sim()
    live_slots = list(range(sg.NOISE_FIRST, 390, sg.NOISE_STEP))
    assert live_slots[-1] == 360
    variants = {"G1 15-min": (list(range(sg.NOISE_FIRST, 390, 15)), frozenset()),
                "G2 no midday entries": (live_slots, frozenset(MIDDAY))}
    cap = LIVE["noise_cap"]
    for cost in (0.5, 1.0):
        base = {sym: noise_grid(sym, live_slots, cost=cost) for sym in G.S2}
        chk = noise_grid("QQQ", live_slots, cost=0.5) if cost == 0.5 else None
        if chk is not None:
            ref = B.noise_days("QQQ", cost=0.5)
            assert np.allclose(ref["ret"].values, chk["ret"].values), "grid copy differs from book.noise_days"
        ub = noise_unit(base, cap)
        log(f"\n== noise cost {cost}bp/side; base trades/day QQQ {base['QQQ'].trades.mean():.2f} SMH {base['SMH'].trades.mean():.2f}")
        for lab, (slots, block) in variants.items():
            V = {sym: noise_grid(sym, slots, block, cost=cost) for sym in G.S2}
            d = noise_unit(V, cap) - ub
            by = d.groupby(d.index.year).mean() * 252 * 100
            log(f"  {lab}: trades/day QQQ {V['QQQ'].trades.mean():.2f}; unit inc 2016-20 {d[:'2020-12-31'].mean()*25200:+.2f}pp  "
                f"2021-23 {d['2021':'2023'].mean()*25200:+.2f}  2024-26 {d['2024':].mean()*25200:+.2f}  | by year "
                + " ".join(f"{y}:{v:+.1f}" for y, v in by.items()))
            if cost != 0.5:
                continue
            hold_ok = d[:"2020-12-31"].mean() > 0
            extra = None
            if block:
                rng = np.random.default_rng(11); real = d["2021":].mean(); sims = []
                for k in range(100):
                    blk = frozenset(rng.choice(live_slots, 4, replace=False).tolist())
                    P = {sym: noise_grid(sym, live_slots, blk, cost=cost) for sym in G.S2}
                    sims.append((noise_unit(P, cap) - ub)["2021":].mean())
                extra = float((np.array(sims) < real).mean() * 100)

            def mk(s_, c, V=V):
                old = s_.NZ
                s_.NZ = {**old, **V}
                return params(c), (lambda: setattr(s_, "NZ", old))
            ok, _ = book_table(log, s, mk, lab, extra)
            log(f"  [{lab}] 2016-20 holdout unit increment > 0: {hold_ok}  -> {'PASS' if ok and hold_ok else 'DEAD'}")


# ------------------------------------------------------------------ DS5: seasonal night size
def season_days(days):
    days = pd.DatetimeIndex(days)
    sel = []
    for (y, m), g in pd.Series(days, index=days).groupby([days.year, days.month]):
        if m == 12:
            sel += list(g.index[-10:])
        elif m in (3, 6, 9):
            sel += list(g.index[-3:])
    return set(sel)


def scaled(N, dates, k=1.5):
    return {d: (dataclasses.replace(nd, frac=nd.frac * k) if d in dates else nd) for d, nd in N.items()}


def run_season():
    log = out("season")
    s = base_sim()
    N0 = s.N
    cal = s.days
    S = season_days(cal)
    nights = [d for d in S if d in N0]
    log(f"DS5 S1: {len(S)} seasonal sessions in {cal[0].date()}..{cal[-1].date()}, {len(nights)} with night picks")
    x = pd.Series({d: float(np.mean(nd.ret)) for d, nd in N0.items()})
    log(f"  mean pick return (auction) seasonal nights {x[x.index.isin(S)].mean()*1e4:+.1f}bp vs other {x[~x.index.isin(S)].mean()*1e4:+.1f}bp")
    # matched placebo: same count of random sessions per calendar year, ×1.5, $10k 2.5bp increment
    base = M.replay(s, 10000.0, params())
    s.N = scaled(N0, S)
    real = (M.replay(s, 10000.0, params()) - base).mean()
    rng = np.random.default_rng(5); sims = []
    years = pd.Series(cal, index=cal).groupby(cal.year)
    cnt = pd.Series(1, index=list(S)).groupby(pd.DatetimeIndex(list(S)).year).sum()
    for k in range(200):
        R = set()
        for y, g in years:
            R |= set(rng.choice(g.values, int(cnt.get(y, 0)), replace=False).tolist()) if cnt.get(y, 0) else set()
        s.N = scaled(N0, {pd.Timestamp(v) for v in R})
        sims.append((M.replay(s, 10000.0, params()) - base).mean())
    s.N = N0
    extra = float((np.array(sims) < real).mean() * 100)

    def mk(s_, c):
        s_.N = scaled(N0, S)
        return params(c), (lambda: setattr(s_, "N", N0))
    ok, d = book_table(log, s, mk, "S1", extra)
    log(f"  S1 -> {'PASS' if ok else 'DEAD'}")


# ------------------------------------------------------------------ DS4: days-to-cover tilt
SI_DIR = ROOT / "data/research/night/finra_si"


def dtc_table():
    import glob
    fr = [pd.read_parquet(f) for f in sorted(glob.glob(str(SI_DIR / "*.parquet")))]
    x = pd.concat(fr, ignore_index=True)
    x["settle"] = pd.to_datetime(x.settlementDate)
    x["pub"] = x.settle + pd.offsets.BDay(10)
    x["dtc"] = pd.to_numeric(x.daysToCoverQuantity, errors="coerce")
    bad = ~np.isfinite(x.dtc)
    adv = pd.to_numeric(x.averageDailyVolumeQuantity, errors="coerce")
    x.loc[bad, "dtc"] = pd.to_numeric(x.currentShortPositionQuantity, errors="coerce")[bad] / adv[bad].where(adv[bad] > 0)
    return x[["symbolCode", "pub", "dtc"]].rename(columns={"symbolCode": "sym"}).dropna().sort_values("pub")


def dtc_features(N, T):
    rows = [(d, str(sym)) for d, nd in N.items() for sym in nd.syms]
    P = pd.DataFrame(rows, columns=["d", "sym"]).sort_values("d")
    m = pd.merge_asof(P, T, left_on="d", right_on="pub", by="sym", direction="backward")
    m = m[(m.d - m.pub).dt.days <= 45]                         # stale (> one cycle late) = missing
    return {(a, b): np.log1p(max(v, 0.0)) for a, b, v in zip(m.d, m.sym, m.dtc)}


def dtc_tilt(N, F, mu, sd, shuffle_rng=None):
    date_of = {id(nd): d for d, nd in N.items()}

    def f(nd):
        d = date_of[id(nd)]
        live = sg.night_tilt(nd.vol20, nd.day_ret, 0.25)
        v = np.array([F.get((d, str(s)), np.nan) for s in nd.syms], float)
        if shuffle_rng is not None:
            v = shuffle_rng.permutation(v)
        z = np.where(np.isfinite(v), (v - mu) / sd, 0.0)
        w = live * np.clip(1 + 0.25 * z, 0.25, 2.0)
        return w * live.mean() / w.mean()
    return f


def run_dtc():
    log = out("dtc")
    s = base_sim(); N0 = s.N
    F = dtc_features(N0, dtc_table())
    npk = sum(len(nd.syms) for nd in N0.values())
    A = np.array([v for (d, _), v in F.items() if d <= pd.Timestamp("2023-12-31")], float)
    mu, sd = float(np.mean(A)), float(np.std(A))
    log(f"DS4 Q1: DTC coverage {len(F)}/{npk} picks ({len(F)/npk:.0%}); log1p(DTC) 2021-23 mu {mu:.2f} sd {sd:.2f}")
    # descriptive: per-pick auction return by DTC tercile, per half
    rows = [(d, str(sym), F.get((d, str(sym)), np.nan), float(nd.ret[j]), float(nd.vol20[j]), float(np.log(nd.price[j])))
            for d, nd in N0.items() for j, sym in enumerate(nd.syms)]
    X = pd.DataFrame(rows, columns=["d", "sym", "x", "ret", "vol20", "lp"]).dropna()
    X["t"] = pd.qcut(X.x, 3, labels=["lo", "mid", "hi"])
    for lab, (a, z) in (("2021-23", H1), ("2024-26", H2)):
        g = X[(X.d >= a) & (X.d <= z)].groupby("t", observed=True).ret.mean() * 1e4
        log(f"  {lab} per-pick auction ret by DTC tercile (bp, gross): " + "  ".join(f"{k} {v:+.1f}" for k, v in g.items()))
    log("  Spearman corr of DTC with vol20 {:+.2f}, log price {:+.2f}".format(
        X.x.corr(X.vol20, method="spearman"), X.x.corr(X.lp, method="spearman")))
    base = M.replay(s, 10000.0, params())
    real = (M.replay(s, 10000.0, params(tilt=dtc_tilt(N0, F, mu, sd))) - base).mean()
    rng = np.random.default_rng(13)
    sims = [(M.replay(s, 10000.0, params(tilt=dtc_tilt(N0, F, mu, sd, rng))) - base).mean() for _ in range(200)]
    extra = float((np.array(sims) < real).mean() * 100)

    def mk(s_, c):
        return params(c, tilt=dtc_tilt(N0, F, mu, sd)), (lambda: None)
    ok, _ = book_table(log, s, mk, "Q1", extra)
    log(f"  Q1 -> {'PASS' if ok else 'DEAD'}")


# ------------------------------------------------------------------ DS1: earnings-announcement premium
EARN_DIR = ROOT / "data/research/night/earn_cal"


def earn_events():
    import glob
    import json
    rows = []
    for f in sorted(glob.glob(str(EARN_DIR / "*.json"))):
        d = pd.Timestamp(pathlib.Path(f).stem)
        for r in json.load(open(f)):
            sym = str(r.get("symbol", "")).strip().upper().replace("/", ".")
            if sym:
                rows.append((d, sym))
    return pd.DataFrame(rows, columns=["d", "sym"]).drop_duplicates()


def earn_panel():
    P = D.panel()
    P2 = pd.read_pickle(ROOT / "data/research/night/panel2020.pkl")
    out = {}
    for k in ("open", "close", "volume"):
        a, b = P2[k], P[k]
        out[k] = pd.concat([a[a.index < b.index[0]], b]).astype("float64")
    return out


def earn_table(ev, P):
    O, C, V = P["open"], P["close"], P["volume"]
    cal = C.index; pos = {d: i for i, d in enumerate(cal)}
    adv = (C * V).rolling(20, min_periods=15).mean()
    cols = {s: j for j, s in enumerate(C.columns)}
    Ov, Cv, Av = O.values, C.values, adv.values
    sp = cols["SPY"]
    out = []
    for d, sym in zip(ev.d, ev.sym):
        i, j = pos.get(d), cols.get(sym)
        if i is None or j is None or i < 21 or i + 1 >= len(cal):
            continue
        c0, o1, c1, o2 = Cv[i - 1, j], Ov[i, j], Cv[i, j], Ov[i + 1, j]
        if not np.all(np.isfinite([c0, o1, c1, o2])) or min(c0, o1, c1, o2) <= 0:
            continue
        w = o2 / c0 - 1
        if abs(w) > 0.5:
            continue
        s0, s1, s2, s3 = Cv[i - 1, sp], Ov[i, sp], Cv[i, sp], Ov[i + 1, sp]
        out.append((d, cal[i - 1], sym, Av[i - 1, j], w, o1 / c0 - 1 + o2 / c1 - 1,
                    s3 / s0 - 1, s1 / s0 - 1 + s3 / s2 - 1))
    return pd.DataFrame(out, columns=["d", "entry", "sym", "adv", "w", "on2", "spy_w", "spy_on2"])


VARIANTS = {"E1 liquid, close d-1 -> open d+1": ("liq", "w", 2),
            "E2 thin, close d-1 -> open d+1": ("thin", "w", 2),
            "E3 liquid, two overnights only": ("liq", "on2", 4)}


def ex_net(X, col, sides, cost=2.5):
    spy = X["spy_w"] if col == "w" else X["spy_on2"]
    return X[col] - spy - sides * cost / 1e4


def bucket(X, b):
    return X[(X.adv >= 2e7)] if b == "liq" else X[(X.adv >= 2e6) & (X.adv < 2e7)]


def run_earn():
    log = out("earn")
    ev = earn_events(); P = earn_panel()
    log(f"DS1: {len(ev)} calendar rows, {ev.d.min().date()}..{ev.d.max().date()}, {ev.sym.nunique()} symbols")
    X = earn_table(ev, P)
    log(f"  events with clean windows: {len(X)}; liquid {len(bucket(X, 'liq'))}, thin {len(bucket(X, 'thin'))}")
    # placebo pool: every stock-session not within 10 sessions of an announcement of that stock
    cal = P["close"].index; pos = {d: i for i, d in enumerate(cal)}
    near = {}
    for d, sym in zip(ev.d, ev.sym):
        i = pos.get(d)
        if i is not None:
            near.setdefault(sym, set()).update(range(i - 10, i + 11))
    for lab, (b, col, sides) in VARIANTS.items():
        Y = bucket(X, b).copy()
        Y["x"] = ex_net(Y, col, sides)
        ser = Y.groupby("entry").x.mean()
        hv = [Y[(Y.d >= a) & (Y.d <= z)].x.mean() * 1e4 for a, z in (H1, H2)]
        pre = Y[Y.d < "2021-01-01"].x
        t, pct = M.nw_t(ser.values), signflip_pct(ser.values)
        log(f"\n  {lab}: n {len(Y)} events, {len(ser)} entry dates; mean net excess {Y.x.mean()*1e4:+.1f}bp "
            f"(median {Y.x.median()*1e4:+.1f}); halves {hv[0]:+.1f} / {hv[1]:+.1f}bp; 2020 (pre) {pre.mean()*1e4:+.1f}bp n {len(pre)}")
        log("    by year: " + "  ".join(f"{y}:{v*1e4:+.1f}" for y, v in Y.groupby(Y.d.dt.year).x.mean().items()))
        log(f"    gross (no cost) {(Y.x.mean() + sides*2.5e-4)*1e4:+.1f}bp; tier_hi-ish at 10bp/side {(Y.x.mean() - sides*7.5e-4)*1e4:+.1f}bp")
        log(f"    entry-date series NW t {t:+.2f}; sign-flip {pct:.0f}%")
        # feature placebo: same stock, random non-announcement session in the same year
        O, C = P["open"].values, P["close"].values
        cols = {s: j for j, s in enumerate(P["close"].columns)}; sp = cols["SPY"]
        rng = np.random.default_rng(17)
        elig = {}
        for sym, y in set(zip(Y.sym, Y.d.dt.year)):
            idx = [i for i, dd in enumerate(cal) if dd.year == y and 21 <= i < len(cal) - 1 and i not in near.get(sym, ())]
            elig[(sym, y)] = np.array(idx)
        keys = list(zip(Y.sym, Y.d.dt.year))
        sims = []
        for k in range(200):
            vals = []
            for sym, y in keys:
                e = elig[(sym, y)]
                if len(e) == 0:
                    continue
                i = int(rng.choice(e)); j = cols[sym]
                c0, o1, c1, o2 = C[i - 1, j], O[i, j], C[i, j], O[i + 1, j]
                if not np.all(np.isfinite([c0, o1, c1, o2])) or min(c0, o1, c1, o2) <= 0:
                    continue
                if col == "w":
                    r = o2 / c0 - 1; s_ = O[i + 1, sp] / C[i - 1, sp] - 1
                else:
                    r = o1 / c0 - 1 + o2 / c1 - 1; s_ = O[i, sp] / C[i - 1, sp] - 1 + O[i + 1, sp] / C[i, sp] - 1
                if abs(r) > 0.5:
                    continue
                vals.append(r - s_ - sides * 2.5e-4)
            sims.append(np.mean(vals))
        sims = np.array(sims)
        fp = float((sims < Y.x.mean()).mean() * 100)
        log(f"    feature placebo (same stocks, random non-announcement dates): mean {sims.mean()*1e4:+.1f}bp "
            f"[5-95% {np.percentile(sims,5)*1e4:+.1f}..{np.percentile(sims,95)*1e4:+.1f}]; real beats {fp:.0f}%")
        ok = min(hv) > 0 and t >= 2 and pct >= 95 and fp >= 95
        log(f"    (a)-(d) -> {'PASS, go to crosses (e) and book (f)' if ok else 'DEAD'}")
        Y.to_pickle(ROOT / f"data/research/program/deep_search_earn_{lab[:2]}.pkl")


if __name__ == "__main__":
    {"noise": run_noise, "season": run_season, "dtc": run_dtc, "earn": run_earn}[sys.argv[1]]()
