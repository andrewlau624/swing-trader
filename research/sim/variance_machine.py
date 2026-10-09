"""Variance machine: an evolutionary search over night-leg pick filters (unattended, time-boxed). DISCOVERY ONLY.

Every survivor is a candidate to pre-register and judge forward, never a validated rule: this is exactly the multiple-testing
search CLAUDE.md warns about, so the output prints the trial count and the expected-max t under that many trials.

Data: data/research/vm/picks.parquet (19.5k night picks 2016-02..2026-10: exact 15:40 replay; ret = next open / close - 1 in bp,
gross). Filters only use what is known at the 15:40 decision (day_ret, ibs, vol20, adv, category, SPY day, crowd, days since the
symbol's last pick). The next-day gap is the outcome window and is never a filter.
Search folds: 2016-19, 2020-22, 2023-24-09. LOCKED holdout 2024-10..2026-10: never scored during the search, read once at the end
for the final leaderboard. Objective = min over folds of the per-day return (bp/day incl. no-pick days as 0, net 15bp round trip),
so a rule must work in every fold; >= MIN_TRADES per fold.
ES: population POP, top ELITE survive, children = elites mutated with step sigma (the learning rate) that decays each generation
and resets on stagnation; IMMIG random newcomers per generation.
Run: nice -n 19 python research/sim/variance_machine.py [hours] -> runs/vm/leaderboard.txt (rewritten every generation), runs/vm/log.txt
"""
import json, math, os, sys, time
import numpy as np, pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "runs", "vm"); os.makedirs(OUT, exist_ok=True)
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 8.0
EPOCH_MIN = float(os.environ.get("VM_EPOCH_MIN", 3.0)); COST = 15.0; MIN_TRADES = 60; POP = 48; ELITE = 12; IMMIG = 8
rng = np.random.default_rng(int(time.time()))

X = pd.read_parquet(os.path.join(ROOT, "data", "research", "vm", "picks.parquet"))
X = X.sort_values(["date", "day_ret"]).reset_index(drop=True)
CATS = sorted(X.cat.unique())
d = X.date.values
FOLDS = [("16-19", d < np.datetime64("2020-01-01")),
         ("20-22", (d >= np.datetime64("2020-01-01")) & (d < np.datetime64("2023-01-01"))),
         ("23-24", (d >= np.datetime64("2023-01-01")) & (d < np.datetime64("2024-10-01")))]
HOLD = d >= np.datetime64("2024-10-01")
# all trading days per fold (days with no pick count as 0): approximate by the business days in each window
NDAYS = {k: int(np.busday_count(X.date[m].min().date(), X.date[m].max().date()) * 0.97) for k, m in FOLDS}
NDAYS["hold"] = int(np.busday_count(X.date[HOLD].min().date(), X.date[HOLD].max().date()) * 0.97)
day_codes, day_idx = np.unique(d, return_inverse=True)
A = dict(dr=X.day_ret.values, ibs=X.ibs.values, vol=X.vol20.values, ladv=np.log10(X.adv.values.clip(1)),
         spy=X.spy.values, crowd=X.crowd.values, prev=X.prev.fillna(999).values, ret=X.ret.values,
         cat=np.searchsorted(CATS, X.cat.values))

# genome: continuous genes in [0,1] mapped to ranges; category mask; discrete choices
G = {"max_dr": (-0.30, -0.08), "max_ibs": (0.005, 0.10), "min_vol": (0.0, 2.0), "min_ladv": (7.0, 9.0),
     "spy_lo": (-0.06, 0.02), "spy_hi": (-0.02, 0.06), "max_crowd": (1, 120), "min_prev": (0, 20), "top_k": (1, 15)}


def rand_genome():
    g = {k: rng.random() for k in G}
    g["min_vol"] = rng.random() * 0.3; g["spy_lo"] = rng.random() * 0.3; g["spy_hi"] = 0.7 + rng.random() * 0.3
    g["max_crowd"] = 0.6 + rng.random() * 0.4; g["top_k"] = 0.5 + rng.random() * 0.5
    g["cats"] = (rng.random(len(CATS)) < 0.7)          # ~30% of categories off per random rule: explore bans
    g["w"] = int(rng.integers(0, 2))                     # 0 equal weight, 1 weight by |day_ret|
    return g


def mutate(g, sigma):
    c = {k: float(np.clip(v + rng.normal(0, sigma), 0, 1)) for k, v in g.items() if k in G}
    c["cats"] = g["cats"] ^ (rng.random(len(CATS)) < sigma / 3)
    c["w"] = g["w"] if rng.random() > sigma / 2 else 1 - g["w"]
    return c


def val(g, k):
    lo, hi = G[k]; return lo + g[k] * (hi - lo)


def decode(g):
    out = {k: round(val(g, k), 4) for k in G}
    out["cats_off"] = [c for c, on in zip(CATS, g["cats"]) if not on]; out["weight"] = ["equal", "depth"][g["w"]]
    return out


