"""Study ACC - account structure for the OOS-validated IBS leg at small size.

    PYTHONPATH=. .venv/bin/python -m research.sim.account_struct > data/research/program/account_struct_out.txt

Pre-registered: research/drafts/round1_prose.md, "Amendment - Study ACC" (N 833 -> 834). One look.
Research only, no deployment. The leg is the LIVE IBS rule only (book.ibs_days), 3bp/side. Night
and noise legs are OFF. Leverage is non-callable by design: a partial 3x-ETF allocation (f = L/3 of
the capital in the actual 3x proxy of each pick, the rest in T-bills) vs a callable Reg-T margin
twin. Accounts: taxable (30% year-end on the net gain, loss carried forward) vs Roth (tax-free,
cash IRA - no borrowing). Whole shares, idle cash in BIL. The Roth-first structure sends the
guaranteed $7.5k/yr ($625/21 sessions) to the Roth and holds the starting capital where it is.

Judge window 2016-02..2020-12 (the untouched IBS regime); also tested ex-2020 (2017-19) and the
2022 bear (in-sample) because the CLE leverage return is vol-regime-concentrated. Constraint: an
arm passes only if its strategy maxDD stays within -25% and it never liquidates in EVERY window.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import cle_attack as CA
from . import data as D

IBS_BPS = CA.IBS_BPS
TAX = CA.TAX
MARGIN_FIN = 0.125
MARGIN_FLOOR = 2000.0
MAINT = 0.25
DEP = 625.0
DEP_EVERY = 21
SIZES = (2300.0, 10000.0, 25000.0)
FULL = ("2016-02-01", "2020-12-31")
EX2020 = ("2017-02-01", "2019-12-31")
BEAR2022 = ("2022-01-01", "2022-12-31")
INSAMPLE = ("2021-01-01", "2026-09-30")
WINDOWS = [("JUDGE 2016-20", FULL), ("EX-2020 2017-19", EX2020),
           ("2022 BEAR", BEAR2022), ("IN-SAMPLE 2021-26", INSAMPLE)]

# The proxy map and the letf sizing are the economics the Study ACC shadow imports verbatim.
# Keep them import-safe (no research data load): the live shadow must not depend on the cache.
PROXY = CA.PROXY
LEV = 1.25


def letf_fraction(L: float = LEV) -> float:
    """Fraction of capital in the 3x proxy for a target multiple L (Study ACC / CLE frost)."""
    return min(L / 3.0, 1.0)


DF = IDX = GROUPS = CLOSE = BIL = None


def _load() -> None:
    """Load the cached research data (build_legs + ETF daily bars). Lazy: importing this
    module to reach PROXY / letf_fraction must not need the ~3 GB research cache."""
    global DF, IDX, GROUPS, CLOSE, BIL
    if DF is not None:
        return
    DF = CA.build_legs()
    IDX = CA.IDX
    GROUPS = {d: g for d, g in DF.groupby("d")}
    CLOSE = D.etf()["close"]
    BIL = CLOSE["BIL"].pct_change(fill_method=None).reindex(IDX).fillna(0.0)


def leg_pnl(E: float, kind: str, m: float, g: pd.DataFrame):
    """Whole-share P&L fraction of equity E for one signal-day's basket.

    kind 'base'   : all E in the base ETF at 1x.
    kind 'letf'   : f = min(m/3, 1) of E in the actual 3x proxy (or the base name where no
                    liquid 3x exists), the rest idle in BIL. Non-callable.
    kind 'margin' : m x E notional in the base ETF borrowed at 12.5%/yr, callable.
    """
    if kind == "base":
        budget, ep, xp = E, "b_entry", "b_exit"
    elif kind == "letf":
        budget, ep, xp = letf_fraction(m) * E, "l_entry", "l_exit"
    else:
        budget, ep, xp = m * E, "b_entry", "b_exit"
    k = max(len(g), 1)
    inv = cost = proc = 0.0
    for _, row in g.iterrows():
        p = row[ep]
        if not np.isfinite(p) or p <= 0:
            continue
        sh = np.floor((budget / k) / p)
        if sh < 1:
            continue
        inv += sh * p
        cost += sh * p
        proc += sh * row[xp]
    pnl = proc - cost - 2 * IBS_BPS / 1e4 * cost
    borrow = max(0.0, inv - E) if kind == "margin" else 0.0
    if borrow:
        pnl -= MARGIN_FIN / 360.0 * borrow
    return pnl / E, inv, borrow


def irr(flows, final, t_end):
    """Money-weighted return from dated negative contributions + a final balance."""
    t0 = flows[0][0]

    def npv(r):
        return sum(c / (1 + r) ** ((t - t0).days / 365.25) for t, c in flows) \
            + final / (1 + r) ** ((t_end - t0).days / 365.25)

    lo, hi = -0.95, 5.0
    if npv(lo) < 0 or npv(hi) > 0:
        return float("nan")
    for _ in range(200):
        mid = (lo + hi) / 2
        if npv(mid) > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def simulate(days, start_tax, start_roth, kind, m, dep_tax, dep_roth, taxable=True):
    Et, Er = start_tax, start_roth
    y0t, y0r = start_tax, start_roth
    carry = 0.0
    contrib = start_tax + start_roth
    contrib_t = start_tax
    flows = [(days[0], -contrib)]
    eq = []
    peak = contrib
    mdd_acct = 0.0
    nav = peak_nav = 1.0
    mdd_tw = 0.0
    liq = 0
    effx, rets = [], []
    for i, t in enumerate(days):
        e0 = Et + Er
        g = GROUPS.get(t)
        for acct in (0, 1):
            E = Et if acct == 0 else Er
            if E <= 0:
                continue
            if g is not None:
                k, mm = (kind, m)
                if kind == "margin" and E < MARGIN_FLOOR:
                    k, mm = "base", 1.0                 # Reg T floor: no borrowing below $2k
                r, inv, borrow = leg_pnl(E, k, mm, g)
                if kind == "margin" and E >= MARGIN_FLOOR:
                    if E * (1 + r) < MAINT * max(inv, 1e-9):
                        liq += 1
                E *= (1 + r)
                effx.append((3.0 * inv / E) if kind == "letf" else (inv / E))
            else:
                E *= (1 + float(BIL.get(t, 0.0)))
            if acct == 0:
                Et = E
            else:
                Er = E
        e1 = Et + Er
        r_comb = (e1 - e0) / e0 if e0 > 0 else 0.0
        rets.append(r_comb)
        nav *= (1 + r_comb)
        peak_nav = max(peak_nav, nav)
        mdd_tw = min(mdd_tw, nav / peak_nav - 1)
        if i > 0 and i % DEP_EVERY == 0:
            Et += dep_tax
            Er += dep_roth
            y0t += dep_tax
            y0r += dep_roth
            contrib += dep_tax + dep_roth
            contrib_t += dep_tax
            if dep_tax + dep_roth:
                flows.append((t, -(dep_tax + dep_roth)))
        last = (i == len(days) - 1) or (days[i + 1].year != t.year)
        if last and taxable and Et > 0:
            net = (Et - y0t) - carry
            if net > 0:
                Et -= TAX * net
                carry = 0.0
            else:
                carry = -net
            y0t = Et
        eq.append(Et + Er)
        peak = max(peak, Et + Er)
        mdd_acct = min(mdd_acct, (Et + Er) / peak - 1)
    end = Et + Er
    yrs = (days[-1] - days[0]).days / 365.25
    flows.append((days[-1], end))
    return dict(
        irr=irr(flows, 0.0, days[-1]),
        tw=nav ** (252 / len(days)) - 1 if nav > 0 else -1.0,
        dollars=(end - contrib) / yrs if yrs > 0 else float("nan"),
        mdd_acct=mdd_acct, mdd_tw=mdd_tw, liq=liq, end=end, contrib=contrib,
        effx=float(np.mean(effx)) if effx else 1.0,
        rets=pd.Series(rets, index=days), eq=pd.Series(eq, index=days), flows=flows,
    )


def run(days, size, acct, kind, m, rho=1.0):
    if acct == "tax":
        return simulate(days, size, 0.0, kind, m, DEP, 0.0, taxable=True)
    if acct == "roth":
        return simulate(days, 0.0, size, kind, m, 0.0, DEP, taxable=False)
    if acct == "seq":                      # starting capital taxable; $7.5k/yr to the Roth
        return simulate(days, (1 - rho) * size, rho * size, kind, m, 0.0, DEP, taxable=True)
    raise ValueError(acct)


STRUCTURES = [
    ("A all-taxable   base 1x ", "tax", "base", 1.0),
    ("B all-taxable   letf 1.25x", "tax", "letf", 1.25),
    ("C all-Roth      base 1x ", "roth", "base", 1.0),
    ("D all-Roth      letf 1.25x", "roth", "letf", 1.25),
    ("E all-Roth      letf 1.50x", "roth", "letf", 1.5),
    ("F all-Roth      letf 2.00x", "roth", "letf", 2.0),
    ("G seq(rho=0)    letf 1.25x", "seq", "letf", 1.25),
    ("H seq(rho=0)    letf 1.50x", "seq", "letf", 1.5),
    ("I seq(rho=1)    letf 1.25x", "seq", "letf", 1.25),
    ("J all-taxable   margin 1.25x", "tax", "margin", 1.25),
    ("K all-taxable   margin 1.50x", "tax", "margin", 1.5),
]


def rho_of(name):
    return 1.0 if "(rho=1)" in name else 0.0


def main():
    _load()
    print("Study ACC - account structure for the OOS-validated IBS leg (one look, N 833 -> 834)")
    print(f"leg: book.ibs_days (top-3 EQ18, IBS<0.2, open d+1 -> open d+2), {IBS_BPS:.0f}bp/side; "
          f"night/noise OFF")
    print(f"3x proxies for {DF['proxy'].notna().mean()*100:.0f}% of legs; no-proxy names express 1x. "
          f"margin {MARGIN_FIN*100:.1f}%/yr, callable, floor ${MARGIN_FLOOR:.0f}; tax {TAX*100:.0f}% "
          f"(taxable only); deposits ${DEP:.0f}/21 sessions to the Roth.")
    print("Judge window 2016-02..2020-12 (IBS signals start 2017-02 after the 12-1 momentum warmup).")
    print("Stress windows tested: ex-2020 (2017-19) and the 2022 bear; in-sample 2021-26. Any arm")
    print("whose strategy maxDD breaches -25% in ANY window, or liquidates, is rejected.\n")

    gate = {}   # (name, size) -> worst strategy maxDD over windows, total liquidations
    for lab, (lo, hi) in WINDOWS:
        days = IDX[(IDX >= lo) & (IDX <= hi)]
        print("=" * 118)
        print(f"{lab}   {days[0]:%Y-%m-%d}..{days[-1]:%Y-%m-%d}  ({len(days)} sessions)")
        print("=" * 118)
        print(f"  {'structure':<28} {'size':>7} {'IRR%':>6} {'$/yr':>8} {'end$':>10} {'mddAcct':>8} "
              f"{'mddTW':>7} {'effx':>5} {'liq':>3}  flag")
        for size in SIZES:
            for name, acct, kind, m in STRUCTURES:
                o = run(days, size, acct, kind, m, rho=rho_of(name))
                ok = (o["mdd_acct"] >= -0.25 and o["mdd_tw"] >= -0.25 and o["liq"] == 0)
                flag = "OK" if ok else ("DD" if o["mdd_tw"] < -0.25 else "liq")
                print(f"  {name:<28} {size:>7.0f} {o['irr']*100:6.1f} {o['dollars']:8.0f} "
                      f"{o['end']:10,.0f} {o['mdd_acct']*100:7.1f}% {o['mdd_tw']*100:6.1f}% "
                      f"{o['effx']:5.2f} {o['liq']:3d}  {flag}")
                g = gate.setdefault((name, size), dict(mdd=0.0, liq=0, effx=[]))
                g["mdd"] = min(g["mdd"], o["mdd_tw"])
                g["liq"] += o["liq"]
                g["effx"].append(o["effx"])
        print()

    print("=" * 118)
    print("DRAWDOWN GATE: worst strategy maxDD across ALL windows (2016-20, ex-2020, 2022 bear,")
    print("in-sample 2021-26); any arm < -25% or with a liquidation is REJECTED. realized exposure = mean.")
    print("=" * 118)
    print(f"  {'structure':<28} {'$2.3k':>9} {'$10k':>9} {'$25k':>9} {'effx':>5}   verdict")
    for name, acct, kind, m in STRUCTURES:
        vals = [gate[(name, s)]["mdd"] for s in SIZES]
        liq = sum(gate[(name, s)]["liq"] for s in SIZES)
        ex = np.mean([np.mean(gate[(name, s)]["effx"]) for s in SIZES])
        ok = min(vals) >= -0.25 and liq == 0
        tail = f" (liq {liq})" if liq else ""
        print(f"  {name:<28} " + " ".join(f"{v*100:8.1f}%" for v in vals)
              + f" {ex:5.2f}   {'PASS' if ok else 'REJECT'}{tail}")
    print()

    # no-deposit, constant-capital comparison (isolates account/tax/leverage from deposits)
    print("=" * 118)
    print("NO-DEPOSIT reference (constant capital, 2016-20; same metrics, no $7.5k/yr)")
    print("=" * 118)
    days = IDX[(IDX >= FULL[0]) & (IDX <= FULL[1])]
    print(f"  {'structure':<28} {'size':>7} {'TW%':>6} {'$/yr':>8} {'end$':>9} {'mddTW':>7} {'effx':>5}")
    for size in SIZES:
        for name, acct, kind, m in STRUCTURES:
            st = size if acct in ("tax", "seq") else 0.0
            sr = size if acct == "roth" else 0.0
            o = simulate(days, st, sr, kind, m, 0.0, 0.0, taxable=(acct != "roth"))
            print(f"  {name:<28} {size:>7.0f} {o['tw']*100:6.1f} {o['dollars']:8.0f} "
                  f"{o['end']:9,.0f} {o['mdd_tw']*100:6.1f}% {o['effx']:5.2f}")
    print()

    # per-year IRR (deposited, all-Roth letf 1.25x vs base) to expose the regime concentration
    print("=" * 118)
    print("PER-YEAR (all-Roth, $7.5k/yr deposited): IRR by calendar year")
    print("=" * 118)
    for label, kind, m in (("base 1x", "base", 1.0), ("letf 1.25x", "letf", 1.25),
                           ("letf 1.5x", "letf", 1.5)):
        cells = []
        for y in range(2017, 2027):
            d = IDX[(IDX >= f"{y}-01-01") & (IDX <= f"{y}-12-31")]
            if len(d) < 20:
                continue
            o = simulate(d, 0.0, 10000.0, kind, m, 0.0, DEP, taxable=False)
            cells.append(f"{y} {o['tw']*100:+6.1f}")
        print(f"  {label:<12} " + "  ".join(cells))

    print("\nCONSTRAINT: account maxDD <= 25% and no liquidation. flag OK = both mddAcct and")
    print("mddTW within 25% and liq 0; DD = strategy (constant-capital) DD breaches; liq = margin call.")


if __name__ == "__main__":
    main()
