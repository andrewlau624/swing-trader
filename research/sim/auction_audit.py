"""Round 19: Study AW (night-leg returns on the official auction prints, report) and the
adversarial checks on Study AU's survivor AU3 (tug-of-war tilt).

    PYTHONPATH=. .venv/bin/python -m research.sim.auction_fetch      # data first
    PYTHONPATH=. .venv/bin/python -m research.sim.auction_audit

AW is pre-registered (round1_prose.md Round 19). The AU3 checks below are POST-HOC verification of
a variant that passed (no new variant, no N): (1) by year; (2) what TOW correlates with; (3) a
second, independent implementation (fractional per-pick contributions, no Sim); (4) AU3 re-judged
with every night return taken from the auction prints, because TOW is built from vendor opens and
a name-level first-print bias would make it predict the vendor-open return mechanically; (5) DSR.
"""
from __future__ import annotations

import dataclasses
import json
import pathlib
import time

import numpy as np
import pandas as pd
import scipy.stats as SS

from swingtrader.daily import signals as sg

from . import book as B
from . import data as D
from . import max_edge as M
from .validate import load_sim

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/auction_audit_out.txt"
AUC = ROOT / "data/research/night/auctions"


def big(lst):
    return max(lst, key=lambda x: x.get("s", 0))["p"] if lst else np.nan


def auction_rets(N):
    cal = list(D.etf()["close"].index)
    nxt = {a: b for a, b in zip(cal[:-1], cal[1:])}
    rows = []
    for d, nd in N.items():
        f = AUC / f"{d.date()}.json"
        js = json.load(open(f)) if f.exists() else {}
        e = nxt.get(d)
        for j, sym in enumerate(nd.syms):
            v = {x["d"]: x for x in js.get(str(sym), [])}
            c = big(v.get(str(d.date()), {}).get("c", []))
            o = big(v.get(str(e.date()), {}).get("o", [])) if e is not None else np.nan
            rows.append(dict(d=d, sym=str(sym), j=j, paid=float(nd.close[j]), price=float(nd.price[j]),
                             adv=float(nd.adv[j]), ret=float(nd.ret[j]), c_auc=c, o_auc=o))
    T = pd.DataFrame(rows)
    T["ret_auc"] = T.o_auc / T.c_auc - 1
    T["ok"] = np.isfinite(T.ret_auc) & ((T.ret_auc - T.ret).abs() <= 0.2)
    return T


def with_rets(N, T, col):
    out = {}
    for d, g in T.groupby("d"):
        nd = N[d]
        r = nd.ret.copy()
        gg = g[g.ok]
        r[gg.j.values] = gg[col].values
        out[d] = dataclasses.replace(nd, ret=r)
    return out


