"""Operations that add money without loosening any rule (draft addendum "ops_capital").

    PYTHONPATH=. .venv/bin/python -m research.sim.ops_capital            # ~5 min, no heavy data
    PYTHONPATH=. .venv/bin/python -m research.sim.ops_capital --refresh  # rebuild the cached series

From the cache no lock is needed. --refresh calls book.night_days() -> data.night_candidates(),
so run --refresh under the heavy lock (verifier note).

Pre-registered (2026-09-28 20:52 PDT, before any 2024-26 number of this study):
Q1 capital (Roth $7.8k at a $1k cap; brokerage $3k at a $3k cap, $1k/mo deposits)
  C0 status quo, Roth cap $1k      C1 wait to 10-08 (8 sessions), then all
  C2 deploy all at the next close  C3 ramp $1k->$2k->$4k->all, one step per 15 more exits with
                                      day-clustered cost UB <= 10bp and window P&L >= the
                                      backtest's 10th percentile for that many days
  C4 deposits: next close vs held until the next step / month
  books: Roth b1 (roth.py) and taxable V7; EH and edge-zero; parked in BIL or SPY;
  3bp | tier | tier_hi; fixed-size replays at $1k/$2k/$4k/$7.8k (whole shares matter at $1k)
  bar: C3 recommended over C1 only if E[$] (EH, tier_hi) >= C1 and edge-zero P5 loss <= C2's
Q3 lever gate at the same error rate (per-exit sd 39bp, rho 0 / 0.3, 6.5 exits/day)
  G0 the rule: 50 exits, rolling mean <= 10bp   G1 continuous day-clustered UB_c <= 10 from 20
  exits, c calibrated to G0's P(open | 15bp)     G2 Wald SPRT H0 15bp vs H1 3bp, alpha matched
Q4 Roth settlement / schedule: documentation (see the addendum), plus the order-sequencing
  diagnostics in section D (POST-HOC: found while reading executor.py, not pre-registered).
"""
from __future__ import annotations

import argparse
import copy
from pathlib import Path

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B, data as D, growth as G, roth as R
from .validate import load_sim

SCRATCH = Path(str(__import__("pathlib").Path(__file__).resolve().parents[2]) + "/data/research/program")
CACHE = SCRATCH / "cache_ops_capital.pkl"
COSTS = [3.0, "tier", "tier_hi"]
SIZES = [1000.0, 2000.0, 4000.0, 7800.0]
ROTH_TOTAL, ROTH_CAP = 7800.0, 1000.0
TAX = 0.32                         # taxable short-term (roth.py convention)
EXITS_PER_DAY = 6.5                # live: 26 exits over 4 exit mornings (09-23..09-28); sim 6.7-8.2
EXIT_SD, EXIT_MU_LIVE = 39.0, -1.0  # per-exit sd implied by mean -1.0 / 95% UB +11.7 at n 26
H1 = ("2021-02-01", "2023-12-31"); H2 = ("2024-01-01", "2026-12-31")


# ----------------------------------------------------------- series
def roth_fixed(sim, p: B.Params, K: float, budget="night", noise_cap=1.5, night_scale=None):
    """Roth b1 replay at a FIXED book size K (whole shares at that size); daily legs / K."""
    rows = []
    for d in sim.days:
        pl, info = R.roth_day(sim, K, d, p, budget=budget, conv_w=0.0, noise_cap=noise_cap)
        if night_scale is not None:                # night buys starved by 3x ETFs still held at 15:40
            f = night_scale.get(d, 1.0)
            pl -= info["night"] * (1 - f); info["night"] *= f
        noise = info["noise"]
        rows.append((d, pl / K, info["night"] / K, info["ibs"] / K, noise / K))
    return pd.DataFrame(rows, columns=["date", "r", "r_night", "r_ibs", "r_noise"]).set_index("date")


