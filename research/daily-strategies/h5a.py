import pandas as pd, numpy as np, sys
SP=sys.argv[1]
d=pd.read_parquet(f'{SP}/etf_daily.parquet'); d['date']=d.timestamp.dt.tz_convert('America/New_York').dt.normalize().dt.tz_localize(None)
P={f:d.pivot(index='date',columns='symbol',values=f) for f in ['open','high','low','close']}
O,H,L,C=P['open'],P['high'],P['low'],P['close']
IBS=(C-L)/(H-L)
oo=(O.shift(-2)/O.shift(-1)-1)
EQ="SPY QQQ IWM DIA MDY XLK XLF XLE XLV XLI XLY XLP XLU XLB SMH XBI EEM EFA".split()
LEV="TQQQ UPRO SPXL TNA SOXL TECL FAS UDOW LABU".split()
def run(sig,cost=1,cap=1.0):
    n=sig.sum(axis=1); w=sig.div(n.where(n>0),axis=0).clip(upper=cap).fillna(0)
    r=((w*oo[sig.columns]).sum(axis=1)-(w-w.shift(1).fillna(0)).abs().sum(axis=1)*cost/1e4).shift(1)
    return r.fillna(0), (n>0).mean()
def st(r,e,lab):
    out=[]
    for sl in [slice('2016','2020'),slice('2021','2026'),slice('2016','2026')]:
        v=r[sl]; y=len(v)/252; c=(1+v).prod()**(1/y)-1; s=v.mean()/v.std()*np.sqrt(252); eq=(1+v).cumprod(); dd=(eq/eq.cummax()-1).min()
        out.append(f"{c*100:5.1f}%/{s:4.2f}/{dd*100:4.0f}")
    yr=r.groupby(r.index.year).apply(lambda v:(1+v).prod()-1)*100
    print(f"{lab:44s} "+"  ".join(out)+f" | in mkt {e*100:3.0f}% | yrs+ {(yr>0).sum()}/{len(yr)}")
print(f"{'IBS<0.2, enter next open':44s} {'2016-20':>14s}  {'2021-26':>14s}  {'2016-26':>14s}")
st(*run(IBS[['QQQ','SMH','XLK']]<0.2),'tech3 (live now; hand-picked)')
st(*run(IBS[EQ]<0.2),'all 18 equity ETFs')
sma=C.rolling(200).mean()
st(*run((IBS[EQ]<0.2)&(C[EQ]>sma[EQ])),'18 ETFs, only above 200d SMA')
st(*run((IBS[EQ+LEV]<0.2)&(C[EQ+LEV]>sma[EQ+LEV])),'27 incl. leveraged, above 200d SMA')
# momentum selection: month-end ranks by 12m return (skip last month), top K, IBS on those
mom=C[EQ].shift(21)/C[EQ].shift(252)-1
me=mom.resample('ME').last().reindex(C.index,method='ffill').shift(1)
for K in [2,3,5]:
    top=me.rank(axis=1,ascending=False)<=K
    st(*run((IBS[EQ]<0.2)&top),f'top-{K} by 12m momentum (monthly), IBS<0.2')
top=me.rank(axis=1,ascending=False)<=3
st(*run((IBS[EQ]<0.2)&top&(C[EQ]>sma[EQ])),'top-3 momentum & above 200d')
# control: bottom-3 momentum
bot=me.rank(axis=1,ascending=True)<=3
st(*run((IBS[EQ]<0.2)&bot),'CONTROL bottom-3 momentum, IBS<0.2')
st(*run(pd.DataFrame(True,index=C.index,columns=['QQQ'])),'QQQ buy & hold (open->open)')
