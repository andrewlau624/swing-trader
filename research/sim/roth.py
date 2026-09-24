"""Roth IRA: what version of the book can an IRA run, and does it beat ETFs?

    .venv/bin/python -m research.sim.roth

An IRA cannot borrow or short. With Schwab's "limited margin" on the IRA it
CAN reuse unsettled sale proceeds (sell at the open, buy at the close), so the
overnight legs run exactly as in taxable at 1.0x. Without it (plain cash IRA)
the book depends on how Schwab reads a sale on the settlement date:
  lenient: a close buy funded by that morning's sale, sold at the next open
           (= the funding sale's settlement date) is allowed -> same as above
  strict:  it is a good-faith violation -> each dollar works every other
           night, modelled as both overnight legs at half weight (0.25 + 0.25)

The intraday legs cannot short and cannot lever, so in an IRA they run
through 3x ETFs (TQQQ/SQQQ, SOXL/SOXS) on the daytime cash: the night leg's
money is sitting idle from the open sell to the close buy. 3x on 0.5 of
equity = 1.5x of the underlying, the same cap the taxable book uses. Intraday
the 3x ETF moves ~3x its index (it resets at the close, not intraday), so the
underlying noise return x3 is a fair model; extra cost: 1bp/side in
underlying terms for the wider leveraged-ETF spreads (see LEV_ETF_EXTRA_BPS).

Account: $10,000 on 2021-02-01 plus $7,000/yr ($583.33 every 21 sessions).
Taxable comparisons pay 32% on each calendar year's gain on Dec 31, from the
account, with losses carried forward. VTI is not in the research data; it
tracks SPY at ~0.99 correlation, so SPY stands in for it.
"""
from __future__ import annotations

import copy

import numpy as np
import pandas as pd

from . import book as B
from .validate import load_sim

S2 = {"QQQ": 0.5, "SMH": 0.5}
START_EQ, MONTHLY = 10_000.0, 7_000.0 / 12
LEV_ETF_EXTRA_BPS = 0.3        # per side, underlying terms, on top of the 0.5bp noise cost.
                               # TQQQ ~1c on ~$90 (half-spread ~0.2bp underlying), SOXL ~1c on ~$30
                               # (~0.6bp). Sensitivity 0 / 0.6 / 1.0 printed at the end: it matters.


def roth_day(sim, E, d, p: B.Params, *, budget: str | None, conv_w: float, noise_cap: float):
    """One day. Overnight legs via the simulator; intraday legs from the
    daytime cash only. budget: None = no intraday, "night" = the night half's
    cash, "all" = everything not in an IBS position (idle IBS cash earns 0)."""
    pl, info = sim.day_pnl(E, d, p)            # p has noise_on=False, conviction_w=0
    if budget is None:
        return pl, info
    B_ = p.night_w * E if budget == "night" else max(0.0, E - info["ibs_v"])
    x = 0.0
    conv = min(conv_w * E, B_)
    if conv and d in sim.BO.index:
        x += conv * float(sim.BO.at[d])        # TQQQ / SQQQ notional, cost inside BO
    cap = min(noise_cap, 3.0 * (B_ - conv) / E) if E > 0 else 0.0
    for s, share in S2.items():
        z = sim.NZ[s]
        if d in z.index and cap > 0:
            lev = min(float(z.at[d, "lev"]), cap) * share
            x += E * lev * (float(z.at[d, "ret"]) - z.at[d, "trades"] * LEV_ETF_EXTRA_BPS / 1e4)
    info["noise"] += x
    return pl + x, info


def replay(sim, dates, p: B.Params, budget=None, conv_w=0.0, noise_cap=1.5,
           taxable_intraday=False) -> pd.DataFrame:
    """Daily time-weighted return series plus diagnostics."""
    E, rows = 1e5, []
    for d in dates:
        if taxable_intraday:                    # margin account: the simulator's own intraday path
            pl, info = sim.day_pnl(E, d, p)
        else:
            pl, info = roth_day(sim, E, d, p, budget=budget, conv_w=conv_w, noise_cap=noise_cap)
        rows.append((d, pl / E, info["margin"] / E))
        E += pl
    return pd.DataFrame(rows, columns=["date", "r", "margin"]).set_index("date")


