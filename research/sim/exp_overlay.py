"""EXP round 5, N 1238 R5-OVERLAY: linear risk overlay with leverage on the whole book (0.5 IBS + 0.5 night).

Pre-registration: research/drafts/round1_prose.md "## Amendment - EXP round 5" (N 1238) on top of "## Amendment - EXP round 3"
(R1's book series, state, FIT/JUDGE/REPORT frame). Frozen before any judge number was printed; one run. Data loading and the R1
state come from research/sim/exp_legalloc.py (imported, not edited).

Rule as implemented
  book    r_d = 0.5 * ibs_d + 0.5 * night_d (exp_legalloc.build(): net of 1bp/side IBS and 5bp RT night), keyed by decision day d.
  state   exp_legalloc.FEATS (R1) + vix (VIXCLS close d) + dvix (log VIX_d / VIX_{d-1}) + dd252 (flat-book drawdown vs its
          252-row high, equity through r_{d-2}: the last book return fully known at d, since IBS r_{d-1} ends at open d+1).
          z-scored on FIT rows, clipped +-5 (exp_legalloc.zstate). VIX/SPY use the d close as the 15:40 value (R1 convention);
          a lag-1 VIX sensitivity is printed and NOT judged.
  model   ridge on the next-day book return r_d, walk-forward exactly as R1 (exp_legalloc.ridge_fit; expanding train rows
          [FIT start, i-2], refit every 21 rows, WARM 252 rows); lambda from exp_legalloc.LAMBDAS by WF MSE on FIT;
          z = centred forecast / sd(fitted) (R1's standardisation).
  scale   s = clip(1 + k z, 0, 1.5). k = the largest k on a 0.01 grid in (0, 5] whose FIT walk-forward net maxDD >= the flat
          book's FIT maxDD (same rows), i.e. the fit maxDD equals the flat book's; empty set -> k = 0 (overlay = flat, fails).
  cost    |s_d - s_{d-1}| * 2.5bp; financing (s_d - 1)+ * (DFF_d + 1%) / 252 per session (FRED DFF; FRED DTB3 local fallback when DFF cannot be fetched; ffill).
  gates   JUDGE 2013-20 vs the flat book: CAGR at matched maxDD (exp_legalloc.vs: overlay scaled to flat judge maxDD) >= +2pp;
          Sharpe gain >= +0.15; both halves (13-16, 17-20) beat flat on Sharpe; placebo: FIT state rows shuffled in 20-row
          blocks, lambda and k re-chosen, judge state real (R1's placebo form), 200 draws, real judge Sharpe >= 95th pct;
          ex-top-5 (drop the 5 days of largest overlay-minus-flat) Sharpe gain > 0. Stress years 2008 (FIT, WF) and 2020.

    PYTHONPATH=. python3 research/sim/exp_overlay.py --prep   # data + FIT-only checks, no judge numbers
    PYTHONPATH=. python3 research/sim/exp_overlay.py          # full run -> research/sim/exp_overlay_out.txt
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_v] = "2"

import hashlib  # noqa: E402
import pathlib  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.sim import exp_legalloc as LA  # noqa: E402
from research.sim.exp_rl import sharpe, maxdd, dsr  # noqa: E402

import torch  # noqa: E402  (exp_rl already requires it; cap threads at 2)
torch.set_num_threads(2)

OUT = ROOT / "research/sim/exp_overlay_out.txt"
VIXF = ROOT / "data/research/oil_shock/VIXCLS.csv"
DFFF = ROOT / "data/research/r5_overlay/DFF.csv"
DTB3F = ROOT / "data/research/regime_x/DTB3.csv"     # fallback when FRED DFF cannot be fetched (FRED timed out 2026-11-21)
N_TRIALS = 1239
S_MAX = 1.5
SCALE_COST = 2.5e-4
FIN_SPREAD = 0.01
KGRID = np.round(np.arange(0.01, 5.0001, 0.01), 2)
N_PLAC = 200
BLOCK = 20
FEATS = LA.FEATS + ["vix", "dvix", "dd252"]

lines: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    lines.append(s)


def fred_csv(path, col):
    d = pd.read_csv(path, na_values=".")
    return pd.Series(pd.to_numeric(d[col], errors="coerce").values, index=pd.to_datetime(d["observation_date"])).dropna()


def build():
    df, chk = LA.build()
    sess = df.index
    vix = fred_csv(VIXF, "VIXCLS")
    v = vix.reindex(sess.union(vix.index)).ffill(limit=3).reindex(sess)
    df["vix"] = v
    df["dvix"] = np.log(v / v.shift(1))
    df["vix_l1"] = v.shift(1)
    df["dvix_l1"] = df["dvix"].shift(1)
    df["flat"] = 0.5 * df["ibs"] + 0.5 * df["night"]
    eq = (1 + df["flat"].shift(2).fillna(0.0)).cumprod()
    df["dd252"] = eq / eq.rolling(252, min_periods=1).max() - 1
    if DFFF.exists() and DFFF.stat().st_size > 0:
        ff, fsrc = fred_csv(DFFF, "DFF"), "FRED DFF"
    else:
        ff, fsrc = fred_csv(DTB3F, "DTB3"), "FRED DTB3 (local; DFF fetch failed) as the fed-funds proxy"
    df["ff"] = ff.reindex(sess.union(ff.index)).ffill().reindex(sess) / 100.0
    return df, chk, dict(vix_first=str(vix.index[0].date()), vix_last=str(vix.index[-1].date()),
                         vix_missing_sessions=int(vix.reindex(sess).isna().sum()), ff_first=str(ff.index[0].date()), ff_src=fsrc)


def wf1(X, y, lam, lo, start, end):
    """R1's walk-forward (exp_legalloc.wf) for one target: refit every REFIT rows on rows [lo, i-2]."""
    Z = np.zeros(end - start); Fm = np.zeros(end - start)
    m = None
    for i in range(start, end):
        if (i - start) % LA.REFIT == 0:
            m = LA.ridge_fit(X[lo:i - 1], y[lo:i - 1], lam)
        xc = X[i] - m["xm"]
        Fm[i - start] = m["ym"] + xc @ m["b"]
        Z[i - start] = (xc @ m["b"]) / m["sdf"] if m["sdf"] > 0 else 0.0
    return Z, Fm


