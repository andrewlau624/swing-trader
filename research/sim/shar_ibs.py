"""Study SHAR-IBS: the live IBS leg judged on untouched 2003-15 ETF data.

Pre-reg: research/drafts/round1_prose.md ~:3945 (N 838 -> 839), written before any
2003-15 IBS outcome was computed. Rule is frozen = live `signals.ibs_targets` +
`signals.momentum_top`, run as `book.ibs_days`: on session d (>= 260 sessions into the
panel) rank the 18 live ibs_symbols by 12-1 momentum at the last month-end strictly
before d+1, keep top-3; hold each with IBS(d) < 0.2; buy open(d+1), sell open(d+2);
per-name return open(d+2)/open(d+1)-1, equal weight. Judge 2003-01-02..2015-12-31,
one look. Costs `book.cost_bps("tier", raw_open, adv)` per side; tier_hi and 2*tier_hi
stress.

Data: Sharadar SFP funds bars (delisted funds included), 1997-2016-01, via the local
`sharadar` loader (`prices(..., adjust="split", source="funds")`). OHLC stored is
split-adjusted; raw OHLC = stored * closeunadj/close (the loader's adjust="raw"), and
`closeunadj` is the raw close. Dollar volume close*volume is split-invariant, so ADV$
uses it (stated). Sessions = the union of the 18 funds bars' dates (all 18 are US-listed,
so this is the NYSE/Nasdaq session set; stated, not a broker day). Momentum and IBS use
the split-adjusted close/high/low (IBS is split-invariant; raw close would corrupt the
252-session momentum ratio). The trade return uses the SPLIT-ADJUSTED open, open(d+2)/
open(d+1)-1, so it is split-invariant; raw open feeds only the cost tier / price / ADV.
(A raw-open ratio was wrong: on a split ex-date at d+2, raw_open(d+1) ~ k*raw_open(d+2),
giving a spurious -67%. The split-adjusted ratio fixes it; do not drop the rows.)

Report-only beyond the pass bar: 2000-02, 2008-09, per-year, effective universe size,
hit rate, ex-top-5, placebo (IBS lagged/led one session; random-name top-3), DSR at N 839.

Run: PYTHONPATH=. .venv/bin/python -m research.sim.shar_ibs
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd
from scipy.stats import kurtosis, norm, skew

from sharadar import prices
from swingtrader.daily import signals as sg

from . import book as B

OUT = pathlib.Path(__file__).with_name("shar_ibs_out.txt")
EQ18 = ["SPY", "QQQ", "IWM", "DIA", "MDY", "XLK", "XLF", "XLE", "XLV", "XLI",
        "XLY", "XLP", "XLU", "XLB", "SMH", "XBI", "EEM", "EFA"]
N_PROG = 839
JUDGE = ("2003-01-02", "2015-12-31")
HALVES = [("2003-09", "2003", "2009"), ("2010-15", "2010", "2015")]
PANEL_START, PANEL_END = "1997-01-01", "2016-01-31"
WARM = 260


def load_panel():
    """date x ticker panels; split-adj OHLC (signals/returns), raw open (cost tier/ADV)."""
    px = prices(EQ18, PANEL_START, PANEL_END, adjust="split", source="funds")
    px = px[px["close"] > 0].copy()
    px["date"] = pd.DatetimeIndex(pd.to_datetime(px["date"]))
    f = px["closeunadj"] / px["close"]
    px["raw_open"] = px["open"] * f
    px["dv"] = px["close"] * px["volume"]              # split-invariant dollar volume

    def piv(col):
        return px.pivot(index="date", columns="ticker", values=col).reindex(columns=EQ18)

    O = piv("open")
    C = piv("close")
    H = piv("high")
    L = piv("low")
    RO = piv("raw_open")
    DV = piv("dv")
    ADV = DV.rolling(20, min_periods=10).mean()          # known at d, applied at entry d+1
    return O, C, H, L, RO, ADV


def present_count(C):
    """effective universe per year: mean # of the 18 ETFs with a close bar."""
    return C.notna().sum(axis=1).groupby(C.index.year).mean()


