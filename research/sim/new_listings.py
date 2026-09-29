"""Addendum NN: a future-agnostic universe -- rules on market structure, not ticker lists.

    # one locked run builds the slim cache (panel + 2016-20 SIP daily + night pool):
    PYTHONPATH=. .venv/bin/python -m research.sim.new_listings --cache
    # everything else works from the cache:
    PYTHONPATH=. .venv/bin/python -m research.sim.new_listings

PRE-REGISTERED 2026-09-28 20:52 PDT (scratchpad addenda/new_listings.md), before any
2024-26 number of this study:

Q1 rule-based IBS universe (replaces the hand list book.EQ18). At each month-end,
   bars strictly up to it: US-listed ETF by asset name, not levered / inverse /
   single-stock (name) and 252d beta to SPY <= 1.6 (structure); equity = no
   bond/commodity/crypto/currency/vol token in the name AND 252d corr to SPY >= 0.5;
   age >= 252 bars; close >= $10; 60d median $volume >= X; dedupe greedily by 60d
   return correlation >= c keeping the most liquid; then the live rule
   (momentum_top 12-1, top 3; IBS < 0.2; next open -> next open).
     U1 X=$100M c=0.95 (primary)   U2 $25M/0.95   U3 $500M/0.95   U4 $100M/0.90
   reference EQ18 (same code, same data); placebo: 18 random funds per month from
   the rule's eligible deduped set, 50 seeds.
Q2 new listings in the night leg. new = first bar (2016-01..2026-09 SIP daily) after
   2021-01-04 (2016-20 proxy: after 2017-01-03).
     F1 age < 252 sessions   F2 age < 63   F3 de-SPAC (first bar <= 5 sessions after
     the last bar of an "Acquisition" name whose last close is within 20% of the
     new symbol's first open)
   x actions EXCLUDE / UP-WEIGHT 2x (tilt, renormalised) on the V7 night pool.
   placebo: exclude the same count of random unflagged names from the same vol20
   decile (200 seeds).
Q3 new ETF launches (prior: dead).
     L1 overnight basket of equity ETFs aged 10-252 sessions vs vol-decile-matched
        seasoned ETFs (50 seeds)
     L2 descriptive: session 21 -> 252 return after launch minus SPY, by launch year.

POST-HOC (reported, can at most be shadow): Q1 U1b beta cap 2.0 (the 1.6 cap drops SMH);
Q2 winsorised / by-year / age 63-252 band / matched up-weight placebo; Q3 L1 liquidity
floors $10M / $50M and a $volume-matched placebo. Data hygiene revised once after the first
Q1 run (the panel carries delisted names at volume 0; reused tickers such as INFO/FB/PCLN).
Runtime ~11 min from the cache.
"""
from __future__ import annotations

import glob
import json
import os
import pickle
import re
import sys

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import growth as G

SP = str(__import__("pathlib").Path(__file__).resolve().parents[2]) + "/data/research/program"
CACHE = f"{SP}/cache_new_listings.pkl"
SIPD1520 = (str(__import__("pathlib").Path(__file__).resolve().parents[2]) + "/data/research/program/add28/sipd1520")   # add. 28 fetch, 2016-01..2020-09
META = "data/research/night/asset_meta.json"
PERIODS = [("2016-20", "2016-01-01", "2020-12-31"), ("2021-23", "2021-01-01", "2023-12-31"),
           ("2024-26", "2024-01-01", "2026-12-31")]
COSTS = [3.0, "tier", "tier_hi"]

# ---------------------------------------------------------------- name rules (fixed ex ante)
ISSUER = (r"ISHARES|SPDR|INVESCO|VANGUARD|SCHWAB|VANECK|GLOBAL X|PROSHARES|DIREXION|WISDOMTREE|"
          r"FIRST TRUST|XTRACKERS|FLEXSHARES|KRANESHARES|AMPLIFY|PACER|ROUNDHILL|AVANTIS|"
          r"DIMENSIONAL|SELECT SECTOR|ARK |JPMORGAN|FIDELITY|FRANKLIN|GOLDMAN SACHS|NUVEEN|"
          r"DEFIANCE|GRANITESHARES|YIELDMAX|T-REX|TRADR|MICROSECTORS|COLUMBIA|HARTFORD|VICTORYSHARES")
ETF_RE = re.compile(rf"\bETF\b|\bETN\b|(({ISSUER}).*\b(TRUST|FUND|SHARES|PORTFOLIO|INDEX)\b)")
LEV_RE = re.compile(r"\b(\d(\.\d+)?X|-\dX|ULTRA|ULTRAPRO|ULTRASHORT|BULL|BEAR|SHORT|INVERSE|DAILY|"
                    r"LEVERAGED|LEVERAGE|T-REX|TRADR|GRANITESHARES|YIELDMAX|MICROSECTORS|"
                    r"OPTION INCOME STRATEGY|ETN)\b")
NONEQ_RE = re.compile(r"\b(BOND|BONDS|TREASURY|TREAS|MUNI|MUNICIPAL|CREDIT|CORPORATE|HIGH YIELD|"
                      r"AGGREGATE|TIPS|MORTGAGE|FLOATING|LOAN|LOANS|T-BILL|BILL|BILLS|COMMODITY|"
                      r"COMMODITIES|GOLD|SILVER|PLATINUM|PALLADIUM|OIL|CRUDE|NATURAL GAS|COPPER|"
                      r"AGRICULTURE|BITCOIN|ETHER|ETHEREUM|CRYPTO|CURRENCY|DOLLAR|EURO|YEN|"
                      r"VOLATILITY|VIX|FIXED INCOME|DURATION)\b")
EQ_OVERRIDE = re.compile(r"\b(MINERS|EQUITY|PRODUCERS|SERVICES|EXPLORATION|STOCK|COMPANIES)\b")
EXCH = {"ARCA", "NASDAQ", "NYSE", "BATS", "AMEX"}


def load_meta():
    return json.load(open(META))


def etf_kind(sym: str, meta: dict) -> str | None:
    """None = not an ETF; 'lev' levered/inverse/single-stock/ETN; 'noneq'; 'eq'."""
    m = meta.get(sym)
    if not m or m.get("exchange") not in EXCH:
        return None
    nm = (m.get("name") or "").upper()
    if not ETF_RE.search(nm) or "COMMON STOCK" in nm:
        return None
    if LEV_RE.search(nm):
        return "lev"
    if NONEQ_RE.search(nm) and not EQ_OVERRIDE.search(nm):
        return "noneq"
    return "eq"


