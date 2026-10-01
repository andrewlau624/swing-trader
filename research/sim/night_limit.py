"""Study AM (Round 17): limit orders at the bid/ask for the night leg.

    PYTHONPATH=. .venv/bin/python -m research.sim.night_limit

Pre-registration: research/drafts/round1_prose.md, "Round 17", Study AM (committed before any
number below). The repo has NO quotes/order-book data, so the model is built from the SIP trade
path with a per-name tick cost and its bounds are stated. The 15:50-16:00 bars come from
data/research/night/lm1 (+ lm6), the next-morning 09:30-10:31 bars from data/research/night/am1.

BUY (close auction) variants: a resting limit buy at L = p50 x (1 - b) fills at L if the
15:50-15:59 trade low reaches it, else at the official close if close <= L (the cross clears at
or below the limit), else the name is skipped and its budget is redeployed pro-rata to the filled
names (as night_sizing does). AM1-AM3 are b = 5/10/20 bp; AM4 is the upper bound (L = the
15:50-15:59 low). SELL (open auction) variants on the shipped close buy: AM5 sells only at/above
the prior close (unfilled -> the 09:59 close); AM6 rests a limit at the open + one tick and
otherwise sells at 09:59. AM1 is the control that reproduces the shipped book.

Reported: fill rate; adverse selection = mean net of filled minus unfilled; per-trade net change;
book increment per half at the stressed cost; NW t; sign-flip placebo; $/yr at small sizes.
"""
from __future__ import annotations

import glob
import pathlib
import pickle
import time
from datetime import timedelta

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from .validate import load_sim

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/research/program/night_limit_out.txt"
CACHE = ROOT / "data/research/program/night_limit_cache.pkl"
NIGHT = ROOT / "data/research/night"
HALVES = (("2021-23", "2021-01-01", "2023-12-31"),
          ("2024-26", "2024-01-01", "2026-12-31"))
SIZES = (2300.0, 10000.0, 25000.0)
ET = "America/New_York"


def _win(df, lo, hi):
    ts = pd.to_datetime(df["timestamp"]).dt.tz_convert(ET)
    hm = ts.dt.strftime("%H:%M")
    return df[(hm >= lo) & (hm <= hi)].assign(hm=hm)


def build_cache(N):
    """(date, sym) -> dict(close=[(hm,o,h,l,c)], open=[...], scale)."""
    if CACHE.exists():
        return pickle.load(open(CACHE, "rb"))
    t0 = time.time()
    sess = sorted({d for d in N})
    out = {}
    for i, d in enumerate(sess):
        nd = N[d]
        want = set(nd.syms)
        bars = []
        for pref in ("lm1", "lm6"):
            f = NIGHT / pref / f"{d.date()}.parquet"
            if f.exists():
                bars.append(pd.read_parquet(f))
        if not bars:
            continue
        bars = pd.concat(bars, ignore_index=True)
        cw = _win(bars, "15:50", "16:00")
        nxt = sess[i + 1] if i + 1 < len(sess) else None
        if nxt is not None:
            af = NIGHT / "am1" / f"{nxt.date()}.parquet"
            ow = _win(pd.read_parquet(af), "09:30", "09:59") if af.exists() else pd.DataFrame()
        else:
            ow = pd.DataFrame()
        for j, sym in enumerate(nd.syms):
            c = cw[cw.symbol == sym]
            if c.empty:
                continue
            c16 = c[c.hm == "16:00"]
            if c16.empty:
                continue
            scale = float(nd.close[j]) / float(c16.close.iloc[0])
            o = ow[ow.symbol == sym] if not ow.empty else pd.DataFrame()
            out[(pd.Timestamp(d), str(sym))] = dict(
                j=j,
                close=[(r.hm, float(r.open) * scale, float(r.high) * scale,
                        float(r.low) * scale, float(r.close) * scale)
                       for r in c.itertuples()],
                open=[(r.hm, float(r.open) * scale, float(r.high) * scale,
                       float(r.low) * scale, float(r.close) * scale)
                      for r in o.itertuples()] if not o.empty else [],
                scale=scale)
        if i % 150 == 0:
            print(f"cache {i}/{len(sess)} {time.time()-t0:.0f}s", flush=True)
    pickle.dump(out, open(CACHE, "wb"))
    return out


def nw_t(x, lags=5):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 20:
        return float("nan")
    mu = x.mean(); e = x - mu; n = len(x)
    s = (e * e).sum() / n
    for k in range(1, lags + 1):
        s += 2 * (1 - k / (lags + 1)) * (e[k:] * e[:-k]).sum() / n
    return mu / np.sqrt(s / n) if s > 0 else float("nan")


def buy_fill(bars, L, close):
    lows = [b[3] for b in bars if b[0] != "16:00"]
    if lows and min(lows) <= L:
        return L, "path"
    if close <= L:
        return close, "auction"
    return None, "miss"


