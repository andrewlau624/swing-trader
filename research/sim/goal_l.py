"""Goal L1 / L2: concentration and leverage on the proven legs only (IBS ETF leg + night leg).

    PYTHONPATH=. .venv/bin/python -m research.sim.goal_l          # ~2-4 min, no heavy lock

Pre-registered in research/drafts/round1_prose.md (db80f87, N 788 -> 791) before any outcome:
  B0   ibs 0.5 / night 0.5 (live today, 1.0x overnight)
  L1   one 1.0x budget: the only leg with a signal gets 1.0 of equity; both -> 0.5 / 0.5
  L2a  both legs x1.5 (0.75 / 0.75), L2b x2.0 (1.0 / 1.0); taxable only; capped at half-Kelly
       (f* = mu / sigma^2 of the 1.0x book on the 2016-20 holdout); margin only while equity >= $2,000;
       hard stop: equity 15% below its running peak -> B0 until a new peak.
Costs: night tier_hi (2020 rebuild: flat 10bp/side + 9.1bp bias charge), IBS 3bp/side, margin 12.5%/yr on the
overnight debit, idle cash earns BIL. Tax 30% on each year's net gain (loss carry-forward), paid Dec 31.
Noise / conviction legs are off (not proven on a holdout): this is the two-leg book only.

Two engines, the same rules:
  * dollar replay on the shipped simulator (load_sim(raw_price=True), whole shares), 2021-26, $2.3k / $10k / $25k;
  * a returns engine on unit-leg daily returns (fractional) for the 2016-20 holdout and the 3-yr block bootstrap.
"""
from __future__ import annotations

import copy
import pickle

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import crash as CR
from . import growth as G
from . import rawprice as RP
from .validate import load_sim

RATE = 0.125            # Schwab debit rate assumed for < $25k balances (~12-13%; not in SCHWAB.md)
TAX = 0.30
IBS_BPS = 3.0
FLOOR = 2000.0          # Reg T: no margin below $2,000 equity
STOP = 0.15             # leverage off at -15% from the running peak, back on at a new peak
SIZES = (2300.0, 10000.0, 25000.0)
COVID = ("2020-02-19", "2020-03-23")
HO = ("2016-02-01", "2020-12-31")
VARIANTS = {"B0": ("base", 1.0), "L1": ("conc", 1.0), "L2a 1.5x": ("lev", 1.5), "L2b 2.0x": ("lev", 2.0)}


# ------------------------------------------------------------------ rules
class Rule:
    """Per-day weights for one variant; the same object drives both engines."""

    def __init__(self, kind, L, cap=np.inf):
        self.kind, self.L = kind, min(L, cap)
        self.peak, self.stopped = 0.0, False

    def weights(self, E, fi, fn):
        if self.kind == "conc":
            if fi and not fn:
                return 1.0, 0.0
            if fn and not fi:
                return 0.0, 1.0
            return 0.5, 0.5
        if self.kind in ("lev", "levi"):
            self.peak = max(self.peak, E)
            if self.stopped and E >= self.peak:
                self.stopped = False
            if E < (1 - STOP) * self.peak:
                self.stopped = True
            if E >= FLOOR and not self.stopped:
                return 0.5 * self.L, (0.5 if self.kind == "levi" else 0.5 * self.L)
        return 0.5, 0.5


class Tax:
    def __init__(self):
        self.carry, self.y0 = 0.0, None

    def year_end(self, E):
        """Called on the last session of a year with equity E; returns the tax paid."""
        gain = E - self.y0
        net = gain - self.carry
        if net > 0:
            self.carry = 0.0
            return TAX * net
        self.carry = -net
        return 0.0


# ------------------------------------------------------------------ dollar replay (shipped simulator)
def base_params(cost="tier_hi"):
    return B.Params(**{**G.V7, "night_cost": cost, "ibs_cost_bps": IBS_BPS, "noise_on": False,
                       "conviction_w": 0.0, "ibs_idle": "cash", "margin_rate": RATE, "whole": True})


