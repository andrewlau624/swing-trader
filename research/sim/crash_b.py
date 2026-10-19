"""Study CRASH-B (N 1025): fixed-budget rolled SPY tail puts at far-side fills. Pre-reg in round1_prose.md.
Usage: .venv/bin/python -m research.sim.crash_b [--pull]   cache data/research/crash_b/ ; out data/research/program/crash_b_out.txt"""
import sys, pathlib, numpy as np, pandas as pd
from math import log, sqrt
from scipy.stats import norm
D = pathlib.Path("data/research/crash_b"); D.mkdir(parents=True, exist_ok=True)
OUT = pathlib.Path("data/research/program/crash_b_out.txt")
SECID = 109820; B = 0.001; YEARS = range(2005, 2026)
OTM, OTM2, TENOR, DELTA_TRIG, EXIT_DTE = 0.90, 0.75, 90, -0.70, 21
LOG = []
def say(s=""):
    print(s); LOG.append(s)

def pull():
    from research.sim.borrow_xs import conn
    db = conn()
    for y in YEARS:
        f = D / f"puts_{y}.parquet"
        if not f.exists():
            df = db.raw_sql(f"""select date, exdate, strike_price/1000.0 as k, best_bid as bid, best_offer as ask,
              delta, impl_volatility as iv, open_interest as oi, volume from optionm.opprcd{y}
              where secid={SECID} and cp_flag='P' and exdate-date between 15 and 130 and best_offer>0""")
            df["date"] = pd.to_datetime(df["date"]); df["exdate"] = pd.to_datetime(df["exdate"]); df.to_parquet(f)
        g = D / f"und_{y}.parquet"
        if not g.exists():
            u = db.raw_sql(f"select date, close, return as ret from optionm.secprd{y} where secid={SECID}")
            u["date"] = pd.to_datetime(u["date"]); u.to_parquet(g)
        print("pulled", y, flush=True)

def load():
    P = pd.concat([pd.read_parquet(D / f"puts_{y}.parquet") for y in YEARS], ignore_index=True)
    U = pd.concat([pd.read_parquet(D / f"und_{y}.parquet") for y in YEARS]).sort_values("date").set_index("date")
    for c in ("k","bid","ask","delta","iv","oi","volume"): P[c] = pd.to_numeric(P[c], errors="coerce").astype(float)
    U["close"] = U["close"].astype(float); U["ret"] = pd.to_numeric(U["ret"], errors="coerce").astype(float)
    P["dte"] = (P["exdate"] - P["date"]).dt.days
    return P, U

def bs_delta(S, K, T, iv):
    d1 = (np.log(S / K) + 0.5 * iv ** 2 * T) / (iv * np.sqrt(T)); return norm.cdf(d1) - 1

class Book:
    """Index chain rows by (date) for fast lookup."""
    def __init__(s, P, U):
        s.U = U; s.G = {d: g for d, g in P.groupby("date")}
    def pick(s, d, target_k, tenor=TENOR):
        g = s.G.get(d)
        if g is None: return None
        g = g[(g.dte >= 60) & (g.dte <= 120)]
        g = g[(g.bid > 0) | (g.ask > 0)]
        if g.empty: return None
        ex = g.loc[(g.dte - tenor).abs().idxmin(), "exdate"]
        g = g[g.exdate == ex]
        r = g.loc[(g.k - target_k).abs().idxmin()]
        return r
    def mark(s, d, ex, k, side):
        """bid (long) or ask (short buyback) for contract; None if missing"""
        g = s.G.get(d)
        if g is None: return None
        r = g[(g.exdate == ex) & (np.isclose(g.k, k))]
        if r.empty: return None
        r = r.iloc[0]; return (r.bid, r.delta, r.iv, r.dte) if side == "long" else (r.ask, r.delta, r.iv, r.dte)

def iv_series(bk, dates):
    out = {}
    for d in dates:
        S = bk.U.close.get(d)
        r = bk.pick(d, OTM * S) if S else None
        out[d] = r.iv if r is not None and r.iv == r.iv and r.iv > 0 else np.nan
    return pd.Series(out)