# ---------------------------------------------------------------- cache (LOCKED run)
def build_cache():
    from swingtrader.universe import valid_symbol
    from . import data as D
    meta = load_meta()
    out = {}
    # ---- 2016-20 SIP daily, long -> wide per field
    old = pd.concat([pd.read_parquet(f, columns=["symbol", "timestamp", "open", "high", "low",
                                                 "close", "volume"])
                     for f in sorted(glob.glob(f"{SIPD1520}/*.parquet"))])
    old["date"] = old.timestamp.dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    old = old.drop(columns="timestamp")
    print("old rows", len(old), flush=True)
    new = D.panel()
    P0 = {}
    for f in ("open", "high", "low", "close", "volume"):
        P0[f] = old.pivot_table(index="date", columns="symbol", values=f, aggfunc="last").astype("float32")
        P0[f] = P0[f][P0[f].index < new["close"].index.min()]
    del old
    syms_all = sorted(set(P0["close"].columns) | set(new["close"].columns))
    # ---- per-symbol first / last bar, first open, last close (all symbols)
    fl = {}
    for P in (P0, new):
        C = P["close"]; O = P["open"]
        nn = C.notna()
        first = nn.idxmax().where(nn.any()); last = nn[::-1].idxmax().where(nn.any())
        for s in C.columns:
            if pd.isna(first[s]):
                continue
            f0, l0 = first[s], last[s]
            a = fl.get(s)
            fo, lc = float(O.at[f0, s]), float(C.at[l0, s])
            if a is None:
                fl[s] = [f0, l0, fo, lc]
            else:
                if f0 < a[0]:
                    a[0], a[2] = f0, fo
                if l0 > a[1]:
                    a[1], a[3] = l0, lc
    out["firstlast"] = pd.DataFrame.from_dict(fl, orient="index", columns=["first", "last", "fopen", "lclose"])
    print("symbols", len(fl), flush=True)
    # ---- ETF subset, full OHLCV 2016-2026
    etfs = [s for s in syms_all if etf_kind(s, meta) is not None]
    E = {}
    for f in ("open", "high", "low", "close", "volume"):
        a = P0[f].reindex(columns=etfs); b = new[f].reindex(columns=etfs).astype("float32")
        E[f] = pd.concat([a, b]).sort_index()
    out["etf"] = E
    print("etfs", len(etfs), flush=True)
    # ---- daily-bar night proxy (close signal), both eras, stocks and ETFs alike
    rows = []
    for P in (P0, new):
        O, H, L, C, V = (P[k].astype("float32") for k in ("open", "high", "low", "close", "volume"))
        R = C.pct_change(fill_method=None)
        adv = (C * V).rolling(20, min_periods=15).mean().shift(1)
        vol20 = R.rolling(20, min_periods=15).std().shift(1) * np.sqrt(252)
        nxt = O.shift(-1) / C - 1
        ibs = (C - L) / (H - L).where(lambda x: x > 0)
        m = (R <= -0.08) & (ibs < 0.1) & (C >= 5) & (adv >= 1e7) & nxt.abs().le(1)
        st = m.stack()
        st = st[st]
        idx = st.index
        get = lambda X: X.stack().reindex(idx).values  # noqa: E731
        df = pd.DataFrame({"date": idx.get_level_values(0), "sym": idx.get_level_values(1),
                           "day_ret": get(R), "ibs": get(ibs), "close": get(C), "ret": get(nxt),
                           "vol20": get(vol20), "adv": get(adv)})
        rows.append(df)
        del O, H, L, C, V, R, adv, vol20, nxt, ibs, m
    q = pd.concat(rows, ignore_index=True)
    q = q[q.sym.map(valid_symbol)]
    out["proxy"] = q
    print("proxy rows", len(q), flush=True)
    # ---- the honest 15:50 night pool as shipped (V7: corr 0.7, cap 0.10)
    out["N"] = B.night_days(max_corr=0.7, max_name_pct=0.10)
    # session calendar
    out["cal"] = pd.DatetimeIndex(sorted(set(P0["close"].index) | set(new["close"].index)))
    pickle.dump(out, open(CACHE, "wb"), protocol=4)
    print("cache written", CACHE, flush=True)


def load_cache():
    return pickle.load(open(CACHE, "rb"))


def load_segments():
    return pickle.load(open(f"{SP}/cache_new_listings_seg.pkl", "rb"))


if __name__ == "__main__" and "--cache" in sys.argv:
    build_cache()


# ================================================================= helpers
def pstats(r: pd.Series) -> dict:
    return {k: B.stats(r[a:b]) for k, a, b in PERIODS}


def fmt3(r: pd.Series, periods=("2016-20", "2021-23", "2024-26")) -> str:
    st = pstats(r)
    return "  ".join(f"{st[k][0]*100:6.1f}/{st[k][1]:5.2f}/{st[k][2]*100:4.0f}" for k in periods)


def cluster_t(y: np.ndarray, flag: np.ndarray, groups: np.ndarray) -> tuple[float, float]:
    """OLS y = a + b*flag, SE clustered by group (day). Returns (b, t)."""
    X = np.column_stack([np.ones(len(y)), flag.astype(float)])
    XtX = np.linalg.inv(X.T @ X)
    beta = XtX @ X.T @ y
    u = y - X @ beta
    df = pd.DataFrame({"g": groups, "a": u, "b": u * X[:, 1]})
    S = df.groupby("g")[["a", "b"]].sum().values
    meat = S.T @ S
    G_ = len(S)
    V = XtX @ meat @ XtX * G_ / max(G_ - 1, 1)
    return float(beta[1]), float(beta[1] / np.sqrt(V[1, 1])) if V[1, 1] > 0 else np.nan


def nw_t(r: pd.Series, lags: int = 5) -> float:
    x = r.dropna().values - r.dropna().mean()
    n = len(x)
    if n < 30:
        return np.nan
    g0 = (x * x).mean(); s = g0
    for L in range(1, lags + 1):
        s += 2 * (1 - L / (lags + 1)) * (x[L:] * x[:-L]).mean()
    return float(r.dropna().mean() / np.sqrt(s / n))


def v7(s, cost, **kw):
    return s.replay(B.Params(**{**G.V7, **G.cfg(1.0, 0.5, 2, None), "night_cost": cost,
                                "ibs_cost_bps": 0.0, **kw}))


def roth_b1(s, cost):
    from . import roth as RT
    base = dict(tilt="live", weekend_scale=0.5, noise_on=False, conviction_w=0.0, margin_rate=0.0)
    return RT.replay(s, s.days, B.Params(night_cost=cost, ibs_cost_bps=0.0, **base),
                     budget="night", noise_cap=1.5)


def book_line(lab, df):
    r = df["r"]
    return f"  {lab:40s} {fmt3(r, ('2021-23', '2024-26'))}   full {B.stats(r)[0]*100:5.1f}/{B.stats(r)[1]:4.2f}"