def replay(s, rule, start, cost="tier_hi"):
    p0 = base_params(cost)
    E, rows, tx = start, [], Tax()
    days = s.days
    for i, d in enumerate(days):
        if tx.y0 is None:
            tx.y0 = E
        fi, fn = bool(s.I.get(d)), s.N.get(d) is not None
        wi, wn = rule.weights(E, fi, fn)
        p = copy.copy(p0); p.ibs_w, p.night_w = wi, wn
        pl, info = s.day_pnl(E, d, p)
        cash = E - info["night_v"] - info["ibs_v"]
        if cash > 0:
            pl += cash * float(np.nan_to_num(s.bil.get(d, 0.0)))
        gross = (info["night_v"] + info["ibs_v"]) / E if E else 0.0
        r = pl / E
        E += pl
        if i == len(days) - 1 or days[i + 1].year != d.year:
            t = tx.year_end(E); E -= t; r = (E - (E + t - pl)) / (E + t - pl); tx.y0 = E
        rows.append((d, E, r, gross))
    return pd.DataFrame(rows, columns=["date", "E", "r", "gross"]).set_index("date")


# ------------------------------------------------------------------ unit legs (returns engine)
def night2020_used(d20, cap=0.10):
    """program_books.night2020 (unit leg return), plus the fraction of the leg actually deployed."""
    o, u = {}, {}
    for d in sorted(d20):
        ret, vol20, day_ret, n_raw, gap = d20[d]
        keep = np.nan_to_num(vol20) >= 0.6
        if not keep.any():
            o[d] = 0.0; u[d] = 0.0; continue
        r, v, dr = ret[keep], vol20[keep], day_ret[keep]
        per = min(1 / len(r), cap) * min(1.0, 30 / max(n_raw, 1))
        x = per * sg.night_tilt(v, dr) * (0.5 if gap > 1 else 1.0)
        val = float((x * (np.nan_to_num(r) - 2 * CR.COST / 1e4)).sum())
        o[d] = val - 9.1e-4 * (val != 0)
        u[d] = float(x.sum())
    return pd.Series(o), pd.Series(u)


def unit_legs(s, cost="tier_hi"):
    """Daily frame 2016-02 .. 2026-09: ri (IBS unit return), fi, rn (night unit), un (night deployed), fn, bil."""
    ix = s.C.index[(s.C.index >= HO[0]) & (s.C.index <= s.days[-1])]
    ri = {d: float(np.mean([r for _, _, r in lst])) - 2 * IBS_BPS / 1e4 for d, lst in s.I.items() if lst}
    rp = pickle.load(open(RP.CACHE, "rb"))
    n20, u20 = night2020_used(rp["y2020"]["raw"][0])
    n20, u20 = n20[n20.index < "2020-11-05"], u20[u20.index < "2020-11-05"]
    if not isinstance(cost, str):          # the 2020 rebuild charges a flat CR.COST per side: swap it
        n20 = n20 + 2 * (CR.COST - cost) / 1e4 * u20
    p = base_params(cost); p.ibs_w, p.night_w, p.whole = 0.0, 1.0, False
    rn, un = dict(n20), dict(u20)
    for d in s.days:
        if s.N.get(d) is None:
            continue
        pl, info = s.day_pnl(1e6, d, p)
        rn[d], un[d] = info["night"] / 1e6, info["night_v"] / 1e6
    f = pd.DataFrame(index=ix)
    f["ri"] = pd.Series(ri).reindex(ix)
    f["fi"] = f.ri.notna(); f["ri"] = f.ri.fillna(0.0)
    f["rn"] = pd.Series(rn).reindex(ix)
    f["fn"] = f.rn.notna() & (pd.Series(un).reindex(ix).fillna(0) > 0)
    f["rn"] = f.rn.fillna(0.0); f["un"] = pd.Series(un).reindex(ix).fillna(0.0)
    f["bil"] = s.bil.reindex(ix).fillna(0.0)
    f["yend"] = [i == len(ix) - 1 or ix[i + 1].year != d.year for i, d in enumerate(ix)]
    return f


