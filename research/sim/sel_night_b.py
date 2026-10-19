"""Study SEL-NIGHT-B: night-leg cash-starvation buy order (round1_prose.md, N 1030 -> 1031).

Post-processes `sel_night.py`'s kept-name file (current survivor rule; per = fraction of the leg budget,
w = tilt, price, r = overnight outcome). Per night: target_i = per_i x leg$; buy loop in the rule's order
with whole shares, 1-share probe when target < 1 share and price <= $150, skip-and-continue when cash is
exhausted (executor.py:1127-1141); cash pool = kappa x sum(targets).
Orders: A current (day_ret asc)  B price asc  C tilt w desc  D random.
Metric: per-night $ P&L of the bought set / leg$ (bp of leg budget), paired vs A on binding nights.

Run:  PYTHONPATH=. .venv/bin/python research/sim/sel_night_b.py [--which primary]
Out:  data/research/program/sel_night_b_out.txt
"""
from __future__ import annotations

import argparse
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROG = ROOT / "data" / "research" / "program"
NIGHT_W = 0.65           # nx_s2 night weight (taxable); Roth 0.5 reported via equity scaling
PROBE_MAX = 150.0
ORDERS = ["A_dayret", "B_cheap", "C_tilt", "D_random"]


def order_idx(rule: str, g: pd.DataFrame, rng: np.random.Generator) -> np.ndarray:
    if rule == "A_dayret":
        return np.argsort(g["day_ret"].to_numpy(float), kind="stable")
    if rule == "B_cheap":
        return np.argsort(g["price"].to_numpy(float), kind="stable")
    if rule == "C_tilt":
        return np.argsort(-g["w"].to_numpy(float), kind="stable")
    if rule == "D_random":
        return rng.permutation(len(g))
    raise ValueError(rule)


def night_pnl(g: pd.DataFrame, order: np.ndarray, leg_usd: float, kappa: float) -> tuple[float, int, int, float]:
    px = g["price"].to_numpy(float)
    per = g["per"].to_numpy(float)
    r = g["r"].to_numpy(float)
    target = per * leg_usd
    cash = kappa * target.sum()
    pnl, bought, skipped, deployed = 0.0, 0, 0, 0.0
    for i in order:
        q = int(np.floor(target[i] / px[i]))
        if q < 1 and px[i] <= PROBE_MAX:
            q = 1
        if q < 1:
            continue
        if cash - q * px[i] < 0:
            skipped += 1
            continue
        cash -= q * px[i]
        deployed += q * px[i]
        pnl += q * px[i] * r[i]
        bought += 1
    return pnl, bought, skipped, deployed


def clus_t(x: np.ndarray) -> float:
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--which", default="primary")
    args = ap.parse_args()
    nm = pd.read_parquet(PROG / f"sel_night_names_{args.which}.parquet")
    if "rule" in nm.columns:            # sel_night.py now records every rule; B tests the live one
        nm = nm[nm["rule"] == "current"].drop(columns=["rule"]).copy()
    nm["date"] = pd.to_datetime(nm["date"])
    if "rule" in nm.columns:
        nm = nm[nm["rule"] == "current"].drop(columns=["rule"]).reset_index(drop=True)
    L = [f"SEL-NIGHT-B: cash-starvation buy order, universe {args.which}, names {len(nm)} nights {nm['date'].nunique()} "
         f"{nm['date'].min().date()}..{nm['date'].max().date()}", ""]
    groups = list(nm.groupby("date"))
    for equity in [2300.0, 4000.0, 10000.0]:
        leg_usd = NIGHT_W * equity
        for kappa in [1.0, 0.5, 0.25]:
            rng = np.random.default_rng(20261018)
            rows = []
            for d, g in groups:
                rec = dict(date=d, n=len(g))
                for rule in ORDERS:
                    o = order_idx(rule, g, rng)
                    p, b, s, dep = night_pnl(g, o, leg_usd, kappa)
                    rec[f"pnl_{rule}"] = p / leg_usd * 1e4
                    rec[f"b_{rule}"] = b
                    rec[f"s_{rule}"] = s
                    rec[f"dep_{rule}"] = dep
                rows.append(rec)
            t = pd.DataFrame(rows)
            t["year"] = t["date"].dt.year
            bind = t[t["s_A_dayret"] > 0]
            L.append(f"== equity ${equity:,.0f} (leg ${leg_usd:,.0f}) kappa {kappa}: binding nights {len(bind)}/{len(t)} "
                     f"({len(bind)/len(t):.1%}); A buys/night {t['b_A_dayret'].mean():.1f}, skipped on binding nights "
                     f"{bind['s_A_dayret'].mean() if len(bind) else 0:.1f}; A level {t['pnl_A_dayret'].mean():+.2f} bp/night of leg ==")
            for rule in ORDERS[1:]:
                d = (bind[f"pnl_{rule}"] - bind["pnl_A_dayret"]).to_numpy(float)
                if not len(d):
                    L.append(f"  {rule:9s} no binding nights")
                    continue
                h1 = d[bind["year"].to_numpy() <= 2012]
                h2 = d[bind["year"].to_numpy() >= 2013]
                s = np.sort(d)
                ex5 = s[:-5].mean() if len(s) > 10 else float("nan")
                all_d = (t[f"pnl_{rule}"] - t["pnl_A_dayret"]).to_numpy(float)
                L.append(f"  {rule:9s} vs A on binding nights: {d.mean():>+7.2f} bp/night t {clus_t(d):>6.2f} med {np.median(d):>+6.2f} "
                         f"hit {(d > 0).mean():.3f} h1 {h1.mean() if len(h1) else float('nan'):>+7.2f} h2 {h2.mean() if len(h2) else float('nan'):>+7.2f} "
                         f"ex5 {ex5:>+7.2f} | all nights {all_d.mean():>+6.2f} bp/night = {all_d.mean() * 250 / 100 * NIGHT_W:>+5.2f} pp/yr of equity "
                         f"| buys/night {t[f'b_{rule}'].mean():.1f}")
        L.append("")
    txt = "\n".join(L) + "\n"
    (PROG / "sel_night_b_out.txt").write_text(txt)
    print(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