def main():
    t0 = time.time()
    f = open(OUT, "w")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); f.write(x + "\n"); f.flush()

    log("== Round 19: Study AW (auction-print audit) + AU3 checks; started", pd.Timestamp.now(), "==")
    s = load_sim(raw_price=True)
    N0 = B.night_days(raw_price=True, max_corr=0.7)
    s.N = N0; s.I = B.ibs_days()
    T = auction_rets(N0)

    # ======================= AW
    log("\n######## Study AW — night returns: vendor daily bars vs official crosses")
    has_c, has_o = np.isfinite(T.c_auc), np.isfinite(T.o_auc)
    log(f"picks {len(T)}; close cross {has_c.mean():.1%}, open cross {has_o.mean():.1%}, both {(has_c & has_o).mean():.1%}; "
        f"corporate-action / bad (|diff|>20%) {(np.isfinite(T.ret_auc) & ~T.ok).sum()}")
    ok = T[T.ok].copy()
    ok["dret"] = (ok.ret_auc - ok.ret) * 1e4
    ok["dpaid"] = (ok.c_auc / ok.paid - 1) * 1e4
    ok["tier"] = np.where(ok.price < 10, "<$10", np.where(ok.price < 20, "$10-20", ">$20"))
    for lab, a, z in (("2021-23", "2021-01-01", "2023-12-31"), ("2024-26", "2024-01-01", "2026-12-31"), ("all", "2000", "2100")):
        x = ok[(ok.d >= a) & (ok.d <= z)]
        log(f"  {lab}: n {len(x)}  ret vendor {x.ret.mean()*1e4:+6.1f}bp  auction {x.ret_auc.mean()*1e4:+6.1f}bp  "
            f"diff mean {x.dret.mean():+5.1f} median {x.dret.median():+5.1f} (t {x.dret.mean()/x.dret.std()*np.sqrt(len(x)):+.1f})  "
            f"|close cross vs paid| median {x.dpaid.abs().median():.1f}bp")
    for tr, x in ok.groupby("tier"):
        log(f"   tier {tr:7s} n {len(x):5d}  diff mean {x.dret.mean():+6.1f}bp  median {x.dret.median():+5.1f}  "
            f"share |diff|>10bp {(x.dret.abs() > 10).mean():.0%}")
    Na = with_rets(N0, T, "ret_auc")
    for c in M.COSTS:
        for bk, bp in M.BOOKS.items():
            p = B.Params(**{**bp, "night_cost": c})
            line = []
            for E in M.SIZES:
                s.N = N0; a = B.stats(M.replay(s, E, p))
                s.N = Na; b = B.stats(M.replay(s, E, p))
                line.append(f"${E/1e3:.1f}k {a[0]*100:5.1f} -> {b[0]*100:5.1f}%/yr ({(b[0]-a[0])*E:+,.0f} $/yr)")
            log(f"  [{bk}, night {c}/side] vendor -> auction: " + " | ".join(line))
    s.N = N0

    # ======================= AU3 checks
    log("\n######## AU3 (tug-of-war tilt) — post-hoc verification")
    F = M.au_features(N0)
    A = np.array([v for (d, _), v in F.items() if d <= pd.Timestamp("2023-12-31")], float)
    mu, sd = np.nanmean(A, axis=0), np.nanstd(A, axis=0)
    p0 = B.Params(**{**M.BOOKS["V7"], "night_cost": 2.5})
    base = M.replay(s, 10000.0, p0)
    r3 = M.replay(s, 10000.0, dataclasses.replace(p0, tilt=M.make_tilt(N0, F, "AU3", mu, sd)))
    inc = r3 - base
    log("  (1) V7 $10k 2.5bp increment by year (pp): " +
        "  ".join(f"{y}: {g.mean()*25200:+.2f}" for y, g in inc.groupby(inc.index.year)))
    from .program_books import dsr
    for lab, x in (("increment", inc), ("book", r3)):
        q = dsr(x, n_trials=M.N_TRIALS)
        log(f"  (5) DSR at N {M.N_TRIALS} ({lab}): SR {q['sr_ann']:.2f} vs SR0 {q['sr0_ann']:.2f} -> DSR {q['dsr']:.3f}")

    # (2) correlations, per pick
    P = D.panel(); C = P["close"]
    prev = C / C.shift(1) - 1
    rows = []
    for d, nd in N0.items():
        i = C.index.get_loc(d)
        for j, sym in enumerate(nd.syms):
            sym = str(sym)
            pv = prev[sym].iloc[i - 1] if sym in prev.columns else np.nan
            rows.append(dict(tow=F[(d, sym)][1], on20=F[(d, sym)][0], vol20=nd.vol20[j], day=nd.day_ret[j],
                             prev=pv, lprice=np.log(nd.price[j]), ladv=np.log(nd.adv[j]), ret=nd.ret[j]))
    X = pd.DataFrame(rows)
    cs = X.corr(method="spearman")["tow"].drop(["tow"])
    log("  (2) Spearman corr of TOW with: " + "  ".join(f"{k} {v:+.2f}" for k, v in cs.items()))
    # TOW's tercile spread inside price buckets and vol buckets (is it a price/vol proxy?)
    q = X.tow.quantile([1 / 3, 2 / 3]).values
    X["tb"] = np.digitize(X.tow, q)
    for col in ("lprice", "vol20"):
        X["b"] = pd.qcut(X[col], 3, labels=False)
        line = []
        for b, g in X.groupby("b"):
            line.append(f"{col} T{b+1}: " + "/".join(f"{g.ret[g.tb == k].mean()*1e4:+.0f}" for k in range(3)))
        log(f"      TOW tercile net-ret (bp, low/mid/high TOW) within {col} terciles: " + " | ".join(line))

    # (3) independent implementation: fractional per-pick contributions, no Sim
    def contrib(Nx, wfun, c=2.5e-4):
        out = {}
        for d, nd in Nx.items():
            w = wfun(d, nd)
            out[d] = 0.5 * float((np.minimum(nd.frac * w, 0.10) * (nd.ret - 2 * c)).sum())
        return pd.Series(out)

    def live(d, nd):
        return sg.night_tilt(nd.vol20, nd.day_ret, 0.25)

    def au3(d, nd):
        lv = live(d, nd)
        z = np.array([F[(d, str(x))][1] for x in nd.syms], float)
        z = np.where(np.isfinite(z), (z - mu[1]) / sd[1], 0.0)
        w = lv * np.clip(1 + 0.25 * z, 0.25, 2.0)
        return w * lv.mean() / w.mean()

    for lab, Nx in (("vendor rets", N0), ("AUCTION rets", Na)):
        di = (contrib(Nx, au3) - contrib(Nx, live)).reindex(s.days).fillna(0)
        h = [di[(di.index >= a) & (di.index <= z)].mean() * 25200 for _, a, z in M.HALVES]
        log(f"  (3) independent impl, {lab}: inc {h[0]:+.2f} / {h[1]:+.2f} pp/yr, NW t {M.nw_t(di.values):+.2f}")

    # (4) the registered judge, every cell, on auction returns
    log("  (4) AU3 re-judged on AUCTION returns (pre-registered bar, 2.5bp/side judged, tier_hi reported)")
    s.N = Na
    allok = []
    for c in M.COSTS:
        for bk, bp in M.BOOKS.items():
            p = B.Params(**{**bp, "night_cost": c})
            log(f"   [{bk}, night {c}/side]")
            for E in M.SIZES:
                b0 = M.replay(s, E, p)
                r = M.replay(s, E, dataclasses.replace(p, tilt=M.make_tilt(Na, F, "AU3", mu, sd)))
                okk, _ = M.judge(log, f"${E/1e3:.1f}k", r, b0, judged=(c == 2.5))
                if c == 2.5:
                    allok.append(okk)
    log(f"   AU3 on auction returns: {sum(allok)}/{len(allok)} judged cells pass")
    T.to_pickle(ROOT / "data/research/program/auction_audit_picks.pkl")
    log(f"\ndone {time.time()-t0:.0f}s")
    f.close()


if __name__ == "__main__":
    main()
