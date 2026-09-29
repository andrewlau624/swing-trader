"""Addendum NN: the after-tax growth frontier of the TAXABLE brokerage book.

    # once, under the heavy lock (night_days needs the SIP panel; COVID legs need panel2020):
    PYTHONPATH=. .venv/bin/python -m research.sim.taxable_frontier cache
    # everything else (~10-15 min, no lock):
    PYTHONPATH=. .venv/bin/python -m research.sim.taxable_frontier

Objective: maximum AFTER-TAX growth, P(DD>50% in 5y, edge-halves) <= ~5%.

TAX MODEL (after_tax / mc_tax below; import them):
  every leg short-term (ST, default 35% combined); annual netting with ST/LT character;
  net losses carry forward with character; $3k/yr of net loss deducted against ordinary
  income (refund at the ST rate); tax paid FROM the account on the first session on/after
  Apr 15 of the next year (pay="april") or on Dec 31 (pay="dec31", roth.py style); the final
  partial year is taxed on the last day. Wash sales from the simulated trade list: a loss is
  disallowed pro rata by shares if the same symbol is bought again within 30 calendar days
  after the sale (forward window, as the 1099-B does it for lots already closed), and the
  disallowed loss is added to that next lot's basis (realized when it is sold). Section 1256
  (MNQ/MES/M2K/MYM): 60% LT / 40% ST, no wash sales, marked to market at year end.
  NOTE 475(f) (trader mark-to-market election): all gains/losses become ORDINARY (no $3k cap on
  losses, no carry-forward limit), wash sales no longer apply, but 1256 contracts also lose the
  60/40 rate if they are part of the trading business. Needs trader-tax-status (volume,
  frequency, continuity) and an election by the return due date of the PRIOR year. CPA question.

PRE-REGISTERED VARIANTS (addendum draft, stamped Mon Sep 28 20:54:07 PDT 2026):
  A. leverage schedule: add. 29's seven profiles re-run for daily series + trades (reuse);
     NEW A5 vol-target: g_t = clip(tv / sigma20_{t-1}, 0.5, 1.5), sigma20 = trailing 20-session std
     of the 1.0x cap-0.15 book; tv = median over 2021-23 of 1.3 x sigma20; cap 0.15, conv 0.5.
     Reverse: tv from 2024-26. Placebo: 20 permutations of the same g_t series.
  C. conviction off: A5, moderate (1.3x cap 0.15), aggressive.
  T. tax: T1 dec31 / T2 april + carry + $3k / T3 = T2 + wash sales; rate 25 / 35 / 45%.
  M. 1256: M1 QQQ noise half -> MNQ floor contracts; M2 round-nearest; M3 = M1 + IBS index legs
     (SPY/QQQ/IWM/DIA -> MES/MNQ/M2K/MYM). Parked margin earns BIL, not the book.
     Sizes $10k 30k 60k 100k 200k 300k 1M in 2026 dollars at 2026 contract notional.
"""
from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import growth as G
from .validate import load_sim

SCRATCH = Path(str(__import__("pathlib").Path(__file__).resolve().parents[2]) + "/data/research/program")
CACHE = SCRATCH / "cache_taxable_frontier.pkl"
RES = SCRATCH / "res_taxable_frontier.pkl"

TAX_ST, TAX_LT = 0.35, 0.20
DED = 3000.0

# (overnight gross or "vt", night name cap, conviction, intraday cap or None = max)
PROFILES = {
    "V7 1.0x cap .10": (1.0, 0.10, 0.5, None),
    "1.3x gate cap .10": (1.3, 0.10, 0.5, None),
    "moderate 1.3x cap .15": (1.3, 0.15, 0.5, None),
    "aggressive 1.3x .20 i.6": (1.3, 0.20, 0.5, 0.6),
    "1.5x cap .10": (1.5, 0.10, 0.5, None),
    "1.5x cap .15": (1.5, 0.15, 0.5, None),
    "1.3x cap .10 no conv": (1.3, 0.10, 0.0, None),
    # new (pre-registered)
    "A5 vol-target cap .15": ("vt", 0.15, 0.5, None),
    "A5 vol-target no conv": ("vt", 0.15, 0.0, None),
    "moderate no conv": (1.3, 0.15, 0.0, None),
    "aggressive no conv": (1.3, 0.20, 0.0, 0.6),
}
NEW = ("A5 vol-target cap .15", "A5 vol-target no conv", "moderate no conv", "aggressive no conv")


# ================================================================ cache (heavy)
def build_cache():
    s = load_sim()
    Ns = {c: B.night_days(max_corr=0.7, max_name_pct=c) for c in (0.10, 0.15, 0.20)}
    legs = G.covid_legs(s, caps=(0.10, 0.15, 0.20))
    pickle.dump(dict(Ns=Ns, covid=legs), open(CACHE, "wb"))
    print("cached", CACHE)


def load():
    s = load_sim()
    c = pickle.load(open(CACHE, "rb"))
    s.BO = B.breakout_days()
    return s, c["Ns"], c["covid"]


# ================================================================ replay + trades
def _params(g, cap_unused, conv, noise, cost):
    kw = G.cfg(g, conv, 2, noise)
    return B.Params(**{**G.V7, **kw, "night_cost": cost})