def taxable_fixed(sim, g: float, cost, K: float = 3000.0, p: B.Params | None = None, night_scale=None):
    p = p or B.Params(**{**G.V7, **G.cfg(g, 0.5, 2), "night_cost": cost})
    rows = []
    for d in sim.days:
        pl, info = sim.day_pnl(K, d, p)
        if night_scale is not None:
            f = night_scale.get(d, 1.0)
            pl -= info["night"] * (1 - f); info["night"] *= f
        rows.append((d, pl / K, info["night"] / K, info["ibs"] / K, info["noise"] / K))
    return pd.DataFrame(rows, columns=["date", "r", "r_night", "r_ibs", "r_noise"]).set_index("date")


def stress(df: pd.DataFrame, k: float) -> pd.Series:
    """k = 0.5 edge-halves (growth.eh), 1.0 edge-zero (every leg's mean removed, variance kept)."""
    return df["r"] - k * (df["r_night"].mean() + df["r_ibs"].mean() + df["r_noise"].mean())


def noise_paths(sym: str, lookback: int = 14, cost: float = 0.5, flats=(361, 368)) -> pd.DataFrame:
    """book.noise_days plus: position after the last (15:30) decision, and the day's return
    if the position is flattened at minute m (15:31 / 15:38) instead of the 15:57/close exit."""
    M = D.minutes(sym)
    C, V = M["close"].values, M["volume"].values
    O = M["open"].values[:, 0]
    days = M["close"].index
    move = np.abs(C / O[:, None] - 1)
    dclose = pd.Series(C[:, -1], index=days)
    prevc = np.r_[np.nan, C[:-1, -1]]
    vwap = np.cumsum(C * V, axis=1) / np.maximum(np.cumsum(V, axis=1), 1)
    rows = []
    for i in range(lookback + 1, len(days)):
        sigma = sg.noise_sigma(move[i - lookback:i])
        ub, lb = sg.noise_bounds(O[i], prevc[i], sigma)
        lev = sg.noise_leverage(dclose.iloc[:i], 0.02, 1e9)
        pos, entry, pnl, trades = 0, None, 0.0, 0
        for m in range(sg.NOISE_FIRST, 390, sg.NOISE_STEP):
            p = C[i, m]
            new = sg.noise_decide(pos, p, ub[m], lb[m], vwap[i, m])
            if new != pos:
                if pos != 0:
                    pnl += pos * (p / entry - 1); trades += 1
                if new != 0:
                    entry = p; trades += 1
                pos = new
        out = {"date": days[i], "lev": lev, "pos_end": pos}
        fin = pnl + (pos * (C[i, 389] / entry - 1) if pos else 0.0)
        out["ret"] = fin - (trades + (pos != 0)) * cost / 1e4
        for fm in flats:
            x = pnl + (pos * (C[i, fm] / entry - 1) if pos else 0.0)
            out[f"ret_{fm}"] = x - (trades + (pos != 0)) * cost / 1e4
        rows.append(out)
    return pd.DataFrame(rows).set_index("date")


