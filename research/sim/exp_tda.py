"""Study TDA (N 1245): Gidea-Katz (2018) persistent-homology crash warning as a book exposure switch, one run.
Pre-reg research/drafts/round1_prose.md "Amendment - DEEP round 1", N 1245 bullet. Nothing tuned (w 50, z > 2.0 vs trailing
500, 20-session off rule are the registered values).
  OMP_NUM_THREADS=3 PYTHONPATH=. <venv with ripser+persim>/bin/python research/sim/exp_tda.py
Data: Sharadar SFP (~/data/sharadar/funds.parquet, dividend-adjusted closeadj) for SPY/DIA/MDY/QQQ; book = REGIME-X leg cache
(data/research/regime_x/legs.parquet, 0.5 IBS + 0.5 night, 5bp/side), cash = 3m T-bill (DTB3), as in research/sim/regime_x.py.
Timing: L1/z use closes <= t; a warning at close t sets exposure 0 on book rows t+1..t+20 (regime_x convention: signals as of
d-1, book rows dated by signal day). SPY arm: close(d-1)->close(d) return on the same exposure series.
Point cloud: 4-D (SPY, DIA, MDY, QQQ) once QQQ has a full 50-return window (1999-05), 3-D before; the trailing-500 z mixes the
two until ~2001-05 (stated, not fixed)."""
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "3")
import math
import pathlib
import time
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import scipy.stats as SS
from ripser import ripser

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/regime_x"
OUT = ROOT / "research/sim/exp_tda_out.txt"
CACHE = ROOT / "data/research/exp_tda/l1.parquet"
FUNDS = pathlib.Path.home() / "data/sharadar/funds.parquet"
TICK = ["SPY", "DIA", "MDY", "QQQ"]
W, ZWIN, ZTH, OFF = 50, 500, 2.0, 20
N_TRIALS = 1245
JUDGE = ("2001-01-02", "2015-12-31")
REPORT = ("2016-01-04", "2026-09-18")
NPL = 200
COST = 5e-4
L = []
rng = np.random.default_rng(1245)


def P(s=""):
    print(s, flush=True); L.append(s)


# ---- stats: same formulas as research/sim/regime_x.py (stats / mdd / gate_returns), copied because that module runs on import
def stats(r):
    r = r.fillna(0.0); eq = (1 + r).cumprod(); yrs = len(r) / 252
    cagr = eq.iloc[-1] ** (1 / yrs) - 1; mdd = float((eq / eq.cummax() - 1).min())
    return cagr, mdd, cagr / abs(mdd) if mdd < 0 else np.nan


def dsr(x, n_trials):  # research/sim/exp_rl.py
    x = np.asarray(x, float); T = len(x)
    sr = x.mean() / x.std(ddof=1); sk = SS.skew(x); ku = SS.kurtosis(x, fisher=False); g = 0.5772156649
    sr0 = math.sqrt(1.0 / T) * ((1 - g) * SS.norm.ppf(1 - 1 / n_trials) + g * SS.norm.ppf(1 - 1 / (n_trials * math.e)))
    z = (sr - sr0) * math.sqrt(T - 1) / math.sqrt(max(1e-12, 1 - sk * sr + (ku - 1) / 4 * sr ** 2))
    return float(SS.norm.cdf(z))


# ---- persistence landscape L1 norm (first K landscapes) on a fine grid
def landscape_l1(dgm, k=3, ngrid=4000):
    dgm = dgm[np.isfinite(dgm[:, 1]) & (dgm[:, 1] > dgm[:, 0])] if len(dgm) else dgm
    if len(dgm) == 0:
        return 0.0
    b, d = dgm[:, 0], dgm[:, 1]
    t = np.linspace(b.min(), d.max(), ngrid)
    tent = np.maximum(0.0, np.minimum(t[None, :] - b[:, None], d[:, None] - t[None, :]))
    tent = -np.sort(-tent, axis=0)[:k]
    return float(np.trapezoid(tent, t, axis=1).sum()) if hasattr(np, "trapezoid") else float(np.trapz(tent, t, axis=1).sum())