# ================================================================= Q1: IBS universe
class ETFs:
    def __init__(self, cache):
        E = cache["etf"]; meta = load_meta()
        self.O, self.H, self.L, self.C, self.V = (E[k].astype("float64") for k in
                                                  ("open", "high", "low", "close", "volume"))
        self.days = self.C.index
        self.kind = pd.Series({s: etf_kind(s, meta) for s in self.C.columns})
        # data hygiene (fixed before any Q1 result): the panel carries delisted names forward
        # at volume 0, and a ticker can be reused (INFO: IHS Markit -> a Harbor ETF, FB, PCLN).
        # A bar exists only with volume > 0; the current name belongs to the LAST listing,
        # split at gaps > 60 sessions or a |daily return| > 40% (impossible in an unlevered fund).
        # (revised once after the first Q1 run exposed INFO; thin funds skip days, so not 5)
        bad = ~(self.V > 0)
        for X in (self.O, self.H, self.L, self.C, self.V):
            X[bad] = np.nan
        R0 = self.C.pct_change(fill_method=None)
        cutc = {}
        A = self.C.notna().values
        for j, s in enumerate(self.C.columns):
            pos = np.flatnonzero(A[:, j])
            if not len(pos):
                continue
            brk = pos[1:][np.diff(pos) > 60]
            if self.kind.get(s) in ("eq", "noneq"):
                jump = np.flatnonzero((R0.iloc[:, j].abs() > 0.40).values)
                brk = np.r_[brk, jump]
            if len(brk):
                cutc[s] = self.days[int(brk.max())]
        for s, t in cutc.items():
            m = self.days < t
            for X in (self.O, self.H, self.L, self.C, self.V):
                X.loc[m, s] = np.nan
        self.n_relisted = len(cutc)
        self.R = self.C.pct_change(fill_method=None)
        self.dv = self.C * self.V
        self.adv60 = self.dv.rolling(60, min_periods=40).median()
        self.adv20 = self.dv.rolling(20, min_periods=15).median()
        self.nbars = self.C.notna().cumsum()
        self.spy = self.R["SPY"]
        self.first = cache["firstlast"]["first"].reindex(self.C.columns)
        me = pd.Series(self.days, index=self.days).groupby([self.days.year, self.days.month]).last()
        self.month_ends = pd.DatetimeIndex(me.values)

    def eligible(self, t, X, eq_only=True):
        """Funds passing the Q1 rule at month-end t (bars up to and including t)."""
        i = self.days.get_loc(t)
        if i < 260:
            return []
        cols = self.kind.index[self.kind == "eq"] if eq_only else self.kind.index[self.kind.notna()]
        ok = ((self.nbars.iloc[i][cols] >= 252) & (self.C.iloc[i][cols] >= 10)
              & (self.adv60.iloc[i][cols] >= X))
        cols = ok.index[ok.fillna(False).values]
        W = self.R.iloc[i - 251:i + 1][cols]; m = self.spy.iloc[i - 251:i + 1]
        n = W.notna().sum()
        Wc = W.sub(W.mean()); mc_ = m - m.mean()
        cov = Wc.mul(mc_, axis=0).mean(); corr = cov / (W.std(ddof=0) * m.std(ddof=0))
        beta = cov / m.var(ddof=0)
        keep = (n >= 200) & (corr >= 0.5) & (beta <= 1.6)
        return list(keep.index[keep.values])

    def dedupe(self, t, cols, X, c):
        i = self.days.get_loc(t)
        if not cols:
            return []
        order = self.adv60.iloc[i][cols].sort_values(ascending=False).index
        M = self.R.iloc[i - 59:i + 1][order].corr(min_periods=40).values
        kept = []
        for j in range(len(order)):
            if all(not (M[j, k] >= c) for k in kept):
                kept.append(j)
        return [order[j] for j in kept]

    def universes(self, X, c):
        """month-end t -> deduped eligible list."""
        out = {}
        for t in self.month_ends:
            if t >= self.days[-1]:
                continue
            out[t] = self.dedupe(t, self.eligible(t, X), X, c)
        return out

    def momentum(self, t, cols, k=3):
        i = self.days.get_loc(t)
        if i < 252 or not cols:
            return []
        mom = self.C.iloc[i - 21][cols] / self.C.iloc[i - 252][cols] - 1
        return sorted(mom.dropna().sort_values(ascending=False).index[:k])

    def ibs_dict(self, top_by_month: dict, cost, ibs_max=0.2):
        """Same shape as book.ibs_days, cost already inside r: d -> [(sym, o1, r_net)]."""
        O, H, L, C = self.O, self.H, self.L, self.C
        days = self.days
        me = sorted(top_by_month)
        out = {}
        for j in range(260, len(days) - 2):
            d, today = days[j], days[j + 1]
            prior = [t for t in me if t.to_period("M") < today.to_period("M")]
            if not prior:
                continue
            uni = top_by_month[prior[-1]]
            legs = []
            for s in uni:
                h, l, cl = H.iat[j, H.columns.get_loc(s)], L.iat[j, L.columns.get_loc(s)], C.iat[j, C.columns.get_loc(s)]
                v = sg.ibs(h, l, cl)
                if not (np.isfinite(v) and v < ibs_max):
                    continue
                o1, o2 = O.at[days[j + 1], s], O.at[days[j + 2], s]
                if not (np.isfinite(o1) and np.isfinite(o2)):
                    continue
                cb = float(B.cost_bps(cost, np.array([o1]), np.array([self.adv20.at[d, s]]))[0])
                legs.append((s, o1, o2 / o1 - 1 - 2 * cb / 1e4))
            if legs:
                out[d] = legs
        return out


def leg_series(I: dict, days) -> pd.Series:
    r = pd.Series({d: np.mean([x[2] for x in v]) for d, v in I.items()})
    return r.reindex(days).fillna(0.0)


# ---------------------------------------------------------------- listing segments (LOCKED run)
GAP = 20   # sessions without a bar that end a listing (ticker reuse: FB, PCLN, ...)


def segments_of(nn: pd.DataFrame) -> dict:
    """nn: session x symbol bool (has bar). -> sym -> [(start, end), ...] split at gaps > GAP."""
    idx = nn.index; out = {}
    A = nn.values
    for j, s in enumerate(nn.columns):
        pos = np.flatnonzero(A[:, j])
        if not len(pos):
            continue
        br = np.flatnonzero(np.diff(pos) > GAP)
        st = np.r_[pos[0], pos[br + 1]]; en = np.r_[pos[br], pos[-1]]
        out[s] = [(idx[a], idx[b]) for a, b in zip(st, en)]
    return out