def daily(g, m):
    sel = m & (A["dr"] <= val(g, "max_dr")) & (A["ibs"] <= val(g, "max_ibs")) & (A["ladv"] >= val(g, "min_ladv")) \
        & ((A["vol"] >= val(g, "min_vol")) | np.isnan(A["vol"])) & (A["spy"] >= val(g, "spy_lo")) & (A["spy"] <= val(g, "spy_hi")) \
        & (A["crowd"] <= val(g, "max_crowd")) & (A["prev"] >= val(g, "min_prev")) & g["cats"][A["cat"]]
    i = np.flatnonzero(sel)
    if len(i) == 0:
        return i, np.zeros(0), np.zeros(0)
    di = day_idx[i]
    first = np.r_[0, np.flatnonzero(np.diff(di)) + 1]           # rows are sorted by date then deepest drop first
    rank = np.arange(len(i)) - np.repeat(first, np.diff(np.r_[first, len(i)]))
    keep = rank < int(round(val(g, "top_k")))
    i, di = i[keep], di[keep]
    w = np.abs(A["dr"][i]) if g["w"] else np.ones(len(i))
    r = A["ret"][i] - COST
    sw = np.bincount(di, w, len(day_codes)); sr = np.bincount(di, w * r, len(day_codes))
    act = sw > 0
    return i, sr[act] / sw[act], act


def score(g):
    res = {}
    for k, m in FOLDS:
        i, dr, _ = daily(g, m)
        if len(i) < MIN_TRADES:
            return -1e9, None
        t = dr.mean() / dr.std() * math.sqrt(len(dr)) if len(dr) > 2 and dr.std() > 0 else 0
        res[k] = dict(n=len(i), days=len(dr), bp_day=dr.sum() / NDAYS[k], bp_trade=float(np.mean(A["ret"][i] - COST)), t=t)
    return min(v["bp_day"] for v in res.values()), res


def holdout(g):
    i, dr, _ = daily(g, HOLD)
    if len(i) == 0:
        return dict(n=0)
    t = dr.mean() / dr.std() * math.sqrt(len(dr)) if len(dr) > 2 and dr.std() > 0 else 0
    ex5 = np.sort(dr)[:-5].sum() / NDAYS["hold"] if len(dr) > 5 else None
    return dict(n=len(i), bp_day=dr.sum() / NDAYS["hold"], t=t, med_trade=float(np.median(A["ret"][i] - COST)), ex_top5_bp_day=ex5)


def categories():
    """Category ablation on the live-like rule: ban one category (and the healthcare pair) at a time, budget reallocated
    within the night. Fold bp/day and the LOCKED holdout, so a ban that only helps in-sample shows up as such."""
    base_s, base_r = score(LIVE); base_h = holdout(LIVE)
    rows = [("(none: live-like)", base_s, base_r, base_h)]
    sets = [[c] for c in CATS] + [["Stock_biotech_pharma", "Stock_healthcare_other"]]
    for ban in sets:
        g = dict(LIVE, cats=np.array([c not in ban for c in CATS]))
        s_, r_ = score(g); rows.append(("ban " + "+".join(ban), s_, r_, holdout(g)))
    n = {c: int((X.cat == c).sum()) for c in CATS}
    L = ["CATEGORY ABLATION (live-like rule, one ban at a time; net bp/day of account; holdout 2024-10..2026-10 locked)",
         "picks per category: " + ", ".join(f"{c} {n[c]}" for c in CATS), ""]
    for lab, s_, r_, h in rows:
        f = "  ".join(f"{k} {v['bp_day']:+6.2f} (t {v['t']:.1f})" for k, v in (r_ or {}).items()) if r_ else "too few trades"
        L.append(f"{lab:58s} worst {s_:+7.2f} | {f} | holdout {h.get('bp_day', 0):+6.2f} (t {h.get('t', 0):.1f}, n {h.get('n', 0)})")
    open(os.path.join(OUT, "categories.txt"), "w").write("\n".join(L) + "\n")


LIVE = {"max_dr": 1.0, "max_ibs": 1.0, "min_vol": 0.3, "min_ladv": 0.0, "spy_lo": 0.0, "spy_hi": 1.0, "max_crowd": 1.0,
        "min_prev": 0.0, "top_k": 1.0, "cats": np.ones(len(CATS), bool), "w": 0}


def search(minutes, log):
    """One independent ES run from random starts; returns (best dict, trials)."""
    t0 = time.time(); trials = 0; best = {}; sigma = 0.25; stall = 0; gen = 0; top = -1e18
    pop = [LIVE] + [rand_genome() for _ in range(POP - 1)]
    while time.time() - t0 < minutes * 60:
        gen += 1
        scored = []
        for g in pop:
            s, r = score(g); trials += 1
            scored.append((s, g, r))
            key = json.dumps(decode(g), sort_keys=True)
            if r is not None and (key not in best or best[key][0] < s):
                best[key] = (s, g, r)
        scored.sort(key=lambda z: -z[0])
        if scored[0][0] > top + 1e-6:
            top = scored[0][0]; stall = 0
        else:
            stall += 1
        sigma = max(0.02, sigma * 0.97)
        if stall >= 40:                                   # stagnation: restart around new randoms with a big step
            sigma, stall = 0.3, 0
            pop = [s[1] for s in scored[:2]] + [rand_genome() for _ in range(POP - 2)]
            continue
        el = [s[1] for s in scored[:ELITE]]
        pop = el + [mutate(el[rng.integers(0, len(el))], sigma) for _ in range(POP - ELITE - IMMIG)] + [rand_genome() for _ in range(IMMIG)]
        if len(best) > 20000:                             # keep memory small on the 1 GB server
            best = dict(sorted(best.items(), key=lambda kv: -kv[1][0])[:2000])
    return best, trials


