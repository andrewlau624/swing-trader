"""Study AO (Round 17): whole-share drag at $2.3k and the cheaper look-alike / probe levers.

    PYTHONPATH=. .venv/bin/python -m research.sim.ibs_whole

Pre-registration: research/drafts/round1_prose.md, "Round 17", Study AO (committed before any
number below). Study R's method (whole vs fractional, by size). The book = night 0.5 + IBS 0.5,
no intraday leg, live tilt, weekend x0.5, corr 0.7, name cap 0.10, whole shares + the $150
1-share probe; deposits off (fixed-capital daily returns). Look-alike prices come from
panel.pkl (2020-10+); the same-index return is used for sizing only. SPLG has no research data:
the SPY->SPLG gain is shown separately as SPY_price/8.5 and labelled a sensitivity.
"""
from __future__ import annotations

import pathlib
import time

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import data as D
from .validate import load_sim

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/ibs_whole_out.txt"
PROBE_USD = 150.0
SIZES = (2300.0, 10000.0, 25000.0)
HALVES = (("2021-23", "2021-01-01", "2023-12-31"),
          ("2024-26", "2024-01-01", "2026-12-31"),
          ("full", None, None))
LOOK = {"QQQ": "QQQM", "IWM": "VTWO", "MDY": "IJH", "XLK": "VGT", "XLF": "VFH", "XLE": "VDE",
        "XLV": "VHT", "XLI": "VIS", "XLY": "VCR", "XLP": "VDC", "XLU": "VPU", "XLB": "VAW",
        "SMH": "SOXX", "EEM": "IEMG", "EFA": "IEFA"}          # DIA, XBI, SPY(SPLG missing)


def day(s, N, O, lookO, E, d, p, whole, probe, ibs_probe, use_look):
    pnl = 0.0
    # --- IBS leg
    legs = s.I.get(d, [])
    iused = 0.0
    if legs:
        ibs_leg = p.ibs_w * E
        for sym, o1, r in legs:
            px = o1
            if use_look and sym in lookO and d in O.index:
                i = O.index.get_loc(d)
                if i + 1 < len(O.index):
                    v = lookO[sym].get(O.index[i + 1], np.nan)
                    if np.isfinite(v) and v > 0:
                        px = float(v)
            per = ibs_leg / len(legs)
            if whole:
                sh = np.floor(per / px)
                if sh < 1 and ibs_probe and px <= ibs_probe:
                    sh = 1.0
            else:
                sh = per / px
            iused += sh * px
            pnl += sh * px * (r - 2 * 1.0 / 1e4)
    idle = max(0.0, p.ibs_w * E - iused)
    b = s.bil.get(d, 0.0); b = float(b) if np.isfinite(b) else 0.0
    pxb = float(s.C.at[d, "BIL"]) if d in s.C.index and np.isfinite(s.C.at[d, "BIL"]) else np.nan
    tb = np.floor(idle / pxb) * pxb if (whole and np.isfinite(pxb) and idle >= 50) else (0.0 if whole else idle)
    pnl += tb * b
    cash = E - iused - tb
    # --- night leg
    nd = N.get(d)
    if nd is not None:
        leg = p.night_w * E
        wt = sg.night_tilt(nd.vol20, nd.day_ret, p.tilt_k)
        c = B.cost_bps(p.night_cost, nd.price, nd.adv)
        per = leg * nd.frac * wt
        if s._gap(d) > 1:
            per = per * 0.5
        for i in range(len(per)):
            if whole:
                q = np.floor(per[i] / nd.price[i])
                if q < 1 and probe and nd.price[i] <= probe:
                    q = 1.0
                if q < 1:
                    continue
                if cash - q * nd.price[i] < 0:
                    continue
            else:
                q = per[i] / nd.price[i]
            cash -= q * nd.price[i]
            pnl += q * nd.close[i] * (nd.ret[i] - 2 * c[i] / 1e4)
    return pnl


def replay(s, N, O, lookO, size, p, whole, probe, ibs_probe, use_look):
    return pd.Series([day(s, N, O, lookO, size, d, p, whole, probe, ibs_probe, use_look) / size
                      for d in s.days], index=s.days)


def main():
    t0 = time.time()
    f = open(OUT, "w")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); f.write(x + "\n"); f.flush()

    log("== Study AO: whole-share drag at $2.3k; started", pd.Timestamp.now(), "==")
    s = load_sim(raw_price=True)
    N = B.night_days(raw_price=True, max_corr=0.7)
    s.N = N
    etf = D.etf(); O = etf["open"]
    pan = D.panel()["open"]
    lookO = {orig: pan[la] for orig, la in LOOK.items() if la in pan.columns}
    # SPLG sensitivity: SPY/8.5
    if "SPY" in O.columns:
        lookO["SPY"] = O["SPY"] / 8.5
    log(f"look-alike price series: {sorted(lookO)}  (from {len(O)} sessions)\n")
    I3, I2, I1 = B.ibs_days(top_k=3), B.ibs_days(top_k=2), B.ibs_days(top_k=1)

    for cost in ("tier", "tier_hi"):
        p = B.Params(night_w=0.5, ibs_w=0.5, night_cost=cost, ibs_cost_bps=1.0, noise_on=False,
                     tilt="live", weekend_scale=0.5, conviction_w=0.0)
        log(f"[{cost}] fixed capital, CAGR / Sharpe / maxDD by half; gap vs fractional (pp/yr)")
        for size in SIZES:
            rows = [
                ("whole+probe", True, PROBE_USD, None, False, I3),
                ("fractional", False, None, None, False, I3),
                ("IBS top1", True, PROBE_USD, None, False, I1),
                ("IBS top2", True, PROBE_USD, None, False, I2),
                ("look-alike", True, PROBE_USD, None, True, I3),
                ("IBS probe", True, PROBE_USD, PROBE_USD, False, I3),
                ("look+IBSprobe", True, PROBE_USD, PROBE_USD, True, I3),
                ("top2+look POST-HOC", True, PROBE_USD, None, True, I2),
            ]
            frac = replay(s, N, O, lookO, size, p, False, None, None, False)
            fcagr = B.stats(frac)[0]
            base = replay(s, N, O, lookO, size, p, True, PROBE_USD, None, False)
            bcagr = B.stats(base)[0]
            for lab, wh, pr, ibpr, ul, I in rows:
                s.I = I
                r = replay(s, N, O, lookO, size, p, wh, pr, ibpr, ul)
                c_, sh, dd = B.stats(r)
                gap = (c_ - fcagr) * 100
                dl = (c_ - bcagr) * 100
                h = "/".join(f"{B.stats(r[a:b])[0]*100:5.1f}" for _, a, b in HALVES[:2])
                log(f"  ${size/1e3:5.1f}k {lab:14s} {h} full {c_*100:5.1f}/{sh:4.2f}/{dd*100:4.0f}  "
                    f"gap-vs-frac {gap:+5.2f}  d-vs-base {dl:+5.2f}")
            s.I = I3
        log("")

    log(f"done {time.time()-t0:.0f}s")
    f.close()


if __name__ == "__main__":
    main()
