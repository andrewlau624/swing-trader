"""Round 13: the untested "use the day" ideas -- Studies Z, AA, AB, AD (AC is a feasibility note).

    PYTHONPATH=. .venv/bin/python -m research.sim.day_ideas [z|aa|ab|ad ...]

Stamp: research/drafts/round1_prose.md, "Round 13" (commit b6552d4). Book = Study Y B2 (scale plan,
noise as MNQ 60/40) at constant equity, CENTRAL truth, from scale_book.py's legs.
Z  SPX put-write overlay (Cboe PUT / WPUT / CNDR excess over BIL), k = 0.5 E, 60/40.
AA box-spread financing of the overnight debit at 1.3x / 2.0x (report).
AB fade QQQ inside the noise band while the noise rule is flat (theta 0.5 / 1.0).
AD the QQQ noise leg as an intraday overlay on SPY held (report).
"""
from __future__ import annotations

import sys
import time

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import data as D
from .index_mechanics import nw_t
from .night_filings import FULL, PER, ROOT
from .scale_book import (BRACKETS, H, SIZES, after_tax, etf_imp, ibs_leg, idle, night_leg,
                         night_table, noise_leg)
from .validate import load_sim

OUT = ROOT / "data/research/program/day_ideas_out.txt"
CBOE = ROOT / "data/research/program/cboe"
HOLD = ("2016-20", "2016-01-01", "2020-12-31")
PER3 = (HOLD,) + PER
_fs = None


def log(*a):
    s_ = " ".join(str(x) for x in a)
    print(s_, flush=True)
    _fs.write(s_ + "\n"); _fs.flush()


def ann(r: pd.Series) -> float:
    return float(r.mean() * 252) if len(r) else np.nan


def maxdd(r: pd.Series) -> float:
    w = (1 + r.fillna(0)).cumprod()
    return float((w / w.cummax() - 1).min())


def cagr(r: pd.Series) -> float:
    w = (1 + r.fillna(0)).prod()
    return float(w ** (252 / max(len(r), 1)) - 1)


def sharpe(r: pd.Series) -> float:
    return float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else np.nan


class Ctx:
    """Shared: the Sim, the night table, B2's legs per size (CENTRAL)."""

    def __init__(self):
        self.s = load_sim(raw_price=True)
        self.days = self.s.days[(self.s.days >= FULL[0]) & (self.s.days <= FULL[1])]
        self.yrs = len(self.days) / 252
        self._T, self._legs = None, {}

    def b2(self, E: float) -> dict:
        if E not in self._legs:
            if self._T is None:
                self._T = night_table()
            s, d = self.s, self.days
            nr, _ = night_leg(self._T, E, "CENTRAL", d, s.bil)
            self._legs[E] = {"night": nr, "ibs": ibs_leg(s, E, 1.0, d),
                             "noise": noise_leg(s, E, 1.0, d, {"QQQ": 1.0}, 1.5),
                             "cash": idle(s, d)}
        return dict(self._legs[E])


def at_mod(parts: dict, s1256=True) -> float:
    st, lt = BRACKETS["MOD"]
    return after_tax(parts, st, lt, s1256)


# ------------------------------------------------------------------ Study Z
def cboe(sym: str) -> pd.Series:
    df = pd.read_csv(CBOE / f"{sym}.csv")
    df.columns = [c.strip().upper() for c in df.columns]
    col = "CLOSE" if "CLOSE" in df.columns else df.columns[1]
    x = pd.Series(df[col].astype(float).values, index=pd.to_datetime(df["DATE"]))
    return x[~x.index.duplicated()].sort_index()


def roll_days(ix: pd.DatetimeIndex, weekly: bool) -> pd.DatetimeIndex:
    """The last trading day on or before each roll Friday (3rd Friday monthly, or every Friday)."""
    fr = pd.date_range(ix[0], ix[-1], freq="W-FRI")
    if not weekly:
        fr = fr[(fr.day >= 15) & (fr.day <= 21)]
    pos = ix.searchsorted(fr, side="right") - 1
    return pd.DatetimeIndex(sorted(set(ix[pos[pos >= 0]])))