def build_segments():
    from . import data as D
    old = pd.concat([pd.read_parquet(f, columns=["symbol", "timestamp"])
                     for f in sorted(glob.glob(f"{SIPD1520}/*.parquet"))])
    old["date"] = old.timestamp.dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    old["x"] = True
    a = old.pivot_table(index="date", columns="symbol", values="x", aggfunc="any").fillna(False)
    del old
    P = D.panel()
    b = P["close"].notna() & (P["volume"] > 0)      # the panel carries delisted names forward at volume 0
    a = a[a.index < b.index.min()]
    cols = sorted(set(a.columns) | set(b.columns))
    nn = pd.concat([a.reindex(columns=cols, fill_value=False), b.reindex(columns=cols, fill_value=False)]).fillna(False).astype(bool)
    seg = segments_of(nn)
    pickle.dump(seg, open(f"{SP}/cache_new_listings_seg.pkl", "wb"), protocol=4)
    print("segments", len(seg), sum(len(v) > 1 for v in seg.values()), "with gaps", flush=True)


if __name__ == "__main__" and "--segments" in sys.argv:
    build_segments()


Q1_VARIANTS = {"U1 $100M c0.95": (1e8, 0.95), "U2 $25M c0.95": (2.5e7, 0.95),
               "U3 $500M c0.95": (5e8, 0.95), "U4 $100M c0.90": (1e8, 0.90)}


def q1_universes(e: ETFs, beta_cap=1.6):
    """variant -> {month-end: top-3}; also the U1 deduped eligible sets for the placebo."""
    tops, sets = {}, {}
    for lab, (X, c) in Q1_VARIANTS.items():
        U = {}
        for t in e.month_ends:
            if t >= e.days[-1]:
                continue
            U[t] = e.dedupe(t, e.eligible(t, X), X, c)
        sets[lab] = U
        tops[lab] = {t: e.momentum(t, u) for t, u in U.items()}
    eq = {}
    for t in e.month_ends:
        if t >= e.days[-1]:
            continue
        i = e.days.get_loc(t)
        ok = [s for s in B.EQ18 if e.nbars.iat[i, e.C.columns.get_loc(s)] >= 252]
        eq[t] = e.momentum(t, ok)
    tops["EQ18 (hand list)"] = eq
    return tops, sets


EPIS = {"COVID": ("2020-02-19", "2020-03-23"), "2022": ("2022-01-03", "2022-10-12"),
        "Apr25": ("2025-04-02", "2025-04-08")}


def epis(r: pd.Series) -> str:
    return "  ".join(f"{k} {((1 + r[a:b]).prod() - 1)*100:6.1f}%" for k, (a, b) in EPIS.items()
                     if len(r[a:b]))


def worst(r: pd.Series) -> str:
    return f"worst day {r.min()*100:5.1f}%  worst month {G.monthly_worst(r)*100:5.1f}%"


def mc_line(df) -> str:
    e = G.eh(df)
    a, b = G.mc(e, 3000, 1000), G.mc(e, 10000, 0)
    st = B.stats(e)
    return (f"EH {st[0]*100:5.1f}/{st[1]:4.2f}/{st[2]*100:4.0f} | $3k+1k/mo med ${a['med']:>9,.0f} "
            f"P(DD>30) {a['dd30']:4.0%} P(DD>50) {a['dd50']:4.0%} | $10k med ${b['med']:>9,.0f} "
            f"P(DD>30) {b['dd30']:4.0%} P(DD>50) {b['dd50']:4.0%}")


def run_q1(c, s, out):
    import copy
    e = ETFs(c)
    tops, sets = q1_universes(e)
    # POST-HOC (added after seeing that the 1.6 beta cap removes SMH in 2023-24): beta cap 2.0
    e2 = e
    X, cc = Q1_VARIANTS["U1 $100M c0.95"]
    tops["U1b beta<=2.0 (POST-HOC)"] = {}
    orig = ETFs.eligible
    def elig2(self, t, X, eq_only=True):          # same rule, beta cap 2.0
        i = self.days.get_loc(t)
        if i < 260:
            return []
        cols = self.kind.index[self.kind == "eq"]
        ok = ((self.nbars.iloc[i][cols] >= 252) & (self.C.iloc[i][cols] >= 10) & (self.adv60.iloc[i][cols] >= X))
        cols = ok.index[ok.fillna(False).values]
        W = self.R.iloc[i - 251:i + 1][cols]; m = self.spy.iloc[i - 251:i + 1]
        n = W.notna().sum(); Wc = W.sub(W.mean()); mc_ = m - m.mean()
        cov = Wc.mul(mc_, axis=0).mean(); corr = cov / (W.std(ddof=0) * m.std(ddof=0)); beta = cov / m.var(ddof=0)
        keep = (n >= 200) & (corr >= 0.5) & (beta <= 2.0)
        return list(keep.index[keep.values])
    for t in e.month_ends:
        if t >= e.days[-1]:
            continue
        tops["U1b beta<=2.0 (POST-HOC)"][t] = e.momentum(t, e.dedupe(t, elig2(e, t, X), X, cc))
    print("\n== Q1 rule-based IBS universe. Picks (top-3) at selected month-ends")
    for t in e.month_ends[[12, 36, 48, 60, 72, 84, 96, 108, -3]]:
        print(f"  {t:%Y-%m}  " + "  ".join(f"{k.split()[0]}:{','.join(v.get(t, []))}" for k, v in tops.items()))
    ov = {k: np.mean([len(set(v[t]) & set(tops['EQ18 (hand list)'][t])) / 3 for t in v if t in tops['EQ18 (hand list)']])
          for k, v in tops.items()}
    print("  overlap with EQ18 picks: " + "  ".join(f"{k.split()[0]} {x:.0%}" for k, x in ov.items()))
    print("  eligible/deduped set size U1 (median): %d" % np.median([len(u) for u in sets["U1 $100M c0.95"].values() if u]))

    print("\n-- standalone IBS leg (unit weight, 0 on no-signal days): CAGR/Sharpe/maxDD   2016-20 | 2021-23 | 2024-26   NW t (full)")
    I_all, leg = {}, {}
    for cost in (1.0, 3.0, "tier", "tier_hi"):
        for k, tb in tops.items():
            I = e.ibs_dict(tb, cost); I_all[(k, cost)] = I
            r = leg_series(I, e.days[(e.days >= "2016-01-01")]); leg[(k, cost)] = r
            print(f"  {k:28s} {str(cost):>7s}  {fmt3(r)}   t {nw_t(r[r != 0]):5.2f}  days {len(I)}")
    # placebo: 18 random funds a month from the U1 eligible deduped set
    rng = np.random.default_rng(11)
    U = sets["U1 $100M c0.95"]
    pl = []
    for seed in range(50):
        tb = {t: e.momentum(t, list(rng.choice(u, size=min(18, len(u)), replace=False))) if u else []
              for t, u in U.items()}
        I = e.ibs_dict(tb, 3.0)
        r = leg_series(I, e.days[e.days >= "2016-01-01"])
        st = pstats(r)
        s.I = I
        df = v7(s, "tier_hi")
        pl.append([st[p][1] for p, _, _ in PERIODS] + [B.stats(df.r[:"2023-12-31"])[0], B.stats(df.r["2024-01-01":])[0]])
    pl = np.array(pl)
    print("  placebo (50 seeds) standalone Sharpe p50/p90 by period: "
          + "  ".join(f"{p} {np.median(pl[:, j]):4.2f}/{np.percentile(pl[:, j], 90):4.2f}" for j, (p, _, _) in enumerate(PERIODS))
          + f" | book tier_hi CAGR p50/p90 21-23 {np.median(pl[:,3])*100:5.1f}/{np.percentile(pl[:,3],90)*100:5.1f}"
            f" 24-26 {np.median(pl[:,4])*100:5.1f}/{np.percentile(pl[:,4],90)*100:5.1f}")
    for k in tops:
        st = pstats(leg[(k, 3.0)])
        pc = [(pl[:, j] < st[p][1]).mean() for j, (p, _, _) in enumerate(PERIODS)]
        print(f"    {k:28s} standalone Sharpe pct vs placebo: " + " ".join(f"{x:4.0%}" for x in pc))

    print("\n-- V7 book with the IBS universe swapped (night pool as shipped). 2021-23 | 2024-26 CAGR/Sh/DD")
    books = {}
    for cost in (3.0, "tier", "tier_hi"):
        for k in tops:
            s.I = I_all[(k, cost)]
            df = v7(s, cost); books[(k, cost)] = df
            ex = f"  pct-vs-placebo(CAGR) {(pl[:,3] < B.stats(df.r[:'2023-12-31'])[0]).mean():4.0%}/{(pl[:,4] < B.stats(df.r['2024-01-01':])[0]).mean():4.0%}" if cost == "tier_hi" else ""
            print(book_line(f"{k} @{cost}", df) + ex)
    print("\n-- tails, tier_hi: edge-halves + 5y MC; episodes; worst")
    for k in tops:
        df = books[(k, "tier_hi")]
        print(f"  {k:28s} {mc_line(df)}")
        print(f"  {'':28s} {epis(df.r)}  {worst(df.r)}   standalone IBS leg: {epis(leg[(k, 'tier_hi')])}")
    print("\n-- Roth b1 (1.0x, IBS + night, intraday via 3x ETFs), IBS universe swapped")
    for cost in (3.0, "tier_hi"):
        for k in tops:
            s.I = I_all[(k, cost)]
            print(book_line(f"Roth {k} @{cost}", roth_b1(s, cost)))
    out["q1"] = {"books": {k: v.r for k, v in books.items()}, "leg": leg, "pl": pl, "tops": tops}
    return I_all


