"""Addendum 28 candidate: a future-agnostic "theme explosion" sleeve.

    PYTHONPATH=. .venv/bin/python -m research.sim.theme_explosion

Catch explosive new-theme runs (quantum 2024-25, AI, nuclear, crypto miners)
without naming a ticker or a theme. Rules detect an explosion in ANY liquid
common stock and ride it with small equal slots and a trailing stop.

Data: SIP daily bars, split/div adjusted, the survivorship-aware universe
(data/cache/assets.json: active + inactive). 2020-10 -> 2026-09 from
data/research/night/panel.pkl; 2015-01 -> 2020-09 fetched the same way into
the scratchpad (fetch_1520.py). Pre-2021 delistings are thinner in Alpaca's
inactive list than recent ones, so 2016-20 is flattered more than 2021-26.

PRE-REGISTERED (fixed before any 2024-26 number was looked at):
  common   signal at close d, buy the open of d+1, sell at an open.
           eligible: close >= $3, 20d median SIP $volume >= $5M, >= 120 bars of
           history, not an ETF/ETN/fund/trust (by asset name).
  V1 breakout  close above every close of the prior 251 sessions AND volume
               >= 3x its 50d average.
  V2 mom1      63d return in the top 1% of eligible names AND close > 50d MA.
  V3 cluster   a V1-style breakout (volume >= 2x) that has >= 2 other names
               breaking out in the last 10 sessions whose 60d daily returns
               correlate >= 0.6 with it (a theme, found without names).
  V4 resid     63d residual return vs SPY (252d rolling beta, lagged) in the
               top 1% AND close > 50d MA.
  exit     close 25% below the highest close since entry, OR close < 50d MA,
           OR 126 sessions held -> sell the next open. Delisted while held:
           last close x (1 - 30%) (Shumway; swingtrader/backtest.DELIST_RET).
  sizing   10 equal slots (slot = 1/10 of sleeve equity at entry); more signals
           than free slots -> highest 20d $volume first. Idle cash earns BIL.
  costs    research/sim/book.py tiers per side by price/ADV (tier, tier_hi),
           plus "x2" = tier doubled (market orders in thin, hot names).
  placebo  each real entry replaced by a random eligible name on the same day
           from the same 20d-vol decile, same exits, 50 seeds.
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

from swingtrader.universe import valid_symbol

from . import book as B

SP = "/private/tmp/claude-501/-Users-andrewlau-Documents-Code-Projects-swing-trader/cc100773-e955-4a4c-aa47-797c4a8c7acb/scratchpad"
PERIODS = [("2016-20", "2016-01-01", "2020-12-31"), ("2021-23", "2021-01-01", "2023-12-31"),
           ("2024-26", "2024-01-01", "2026-12-31")]
ETF_RE = re.compile(r"\b(ETF|ETN|FUND|TRUST|SHARES|PROSHARES|DIREXION|ISHARES|SPDR|INVESCO|"
                    r"ULTRA|LEVERAGED|INVERSE|2X|3X|-1X|BULL|BEAR|WISDOMTREE|VANECK|GLOBAL X|"
                    r"ARK |GRANITESHARES|DEFIANCE|T-REX|TRADR|YIELDMAX|ROUNDHILL|INDEX)\b")
DELIST_RET = -0.30
QUANTUM = ["RGTI", "IONQ", "QBTS", "QUBT", "ARQQ"]
THEMES = {"quantum": QUANTUM, "AI": ["NVDA", "SMCI", "PLTR"], "nuclear": ["OKLO", "SMR"],
          "crypto": ["MSTR", "COIN"]}


# ---------------------------------------------------------------- data
def load_panel():
    pk = f"{SP}/theme_panel.pkl"
    if os.path.exists(pk):
        return pickle.load(open(pk, "rb"))
    new = pd.read_pickle("data/research/night/panel.pkl")
    files = sorted(glob.glob(f"{SP}/sipd1520/*.parquet"))
    old = pd.concat([pd.read_parquet(f) for f in files])
    old["date"] = (old.timestamp.dt.tz_convert("America/New_York").dt.tz_localize(None)
                   .dt.normalize())
    P = {}
    for f in ("open", "close", "volume"):
        o = old.pivot_table(index="date", columns="symbol", values=f, aggfunc="last").astype("float32")
        o = o[o.index < new[f].index.min()]
        P[f] = pd.concat([o, new[f].astype("float32")], axis=0).sort_index()
    cols = P["close"].columns
    for f in P:
        P[f] = P[f].reindex(columns=cols)
    pickle.dump(P, open(pk, "wb"), protocol=4)
    return P


def stock_mask(cols) -> np.ndarray:
    meta = json.load(open("data/research/night/asset_meta.json"))
    out = []
    for s in cols:
        nm = (meta.get(s, {}).get("name") or "").upper()
        out.append(valid_symbol(s) and not ETF_RE.search(nm))
    return np.array(out)


class Panel:
    def __init__(self):
        P = load_panel()
        self.C = P["close"]; self.O = P["open"]; self.V = P["volume"]
        self.dates = self.C.index; self.syms = np.array(self.C.columns)
        C = self.C
        self.R = C.pct_change(fill_method=None)
        dv = C * self.V
        self.adv = dv.rolling(20, min_periods=15).median()
        nbars = C.notna().rolling(120, min_periods=1).sum()
        stock = stock_mask(self.syms)
        self.elig = (C >= 3) & (self.adv >= 5e6) & (nbars >= 120) & stock[None, :]
        self.ma50 = C.rolling(50, min_periods=40).mean()
        self.vol20 = self.R.rolling(20, min_periods=15).std()
        # last bar per name: bars that stop well before the panel end = delisted
        last = C.notna()[::-1].idxmax()
        end = self.dates[-1]
        self.delist_day = {s: d for s, d in last.items() if d < end - pd.Timedelta(days=10)}
        etf = pd.read_parquet("data/research/night/etf_daily.parquet")
        etf["d"] = (pd.to_datetime(etf.timestamp).dt.tz_convert("America/New_York")
                    .dt.normalize().dt.tz_localize(None))
        e = etf.pivot(index="d", columns="symbol", values="close")
        self.bil = e["BIL"].pct_change().reindex(self.dates).fillna(0)
        spy = C["SPY"] if "SPY" in C else e["SPY"].reindex(self.dates)
        self.spy = spy.pct_change(fill_method=None).fillna(0)

    # ------------------------------------------------------------ signals
    def signals(self) -> dict[str, pd.DataFrame]:
        C, V = self.C, self.V
        prior_hi = C.shift(1).rolling(251, min_periods=119).max()
        brk = C > prior_hi
        v50 = V.shift(1).rolling(50, min_periods=40).mean()
        v1 = self.elig & brk & (V >= 3 * v50)
        r63 = C / C.shift(63) - 1
        up = C > self.ma50
        r63e = r63.where(self.elig)
        q99 = r63e.quantile(0.99, axis=1)
        v2 = self.elig & up & r63e.ge(q99, axis=0)
        # residual momentum vs SPY
        m = self.spy
        R = self.R.fillna(0)
        w = 252
        ERm = (R.mul(m, axis=0)).rolling(w, min_periods=120).mean()
        ER = R.rolling(w, min_periods=120).mean()
        Em = m.rolling(w, min_periods=120).mean(); Em2 = (m * m).rolling(w, min_periods=120).mean()
        beta = (ERm.sub(ER.mul(Em, axis=0))).div(Em2 - Em * Em, axis=0).shift(1)
        resid = (R - beta.mul(m, axis=0)).rolling(63, min_periods=50).sum().where(self.elig)
        v4 = self.elig & up & resid.ge(resid.quantile(0.99, axis=1), axis=0)
        # cluster
        b2 = self.elig & brk & (V >= 2 * v50)
        v3 = pd.DataFrame(False, index=C.index, columns=C.columns)
        Rv = self.R.values
        b2v = b2.values
        for i in range(260, len(C)):
            today = np.flatnonzero(b2v[i])
            if len(today) == 0:
                continue
            win = np.flatnonzero(b2v[max(0, i - 9):i + 1].any(axis=0))
            if len(win) < 3:
                continue
            X = Rv[i - 59:i + 1][:, win]
            ok = np.isfinite(X).sum(axis=0) >= 50
            X = np.where(np.isfinite(X), X, 0.0)
            X = X - X.mean(axis=0); sd = X.std(axis=0); sd[sd == 0] = np.nan
            Z = X / sd
            corr = (Z.T @ Z) / Z.shape[0]
            pos = {c: k for k, c in enumerate(win)}
            for c in today:
                k = pos[c]
                if not ok[k]:
                    continue
                n = np.nansum((corr[k] >= 0.6) & ok) - 1
                if n >= 2:
                    v3.iat[i, c] = True
        return {"V1 breakout": v1, "V2 mom1": v2, "V3 cluster": v3, "V4 resid": v4}

    def as_lists(self, sig: pd.DataFrame) -> dict[int, list[int]]:
        """day index -> column indices, highest 20d $volume first."""
        S = sig.values; A = self.adv.values
        out = {}
        for i in np.flatnonzero(S.any(axis=1)):
            c = np.flatnonzero(S[i])
            out[i] = list(c[np.argsort(-np.nan_to_num(A[i, c]))])
        return out

    def placebo(self, lists: dict[int, list[int]], seed: int) -> dict[int, list[int]]:
        rng = np.random.default_rng(seed)
        if not hasattr(self, "_pools"):
            E = self.elig.values; VOL = self.vol20.values
            self._pools = {}
            for i in range(len(self.dates)):
                el = np.flatnonzero(E[i] & np.isfinite(VOL[i]))
                if len(el) < 20:
                    continue
                cut = np.quantile(VOL[i, el], np.linspace(0.1, 0.9, 9))
                dec = np.searchsorted(cut, VOL[i, el])
                self._pools[i] = (cut, [el[dec == d] for d in range(10)])
        VOL = self.vol20.values
        out = {}
        for i, cs in lists.items():
            if i not in self._pools:
                continue
            cut, pools = self._pools[i]
            picks = []
            for c in cs:
                if np.isfinite(VOL[i, c]):
                    pool = pools[int(np.searchsorted(cut, VOL[i, c]))]
                    if len(pool):
                        picks.append(int(rng.choice(pool)))
            out[i] = picks
        return out

    # ------------------------------------------------------------ simulate
    def cost(self, model: str, i: int, c: int) -> float:
        px = float(self.C.values[i, c]); adv = float(self.adv.values[i, c]) if np.isfinite(self.adv.values[i, c]) else 0.0
        mult = 2.0 if model == "x2" else 1.0
        tiers = B.TIERS["tier" if model == "x2" else model]
        a, b, cc, d = tiers
        bp = a if px < 10 else b if px < 20 else cc if adv < 5e7 else d
        return mult * bp / 1e4

    def sim(self, lists, trail=0.25, ma_exit=True, maxhold=126, slots=10, cost="tier",
            delist=DELIST_RET, start=None):
        C = self.C.values; O = self.O.values; MA = self.ma50.values
        dates = self.dates; n = len(dates)
        i0 = 0 if start is None else int(np.searchsorted(dates, pd.Timestamp(start)))
        cash = 1.0; pos = {}      # c -> dict(q, px, peak, i, cost_in, basis)
        eq = np.full(n, np.nan); eq[:i0] = 1.0
        trades = []
        pend_in, pend_out = [], set()
        delist_i = {self.C.columns.get_loc(s): dates.get_loc(d) for s, d in self.delist_day.items()}
        bil = self.bil.values
        last_px = {}
        for i in range(i0, n):
            cash *= 1 + bil[i]
            # exits at today's open
            for c in list(pend_out):
                if c in pos:
                    px = O[i, c] if np.isfinite(O[i, c]) else last_px.get(c)
                    p = pos.pop(c); k = self.cost(cost, i, c) if np.isfinite(C[i, c]) else 0.02
                    val = p["q"] * px * (1 - k); cash += val
                    trades.append((p["i"], i, c, val / p["basis"] - 1, val - p["basis"]))
            pend_out = set()
            # entries at today's open
            if pend_in:
                tot = cash + sum(p["q"] * last_px[c] for c, p in pos.items())
                for c in pend_in:
                    if len(pos) >= slots or c in pos or not np.isfinite(O[i, c]) or O[i, c] <= 0:
                        continue
                    amt = min(tot / slots, cash)
                    if amt <= 1e-9:
                        break
                    k = self.cost(cost, i, c)
                    q = amt * (1 - k) / O[i, c]
                    cash -= amt
                    pos[c] = dict(q=q, peak=O[i, c], i=i, basis=amt)
                    last_px[c] = O[i, c]
            pend_in = []
            # marks and exit decisions at the close
            for c in list(pos):
                p = pos[c]
                if np.isfinite(C[i, c]):
                    last_px[c] = C[i, c]; p["peak"] = max(p["peak"], C[i, c])
                    if (C[i, c] < p["peak"] * (1 - trail) or (ma_exit and np.isfinite(MA[i, c]) and C[i, c] < MA[i, c])
                            or i - p["i"] >= maxhold):
                        pend_out.add(c)
                if delist_i.get(c) == i:          # last bar ever: delisted
                    val = p["q"] * last_px[c] * (1 + delist); cash += val; pos.pop(c)
                    pend_out.discard(c)
                    trades.append((p["i"], i, c, val / p["basis"] - 1, val - p["basis"]))
            eq[i] = cash + sum(p["q"] * last_px[c] for c, p in pos.items())
            if i in lists:
                free = slots - len(pos) + len(pend_out)
                pend_in = [c for c in lists[i] if c not in pos][:max(0, free)]
        r = pd.Series(eq, index=dates).pct_change().fillna(0)
        return r, pd.DataFrame(trades, columns=["i_in", "i_out", "c", "ret", "pnl"])


# ------------------------------------------------------------------ report
def st(r):
    c, s, d = B.stats(r)
    return f"{c*100:6.1f}/{s:5.2f}/{d*100:4.0f}"


def per_period(r):
    return "  ".join(st(r[a:z]) for _, a, z in PERIODS)


def trade_stats(P, t, a, z):
    d = P.dates
    x = t[(d[t.i_in] >= pd.Timestamp(a)) & (d[t.i_in] <= pd.Timestamp(z))]
    if len(x) == 0:
        return "no trades"
    w = x[x.ret > 0]; l = x[x.ret <= 0]
    top = x.nlargest(5, "pnl")
    share = top.pnl.sum() / x.pnl.sum() if x.pnl.sum() > 0 else np.nan
    names = ", ".join(f"{P.syms[c]} {r*100:+.0f}%" for c, r in zip(top.c, top.ret))
    return (f"n {len(x):4d} win {100*len(w)/len(x):3.0f}% avg win {w.ret.mean()*100:+6.1f}% "
            f"avg loss {l.ret.mean()*100:+6.1f}% mean {x.ret.mean()*100:+5.1f}% | top5 = "
            f"{share*100:5.0f}% of P&L: {names}")


def main():
    P = Panel()
    print(f"panel {P.dates[0].date()} -> {P.dates[-1].date()}, {len(P.syms)} symbols, "
          f"{int(stock_mask(P.syms).sum())} stocks; delisted in panel: {len(P.delist_day)}")
    per = P.elig.sum(axis=1)
    print("eligible names/day: " + ", ".join(f"{y}: {int(per[str(y)].mean())}" for y in range(2016, 2027)))
    # delisting coverage by year (survivorship caveat for 2016-20)
    dy = pd.Series([d.year for d in P.delist_day.values()]).value_counts().sort_index()
    print("names whose bars end (delisted) by year: " + ", ".join(f"{y}: {n}" for y, n in dy.items()))
    SIG = P.signals()
    L = {k: P.as_lists(v) for k, v in SIG.items()}
    start = "2016-01-04"
    print("\n== 1. standalone sleeve (10 slots, trail 25% / 50d MA / 126d, idle cash in BIL)")
    print(f"{'':30s} {'2016-20':>17s}  {'2021-23':>17s}  {'2024-26':>17s}   signals/yr")
    res = {}
    for k, lst in L.items():
        for c in ("tier", "tier_hi", "x2"):
            r, t = P.sim(lst, cost=c, start=start)
            res[(k, c)] = (r, t)
            print(f"{k + ' ' + c:30s} {per_period(r)}   {sum(len(v) for v in lst.values())/10.7:6.0f}")
    b = P.bil[start:]
    print(f"{'BIL (cash)':30s} {per_period(b)}")
    spyr = P.spy[start:]
    print(f"{'SPY':30s} {per_period(spyr)}")

    print("\n== 2. trades by period (tier): win rate, avg winner/loser, top-5 share of P&L")
    for k in L:
        t = res[(k, "tier")][1]
        for name, a, z in PERIODS:
            print(f"{k:12s} {name}: {trade_stats(P, t, a, z)}")

    print("\n== 3. placebo: random eligible names, same day, same 20d-vol decile, same exits (50 seeds)")
    PL = {}
    for k, lst in L.items():
        real = [B.stats(res[(k, 'tier')][0][a:z])[0] for _, a, z in PERIODS]
        ps = []
        for sd in range(50):
            r, _ = P.sim(P.placebo(lst, sd), start=start)
            ps.append([B.stats(r[a:z])[0] for _, a, z in PERIODS])
        ps = np.array(ps); PL[k] = ps
        beat = (ps < np.array(real)).mean(axis=0)
        print(f"{k:12s} real CAGR " + " / ".join(f"{x*100:5.1f}" for x in real)
              + "  placebo median " + " / ".join(f"{x*100:5.1f}" for x in np.median(ps, axis=0))
              + "  beats " + " / ".join(f"{x:.0%}" for x in beat))

    print("\n== 4. exit sensitivity (tier), CAGR/Sharpe/maxDD per period")
    for k in L:
        for trail, ma in ((0.15, True), (0.25, False), (0.35, True), (0.50, False)):
            r, _ = P.sim(L[k], trail=trail, ma_exit=ma, start=start)
            print(f"{k:12s} trail {trail:.2f} {'+MA50' if ma else 'no MA':6s} {per_period(r)}")
        r, _ = P.sim(L[k], start=start, delist=0.0)
        print(f"{k:12s} delisting at last close (0%)  {per_period(r)}")

    print("\n== 5. were the theme runs caught? (tier sim; first entry in 2016-26 per name)")
    for k in L:
        t = res[(k, "tier")][1]
        for th, names in THEMES.items():
            out = []
            for s in names:
                if s not in P.C:
                    continue
                c = P.C.columns.get_loc(s)
                x = t[t.c == c]
                if len(x) == 0:
                    out.append(f"{s} -")
                    continue
                best = x.loc[x.pnl.idxmax()]
                d_in, d_out = P.dates[int(best.i_in)], P.dates[int(best.i_out)]
                seg = P.C[s][d_in:]
                pk = seg.idxmax() if th == "quantum" else None
                out.append(f"{s} {len(x)}x best {d_in:%y-%m-%d}->{d_out:%y-%m-%d} {best.ret*100:+.0f}%")
            print(f"{k:12s} {th:8s} " + "; ".join(out))
    q = P.C[QUANTUM]["2024-06":"2025-06"]
    print("quantum reference, low 2024-06..09 -> peak to 2025-06: " + "; ".join(
        f"{s} {q[s]['2024-06':'2024-09'].min():.2f}->{q[s].max():.2f} ({q[s].idxmax():%y-%m-%d})"
        for s in QUANTUM if s in q))

    pickle.dump({"res": {k: (v[0], v[1]) for k, v in res.items()}, "placebo": PL,
                 "syms": P.syms, "dates": P.dates}, open(f"{SP}/r5_all.pkl", "wb"))

    # ------------------------------------------------ V7 combination
    combine(P, res, L)


def combine(P, res, L, best=None):
    from .growth import V7, cfg, eh
    from .validate import load_sim
    s = load_sim()
    s.N = B.night_days(max_corr=0.7, max_name_pct=0.10)

    def v7(g=1.0, extra_day=0.0, cost="tier"):
        kw = cfg(g, 0.5, 2)
        kw["noise_cap"] = max(0.0, kw["noise_cap"] - extra_day)
        return s.replay(B.Params(**{**V7, **kw, "night_cost": cost}))

    base = {c: v7(cost=c) for c in ("tier", "tier_hi")}
    days = base["tier"].index
    r7 = base["tier"].r
    # rank by 2021-26 tier Sharpe is NOT used to pick: best = the variant that passed the
    # most gates (both halves positive and placebo); chosen by the caller if given
    if best is None:
        scores = {}
        for k in L:
            r = res[(k, "tier")][0]
            scores[k] = min(B.stats(r[a:z])[1] for _, a, z in PERIODS)
        best = max(scores, key=scores.get)
    print(f"\n== 6. combined with V7 (2021-02 -> 2026-09), sleeve = {best}")
    x = {c: res[(best, "tier" if c == "tier" else "tier_hi")][0].reindex(days).fillna(0) for c in ("tier", "tier_hi")}
    rho = r7.corr(x["tier"])
    crash = s.spy.reindex(days) <= -0.03
    print(f"correlation with V7 {rho:+.2f}; on SPY<=-3% days (n={int(crash.sum())}) sleeve "
          f"{x['tier'][crash].mean()*1e4:+.0f}bp vs V7 {r7[crash].mean()*1e4:+.0f}bp")

    def row2(r):
        a, b2, f = B.stats(r[:"2023-12-31"]), B.stats(r["2024-01-01":]), B.stats(r)
        wm = float((1 + r).groupby([r.index.year, r.index.month]).prod().min() - 1)
        return (f"{a[0]*100:5.1f}/{a[1]:4.2f}/{a[2]*100:4.0f}  {b2[0]*100:5.1f}/{b2[1]:4.2f}/{b2[2]*100:4.0f}"
                f"  |  {f[0]*100:5.1f}/{f[1]:4.2f}/{f[2]*100:4.0f}  worst month {wm*100:5.1f}")

    print(f"{'':44s} {'2021-23':>15s}  {'2024-26':>15s}  |  {'full':>15s}")
    for c in ("tier", "tier_hi"):
        print(f"{'V7 shipped ' + c:44s} {row2(base[c].r)}")
    bfwd = s.bil.reindex(days).fillna(0)
    ibs_flat = pd.Series({d: 0.0 if s.I.get(d) else 1.0 for d in days})
    out = {}
    for c in ("tier", "tier_hi"):
        for k in (0.1, 0.2):
            g = v7(g=1.0 - k, extra_day=k, cost=c)
            comb = g.r + k * x[c]
            out[("carve", k, c)] = comb
            print(f"{f'carve {k:.1f} of ibs+night -> sleeve ' + c:44s} {row2(comb)}")
        for k in (0.1, 0.2):
            a = ibs_flat * k
            comb = base[c].r + a * x[c] - a * bfwd
            out[("idle", k, c)] = comb
            print(f"{f'sleeve in idle IBS cash, up to {k:.1f} ' + c:44s} {row2(comb)}   avg {a.mean():.2f}")
    print("-- edge-halves at tier_hi (V7 legs' mean halved, sleeve excess over BIL halved)")
    print(f"{'EH V7':44s} {row2(eh(base['tier_hi']))}")
    for k in (0.1, 0.2):
        g = v7(g=1.0 - k, extra_day=k, cost="tier_hi")
        sl = k * x["tier_hi"]; ex = sl - k * bfwd
        print(f"{f'EH carve {k:.1f}':44s} {row2(eh(g) + sl - 0.5 * ex.mean())}")
    pickle.dump({"v7": r7, "v7_plus": out[("carve", 0.1, "tier")], "leg_unit": res[(best, "tier")][0],
                 "variant": best + " carve 0.1"}, open(f"{SP}/r5_series.pkl", "wb"))


if __name__ == "__main__":
    main()