def run(bk, mode, gate=None, exit_rule="delta", gate_series=None):
    """mode 'put' or 'spr'. Per-unit-of-account fractional contracts; account-fraction P&L (budget B of a notional account of 1.0, non-compounding)
    returns daily put-book equity curve (cum P&L in account units) and spend per day."""
    U = bk.U; dates = U.index; month_first = set(pd.Series(dates).groupby([dates.year, dates.month]).min().values)
    pos = []; cash = 0.0; eq = {}; spent = {}; trades = []
    sma = U.close.rolling(200).mean()
    for d in dates:
        S = U.close[d]
        # exits
        keep = []
        for p in pos:
            m = bk.mark(d, p["ex"], p["k"], "long")
            m2 = bk.mark(d, p["ex"], p["k2"], "short") if mode == "spr" else (0, 0, 0, 0)
            dte = (p["ex"] - d).days
            if m is None or m2 is None:
                keep.append(p); continue
            dlt = m[1] if m[1] == m[1] and m[1] is not None else bs_delta(S, p["k"], max(dte, 1) / 365, m[2] if m[2] == m[2] else 0.2)
            trig = (dlt <= DELTA_TRIG if exit_rule == "delta" else False) or dte <= EXIT_DTE
            if trig:
                val = (m[0] - (m2[0] if mode == "spr" else 0)) * p["n"]
                cash += val; trades.append(dict(buy=p["d0"], sell=d, cost=p["cost"], proceeds=val, S0=p["S0"], S1=S, mult=val / p["cost"] if p["cost"] else np.nan))
            else: keep.append(p)
        pos = keep
        # entry
        if d in month_first:
            ok = True
            if gate == "iv":
                h = gate_series.loc[:d].dropna().iloc[-253:-1] if gate_series is not None else None
                cur = gate_series.get(d, np.nan)
                ok = h is not None and len(h) >= 200 and cur == cur and cur <= h.quantile(1 / 3)
            elif gate == "sma":
                ok = sma[d] == sma[d] and S < sma[d]
            if ok:
                r = bk.pick(d, OTM * S)
                if r is not None:
                    cost = r.ask; k2 = None
                    if mode == "spr":
                        g = bk.G[d]; g = g[g.exdate == r.exdate]
                        r2 = g.loc[(g.k - OTM2 * S).abs().idxmin()]
                        if r2.bid > 0 and r2.k < r.k: cost = r.ask - r2.bid; k2 = r2.k
                        else: cost = None
                    if cost and cost > 0:
                        n = B / cost * S * 0 + B / cost  # contracts-units: spend B (account units 1.0 = account) per month
                        cash -= B; spent[d] = B
                        pos.append(dict(d0=d, ex=r.exdate, k=r.k, k2=k2, n=n, cost=B, S0=S))
        # mark
        mtm = 0.0
        for p in pos:
            m = bk.mark(d, p["ex"], p["k"], "long"); m2 = bk.mark(d, p["ex"], p["k2"], "short") if mode == "spr" else (0, 0, 0, 0)
            if m is not None and m2 is not None: p["last"] = (m[0] - (m2[0] if mode == "spr" else 0)) * p["n"]
            mtm += p.get("last", 0.0)
        eq[d] = cash + mtm
    return pd.Series(eq), pd.Series(spent), pd.DataFrame(trades)

def yearly(eq, spent):
    e = eq.copy(); e.index = pd.to_datetime(e.index)
    ye = e.groupby(e.index.year).last(); pnl = ye.diff(); pnl.iloc[0] = ye.iloc[0]
    sp = pd.Series(spent); sp.index = pd.to_datetime(sp.index); sp = sp.groupby(sp.index.year).sum()
    return pd.DataFrame({"net_pnl": pnl, "spent": sp}).fillna(0)

def combined(U, eq):
    """100% SPY total return; put book funded by selling SPY. W0=1; book P&L in account units scales with W (monthly budget B*W)."""
    r = U.ret.fillna(0); d = U.index
    # approximate: put P&L per unit budget scales with wealth -> compound the book returns on current wealth
    dp = eq.diff().fillna(0)  # per-account-unit change for budget fraction B of unit wealth
    W = 1.0; curve = []
    for t in d:
        W *= 1 + r[t]
        W += dp.get(t, 0) * W  # puts P&L (incl. -B premium on buy days) scaled by wealth
        curve.append(W)
    c = pd.Series(curve, index=d); return c