Z_SPEC = {"Z1 PUT": ("PUT", False, 1), "Z2 WPUT": ("WPUT", True, 1), "Z3 CNDR": ("CNDR", False, 4)}


def study_z(c: Ctx):
    s = c.s
    bil_same = s.C["BIL"].pct_change(fill_method=None)          # same-day, as the index's collateral
    spy = s.C["SPY"].pct_change(fill_method=None)
    log("== Study Z: SPX put-write overlay, k = 0.5 x E notional, excess over BIL, 60/40\n")
    E0 = 100_000
    base = c.b2(E0)
    rb = sum(base.values())
    log(f"B2 CENTRAL at ${E0:,}: pre-tax {rb.sum() / c.yrs:+.1%}/yr, after-tax MOD {at_mod(base):+.1%}, "
        f"max DD {maxdd(rb):.1%}\n")
    for name, (sym, weekly, legs) in Z_SPEC.items():
        lvl = cboe(sym)
        raw = lvl.pct_change().dropna()
        rolls = roll_days(raw.index, weekly)
        log(f"## {name} ({sym}, {'weekly' if weekly else 'monthly'} roll, {legs} leg(s)); "
            f"{len(rolls) / (len(raw) / 252):.1f} rolls/yr")
        # worst 21-day loss at k 0.5 on the raw index (collateral included; 2007-26)
        r07 = raw["2007-01-01":]
        w21 = (0.5 * r07).rolling(21).sum()
        log(f"  overlay worst 21-day (k 0.5, 2007-26): {w21.min():+.1%} of E, ending {w21.idxmin():%Y-%m-%d};"
            f" 2020-02..04 worst {w21['2020-02-01':'2020-04-30'].min():+.1%};"
            f" 2008 worst {w21['2008-01-01':'2008-12-31'].min():+.1%}")
        res = {}
        for cname, cb in (("tier", 2.0), ("tier_hi", 5.0)):
            x = (raw - bil_same.reindex(raw.index)).dropna()
            cost = pd.Series(0.0, index=x.index)
            cost[cost.index.isin(rolls)] = legs * cb / 1e4
            xn = x - cost
            per = {lab: ann(xn[a:b]) for lab, a, b in PER3}
            inc = (0.5 * xn).reindex(c.days).fillna(0)
            hv = {lab: ann(inc[a:b]) for lab, a, b in PER}
            t = nw_t(inc)
            comb = dict(base); comb["noise"] = base["noise"] + inc
            rc = sum(comb.values())
            ddd = maxdd(rc) - maxdd(rb)
            res[cname] = (per, hv, t, ddd, at_mod(comb) - at_mod(base), w21.min())
            log(f"  {cname:8s} standalone net excess %/yr: "
                + ", ".join(f"{k} {v * 100:+.2f}" for k, v in per.items())
                + f" | increment (k .5) {ann(inc) * 100:+.2f}pp/yr, halves "
                + ", ".join(f"{v * 100:+.2f}" for v in hv.values())
                + f", NW t {t:+.2f}, DD {maxdd(rc):.1%} (vs {maxdd(rb):.1%}, {ddd * 100:+.1f}pp),"
                  f" after-tax MOD +{(at_mod(comb) - at_mod(base)) * 100:.2f}pp")
        per, hv, t, ddd, _, w = res["tier_hi"]
        checks = [all(v > 0 for v in per.values()), all(v > 0 for v in hv.values()), t >= 2.0,
                  ddd >= -0.03, w >= -0.15]
        log(f"  PASS checks (tier_hi) 1 standalone>0 all 3 periods {checks[0]}, 2 halves {checks[1]}, "
            f"3 NW t>=2 {checks[2]}, 4a DD {checks[3]}, 4b worst21 >= -15% {checks[4]} -> "
            f"{'SHADOW' if all(checks) else 'DEAD'}")
        # $/yr at sizes (the overlay is size-free; the tax interacts with B2)
        row = []
        for E in (2_300, 25_000, 100_000, 500_000):
            b = c.b2(E); cc = dict(b)
            xn = ((raw - bil_same.reindex(raw.index)).dropna())
            cst = pd.Series(0.0, index=xn.index); cst[cst.index.isin(rolls)] = legs * 5.0 / 1e4
            cc["noise"] = b["noise"] + (0.5 * (xn - cst)).reindex(c.days).fillna(0)
            row.append(f"${E:,}: {(at_mod(cc) - at_mod(b)) * E:+,.0f}")
        log("  after-tax MOD $/yr at tier_hi: " + ", ".join(row) + "\n")
    # Roth sleeve report: PUT vs SPY
    log("## report: PUT as the Roth's destination past capacity (vs SPY / SPX)")
    put = cboe("PUT").pct_change().dropna()
    spx = cboe("SPX").pct_change().dropna()
    for lab, a, b, ref, rn in (("2016-26", "2016-01-04", "2026-09-30", spy, "SPY TR"),
                               ("2007-26", "2007-01-01", "2026-09-30", spx, "SPX price (no dividends, ~-1.8pp)")):
        p_, r_ = put[a:b], ref.dropna()[a:b]
        log(f"  {lab}: PUT CAGR {cagr(p_):+.1%} Sharpe {sharpe(p_):.2f} maxDD {maxdd(p_):.1%} | "
            f"{rn} CAGR {cagr(r_):+.1%} Sharpe {sharpe(r_):.2f} maxDD {maxdd(r_):.1%}")
    log("")