def overlay(Z, k, r, ff):
    s = np.clip(1.0 + k * Z, 0.0, S_MAX)
    ds = np.abs(np.diff(np.concatenate([[1.0], s])))
    net = s * r - ds * SCALE_COST - np.maximum(s - 1.0, 0.0) * (ff + FIN_SPREAD) / 252
    return net, s


def pipeline(X, y, ff, ix):
    f0, f1, end = ix["f0"], ix["f1"], ix["end"]
    ws = f0 + LA.WARM
    mse = {}
    for L in LA.LAMBDAS:
        _, Fm = wf1(X, y, L, f0, ws, f1)
        mse[L] = float(((y[ws:f1] - Fm) ** 2).mean())
    lam = min(LA.LAMBDAS, key=lambda L: (round(mse[L], 15), L))
    Zf, _ = wf1(X, y, lam, f0, ws, f1)
    dd_flat = maxdd(y[ws:f1])
    ok = [k for k in KGRID if maxdd(overlay(Zf, k, y[ws:f1], ff[ws:f1])[0]) >= dd_flat]
    k = float(max(ok)) if ok else 0.0
    Zj, _ = wf1(X, y, lam, f0, f1, end)
    rf, sf = overlay(Zf, k, y[ws:f1], ff[ws:f1])
    rj, sj = overlay(Zj, k, y[f1:end], ff[f1:end])
    return dict(lam=lam, mse=mse, k=k, Zf=Zf, rf=rf, sf=sf, rj=rj, sj=sj, dd_flat=dd_flat, ws=ws, nok=len(ok))


