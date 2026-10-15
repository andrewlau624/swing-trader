"""Noise leg (daybook PROD, QQQ+SMH) per-year / post-publication, no-lag vs one-bar-lag, by cost.
Lag = decision at 30-min bar m, fill at the print of m+30 (matches live coid 'noise-sell-m60' filled ~m90).
Signal logic copied from swingtrader.daybook.shadow.replay_instrument (unchanged). No tuning.
Run: PYTHONPATH=. .venv/bin/python research/sim/noise_recent.py"""
import numpy as np, pandas as pd
from swingtrader.daybook import shadow as sh
from swingtrader.daybook.signals import noise_bounds, breakout_strength, vol_leverage

cfg = sh.CFGS["PROD"]; W = cfg.core
def trades_for(S, sym, w, lag):
    out = []; days = list(S)
    for k, day in enumerate(days):
        prev = days[:k]
        if len(prev) < 5: continue
        hist = prev[-cfg.lookback:]; T = S[day]; C, V = T["close"], T["volume"]
        if not np.isfinite(C).any(): continue
        moves = np.array([np.abs(S[d]["close"]/S[d]["open"]-1.0) for d in hist])
        sigma = np.nanmean(moves, axis=0)
        ub, lb = noise_bounds(T["open"], S[prev[-1]]["close"][-1], sigma)
        pv = np.cumsum(C*V)/np.maximum(np.cumsum(V),1); pv = np.where(np.isfinite(pv), pv, C)
        closes = np.array([S[d]["close"][-1] for d in days[:k+1]])
        lev = vol_leverage(closes, cfg.target_vol, cfg.max_lev)
        if lev <= 0: continue
        mult = lev*w; pos = 0; ep = 0.0
        def fm(m): return min(m+lag, cfg.close_min)
        def rec(mx, px_exit_m):
            out.append((day, sym, pos, (float(C[px_exit_m])/ep-1)*pos*1e4, mult))
        for m in sh.DEC:
            p = float(C[m])
            if pos == 1 and p < max(ub[m], pv[m]): rec(m, fm(m)); pos = 0
            elif pos == -1 and p > min(lb[m], pv[m]): rec(m, fm(m)); pos = 0
            if pos == 0:
                d, _ = breakout_strength(p, ub[m], lb[m], sigma[m])
                if d: pos, ep = d, float(C[fm(m)])
        if pos: rec(0, cfg.close_min)
    return pd.DataFrame(out, columns=["date","sym","dir","gross","lev"])

def stats(df, alldays, c):
    if df.empty: return None
    net = df.gross - 2*c; n = len(net)
    t = net.mean()/(net.std()/np.sqrt(n)) if n > 2 and net.std() > 0 else np.nan
    dp = (net*1e-4*df.lev).groupby(df.date).sum().reindex(alldays).fillna(0)
    sh_ = dp.mean()/dp.std()*np.sqrt(252) if dp.std() > 0 else np.nan
    return dict(n=n, mean=net.mean(), med=net.median(), t=t, hit=(net>0).mean()*100, sharpe=sh_, ann=dp.mean()*252*100)

if __name__ == "__main__":
    S = {s: sh._sessions_cache(s, 14, None) for s in W}
    allt = {}
    for lag in (0, 30):
        allt[lag] = pd.concat([trades_for(S[s], s, W[s], lag) for s in W]); 
    alld = {lag: pd.DatetimeIndex(sorted(allt[lag].date.unique())) for lag in allt}
    allt[0].to_pickle("/private/tmp/claude-501/scr/t0.pkl"); allt[30].to_pickle("/private/tmp/claude-501/scr/t30.pkl")
    rows = []
    for lag in (0, 30):
        T = allt[lag]; ad = pd.DatetimeIndex(sorted(set(S["QQQ"]) & set(S["SMH"])))
        for per, sel in [(str(y), (T.date.dt.year==y)) for y in range(2016, 2027)] + [("post-2024-05", T.date>="2024-06-01"), ("pre-2024-06", T.date<"2024-06-01"), ("all", T.date>=T.date.min())]:
            for sym in ("QQQ","SMH","both"):
                d = T[sel & ((T.sym==sym) if sym!="both" else True)]
                dd = ad[(ad>=d.date.min())&(ad<=d.date.max())] if len(d) else ad[:0]
                if per=="post-2024-05": dd = ad[ad>="2024-06-01"]
                if per=="pre-2024-06": dd = ad[ad<"2024-06-01"]
                for c in (0.5,1.0,2.0):
                    s = stats(d, dd, c)
                    if s: rows.append(dict(lag=lag, period=per, sym=sym, cost=c, **s))
    R = pd.DataFrame(rows); R.to_csv("/private/tmp/claude-501/scr/res.csv", index=False)
    pd.set_option("display.width", 200)
    print(R.round(2).to_string(index=False))

def live_window(first="2026-09-23", last="2026-10-05"):
    """Replay the live days from Alpaca SIP (cache ends earlier). Returns {lag: trades}."""
    S = {s: sh._sessions_alpaca(s, 30) for s in W}
    res = {}
    for lag in (0, 30):
        T = pd.concat([trades_for(S[s], s, W[s], lag) for s in W])
        res[lag] = T[(T.date >= first) & (T.date <= last)]
    return res