# ----------------------------------------------------------------- Study AA
def study_aa(c: Ctx):
    s = c.s
    log("== Study AA: box-spread financing of the overnight debit (report)\n")
    bil_yld = s.C["BIL"].pct_change(fill_method=None).rolling(21).mean() * 252
    for lab, w in (("1.3x (lever_weight 0.65)", 0.65), ("2.0x (MAX)", 1.0)):
        p = B.Params(night_w=w, ibs_w=w, whole=False, noise_on=False, night_cost="tier")
        E = 1e6
        deb = {}
        for d in c.days:
            _, info = s.day_pnl(E, d, p)
            deb[d] = max(0.0, info["night_v"] + info["ibs_v"] - E) / E
        deb = pd.Series(deb)
        box = (bil_yld.reindex(c.days).clip(lower=0) + 0.003)
        log(f"## {lab}: mean overnight debit {deb.mean():.1%} of equity (days with a debit {np.mean(deb > 0):.0%});"
            f" box rate mean {box.mean():.2%}/yr (2021-23 {box[:'2023'].mean():.2%}, 2024-26 {box['2024':].mean():.2%})")
        for rate in (0.12, 0.10, 0.08):
            sv = (deb * (rate - box) / 252)
            pp = ann(sv)
            hv = ", ".join(f"{lab2} {ann(sv[a:b]) * 100:+.2f}" for lab2, a, b in PER)
            log(f"  margin {rate:.0%}: saves {pp * 100:+.2f}pp/yr ({hv}); $/yr "
                + ", ".join(f"${E_:,}: {pp * E_:+,.0f}" for E_ in (2_300, 25_000, 100_000, 500_000, 1_000_000)))
        log(f"  mean debit in $: " + ", ".join(f"${E_:,}: ${deb.mean() * E_:,.0f}" for E_ in (25_000, 100_000, 500_000))
            + " (XSP box face $10k per 100-wide)")
    log("")