# ================================================================= Q2: new listings, night leg
NEW_AFTER = pd.Timestamp("2021-01-04")
NEW_AFTER_PROXY = pd.Timestamp("2017-01-03")


class Ages:
    def __init__(self, c):
        self.seg = load_segments(); self.cal = c["cal"]; self.pos = {d: i for i, d in enumerate(self.cal)}
        fl = c["firstlast"]; meta = load_meta()
        acq = [s for s, v in meta.items() if "ACQUISITION" in (v.get("name") or "").upper() and s in self.seg]
        ends = [(self.pos[self.seg[s][-1][1]], float(fl.at[s, "lclose"])) for s in acq if s in fl.index]
        ends = np.array(ends) if ends else np.zeros((0, 2))
        self.despac = {}
        for s, sgs in self.seg.items():
            st = sgs[-1][0]
            if st <= NEW_AFTER_PROXY or s not in fl.index:
                continue
            p0, fo = self.pos[st], float(fl.at[s, "fopen"])
            gap = p0 - ends[:, 0]
            m = (gap >= 0) & (gap <= 5) & (np.abs(ends[:, 1] / fo - 1) <= 0.20) if len(ends) else np.array([])
            self.despac[s] = bool(m.any()) if len(m) else False

    def start(self, s, d):
        for a, b in self.seg.get(s, []):
            if a <= d <= b + pd.Timedelta(days=5):
                return a
        return None

    def flags(self, s, d, after):
        st = self.start(s, d)
        if st is None:
            return (False, False, False, np.nan)
        age = self.pos.get(d, np.nan) - self.pos[st] if d in self.pos else np.nan
        new = st > after
        return (new and age < 252, new and age < 63, new and self.despac.get(s, False), age)


def q2_tables(c, A: Ages):
    rows = []
    for d, nd in c["N"].items():
        c_t = B.cost_bps("tier", nd.price, nd.adv); c_h = B.cost_bps("tier_hi", nd.price, nd.adv)
        for j, s in enumerate(nd.syms):
            f1, f2, f3, age = A.flags(s, d, NEW_AFTER)
            rows.append((d, s, nd.ret[j], nd.ret[j] - 2 * c_t[j] / 1e4, nd.ret[j] - 2 * c_h[j] / 1e4,
                         nd.vol20[j], nd.day_ret[j], f1, f2, f3, age))
    T = pd.DataFrame(rows, columns=["date", "sym", "ret", "net_t", "net_h", "vol20", "day_ret", "F1", "F2", "F3", "age"])
    P = c["proxy"]; P = P[P.vol20 >= 0.6].copy()
    fl = [A.flags(s, d, NEW_AFTER_PROXY if d < pd.Timestamp("2020-10-01") else NEW_AFTER) for s, d in zip(P.sym, P.date)]
    P[["F1", "F2", "F3", "age"]] = pd.DataFrame(fl, index=P.index)
    P["net_t"] = P.ret - 2 * B.cost_bps("tier", P.close.values, P.adv.values) / 1e4
    return T, P


def with_flags(N: dict, T: pd.DataFrame, f: str) -> dict:
    fl = T.set_index(["date", "sym"])[f]
    out = {}
    for d, nd in N.items():
        x = B.NightDay(**{k: getattr(nd, k) for k in nd.__dataclass_fields__})
        x.flag = np.array([bool(fl.get((d, s), False)) for s in nd.syms])
        out[d] = x
    return out


def exclude(N: dict, mask_of) -> dict:
    """Drop names (mask True) before sizing; the crowd count n_raw is unchanged."""
    out = {}
    for d, nd in N.items():
        m = mask_of(d, nd)
        if not m.any():
            out[d] = nd; continue
        k = ~m
        if not k.any():
            continue
        frac = min(1.0 / k.sum(), 0.10) * min(1.0, 30 / max(nd.n_raw, 1))
        out[d] = B.NightDay(nd.syms[k], nd.price[k], nd.close[k], nd.ret[k], nd.adv[k], nd.vol20[k],
                            nd.ret20[k], nd.day_ret[k], frac, nd.n_raw)
    return out