def day_trades(s, E, d, p, nxt):
    """Per-lot P&L ($) of one day, the same arithmetic as book.Sim.day_pnl:
    (sym, buy_date, sell_date, qty, pnl)."""
    out = []
    nd = s.N.get(d)
    if nd is not None:
        w = sg.night_tilt(nd.vol20, nd.day_ret, p.tilt_k)
        c = B.cost_bps(p.night_cost, nd.price, nd.adv)
        per = p.night_w * E * nd.frac * w
        if p.weekend_scale != 1.0 and s._gap(d) > 1:
            per = per * p.weekend_scale
        sh = np.floor(per / nd.price)
        pnl = sh * nd.close * (nd.ret - 2 * c / 1e4)
        for k in np.where(sh > 0)[0]:
            out.append((nd.syms[k], d, nxt(d, 1), sh[k], pnl[k]))
    lst = s.I.get(d, [])
    for sym, o1, r in lst:
        per = p.ibs_w * E / len(lst)
        sh = np.floor(per / o1)
        if sh > 0:
            out.append((sym, nxt(d, 1), nxt(d, 2), sh, sh * o1 * (r - 2 * p.ibs_cost_bps / 1e4)))
    if p.conviction_w and d in s.BO.index:
        out.append(("TQQQ|SQQQ", d, d, E * p.conviction_w, E * p.conviction_w * float(s.BO.at[d])))
    for sym, share in p.noise.items():
        z = s.NZ[sym]
        if d in z.index:
            lev = min(float(z.at[d, "lev"]), p.noise_cap) * share
            if lev > 0:
                out.append((sym, d, d, E * lev, E * lev * float(z.at[d, "ret"])))
    return out


def replay(s, N, g, cap, conv, noise, cost, start=3000.0, monthly=1000.0, trades=True):
    """g: float, or a Series of daily overnight gross. Returns (df like Sim.replay, trades df)."""
    s.N = N
    ix = s.C.index
    pos = {d: i for i, d in enumerate(ix)}
    nxt = lambda d, k: ix[min(pos[d] + k, len(ix) - 1)]
    E, rows, T, pc = start, [], [], {}
    for i, d in enumerate(s.days):
        if i and i % 21 == 0:
            E += monthly
        gd = float(g) if np.isscalar(g) else float(g.get(d, 1.0))
        key = round(gd, 3)
        if key not in pc:
            pc[key] = _params(key, cap, conv, noise, cost)
        p = pc[key]
        pl, info = s.day_pnl(E, d, p)
        if trades:
            for t in day_trades(s, E, d, p, nxt):
                T.append((d,) + t + (E,))
        k = E if E else 1.0
        rows.append((d, E, pl / k, info["night"] / k, info["ibs"] / k, info["noise"] / k,
                     (info["idle"] + info["margin"]) / k))
        E += pl
    df = pd.DataFrame(rows, columns=["date", "E", "r", "r_night", "r_ibs", "r_noise", "r_cash"]).set_index("date")
    tr = pd.DataFrame(T, columns=["book", "sym", "buy", "sell", "qty", "pnl", "E"]) if trades else None
    if tr is not None:
        tr["frac"] = tr.pnl / tr.E
    return df, tr


def vt_schedule(r_unit: pd.Series, fit=("2021-01-01", "2023-12-31"), lo=0.5, hi=1.5, base=1.3):
    """A5: g_t = clip(tv / sigma20_{t-1}, lo, hi); tv from the fit window only."""
    sig = r_unit.rolling(20).std().shift(1)
    tv = float((base * sig[fit[0]:fit[1]]).median())
    g = (tv / sig).clip(lo, hi).fillna(1.0)
    return g, tv


# ================================================================ tax
def _net_year(S, L, r_st, r_lt, ded):
    """S, L: this year's ST / LT net incl. carry-forwards. -> (tax, carry_S, carry_L)."""
    if S >= 0 and L >= 0:
        return r_st * S + r_lt * L, 0.0, 0.0
    if S < 0 < L:
        n = S + L
        if n >= 0:
            return r_lt * n, 0.0, 0.0
        S, L = n, 0.0
    elif L < 0 < S:
        n = S + L
        if n >= 0:
            return r_st * n, 0.0, 0.0
        S, L = 0.0, n
    tot = -(S + L)
    dd = min(ded, tot)
    uS = min(dd, -S)
    return -r_st * dd, S + uS, L + (dd - uS)