# ----------------------------------------------------------------- Study AB
def fade_days(sym: str, theta: float, lookback: int = 14) -> tuple[pd.DataFrame, list]:
    """Per day: lev (noise vol target) and the list of fade trades' signed gross returns."""
    M = D.minutes(sym)
    C, V = M["close"].values, M["volume"].values
    O = M["open"].values[:, 0]
    days = M["close"].index
    move = np.abs(C / O[:, None] - 1)
    dclose = pd.Series(C[:, -1], index=days)
    prevc = np.r_[np.nan, C[:-1, -1]]
    vwap = np.cumsum(C * V, axis=1) / np.maximum(np.cumsum(V, axis=1), 1)
    rows, trades = [], []
    for i in range(lookback + 1, len(days)):
        sig = sg.noise_sigma(move[i - lookback:i])
        ub, lb = sg.noise_bounds(O[i], prevc[i], sig)
        lev = sg.noise_leverage(dclose.iloc[:i], 0.02, 1e9)
        pos, f, e, g = 0, 0, None, []
        for m in range(sg.NOISE_FIRST, 390, sg.NOISE_STEP):
            p, vw = C[i, m], vwap[i, m]
            new = sg.noise_decide(pos, p, ub[m], lb[m], vw)
            if f != 0 and (new != 0 or (f == 1 and p >= vw) or (f == -1 and p <= vw)):
                g.append(f * (p / e - 1)); f = 0
            pos = new
            if pos == 0 and f == 0 and lb[m] <= p <= ub[m] and abs(p / vw - 1) >= theta * sig[m]:
                f, e = (-1 if p > vw else 1), p
        if f != 0:
            g.append(f * (C[i, 389] / e - 1))
        rows.append((days[i], lev, len(g)))
        trades.append((days[i], g))
    return pd.DataFrame(rows, columns=["date", "lev", "n"]).set_index("date"), trades


def study_ab(c: Ctx):
    log("== Study AB: fade QQQ inside the noise band while the noise rule is flat\n")
    rng = np.random.default_rng(13)
    full = ("2016-01-01", "2026-09-30")
    for theta in (0.5, 1.0):
        info, tr = fade_days("QQQ", theta)
        lev = np.minimum(info.lev, 1.5)
        gs = pd.Series({d: sum(g) for d, g in tr})
        n = info.n
        log(f"## theta {theta}: {n[full[0]:].sum() / (len(n[full[0]:]) / 252):.0f} trades/yr, "
            f"days with a fade {np.mean(n[full[0]:] > 0):.0%}, gross/trade "
            f"{gs[full[0]:].sum() / max(n[full[0]:].sum(), 1) * 1e4:+.2f}bp")
        out = {}
        for cb in (0.5, 1.0):
            inc = (lev * (gs - 2 * n * cb / 1e4))[full[0]:full[1]]
            per = {lab: ann(inc[a:b]) for lab, a, b in PER3}
            t = nw_t(inc)
            out[cb] = (inc, per, t)
            log(f"  {cb}bp/side: increment {ann(inc) * 100:+.2f}pp/yr; "
                + ", ".join(f"{k} {v * 100:+.2f}" for k, v in per.items()) + f"; NW t {t:+.2f}")
        inc, per, t = out[1.0]
        # placebo: same trades, random direction
        flat = [(d, np.array(g)) for d, g in tr if full[0] <= str(d.date()) <= full[1]]
        pl = []
        for _ in range(200):
            x = pd.Series({d: (rng.choice([-1, 1], len(g)) * g).sum() if len(g) else 0.0 for d, g in flat})
            pl.append(float((lev.reindex(x.index) * (x - 2 * n.reindex(x.index) * 1.0 / 1e4)).mean()))
        pct = float(np.mean(np.array(pl) < inc.mean()) * 100)
        E0 = 100_000
        base = c.b2(E0); comb = dict(base)
        imp = (lev * n * etf_imp("QQQ", E0 * lev, 1.0)).reindex(c.days).fillna(0)
        comb["noise"] = base["noise"] + inc.reindex(c.days).fillna(0) - imp
        ddd = maxdd(sum(comb.values())) - maxdd(sum(base.values()))
        checks = [all(v > 0 for v in per.values()), t >= 2.0, pct >= 95, ddd >= -0.02]
        log(f"  placebo pct {pct:.0f}; book DD change at $100k {ddd * 100:+.1f}pp")
        log(f"  PASS checks (1.0bp) 1 all 3 periods>0 {checks[0]}, 2 NW t>=2 {checks[1]}, 3 placebo>=95 "
            f"{checks[2]}, 4 DD {checks[3]} -> {'SHADOW' if all(checks) else 'DEAD'}")
        row = []
        for E in (2_300, 25_000, 100_000, 500_000, 1_000_000):
            b = c.b2(E); cc = dict(b)
            imp = (lev * n * etf_imp("QQQ", E * lev, 1.0)).reindex(c.days).fillna(0)
            cc["noise"] = b["noise"] + inc.reindex(c.days).fillna(0) - imp
            row.append(f"${E:,}: {(at_mod(cc) - at_mod(b)) * E:+,.0f}")
        log("  after-tax MOD $/yr (1.0bp + impact Y 1): " + ", ".join(row) + "\n")