def upweight_tilt(nd):
    w = sg.night_tilt(nd.vol20, nd.day_ret, 0.25) * np.where(nd.flag, 2.0, 1.0)
    return w / w.mean()


def run_q2(c, s, out):
    A = Ages(c)
    T, P = q2_tables(c, A)
    N = c["N"]
    # sanity: sizing formula reproduces the pool's frac
    bad = [d for d, nd in N.items() if abs(min(1 / len(nd.syms), 0.10) * min(1, 30 / max(nd.n_raw, 1)) - nd.frac) > 1e-12]
    print(f"\n== Q2 new listings in the night leg. pool trades {len(T)}, frac mismatches {len(bad)}; "
          f"de-SPAC-matched new symbols {sum(A.despac.values())} of {len(A.despac)} new")
    print("  flag share of pool trades: " + "  ".join(f"{f} {T[f].mean():.1%}" for f in ("F1", "F2", "F3")))
    print("\n-- per trade, next-open return net of tier (bp): flagged | seasoned | diff, day-clustered t")
    halves = {"2021-23": T[T.date <= "2023-12-31"], "2024-26": T[T.date >= "2024-01-01"], "2021-26": T}
    prx = {"proxy 2017-20": P[(P.date >= "2017-01-01") & (P.date < "2020-10-01")], "proxy 2021-26": P[P.date >= "2021-01-01"]}
    res = {}
    for f in ("F1", "F2", "F3"):
        for lab, X in {**halves, **prx}.items():
            y = X.net_t.values; fl = X[f].fillna(False).values.astype(bool)
            if fl.sum() < 5:
                print(f"  {f} {lab:14s} n_flag {fl.sum():4d}  (too few)"); continue
            b, t = cluster_t(y, fl, X.date.values)
            res[(f, lab)] = (b, t)
            print(f"  {f} {lab:14s} n_flag {fl.sum():5d} {y[fl].mean()*1e4:7.1f} | {y[~fl].mean()*1e4:6.1f} | {b*1e4:7.1f}  t {t:5.2f}"
                  f"   win {np.mean(y[fl] > 0):.0%}/{np.mean(y[~fl] > 0):.0%}")
    print("\n-- V7 book: EXCLUDE / UP-WEIGHT 2x flagged names. 2021-23 | 2024-26 CAGR/Sh/DD")
    books = {}
    for cost in (3.0, "tier", "tier_hi"):
        s.N = N
        base = v7(s, cost); books[("base", cost)] = base
        print(book_line(f"shipped V7 @{cost}", base))
        for f in ("F1", "F2", "F3"):
            Nf = with_flags(N, T, f)
            s.N = exclude(Nf, lambda d, nd: nd.flag); df = v7(s, cost); books[(f + " excl", cost)] = df
            print(book_line(f"{f} EXCLUDE @{cost}", df))
            s.N = Nf; df = v7(s, cost, tilt=upweight_tilt); books[(f + " up2x", cost)] = df
            print(book_line(f"{f} UP-WEIGHT 2x @{cost}", df))
    # placebo for EXCLUDE: same count of random unflagged names from the same vol20 decile
    print("\n-- placebo (200 seeds): exclude random same-decile unflagged names, tier_hi. CAGR gain vs shipped p50/p90 per half")
    s.N = N; base = books[("base", "tier_hi")].r
    b1, b2 = B.stats(base[:"2023-12-31"])[0], B.stats(base["2024-01-01":])[0]
    edges = np.nanpercentile(T.vol20, np.arange(10, 100, 10))
    for f in ("F1", "F2", "F3"):
        Nf = with_flags(N, T, f)
        g = []
        for seed in range(200):
            rng = np.random.default_rng(seed)
            def mk(d, nd, rng=rng):
                m = np.zeros(len(nd.syms), bool)
                dec = np.digitize(nd.vol20, edges)
                for j in np.flatnonzero(nd.flag):
                    cand = np.flatnonzero(~nd.flag & ~m & (dec == dec[j]))
                    if not len(cand):
                        cand = np.flatnonzero(~nd.flag & ~m)
                    if len(cand):
                        m[rng.choice(cand)] = True
                return m
            s.N = exclude(Nf, mk); df = v7(s, "tier_hi")
            g.append((B.stats(df.r[:"2023-12-31"])[0] - b1, B.stats(df.r["2024-01-01":])[0] - b2))
        g = np.array(g)
        real = books[(f + " excl", "tier_hi")].r
        r1, r2 = B.stats(real[:"2023-12-31"])[0] - b1, B.stats(real["2024-01-01":])[0] - b2
        print(f"  {f}: real {r1*100:+5.2f} / {r2*100:+5.2f}pp   placebo p50 {np.median(g[:,0])*100:+5.2f} / {np.median(g[:,1])*100:+5.2f}"
              f"  p90 {np.percentile(g[:,0],90)*100:+5.2f} / {np.percentile(g[:,1],90)*100:+5.2f}"
              f"   real pct {np.mean(g[:,0] < r1):.0%} / {np.mean(g[:,1] < r2):.0%}")
    s.N = N
    print("\n-- tails, tier_hi")
    for k in [("base", "tier_hi")] + [(f + a, "tier_hi") for f in ("F1", "F2", "F3") for a in (" excl", " up2x")]:
        print(f"  {k[0]:12s} {mc_line(books[k])}  {epis(books[k].r)}  {worst(books[k].r)}")
    print("\n-- Roth b1 at tier_hi")
    for f in ("F1", "F2", "F3"):
        Nf = with_flags(N, T, f)
        s.N = N; print(book_line("Roth shipped", roth_b1(s, "tier_hi"))) if f == "F1" else None
        s.N = exclude(Nf, lambda d, nd: nd.flag); print(book_line(f"Roth {f} EXCLUDE", roth_b1(s, "tier_hi")))
    s.N = N
    out["q2"] = {"T": T, "res": res, "books": {k: v.r for k, v in books.items()}}