def build_legs(O, C, H, L, RO, ADV, ibs_shift: int = 0, random_names: bool = False,
               rng: np.random.default_rng | None = None, d_lo=None, d_hi=None):
    """signal days d -> (names, rets, raw_open_entry, adv_at_d). Return is
    split-invariant: open(d+2)/open(d+1)-1 on the SPLIT-ADJUSTED open (raw open only
    feeds the cost tier, as registered). ibs_shift != 0 breaks the signal alignment
    (placebo); random_names replaces the momentum top-3 (placebo); d_lo/d_hi bound
    the emitted signal days (placebo speed)."""
    days = list(C.index)
    out, mom_cache = {}, {}
    for j in range(WARM, len(days) - 2):
        d, today = days[j], days[j + 1]
        if d_lo is not None and d < pd.Timestamp(d_lo):
            continue
        if d_hi is not None and d > pd.Timestamp(d_hi):
            continue
        m = today.to_period("M")
        if random_names:
            present = [s for s in EQ18 if np.isfinite(C.at[d, s])]
            uni = (list(rng.choice(present, size=min(3, len(present)), replace=False))
                   if present else [])
        else:
            if m not in mom_cache:
                mom_cache[m] = sg.momentum_top(C[C.index < today], today, 3)
            uni = mom_cache[m]
        if not uni:
            continue
        ds = days[j + ibs_shift]
        last = {s: {"high": H.at[ds, s], "low": L.at[ds, s], "close": C.at[ds, s]}
                for s in uni}
        tg = sg.ibs_targets(last, 0.2)
        if not tg:
            continue
        ro1 = RO.loc[days[j + 1]]                     # raw entry price: cost tier only
        oa1, oa2 = O.loc[days[j + 1]], O.loc[days[j + 2]]
        names, rets, advs = [], [], []
        for s in tg:
            a1, a2 = oa1.get(s), oa2.get(s)           # split-adj: split-invariant return
            p1 = ro1.get(s)                           # raw entry price for the cost tier
            if not (np.isfinite(a1) and np.isfinite(a2) and a1 > 0 and p1 > 0):
                continue
            names.append(s)
            rets.append(a2 / a1 - 1.0)
            advs.append(ADV.at[d, s] if s in ADV.columns else np.nan)
        if names:
            out[d] = (names, np.asarray(rets), np.asarray(ro1[names].values),
                      np.asarray(advs))
    return out


def costs(o1, adv, model):
    if model == "2*tier_hi":
        c = B.cost_bps("tier_hi", np.asarray(o1), np.asarray(adv)) * 2.0
    else:
        c = B.cost_bps(model, np.asarray(o1), np.asarray(adv))
    return np.asarray(c, float)


def name_nets(rec, model):
    names, rets, o1, adv = rec
    return rets - 2.0 * costs(o1, adv, model) / 1e4


def net_series(legs, dates, model):
    return np.array([name_nets(legs[d], model).mean() for d in dates])


def dclust_t(x):
    x = np.asarray(x, float)
    if len(x) < 2 or x.std() == 0:
        return np.nan
    return x.mean() / x.std(ddof=1) * np.sqrt(len(x))


def dsr(x, N):
    """Repo convention (research/sim/ibs_voltilt.py:43): per-leg-day SR, V[SR]=1/T."""
    x = np.asarray(x, float)
    T = len(x)
    sr = x.mean() / x.std(ddof=1)
    em = 0.5772156649
    sr0 = np.sqrt(1 / T) * ((1 - em) * norm.ppf(1 - 1 / N) + em * norm.ppf(1 - 1 / (N * np.e)))
    den = np.sqrt(1 - skew(x) * sr + (kurtosis(x, fisher=False) - 1) / 4 * sr ** 2)
    return norm.cdf((sr - sr0) * np.sqrt(T - 1) / den), sr, sr0


def block(x, lab, lines):
    x = np.asarray(x, float)
    n = len(x)
    mu, sd = x.mean(), x.std(ddof=1)
    t = dclust_t(x)
    ex5 = np.sort(x)[:-5].mean() if n > 5 else np.nan
    lines.append(f"  {lab:24s} n={n:4d} mean={mu*1e4:7.2f}bp t={t:5.2f} "
                 f"med={np.median(x)*1e4:7.2f}bp hit={(x>0).mean()*100:3.0f}% "
                 f"ex5={ex5*1e4:7.2f}bp sd={sd*1e4:6.1f}")