def run_returns(f, rule, start, taxed=True):
    E, out, tx = start, [], Tax()
    for d, ri, fi, rn, un, fn, bl, ye in zip(f.index, f.ri.values, f.fi.values, f.rn.values, f.un.values,
                                             f.fn.values, f.bil.values, f.yend.values):
        if tx.y0 is None:
            tx.y0 = E
        wi, wn = rule.weights(E, fi, fn)
        expo = wi * fi + wn * un * fn
        r = wi * ri * fi + wn * rn * fn
        cash = 1 - expo
        r += cash * bl if cash > 0 else cash * RATE / 252
        E0 = E; E *= 1 + r
        if taxed and ye:
            E -= tx.year_end(E); tx.y0 = E
        out.append((d, E, E / E0 - 1, expo))
    return pd.DataFrame(out, columns=["date", "E", "r", "gross"]).set_index("date")


def boot(f, kind, L, cap, start, n=2000, yrs=3, block=21, seed=7, eh=True):
    """3-yr 21-day block bootstrap of the unit legs; rules and tax applied on each path.
    Returns P(min equity < 50% of start), P(min equity < $2,000), median CAGR."""
    rng = np.random.default_rng(seed)
    a = f[["ri", "fi", "rn", "un", "fn", "bil"]].to_numpy(float)
    if eh:
        a = a.copy()
        a[:, 0] -= 0.5 * a[a[:, 1] > 0, 0].mean() * a[:, 1]
        a[:, 2] -= 0.5 * a[a[:, 4] > 0, 2].mean() * a[:, 4]
    T = 252 * yrs
    nb = T // block + 1
    idx = (rng.integers(0, len(a) - block, (n, nb))[:, :, None] + np.arange(block)).reshape(n, -1)[:, :T]
    E = np.full(n, start); peak = E.copy(); stopped = np.zeros(n, bool)
    y0 = E.copy(); carry = np.zeros(n); mn = E.copy()
    Lc = min(L, cap)
    for t in range(T):
        x = a[idx[:, t]]
        ri, fi, rn, un, fn, bl = x.T
        if kind == "conc":
            wi = np.where((fi > 0) & (fn == 0), 1.0, np.where((fn > 0) & (fi == 0), 0.0, 0.5))
            wn = np.where((fn > 0) & (fi == 0), 1.0, np.where((fi > 0) & (fn == 0), 0.0, 0.5))
        elif kind in ("lev", "levi"):
            peak = np.maximum(peak, E)
            stopped = np.where(stopped & (E >= peak), False, stopped)
            stopped |= E < (1 - STOP) * peak
            on = (E >= FLOOR) & ~stopped
            wi = np.where(on, 0.5 * Lc, 0.5)
            wn = wi if kind == "lev" else np.full(n, 0.5)
        else:
            wi = wn = np.full(n, 0.5)
        expo = wi * fi + wn * un * fn
        r = wi * ri * fi + wn * rn * fn
        cash = 1 - expo
        r += np.where(cash > 0, cash * bl, cash * RATE / 252)
        E = E * (1 + r)
        if (t + 1) % 252 == 0:
            net = (E - y0) - carry
            E = E - np.where(net > 0, TAX * net, 0.0)
            carry = np.where(net > 0, 0.0, -net); y0 = E.copy()
        mn = np.minimum(mn, E)
    return (mn < 0.5 * start).mean(), (mn < FLOOR).mean(), np.median((E / start) ** (1 / yrs) - 1)


# ------------------------------------------------------------------ stats
def st(r):
    c, _, dd = B.stats(r)
    wm = G.monthly_worst(r)
    return c, dd, wm


def kelly(r):
    mu, var = r.mean(), r.var()
    return mu / var, (mu - RATE / 252) / var