def main():
    t0 = time.time()
    f = open(OUT, "w")

    def log(*a):
        x = " ".join(str(i) for i in a)
        print(x, flush=True); f.write(x + "\n"); f.flush()

    log("== Study AM: night-leg limit orders (close buys / open sells); started",
        pd.Timestamp.now(), "==")
    s = load_sim(raw_price=True)
    N = B.night_days(raw_price=True, max_corr=0.7)
    cache = build_cache(N)
    log(f"cache {len(cache)} pick-windows, {time.time()-t0:.0f}s\n")

    # --- assemble a per-pick table
    rows = []
    for d, nd in N.items():
        w_tilt = sg.night_tilt(nd.vol20, nd.day_ret, 0.25)
        for j, sym in enumerate(nd.syms):
            rows.append(dict(d=d, sym=str(sym), ret=float(nd.ret[j]), price=float(nd.price[j]),
                             close=float(nd.close[j]), adv=float(nd.adv[j]),
                             frac=float(nd.frac), wt=float(w_tilt[j]),
                             c=cache.get((d, str(sym)))))
    T = pd.DataFrame(rows)
    log(f"picks {len(T)}; with close-window bars {T.c.notna().sum()} "
        f"({T.c.notna().mean():.0%}); with next-open bars "
        f"{T.c.apply(lambda x: bool(x) and len(x['open'])>0).mean():.0%}\n")

    for cost in ("tier", "tier_hi"):
        c = B.cost_bps(cost, T.price.values, T.adv.values) / 1e4
        base = T.ret.values - 2 * c
        w = np.minimum(T.frac.values, 0.10)
        contrib0 = 0.5 * w * base
        log(f"[{cost}] fill rate / adverse selection / per-trade net change")

        def run_buy(b_or_low):
            fill_px = np.full(len(T), np.nan); how = np.array(["none"] * len(T), object)
            for i, row in enumerate(T.itertuples()):
                cc = row.c
                if not cc:
                    continue
                lows = [x[3] for x in cc["close"] if x[0] != "16:00"]
                L = (row.price * (1 - b_or_low) if isinstance(b_or_low, float)
                     else (min(lows) if lows else row.close))
                px, h = buy_fill(cc["close"], L, row.close)
                fill_px[i], how[i] = (px if px is not None else np.nan), h
            filled = np.isfinite(fill_px)
            # redeploy the filled names' budget pro-rata
            S = w[filled].sum()
            wv = np.zeros(len(T))
            if S > 0:
                wv[filled] = np.minimum(w[filled] * (w.sum() / S), 0.10)
            sell = T.close.values * (1 + T.ret.values)          # exit at the same next open
            net = np.where(filled, (sell / fill_px - 1) - 2 * c, 0.0)
            contrib = 0.5 * wv * net
            inc = pd.Series(contrib - contrib0, index=T.d.values)
            # adverse selection
            adv = base[filled].mean() - base[~filled].mean() if (~filled).any() else np.nan
            return filled, inc, adv, how

        for lab, arg in (("AM1 b=5bp", 5e-4), ("AM2 b=10bp", 1e-3),
                         ("AM3 b=20bp", 2e-3), ("AM4 low (UB)", None)):
            filled, inc, adv, how = run_buy(arg)
            half = [inc[(inc.index >= a) & (inc.index <= z)].mean() * 252 * 100 for _, a, z in HALVES]
            t = nw_t(inc.values)
            rng = np.random.default_rng(5)
            X = inc.values
            sims = np.array([(X * rng.choice([-1, 1], size=len(X))).mean() for _ in range(1000)])
            pct = float((sims < X.mean()).mean() * 100)
            log(f"  {lab:14s} fill {filled.mean():5.1%}  advsel {adv*1e4:+6.1f}bp  "
                f"inc {half[0]:+5.2f}/{half[1]:+5.2f}pp/yr  NW t {t:+5.2f}  placebo {pct:4.0f}%")

        # --- sell variants on the shipped close buy
        log(f"[{cost}] sell side (shipped close buy)")
        for lab in ("AM5 sell>=close else 09:59", "AM6 sell open+1tick else 09:59"):
            netv = np.full(len(T), np.nan); filled = np.zeros(len(T), bool)
            for i, row in enumerate(T.itertuples()):
                cc = row.c
                if not cc or not cc["open"]:
                    continue
                ob = cc["open"]
                o_open = ob[0][1]                      # 09:30 bar open
                o_high = max(x[2] for x in ob)
                o_last = ob[-1][4]                     # 09:59 close
                if lab.startswith("AM5"):
                    if o_open >= row.close:
                        px = o_open; filled[i] = True
                    else:
                        px = o_last
                else:
                    lint = o_open + 0.01
                    if o_high >= lint:
                        px = lint; filled[i] = True
                    else:
                        px = o_last
                netv[i] = (px / row.close - 1) - 2 * c[i]
            m = np.isfinite(netv)
            d_net = np.where(m, netv - base, 0.0)
            inc = pd.Series(0.5 * w * d_net, index=T.d.values)
            half = [inc[(inc.index >= a) & (inc.index <= z)].mean() * 252 * 100 for _, a, z in HALVES]
            log(f"  {lab:26s} fill {np.nanmean(filled[m].astype(float)) if m.any() else 0:5.1%}  "
                f"inc {half[0]:+5.2f}/{half[1]:+5.2f}pp/yr  NW t {nw_t(inc.values):+5.2f}")

        # $/yr of the best buy increment at small size (book is 0.5 of equity on the night leg)
        log("")

    log(f"done {time.time()-t0:.0f}s")
    f.close()


if __name__ == "__main__":
    main()