# ================================================================= Q3: new ETF launches
def run_q3(c, out, e: ETFs | None = None):
    e = e or ETFs(c)
    eq = e.kind.index[e.kind == "eq"]
    C, O = e.C[eq], e.O[eq]
    days = e.days
    start = C.notna().idxmax().where(C.notna().any())
    pos = pd.Series(np.arange(len(days)), index=days)
    spos = start.map(lambda t: pos[t] if pd.notna(t) else np.nan)
    age = pd.DataFrame(np.arange(len(days))[:, None] - spos.values[None, :], index=days, columns=eq)
    new_fund = start > pd.Timestamp("2016-03-01")
    seasoned_fund = start <= pd.Timestamp("2016-01-08")
    on = O.shift(-1) / C - 1
    on = on.where(on.abs() <= 0.5)
    intra = C / O - 1
    vol20 = C.pct_change(fill_method=None).rolling(20, min_periods=15).std() * np.sqrt(252)
    ok = (C >= 10) & (e.adv20[eq] >= 1e6) & on.notna() & vol20.notna()
    NEW = ok & new_fund.values[None, :] & (age >= 10) & (age <= 252)
    OLD = ok & (seasoned_fund.values[None, :] | (age > 756))
    print(f"\n== Q3 new ETF launches. equity ETFs {len(eq)}, launched after 2016-03: {int(new_fund.sum())}; "
          f"listings split by hygiene rule: {e.n_relisted}")
    print("  mean new funds in the basket per day: " + "  ".join(
        f"{k} {NEW[a:b].sum(axis=1).mean():5.1f}" for k, a, b in PERIODS))
    res = {}
    for cost in COSTS:
        cb = B.cost_bps(cost, C.values.ravel(), e.adv20[eq].values.ravel()).reshape(C.shape) if isinstance(cost, str) else np.full(C.shape, cost)
        net = on - 2 * cb / 1e4
        l1 = net.where(NEW).mean(axis=1).fillna(0)
        res[cost] = l1
        print(f"  L1 new-ETF overnight basket @{str(cost):7s} {fmt3(l1)}   NW t {nw_t(l1[l1 != 0]):5.2f}")
    # descriptive split: gross overnight vs intraday, new vs seasoned (bp/day, fund-day mean)
    for k, a, b in PERIODS:
        n1, o1 = on[a:b].where(NEW[a:b]), on[a:b].where(OLD[a:b])
        i1, j1 = intra[a:b].where(NEW[a:b]), intra[a:b].where(OLD[a:b])
        print(f"  {k}: gross bp/fund-day overnight new {np.nanmean(n1.values)*1e4:5.1f} vs seasoned {np.nanmean(o1.values)*1e4:5.1f}"
              f" | intraday new {np.nanmean(i1.values)*1e4:5.1f} vs seasoned {np.nanmean(j1.values)*1e4:5.1f}")
    # placebo: per day, one random seasoned fund from the same vol20 decile per new fund, 50 seeds, 3bp
    edges = np.nanpercentile(vol20.where(ok).values, np.arange(10, 100, 10))
    dec = np.digitize(np.nan_to_num(vol20.values, nan=0), edges)
    ONv, NEWv, OLDv = on.values, NEW.values, OLD.values
    pl = np.zeros((50, len(days)))
    rng = np.random.default_rng(5)
    for i in range(len(days)):
        nj = np.flatnonzero(NEWv[i])
        if not len(nj):
            continue
        oj = np.flatnonzero(OLDv[i])
        if not len(oj):
            continue
        for sd in range(50):
            picks = []
            for j in nj:
                cand = oj[dec[i, oj] == dec[i, j]]
                cand = cand if len(cand) else oj
                picks.append(rng.choice(cand))
            pl[sd, i] = np.nanmean(ONv[i, picks]) - 6e-4
    pl = pd.DataFrame(pl.T, index=days)
    real = res[3.0]
    for k, a, b in PERIODS:
        sh = [B.stats(pl[sd][a:b])[1] for sd in range(50)]
        rs = B.stats(real[a:b])[1]
        print(f"  L1 {k}: Sharpe {rs:5.2f}  placebo p50 {np.median(sh):5.2f} p90 {np.percentile(sh, 90):5.2f}  pct {np.mean(np.array(sh) < rs):.0%}")
    # L2: session 21 -> 252 after launch, minus SPY
    spy = e.C["SPY"]
    rows = []
    for s in eq[new_fund.values]:
        p0 = int(spos[s]); x = C[s]
        if p0 + 21 >= len(days):
            continue
        a = x.iloc[p0 + 21]
        seg = x.iloc[p0 + 21:p0 + 253].dropna()
        if not np.isfinite(a) or len(seg) < 2:
            continue
        full = p0 + 252 < len(days)
        if not full:
            continue
        t1 = seg.index[-1]
        rows.append((s, days[p0].year, seg.iloc[-1] / a - 1 - (spy[t1] / spy.iloc[p0 + 21] - 1), len(seg) < 200))
    L2 = pd.DataFrame(rows, columns=["sym", "year", "xs", "closed_early"])
    print("  L2 session 21->252 return minus SPY, by launch year: n / mean / median / % beat SPY / % closed early")
    for y, g in L2.groupby("year"):
        x = g["xs"]
        print(f"    {y}  {len(g):4d}  {x.mean()*100:6.1f}%  {x.median()*100:6.1f}%  {np.mean(x > 0):4.0%}  {g.closed_early.mean():4.0%}")
    x = L2["xs"]
    print(f"    all   {len(L2):4d}  {x.mean()*100:6.1f}%  {x.median()*100:6.1f}%  {np.mean(x > 0):4.0%}")
    # POST-HOC (after seeing L1 pass at 3bp and fail at tier): is it a thin-fund print artifact?
    print("  POST-HOC L1 liquidity floors, and a placebo matched on 20d $volume decile instead of vol (3bp):")
    for floor in (1e7, 5e7):
        m = NEW & (e.adv20[eq] >= floor)
        for cost in (3.0, "tier"):
            cb = B.cost_bps(cost, C.values.ravel(), e.adv20[eq].values.ravel()).reshape(C.shape) if isinstance(cost, str) else np.full(C.shape, cost)
            l = (on - 2 * cb / 1e4).where(m).mean(axis=1).fillna(0)
            print(f"    ADV >= ${floor/1e6:.0f}M @{str(cost):5s} {fmt3(l)}  funds/day {m.sum(axis=1)['2024':].mean():5.1f}")
    ad = np.log10(e.adv20[eq].where(ok))
    aedges = np.nanpercentile(ad.values, np.arange(10, 100, 10))
    adec = np.digitize(np.nan_to_num(ad.values, nan=0), aedges)
    pl2 = np.zeros((20, len(days)))
    for i in range(len(days)):
        nj = np.flatnonzero(NEWv[i]); oj = np.flatnonzero(OLDv[i])
        if not len(nj) or not len(oj):
            continue
        for sd in range(20):
            picks = []
            for j in nj:
                cand = oj[adec[i, oj] == adec[i, j]]
                cand = cand if len(cand) else oj
                picks.append(rng.choice(cand))
            pl2[sd, i] = np.nanmean(ONv[i, picks]) - 6e-4
    pl2 = pd.DataFrame(pl2.T, index=days)
    for k, a, b in PERIODS:
        sh = [B.stats(pl2[sd][a:b])[1] for sd in range(20)]
        print(f"    $vol-matched placebo {k}: Sharpe p50 {np.median(sh):5.2f} p90 {np.percentile(sh, 90):5.2f} vs real {B.stats(real[a:b])[1]:5.2f}")
    out["q3"] = {"l1": res, "L2": L2}


