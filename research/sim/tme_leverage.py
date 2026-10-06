"""Study TME-L2 - capital efficiency of TME via leveraged Treasury ETFs.

    PYTHONPATH=. .venv/bin/python -m research.sim.tme_leverage > data/research/program/tme_leverage_out.txt

Pre-registered: research/drafts/study_tme_leverage.md (N 822 -> 823). Frozen TME1 signal
(close(T-3) -> close(T)); research only, no deployment. Whole-share account at real sizes,
after tax, drawdown budgets, and a cross-edge comparison against IBS.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import tme_shadow as TS

CACHE = __import__("pathlib").Path("data/research/tme")
COST = {"TLT": 2.0, "TMF": 5.0, "UBT": 15.0}      # bp per side
FIN = 0.125                                        # margin debit, /yr act/360
TAX = 0.30
SIZES = (1000.0, 2300.0, 3000.0, 5000.0, 10000.0, 25000.0)
ARMS = {"A TLT 1x": {"TLT": 1.0}, "C UBT 2x": {"UBT": 1.0},
        "D TMF 3x": {"TMF": 1.0}, "E 0.5 TLT+0.5 TMF": {"TLT": 0.5, "TMF": 0.5}}
IBS = {"IBS 1x": (0.083, 83.0), "IBS 1.25x": (0.105, 105.0), "IBS 1.5x": (0.127, 127.0)}  # cle_attack @$10k after tax


def load(sym):
    p = CACHE / f"yahoo_{sym}.parquet"
    if p.exists():
        return pd.read_parquet(p)
    df = TS._yahoo(sym)
    CACHE.mkdir(parents=True, exist_ok=True)
    df.to_parquet(p)
    return df


def main():
    px = {s: load(s) for s in ("TLT", "TMF", "UBT")}
    cal = px["TLT"].index[(px["TLT"].index >= "2009-05-01") & (px["TLT"].index <= "2026-09-30")]
    wins = TS.windows(cal)
    irx = pd.read_csv("data/research/tme/px_IRX.csv", parse_dates=["date"]).set_index("date")["close"]
    irx = irx.reindex(cal.union(irx.index)).ffill().reindex(cal)
    print("STUDY TME-L2 (frozen TME1 signal; research only)")
    print(f"windows {len(wins)}  {wins[0][0].date()}..{wins[-1][1].date()}  "
          f"costs {COST} fin {FIN:.3f}")

    # ---------------- per-window instrument measurement (fractional)
    rows = []
    for t3, t in wins:
        r = {}
        for s in ("TLT", "TMF", "UBT"):
            a = px[s]["adj"]
            if t3 in a.index and t in a.index:
                r[s] = float(a.loc[t] / a.loc[t3] - 1)
        if "TLT" not in r:
            continue
        rows.append((t3, t, r))
    W = pd.DataFrame([{"t3": a, "t": b, **rr} for a, b, rr in rows]).set_index("t")
    W["days"] = (W.index - W["t3"]).dt.days
    W["L1"] = W.TLT - 2 * COST["TLT"] / 1e4
    W["L2"] = 2 * W.TLT - 2 * COST["TLT"] / 1e4 - FIN * W.days / 360
    W["L3"] = W.TMF - 2 * COST["TMF"] / 1e4
    W["L2r"] = W.UBT - 2 * COST["UBT"] / 1e4
    print("\n-- per-window (net of costs/financing), fractional --")
    for k, lab in (("L1", "A TLT 1x"), ("L2", "B TLT 1.25x/2x margin"), ("L3", "D TMF 3x"), ("L2r", "C UBT 2x")):
        x = W[k]
        eq = np.cumprod(1 + x)
        print(f"  {lab:22s} mean {x.mean()*1e4:+6.1f}bp  median {x.median()*1e4:+6.1f}bp  sd {x.std()*1e4:5.0f}  "
              f"worst {x.min()*100:+6.2f}%  maxDD {float((eq/np.maximum.accumulate(eq)-1).min())*100:6.1f}%  "
              f"Sharpe/w {x.mean()/x.std():+.2f}")
    print(f"  ETF drag TMF-3xTLT mean {((W.TMF-3*W.TLT).mean())*1e4:+.1f}bp/w  "
          f"UBT-2xTLT mean {((W.UBT-2*W.TLT).mean())*1e4:+.1f}bp/w")
    print(f"  annualised fractional: L1 {(1+W.L1).prod()**(12/len(W))-1:+.1%}  "
          f"L2 {(1+W.L2).prod()**(12/len(W))-1:+.1%}  L3 {(1+W.L3).prod()**(12/len(W))-1:+.1%}  "
          f"L2r {(1+W.L2r).prod()**(12/len(W))-1:+.1%}  (pre-tax, deployed-capital basis)")

    # ---------------- whole-share account, real sizes
    print("\n-- whole-share account, after tax, 2009-2026 --")
    print(f"  {'size':>6} {'arm':<16} {'CAGR':>7} {'$/yr':>7} {'maxDD':>7} {'worst win':>9} "
          f"{'eff x':>6} {'util%':>6} {'drag$':>7}")
    for size in SIZES:
        for name, legs in ARMS.items():
            if name == "C UBT 2x" and "UBT" not in px:
                continue
            o = run_share(W, px, irx, size, legs)
            print(f"  {size:>6.0f} {name:<16} {o['cagr']*100:6.1f}% {o['dollars']:7.0f} "
                  f"{o['mdd']*100:6.1f}% {o['worst']*100:7.2f}% {o['effx']:6.2f} {o['util']*100:5.1f}% "
                  f"{o['drag']:7.1f}")

    # ---------------- fractionally-levered TLT: risk-budget cap
    print("\n-- synthetic TLT leverage: max under DD budget (fractional, after tax, $10k) --")
    print(f"  {'m':>5} {'CAGR':>7} {'maxDD':>7} {'worst win':>10}")
    cap = {0.20: None, 0.25: None, 0.33: None}
    for m in (1.0, 1.25, 1.5, 2.0, 2.5, 3.0):
        o = run_frac(W, m, 10000.0)
        print(f"  {m:5.2f} {o['cagr']*100:6.1f}% {o['mdd']*100:6.1f}% {o['worst']*100:9.2f}%")
        for b in cap:
            if -o["mdd"] <= b:
                cap[b] = m
    for b, m in cap.items():
        print(f"  cap under {int(b*100)}% DD budget: {m if m else 'none <=3x'}")

    # ---------------- cross-edge comparison
    print("\n-- CROSS-EDGE: $/yr per $1,000 of account capital (after tax) --")
    print(f"  {'strategy':<16} {'$ / 1k / yr':>12} {'maxDD':>8} {'mechanism':<34} {'lev cap (25% DD)':>16}")
    for k, (c, d) in IBS.items():
        print(f"  {k:<16} {d:12.0f} {c:8.1%} {'IBS close-in-range liquidity provision':<34} {'1.25x':>16}")
    for name, legs in (("TME 1x TLT", {"TLT": 1.0}), ("TME TMF 3x", {"TMF": 1.0}),
                       ("TME 0.5/0.5", {"TLT": 0.5, "TMF": 0.5})):
        o = run_share(W, px, irx, 10000.0, legs)
        print(f"  {name:<16} {o['cagr']*1000:12.0f} {o['mdd']:8.1%} {'Treasury month-end duration extension':<34} "
              f"{(str(cap[0.25])+'x' if cap[0.25] else 'none'):>16}")
    print("\n  note: TME is deployed only ~14% of sessions, so it STACKS on IBS's month-end-idle cash;")
    print("  the question is its incremental $/account-dollar, not a replacement for IBS.")

    print("\nVERDICT INPUTS")
    print("  Compare TME 1x vs TMF 3x $/k (above) to IBS 1.25x $105/k. If TME leverage does not beat")
    print("  IBS per account dollar (or beats it only with worse drawdown), the answer is 'more IBS +")
    print("  modest TME', not a standalone leveraged TME leg. No deployment.")


def run_share(W, px, irx, size, legs):
    """Whole-share dollar path; windows are non-overlapping. Daily mark not needed for DD because the
    account is flat (T-bills) between windows; DD = compounded window-equity DD."""
    E, y0, carry = size, size, 0.0
    eq = [E]; worst = 0.0; notional_frac = []; deployed = 0.0
    prev_t = None
    drag = 0.0
    for t3, t in zip(W["t3"], W.index):
        if prev_t is not None:
            gap = (t3 - prev_t).days
            E *= (1 + float(np.nan_to_num(irx.get(t3, 0.0))) / 100 / 252) ** gap
        E0 = E
        for s, w in legs.items():
            p3 = float(px[s]["close"].get(t3, np.nan)); p1 = float(px[s]["close"].get(t, np.nan))
            if not (np.isfinite(p3) and np.isfinite(p1) and p3 > 0):
                continue
            sh = np.floor(w * E0 / p3)
            spend = sh * p3
            E -= spend * COST[s] / 1e4                       # entry cost
            E += sh * p1 - spend                             # P&L
            E -= sh * p1 * COST[s] / 1e4                     # exit cost
            notional_frac.append(sh * p3 / E0)
            if s == "TMF":
                drag += sh * (p1 - p3) * 0 - (3 * (p3 - p3))  # placeholder; drag measured in per-window section
            deployed += 1
        eq.append(E); worst = min(worst, E / E0 - 1)
        prev_t = t
        yr = t.year
        # year-end tax
        nxt = W.index[W.index.get_loc(t) + 1] if W.index.get_loc(t) + 1 < len(W) else None
        if nxt is None or nxt.year != t.year:
            gain = E - y0; net = gain - carry
            if net > 0:
                E -= TAX * net; carry = 0.0
            else:
                carry = -net
            y0 = E
    eq = np.asarray(eq)
    yrs = (W.index[-1] - W["t3"].iloc[0]).days / 365.25
    c = (E / size) ** (1 / yrs) - 1 if E > 0 else -1
    return dict(cagr=c, dollars=size * c, mdd=float((eq / np.maximum.accumulate(eq) - 1).min()),
                worst=worst, effx=float(np.mean(notional_frac)) if notional_frac else 0,
                util=(deployed * 3) / len(pd.bdate_range(W["t3"].iloc[0], W.index[-1])), drag=0.0)


def run_frac(W, m, size):
    """Fractional TLT at leverage m on margin, after tax."""
    E, y0, carry = size, size, 0.0
    eq = [E]; worst = 0.0
    for t, row in W.iterrows():
        r = m * row.TLT - (m - 1) * FIN * row.days / 360 - (2 * COST["TLT"] / 1e4) * m
        E *= 1 + r
        eq.append(E); worst = min(worst, r)
        nxt = W.index[W.index.get_loc(t) + 1] if W.index.get_loc(t) + 1 < len(W) else None
        if nxt is None or nxt.year != t.year:
            gain = E - y0; net = gain - carry
            if net > 0:
                E -= TAX * net; carry = 0.0
            else:
                carry = -net
            y0 = E
    eq = np.asarray(eq)
    yrs = (W.index[-1] - W["t3"].iloc[0]).days / 365.25
    c = (E / size) ** (1 / yrs) - 1 if E > 0 else -1
    return dict(cagr=c, mdd=float((eq / np.maximum.accumulate(eq) - 1).min()), worst=worst)


if __name__ == "__main__":
    main()