def stats(c):
    yrs = (c.index[-1] - c.index[0]).days / 365.25
    return c.iloc[-1], c.iloc[-1] ** (1 / yrs) - 1, (c / c.cummax() - 1).min()

def model_1929():
    """MODEL (not a backtest): 1925-35 CRSP vwretx index, BS puts at sigma = k x RV20, k = measured put-IV/RV20 ratio in 2008/2020 crash windows,
    far-side half-spread h measured on 2008 10%-OTM 90d puts. Same rules/budget/monetization as primary PUT10. No data before 1996 exists for options."""
    from research.sim.borrow_xs import conn
    P, U = load(); iv = pd.read_pickle(D / "iv.pkl").astype(float)
    rv = U.ret.rolling(20).std() * np.sqrt(252); rat = (iv / rv).dropna()
    wins = {"2008-09..2009-03": ("2008-09-01", "2009-03-31"), "2020-02..2020-04": ("2020-02-15", "2020-04-30")}
    kk = {n: float(rat.loc[a:b].median()) for n, (a, b) in wins.items()}
    k = float(np.mean(list(kk.values()))); kall = float(rat.median())
    # half-spread fraction (ask-bid)/(ask+bid) of the 90d 90%-strike put on first-of-month dates 2008
    bk = Book(P, U); hs = []
    for d in U.loc["2008-01-01":"2008-12-31"].index:
        r = bk.pick(d, OTM * U.close[d])
        if r is not None and r.bid > 0: hs.append((r.ask - r.bid) / (r.ask + r.bid))
    h = float(np.median(hs))
    say("\n== MODEL 1929-32 (BS on CRSP vwretx; NOT a backtest: no 1929 option prices exist)")
    say(f"IV/RV20 ratio (10%OTM 90d put IV / 20d realized): " + ", ".join(f"{n} {v:.2f}" for n, v in kk.items()) + f"; used k={k:.2f}; all-days median {kall:.2f}; far-side half-spread h={h*100:.1f}% of mid (2008 median)")
    db = conn(); d = db.raw_sql("select date, vwretx from crsp.dsi where date between '1926-01-01' and '1935-12-31' order by date")
    d["date"] = pd.to_datetime(d["date"]); r = pd.to_numeric(d.vwretx, errors="coerce").fillna(0).astype(float).values
    idx = pd.Series(np.cumprod(1 + r), index=d.date); rvm = pd.Series(r, index=d.date).rolling(20).std() * np.sqrt(252)
    pk = idx.loc["1929-01-01":"1930-12-31"].idxmax(); tr = idx.loc[pk:"1933-12-31"].idxmin()
    say(f"index peak {pk.date()} trough {tr.date()}: {(idx[tr]/idx[pk]-1)*100:.1f}% (price only); first leg to 1929-11-13: {(idx.loc['1929-11-13']/idx[pk]-1)*100:.1f}%")
    rf = 0.03
    def px(S, K, T, sg):
        d1 = (np.log(S / K) + (rf + .5 * sg ** 2) * T) / (sg * np.sqrt(T)); d2 = d1 - sg * np.sqrt(T)
        return K * np.exp(-rf * T) * norm.cdf(-d2) - S * norm.cdf(-d1), norm.cdf(d1) - 1
    for lab, kmul in ((f"k={k:.2f}", k), (f"k={kall:.2f}(all-days)", kall)):
        pos = []; cash = 0.0; eqd = {}; trades = []; dates = idx.loc["1927-01-01":"1934-12-31"].index
        mfirst = set(pd.Series(dates).groupby([dates.year, dates.month]).min().values)
        for t in dates:
            S = idx[t]; sg = max(0.12, kmul * (rvm[t] if rvm[t] == rvm[t] else .15)); keep = []
            for p in pos:
                T = (p["ex"] - t).days / 365
                if T <= 21 / 365 + 1e-9: pr, dl = px(S, p["K"], max(T, 1e-4), sg)
                else: pr, dl = px(S, p["K"], T, sg)
                if dl <= DELTA_TRIG or (p["ex"] - t).days <= EXIT_DTE:
                    v = max(pr * (1 - h), 0) * p["n"] if pr > (p["K"] - S) else max(p["K"] - S, 0) * p["n"] * (1 - 0)
                    v = pr * (1 - h) * p["n"]; cash += v; trades.append((p["d0"], t, v / B, S / p["S0"] - 1)); 
                else: p["last"] = pr * (1 - h) * p["n"]; keep.append(p)
            pos = keep
            if t in mfirst:
                ex = t + pd.Timedelta(days=TENOR); pr, _ = px(S, OTM * S, TENOR / 365, sg); ask = pr * (1 + h)
                cash -= B; pos.append(dict(d0=t, ex=ex, K=OTM * S, S0=S, n=B / ask, last=B / ask * pr * (1 - h)))
            eqd[t] = cash + sum(p["last"] for p in pos)
        e = pd.Series(eqd); ye = e.groupby(e.index.year).last(); pnl = ye.diff()
        say(f"-- {lab}: calendar-year net P&L of the put book (% of account; annual budget 1.2%): " + ", ".join(f"{y} {v*100:+.2f}" for y, v in pnl.dropna().items()))
        t_ = pd.DataFrame(trades, columns=["buy", "sell", "mult", "spot_move"])
        for nm, a, b in (("first leg: bought 1929-06..1929-10", "1929-06-01", "1929-10-31"), ("grind: bought 1930-01..1932-06", "1930-01-01", "1932-06-30")):
            q = t_[(t_.buy >= a) & (t_.buy <= b)]
            say(f"   {nm}: n {len(q)}, mean payoff multiple of premium {q.mult.mean():.2f}x (max {q.mult.max():.1f}x), net {((q.mult-1)*B).sum()*100:+.2f}% of account")
        c = e.loc["1929-06-01":"1932-12-31"]; say(f"   cumulative net 1929-06..1932-12: {(c.iloc[-1]-c.iloc[0])*100:+.2f}% of account (= {(c.iloc[-1]-c.iloc[0])/(12*B):.1f}x annual budget); put cost multiple check: Sep-1929 ATM-90% put ask as % of spot = {px(idx['1929-09-03'],OTM*idx['1929-09-03'],TENOR/365,max(.12,kmul*rvm['1929-09-03']))[0]*(1+h)/idx['1929-09-03']*100:.2f}%, Jul-1931: {px(idx['1931-07-01'],OTM*idx['1931-07-01'],TENOR/365,max(.12,kmul*rvm['1931-07-01']))[0]*(1+h)/idx['1931-07-01']*100:.2f}%")
        say(f"   RV20 1929-09: {rvm['1929-09-03']*100:.0f}%  1929-11: {rvm['1929-11-13']*100:.0f}%  1931-06: {rvm['1931-06-01']*100:.0f}%  1932-06: {rvm['1932-06-01']*100:.0f}%")
    with open(OUT, "a") as f: f.write("\n".join(LOG[-14:]) + "\n")