# ================================================================= POST-HOC diagnostics (Q2 F1 up-weight)
def run_q2_posthoc(c, s, out):
    """Added after seeing Q2: F1 (new, < 252 sessions) names carry the 2024-26 night edge.
    POST-HOC, so at most shadow: (a) matched up-weight placebo, (b) winsorised / top-name
    concentration, (c) the 63-252 age band alone, (d) by-year diff."""
    A = Ages(c)
    T, P = q2_tables(c, A)
    N = c["N"]
    print("\n== Q2 POST-HOC diagnostics (F1 = new listing, < 252 sessions)")
    for lab, X in {"2021-23": T[T.date <= "2023-12-31"], "2024-26": T[T.date >= "2024-01-01"]}.items():
        y = X.net_t.clip(-0.2, 0.2).values; fl = X.F1.values.astype(bool)
        b, t = cluster_t(y, fl, X.date.values)
        g = X[X.F1].groupby("sym").net_t.sum().sort_values(ascending=False)
        top = g.head(10).sum() / max(X[X.F1].net_t.sum(), 1e-9)
        print(f"  {lab}: winsorised +-20% diff {b*1e4:6.1f}bp t {t:5.2f} | flagged names {len(g)}, top-10 names = {top:.0%} of flagged P&L;"
              f" top: {', '.join(g.head(6).index)}")
    for y_, X in T.groupby(T.date.dt.year):
        fl = X.F1.values.astype(bool)
        if fl.sum() > 10:
            b, t = cluster_t(X.net_t.values, fl, X.date.values)
            print(f"    {y_}: n_flag {fl.sum():4d}  diff {b*1e4:6.1f}bp  t {t:5.2f}")
    band = T.F1 & ~T.F2
    for lab, X in {"2021-23": T[T.date <= "2023-12-31"], "2024-26": T[T.date >= "2024-01-01"]}.items():
        m = band[X.index].values
        b, t = cluster_t(X.net_t.values, m, X.date.values)
        print(f"  age 63-252 only {lab}: n {m.sum():4d} diff {b*1e4:6.1f}bp t {t:5.2f}")
    # matched up-weight placebo: up-weight 2x the same number of random unflagged same-decile names
    s.N = N; base = v7(s, "tier_hi").r
    b1, b2 = B.stats(base[:"2023-12-31"])[0], B.stats(base["2024-01-01":])[0]
    Nf = with_flags(N, T, "F1")
    s.N = Nf; real = v7(s, "tier_hi", tilt=upweight_tilt).r
    r1, r2 = B.stats(real[:"2023-12-31"])[0] - b1, B.stats(real["2024-01-01":])[0] - b2
    edges = np.nanpercentile(T.vol20, np.arange(10, 100, 10))
    g = []
    for seed in range(200):
        rng = np.random.default_rng(1000 + seed)
        Np = {}
        for d, nd in Nf.items():
            x = B.NightDay(**{k: getattr(nd, k) for k in nd.__dataclass_fields__})
            m = np.zeros(len(nd.syms), bool); dec = np.digitize(nd.vol20, edges)
            for j in np.flatnonzero(nd.flag):
                cand = np.flatnonzero(~nd.flag & ~m & (dec == dec[j]))
                cand = cand if len(cand) else np.flatnonzero(~nd.flag & ~m)
                if len(cand):
                    m[rng.choice(cand)] = True
            x.flag = m; Np[d] = x
        s.N = Np; df = v7(s, "tier_hi", tilt=upweight_tilt)
        g.append((B.stats(df.r[:"2023-12-31"])[0] - b1, B.stats(df.r["2024-01-01":])[0] - b2))
    g = np.array(g)
    print(f"  F1 UP-WEIGHT 2x tier_hi gain {r1*100:+5.2f} / {r2*100:+5.2f}pp; matched up-weight placebo p50 "
          f"{np.median(g[:,0])*100:+5.2f} / {np.median(g[:,1])*100:+5.2f}  p90 {np.percentile(g[:,0],90)*100:+5.2f} / "
          f"{np.percentile(g[:,1],90)*100:+5.2f}  real pct {np.mean(g[:,0] < r1):.0%} / {np.mean(g[:,1] < r2):.0%}")
    # EH dollars for the up-weight vs shipped (taxable V7 and Roth b1), tier_hi
    s.N = N; b_df = v7(s, "tier_hi"); s.N = Nf; u_df = v7(s, "tier_hi", tilt=upweight_tilt)
    eb, eu = B.stats(G.eh(b_df))[0], B.stats(G.eh(u_df))[0]
    from . import roth as RT
    base_kw = dict(tilt="live", weekend_scale=0.5, noise_on=False, conviction_w=0.0, margin_rate=0.0)
    s.N = N; rb = RT.replay(s, s.days, B.Params(night_cost="tier_hi", ibs_cost_bps=0.0, **base_kw), budget="night", noise_cap=1.5)
    s.N = Nf; ru = RT.replay(s, s.days, B.Params(night_cost="tier_hi", ibs_cost_bps=0.0, **{**base_kw, "tilt": upweight_tilt}), budget="night", noise_cap=1.5)
    print(f"  EH CAGR taxable V7 {eb*100:5.1f} -> {eu*100:5.1f};  Roth b1 full {B.stats(rb.r)[0]*100:5.1f} -> {B.stats(ru.r)[0]*100:5.1f}"
          f"  (halves {B.stats(rb.r[:'2023-12-31'])[0]*100:5.1f}/{B.stats(rb.r['2024-01-01':])[0]*100:5.1f} -> "
          f"{B.stats(ru.r[:'2023-12-31'])[0]*100:5.1f}/{B.stats(ru.r['2024-01-01':])[0]*100:5.1f})")
    s.N = N
    out["q2p"] = {"g": g, "real": (r1, r2)}


def main():
    from .validate import load_sim
    c = load_cache()
    s = load_sim(); s.N = c["N"]
    out = {}
    run_q1(c, s, out)
    run_q2(c, s, out)
    run_q2_posthoc(c, s, out)
    run_q3(c, out)
    pickle.dump(out, open(f"{SP}/nl_all_out.pkl", "wb"), protocol=4)


if __name__ == "__main__" and not ({"--cache", "--segments"} & set(sys.argv)):
    main()
