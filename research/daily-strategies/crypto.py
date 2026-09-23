import pandas as pd, numpy as np, sys
SP=sys.argv[1]
d=pd.read_parquet(f'{SP}/crypto_daily.parquet'); d['date']=d.timestamp.dt.tz_localize(None).dt.normalize()
C=d.pivot(index='date',columns='symbol',values='close'); H=d.pivot(index='date',columns='symbol',values='high'); L=d.pivot(index='date',columns='symbol',values='low')
r=C.pct_change()
COST=25
def run(pos, cost=COST):
    pos=pos.astype(float); n=pos.sum(axis=1); w=pos.div(n.where(n>0),axis=0).fillna(0)
    w=w.shift(1).fillna(0)          # decided at close t, held over day t+1
    ret=(w*r.fillna(0)).sum(axis=1)-(w-w.shift(1).fillna(0)).abs().sum(axis=1)*cost/1e4
    return ret, float((n>0).mean())
def st(x,e,lab):
    out=[]
    for sl in [slice('2021','2023'),slice('2024','2026'),slice('2021','2026')]:
        v=x[sl]; y=len(v)/365; c=(1+v).prod()**(1/y)-1; s=v.mean()/v.std()*np.sqrt(365); eq=(1+v).cumprod(); dd=(eq/eq.cummax()-1).min()
        out.append(f"{c*100:6.1f}%/{s:4.2f}/{dd*100:4.0f}")
    print(f"{lab:40s} "+"  ".join(out)+f" | in mkt {e*100:3.0f}%")
print(f"{'crypto, 25bp/side':40s} {'2021-23':>16s}  {'2024-26':>16s}  {'2021-26':>16s}")
for s in ['BTC/USD','ETH/USD']:
    st(*run(C[[s]].notna()),f'{s} buy & hold')
    for N in [20,50,100]:
        sma=C[[s]].rolling(N).mean(); st(*run(C[[s]]>sma),f'{s} trend > SMA{N}')
    ibs=(C[[s]]-L[[s]])/(H[[s]]-L[[s]]); st(*run(ibs<0.2),f'{s} IBS<0.2 (1 day)')
B=[c for c in C.columns if C[c].loc['2021-06':].notna().mean()>0.9]
print('basket:',B)
st(*run(C[B].notna()),'basket equal-weight buy&hold')
for N in [20,50,100]:
    st(*run(C[B]>C[B].rolling(N).mean()),f'basket trend > SMA{N}')
# BTC-regime gated basket: only hold coins when BTC itself is in trend
bt=(C['BTC/USD']>C['BTC/USD'].rolling(50).mean())
g=(C[B]>C[B].rolling(50).mean()).mul(bt,axis=0)
st(*run(g),'basket SMA50, only when BTC>SMA50')
