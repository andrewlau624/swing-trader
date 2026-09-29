"""Study C: night-tilt v2 (addendum 23, built OFF) restated on the RAW night pool.

    PYTHONPATH=. .venv/bin/python -m research.sim.tilt_v2_raw

Pre-registration: research/drafts/round1_prose.md, "Amendment - Study C" (stamped
Tue Sep 29 01:50:46 PDT 2026, before any number below was computed).

Variants (2): V7 (cap .10) and moderate-as-built (cap .15), 1.0x overnight, conviction .5,
each with tilt = signals.night_tilt_v2(vol20, day_ret, prev_ret, k=.25) on the RAW pool
(corr 0.7), whole shares, $3k + $1k/21 sessions. Baselines: the same books with the shipped
v1 tilt (p.tilt = "live").

Placebo: the same book with the picks' THIRD input (prev day's return) replaced by a
within-day shuffle across the day's picks (the first two inputs are unchanged), 200 draws.
Pass bar: the placebo >= 95th percentile of the increment means in BOTH halves.

Pass bar (pre-registered): v2 beats v1 in BOTH halves at tier AND tier_hi; the placebo
>= 95th pct in both halves; NW t >= 2.0 of the daily increment over 2021-26; the 2016-20
holdout is not computable (the tilt's inputs start 2020-10), so the verdict caps at SHADOW.
"""
from __future__ import annotations

import pathlib
import pickle
import time

import numpy as np
import pandas as pd

from . import book as B
from . import growth as G
from .validate import load_sim
from swingtrader.daily import signals as sg

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/tilt_v2_raw_out.txt"
PER = (("2021-23", "2021-01-01", "2023-12-31"), ("2024-26", "2024-01-01", "2026-12-31"))


def nw_t(x, lags: int = 5) -> float:
    v = x.dropna().values
    n = len(v)
    if n < 30:
        return float("nan")
    e = v - v.mean()
    var = (e * e).sum() / n
    for k in range(1, lags + 1):
        var += 2 * (1 - k / (lags + 1)) * (e[k:] * e[:-k]).sum() / n
    return v.mean() / np.sqrt(max(var, 1e-18) / n)


def main():
    fs = open(OUT, "w")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True)
        fs.write(x + "\n")
        fs.flush()

    t0 = time.time()
    log("== Study C: tilt v2 on the raw pool, started", pd.Timestamp.now(), "\n")
    s = load_sim(raw_price=True)
    P = pickle.load(open(ROOT / "data/research/night/panel.pkl", "rb"))
    C = P["close"].astype("float64")
    icl = {d: i for i, d in enumerate(C.index)}
    rng = np.random.default_rng(11)

    for cap, lab in ((0.10, "V7 cap.10"), (0.15, "T2b as-built cap.15")):
        s.N = B.night_days(raw_price=True, max_corr=0.7, max_name_pct=cap)
        # the picks' third input: yesterday's return, from the adjusted daily panel
        prev_by = {}
        for d, nd in s.N.items():
            i = icl.get(d)
            if i is None or i == 0:
                prev_by[d] = np.full(len(nd.syms), np.nan)
                continue
            row, pr = C.iloc[i], C.iloc[i - 1]
            prev_by[d] = np.array([row[sy] / pr[sy] - 1
                                   if (sy in pr.index and np.isfinite(pr[sy])) else np.nan
                                   for sy in nd.syms])
        for cost in ("tier", "tier_hi"):
            kw = {**G.V7, **G.cfg(1.0, 0.5, 2), "night_cost": cost}
            def key(nd):
                # the (day, first pick) pair is unique per day's NightDay
                return (str(np.asarray(nd.syms, dtype=object)[0]), len(nd.syms))
            PB_ = {key(nd): (prev_by.get(d, np.full(len(nd.syms), np.nan)), d)
                   for d, nd in s.N.items()}
            base = s.replay(B.Params(**{**kw, "tilt": "live"}))

            def vt(nd, _pb=PB_):
                h = _pb.get(key(nd))
                return sg.night_tilt_v2(nd.vol20, nd.day_ret, h[0] if h else np.full(len(nd.syms), np.nan), 0.25)
            alt = s.replay(B.Params(**{**kw, "tilt": vt}))
            d1 = alt["r"] - base["r"]
            draws, dph = [], []

            def mk_pb():
                pb2 = {}
                for d, nd in s.N.items():
                    a0 = prev_by[d]
                    if np.isfinite(a0).sum() >= 2:
                        w = np.where(np.isfinite(a0))[0]
                        a2 = a0.copy()
                        a2[w] = rng.permutation(a0[w])
                    else:
                        a2 = a0
                    pb2[id(nd)] = a2
                return pb2
            for _ in range(200):
                pb2 = {}
                for d, nd in s.N.items():
                    a0 = prev_by[d]
                    if np.isfinite(a0).sum() >= 2:
                        w = np.where(np.isfinite(a0))[0]
                        a2 = a0.copy()
                        a2[w] = rng.permutation(a0[w])
                        pb2[key(nd)] = a2

                def vf(nd, _g=pb2):
                    h = _g.get(key(nd))
                    return sg.night_tilt_v2(nd.vol20, nd.day_ret, h if h is not None else np.full(len(nd.syms), np.nan), 0.25)
                AP = s.replay(B.Params(**{**kw, "tilt": vf}))
                draws.append(B.stats(AP["r"] - base["r"])[0])
                dph.append([B.stats((AP['r'] - base['r'])[a2b[1]:a2b[2]])[0] for a2b in PER])
            draws = np.array(draws)
            dph = np.array(dph)
            parts = [B.stats(d1[a:b2])[0] * 100 for _, a, b2 in PER]
            log(f"{lab} {cost}: v2-v1 halves {parts[0]:+.2f}/{parts[1]:+.2f}pp full "
                f"{B.stats(d1)[0]*100:+.2f}pp  NW t {nw_t(d1):+.2f}")
            for hi in range(2):
                a_, b_ = PER[hi][1], PER[hi][2]
                act = B.stats(d1[a_:b_])[0] * 100          # the period CAGR of the increment
                pm = dph[:, hi].mean() * 100
                p95 = np.percentile(dph[:, hi], 95) * 100
                pct = 100 * (dph[:, hi] < (act / 100)).mean()
                log(f"   placebo {PER[hi][0]}: actual {act:+7.2f}pp  "
                    f"placebo mean {pm:+7.2f}  p95 {p95:+7.2f} -> pct {pct:.0f}")
    fs.close()


if __name__ == "__main__":
    main()