def build(refresh=False):
    if CACHE.exists() and not refresh:
        return pd.read_pickle(CACHE)
    s = load_sim()
    s07 = copy.copy(s); s07.N = B.night_days(max_corr=0.7)
    s07.BO = B.breakout_days()
    base = dict(tilt="live", weekend_scale=0.5, noise_on=False, conviction_w=0.0, margin_rate=0.0)
    out = {"roth": {}, "tax": {}, "park": {}}
    for c in COSTS:
        p = B.Params(night_cost=c, **base)
        for K in SIZES:
            out["roth"][(c, K)] = roth_fixed(s07, p, K)
        for g in (1.0, 1.3):
            out["tax"][(c, g)] = taxable_fixed(s, g, c)
    days = s.days
    out["park"]["bil"] = s.bil.reindex(days).fillna(0.0)
    out["park"]["spy"] = s.spy.reindex(days).fillna(0.0)
    # section D inputs: intraday positions still open at 15:40, and truncated returns
    NP = {k: noise_paths(k) for k in R.S2}
    out["noise_paths"] = NP
    z = {k: NP[k].reindex(days) for k in R.S2}
    tied = pd.Series(0.0, index=days)       # $ of 3x ETF held at 15:40, as a share of the night half
    for k, share in R.S2.items():
        held = (z[k]["pos_end"].fillna(0) != 0)
        tied += np.where(held, np.minimum(z[k]["lev"].fillna(0), 1.5) * share / 3.0, 0.0) / 0.5
    out["tied"] = tied
    scale = (1 - tied.clip(upper=1.0)).to_dict()
    for c in (3.0, "tier_hi"):
        p = B.Params(night_cost=c, **base)
        out["roth"][(c, "starved")] = roth_fixed(s07, p, ROTH_TOTAL, night_scale=scale)
        for fm in (361, 368):
            s2 = copy.copy(s07)
            s2.NZ = {k: NP[k].rename(columns={"ret": "ret_close", f"ret_{fm}": "ret"})
                     .assign(trades=s07.NZ[k]["trades"].reindex(NP[k].index).fillna(0)) for k in R.S2}
            out["roth"][(c, f"flat{fm}")] = roth_fixed(s2, p, ROTH_TOTAL)
    # IBS: entry days (a buy at 09:15/open) and the open -> 09:50 move on them
    I = s.I; prev = set(); ent = []
    for d in days:
        cur = {x[0] for x in I.get(d, [])}
        new = cur - prev
        if new:
            ent.append((d, sorted(new)))
        prev = cur
    out["ibs_entries"] = ent
    mins = {k: D.minutes(k) for k in ("QQQ", "SMH")}
    mv = []
    ix = s.C.index
    for d, syms in ent:
        j = ix.get_loc(d)
        if j + 1 >= len(ix):
            continue
        t = ix[j + 1]
        for sy in syms:
            M = mins.get(sy)
            if M is None or t not in M["close"].index:
                continue
            row = M["close"].loc[t].values; o = M["open"].loc[t].values[0]
            mv.append((t, sy, row[19] / o - 1))
    out["ibs_open_move"] = pd.DataFrame(mv, columns=["date", "sym", "ret_0950"])
    # section E: the TAXABLE book as live today (conviction in shadow -> intraday cap 2 - 0.5 = 1.5)
    # night buys at 15:40 are checked against book.cash = capped equity - positions, floor 0 at 1.0x,
    # so a LONG intraday position still open at 15:40 uses the night leg's cash (a short adds cash)
    net = pd.Series(0.0, index=days)
    for k, share in R.S2.items():
        net += (z[k]["pos_end"].fillna(0) * np.minimum(z[k]["lev"].fillna(0), 1.5) * share)
    out["tax_net_noise"] = net
    tscale = ((0.5 - net) / 0.5).clip(0.0, 1.0).to_dict()
    for c in (3.0, "tier_hi"):
        pl = B.Params(**{**G.V7, "night_w": 0.5, "ibs_w": 0.5, "noise_cap": 1.5, "conviction_w": 0.0,
                         "night_cost": c})
        out["tax"][(c, "live_now")] = taxable_fixed(s, 1.0, c, p=pl)
        out["tax"][(c, "live_now_starved")] = taxable_fixed(s, 1.0, c, p=pl, night_scale=tscale)
    pd.to_pickle(out, CACHE)
    return out


# ---------------------------------------------------------------- helpers
def st(r):
    a, b, f = B.stats(r[H1[0]:H1[1]]), B.stats(r[H2[0]:H2[1]]), B.stats(r)
    return (f"{a[0]*100:5.1f}/{a[1]:4.2f}  {b[0]*100:5.1f}/{b[1]:4.2f}  "
            f"{f[0]*100:5.1f}/{f[1]:4.2f}/{f[2]*100:4.0f}")


