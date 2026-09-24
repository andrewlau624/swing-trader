"""Dollar-level simulation of the live daily book with whole shares and deposits."""
import sys, pickle, numpy as np, pandas as pd
sys.path.insert(0, '.')
from noise import noise
S = pd.read_pickle('series2.pkl'); days = S.index[S.index >= '2021-02-01']
# ---------------- night leg (corrected trades, live rules)
x = pd.read_pickle('night_trades.v2.pkl'); x = x[x.ret.abs() <= 1]
k = x.groupby(['date', 'day50', 'ret']).sym.transform('count'); x = x[k == 1]
x = x[~((x.kind == 'stock') & (x.vol20 < 0.6))].copy()
x['C'] = x.p50 * (1 + x.close_move)
x['crowd'] = np.minimum(1, 30 / x.n_day)
NIGHT = {d: (g.p50.values, g.C.values, g.ret.values, float(g.crowd.iloc[0]))
         for d, g in x.groupby('date')}
# ---------------- IBS leg: top-3 of 18 by 12-1 momentum, IBS<0.2, open->open
e = pd.read_parquet('etf_daily.parquet')
e['date'] = e.timestamp.dt.tz_convert('America/New_York').dt.normalize().dt.tz_localize(None)
P = {f: e.pivot(index='date', columns='symbol', values=f) for f in ['open', 'high', 'low', 'close']}
O, H, L, C = P['open'], P['high'], P['low'], P['close']
EQ = "SPY QQQ IWM DIA MDY XLK XLF XLE XLV XLI XLY XLP XLU XLB SMH XBI EEM EFA".split()
mom = C[EQ].shift(21) / C[EQ].shift(252) - 1
me = mom.resample('ME').last().reindex(C.index, method='ffill').shift(1)
sig = ((H - L) > 0)[EQ] & (((C - L) / (H - L))[EQ] < 0.2) & (me.rank(axis=1, ascending=False) <= 3)
O1, O2 = O.shift(-1), O.shift(-2)
IBS = {}
for d in sig.index:
    s = [c for c in EQ if sig.at[d, c] and np.isfinite(O1.at[d, c]) and np.isfinite(O2.at[d, c])]
    if s: IBS[d] = (np.array([O1.at[d, c] for c in s]), np.array([O2.at[d, c] / O1.at[d, c] - 1 for c in s]))
bil = C['BIL'].pct_change().shift(-1)       # next session's T-bill return
spy = C['SPY'].pct_change()
NZ = {}
def noise_series(cost, lev):
    key = (cost, lev)
    if key not in NZ: NZ[key] = noise('QQQ', cost_bps=cost, maxlev=lev)[0]
    return NZ[key]

def day_pnl(E, d, *, whole=True, resplit=True, ibs_frac=False, night_cost=7.5,
            nz=None, intraday_on=True, ibs_w=0.5, night_w=0.5):
    pnl = 0.0
    # night leg
    if d in NIGHT:
        p, c, r, crowd = NIGHT[d]; leg = night_w * E
        idx = np.arange(len(p))
        for _ in range(3):
            per = leg * min(1 / max(len(idx), 1), 0.10) * crowd
            sh = np.floor(per / p[idx]) if whole else per / p[idx]
            if not resplit or (sh >= 1).all() or not whole: break
            idx = idx[sh >= 1]
            if not len(idx): break
        if len(idx):
            per = leg * min(1 / len(idx), 0.10) * crowd
            sh = np.floor(per / p[idx]) if whole else per / p[idx]
            v = sh * c[idx]
            pnl += float((v * (r[idx] - 2 * night_cost / 1e4)).sum())
    # IBS leg (idle part earns T-bills)
    used = 0.0
    if d in IBS:
        o1, r = IBS[d]; per = ibs_w * E / len(o1)
        sh = per / o1 if (ibs_frac or not whole) else np.floor(per / o1)
        v = sh * o1; used = v.sum()
        pnl += float((v * (r - 1e-4)).sum())
    b = bil.get(d, 0.0); pnl += (ibs_w * E - used) * (b if np.isfinite(b) else 0.0)
    if intraday_on and nz is not None:
        pnl += E * float(nz.get(d, 0.0))
    return pnl

def replay(start=3000, monthly=1000, dates=days, **kw):
    E, dep, eq, sp = start, start, [], start
    for i, d in enumerate(dates):
        if i and i % 21 == 0: E += monthly; dep += monthly; sp += monthly
        E += day_pnl(E, d, **kw)
        s = spy.get(d, 0.0); sp *= 1 + (s if np.isfinite(s) else 0.0)
        eq.append((d, E, dep, sp))
    return pd.DataFrame(eq, columns=['date', 'E', 'dep', 'spy']).set_index('date')
