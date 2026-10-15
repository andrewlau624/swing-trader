"""IBS whole-share rounding loss and twin-execution gain. Signals on the original ETF (live rule: top-3 12-1 momentum
of the 18-ETF universe, IBS<0.2 on last bar, equal split of leg=ibs_weight*equity, buy next open, floor shares,
held names are not resized). Execution symbol may be a twin. Sharadar SFP daily, open-to-open."""
import os, sys, math
import pandas as pd, numpy as np
sys.path.insert(0, '.')
from swingtrader.daily import signals as sg
U = ["SPY","QQQ","IWM","DIA","MDY","XLK","XLF","XLE","XLV","XLI","XLY","XLP","XLU","XLB","SMH","XBI","EEM","EFA"]
TW = {"SPY":"SPYM","QQQ":"QQQM","IWM":"VTWO","MDY":"IJH","XLK":"FTEC","XLF":"FNCL","XLE":"FENY","XLV":"FHLC","XLI":"FIDU",
      "XLY":"FDIS","XLP":"FSTA","XLU":"FUTY","XLB":"FMAT","SMH":"SOXQ","EEM":"IEMG","EFA":"IEFA"}
# conservative subset (liquid twin, corr>=.985): the only ones that matter by price
TWS = {k:v for k,v in TW.items() if k in ("SPY","QQQ","MDY","SMH","IWM","EEM","EFA")}
f = pd.read_parquet(os.path.expanduser('~/data/sharadar/funds.parquet'))
f = f[f.ticker.isin(set(U)|set(TW.values()))].copy(); f['date']=pd.to_datetime(f.date)
P = lambda c: f.pivot(index='date', columns='ticker', values=c)
op, hi, lo, cl, ca, cu = P('open'), P('high'), P('low'), P('close'), P('closeadj'), P('close')
adj = ca/cu; opa = op*adj
def run(E, start, end, twins, X=0.0, w=0.5):
    """returns (pnl$ , avg deployed frac of target, n entries, days) over [start,end]."""
    dates = [d for d in cl.index if start <= d <= end]
    held = {}   # sig -> (exec, shares)
    pnl = 0.0; dep = []; ent = 0
    idx = list(cl.index); pos = {d:i for i,d in enumerate(idx)}
    for d in dates:
        i = pos[d]
        if i < 260 or i+1 >= len(idx): continue
        prev = idx[i-1]
        last = {s:{"high":hi.at[prev,s],"low":lo.at[prev,s],"close":cl.at[prev,s]} for s in U if not np.isnan(cl.at[prev,s])}
        top = sg.momentum_top(ca.loc[:prev, U].dropna(how='all', axis=1), d, 3)
        tg = sg.ibs_targets({s:last[s] for s in top if s in last}, 0.2)
        held = {s:v for s,v in held.items() if s in tg}
        leg = w*E
        if tg:
            per = leg/len(tg)
            for s in tg:
                if s in held: continue
                ex = s
                if twins and s in TWS and not np.isnan(op.at[d,TWS[s]]):
                    px_o = last[s]["close"]; loss = (per % px_o)/per if per>=px_o else 1.0
                    if loss > X: ex = TWS[s]
                refp = cl.at[prev, ex] if not np.isnan(cl.at[prev, ex]) else op.at[d, ex]
                sh = math.floor(per/refp); held[s] = (ex, sh); ent += 1
        nxt = idx[i+1]
        for s,(ex,sh) in held.items():
            pnl += sh*op.at[d,ex]*(opa.at[nxt,ex]/opa.at[d,ex]-1) if sh else 0.0
            dep.append(sh*op.at[d,ex]/(w*E/len(tg)))
    return pnl, (np.mean(dep) if dep else np.nan), ent, len(dates)
if __name__ == "__main__":
    for lab,(a,b) in {"2y 2024-10..2026-10":("2024-10-07","2026-10-02"),"5y 2021-10..2026-10":("2021-10-07","2026-10-02")}.items():
        a,b = pd.Timestamp(a), pd.Timestamp(b); yrs=(b-a).days/365.25
        print("==",lab)
        for E in (1000,2300,10000,25000):
            r0 = run(E,a,b,False); r1 = run(E,a,b,True,X=0.0); r2 = run(E,a,b,True,X=0.10); rI=run(E*1000,a,b,False)
            ideal = rI[0]/1000
            print(f"E={E:>6}: ideal ${ideal/yrs:8.1f}/yr ({ideal/yrs/E*100:5.2f}%) | base dep {r0[1]*100:5.1f}% pnl {r0[0]/yrs/E*100:5.2f}%/yr | twin X=0 {r1[0]/yrs/E*100:5.2f}%/yr dep {r1[1]*100:5.1f}% | twin X=10% {r2[0]/yrs/E*100:5.2f}%/yr | n={r0[2]}")