def landscape_l1_exact_single(b, d):
    return (d - b) ** 2 / 4.0  # one tent: area = half-base x height = (d-b) * (d-b)/2 / 2


def selftest():
    th = rng.uniform(0, 2 * np.pi, 50); X = np.c_[np.cos(th), np.sin(th)] + rng.normal(0, 0.03, (50, 2))
    h1 = ripser(X, maxdim=1)["dgms"][1]; pers = np.sort(h1[:, 1] - h1[:, 0])[::-1]
    one = np.array([[0.2, 1.4]]); err = abs(landscape_l1(one) - landscape_l1_exact_single(0.2, 1.4))
    noise = ripser(rng.normal(size=(50, 2)), maxdim=1)["dgms"][1]
    P(f"selftest: circle H1 bars {len(h1)}, top persistences {pers[:3].round(3).tolist()} (one long bar expected); "
      f"gaussian-blob top {np.sort(noise[:,1]-noise[:,0])[::-1][:2].round(3).tolist()}; single-tent L1 grid err {err:.2e}")


# ---- data
def load_prices():
    t = pq.read_table(FUNDS, columns=["ticker", "date", "closeadj"], filters=[("ticker", "in", TICK)]).to_pandas()
    t["date"] = pd.to_datetime(t["date"])
    C = t.pivot(index="date", columns="ticker", values="closeadj").sort_index()[TICK]
    C = C[C.SPY.notna()]
    return C


def build_l1(C, standardize=True, cache=CACHE):
    if cache.exists():
        s = pd.read_parquet(cache)
        if s.index.max() == C.index.max():
            return s
    R = np.log(C).diff()
    rows = []; t0 = time.time(); Rv = R.to_numpy(); idx = R.index
    for i in range(W, len(R)):
        win = Rv[i - W + 1:i + 1]
        cols = [j for j in range(4) if np.isfinite(win[:, j]).all()]
        if len(cols) < 3 or not all(c in cols for c in (0, 1, 2)):
            continue
        X = win[:, cols]
        if standardize:
            X = (X - X.mean(0)) / X.std(0, ddof=1)
        h1 = ripser(X, maxdim=1)["dgms"][1]
        rows.append((idx[i], landscape_l1(h1), len(cols), len(h1), float((h1[:, 1] - h1[:, 0]).max()) if len(h1) else 0.0))
    s = pd.DataFrame(rows, columns=["date", "l1", "dim", "nbars", "maxpers"]).set_index("date")
    cache.parent.mkdir(parents=True, exist_ok=True); s.to_parquet(cache)
    P(f"[l1] {len(s)} days computed in {time.time()-t0:.0f}s")
    return s


def zscore(x):
    m = x.rolling(ZWIN, min_periods=ZWIN).mean(); sd = x.rolling(ZWIN, min_periods=ZWIN).std()
    return (x - m) / sd


def exposure(warn, index):
    """warn: bool series on signal dates (close t). Exposure 0 on rows t+1..t+OFF, renewed while the warning holds."""
    w = warn.reindex(index, fill_value=False).astype(float)
    off = w.shift(1).fillna(0.0).rolling(OFF, min_periods=1).max()
    return 1.0 - off


def spells(e):
    """Lengths of OFF runs and ON runs of a 0/1 exposure array."""
    v = (np.asarray(e) < 0.5).astype(int); runs = []; cur = v[0]; n = 0
    for x in v:
        if x == cur:
            n += 1
        else:
            runs.append((cur, n)); cur, n = x, 1
    runs.append((cur, n))
    return [n for c, n in runs if c == 1], sum(n for c, n in runs if c == 0)


def random_gate(off_lens, n_total):
    k = len(off_lens); U = n_total - sum(off_lens)
    if k == 0:
        return np.ones(n_total)
    Up = U - (k - 1)  # keep >= 1 ON day between spells
    cuts = np.sort(rng.choice(Up + k, size=k, replace=False)); pos = cuts - np.arange(k)  # uniform composition
    gaps = np.diff(np.r_[0, pos, Up]); gaps[1:k] += 1
    order = rng.permutation(off_lens); e = []
    for j in range(k):
        e += [1.0] * gaps[j] + [0.0] * order[j]
    e += [1.0] * gaps[k]
    return np.array(e[:n_total])