class Wash:
    """Wash-sale deferral on a trade list (sym, buy, sell, qty, frac) booked on 'book' dates."""

    def __init__(self, tr: pd.DataFrame, window=30):
        tr = tr.sort_values(["sym", "buy", "book"]).reset_index(drop=True)
        nxt = np.full(len(tr), -1)
        f = np.zeros(len(tr))
        sym, buy, sell, q = tr.sym.values, tr.buy.values, tr.sell.values, tr.qty.values
        for i in range(len(tr) - 1):
            if sym[i + 1] == sym[i]:
                gap = (buy[i + 1] - sell[i]) / np.timedelta64(1, "D")
                if window >= 0 and -1 <= gap <= window:     # same-day re-buy (IBS: sell and buy at the same open) counts
                    nxt[i] = i + 1
                    f[i] = min(1.0, q[i + 1] / q[i]) if q[i] > 0 else 1.0
        tr["nxt"], tr["f"] = nxt, f
        self.tr = tr
        self.by_day = {d: g for d, g in tr.groupby("book")}
        self.adj = {}

    def realize(self, d, E):
        """Yields (sell_year, reported $) for lots booked on d, given equity E."""
        g = self.by_day.get(d)
        if g is None:
            return []
        out = []
        for idx, frac, sell, n, f in zip(g.index, g.frac.values, g.sell.values, g.nxt.values, g.f.values):
            x = frac * E + self.adj.pop(idx, 0.0)
            if x < 0 and n >= 0:
                self.adj[n] = self.adj.get(n, 0.0) + f * x
                x = (1 - f) * x
            out.append((pd.Timestamp(sell).year, x))
        return out


def after_tax(r: pd.Series, rate: float = TAX_ST, lt: float = TAX_LT, trades: pd.DataFrame | None = None,
              r1256: pd.Series | None = None, pay: str = "april", ded: float = DED,
              start: float = 3000.0, monthly: float = 1000.0, wash: bool = True, window: int = 30):
    """After-tax daily time-weighted returns of a book.

    r      : the book's daily return (ALL legs, incl. any 1256 part given in r1256)
    trades : optional trade list with 'book' (date booked), 'sym', 'buy', 'sell', 'qty', 'frac'
             (P&L as a fraction of the day's equity). Used for wash sales; the rest of r
             (BIL, margin interest, edge-halves cut) is ordinary ST income on its day.
    r1256  : part of r that is Section 1256 (60/40, no wash).
    Returns (r_net, info). r_net is the daily return of equity NET of the tax liability
    (unpaid past-year tax + the tax this year's income would owe today): tax is charged in the
    year it is earned, and an April payment is not a drawdown. info["r_account"] is the raw
    account balance (tax leaves in April), info["tax"] tax by year, info["shift"] the wash-sale
    shift of reported vs economic ST income by year."""
    r = r.fillna(0.0)
    f56 = (r1256.reindex(r.index).fillna(0.0) if r1256 is not None else pd.Series(0.0, index=r.index))
    tfrac = (trades.groupby("book").frac.sum().reindex(r.index).fillna(0.0)
             if trades is not None else pd.Series(0.0, index=r.index))
    W = Wash(trades, window if wash else -10) if trades is not None else None
    ST, LT, ECON = {}, {}, {}
    cS = cL = 0.0
    due = []                       # (pay_date, amount)
    E, out, info = start, [], {"tax": {}, "shift": {}}
    net_out, NE_prev = [], start
    years = sorted(set(r.index.year))
    last = r.index[-1]

    def settle(y):
        nonlocal cS, cL
        S = ST.get(y, 0.0) + cS + 0.4 * LT.get(("f", y), 0.0)
        L = LT.get(y, 0.0) + cL + 0.6 * LT.get(("f", y), 0.0)
        tax, cS, cL = _net_year(S, L, rate, lt, ded)
        info["tax"][y] = tax
        return tax

    pay_day = {}
    for y in years[:-1]:
        cand = r.index[(r.index >= pd.Timestamp(f"{y + 1}-04-15"))]
        pay_day[y] = (cand[0] if len(cand) else last) if pay == "april" else r.index[r.index.year == y][-1]
    for i, (d, x) in enumerate(r.items()):
        if i and i % 21 == 0:
            E += monthly
        E0 = E
        pnl = x * E
        y = d.year
        # income
        if W is not None:
            for yy, amt in W.realize(d, E):
                ST[yy] = ST.get(yy, 0.0) + amt
            rest = (x - tfrac.at[d] - f56.at[d]) * E
        else:
            rest = (x - f56.at[d]) * E
        ST[y] = ST.get(y, 0.0) + rest
        LT[("f", y)] = LT.get(("f", y), 0.0) + f56.at[d] * E
        ECON[y] = ECON.get(y, 0.0) + (x - f56.at[d]) * E
        E += pnl
        # year end -> tax due
        if i + 1 < len(r) and r.index[i + 1].year != y:
            due.append((pay_day[y], settle(y)))
        paid = sum(a for pdd, a in due if pdd == d)
        due = [(pdd, a) for pdd, a in due if pdd != d]
        if d == last:
            paid += sum(a for _, a in due) + settle(y)
        E -= paid
        out.append((E - E0) / (E0 if E0 else 1.0))
        # liability: tax owed but unpaid (due list) + what this year's income would owe today
        if d == last:
            liab = 0.0
        else:
            yy_open = y if not (i + 1 < len(r) and r.index[i + 1].year != y) else None
            pend = sum(W.adj.values()) if W is not None else 0.0     # deferred losses sitting in open lots' basis
            if yy_open is not None:
                acc = _net_year(ST.get(y, 0.0) + pend + cS + 0.4 * LT.get(("f", y), 0.0),
                                cL + 0.6 * LT.get(("f", y), 0.0), rate, lt, ded)[0]
            else:
                acc = rate * pend
            liab = sum(a for _, a in due) + acc
        ne_before = NE_prev + (monthly if (i and i % 21 == 0) else 0.0) if i else start
        NE = E - liab
        net_out.append((NE - ne_before) / (ne_before if ne_before else 1.0))
        NE_prev = NE
    for y in years:
        info["shift"][y] = ST.get(y, 0.0) - ECON.get(y, 0.0)   # reported - economic ST income
    info["econ"], info["st"] = ECON, ST
    info["end_E"] = E
    info["r_account"] = pd.Series(out, index=r.index)
    return pd.Series(net_out, index=r.index), info