def dollars(r: pd.Series, tax: float = 0.0, start=START_EQ, monthly=MONTHLY) -> pd.DataFrame:
    """Deposits every 21 sessions; optional tax on each calendar year's gain."""
    E, dep, carry, rows = start, start, 0.0, []
    y0_E, y0_dep, year = E, dep, r.index[0].year
    for i, (d, x) in enumerate(r.items()):
        if d.year != year:                      # Dec 31: tax the year just finished
            gain = (E - y0_E) - (dep - y0_dep) + carry
            if tax and gain > 0:
                E -= tax * gain; carry = 0.0
            else:
                carry = min(0.0, gain)
            y0_E, y0_dep, year = E, dep, d.year
        if i and i % 21 == 0:
            E += monthly; dep += monthly
        E *= 1 + (x if np.isfinite(x) else 0.0)
        rows.append((d, E, dep))
    df = pd.DataFrame(rows, columns=["date", "E", "dep"]).set_index("date")
    if tax:                                     # tax the final partial year too (fair to Roth)
        gain = (E - y0_E) - (dep - y0_dep) + carry
        if gain > 0:
            df.iloc[-1, 0] = E - tax * gain
    return df


def line(lab, r, D):
    c1, s1, d1 = B.stats(r[:"2023-12-31"]); c2, s2, d2 = B.stats(r["2024-01-01":]); c, s, dd = B.stats(r)
    yr = (1 + r).groupby(r.index.year).prod() - 1
    wm = ((1 + r).resample("ME").prod() - 1).min()
    return (f"{lab:46s} {c1*100:5.1f}/{s1:4.2f}  {c2*100:5.1f}/{s2:4.2f}  {c*100:5.1f}/{s:4.2f}/{dd*100:4.0f}"
            f"  worst yr {yr.min()*100:5.1f}%  worst mo {wm*100:5.1f}%   ${D.E.iloc[-1]:>9,.0f}")