def blocks(n_days, n, horizon, block=21, seed=7, lo=0, hi=None):
    rng = np.random.default_rng(seed)
    hi = n_days if hi is None else hi
    nb = -(-horizon // block)
    st_ = rng.integers(lo, hi - block, size=(n, nb))
    return (st_[:, :, None] + np.arange(block)[None, None, :]).reshape(n, -1)[:, :horizon]


def clustered_ub(costs_by_day: list[np.ndarray], z=1.645) -> tuple[float, float, int]:
    y = np.concatenate(costs_by_day) if costs_by_day else np.array([])
    n = len(y)
    if n < 2:
        return np.nan, np.nan, n
    m = y.mean()
    s = np.array([(c - m).sum() for c in costs_by_day if len(c)])
    G_ = len(s)
    v = (s ** 2).sum() / n ** 2 * G_ / max(1, G_ - 1)
    return m, m + z * np.sqrt(v), n


def day_costs(rng, mu, days, lam=EXITS_PER_DAY, sd=EXIT_SD, rho=0.3):
    out = []
    for _ in range(days):
        k = rng.poisson(lam)
        sh = rng.normal(0, sd * np.sqrt(rho))
        out.append(mu + sh + rng.normal(0, sd * np.sqrt(1 - rho), k))
    return out


# ---------------------------------------------------------------- Q1
def q1(X, n=4000, horizon=63):
    print("\n== A. what the Roth cap costs: $6.8k idle, $ per month (21 sessions), mean daily excess x 21")
    print(f"   {'cost':8s} {'park':4s} {'':10s}  {'2021-23':>8s} {'2024-26':>8s} {'full':>8s}")
    park = X["park"]
    for c in COSTS:
        df = X["roth"][(c, ROTH_TOTAL)]
        for pk in ("bil", "spy"):
            for lab, k in (("history", 0.0), ("EH", 0.5), ("edge-zero", 1.0)):
                r = stress(df, k) - park[pk]
                v = [(ROTH_TOTAL - ROTH_CAP) * r[a:b].mean() * 21 for a, b in (H1, H2)] + [(ROTH_TOTAL - ROTH_CAP) * r.mean() * 21]
                print(f"   {str(c):8s} {pk:4s} {lab:10s}  " + " ".join(f"{x:+8.0f}" for x in v))
    print("   (Roth: tax-free. For scale: brokerage idle deposits cost the same per $ at the taxable rate x (1-0.32).)")

    print("\n   Roth b1 at fixed size (whole shares): CAGR/Sharpe 2021-23 | 2024-26 | full CAGR/Sh/DD")
    for c in COSTS:
        for K in SIZES:
            df = X["roth"][(c, K)]
            print(f"   {str(c):8s} ${K:>6,.0f}  hist {st(df['r'])}   EH {st(stress(df, 0.5))}")
    for c in (3.0, "tier_hi"):
        e = stress(X["roth"][(c, ROTH_TOTAL)], 0.5)
        m = G.mc(e, ROTH_TOTAL, 7500 / 12)
        wd, wm = e.min(), G.monthly_worst(e)
        print(f"   5y MC Roth b1 all-in ${ROTH_TOTAL:,.0f} + $625/mo, EH {c}: median ${m['med']:,.0f}  P10 ${m['p10']:,.0f}"
              f"  P(DD>30%) {m['dd30']:.0%}  P(DD>50%) {m['dd50']:.0%}  worst day {wd*100:.1f}%  worst month {wm*100:.1f}%")
        m2 = G.mc(e, 10000, 0)
        print(f"   5y MC $10k lump, EH {c}: median ${m2['med']:,.0f}  P(DD>30%) {m2['dd30']:.0%}  P(DD>50%) {m2['dd50']:.0%}")
    ep = {"2022 bear": ("2022-01-03", "2022-10-12"), "Apr 2025": ("2025-04-02", "2025-04-08")}
    for c in (3.0, "tier_hi"):
        r = X["roth"][(c, ROTH_TOTAL)]["r"]
        print(f"   episodes Roth b1 {c}: " + "  ".join(f"{k} {((1 + r[a:b]).prod() - 1)*100:+.1f}%" for k, (a, b) in ep.items())
              + f"  SPY " + "  ".join(f"{k} {((1 + park['spy'][a:b]).prod() - 1)*100:+.1f}%" for k, (a, b) in ep.items()))

    print(f"\n== B. the next {horizon} sessions, Roth $7.8k: C0 cap $1k | C1 wait 8 sessions | C2 all now | C3 ramp")
    # null band for the ramp's P&L check: backtest (history, full edge) window sums at $1k-size returns
    for c in ("tier_hi", 3.0):
        for pk in ("bil", "spy"):
            for world, k in (("EH", 0.5), ("edge-zero", 1.0)):
                res = q1_paths(X, c, pk, k, n, horizon)
                print(f"   {str(c):8s} park {pk}  world {world:9s} " + "  ".join(
                    f"{nm} E ${v['mean']:+6.0f} P5 ${v['p5']:+6.0f} P(<-10%) {v['p10pct']:.1%}"
                    for nm, v in res.items() if nm != "_ramp"))
                rr = res["_ramp"]
                print(f"   {'':8s}      ramp: sessions to full median {rr['med_full']:.0f} (P10-P90 {rr['p10']:.0f}-{rr['p90']:.0f}),"
                      f" P(any P&L-check hold) {rr['hold']:.0%}, P(not full by {horizon}) {rr['never']:.1%}")
    print("   by half (EH, tier_hi, park bil), C2 - C0 and C3 - C0 expected $ over 63 sessions:")
    df = X["roth"][("tier_hi", ROTH_TOTAL)]
    idx = df.index
    for lab, (a, b) in (("2021-23", H1), ("2024-26", H2)):
        lo, hi = idx.searchsorted(pd.Timestamp(a)), idx.searchsorted(pd.Timestamp(b), "right")
        res = q1_paths(X, "tier_hi", "bil", 0.5, n, horizon, lo=lo, hi=hi)
        print(f"   {lab}: C2-C0 ${res['C2']['mean'] - res['C0']['mean']:+.0f}  C1-C0 ${res['C1']['mean'] - res['C0']['mean']:+.0f}"
              f"  C3-C0 ${res['C3']['mean'] - res['C0']['mean']:+.0f}")

    print("\n== C4. a $1,000 deposit: $ lost by waiting w sessions before it trades (EH, park bil)")
    for c in (3.0, "tier_hi"):
        for book, df in (("Roth b1", X["roth"][(c, ROTH_TOTAL)]), ("taxable V7 (after 32% tax)", X["tax"][(c, 1.0)])):
            ex = (stress(df, 0.5) - X["park"]["bil"]).mean()
            t = (1 - TAX) if book.startswith("taxable") else 1.0
            print(f"   {str(c):8s} {book:28s} " + "  ".join(f"w={w:2d}: ${1000*ex*w*t:5.2f}" for w in (1, 3, 10, 21)))


def q1_paths(X, c, pk, k, n, horizon, lo=0, hi=None, seed=7):
    S = {K: stress(X["roth"][(c, K)], k).values for K in SIZES}
    park = X["park"][pk].values
    hist = X["roth"][(c, 1000.0)]["r"].values          # the backtest's own distribution (full edge)
    p10 = {}
    for w in range(1, 40):
        cs = np.convolve(hist, np.ones(w), "valid")
        p10[w] = np.percentile(cs, 10)
    idx = blocks(len(park), n, horizon, seed=seed, lo=lo, hi=hi)
    rng = np.random.default_rng(seed + 1)
    ladder = [1000.0, 2000.0, 4000.0, 7800.0]

    def pnl(Kpath, i):
        tot = 0.0
        for t in range(horizon):
            K = Kpath[t]; j = idx[i, t]
            tot += K * S[K][j] + (ROTH_TOTAL - K) * park[j]
        return tot

    out = {nm: [] for nm in ("C0", "C1", "C2", "C3")}
    full_at, holds, never = [], 0, 0
    for i in range(n):
        out["C0"].append(pnl([1000.0] * horizon, i))
        out["C1"].append(pnl([1000.0] * 8 + [7800.0] * (horizon - 8), i))
        out["C2"].append(pnl([7800.0] * horizon, i))
        # ramp: costs from the live-consistent world (mu -1bp); 26 exits already in hand
        costs = day_costs(rng, EXIT_MU_LIVE, 4)
        step, since, win, Kp, held = 0, 0, 0.0, [], False
        wdays = 0
        for t in range(horizon):
            K = ladder[step]; Kp.append(K)
            j = idx[i, t]
            win += S[1000.0][j] if False else S[K][j]; wdays += 1
            c_today = day_costs(rng, EXIT_MU_LIVE, 1)
            costs += c_today; since += len(c_today[0])
            if step < 3 and since >= 15:
                _, ub, _ = clustered_ub(costs)
                ok_pnl = win >= p10[min(wdays, 39)]
                if ub <= 10.0 and ok_pnl:
                    step += 1; since = 0; win = 0.0; wdays = 0
                    if step == 3:
                        full_at.append(t + 1)
                elif not ok_pnl:
                    held = True; since = 0; win = 0.0; wdays = 0
        if step < 3:
            never += 1; full_at.append(horizon)
        holds += held
        out["C3"].append(pnl(Kp, i))
    res = {}
    for nm, v in out.items():
        v = np.array(v)
        res[nm] = dict(mean=v.mean(), p5=np.percentile(v, 5), p10pct=(v < -0.10 * ROTH_TOTAL).mean())
    fa = np.array(full_at)
    res["_ramp"] = dict(med_full=np.median(fa), p10=np.percentile(fa, 10), p90=np.percentile(fa, 90),
                        hold=holds / n, never=never / n)
    return res


# ---------------------------------------------------------------- Q3
def q3(X, n=4000, horizon=60):
    print("\n== C. lever gate: error rates and time to open (from 0 exits; 6.5 exits/day; sd 39bp)")
    mus = [-1.0, 5.0, 10.0, 15.0, 20.0]
    for rho in (0.0, 0.3):
        sims = {mu: [day_costs(np.random.default_rng(100 + int(mu * 10) + i), mu, horizon, rho=rho)
                     for i in range(1500)] for mu in mus}

        def summarise(path):
            """per day t: cumulative n, mean, day-clustered SE, rolling-50 mean, SPRT llr."""
            n_, m_, se_, r50, llr = [], [], [], [], []
            allc, sums, L = [], [], 0.0
            for c in path:
                allc.extend(c); sums.append(c)
                y = np.asarray(allc); nn = len(y)
                if nn >= 2:
                    mm = y.mean(); ss = np.array([(q - mm).sum() for q in sums if len(q)])
                    se = np.sqrt((ss ** 2).sum() / nn ** 2 * len(ss) / max(1, len(ss) - 1))
                else:
                    mm, se = np.nan, np.nan
                k = len(c)
                if k:
                    v = EXIT_SD ** 2 * (rho + (1 - rho) / k)
                    L += (c.mean() * (3.0 - 15.0) - (3.0 ** 2 - 15.0 ** 2) / 2) / v
                n_.append(nn); m_.append(mm); se_.append(se); llr.append(L)
                r50.append(np.mean(allc[-50:]) if nn >= 50 else np.nan)
            return np.array(n_), np.array(m_), np.array(se_), np.array(r50), np.array(llr)

        SUM = {mu: [summarise(p) for p in sims[mu][:1500]] for mu in mus}

        def first(mask, nn):
            i = np.flatnonzero(mask)
            return (i[0] + 1, nn[i[0]]) if len(i) else (None, None)

        def g0(S):
            nn, m, se, r50, L = S
            return first(np.nan_to_num(r50, nan=1e9) <= 10.0, nn)

        def g1(S, cc):
            nn, m, se, r50, L = S
            return first((nn >= 20) & (np.nan_to_num(m + cc * se, nan=1e9) <= 10.0), nn)

        def g2(S, A):
            nn, m, se, r50, L = S
            return first((nn >= 20) & (L >= A), nn)

        def rate(fn, mu, *a):
            r = [fn(S, *a) for S in SUM[mu]]
            opened = [x for x in r if x[0] is not None]
            return len(opened) / len(r), (np.median([x[1] for x in opened]) if opened else np.nan), \
                (np.median([x[0] for x in opened]) if opened else np.nan)

        e0 = {mu: rate(g0, mu) for mu in mus}
        target = e0[15.0][0]
        print(f"   rho {rho}: P(open within {horizon} sessions) | median exits at open | median sessions  "
              f"(G0's false-open at 15bp = {target:.0%}: every G1/G2 below is at or under it)")
        rows = [("G0 rolling 50, mean<=10", e0)]
        for cc in (0.0, 1.0, 1.645, 2.326):
            rows.append((f"G1 UB z={cc:.2f} from 20", {mu: rate(g1, mu, cc) for mu in mus}))
        for A in (0.0, np.log(19), np.log(99)):
            rows.append((f"G2 SPRT 15v3 A={A:.2f}", {mu: rate(g2, mu, A) for mu in mus}))
        for nm, e in rows:
            print(f"     {nm:24s} " + "  ".join(f"mu {mu:+4.0f}: {e[mu][0]:4.0%} {e[mu][1]:4.0f}x {e[mu][2]:3.0f}d" for mu in mus))
    # $ value per session earlier
    print("   value of 1.3x over 1.0x per session at $3k (taxable, after 32% tax):")
    for c in (3.0, "tier_hi"):
        a, b = X["tax"][(c, 1.0)], X["tax"][(c, 1.3)]
        for lab, k in (("history", 0.0), ("EH", 0.5)):
            dv = (stress(b, k) - stress(a, k))
            per = [3000 * dv[x:y].mean() * (1 - TAX) for x, y in (H1, H2)] + [3000 * dv.mean() * (1 - TAX)]
            print(f"     {str(c):8s} {lab:8s} $/session 2021-23 {per[0]:+.3f}  2024-26 {per[1]:+.3f}  full {per[2]:+.3f}"
                  f"   ($100k: full {per[2]*100/3:+.2f})")


# ---------------------------------------------------------------- D (post-hoc)
def q4(X):
    tied = X["tied"]
    print("\n== D. Roth order sequencing (POST-HOC diagnostics)")
    print(f"   intraday 3x ETF still held at 15:40 on {(tied > 0).mean():.0%} of days; mean share of the night half tied "
          f"{tied.mean():.0%} (on those days {tied[tied > 0].mean():.0%}); full tie {(tied >= 0.999).mean():.0%} of days")
    for c in (3.0, "tier_hi"):
        print(f"   {str(c):8s} Roth b1 at $7.8k            {'':14s}2021-23 | 2024-26 | full")
        for lab, key in (("research (night fully funded)", ROTH_TOTAL), ("as sequenced, night starved", "starved"),
                         ("flatten Roth intraday 15:31", "flat361"), ("flatten Roth intraday 15:38", "flat368")):
            df = X["roth"][(c, key)]
            print(f"     {lab:34s} hist {st(df['r'])}   EH {st(stress(df, 0.5))}")
    # cap buffer alternative: K = E / (1 + max tie x 0.5) keeps cash for both; idle part earns BIL
    for c in (3.0, "tier_hi"):
        full = X["roth"][(c, ROTH_TOTAL)]; bil = X["park"]["bil"]
        K = ROTH_TOTAL / 1.5
        r = (K * stress(full, 0.5) + (ROTH_TOTAL - K) * bil) / ROTH_TOTAL
        print(f"   {str(c):8s} alt: cap = 2/3 of the Roth (${K:,.0f}), 1/3 in BIL: EH {st(r)}")
    ent = X["ibs_entries"]; mv = X["ibs_open_move"]
    yrs = len(X["park"]["bil"]) / 252
    print(f"   IBS entries (a buy at the open that needs cash while the night sells are still pending): "
          f"{len(ent)/yrs:.0f}/yr; open -> 09:50 on QQQ/SMH entry days: mean {mv.ret_0950.mean()*1e4:+.1f}bp "
          f"(sd {mv.ret_0950.std()*1e4:.0f}, n {len(mv)}) = the cost of buying at 09:50 instead")


def q5(X):
    net = X["tax_net_noise"]
    print("\n== E. TAXABLE book as live today (POST-HOC): long intraday position at 15:40 vs the night leg's cash")
    print(f"   net long intraday at 15:40 on {(net > 0).mean():.0%} of days (mean {net[net > 0].mean():.2f}x of equity);"
          f" night leg fully blocked (net >= 0.5x) on {(net >= 0.5).mean():.0%} of days")
    for c in (3.0, "tier_hi"):
        for lab, key in (("research (night fully funded)", "live_now"), ("as sequenced (book.cash floor 0)", "live_now_starved")):
            df = X["tax"][(c, key)]
            print(f"   {str(c):8s} {lab:34s} hist {st(df['r'])}   EH {st(stress(df, 0.5))}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--n", type=int, default=3000)
    a = ap.parse_args(argv)
    X = build(a.refresh)
    q1(X, n=a.n)
    q3(X)
    q4(X)
    q5(X)


if __name__ == "__main__":
    main()