def block_perm(n, rng):
    blocks = [np.arange(a, min(a + BLOCK, n)) for a in range(0, n, BLOCK)]
    return np.concatenate([blocks[i] for i in rng.permutation(len(blocks))])


def line(tag, e):
    return (f"{tag:<26} Sh {e['sh']:5.2f} CAGR {e['cagr']*100:6.2f}% maxDD {e['mdd']*100:6.1f}% | 13-16 Sh {e['sh1']:5.2f} "
            f"17-20 Sh {e['sh2']:5.2f} | mean {e['mean']*1e4:+6.2f}bp med {e['med']*1e4:+5.2f} hit {e['hit']*100:3.0f}%")


def yr(tag, d, r_o, r_f, s=None):
    st = f"  {tag}: overlay CAGR {LA.cagr(r_o)*100:+6.1f}% maxDD {maxdd(r_o)*100:6.1f}% | flat CAGR {LA.cagr(r_f)*100:+6.1f}% " \
         f"maxDD {maxdd(r_f)*100:6.1f}% | days {len(r_o)}"
    if s is not None:
        st += f" | mean s {s.mean():.2f}, s=0 {np.mean(s == 0)*100:.0f}%, s=1.5 {np.mean(s == S_MAX)*100:.0f}%"
    return st


def main():
    prep = "--prep" in sys.argv
    t0 = time.time()
    sha = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]
    df, chk, vchk = build()
    say("EXP round 5 R5-OVERLAY (N 1238): ridge risk overlay s = clip(1 + k z, 0, 1.5) on the flat book 0.5 IBS + 0.5 night.")
    say(f"Pre-reg round1_prose.md 'Amendment - EXP round 5' + 'EXP round 3'. Code sha256[:16] {sha} (frozen before judge).")
    say(f"FIT {LA.FIT[0]}..{LA.FIT[1]}  JUDGE {LA.JUDGE[0]}..{LA.JUDGE[1]}  REPORT {LA.REPORT[0]}..{df.index[-1].date()}")
    say(f"VIX: FRED VIXCLS local copy {VIXF.relative_to(ROOT)} ({vchk['vix_first']}..{vchk['vix_last']}), sessions w/o a print "
        f"{vchk['vix_missing_sessions']} (ffill <= 3); financing rate: {vchk['ff_src']} from {vchk['ff_first']}")
    say(f"IBS cross-check (exp_legalloc): {chk['ibs']}")
    fm = np.asarray((df.index >= LA.FIT[0]) & (df.index <= LA.FIT[1]))
    jm = np.asarray((df.index >= LA.JUDGE[0]) & (df.index <= LA.JUDGE[1]))
    rm = np.asarray(df.index >= LA.REPORT[0])
    use = fm | jm | rm
    assert df.loc[use, FEATS + ["ff", "vix_l1", "dvix_l1"]].notna().all().all(), df.loc[use, FEATS].isna().sum()
    df = df.loc[df.index >= LA.FIT[0]]
    fm = np.asarray((df.index >= LA.FIT[0]) & (df.index <= LA.FIT[1]))
    jm = np.asarray((df.index >= LA.JUDGE[0]) & (df.index <= LA.JUDGE[1]))
    rm = np.asarray(df.index >= LA.REPORT[0])
    mu, sd = df.loc[fm, FEATS].mean(), df.loc[fm, FEATS].std(ddof=0)
    X = np.clip(((df[FEATS] - mu) / sd).to_numpy(float), -LA.ZCLIP, LA.ZCLIP)
    y = df["flat"].to_numpy(float)
    ff = df["ff"].to_numpy(float)
    f0, f1, j1, end = 0, int(np.argmax(jm)), int(np.argmax(rm)), len(df)
    ix = dict(f0=f0, f1=f1, end=end)
    nj = int(jm.sum())
    dates = df.index
    say(f"rows: fit {fm.sum()} (WF from row {LA.WARM}) judge {nj} report {rm.sum()}; fit flat mean {y[fm].mean()*1e4:+.2f}bp/d")

    real = pipeline(X, y, ff, ix)
    say(f"\nFIT choices: lambda {real['lam']:g} (WF MSE " + " ".join(f"{L:g}:{v*1e8:.4f}" for L, v in real["mse"].items())
        + "  x1e-8)")
    say(f"  k {real['k']:.2f} ({real['nok']} grid k in (0,5] keep fit maxDD >= flat {real['dd_flat']*100:.1f}%); fit WF overlay "
        f"maxDD {maxdd(real['rf'])*100:.1f}% Sh {sharpe(real['rf']):.2f} vs flat Sh {sharpe(y[real['ws']:f1]):.2f}; "
        f"mean s {real['sf'].mean():.2f}")
    m = LA.ridge_fit(X[:f1 - 1], y[:f1 - 1], real["lam"])
    say("  ridge b (fit 2003-12, z units, bp): " + " ".join(f"{n} {b*1e4:+.2f}" for n, b in zip(FEATS, m["b"])))
    fdates = dates[real["ws"]:f1]
    m08 = np.asarray(fdates.year == 2008)
    say(yr("stress 2008 (FIT, walk-forward)", None, real["rf"][m08], y[real["ws"]:f1][m08], real["sf"][m08]))
    if prep:
        say("prep only: no judge numbers printed")
        return

    # ---------------- judge
    dj = dates[jm]
    rj, sj = real["rj"][:nj], real["sj"][:nj]
    fj = y[f1:f1 + nj]
    ef, eo = LA.stats(fj, dj), LA.stats(rj, dj)
    say("\nJUDGE 2013-20 (net)")
    say(line("flat 0.5/0.5", ef))
    say(line("R5-OVERLAY", eo) + f" | mean s {sj.mean():.2f}+-{sj.std():.2f}, s=0 {np.mean(sj == 0)*100:.0f}%, "
        f"s=1.5 {np.mean(sj == S_MAX)*100:.0f}%")
    v = LA.vs(eo, rj, fj, ef, dj)
    say(f"  dSh {v['dsh']:+.3f} | CAGR@flat maxDD {ef['mdd']*100:.1f}% = {v['cagr_m']*100:.2f}% (x{v['scale']:.2f}) vs "
        f"{ef['cagr']*100:.2f}% (d {v['dcagr_m']*100:+.2f}pp) | halves beat {v['halves']} | ex-top-5 dSh {v['gx5']:+.3f}")
    cost = np.abs(np.diff(np.concatenate([[1.0], sj]))) * SCALE_COST
    fin = np.maximum(sj - 1, 0) * (ff[f1:f1 + nj] + FIN_SPREAD) / 252
    say(f"  cost drag {cost.mean()*252*100:.2f}%/yr scale changes + {fin.mean()*252*100:.2f}%/yr financing; "
        f"corr(s, vix) {np.corrcoef(sj, df['vix'].to_numpy()[jm])[0,1]:+.2f} corr(s, dd252) "
        f"{np.corrcoef(sj, df['dd252'].to_numpy()[jm])[0,1]:+.2f} corr(s, same-day flat r) {np.corrcoef(sj, fj)[0,1]:+.3f}")

    rng = np.random.default_rng(1238)
    plac = []
    t1 = time.time()
    for p in range(N_PLAC):
        Xp = X.copy()
        Xp[f0:f1] = X[f0:f1][block_perm(f1 - f0, rng)]
        pr = pipeline(Xp, y, ff, ix)
        plac.append(sharpe(pr["rj"][:nj]))
    plac = np.array(plac)
    p95 = float(np.percentile(plac, 95))
    say(f"  placebo ({N_PLAC}, FIT state in 20-row blocks, lambda/k re-chosen; {(time.time()-t1)/60:.1f} min): judge Sh median "
        f"{np.median(plac):.2f} 95th {p95:.2f} max {plac.max():.2f}; real {eo['sh']:.2f} at pct "
        f"{(plac < eo['sh']).mean()*100:.0f}")
    say(f"  DSR (N {N_TRIALS}): {dsr(rj, N_TRIALS):.3f} (flat {dsr(fj, N_TRIALS):.3f})")
    g = dict(cagr=v["dcagr_m"] >= 0.02, sh=v["dsh"] >= 0.15, halves=v["halves"], plac=eo["sh"] >= p95, x5=v["gx5"] > 0)
    labs = [("cagr", "CAGR@DD>=+2pp"), ("sh", "dSh>=+0.15"), ("halves", "both halves"), ("plac", "placebo>=95th"),
            ("x5", "ex-top-5 gain>0")]
    say("  GATES: " + " | ".join(f"{lab}: {'PASS' if g[k] else 'FAIL'}" for k, lab in labs))
    verdict = "PASS" if all(g.values()) else "KILL"
    m20 = np.asarray(dj.year == 2020)
    say(yr("stress 2020 (JUDGE)", None, rj[m20], fj[m20], sj[m20]))
    for y0, y1 in [("2013", "2016"), ("2017", "2020")]:
        mm = np.asarray((dj.year >= int(y0)) & (dj.year <= int(y1)))
        say(yr(f"{y0}-{y1}", None, rj[mm], fj[mm], sj[mm]))

    # ---------------- report 2021-26 (not judged)
    dr = dates[rm]
    rr, sr = real["rj"][nj:], real["sj"][nj:]
    fr = y[j1:end]
    say("\nREPORT 2021-26 (not judged; IBS leg on Alpaca etf_daily)")
    say(line("flat 0.5/0.5", LA.stats(fr, dr)) + "  [halves cols n/a]")
    say(line("R5-OVERLAY", LA.stats(rr, dr)) + f" | mean s {sr.mean():.2f}")

    # ---------------- descriptive (not judged): fixed k from R1's grid, since the registered k can be 0 (overlay = flat)
    Zfix = np.concatenate([real["Zf"], wf1(X, y, real["lam"], f0, f1, end)[0]])
    yy, fx, dd_ = y[real["ws"]:end], ff[real["ws"]:end], dates[real["ws"]:end]
    say("\nDESCRIPTIVE (not judged): same forecasts, fixed k in R1's grid {0.25, 0.5, 1}")
    for kk in LA.KS:
        ro, so = overlay(Zfix, kk, yy, fx)
        mj = np.asarray((dd_ >= LA.JUDGE[0]) & (dd_ <= LA.JUDGE[1]))
        ek = LA.stats(ro[mj], dj)
        vk = LA.vs(ek, ro[mj], fj, ef, dj)
        say(f"  k {kk}: " + line("judge", ek) + f" | dSh {vk['dsh']:+.3f} CAGR@DD d {vk['dcagr_m']*100:+.2f}pp | mean s {so[mj].mean():.2f}")
        for Y in (2008, 2020):
            my = np.asarray(dd_.year == Y)
            say("  " + yr(f"k {kk} {Y}", None, ro[my], yy[my], so[my]))

    # ---------------- sensitivity (not judged): VIX lagged one session
    Fl = [f if f not in ("vix", "dvix") else f + "_l1" for f in FEATS]
    mu2, sd2 = df.loc[fm, Fl].mean(), df.loc[fm, Fl].std(ddof=0)
    X2 = np.clip(((df[Fl] - mu2) / sd2).to_numpy(float), -LA.ZCLIP, LA.ZCLIP)
    s2 = pipeline(X2, y, ff, ix)
    e2 = LA.stats(s2["rj"][:nj], dj)
    say(f"\nSENSITIVITY (not judged) VIX/dVIX at d-1 close: lambda {s2['lam']:g} k {s2['k']:.2f} | "
        + line("judge", e2) + f" | dSh vs flat {e2['sh']-ef['sh']:+.3f}")

    say(f"\nVERDICT R5-OVERLAY (N 1238): {verdict}")
    say(f"[{(time.time()-t0)/60:.1f} min]")
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