def mc_tax(r: pd.Series, rate=TAX_ST, lt=TAX_LT, r1256: pd.Series | None = None, start=3000.0,
           monthly=1000.0, n=4000, days=1260, block=21, seed=7, pay_lag=73, ded=DED) -> dict:
    """growth.mc with tax: same bootstrap draws; each path pays tax on each 252-day year's
    net $ gain pay_lag sessions later (April), carry-forwards and $3k deduction per path."""
    rng = np.random.default_rng(seed)
    x = r.fillna(0).values
    x56 = r1256.reindex(r.index).fillna(0).values if r1256 is not None else np.zeros(len(x))
    nb = days // block
    starts = rng.integers(0, len(x) - block, size=(n, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(n, -1)
    R, R56 = x[idx], x56[idx]
    E = np.full(n, start); dep = start
    tw = np.ones(n); peak = np.ones(n); dd = np.zeros(n)
    gS = np.zeros(n); g56 = np.zeros(n); cS = np.zeros(n); cL = np.zeros(n)
    pending = None
    twn = np.ones(n); pkn = np.ones(n); ddn = np.zeros(n); NEb = np.full(n, start)
    net = np.vectorize(lambda S, L: _net_year(S, L, rate, lt, ded), otypes=[float, float, float])
    T = R.shape[1]
    for t in range(T):
        if t and t % 21 == 0:
            E = E + monthly; dep += monthly
        E0 = E.copy()
        gS += (R[:, t] - R56[:, t]) * E; g56 += R56[:, t] * E
        E = E * (1 + R[:, t])
        if (t + 1) % 252 == 0 or t == T - 1:
            tax, cS, cL = net(gS + cS + 0.4 * g56, cL + 0.6 * g56)
            gS[:] = 0; g56[:] = 0
            if t == T - 1:
                E = E - tax - (pending[1] if pending is not None else 0)
                pending = None
            else:
                if pending is not None:          # (never: lag < 252)
                    E = E - pending[1]
                pending = (t + pay_lag, tax)
        if pending is not None and t == pending[0]:
            E = E - pending[1]; pending = None
        tw = tw * (E / E0)
        peak = np.maximum(peak, tw); dd = np.minimum(dd, tw / peak - 1)
        S = gS + cS + 0.4 * g56; L = cL + 0.6 * g56
        liab = np.maximum(0.0, rate * S + lt * L) + (pending[1] if pending is not None else 0.0)
        NE = E - liab
        if t:
            twn = twn * (NE / NEb)
        else:
            twn = NE / start
        NEb = NE + (monthly if (t + 1) % 21 == 0 else 0.0)
        pkn = np.maximum(pkn, twn); ddn = np.minimum(ddn, twn / pkn - 1)
    return dict(p10=np.percentile(E, 10), med=np.median(E), p90=np.percentile(E, 90),
                dd30=(ddn < -0.30).mean(), dd50=(ddn < -0.50).mean(),
                dd30_acct=(dd < -0.30).mean(), dd50_acct=(dd < -0.50).mean(), dep=dep)


# ================================================================ helpers
def st3(r):
    a, b, f = B.stats(r[:"2023-12-31"]), B.stats(r["2024-01-01":]), B.stats(r)
    return a, b, f


def fmt3(r):
    a, b, f = st3(r)
    return f"{a[0]*100:5.1f}/{a[1]:4.2f}  {b[0]*100:5.1f}/{b[1]:4.2f}  {f[0]*100:5.1f}/{f[1]:4.2f}/{f[2]*100:4.0f}"


def nw_t(x: pd.Series, lags=5):
    x = x.dropna().values; x = x - 0; n = len(x); m = x.mean(); e = x - m
    v = e @ e / n
    for L in range(1, lags + 1):
        v += 2 * (1 - L / (lags + 1)) * (e[L:] @ e[:-L]) / n
    return m / np.sqrt(v / n)


def eh_series(df):
    return G.eh(df.rename(columns={}))


def episodes(r):
    tw = (1 + r).cumprod()
    out = {}
    for lab, a, b in (("2022", "2022-01-01", "2022-12-31"), ("Apr25", "2025-04-02", "2025-04-08")):
        x = r[a:b]; t = (1 + x).cumprod()
        out[lab] = (t.iloc[-1] - 1, (t / t.cummax() - 1).min())
    m = (1 + r).groupby([r.index.year, r.index.month]).prod() - 1
    out["worst_day"], out["worst_month"] = r.min(), m.min()
    return out


def covid_series(legs, g_of, cap, conv, noise=None, a="2020-01-02", b="2020-12-31"):
    """growth.covid_book, returning the daily series, with a per-day gross g_of(d, hist)."""
    night, ibs, bil, nz, bo = legs
    days = pd.bdate_range(a, b)
    r = []
    for d in days:
        g = g_of(d, r)
        p = G.cfg(g, conv, 2, noise)
        x = p["night_w"] * float(night[cap].get(d, 0.0))
        iv = ibs.get(d, np.nan)
        x += p["ibs_w"] * (float(iv) if np.isfinite(iv) else float(np.nan_to_num(bil.get(d, 0.0))))
        for sy, share in G.S2.items():
            z = nz[sy]
            if d in z.index:
                x += min(float(z.at[d, "lev"]), p["noise_cap"]) * share * float(z.at[d, "ret"])
        x += p["conviction_w"] * float(bo.get(d, 0.0))
        x -= max(0.0, p["ibs_w"] + p["night_w"] - 1) * 0.12 / 252
        r.append(x)
    return pd.Series(r, index=days)


# ================================================================ 1256 migration
MNQ_N_RATIO = dict(QQQ=(41.0, 2.0), SPY=(10.0, 5.0), IWM=(10.0, 5.0), DIA=(100.0, 0.5))
TICK = dict(QQQ=0.50, SPY=1.25, IWM=0.50, DIA=0.50)          # $ per tick per micro
FUT_COST = {3.0: (1.00, 1), "tier_hi": (1.50, 2)}             # (commission $, ticks) per side
DAY_MARGIN, ON_MARGIN = 0.25 * 0.07, 0.07


def migrate(s, df, prof, cost, E0, rounding="floor", ibs=False, park_mult=1.5):
    """Split the book's daily return into (ST part, 1256 part) for a constant account E0
    in 2026 dollars. Returns (r_total, r_1256, info)."""
    g, cap, conv, nz = prof
    C = s.C
    px26 = {k: float(C[k].dropna().iloc[-1]) for k in MNQ_N_RATIO}
    N = {k: px26[k] * a * m for k, (a, m) in MNQ_N_RATIO.items()}
    comm, ticks = FUT_COST[cost if cost in FUT_COST else "tier_hi"]
    fbps = {k: (comm + ticks * TICK[k]) / N[k] * 1e4 for k in N}
    rnd = np.rint if rounding == "nearest" else np.floor
    idx = df.index
    z = s.NZ["QQQ"].reindex(idx)
    gser = df["g"] if "g" in df else pd.Series(float(g) if np.isscalar(g) else 1.0, index=idx)
    ncap = gser.map(lambda gg: G.cfg(round(float(gg), 3), conv, 2, nz)["noise_cap"])
    tgt = np.minimum(z.lev.fillna(0), ncap) * 0.5                # QQQ half, fraction of E
    q_etf = (tgt * z.ret.fillna(0)).fillna(0)
    gross = z.ret.fillna(0) + z.trades.fillna(0) * 0.5e-4
    k = rnd(tgt * E0 / N["QQQ"])
    q_fut = (k * N["QQQ"] / E0 * (gross - z.trades.fillna(0) * fbps["QQQ"] / 1e4)).fillna(0)
    if rounding == "hybrid":          # POST-HOC: whole contracts + the remainder stays in the ETF
        rem = (tgt - k * N["QQQ"] / E0).clip(lower=0)
        q_etf_keep = (rem * z.ret.fillna(0)).fillna(0)
    else:
        q_etf_keep = pd.Series(0.0, index=idx)
    kmax = float(rnd(ncap.max() * 0.5 * E0 / N["QQQ"]))
    park = kmax * park_mult * DAY_MARGIN * N["QQQ"]
    i_etf = pd.Series(0.0, index=idx); i_fut = pd.Series(0.0, index=idx)
    if ibs:
        on_need = 0.0
        for d in idx:
            lst = s.I.get(d, [])
            gw = float(gser.at[d]) / 2
            need = 0.0
            for sym, o1, rr in lst:
                if sym in N:
                    fr = gw / len(lst)
                    kk = rnd(fr * E0 / N[sym])
                    i_etf.at[d] += fr * (rr - 2 * 1.0 / 1e4)
                    i_fut.at[d] += kk * N[sym] / E0 * (rr - 2 * fbps[sym] / 1e4)
                    need += kk * ON_MARGIN * N[sym]
            on_need = max(on_need, need)
        park += on_need
    pf = min(park / E0, 0.9)
    bil = s.bil.reindex(idx).fillna(0)
    rest = df["r"] - q_etf - i_etf
    rest = rest + q_etf_keep
    r_new = rest - pf * (rest - bil) + q_fut + i_fut
    return r_new, q_fut + i_fut, dict(kmax=kmax, park=park, pf=pf, fbps=fbps["QQQ"],
                                      used=(k > 0).mean(), N=N["QQQ"])


# ================================================================ main
def main():
    s, Ns, covid = load()
    res = pickle.load(open(RES, "rb")) if RES.exists() else {}
    COSTS = (3.0, "tier_hi")

    def run(name, cost, gsched=None):
        key = (name, cost)
        if key in res and gsched is None:
            return res[key]
        g, cap, conv, nz = PROFILES[name]
        gg = gsched if gsched is not None else g
        df, tr = replay(s, Ns[cap], gg, cap, conv, nz, cost)
        if not np.isscalar(gg):
            df["g"] = gg.reindex(df.index).fillna(1.0)
        out = (df, tr)
        if gsched is None:
            res[key] = out
        return out

    # ---- vol-target schedules (fit 2021-23, and the reverse)
    sched = {}
    for cost in COSTS:
        unit, _ = replay(s, Ns[0.15], 1.0, 0.15, 0.5, None, cost, trades=False)
        g1, tv1 = vt_schedule(unit["r"])
        g2, tv2 = vt_schedule(unit["r"], fit=("2024-01-01", "2026-12-31"))
        sched[cost] = (g1, tv1, g2, tv2, unit["r"])
        print(f"vol-target {cost}: tv(2021-23) {tv1*100:.3f}%/day  median g 21-23 {g1[:'2023'].median():.2f} "
              f"24-26 {g1['2024':].median():.2f}  mean {g1.mean():.2f}  | reverse tv {tv2*100:.3f}%")

    for cost in COSTS:
        for name, (g, cap, conv, nz) in PROFILES.items():
            if (name, cost) in res:
                continue
            if g == "vt":
                df, tr = run(name, cost, sched[cost][0]); res[(name, cost)] = (df, tr)
            else:
                run(name, cost)
    pickle.dump(res, open(RES, "wb"))

    # ================= 1. tax-model axis on shipped V7 and moderate, 3bp
    print("\n== 1. tax model (T1 dec31 / T2 april+carry+$3k / T3 T2+wash), $3k + $1k/mo, 3bp and tier_hi")
    print(f"{'':34s}{'cost':>8s} {'model':>14s}   2021-23      2024-26      full CAGR/Sh/DD")
    for cost in COSTS:
        for name in ("V7 1.0x cap .10", "moderate 1.3x cap .15", "aggressive 1.3x .20 i.6"):
            df, tr = res[(name, cost)]
            print(f"{name:34s}{str(cost):>8s} {'pre-tax':>14s}   {fmt3(df['r'])}")
            for lab, kw in (("T1 dec31 35%", dict(pay="dec31", wash=False)),
                            ("T2 april 35%", dict(wash=False)),
                            ("T3 +wash 35%", dict(trades=tr)),
                            ("T3 25%", dict(trades=tr, rate=0.25)),
                            ("T3 45%", dict(trades=tr, rate=0.45))):
                ra, info = after_tax(df["r"], **kw)
                print(f"{'':34s}{'':>8s} {lab:>14s}   {fmt3(ra)}")
            ra, info = after_tax(df["r"], trades=tr)
            sh_, econ = info["shift"], info["econ"]
            print(f"{'':34s} wash-sale shift, reported - economic ST income ($ at the sim's size, % of the year's gain): " +
                  "  ".join(f"{y}: {v:+,.0f} ({v / econ[y] * 100 if econ[y] else 0:+.1f}%)" for y, v in sh_.items()))

    # wash-sale anatomy from the trade list (moderate, 3bp)
    df, tr = res[("moderate 1.3x cap .15", 3.0)]
    W = Wash(tr)
    t = W.tr
    kinds = np.where(t.sym.isin(list(B.EQ18)) & (t.buy != t.sell), "IBS ETF",
                     np.where(t.buy == t.sell, "intraday", "night name"))
    t["kind"] = kinds
    print("\n   trade list (moderate, 3bp): lots, losing lots, share of losing lots re-bought <= 30d")
    for kd, g in t.groupby("kind"):
        los = g[g.pnl < 0]
        print(f"   {kd:12s} lots {len(g):6d}  losers {len(los):6d}  re-bought<=30d {(los.nxt >= 0).mean():5.0%}  "
              f"names {g.sym.nunique():5d}")
    dec = t[(pd.to_datetime(t.sell).dt.month == 12) & (pd.to_datetime(t.sell).dt.day >= 1) & (t.pnl < 0) & (t.nxt >= 0)]
    print(f"   December losing lots re-bought within 30d: {len(dec)} (sum ${dec.pnl.sum():,.0f} at the sim's $ size)")

    # ================= 2. frontier
    print("\n== 2. after-tax frontier (T3 35%): history | EH | 5y MC under EH with tax ($3k+$1k/mo; $10k lump)")
    print(f"{'profile':30s}{'cost':>8s}  pre-tax full    after-tax 21-23 / 24-26 / full  | EH after-tax CAGR/Sh/DD"
          f" | MC med  P30  P50 | $10k med P30 P50 | pre-tax EH MC P30 P50")
    front = {}
    for cost in COSTS:
        for name in PROFILES:
            df, tr = res[(name, cost)]
            ra, _ = after_tax(df["r"], trades=tr)
            e = G.eh(df)
            rea, _ = after_tax(e, trades=tr)
            m = mc_tax(e, start=3000, monthly=1000)
            m10 = mc_tax(e, start=10000, monthly=0)
            m0 = G.mc(e, 3000, 1000)
            a, b, f = st3(ra); pf = B.stats(df["r"]); ef = B.stats(rea)
            front[(name, cost)] = dict(pre=pf, at=(a, b, f), eh=ef, mc=m, mc10=m10, mc0=m0, ra=ra, rea=rea)
            print(f"{name:30s}{str(cost):>8s}  {pf[0]*100:5.1f}/{pf[1]:4.2f}/{pf[2]*100:3.0f}   "
                  f"{a[0]*100:5.1f}/{a[1]:4.2f} {b[0]*100:5.1f}/{b[1]:4.2f} {f[0]*100:5.1f}/{f[1]:4.2f}/{f[2]*100:3.0f} | "
                  f"{ef[0]*100:5.1f}/{ef[1]:4.2f}/{ef[2]*100:3.0f} | ${m['med']:>8,.0f} {m['dd30']:4.0%} {m['dd50']:4.0%} | "
                  f"${m10['med']:>8,.0f} {m10['dd30']:4.0%} {m10['dd50']:4.0%} | {m0['dd30']:4.0%} {m0['dd50']:4.0%} | "
                  f"acct {m['dd30_acct']:4.0%} {m['dd50_acct']:4.0%}")
    pickle.dump(front, open(SCRATCH / "front_taxable_frontier.pkl", "wb"))

    # ================= 3. vol-target tests
    print("\n== 3. A5 vol-target vs fixed moderate (after tax T3 35%)")
    for cost in COSTS:
        g1, tv1, g2, tv2, _ = sched[cost]
        dv, tv_ = res[("A5 vol-target cap .15", cost)]
        dm, tm = res[("moderate 1.3x cap .15", cost)]
        rv, _ = after_tax(dv["r"], trades=tv_); rm, _ = after_tax(dm["r"], trades=tm)
        d = dv["r"] - dm["r"]
        print(f"  {cost}: A5 {fmt3(rv)} | moderate {fmt3(rm)} | pre-tax diff NW t "
              f"21-23 {nw_t(d[:'2023']):+.2f} 24-26 {nw_t(d['2024':]):+.2f}")
        dr, trr = run("A5 vol-target cap .15", cost, g2)
        rr, _ = after_tax(dr["r"], trades=trr)
        print(f"     reverse (tv from 2024-26 {tv2*100:.3f}%): {fmt3(rr)}")
        if cost == 3.0:
            sh = []
            rng = np.random.default_rng(11)
            for k in range(20):
                gp = pd.Series(rng.permutation(g1.values), index=g1.index)
                dp, _ = replay(s, Ns[0.15], gp, 0.15, 0.5, None, cost, trades=False)
                sh.append((B.stats(dp["r"])[1], B.stats(dp["r"][:"2023"])[1], B.stats(dp["r"]["2024":])[1],
                           B.stats(dp["r"])[0]))
            sh = np.array(sh)
            real = B.stats(dv["r"])
            print(f"     placebo (20 shuffles of g_t): real full Sharpe {real[1]:.2f} vs shuffles "
                  f"median {np.median(sh[:, 0]):.2f} max {sh[:, 0].max():.2f}; beats {int((real[1] > sh[:, 0]).sum())}/20; "
                  f"halves beat {int((B.stats(dv['r'][:'2023'])[1] > sh[:, 1]).sum())}/20, "
                  f"{int((B.stats(dv['r']['2024':])[1] > sh[:, 2]).sum())}/20; shuffle CAGR median {np.median(sh[:, 3])*100:.1f}%")

    # ================= 4. crash episodes
    print("\n== 4. crash episodes (pre-tax; COVID rebuilt from 2020 bars, bias-corrected, as growth.py)")
    g1c = None
    for name in ("V7 1.0x cap .10", "1.3x gate cap .10", "moderate 1.3x cap .15", "aggressive 1.3x .20 i.6",
                 "A5 vol-target cap .15", "1.5x cap .15"):
        g, cap, conv, nz = PROFILES[name]
        if g == "vt":
            tv1 = sched[3.0][1]
            unit = covid_series(covid, lambda d, h: 1.0, cap, conv, nz)
            sig = unit.rolling(20).std().shift(1)
            gv = (tv1 / sig).clip(0.5, 1.5).fillna(1.0)
            cr = covid_series(covid, lambda d, h: float(gv.get(d, 1.0)), cap, conv, nz)
        else:
            cr = covid_series(covid, lambda d, h, g=g: g, cap, conv, nz)
        x = cr["2020-02-19":"2020-03-23"]; t = (1 + x).cumprod()
        ep = episodes(res[(name, 3.0)][0]["r"])
        eh_ = episodes(res[(name, "tier_hi")][0]["r"])
        print(f"  {name:28s} COVID {t.iloc[-1]*100-100:+6.1f}% (DD {(t / t.cummax() - 1).min()*100:5.1f}%, "
              f"worst day {x.min()*100:5.1f}%) | 2022 {ep['2022'][0]*100:+6.1f}% DD {ep['2022'][1]*100:5.1f}% | "
              f"Apr25 {ep['Apr25'][0]*100:+5.1f}% | worst day {ep['worst_day']*100:5.1f}% month {ep['worst_month']*100:5.1f}% "
              f"(tier_hi 2022 {eh_['2022'][0]*100:+5.1f}%)")

    # ================= 5. 1256 migration vs account size
    print("\n== 5. QQQ noise half (and IBS index legs) -> micro futures, after tax T2 (35% ST / 26% 1256), "
          "constant account in 2026 $; gain in after-tax CAGR pp vs all-ETF; halves")
    for name in ("V7 1.0x cap .10", "moderate 1.3x cap .15"):
        prof = PROFILES[name]
        for cost in COSTS:
            df, tr = res[(name, cost)]
            print(f"  {name} @ {cost}")
            for E0 in (10e3, 30e3, 60e3, 100e3, 200e3, 300e3, 1e6):
                base, _ = after_tax(df["r"], start=E0, monthly=0, wash=False)
                cells = []
                for lab, kw in (("M1", {}), ("M2", dict(rounding="nearest")), ("M3", dict(ibs=True)),
                                ("M1 park 4x", dict(park_mult=4.0)), ("M4* hybrid", dict(rounding="hybrid"))):
                    rn, r56, inf = migrate(s, df, prof, cost, E0, **kw)
                    ra, _ = after_tax(rn, r1256=r56, start=E0, monthly=0, wash=False)
                    dd = [(B.stats(ra[a:b])[0] - B.stats(base[a:b])[0]) * 100
                          for a, b in (("2021", "2023"), ("2024", "2026"), ("2021", "2026"))]
                    cells.append(f"{lab} {dd[2]:+5.2f} ({dd[0]:+.2f}/{dd[1]:+.2f}) k{inf['kmax']:.0f}")
                # pure tax effect: same ETF returns taxed as 1256 (no granularity, no parking)
                z = s.NZ["QQQ"].reindex(df.index)
                ncap = G.cfg(prof[0] if np.isscalar(prof[0]) else 1.3, prof[2], 2, prof[3])["noise_cap"]
                q = (np.minimum(z.lev.fillna(0), ncap) * 0.5 * z.ret.fillna(0)).fillna(0)
                ideal, _ = after_tax(df["r"], r1256=q, start=E0, monthly=0, wash=False)
                di = (B.stats(ideal)[0] - B.stats(base)[0]) * 100
                print(f"    ${E0/1e3:>5,.0f}k  " + "  ".join(cells) + f"   | ideal(tax only) {di:+.2f}")

    # ================= 6. dollars
    print("\n== 6. $ per year after tax, EH tier_hi (T3 35%): extra vs shipped V7 1.0x")
    base = front[("V7 1.0x cap .10", "tier_hi")]["rea"]
    for name in PROFILES:
        r_ = front[(name, "tier_hi")]["rea"]
        c0, c1 = B.stats(base)[0], B.stats(r_)[0]
        print(f"  {name:30s} EH tier_hi after-tax CAGR {c1*100:5.1f}% vs {c0*100:5.1f}%  -> "
              f"$3k: {3000*(c1-c0):+7,.0f}/yr   $100k: {1e5*(c1-c0):+9,.0f}/yr")

    # ================= 7. POST-HOC, descriptive (no fitting): the live states, conviction by half
    print("\n== 7. POST-HOC descriptive: live today (1.0x cap .10, conviction shadow) vs moderate as built "
          "(1.0x cap .15 until the gate opens)")
    live = {}
    for cost in COSTS:
        for lab, (g, cap, conv) in {"live today 1.0x .10 no conv": (1.0, 0.10, 0.0),
                                    "moderate as built 1.0x .15 no conv": (1.0, 0.15, 0.0),
                                    "1.0x .15 conv 0.5": (1.0, 0.15, 0.5)}.items():
            df, tr = replay(s, Ns[cap], g, cap, conv, None, cost)
            ra, _ = after_tax(df["r"], trades=tr); e = G.eh(df); rea, _ = after_tax(e, trades=tr)
            m = mc_tax(e); ef = B.stats(rea); live[(lab, cost)] = (df, ef)
            print(f"  {lab:36s}{str(cost):>8s} pre {fmt3(df['r'])} | after tax {fmt3(ra)} | EH AT "
                  f"{ef[0]*100:.1f}/{ef[1]:.2f}/{ef[2]*100:.0f} | MC ${m['med']:,.0f} P30 {m['dd30']:.0%} "
                  f"P50 {m['dd50']:.0%} (acct {m['dd30_acct']:.0%}/{m['dd50_acct']:.0%})")
        d = live[("moderate as built 1.0x .15 no conv", cost)][0]["r"] - live[("live today 1.0x .10 no conv", cost)][0]["r"]
        d2 = res[("moderate 1.3x cap .15", cost)][0]["r"] - res[("1.3x gate cap .10", cost)][0]["r"]
        c0 = live[("live today 1.0x .10 no conv", cost)][1][0]; c1 = live[("moderate as built 1.0x .15 no conv", cost)][1][0]
        print(f"  {cost}: NW t (pre-tax daily diff) as-built - live {nw_t(d[:'2023']):+.2f} / {nw_t(d['2024':]):+.2f};"
              f" moderate - gate (1.3x) {nw_t(d2[:'2023']):+.2f} / {nw_t(d2['2024':]):+.2f};"
              f" EH after-tax $/yr as-built vs live: $3k {3000*(c1-c0):+,.0f}  $100k {1e5*(c1-c0):+,.0f}")
    for a, b in (("2016", "2020"), ("2021", "2023"), ("2024", "2026")):
        x = s.BO[a:b]
        print(f"  conviction trade {a}-{b}: n {len(x)}  {x.mean()*1e4:+.1f}bp/trade  t {x.mean()/x.std()*np.sqrt(len(x)):.2f}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "cache":
        build_cache()
    else:
        main()