def main():
    s = load_sim()
    s07 = copy.copy(s); s07.N = B.night_days(max_corr=0.7)
    s07.BO = B.breakout_days()
    days = s07.days
    base = dict(tilt="live", weekend_scale=0.5, noise_on=False, conviction_w=0.0, margin_rate=0.0)
    out = {}
    for cost in ("tier", "tier_hi"):
        V = {}
        V["Roth a: IBS + night, 1.0x (limited margin)"] = replay(
            s07, days, B.Params(night_cost=cost, **base))
        V["Roth a-strict: cash IRA, 0.25 + 0.25"] = replay(
            s07, days, B.Params(night_cost=cost, **{**base, "night_w": 0.25, "ibs_w": 0.25}))
        V["Roth b1: a + intraday 1.5x via 3x ETFs"] = replay(
            s07, days, B.Params(night_cost=cost, **base), budget="night", noise_cap=1.5)
        V["Roth b3: b1 but TQQQ conv 0.25 + noise 0.75x"] = replay(
            s07, days, B.Params(night_cost=cost, **base), budget="night", conv_w=0.25, noise_cap=1.5)
        V["Roth b2: all day cash, noise 1.0x + conv 0.5"] = replay(
            s07, days, B.Params(night_cost=cost, **{**base, "ibs_idle": "cash"}),
            budget="all", conv_w=0.5, noise_cap=1.0)
        V["taxable V7 (margin 2x, as shipped)"] = replay(
            s07, days, B.Params(night_cost=cost, tilt="live", weekend_scale=0.5, noise=S2,
                                noise_cap=1.0, conviction_w=0.5), taxable_intraday=True)
        out[cost] = V
        margin = {k: v.margin.sum() for k, v in V.items() if k.startswith("Roth")}
        assert all(abs(m) < 1e-9 for m in margin.values()), margin     # an IRA never borrows

    spy = s.C["SPY"].pct_change(fill_method=None).reindex(days).fillna(0)
    qqq = s.C["QQQ"].pct_change(fill_method=None).reindex(days).fillna(0)
    etfs = {"SPY (≈ VTI) buy & hold": spy, "QQQ buy & hold": qqq}

    dep = dollars(spy).dep.iloc[-1]
    print(f"$10k on {days[0]:%Y-%m-%d} + $583/mo; deposited ${dep:,.0f} by {days[-1]:%Y-%m-%d}\n")
    for cost in ("tier", "tier_hi"):
        print(f"--- night costs: {cost}        2021-23     2024-26     full CAGR/Sharpe/maxDD   (tax-free)")
        for k, v in out[cost].items():
            print(line(k, v.r, dollars(v.r)))
        for k, r in etfs.items():
            print(line(k, r, dollars(r)))
        print()

    print("--- calendar years (tier costs)")
    cols = {**{k: v.r for k, v in out["tier"].items()}, **etfs}
    print(f"{'':46s}" + "".join(f"{y:>8d}" for y in range(2021, 2027)))
    for k, r in cols.items():
        yr = (1 + r).groupby(r.index.year).prod() - 1
        print(f"{k:46s}" + "".join(f"{yr.get(y, np.nan)*100:7.1f}%" for y in range(2021, 2027)))

    print("\n--- episodes (tier costs), % over the window")
    eps = {"2022 bear": ("2022-01-03", "2022-10-12"), "Aug 2024 unwind": ("2024-07-16", "2024-08-05"),
           "Apr 2025 tariffs": ("2025-02-19", "2025-04-08")}
    for k, r in cols.items():
        print(f"{k:46s}" + "".join(f"  {e} {((1 + r[a:b]).prod() - 1)*100:6.1f}%" for e, (a, b) in eps.items()))

    print("\n--- the Roth's tax benefit: same deposits, taxable at 32% short-term vs Roth")
    for k in ("Roth a: IBS + night, 1.0x (limited margin)", "Roth b1: a + intraday 1.5x via 3x ETFs", "taxable V7 (margin 2x, as shipped)"):
        r = out["tier"][k].r
        print(f"{k:46s} tax-free ${dollars(r).E.iloc[-1]:>9,.0f}   taxed 32% ${dollars(r, tax=0.32).E.iloc[-1]:>9,.0f}")
    for k, r in etfs.items():
        print(f"{k:46s} tax-free ${dollars(r).E.iloc[-1]:>9,.0f}   (buy & hold: no tax until sold)")

    global LEV_ETF_EXTRA_BPS
    keep = LEV_ETF_EXTRA_BPS
    print("\n--- leveraged-ETF cost sensitivity, Roth b1 (full CAGR/Sharpe/maxDD, end $)")
    for x in (0.0, 0.3, 0.6, 1.0):
        LEV_ETF_EXTRA_BPS = x
        for cost in ("tier", "tier_hi"):
            r = replay(s07, days, B.Params(night_cost=cost, **base), budget="night", noise_cap=1.5).r
            c, sh, dd = B.stats(r)
            print(f"  +{x:.1f}bp/side  {cost:8s} {c*100:5.1f}% / {sh:4.2f} / {dd*100:4.0f}%   ${dollars(r).E.iloc[-1]:>9,.0f}")
    LEV_ETF_EXTRA_BPS = keep

    pd.to_pickle({c: {k: v.r for k, v in V.items()} for c, V in out.items()}, B.D.DATA / "roth_variants.pkl")
    crash_check(s)


def crash_check(s):
    """COVID crash: the overnight half (no intraday leg) through the 2020
    rebuild, live guards (corr 0.7, weekend x0.5), bias-corrected as in crash.py."""
    from . import crash as CR
    try:
        d20 = CR.days_2020(0.7)
    except FileNotFoundError:
        print("\n(no panel2020.pkl - crash check skipped)"); return
    n = CR.night_series(d20, weekend=0.5)
    n = n[n.index < "2020-11-05"]; n = n - 9.1e-4 * (n != 0)
    ib = {d: np.mean([r - 2e-4 for _, _, r in legs]) for d, legs in s.I.items()}
    ib = pd.Series(ib).sort_index()
    bil = s.bil
    a, b = "2020-02-19", "2020-03-23"
    days = s.C.index[(s.C.index >= a) & (s.C.index <= b)]
    night = n.reindex(days).fillna(0)
    ibs = ib.reindex(days)
    idle = bil.reindex(days).fillna(0)
    book = 0.5 * night + np.where(ibs.notna(), 0.5 * ibs.fillna(0), 0.5 * idle)
    nz = sum(0.5 * (s.NZ[k].lev.clip(upper=1.5) * s.NZ[k].ret).reindex(days).fillna(0) for k in S2)
    spy = s.spy.reindex(days).fillna(0)
    f = lambda r: ((1 + pd.Series(r)).prod() - 1) * 100
    print(f"\n--- COVID crash {a} -> {b}: SPY {f(spy):.1f}%  | Roth a (IBS + night) {f(book):.1f}%"
          f"  | Roth b1 (+ intraday 1.5x) {f(book + nz):.1f}%")


if __name__ == "__main__":
    main()