def arm_stats(base, e, rf, lo, hi):
    m = (base.index >= lo) & (base.index <= hi)
    g = e[m] * base[m] + (1 - e[m]) * rf[m]
    return stats(base[m]), stats(g), g


def dd_episodes(px, lo, hi, n=5):
    eq = px / px.cummax(); peak_id = (eq == 1.0).cumsum()
    m = (px.index >= lo) & (px.index <= hi); out = []
    for pid, seg in eq[m].groupby(peak_id[m]):
        if seg.min() >= 1.0:
            continue
        tr = seg.idxmin(); pk = px.index[px.index <= tr][(eq[px.index <= tr] == 1.0).to_numpy()][-1]
        out.append((pk, tr, float(seg.min() - 1)))
    return sorted(out, key=lambda x: x[2])[:n]


def main(standardize=True, cache=CACHE, n_trials=N_TRIALS, out=OUT, tag="N 1245 TDA"):
    selftest()
    C = load_prices()
    P(f"prices: {C.index.min().date()}..{C.index.max().date()} (SFP closeadj; last on-disk bar {C.index.max().date()})")
    s = build_l1(C, standardize, cache)
    s["z"] = zscore(s.l1)
    warn = s.z > ZTH
    head = (f"L1: {len(s)} days, dim3 {int((s.dim==3).sum())} / dim4 {int((s.dim==4).sum())}; H1 bars/day median {s.nbars.median():.0f}; "
            f"z available from {s.z.first_valid_index().date()}; warnings (z>2) {int(warn.sum())} days")
    ok = run_gates(C, s.l1, s.z, warn, head, n_trials)
    P(f"\n{'PASS' if ok[0] else 'KILL'}: {tag} - {ok[1]}")
    out.write_text("\n".join(L) + "\n")