def main():
    s = load_sim(raw_price=True)
    f = unit_legs(s)
    ho = f[HO[0]:HO[1]]
    # -------- Kelly from the holdout (1.0x book = B0 pre-tax, no debit)
    b0h = run_returns(ho, Rule("base", 1.0), 1e4, taxed=False).r
    fk, fk_net = kelly(b0h)
    ibs_u = ho.ri * ho.fi + (~ho.fi) * ho.bil
    n20 = f["2020-01-01":"2020-11-04"]
    print(f"Holdout 2016-20 1.0x book: mu {b0h.mean()*1e4:.2f}bp/d sigma {b0h.std()*100:.2f}%/d  "
          f"f* = mu/s^2 = {fk:.1f}x  (net of 12.5% borrow {fk_net:.1f}x)  half-Kelly {fk/2:.1f}x")
    ki, _ = kelly(ibs_u); kn, _ = kelly(n20.rn)
    print(f"  IBS unit leg 2016-20 f* {ki:.1f}   night unit leg 2020 f* {kn:.1f}   "
          f"(2021-26: IBS {kelly(f['2021':].ri)[0]:.1f}, night {kelly(f['2021':].rn)[0]:.1f})")
    cap = fk / 2
    # -------- holdout judge (returns engine, $10k and $2.3k)
    print("\nHOLDOUT 2016-20, after interest + 30% tax (returns engine, fractional). L1 is judged on 2020 only.")
    print(f"{'variant':10s} {'start':>7s} {'CAGR':>6s} {'maxDD':>6s} {'wm':>6s} {'COVID':>6s} {'2020':>6s} "
          f"{'mean gross':>10s} {'worst d':>7s}")
    for name, (k, L) in VARIANTS.items():
        for E0 in (2300.0, 1e4):
            df = run_returns(ho, Rule(k, L, cap), E0)
            c, dd, wm = st(df.r)
            cv = (1 + df.r[COVID[0]:COVID[1]]).prod() - 1
            y20 = (1 + df.r["2020"]).prod() - 1
            print(f"{name:10s} {E0:7,.0f} {c*100:6.1f} {dd*100:6.1f} {wm*100:6.1f} {cv*100:6.1f} {y20*100:6.1f} "
                  f"{df.gross.mean():10.2f} {df.r.min()*100:7.1f}")
    # -------- 2021-26 dollar replay
    print("\n2021-26 SHIPPED SIMULATOR (raw pool, whole shares, tier_hi), after interest + 30% tax")
    print(f"{'variant':10s} {'start':>7s} {'21-23':>6s} {'24-26':>6s} {'full':>6s} {'maxDD':>6s} {'wm':>6s} "
          f"{'worst d':>7s} {'gross':>6s} {'end $':>9s}")
    rep = {}
    for name, (k, L) in VARIANTS.items():
        for E0 in SIZES:
            df = replay(s, Rule(k, L, cap), E0)
            rep[(name, E0)] = df
            a, b, (c, dd, wm) = B.stats(df.r[:"2023"])[0], B.stats(df.r["2024":])[0], st(df.r)
            print(f"{name:10s} {E0:7,.0f} {a*100:6.1f} {b*100:6.1f} {c*100:6.1f} {dd*100:6.1f} {wm*100:6.1f} "
                  f"{df.r.min()*100:7.1f} {df.gross.mean():6.2f} {df.E.iloc[-1]:9,.0f}")
    # -------- bootstrap ruin odds
    print("\n3-YR BLOCK BOOTSTRAP (21d blocks, 2000 paths, after interest + tax): P(min E < 50% start) / "
          "P(min E < $2,000) / median CAGR")
    for pool, ff in (("2016-26", f), ("2020-26", f["2020":])):
        for eh in (True, False):
            print(f"  pool {pool}, {'edge-halves' if eh else 'as history'}")
            for name, (k, L) in VARIANTS.items():
                cells = []
                for E0 in SIZES:
                    p50, p2k, med = boot(ff, k, L, cap, E0, eh=eh)
                    cells.append(f"${E0/1e3:4.1f}k {p50*100:5.1f}% {p2k*100:5.1f}% {med*100:5.1f}%")
                print(f"    {name:10s} " + "   ".join(cells))
    # -------- stress: where leverage bites
    print("\nSTRESS (unit night leg = 1.0 of equity in night names; 2x book holds 1.0 night + 1.0 IBS)")
    nn = f[f.fn]
    w = nn.rn.nsmallest(8)
    print("  worst 8 night-leg nights (unit):", ", ".join(f"{d.date()} {v*100:+.1f}%" for d, v in w.items()))
    gap = pd.Series([s._gap(d) if d >= s.days[0] else (2 if d.weekday() == 4 else 1) for d in nn.index], nn.index)
    for lab, m in (("weekday", gap <= 1), ("weekend/holiday", gap > 1)):
        x = nn.rn[m]
        print(f"  {lab:16s} nights n {m.sum():4d} mean {x.mean()*1e4:+6.1f}bp  worst {x.min()*100:+.1f}%  "
              f"sd {x.std()*100:.2f}%")
    for name in ("B0", "L2a 1.5x", "L2b 2.0x"):
        df = run_returns(f["2020-02-01":"2020-04-30"], Rule(*VARIANTS[name], cap), 1e4, taxed=False)
        print(f"  {name:9s} Feb-Apr 2020 path: worst day {df.r.min()*100:+.1f}% ({df.r.idxmin().date()}), "
              f"trough {((df.E / df.E.cummax()).min() - 1)*100:+.1f}%, stop hit "
              f"{'yes' if (df.gross < 1.01).any() and name != 'B0' else 'n/a'}")
    # margin-call arithmetic at Reg T 2x
    print("  Reg T arithmetic: at 2.0x gross, equity = 50% of positions; a 30% house maintenance call comes after "
          "a 28.6% position drop (-57% equity); at 50% house (common on 60%+ vol names) any loss calls.")
    posthoc(s, cap)