# ----------------------------------------------------------------- Study AD
def study_ad(c: Ctx):
    s = c.s
    log("== Study AD: QQQ noise leg as an intraday overlay on SPY held (report)\n")
    d16 = s.C.index[(s.C.index >= "2016-02-01") & (s.C.index <= "2026-09-30")]
    spy = s.C["SPY"].pct_change(fill_method=None)
    for win, days in (("2016-26", d16), ("2021-26", c.days)):
        yrs = len(days) / 252
        sp = spy.reindex(days).fillna(0)
        g = cagr(sp)
        idx = {k: ((1 + g) ** H * (1 - lt) + lt) ** (1 / H) - 1 for k, (_, lt) in BRACKETS.items()}
        log(f"## window {win}: SPY held {g:+.1%}/yr pre-tax; after-tax (H {H}) MOD {idx['MOD']:+.1%}, "
            f"TOP {idx['TOP']:+.1%}")
        log(f"{'equity':>11s} {'Y':>4s} {'noise pre':>9s} " + " ".join(f"{h:>7s}" for h, _, _ in PER3)
            + f" | {'SPY+QQQn MOD':>12s} {'SPY+MNQn MOD':>12s} {'TOP(MNQ)':>8s} | {'B2 MOD':>7s}")
        for E in SIZES:
            for Y in (1.0, 0.5):
                z = noise_leg(s, E, Y, days, {"QQQ": 1.0}, 1.5)
                pre = z.sum() / yrs
                hv = [ann(z[a:b]) if len(z[a:b]) else np.nan for _, a, b in PER3]
                ats = {}
                for k, (st, lt) in BRACKETS.items():
                    for fut in (False, True):
                        parts = {"noise": z, "zero": 0 * z}
                        ats[(k, fut)] = idx[k] + after_tax(parts, st, lt, fut)
                b2 = ""
                if win == "2021-26" and Y == 1.0:
                    b2 = f"{at_mod(c.b2(E)) * 100:+7.1f}"
                log(f"${E:>10,} {Y:4.1f} {pre * 100:+9.1f} " + " ".join(f"{x * 100:+7.1f}" for x in hv)
                    + f" | {ats[('MOD', False)] * 100:+12.1f} {ats[('MOD', True)] * 100:+12.1f}"
                      f" {ats[('TOP', True)] * 100:+8.1f} | {b2:>7s}")
        log("")


def main():
    global _fs
    which = sys.argv[1:] or ["z", "aa", "ab", "ad"]
    _fs = open(OUT if len(which) == 4 else OUT.with_name(f"day_ideas_{'_'.join(which)}_out.txt"), "w")
    t0 = time.time()
    log("== Round 13 (Studies Z, AA, AB, AD), started", pd.Timestamp.now(), "\n")
    c = Ctx()
    for w in which:
        {"z": study_z, "aa": study_aa, "ab": study_ab, "ad": study_ad}[w](c)
    log(f"done in {time.time() - t0:4.0f} s")


if __name__ == "__main__":
    main()