if __name__ == "__main__":
    if "--pull" in sys.argv: pull(); sys.exit()
    if "--model" in sys.argv: model_1929(); sys.exit()
    P, U = load(); bk = Book(P, U)
    say(f"CRASH-B N1025. SPY puts, far-side fills, budget {B*100:.2f}%/month, monetize delta<={DELTA_TRIG} or DTE<={EXIT_DTE}; rows {len(P):,}; {U.index[0].date()}..{U.index[-1].date()}")
    ivs = iv_series(bk, U.index); ivs.to_pickle(D / "iv.pkl")
    arms = [("PUT10", "put", None), ("SPR 90/75", "spr", None), ("COND-IV", "put", "iv"), ("COND-SMA", "put", "sma")]
    res = {}
    for name, mode, gate in arms:
        for xr in ("delta", "hold"):
            if xr == "hold" and name not in ("PUT10", "SPR 90/75"): continue
            eq, sp, tr = run(bk, mode, gate, xr, ivs); res[(name, xr)] = (eq, sp, tr)
            y = yearly(eq, sp)
            say(f"\n== {name} exit={'delta/DTE21 (PRIMARY)' if xr=='delta' else 'M0 hold to DTE21'}  total spend {sp.sum()*100:.1f}% of acct over 21y, trades {len(tr)}")
            say("year  net_pnl%  spent%")
            for yr, rw in y.iterrows(): say(f"{yr}  {rw.net_pnl*100:8.2f}  {rw.spent*100:6.2f}")
            nc = y.drop([2008, 2020, 2022], errors="ignore")
            say(f"non-crash-year worst net {nc.net_pnl.min()*100:.2f}% ; every nc year net >= -spent: {bool(((nc.net_pnl + nc.spent) >= -1e-9).all())}; cum 2010-19 net {y.loc[2010:2019].net_pnl.sum()*100:.2f}% (spent {y.loc[2010:2019].spent.sum()*100:.2f}%)")
            ann = 12 * B
            g08 = y.net_pnl.get(2008, np.nan); g20 = y.net_pnl.get(2020, np.nan)
            say(f"2008 {g08*100:.1f}% = {g08/ann:.1f}x annual budget; 2020 {g20*100:.1f}% = {g20/ann:.1f}x; 2022 {y.net_pnl.get(2022,np.nan)*100:.2f}%")
            say(f"GATE(>=10x both, bleed<=budget): {'PASS' if (g08>=10*ann and g20>=10*ann and ((nc.net_pnl + nc.spent) >= -1e-9).all()) else 'FAIL'}")
            if len(tr):
                big = tr.sort_values("mult", ascending=False).head(4)
                say("top trades (buy, sell, mult, S0->S1): " + "; ".join(f"{a.date()}->{b.date()} {m:.1f}x {s0:.0f}->{s1:.0f}" for a, b, m, s0, s1 in zip(big.buy, big.sell, big.mult, big.S0, big.S1)))
    say("\n== Combined with 100% SPY (puts funded from the account, PRIMARY exit)")
    spy = (1 + U.ret.fillna(0)).cumprod(); w, c, dd = stats(spy); say(f"SPY alone       terminal {w:.2f}x  CAGR {c*100:.2f}%  maxDD {dd*100:.1f}%")
    for (name, xr), (eq, sp, tr) in res.items():
        if xr != "delta": continue
        cb = combined(U, eq); w, c, dd = stats(cb); say(f"SPY + {name:10s} terminal {w:.2f}x  CAGR {c*100:.2f}%  maxDD {dd*100:.1f}%")
    # crash-window drawdown for combined
    for nm, a, b in (("2008-09..2009-03", "2008-09-01", "2009-03-09"), ("2020-02-19..03-23", "2020-02-19", "2020-03-23")):
        s = spy.loc[a:b]; line = f"{nm}: SPY {(s.iloc[-1]/s.iloc[0]-1)*100:.1f}%"
        for (name, xr), (eq, sp, tr) in res.items():
            if xr == "delta": cb = combined(U, eq).loc[a:b]; line += f" | {name} {(cb.iloc[-1]/cb.iloc[0]-1)*100:.1f}%"
        say(line)
    # whole-contract feasibility at the latest year (2025) median far-side prices, SPY ~ latest close
    d25 = [d for d in U.index if d.year == 2025 and d in bk.G]; costs_p, costs_s, notl = [], [], []
    for d in d25[::20]:
        S = U.close[d]; r = bk.pick(d, OTM * S)
        if r is None: continue
        g = bk.G[d]; g = g[g.exdate == r.exdate]; r2 = g.loc[(g.k - OTM2 * S).abs().idxmin()]
        costs_p.append(r.ask * 100); costs_s.append((r.ask - r2.bid) * 100); notl.append(S * 100)
    cp, cs, nt = np.median(costs_p), np.median(costs_s), np.median(notl)
    say(f"\nWhole contracts, 2025 medians: SPY notional ${nt:,.0f}/contract; 90d 90%-put ask ${cp:,.0f}; 90/75 spread debit ${cs:,.0f}")
    for a in (2300, 10000, 25000):
        bud = a * 12 * B
        say(f"acct ${a:>6,}: 1.2%/yr budget ${bud:,.0f} = {bud/cp:.2f} puts/yr or {bud/cs:.2f} spreads/yr; ONE put/quarter costs {4*cp/a*100:.1f}%/yr, ONE spread/quarter {4*cs/a*100:.1f}%/yr of account")
    say(f"min account to buy 1 put/month at 0.1%/mo: ${cp/B:,.0f}; 1 spread/month: ${cs/B:,.0f}; 1 put/quarter at 1.2%/yr: ${4*cp/(12*B):,.0f}")
    OUT.write_text("\n".join(LOG) + "\n")
