"""Amendment IND-SWING-PAIRS: every pair of the 40 IND-SWING features, decile-tail intersections, 5 horizons
(pre-reg round1_prose.md, IND-SWING-PAIRS). Run: PYTHONPATH=. .venv/bin/python -m research.sim.ind_pairs

Discovery is scored first on 2004-14 rows only; only discovery passes are judged on 2015-26 (one look).
Null = each date's forward returns shuffled across eligible names (3 replicates), discovery pass count only.
"""
from __future__ import annotations
import itertools, time, pathlib
import multiprocessing as mp
import numpy as np, pandas as pd
from .ind_swing import load, build, pct, DISC, DHALF, JUDG, JHALF, HZ, COST

OUT = pathlib.Path("data/research/program/ind_pairs_out.txt")
DEC = 0.10
G = {}


def score(mask, Rh, U, okU, h, rows):
    """net excess per non-overlapping date over `rows` (indices); returns (dates idx, net)."""
    ok = mask[rows] & okU[rows]
    cnt = ok.sum(1)
    sm = np.where(ok, Rh[rows], 0).sum(1)
    idx = np.where(cnt >= 3)[0][::int(np.ceil(h / 5))]
    return rows[idx], sm[idx] / cnt[idx] - U[rows][idx] - COST


def gate(net, dts, half, t_min):
    n = len(net)
    if n < 30: return None
    mu, sd = net.mean(), net.std(ddof=1)
    t = mu / sd * np.sqrt(n) if sd > 0 else 0
    h1, h2 = net[dts < half].mean(), net[dts >= half].mean()
    ex5 = np.sort(net)[:-5].mean()
    st = dict(n=n, mean=mu * 1e4, t=t, med=np.median(net) * 1e4, h1=h1 * 1e4, h2=h2 * 1e4, ex5=ex5 * 1e4)
    st["pass"] = bool(mu > 0 and t >= t_min and st["med"] > 0 and h1 > 0 and h2 > 0 and (t_min < 3 and ex5 > 0 or t_min >= 3))
    return st


def job(args):
    rep, pairs = args
    T, R, U, okU, drows, sd = G["T"], G["R"][rep], G["U"][rep], G["okU"], G["drows"], G["sd"]
    out = []
    for (a, b) in pairs:
        m = T[a] & T[b]
        for h in HZ:
            ii, net = score(m, R[h], U[h], okU[h], h, drows)
            st = gate(net, sd[ii], pd.Timestamp(DHALF), 3.0)
            if st and st["pass"]:
                out.append((a, b, h, st))
    return rep, out


def main():
    t0 = time.time()
    dates, tick, M = load()
    sd, E, X, Hp, R0 = build(dates, M)
    del M
    FE = list(X)
    T = {}
    for f in FE:
        if f == "pocket":
            T[(f, "flag")] = (np.nan_to_num(X[f]) == 1) & E
        else:
            p = pct(X[f], E); T[(f, "top")] = (p > 1 - DEC) & E; T[(f, "bot")] = (p <= DEC) & E
    del X
    keys = list(T)
    pairs = [(a, b) for a, b in itertools.combinations(keys, 2) if a[0] != b[0]]
    okU = {h: E & np.isfinite(R0[h]) for h in HZ}
    def umean(R):
        return {h: np.where(okU[h], R[h], 0).sum(1) / np.maximum(okU[h].sum(1), 1) for h in HZ}
    Rs, Us = [R0], [umean(R0)]
    rng = np.random.default_rng(20261015)
    for rep in range(3):  # shuffle returns across eligible names within each date
        Rp = {}
        for h in HZ:
            a = np.full_like(R0[h], np.nan)
            for i in range(a.shape[0]):
                c = np.where(okU[h][i])[0]
                if len(c): a[i, c] = R0[h][i, rng.permutation(c)]
            Rp[h] = a
        Rs.append(Rp); Us.append(umean(Rp))
    drows = np.where((sd >= pd.Timestamp(DISC[0])) & (sd <= pd.Timestamp(DISC[1])))[0]
    G.update(T=T, R=Rs, U=Us, okU=okU, drows=drows, sd=sd)
    chunks = [pairs[i::40] for i in range(40)]
    jobs = [(rep, ch) for rep in range(4) for ch in chunks]
    res = {r: [] for r in range(4)}
    print(f"{len(pairs)} pairs x {len(HZ)} horizons; starting {time.time()-t0:.0f}s", flush=True)
    with mp.get_context("fork").Pool(9) as pool:
        for k, (rep, out) in enumerate(pool.imap_unordered(job, jobs)):
            res[rep] += out
            if k % 20 == 0: print("chunk", k, len(jobs), f"{time.time()-t0:.0f}s", flush=True)
    real = len(res[0]); nulls = [len(res[r]) for r in (1, 2, 3)]
    ok = real > max(nulls) and real > 3 * np.mean(nulls)
    L = [f"IND-SWING-PAIRS: {len(pairs)} pairs x {len(HZ)} horizons = {len(pairs)*len(HZ)} cells (decile tails, long-only, net 20bp RT vs EW universe)",
         f"DISCOVERY 2004-14 passes: REAL {real}; NULL (returns shuffled across names) {nulls}; batch {'COUNTS' if ok else 'LUCK'}"]
    jrows = np.where((sd >= pd.Timestamp(JUDG[0])) & (sd <= pd.Timestamp(JUDG[1])))[0]
    J = []
    for a, b, h, st in res[0]:
        m = T[a] & T[b]
        ii, net = score(m, R0[h], Us[0][h], okU[h], h, jrows)
        sj = gate(net, sd[ii], pd.Timestamp(JHALF), 2.0) or dict(n=len(net), mean=np.nan, t=np.nan, med=np.nan, h1=np.nan, h2=np.nan, ex5=np.nan, **{"pass": False})
        cnt = (m[jrows] & okU[h][jrows]).sum(1)
        J.append(dict(pair=f"{a[0]} {a[1]} & {b[0]} {b[1]}", h=h, d_t=st["t"], d_mean=st["mean"], j_n=sj["n"], j_mean=sj["mean"], j_t=sj["t"],
                      j_med=sj["med"], j_ex5=sj["ex5"], j_h1=sj["h1"], j_h2=sj["h2"], j3=(sj["mean"] - 40) if sj["mean"] == sj["mean"] else np.nan,
                      names=cnt[cnt > 0].mean() if (cnt > 0).any() else 0, jpass=sj["pass"]))
    D = pd.DataFrame(J)
    if len(D):
        D.to_parquet("data/research/program/ind_pairs_cells.parquet")
        L.append(f"Judged once on 2015-26: {len(D)} discovery passes; judge passes {int(D.jpass.sum())}; of those > 0 at 3x cost: {int((D.jpass & (D.j3 > 0)).sum())}")
        L.append("All discovery passes, sorted by judge t (bp/trade, net of 20bp RT, excess vs universe):")
        for _, r in D.sort_values("j_t", ascending=False).iterrows():
            L.append(f"  {r.pair:48s} h={r.h:<2} DISC t={r.d_t:5.2f} net={r.d_mean:+6.1f} | JUDGE n={r.j_n:<3} net={r.j_mean:+7.1f} t={r.j_t:+5.2f} "
                     f"med={r.j_med:+6.1f} ex5={r.j_ex5:+6.1f} h1={r.j_h1:+6.1f} h2={r.j_h2:+6.1f} 3x={r.j3:+6.1f} names={r.names:5.1f}{'  JPASS' if r.jpass else ''}")
    L.append(f"runtime {time.time()-t0:.0f}s")
    OUT.write_text("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    main()
