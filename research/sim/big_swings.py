"""Study AE: the anatomy of the biggest intraday swings, and a held-out test of what predicts their direction.

    PYTHONPATH=. .venv/bin/python -m research.sim.big_swings

Stamp: research/drafts/round1_prose.md, "Round 15" (commit 0f4f3ef). SIP daily panel, open auction -> close.
Part 1 describes big swings (|z| >= 3, z = ln(C/O) / sigma20) on both halves; Part 2 selects up to 3 features on
2021-23 only and judges AE1..AE5 on 2024-26 only. spy_gap_z is the same for every name on a day, so it has no
cross-sectional decile: it is reported in Part 1 (pooled deciles) and cannot be a Part 2 selector.
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

from . import book as B
from . import data as D
from .night_filings import ROOT

OUT = ROOT / "data/research/program/big_swings_out.txt"
DISC, HOLD = ("2021-01-01", "2023-12-31"), ("2024-01-01", "2026-12-31")
FEATS = ["gap_z", "r1_z", "ibs1", "r5_z", "range1_z", "rvol1", "hi20", "vol20", "ladv"]
ADV_MIN, PX_MIN, NMAX, T_SEL = 20e6, 5.0, 10, 3.0
_fs = None


def log(*a):
    s_ = " ".join(str(x) for x in a)
    print(s_, flush=True)
    _fs.write(s_ + "\n"); _fs.flush()


def build():
    P = D.panel()
    O, H, L, C, V = (P[k].astype(float) for k in ("open", "high", "low", "close", "volume"))
    syms = C.columns
    # raw price factor (piecewise constant per symbol) where raw_close.parquet has the name
    r = pd.read_parquet(D.RAW_CLOSE)
    r = r[(r.raw_close > 0) & (r.adj_close > 0)]
    f = (r.assign(f=r.raw_close / r.adj_close, date=pd.to_datetime(r.date))
         .pivot_table(index="date", columns="symbol", values="f", aggfunc="last"))
    f = f.reindex(index=C.index, columns=syms).ffill().bfill()
    praw = C * f.fillna(1.0)
    lr = np.log(C / C.shift(1))
    sig = lr.rolling(20).std().shift(1)
    adv = (C * V).rolling(20).mean().shift(1)
    U = (adv >= ADV_MIN) & (praw.shift(1) >= PX_MIN) & (sig > 0) & O.notna() & C.notna() & (O > 0)
    F = {
        "gap_z": np.log(O / C.shift(1)) / sig,
        "r1_z": lr.shift(1) / sig,
        "ibs1": ((C - L) / (H - L)).shift(1),
        "r5_z": np.log(C / C.shift(5)).shift(1) / (sig * np.sqrt(5)),
        "range1_z": np.log(H / L).shift(1) / sig,
        "rvol1": V.shift(1) / V.rolling(20).mean().shift(1),
        "hi20": C.shift(1) / H.rolling(20).max().shift(1),
        "vol20": sig * np.sqrt(252),
        "ladv": np.log(adv),
    }
    spy = C["SPY"] if "SPY" in syms else D.etf()["close"]["SPY"].reindex(C.index)
    spyo = O["SPY"] if "SPY" in syms else D.etf()["open"]["SPY"].reindex(C.index)
    ssig = np.log(spy / spy.shift(1)).rolling(20).std().shift(1)
    spy_gap = np.log(spyo / spy.shift(1)) / ssig
    z = np.log(C / O) / sig
    return dict(O=O, H=H, L=L, C=C, U=U, sig=sig, adv=adv, praw=praw, F=F, z=z, spy_gap=spy_gap)


def deciles(X: pd.DataFrame, U: pd.DataFrame) -> pd.DataFrame:
    return np.ceil(X.where(U).rank(axis=1, pct=True) * 10).clip(1, 10)


def part1(d):
    U, z = d["U"], d["z"]
    log("== Part 1: anatomy of big swings (|z| >= 3, z = ln(close/open) / sigma20)\n")
    for lab, (a, b) in (("2021-23", DISC), ("2024-26", HOLD)):
        u = U.loc[a:b]; zz = z.loc[a:b].where(u)
        up, dn = (zz >= 3), (zz <= -3)
        n = int(u.values.sum())
        log(f"## {lab}: {n:,} stock-days, big up {int(up.values.sum()):,} ({up.values.sum() / n:.2%}), "
            f"big down {int(dn.values.sum()):,} ({dn.values.sum() / n:.2%}); ~{(up | dn).values.sum() / len(u):.1f}/day")
        log(f"{'feature':9s} | {'UP: lift top/bot':>16s} | {'DOWN: lift top/bot':>18s} | "
            f"{'P(|z|>=3) d1 .. d10':>20s} | {'mean z d1 .. d10':>16s}")
        base = (up | dn).values.sum() / n
        for k in FEATS:
            dc = deciles(d["F"][k].loc[a:b], u)
            row = []
            for ev in (up, dn):
                e = ev.values & np.isfinite(dc.values)
                sh = [np.mean(dc.values[e] == q) / 0.10 for q in (10, 1)]
                row.append(f"{sh[0]:5.1f}x / {sh[1]:4.1f}x")
            big = (up | dn).values
            pb = [np.nanmean(big[dc.values == q]) for q in (1, 10)]
            mz = [np.nanmean(zz.values[dc.values == q]) for q in (1, 10)]
            log(f"{k:9s} | {row[0]:>16s} | {row[1]:>18s} | {pb[0] / base:6.1f}x .. {pb[1] / base:5.1f}x"
                f"{'':5s} | {mz[0]:+.3f} .. {mz[1]:+.3f}")
        # market gap: pooled deciles (same value for every name on a day)
        sg_ = d["spy_gap"].loc[a:b]
        q = pd.qcut(sg_.rank(method="first"), 10, labels=False) + 1
        day_up = up.sum(axis=1) / u.sum(axis=1); day_dn = dn.sum(axis=1) / u.sum(axis=1)
        day_z = zz.mean(axis=1)
        log(f"spy_gap_z (pooled deciles over days): big-up rate d1 {day_up[q == 1].mean():.2%} d10 "
            f"{day_up[q == 10].mean():.2%}; big-down d1 {day_dn[q == 1].mean():.2%} d10 {day_dn[q == 10].mean():.2%};"
            f" mean z d1 {day_z[q == 1].mean():+.3f} d10 {day_z[q == 10].mean():+.3f}")
        # top 10 per day by |z|
        rk = zz.abs().rank(axis=1, ascending=False)
        top = (rk <= 10).values
        log(f"top-10 |z| per day: {np.mean(zz.values[top] > 0):.0%} up; median |z| {np.nanmedian(np.abs(zz.values[top])):.1f}; "
            f"in gap_z top/bottom decile {np.mean(deciles(d['F']['gap_z'].loc[a:b], u).values[top] == 10):.0%} / "
            f"{np.mean(deciles(d['F']['gap_z'].loc[a:b], u).values[top] == 1):.0%}; in vol20 top decile "
            f"{np.mean(deciles(d['F']['vol20'].loc[a:b], u).values[top] == 10):.0%}\n")


def daily_t(x: pd.Series) -> float:
    x = x.dropna()
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 2 and x.std() > 0 else np.nan


def select(d):
    U, O, C = d["U"], d["O"], d["C"]
    a, b = DISC
    r = (C / O - 1).loc[a:b].where(U.loc[a:b])
    mu = r.mean(axis=1)
    rows = []
    for k in FEATS:
        dc = deciles(d["F"][k].loc[a:b], U.loc[a:b])
        for q in (1, 10):
            ex = r.where(dc == q).mean(axis=1) - mu
            rows.append((k, q, float(ex.mean() * 1e4), daily_t(ex)))
    T = pd.DataFrame(rows, columns=["feat", "decile", "excess_bp", "t"])
    log("== Part 2 selection (2021-23 only): extreme-decile open->close excess vs the day's universe mean")
    for _, x in T.sort_values("t", key=np.abs, ascending=False).iterrows():
        log(f"  {x.feat:9s} d{int(x.decile):<2d} {x.excess_bp:+7.1f}bp  t {x.t:+6.2f}")
    best = T.loc[T.groupby("feat").t.apply(lambda s: s.abs().idxmax())]
    sel = best[best.t.abs() >= T_SEL].sort_values("t", key=np.abs, ascending=False).head(3)
    log("selected: " + (", ".join(f"{x.feat} d{int(x.decile)} {'long' if x.t > 0 else 'short'} (t {x.t:+.1f})"
                                  for _, x in sel.iterrows()) or "none") + "\n")
    return [(x.feat, int(x.decile), 1 if x.t > 0 else -1) for _, x in sel.iterrows()]


class Arr:
    def __init__(self, d):
        self.ix = d["C"].index
        self.O, self.H, self.L, self.C = (d[k].values for k in ("O", "H", "L", "C"))
        self.sig, self.adv, self.px = d["sig"].values, d["adv"].values, d["praw"].shift(1).values
        self.gap = (d["O"] / d["C"].shift(1) - 1).values

    def ret(self, t, j, s, stop):
        o, h, l, c, sg = self.O[t, j], self.H[t, j], self.L[t, j], self.C[t, j], self.sig[t, j]
        if not stop:
            return s * (c / o - 1)
        st, tg = np.exp(-0.5 * sg), np.exp(1.0 * sg)
        if s > 0:
            return np.where(l <= o * st, st - 1, np.where(h >= o * tg, tg - 1, c / o - 1))
        su, tl = np.exp(0.5 * sg), np.exp(-1.0 * sg)
        return np.where(h >= o * su, -(su - 1), np.where(l <= o * tl, 1 - tl, -(c / o - 1)))

    def cost(self, t, j, model):
        return 2 * B.cost_bps(model, self.px[t, j], self.adv[t, j]) / 1e4


def picks(d, rule, U):
    """{day index: (cols, dirs)} for a rule: ('one', feat, decile, s) or ('combo', [(feat, dec, s)...])."""
    out = {}
    if rule[0] == "one":
        _, k, q, s = rule
        X = d["F"][k].where(U)
        pct = X.rank(axis=1, pct=True)
        ext = pct if q == 10 else 1 - pct
        ok = ext >= 0.9
    else:
        sc = 0
        for k, q, s in rule[1]:
            pct = d["F"][k].where(U).rank(axis=1, pct=True)
            ext = pct if q == 10 else 1 - pct
            sc = sc + s * (ext - 0.5)
        ext, ok = sc.abs(), sc.notna()
    gap = (d["O"] / d["C"].shift(1) - 1)
    E, OK, G = ext.values, ok.values, gap.values
    SC = sc.values if rule[0] == "combo" else None
    for t in range(len(E)):
        m = OK[t] & np.isfinite(E[t])
        if not m.any():
            continue
        dirs_all = np.sign(SC[t]) if SC is not None else np.full(E.shape[1], rule[3])
        m &= ~((dirs_all < 0) & (G[t] <= -0.10))              # SSR: no short at a -10% open
        idx = np.where(m)[0]
        if not len(idx):
            continue
        idx = idx[np.argsort(-E[t, idx])][:NMAX]
        out[t] = (idx, dirs_all[idx])
    return out


def evaluate(A, P, stop, model, period, rng=None, q5=None, U=None, _pool={}):
    a, b = (A.ix.searchsorted(pd.Timestamp(x)) for x in period)
    per_day, n = {}, 0
    for t, (j, s) in P.items():
        if not (a <= t < b):
            continue
        if rng is not None:        # placebo: same count and directions, random names of the same vol quintile
            jj2 = j.copy()
            for i, jj in enumerate(j):
                key = (t, q5[t, jj])
                if key not in _pool:
                    _pool[key] = np.where(U[t] & (q5[t] == q5[t, jj]))[0]
                p = _pool[key]
                if len(p):
                    jj2[i] = p[rng.integers(len(p))]
            j = jj2
        r = A.ret(t, j, s, stop) - A.cost(t, j, model)
        per_day[A.ix[t]] = np.nanmean(r); n += len(j)
    x = pd.Series(per_day)
    return float(x.mean()) if len(x) else np.nan, daily_t(x), n, len(x)


def part2(d, sel):
    if not sel:
        log("Part 2: no feature reached |t| >= 3 in 2021-23 -> no variant (N stays 619)")
        return
    U = d["U"]
    A = Arr(d)
    Um = U.values
    q5 = np.ceil(d["F"]["vol20"].where(U).rank(axis=1, pct=True) * 5).fillna(0).values
    rules = {f"AE{i + 1} {k} d{q} {'long' if s > 0 else 'short'}": (("one", k, q, s), False)
             for i, (k, q, s) in enumerate(sel)}
    rules["AE4 combo"] = (("combo", sel), False)
    rules["AE5 combo + stop .5σ / target 1σ"] = (("combo", sel), True)
    log("== Part 2 held-out test (2024-26); discovery 2021-23 shown for check (4)")
    rng = np.random.default_rng(15)
    for name, (rule, stop) in rules.items():
        P = picks(d, rule, U)
        res = {}
        for per_lab, per in (("21-23", DISC), ("24-26", HOLD)):
            for m in ("tier", "tier_hi"):
                res[(per_lab, m)] = evaluate(A, P, stop, m, per)
        gross = evaluate(A, P, stop, 0.0, HOLD)
        pl = [evaluate(A, P, stop, "tier", HOLD, rng, q5, Um)[0] for _ in range(200)]
        pct = float(np.mean(np.array(pl) < res[("24-26", "tier")][0]) * 100)
        c = [res[("24-26", "tier_hi")][0] > 0, res[("24-26", "tier")][1] >= 2.0, pct >= 95,
             res[("21-23", "tier_hi")][0] > 0]
        nn = res[("24-26", "tier")]
        log(f"## {name}: {nn[2] / max(nn[3], 1):.1f} names/day on {nn[3]} days (2024-26)")
        log(f"  gross 24-26 {gross[0] * 1e4:+.1f}bp/trade | net tier 21-23 {res[('21-23', 'tier')][0] * 1e4:+.1f}"
            f" (t {res[('21-23', 'tier')][1]:+.1f}), 24-26 {nn[0] * 1e4:+.1f} (t {nn[1]:+.1f}) | tier_hi 21-23 "
            f"{res[('21-23', 'tier_hi')][0] * 1e4:+.1f}, 24-26 {res[('24-26', 'tier_hi')][0] * 1e4:+.1f} | placebo pct {pct:.0f}")
        log(f"  PASS 1 tier_hi>0 {c[0]}, 2 t>=2 {c[1]}, 3 placebo {c[2]}, 4 discovery {c[3]} -> "
            f"{'SHADOW' if all(c) else 'DEAD'}")
        # capacity: $ per name vs the opening auction (1.6% of ADV)
        ad = np.concatenate([A.adv[t, j] for t, (j, _) in P.items() if t >= A.ix.searchsorted(pd.Timestamp(HOLD[0]))])
        log("  % of opening auction per name (median): "
            + ", ".join(f"${E:,}: {np.nanmedian(0.05 * E / (0.016 * ad)) * 100:.2f}%" for E in (25_000, 100_000, 500_000))
            + "\n")


def main():
    global _fs
    _fs = open(OUT, "w")
    t0 = time.time()
    log("== Study AE (Round 15), started", pd.Timestamp.now(), "\n")
    d = build()
    part1(d)
    sel = select(d)
    part2(d, sel)
    log(f"done in {time.time() - t0:4.0f} s")


if __name__ == "__main__":
    main()
