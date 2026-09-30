"""Study W: leveraged ETFs inside the night leg, risk-adjusted.

    PYTHONPATH=. .venv/bin/python -m research.sim.night_letf

Pre-registration: research/drafts/round1_prose.md, "Round 8" (commit c81bda5). LETF = etf_kind
"lev" + a leverage factor parsed from the name, inside the ticker's last listing segment.
Per-trade test on z = ret / daily vol20 vs same-decile non-LETF picks; W1 drop / W2 2x (0.20
cap for index LETFs) on the book increment, placebo on random same-decile non-LETF picks.
"""
from __future__ import annotations

import pickle
import re
import time

import numpy as np
import pandas as pd

from . import book as B
from . import new_listings as NL
from .night_filings import FULL, PER, ROOT
from .night_short import nw_t

OUT = ROOT / "data/research/program/night_letf_out.txt"
N_PLACEBO = 200
SS_ISSUER = re.compile(r"T-REX|TRADR|GRANITESHARES|DEFIANCE")
SS_LONG = re.compile(r"\bLONG [A-Z]{1,5}\b|\b[A-Z]{1,5} DAILY\b")
INV = re.compile(r"\b(BEAR|SHORT|INVERSE)\b")


def lev_factor(name: str) -> float | None:
    nm = name.upper()
    if re.search(r"OPTION INCOME|YIELDMAX", nm):
        return None
    neg = bool(INV.search(nm))
    m = re.search(r"(-?)(\d(?:\.\d+)?)X\b", nm)
    if m:
        v = float(m.group(2))
        return -v if (m.group(1) or neg) else v
    if "ULTRAPRO SHORT" in nm:
        return -3.0
    if "ULTRASHORT" in nm:
        return -2.0
    if "ULTRAPRO" in nm:
        return 3.0
    if "ULTRA" in nm:
        return 2.0
    if neg:
        return -1.0
    return None


def classify(sym: str, d: pd.Timestamp, meta: dict, seg: dict):
    """-> (is_letf, L, single_stock)."""
    if NL.etf_kind(sym, meta) != "lev":
        return False, None, False
    L = lev_factor(meta[sym]["name"])
    if L is None or not (abs(L) >= 1.5 or L == -1.0):
        return False, None, False
    segs = seg.get(sym)
    if not segs or not (segs[-1][0] <= d <= segs[-1][1]):
        return False, None, False
    nm = meta[sym]["name"].upper()
    return True, L, bool(SS_ISSUER.search(nm) or SS_LONG.search(nm))