def main():
    """Many independent short searches. Each epoch's champion is scored on the LOCKED holdout and logged, so the run
    measures shrinkage (in-sample worst-fold vs holdout) across hundreds of searches, not one lucky winner."""
    t0 = time.time(); trials = 0; allbest = {}; ep = 0
    base = score(LIVE); hl = holdout(LIVE)
    categories()
    log = open(os.path.join(OUT, "log.txt"), "a")
    log.write(f"\n{time.ctime()} start; {HOURS}h; live-like baseline {base[0]:+.2f} bp/day worst fold; holdout {json.dumps(hl, default=float)}\n"); log.flush()
    ef = open(os.path.join(OUT, "epochs.jsonl"), "a")
    while time.time() - t0 < HOURS * 3600 - EPOCH_MIN * 60:
        ep += 1
        best, n = search(EPOCH_MIN, log); trials += n
        s, g, r = max(best.values(), key=lambda z: z[0])
        h = holdout(g)
        ef.write(json.dumps(dict(epoch=ep, t=time.ctime(), trials=n, insample=s, folds=r, holdout=h, rule=decode(g)), default=float) + "\n"); ef.flush()
        for k, v in best.items():
            if k not in allbest or allbest[k][0] < v[0]:
                allbest[k] = v
        allbest = dict(sorted(allbest.items(), key=lambda kv: -kv[1][0])[:500])
        write(allbest, trials, base, t0, ep, 0.0, final=False)
        log.write(f"{time.ctime()} epoch {ep} trials {trials} champion {s:+.2f} -> holdout {h.get('bp_day', 0):+.2f} bp/day\n"); log.flush()
    write(allbest, trials, base, t0, ep, 0.0, final=True)
    log.write(f"{time.ctime()} done; trials {trials}\n"); log.close(); ef.close()


def write(best, trials, base, t0, gen, sigma, final):
    rows = sorted(best.values(), key=lambda z: -z[0])[:20]
    emax = math.sqrt(2 * math.log(max(trials, 2)))
    L = [f"VARIANCE MACHINE  {'FINAL' if final else 'running'}  {time.ctime()}  elapsed {(time.time()-t0)/3600:.2f}h  gen {gen}  trials {trials}  sigma {sigma:.3f}",
         "DISCOVERY ONLY: candidates to pre-register and shadow forward. Expected max |t| from pure noise at this many trials ~ "
         f"{emax:.1f}; a fold t below that is not evidence.",
         f"objective = worst-fold net bp/day of account (15bp round trip, no-pick days = 0); live-like baseline {base[0]:+.2f}"
         f"  folds {', '.join(f'{k} {v['bp_day']:+.2f} (t {v['t']:.1f})' for k, v in base[1].items())}"]
    if final:
        h = holdout(LIVE); L.append(f"live-like on LOCKED holdout 2024-10..2026-10: {json.dumps(h, default=float)}")
        try:
            E = [json.loads(x) for x in open(os.path.join(OUT, "epochs.jsonl"))]
            ins = np.array([e["insample"] for e in E]); ho = np.array([e["holdout"].get("bp_day", 0) for e in E])
            L.append(f"SHRINKAGE over {len(E)} independent searches: champion in-sample worst-fold mean {ins.mean():+.2f} bp/day -> "
                     f"holdout mean {ho.mean():+.2f} (median {np.median(ho):+.2f}); share of champions beating the live-like rule on "
                     f"holdout {100*np.mean(ho > h.get('bp_day', 0)):.0f}%; corr(in-sample, holdout) {np.corrcoef(ins, ho)[0,1]:+.2f}")
            L.append("CATEGORY BANS among the champions (share that banned it; mean holdout bp/day when banned vs kept):")
            for c in CATS:
                b = np.array([c in e["rule"]["cats_off"] for e in E])
                if b.any() and (~b).any():
                    L.append(f"   {c:26s} banned {100*b.mean():4.0f}%  holdout banned {ho[b].mean():+6.2f} vs kept {ho[~b].mean():+6.2f}")
        except Exception as exc:
            L.append(f"shrinkage summary unavailable ({exc})")
    for j, (s, g, r) in enumerate(rows, 1):
        L.append(f"\n#{j}  worst-fold {s:+.2f} bp/day  " + "  ".join(f"{k}: {v['bp_day']:+.2f}bp/d {v['bp_trade']:+.0f}bp/tr n{v['n']} t{v['t']:.1f}" for k, v in r.items()))
        L.append(f"    rule {json.dumps(decode(g))}")
        if final:
            L.append(f"    LOCKED holdout: {json.dumps(holdout(g), default=float)}")
    open(os.path.join(OUT, "leaderboard.txt"), "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
