"""Reddit round R11: drop night picks with a recent reverse split (90 / 365 days).

    PYTHONPATH=. .venv/bin/python -m research.sim.reddit_rs

Pre-registration: research/drafts/study_reddit_round.md, section R11 (commit 8742c9c, before any outcome).
Same picks, costs and pass bar as R1 (reddit_8k.py / Study T); every pick is eligible (no EDGAR map needed).
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

from . import book as B
from .night_filings import PER, FULL, N_PERM, clustered_t
from .reddit_8k import OUT as R1_OUT

OUT = R1_OUT.parent / "reddit_rs_out.txt"
RS = R1_OUT.parents[1] / "events/alpaca_reverse_splits.parquet"
WIN = {"R11a": 90, "R11b": 365}


def main():
    t0 = time.time()
    fs = open(OUT, "w")

    def log(*a):
        s_ = " ".join(str(x) for x in a)
        print(s_, flush=True)
        fs.write(s_ + "\n")

    log("== Reddit R11: recent reverse split on the night picks, started", pd.Timestamp.now(), "\n")
    rs = pd.read_parquet(RS)
    rs["ex"] = pd.to_datetime(rs.ex)
    rs = rs[(rs.old / rs.new) >= 1.5]
    exs = {s: np.sort(g.ex.values) for s, g in rs.groupby("symbol")}
    log(f"reverse splits (ratio >= 1.5): {len(rs)}, {rs.ex.min().date()}..{rs.ex.max().date()}")

    N = B.night_days(raw_price=True, max_corr=0.7)
    rows = []
    for d, nd in N.items():
        d = pd.Timestamp(d)
        for j, sym in enumerate(nd.syms):
            r = dict(d=d, sym=sym, ret=nd.ret[j], price=nd.price[j], adv=nd.adv[j], frac=nd.frac)
            e = exs.get(sym)
            for k, w in WIN.items():
                r[k] = bool(e is not None and ((e > (d - pd.Timedelta(days=w)).to_datetime64())
                                               & (e <= d.to_datetime64())).any())
            rows.append(r)
    T = pd.DataFrame(rows)
    log(f"picks {len(T)}")
    for e in WIN:
        log(f"  {e}: {T[e].sum()} tagged ({T[e].mean():.1%}); by half "
            + ", ".join(f"{lab} {T[(T.d >= a) & (T.d <= b)][e].sum()}" for lab, a, b in PER))
    log("")

    sess = B.D.returns20().index
    alld = sess[(sess >= FULL[0]) & (sess <= FULL[1])]
    rng = np.random.default_rng(7)
    verdict = {}
    for cost in ("tier", "tier_hi"):
        T["net"] = T.ret - 2 * B.cost_bps(cost, T.price.values, T.adv.values) / 1e4
        g = T.groupby("d").net
        n_ = g.transform("size")
        T["exc"] = np.where(n_ >= 2, (T.net - (g.transform("sum") - T.net) / (n_ - 1).clip(1)), np.nan)
        M = T[T.d >= FULL[0]].copy()
        log(f"## cost {cost}")
        for e in WIN:
            m = M[M[e] & M.exc.notna()]
            hv = []
            for lab, a, b in PER:
                h = m[(m.d >= a) & (m.d <= b)]
                hv.append((h.exc.mean() * 1e4, len(h), h.net.mean() * 1e4))
            t = clustered_t(m.exc.values, m.d.values)
            Mx = M[M.exc.notna()].reset_index(drop=True)
            lab_ = Mx[e].values
            grp = Mx.groupby("d").indices
            real = Mx.exc[lab_].mean()
            draws = np.empty(N_PERM)
            for k in range(N_PERM):
                perm = lab_.copy()
                for ix in grp.values():
                    if len(ix) > 1:
                        perm[ix] = perm[rng.permutation(ix)]
                draws[k] = Mx.exc[perm].mean() if perm.any() else np.nan
            pct = (draws < real).mean() * 100

            def book(wfun):
                w = wfun(np.minimum(T.frac.values, 0.10))
                inc = pd.Series(0.5 * w * T.net.values).groupby(T.d.values).sum()
                return inc.reindex(alld).fillna(0)
            isev = T[e].values
            diff = book(lambda w: np.where(isev, 0.0, w)) - book(lambda w: w)
            yr = [diff[a:b].sum() / (len(diff[a:b]) / 252) * 100 for _, a, b in PER]
            ok = (int(M[e].sum()) >= 100 and all(h[0] < 0 for h in hv) and t <= -2.0 and pct <= 2.5
                  and all(y > 0 for y in yr))
            verdict.setdefault(e, []).append(ok)
            log(f"  {e}: excess bp 2021-23 {hv[0][0]:+7.1f} (n {hv[0][1]:4d}, raw {hv[0][2]:+6.1f})"
                f"  2024-26 {hv[1][0]:+7.1f} (n {hv[1][1]:4d}, raw {hv[1][2]:+6.1f})  t {t:+5.2f}"
                f"  perm pct {pct:4.1f}  DROP pp/yr {yr[0]:+.3f} / {yr[1]:+.3f}  {'PASS' if ok else ''}")
        log("")
    log("## verdict (pass at tier AND tier_hi)")
    for k, v in verdict.items():
        log(f"  {k}: {'PASS' if all(v) else 'fail'}")
    T.to_pickle(OUT.parent / "reddit_rs_table.pkl")
    log(f"\ndone in {time.time() - t0:4.0f} s")


if __name__ == "__main__":
    main()
