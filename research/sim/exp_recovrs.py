"""DEEP round 3b, N 1254 RECOVERY-RS: residual leaders since the trough, after the recovery is confirmed.

Pre-registration: research/drafts/round1_prose.md, "## Amendment - DEEP round 3b" (N 1253 -> 1255). Not tuned.

    PYTHONPATH=. python3 research/sim/exp_recovrs.py        # -> research/sim/exp_recovrs_out.txt

Reuses research/sim/exp_crashrs.py (N 1250): same D state (rolling 252-session max of the SPY TR index; on <= 0.93, off >= 0.97),
same universe (top 1,500 ADV20, $5+, SEP common, delisted kept; NX caches <= 2020, ~/data/sharadar after), same 252-session beta
ending at P_t (>= 200 obs), same sector demeaning, top decile, close t+1 -> close t+6, beta-matched excess vs EW, costs.
Recovery state (reading of the registration where it is silent):
  * At the first D session L = min SPY TR over P_t..t; while D is on, a close below L resets L (a new trough), ends any running
    sequence and re-arms confirmation.
  * Confirmation = first close with TR >= 1.05 x L while D is on. Decisions at confirmation, then every 5 sessions while D is on,
    at most 12 per sequence; if D ends, the next 5-session step is the one extra decision and the sequence ends.
  * One sequence (confirmation -> last decision) = one "episode" for MC, ex-best-episode and episode-clustered stats.
  * Score = r_i(L..t) - beta_i(P_t) r_SPY(L..t), compounded over sessions L+1..t.
  * Placebo: fake L = t - U{20..120} (the N 1250 draw), beta kept at the real P; 100 draws; gross excess compared.
  * Costs as N 1250: 5bp x turnover within a sequence (1.0 at its first decision) + 5bp exit at its last decision.
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "3")

import pathlib  # noqa: E402
import sys  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import rankdata  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.sim.exp_rl import dsr  # noqa: E402
from research.sim.exp_tail import _read, FULL  # noqa: E402
from research.sim.exp_crashrs import (dstate, load_wide, rolling_beta, cumret, top_decile, hold, tstat,  # noqa: E402
                                      COST, COST_X, J0, J1, H1_END, N_PLACEBO)

OUT = ROOT / "research/sim/exp_recovrs_out.txt"
N_TRIALS = 1255
MAXDEC = 12

lines: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    lines.append(s)


def recovery_decisions(tr, D, P):
    """Returns list of (t, L index, sequence id)."""
    out = []; seq = -1
    L = None; Li = None; armed = False; active = False; last = None; cnt = 0
    for t in range(len(tr)):
        if D[t]:
            if L is None:  # D just switched on
                p = int(P[t]); Li = p + int(np.argmin(tr[p:t + 1])); L = tr[Li]; armed = True; active = False
            if tr[t] < L:
                L = tr[t]; Li = t; armed = True; active = False
            if armed and tr[t] >= 1.05 * L:
                seq += 1; out.append((t, Li, seq)); armed = False; active = True; last = t; cnt = 1
            elif active and t - last == 5 and cnt < MAXDEC:
                out.append((t, Li, seq)); last = t; cnt += 1
                if cnt >= MAXDEC:
                    active = False
        else:
            if active and t - last == 5 and cnt < MAXDEC:   # the one decision after D ended
                out.append((t, Li, seq))
            if active and t - last >= 5:
                active = False
            L = None
    return out


def score_l(LR, B, mcum, sec_codes, cols, t, p, li):
    beta = B[p, cols].astype(np.float64)
    ok = np.isfinite(beta); c = cols[ok]; beta = beta[ok]
    sc = cumret(LR, li + 1, t, c) - beta * (mcum[t] / mcum[li] - 1)
    sg = sec_codes[c]; K = sec_codes.max() + 1
    sm = np.bincount(sg, sc, minlength=K) / np.maximum(np.bincount(sg, minlength=K), 1)
    return c, beta, sc - sm[sg]


def main():
    say("RECOVERY-RS (N 1254): N 1250 D state/universe/beta; L = SPY TR trough since P (reset on a new low), confirmation TR >= 1.05 L"
        " while D on; decisions every 5 sessions, <= 12 per sequence, + 1 after D ends; score = r(L..t) - beta_P r_SPY(L..t), sector-demeaned;"
        " long top decile, close t+1 -> t+6, beta-matched excess vs EW; 5bp/side, shock 10bp; DSR N 1255")
    sp = _read(FULL / "funds.parquet", ["SPY"], "1997-12-01", FULL / "actions.parquet")
    sessions = sp["sessions"]; m = np.nan_to_num(sp["ret"].astype(np.float64)); m[0] = 0.0
    mcum = np.cumprod(1 + m); S = len(sessions)
    D, P, _ = dstate(mcum)
    RD = [x for x in recovery_decisions(mcum, D, P) if x[0] + 20 < S]
    dec = np.array([x[0] for x in RD], int)
    dd = pd.DatetimeIndex(sessions)
    say(f"SPY sessions {dd[0].date()}..{dd[-1].date()}; recovery decisions judge {int(((dd[dec] >= J0) & (dd[dec] <= J1)).sum())},"
        f" report {int((dd[dec] > J1).sum())}, sequences {len(set(x[2] for x in RD))}")
    R, elig, nm, sec = load_wide(sessions, dec)
    B = rolling_beta(R, m)
    R = np.cumsum(np.log1p(np.nan_to_num(R)), axis=0, dtype=np.float32)
    sec_codes = pd.factorize(sec)[0]
    rng = np.random.default_rng(0)
    PL = np.full((N_PLACEBO, len(dec)), np.nan)
    offs = rng.integers(20, 121, (N_PLACEBO, len(dec)))
    rows = []; prev_set, prev_seq = None, None
    for j, (t, li, sq) in enumerate(RD):
        cols = elig.get(t)
        if cols is None or len(cols) < 100:
            continue
        p = int(P[t])
        c, beta, sc = score_l(R, B, mcum, sec_codes, cols, t, p, li)
        if len(c) < 100:
            continue
        idx = top_decile(c, beta, sc)
        ex, port, ew, hs = hold(R, m, mcum, c, beta, idx, t)
        r20 = cumret(R, t + 1, t + 20, c); rs20 = mcum[t + 20] / mcum[t] - 1
        rc = np.corrcoef(rankdata(sc), rankdata(r20 - beta * rs20))[0, 1]
        held = set(c[idx].tolist())
        if prev_seq == sq and prev_set is not None:
            w = 1.0 / len(held); wp = 1.0 / len(prev_set)
            turn = sum(abs((w if x in held else 0) - (wp if x in prev_set else 0)) for x in held | prev_set)
        else:
            turn = 1.0
        rows.append(dict(j=j, t=t, date=dd[t], ep=sq, L=dd[li], P=dd[p], Don=bool(D[t]), n=len(c), k=len(idx), ex=ex, port=port, ew=ew,
                         spy=hs, turn=turn, rc=rc, bport=beta[idx].mean(), bew=beta.mean(), lgap=t - li))
        prev_set, prev_seq = held, sq
        for d_ in range(N_PLACEBO):
            lf = t - int(offs[d_, j])
            cf, bf, sf = score_l(R, B, mcum, sec_codes, cols, t, p, lf)
            PL[d_, j] = hold(R, m, mcum, cf, bf, top_decile(cf, bf, sf), t)[0]
    H = pd.DataFrame(rows)
    H["last"] = H.ep != H.ep.shift(-1)
    H["net"] = H.ex - COST * (H.turn + H["last"])
    H["netx"] = H.ex - COST_X * (H.turn + H["last"])
    epi = H.groupby("ep").agg(start=("date", "first"), end=("date", "last"), L=("L", "first"), holds=("ex", "size"),
                              ex=("ex", "mean"), net=("net", "mean"), rc=("rc", "mean"), spy=("spy", "mean"))
    say("\nSequences (confirmation, last decision, trough L, holds, mean gross/net excess per hold, mean MC rank corr, mean SPY/hold):")
    for e, r in epi.iterrows():
        say(f"  seq {e:2d} {r.start.date()}..{r.end.date()} L {r.L.date()} holds {r.holds:2d} gross {r.ex * 1e4:+7.1f}bp net {r.net * 1e4:+7.1f}bp"
            f" rc {r.rc:+.3f} SPY {r.spy * 1e4:+6.1f}bp")
    for tag, mk, judge in (("JUDGE 1999-2015 (halves 1999-2007 / 2008-15)", (H.date >= J0) & (H.date <= J1), True),
                           ("REPORT 2016-2026-10 (never judged)", H.date > J1, False)):
        h = H[mk]
        if len(h) == 0:
            say(f"\n=== {tag}: no decisions"); continue
        e_rc = h.groupby("ep").rc.mean()
        say(f"\n=== {tag}: {len(h)} holds in {h.ep.nunique()} sequences, names/decision {h.n.mean():.0f}, decile {h.k.mean():.0f},"
            f" beta port {h.bport.mean():.2f} vs EW {h.bew.mean():.2f}, turnover {h.turn.mean():.2f}/hold, sessions since L at decision {h.lgap.mean():.0f},"
            f" holds after D ended {int((~h.Don).sum())}")
        mc_t = tstat(e_rc)
        gMC = e_rc.mean() >= 0.05 and mc_t >= 2 and (e_rc > 0).mean() >= 0.60
        say(f"  MC: mean sequence rank corr(score, next-20 residual) {e_rc.mean():+.4f}, t {mc_t:+.2f} over {len(e_rc)} sequences, positive {(e_rc > 0).mean():.0%};"
            f" pooled over decisions {h.rc.mean():+.4f} (t {tstat(h.rc):+.2f}) -> {'PASS' if gMC else 'FAIL'}")
        x = h.net.to_numpy(); srt = np.sort(x)
        h1 = (h.date <= H1_END).to_numpy() if judge else (h.date <= h.date.iloc[len(h) // 2]).to_numpy()
        epsum = h.groupby("ep").net.sum(); best = epsum.idxmax()
        exb = h[h.ep != best].net.mean()
        t_ = tstat(x); t_ep = tstat(epsum / h.groupby("ep").size())
        plm = np.nanmean(PL[:, h.j.to_numpy()], axis=1); real_g = h.ex.mean()
        pct = (plm < real_g).mean() * 100
        ds = dsr(x, N_TRIALS)
        say(f"  net excess {x.mean() * 1e4:+.1f}bp/hold (gross {h.ex.mean() * 1e4:+.1f}, 2x cost {h.netx.mean() * 1e4:+.1f}) t {t_:+.2f}"
            f" | median {np.median(x) * 1e4:+.1f} hit {(x > 0).mean():.2f} | halves {x[h1].mean() * 1e4:+.1f} / {x[~h1].mean() * 1e4:+.1f}"
            f" | ex-top5 {srt[:-5].mean() * 1e4:+.1f} | ex-best sequence (seq {best}) {exb * 1e4:+.1f} | sequence-clustered t {t_ep:+.2f}")
        say(f"  raw legs: decile {h.port.mean() * 1e4:+.1f}bp/hold, EW {h.ew.mean() * 1e4:+.1f}, SPY {h.spy.mean() * 1e4:+.1f}"
            f" | placebo fake-L (100): gross mean {plm.mean() * 1e4:+.1f}bp, 95th {np.percentile(plm, 95) * 1e4:+.1f}; real gross {real_g * 1e4:+.1f} at pct {pct:.0f}"
            f" | DSR (N {N_TRIALS}, per hold) {ds:.3f}")
        yrs = ((h.date.iloc[-1] if judge else dd[-1]) - (pd.Timestamp(J0) if judge else pd.Timestamp("2016-01-01"))).days / 365.25
        say(f"  ceiling: {len(h) / yrs:.1f} holds/yr x {x.mean() * 1e4:+.1f}bp = {len(h) / yrs * x.mean() * 100:+.1f}pp/yr excess (simple sum)")
        if judge:
            g = [("MC", gMC), ("net>=60bp", x.mean() >= 60e-4), ("t>=2.5", t_ >= 2.5), ("halves", x[h1].mean() > 0 and x[~h1].mean() > 0),
                 ("ex-top5", srt[:-5].mean() > 0), ("ex-best-seq", exb > 0), ("2xcost", h.netx.mean() > 0), ("placebo95", pct >= 95)]
            say("  GATES: " + " | ".join(f"{n} {'PASS' if ok else 'FAIL'}" for n, ok in g) + f" -> {'PASS' if all(o for _, o in g) else 'KILL'}")
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