POST = {"B0": ("base", 1.0), "L1": ("conc", 1.0), "L2a 1.5x": ("lev", 1.5), "L2b 2.0x": ("lev", 2.0),
        "P-IBS 1.5x": ("levi", 1.5), "P-IBS 2.0x": ("levi", 2.0)}


def posthoc(s, cap):
    """POST-HOC, NOT JUDGED: (a) night cost 3bp/side flat (live measured ~0bp; the repo's low tier),
    (b) leverage on the IBS leg only (ibs 0.75 / 1.0, night stays 0.5)."""
    for cost in ("tier_hi", 3.0):
        f = unit_legs(s, cost)
        ho = f[HO[0]:HO[1]]
        print(f"\nPOST-HOC night cost {cost}: holdout $10k CAGR/maxDD/COVID | 2021-26 full CAGR/maxDD/wm at "
              f"$2.3k $10k $25k | boot EH 2016-26 P(<50%) P(<$2k at $2.3k)")
        for name, (k, L) in POST.items():
            if cost == "tier_hi" and k != "levi":
                continue
            h = run_returns(ho, Rule(k, L, cap), 1e4)
            hc, hd, _ = st(h.r); cv = (1 + h.r[COVID[0]:COVID[1]]).prod() - 1
            cells = []
            for E0 in SIZES:
                c, dd, wm = st(replay(s, Rule(k, L, cap), E0, cost).r)
                cells.append(f"{c*100:5.1f}/{dd*100:4.0f}/{wm*100:4.0f}")
            p50, p2k, _ = boot(f, k, L, cap, 2300.0)
            print(f"  {name:11s} {hc*100:5.1f}/{hd*100:4.0f}/{cv*100:4.0f} | " + "  ".join(cells) +
                  f" | {p50*100:4.1f}% {p2k*100:4.1f}%")


if __name__ == "__main__":
    main()