def run_gates(C, score, z, warn, head, n_trials, nm="TDA", slabel="L1"):
    """Five N 1245 gates + reports for a warning series on signal dates. score/z: the raw statistic and its trailing z."""
    legs = pd.read_parquet(D / "legs.parquet"); idx = legs.index
    book = 0.5 * legs.ibs + 0.5 * legs.night
    book2x = 0.5 * (legs.ibs - 2 * COST * (legs.ibs != 0)) + 0.5 * (legs.night - 2 * COST * (legs.night != 0))
    tb = pd.read_csv(D / "DTB3.csv", na_values=".", parse_dates=[0], index_col=0).iloc[:, 0].dropna()
    spy = C.SPY.pct_change()
    full = C.index[C.index >= idx.min()]
    rf_full = (tb.reindex(full, method="ffill") / 100 / 252).fillna(0.0)
    rf = rf_full.reindex(idx).fillna(0.0)
    # vol gate: 20d SPY realized vol, z vs trailing 500, same off rule
    lr = np.log(C.SPY).diff(); rv = lr.rolling(20).std(); vz = (rv - rv.rolling(ZWIN).mean()) / rv.rolling(ZWIN).std()
    vwarn = vz > ZTH
    e_book = exposure(warn, idx); v_book = exposure(vwarn, idx)
    e_spy = exposure(warn, full); v_spy = exposure(vwarn, full)
    spy_f = spy.reindex(full).fillna(0.0)

    P(head)
    cj = pd.concat([score, rv.reindex(score.index)], axis=1).dropna()
    cjj = cj[(cj.index >= JUDGE[0]) & (cj.index <= JUDGE[1])]
    P(f"corr({slabel}, SPY 20d realized vol): full {cj.corr().iloc[0,1]:+.3f} (Spearman {cj.corr('spearman').iloc[0,1]:+.3f}); "
      f"JUDGE {cjj.corr().iloc[0,1]:+.3f} (Spearman {cjj.corr('spearman').iloc[0,1]:+.3f})")
    zz = pd.concat([z, vz.reindex(z.index)], axis=1).dropna()
    P(f"corr({nm} z, vol z) JUDGE {zz[(zz.index>=JUDGE[0])&(zz.index<=JUDGE[1])].corr().iloc[0,1]:+.3f}; "
      f"warning-day overlap {nm}&vol {int((warn & vwarn.reindex(warn.index, fill_value=False)).sum())} of {nm} {int(warn.sum())} / vol {int(vwarn.sum())}")
    P()

    res = {}
    for wn, (lo, hi) in (("JUDGE 2001-15", JUDGE), ("REPORT 2016-26", REPORT)):
        P(f"== {wn}")
        for arm, base, e, v, r_ in (("book", book, e_book, v_book, rf), ("book 2x cost", book2x, e_book, v_book, rf),
                                    ("SPY->cash", spy_f, e_spy, v_spy, rf_full)):
            (bc, bm, bk), (gc, gm, gk), g = arm_stats(base, e, r_, lo, hi)
            (_, _, _), (vc, vm, vk), _ = arm_stats(base, v, r_, lo, hi)
            m = (base.index >= lo) & (base.index <= hi); em = e[m]
            offr = base[m][em < 0.5]; onr = base[m][em >= 0.5]
            P(f"  {arm:13s} ungated CAGR {bc*100:6.2f}% maxDD {bm*100:6.1f}% MAR {bk:5.2f} | {nm} CAGR {gc*100:6.2f}% maxDD {gm*100:6.1f}% "
              f"MAR {gk:5.2f} (x{gk/bk:4.2f}, CAGR loss {(1-gc/bc)*100:+5.1f}%) | vol-gate CAGR {vc*100:6.2f}% maxDD {vm*100:6.1f}% MAR {vk:5.2f} | "
              f"OFF {(em<0.5).mean()*100:4.1f}% of days; base on OFF days {offr.mean()*1e4:+6.2f}bp (n {len(offr)}) vs ON {onr.mean()*1e4:+6.2f}bp")
            res[(wn, arm)] = dict(bc=bc, bm=bm, bk=bk, gc=gc, gm=gm, gk=gk, vk=vk, vc=vc, e=em, base=base[m], rf=r_[m], g=g)
        P()

    # placebo (book, JUDGE)
    r = res[("JUDGE 2001-15", "book")]
    offl, _ = spells(r["e"].to_numpy()); n = len(r["e"]); b = r["base"].to_numpy(); rfj = r["rf"].to_numpy()
    pk = []
    for _ in range(NPL):
        ep = random_gate(offl, n)
        pk.append(stats(pd.Series(ep * b + (1 - ep) * rfj))[2])
    pk = np.array(pk); pct = (pk < r["gk"]).mean()
    P(f"placebo (JUDGE book): {len(offl)} OFF spells, lengths median {np.median(offl) if offl else 0:.0f} max {max(offl) if offl else 0}; "
      f"random-gate MAR p50 {np.median(pk):.2f} p95 {np.percentile(pk,95):.2f}; real {r['gk']:.2f} -> percentile {pct*100:.1f}")
    rs = res[("JUDGE 2001-15", "SPY->cash")]
    offs, _ = spells(rs["e"].to_numpy()); bs = rs["base"].to_numpy(); rfs = rs["rf"].to_numpy(); pks = []
    for _ in range(NPL):
        ep = random_gate(offs, len(bs)); pks.append(stats(pd.Series(ep * bs + (1 - ep) * rfs))[2])
    pcts = (np.array(pks) < rs["gk"]).mean()
    P(f"placebo (JUDGE SPY->cash, report): random MAR p50 {np.median(pks):.2f} p95 {np.percentile(pks,95):.2f}; real {rs['gk']:.2f} -> pct {pcts*100:.1f}")

    # lead time before SPY's 5 largest 2001-15 drawdown troughs
    P("\nSPY 5 largest drawdowns with trough in 2001-15 (closeadj, peak-to-recovery episodes):")
    sidx = C.index; leads_ok = 0
    for pk_, tr, dd in dd_episodes(C.SPY, *JUDGE):
        ip, it = sidx.get_loc(pk_), sidx.get_loc(tr)
        wd = warn.reindex(sidx, fill_value=False).to_numpy()
        fired = [j for j in range(ip, it + 1) if wd[j]]
        first = fired[0] if fired else None; last_pre = max([j for j in fired if j <= it - 5], default=None)
        vd = vwarn.reindex(sidx, fill_value=False).to_numpy(); vf = [j for j in range(ip, it + 1) if vd[j]]
        ok = last_pre is not None; leads_ok += ok
        P(f"  peak {pk_.date()} trough {tr.date()} DD {dd*100:6.1f}% ({it-ip} sessions) | {nm} warnings in peak..trough {len(fired)}, "
          f"first {sidx[first].date() if first is not None else '-'} (lead {it-first if first is not None else '-'} sess) | "
          f">=5 sess before trough: {'yes' if ok else 'no'} | vol-gate first {sidx[vf[0]].date() if vf else '-'} (lead {it-vf[0] if vf else '-'})")
    P(f"  troughs with a {nm} warning >= 5 sessions earlier: {leads_ok} of 5")

    # DSR
    dg = dsr(r["g"].to_numpy() - r["rf"].to_numpy(), n_trials)
    dd_ = r["g"].to_numpy() - (r["base"].to_numpy())
    P(f"\nDSR (N {n_trials}) JUDGE gated book excess-of-cash daily: {dg:.3f}; ungated book: {dsr(b - rfj, n_trials):.3f}; "
      f"gated-minus-ungated: {dsr(dd_, n_trials):.3f}")

    # Oct-Nov 2026
    tail = pd.DataFrame({"sc": score, "z": z})[score.index >= "2026-08-01"]
    P(f"\n2026 tail (last on-disk bar {C.index.max().date()}; no data on disk covers 2026-10-06..2026-11-21):")
    for d_, row in tail.iloc[-10:].iterrows():
        P(f"  {d_.date()} {slabel} {row.sc:.4f} z {row.z:+.2f}{'  WARNING' if warn.get(d_, False) else ''}   vol z {vz.get(d_, np.nan):+.2f}")
    last_w = warn[warn].index.max()
    P(f"  last {nm} warning on disk: {last_w.date() if pd.notna(last_w) else '-'}; 2026 warnings: "
      f"{[x.date().isoformat() for x in warn[warn & (warn.index >= '2026-01-01')].index]}")

    # GATES
    g1 = r["gk"] / r["bk"] >= 1.2; g2 = (1 - r["gc"] / r["bc"]) <= 0.20; g3 = pct >= 0.95; g4 = r["gk"] > r["vk"]; g5 = leads_ok >= 3
    c2 = res[("JUDGE 2001-15", "book 2x cost")]
    P("\nGATES (book arm, JUDGE 2001-15):")
    P(f"  G1 MAR >= 1.2x ungated: {r['gk']:.2f} vs {r['bk']:.2f} = x{r['gk']/r['bk']:.2f} -> {'PASS' if g1 else 'FAIL'}")
    P(f"  G2 CAGR loss <= 20%: {(1-r['gc']/r['bc'])*100:+.1f}% -> {'PASS' if g2 else 'FAIL'}")
    P(f"  G3 random-gate placebo >= 95th pct on MAR: {pct*100:.1f} -> {'PASS' if g3 else 'FAIL'}")
    P(f"  G4 beats vol gate on MAR: {nm} {r['gk']:.2f} vs vol {r['vk']:.2f} -> {'PASS' if g4 else 'FAIL'}")
    P(f"  G5 warning >= 5 sessions before trough in >= 3 of 5: {leads_ok}/5 -> {'PASS' if g5 else 'FAIL'}")
    P(f"  (2x cost shock, reported: MAR x{c2['gk']/c2['bk']:.2f}, CAGR loss {(1-c2['gc']/c2['bc'])*100:+.1f}%, gated CAGR {c2['gc']*100:.2f}%)")
    ok = g1 and g2 and g3 and g4 and g5
    return ok, ('all gates pass' if ok else 'fails ' + ', '.join(n for n, x in zip(['G1','G2','G3','G4','G5'], [g1,g2,g3,g4,g5]) if not x))


if __name__ == "__main__":
    main()
