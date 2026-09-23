import pandas as pd, numpy as np, sys
SP=sys.argv[1]
old=pd.read_pickle(f'{SP}/series.pkl'); days=old.index
# --- night R6
x=pd.read_pickle(f'{SP}/night_trades.pkl')
m=~((x.kind=='stock')&(x.vol20<0.6)); g=x[m].copy(); n=g.groupby('date').sym.transform('count')
g['w']=np.minimum(1/n,0.1)*np.minimum(1,30/g.n_day); g['p']=g.w*(g.ret-2*7.5/1e4)
night2=g.groupby('date').p.sum().reindex(days).fillna(0)
# night returns are realized overnight -> attribute to next session (same convention as old series)
night2=night2.shift(1).fillna(0)
print('check old night corr w/ new', round(np.corrcoef(old.night,night2)[0,1],2))
# --- IBS top-3 momentum
d=pd.read_parquet(f'{SP}/etf_daily.parquet'); d['date']=d.timestamp.dt.tz_convert('America/New_York').dt.normalize().dt.tz_localize(None)
P={f:d.pivot(index='date',columns='symbol',values=f) for f in ['open','high','low','close']}
O,H,L,C=P['open'],P['high'],P['low'],P['close']; IBS=(C-L)/(H-L)
EQ="SPY QQQ IWM DIA MDY XLK XLF XLE XLV XLI XLY XLP XLU XLB SMH XBI EEM EFA".split()
mom=C[EQ].shift(21)/C[EQ].shift(252)-1; me=mom.resample('ME').last().reindex(C.index,method='ffill').shift(1)
sig=(IBS[EQ]<0.2)&(me.rank(axis=1,ascending=False)<=3); k=sig.sum(axis=1); w=sig.div(k.where(k>0),axis=0).fillna(0)
oo=O.shift(-2)/O.shift(-1)-1
ibs2=((w*oo[EQ]).sum(axis=1)-(w-w.shift(1).fillna(0)).abs().sum(axis=1)*1e-4).shift(1).reindex(days).fillna(0)
ibs_on=(k>0).shift(1).reindex(days).fillna(False)
bil=(C['BIL'].pct_change()).reindex(days).fillna(0)
noise=old.noise
S=pd.DataFrame({'night_old':old.night,'night_new':night2,'ibs_old':old.ibs,'ibs_new':ibs2,'noise':noise,'bil':bil,'ibs_on':ibs_on.astype(float)})
S.to_pickle(f'{SP}/series2.pkl')
def st(r,lab):
    out=[]
    for sl in [slice('2021','2023'),slice('2024','2026'),slice('2021','2026')]:
        v=r[sl]; y=len(v)/252; c=(1+v).prod()**(1/y)-1; s=v.mean()/v.std()*np.sqrt(252); eq=(1+v).cumprod(); dd=(eq/eq.cummax()-1).min()
        out.append(f"{c*100:5.1f}%/{s:4.2f}/{dd*100:4.0f}")
    yr=r.groupby(r.index.year).apply(lambda v:(1+v).prod()-1)*100
    print(f"{lab:46s} "+"  ".join(out)+" | yrs "+" ".join(f"{v:4.0f}" for v in yr.values))
print(f"{'':46s} {'2021-23':>14s}  {'2024-26':>14s}  {'full':>14s}")
A_old=0.5*S.night_old+0.5*S.ibs_old; A_new=0.5*S.night_new+0.5*S.ibs_new
st(A_old,'NO-DAYTRADE old (live now)')
st(A_new,'NO-DAYTRADE new (night R6 + IBS momentum)')
tb=A_new+0.5*(1-S.ibs_on)*S.bil
st(tb,'  + idle IBS half in T-bills')
st(S.noise+0.5*S.night_old+0.5*S.ibs_old,'FULL old')
st(S.noise+0.5*S.night_new+0.5*S.ibs_new,'FULL new')
print('--- vol targeting on the no-daytrade book (scale = tgt/realized20d, capped)')
for tgt,capv in [(0.12,1.0),(0.16,1.0),(0.16,2.0),(0.20,2.0)]:
    rv=A_new.rolling(20).std().shift(1)*np.sqrt(252); sc=(tgt/rv).clip(upper=capv).fillna(1)
    st(sc*A_new,f'  vol-target {tgt:.0%}, max {capv:.0f}x (avg {sc.mean():.2f}x)')
st(2*A_new,'  flat 2x (for comparison)')
print('corr new legs:'); print(S[['night_new','ibs_new','noise']].corr().round(2))