def main():
    O, C, H, L, RO, ADV = load_panel()
    days = list(C.index)
    legs = build_legs(O, C, H, L, RO, ADV)
    all_d = sorted(legs)
    jd = [d for d in all_d if JUDGE[0] <= str(d.date()) <= JUDGE[1]]

    lines = ["Study SHAR-IBS (pre-reg round1_prose.md ~:3945; judged rule, N 838 -> 839)",
             f"data: Sharadar SFP funds bars {PANEL_START}..{PANEL_END}, 18 live ibs_symbols",
             f"panel sessions {days[0].date()}..{days[-1].date()} ({len(days)}), "
             f"leg days {len(all_d)}, judged leg days {len(jd)}",
             "costs book.cost_bps per side; returns split-adj open(d+2)/open(d+1)-1 "
             "(split-invariant; raw open feeds the tier); "
             "ADV=prior-20-session mean of split-invariant close*volume",
             "t = day-clustered (one observation per leg day)", ""]

    lines.append("effective universe: mean #of-18 ETFs with a bar, per year")
    pc = present_count(C)
    for y in range(2000, 2016):
        lines.append(f"  {y}: {pc.get(y, float('nan')):4.1f}  leg days {sum(d.year == y for d in all_d)}")
    lines.append("")

    x = net_series(legs, jd, "tier")
    xhi = net_series(legs, jd, "tier_hi")
    x2 = net_series(legs, jd, "2*tier_hi")

    lines.append("=== JUDGE 2003-01-02..2015-12-31, at tier (pass bar) ===")
    block(x, "net tier", lines)
    gx = np.array([legs[d][1].mean() for d in jd])
    block(gx, "gross (0 cost)", lines)
    lines.append("  PASS BAR:")
    t = dclust_t(x)
    lines.append(f"   (1) mean>0 & t>=2.0 : mean={x.mean()*1e4:.2f}bp t={t:.2f} "
                 f"-> {'PASS' if (x.mean() > 0 and t >= 2.0) else 'FAIL'}")
    h1 = net_series(legs, [d for d in jd if d.year <= 2009], "tier")
    h2 = net_series(legs, [d for d in jd if d.year >= 2010], "tier")
    lines.append(f"   (2) both halves >0  : 2003-09 {h1.mean()*1e4:+.2f}bp (t {dclust_t(h1):.2f}) "
                 f"/ 2010-15 {h2.mean()*1e4:+.2f}bp (t {dclust_t(h2):.2f}) "
                 f"-> {'PASS' if (h1.mean() > 0 and h2.mean() > 0) else 'FAIL'}")
    pn = np.concatenate([name_nets(legs[d], "tier") for d in jd])
    lines.append(f"   (3) median per-trade : {np.median(pn)*1e4:+.2f}bp "
                 f"-> {'PASS' if np.median(pn) > 0 else 'FAIL'}")
    ex5 = np.sort(x)[:-5].mean()
    lines.append(f"   (4) ex-best-5 leg days>0: {ex5*1e4:+.2f}bp "
                 f"-> {'PASS' if ex5 > 0 else 'FAIL'}")
    spy = (RO["SPY"].shift(-2) / RO["SPY"].shift(-1) - 1.0).reindex(jd).values
    ok = np.isfinite(spy) & np.isfinite(x)
    beta = np.cov(x[ok], spy[ok], ddof=1)[0, 1] / np.var(spy[ok], ddof=1)
    alpha = x[ok].mean() - beta * spy[ok].mean()
    resid = x[ok] - alpha - beta * spy[ok]
    tres = alpha / (resid.std(ddof=2) / np.sqrt(ok.sum()))
    lines.append(f"   (5) beta-adj to SPY  : beta={beta:+.3f} resid mean={alpha*1e4:+.2f}bp "
                 f"t={tres:.2f} -> {'PASS' if alpha > 0 else 'FAIL'}")
    lines.append("")

    lines.append("=== cost shock (judged window) ===")
    block(x, "tier (judged)", lines)
    block(xhi, "tier_hi", lines)
    block(x2, "2*tier_hi", lines)
    lines.append("")

    lines.append("=== subperiods / per-year (tier) ===")
    for lab, a, b in HALVES:
        block(net_series(legs, [d for d in jd if a <= str(d.year) <= b], "tier"), lab, lines)
    for lab, a, b in [("2000-02 (report)", "2000", "2002"),
                      ("2008-09 (report)", "2008", "2009")]:
        block(net_series(legs, [d for d in all_d if a <= str(d.year) <= b], "tier"), lab, lines)
    for y in range(2000, 2016):
        yy = [d for d in all_d if d.year == y]
        if len(yy) >= 10:
            block(net_series(legs, yy, "tier"), str(y), lines)
    lines.append("")

    q, sr, sr0 = dsr(x, N_PROG)
    lines.append("=== DSR (program N=839, repo V[SR]=1/T convention) ===")
    lines.append(f"  leg days T={len(x)} SR/day={sr:.4f} SR0={sr0:.4f} DSR={q:.3f}")
    lines.append("")

    lines.append("=== placebo (judged window, tier) ===")
    for sh, lab in [(-1, "IBS lagged 1 session"), (1, "IBS led 1 session (lookahead)")]:
        pl = build_legs(O, C, H, L, RO, ADV, ibs_shift=sh, d_lo=JUDGE[0], d_hi=JUDGE[1])
        keep = [d for d in jd if d in pl]
        block(net_series(pl, keep, "tier"), lab, lines)
    draws = []
    for k in range(100):
        rl = build_legs(O, C, H, L, RO, ADV, random_names=True,
                        rng=np.random.default_rng(1000 + k), d_lo=JUDGE[0], d_hi=JUDGE[1])
        if len(rl) >= 100:
            draws.append(net_series(rl, sorted(rl), "tier").mean())
    draws = np.array(draws)
    pct = (draws < x.mean()).mean() * 100
    lines.append(f"  {'random-name top-3 x200':24s} n_draws={len(draws)} "
                 f"mean={draws.mean()*1e4:6.2f}bp sd={draws.std()*1e4:5.1f} "
                 f"actual={x.mean()*1e4:6.2f}bp pct={pct:4.0f}%")
    lines.append("")

    verdict = "PASS"
    if x.mean() <= 0 or t < 1:
        verdict = "FAIL"
    elif not (x.mean() > 0 and t >= 2.0 and h1.mean() > 0 and h2.mean() > 0
              and np.median(pn) > 0 and ex5 > 0 and alpha > 0):
        verdict = "WEAK"
    lines.append(f"VERDICT: {verdict}")

    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