def main():
    t0 = time.time()
    fs = open(OUT, "w")

    def log(*a):
        s_ = " ".join(str(x) for x in a)
        print(s_, flush=True)
        fs.write(s_ + "\n")
        fs.flush()

    log("== Study W: leveraged ETFs inside the night leg, started", pd.Timestamp.now(), "\n")
    N = B.night_days(raw_price=True, max_corr=0.7)
    meta = NL.load_meta()
    seg = pickle.load(open(f"{NL.SP}/cache_new_listings_seg.pkl", "rb"))
    rows = []
    for d, nd in N.items():
        d = pd.Timestamp(d)
        if not (pd.Timestamp(FULL[0]) <= d <= pd.Timestamp(FULL[1])):
            continue
        for j, s in enumerate(nd.syms):
            is_l, L, ss = classify(s, d, meta, seg)
            rows.append(dict(d=d, sym=s, ret=nd.ret[j], price=nd.price[j], adv=nd.adv[j],
                             vol=nd.vol20[j], frac=nd.frac, letf=is_l, L=L, ss=ss))
    T = pd.DataFrame(rows)
    T["w"] = np.minimum(T.frac, 0.10)
    vd = T.vol / np.sqrt(252) if T.vol.median() > 0.2 else T.vol      # vol20 is annualised
    T["z"] = T.ret / vd
    T["dec"] = pd.qcut(T.vol, 10, labels=False, duplicates="drop")
    T["half"] = np.where(T.d <= pd.Timestamp(PER[0][2]), 0, 1)
    Lt = T[T.letf]
    log(f"picks {len(T)}; LETF {len(Lt)} ({len(Lt) / len(T):.1%}); single-stock {Lt.ss.sum()}; "
        f"by half {[(Lt.half == h).sum() for h in (0, 1)]}")
    log("  by L: " + ", ".join(f"{k:+.0f}x {v}" for k, v in Lt.L.value_counts().sort_index().items()))
    log("  top names: " + str(Lt.sym.value_counts().head(12).to_dict()))
    log(f"  vol20 median LETF {Lt.vol.median():.2f} vs non-LETF {T[~T.letf].vol.median():.2f}\n")

    # ---- per-trade risk-adjusted test (gross z; costs enter the book below)
    log("## per-trade z = ret / daily vol20, LETF minus same-decile non-LETF (same half)")
    ref = T[~T.letf].groupby(["half", "dec"]).z.mean()
    T["zx"] = T.z - [ref.get((h, dc), np.nan) for h, dc in zip(T.half, T.dec)]
    zt = {}
    for h, (lab, _, _) in enumerate(PER):
        m = T[T.letf & (T.half == h)].dropna(subset=["zx"])
        e = (m.zx - m.zx.mean()).groupby(m.d).sum()
        t = m.zx.mean() / (np.sqrt((e ** 2).sum()) / len(m))
        zt[h] = m.zx.mean()
        log(f"  {lab}: LETF z excess {m.zx.mean():+.3f} sd-units (n {len(m)}, t {t:+.2f}); "
            f"LETF raw z {m.z.mean():+.3f} vs non-LETF {T[~T.letf & (T.half == h)].z.mean():+.3f}")
    m = T[T.letf].dropna(subset=["zx"])
    e = (m.zx - m.zx.mean()).groupby(m.d).sum()
    t_all = m.zx.mean() / (np.sqrt((e ** 2).sum()) / len(m))
    log(f"  2021-26: {m.zx.mean():+.3f} (t {t_all:+.2f})")
    log("  mechanism (report): mean z excess by L(L-1): " + ", ".join(
        f"{k:.0f}: {g.zx.mean():+.3f} (n {len(g)})"
        for k, g in m.assign(k=m.L * (m.L - 1)).groupby("k")))
    log("  index vs single-stock: " + ", ".join(
        f"{'single' if k else 'index'} {g.zx.mean():+.3f} (n {len(g)})" for k, g in m.groupby("ss")))
    log("")

    sess = B.D.returns20().index
    alld = sess[(sess >= FULL[0]) & (sess <= FULL[1])]
    rng = np.random.default_rng(3)
    # placebo pools: non-LETF picks by decile, with their dates
    nonl = T[~T.letf]
    pool = {dc: (g.index.values, g.d.values.astype("datetime64[D]").astype(np.int64))
            for dc, g in nonl.groupby("dec")}
    by_nd = {k: g.index.values for k, g in nonl.groupby(["d", "dec"])}
    letf_ix = T.index[T.letf].values

    def draw_same():
        out = []
        for i in letf_ix:
            d, dc = T.at[i, "d"], T.at[i, "dec"]
            c = by_nd.get((d, dc))
            if c is None or not len(c):
                ids, dd = pool[dc]
                dist = np.abs(dd - np.datetime64(d.date(), "D").astype(np.int64))
                c = ids[dist == dist.min()]
            out.append(rng.choice(c))
        return np.array(out)

    verdict = {}
    for cost in ("tier", "tier_hi"):
        T["net"] = T.ret - 2 * B.cost_bps(cost, T.price.values, T.adv.values) / 1e4

        def inc(w):
            return pd.Series(0.5 * w * T.net.values).groupby(T.d.values).sum().reindex(alld).fillna(0)

        def mdd(x):
            c = x.cumsum()
            return (c - c.cummax()).min() * 100

        base = inc(T.w.values)
        cap = np.where(T.ss, 0.10, 0.20)

        def w_rule(name, ix):
            w = T.w.values.copy()
            if name == "W1":
                w[ix] = 0.0
            else:
                w[ix] = np.minimum(2 * T.frac.values[ix], cap[ix] if ix is letf_ix else 0.20)
            return w

        log(f"## cost {cost}: book increment (0.5 x w x net) vs baseline")
        for name in ("W1", "W2"):
            diff = inc(w_rule(name, letf_ix)) - base
            yr = [diff[a:b].sum() / (len(diff[a:b]) / 252) * 100 for _, a, b in PER]
            t = nw_t(diff.values)
            dd_b, dd_r = mdd(base), mdd(base + diff)
            draws = np.array([(inc(w_rule(name, draw_same())) - base).sum()
                              for _ in range(N_PLACEBO)])
            pct = (draws < diff.sum()).mean() * 100
            sign = -1 if name == "W1" else 1
            ok = (all(np.sign(zt[h]) == sign for h in (0, 1)) and sign * t_all >= 2.0
                  and all(y > 0 for y in yr) and t >= 2.0 and pct >= 95 and dd_r >= dd_b - 2)
            verdict.setdefault(name, []).append(ok)
            log(f"  {name} ({'drop LETF' if name == 'W1' else '2x LETF'}): pp/yr 2021-23 {yr[0]:+.2f} "
                f"2024-26 {yr[1]:+.2f}  NW t {t:+.2f}  placebo pct {pct:.0f}  "
                f"night-leg maxDD {dd_b:.1f} -> {dd_r:.1f}pp  {'PASS' if ok else ''}")
        log("")

    log("## capacity: LETF order as % of 20d ADV (W2 weights), vs all picks at baseline weights")
    w2 = np.minimum(2 * T.frac, np.where(T.ss, 0.10, 0.20))
    for sz in (25_000, 100_000, 500_000):
        a = 0.5 * sz * w2[T.letf] / T.adv[T.letf] * 100
        b = 0.5 * sz * T.w / T.adv * 100
        log(f"  ${sz:>7,}: LETF median {a.median():.3f}% (p95 {a.quantile(.95):.3f}%); "
            f"all picks median {b.median():.3f}% (p95 {b.quantile(.95):.3f}%); "
            f"LETF median ADV ${T.adv[T.letf].median() / 1e6:.0f}M")

    log("\n## verdict (pass at tier AND tier_hi)")
    for k, v in verdict.items():
        log(f"  {k} {'PASS' if all(v) else 'fail'}")
    T.to_pickle(ROOT / "data/research/program/night_letf_table.pkl")
    log(f"\ndone in {time.time() - t0:4.0f} s")


if __name__ == "__main__":
    main()
