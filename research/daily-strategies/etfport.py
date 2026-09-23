import pandas as pd, numpy as np, sys
SP=sys.argv[0].rsplit('/',1)[0]
d=pd.read_parquet(f'{SP}/etf_daily.parquet')
d['date']=d.timestamp.dt.tz_convert('America/New_York').dt.normalize().dt.tz_localize(None)
P={f:d.pivot(index='date',columns='symbol',values=f) for f in ['open','high','low','close']}
O,H,L,C=P['open'],P['high'],P['low'],P['close']
IBS=(C-L)/(H-L).replace(0,np.nan)
cc_r=C.shift(-1)/C-1; oo_r=O.shift(-2)/O.shift(-1)-1
def st(r):
    out=[]
    for sl in [slice('2016','2020'),slice('2021','2026'),slice('2016','2026')]:
        x=r[sl].fillna(0); yrs=len(x)/252
        cagr=(1+x).prod()**(1/yrs)-1; sh=x.mean()/x.std()*np.sqrt(252); eq=(1+x).cumprod(); dd=(eq/eq.cummax()-1).min()
        out.append(f"{cagr*100:6.1f}%/{sh:4.2f}/{dd*100:5.0f}")
    return "  ".join(out)
U1="SPY QQQ IWM DIA MDY XLK XLF XLE XLV XLI XLY XLP XLU XLB SMH XBI EEM EFA".split()
U2="TQQQ UPRO SPXL TNA SOXL TECL FAS UDOW LABU".split()
U3="QQQ SMH XLK".split()
def port(U, thr=0.2, cost=2, ret=cc_r, maxw=1.0, sel='all', k=3):
    sig=(IBS[U]<thr)
    if sel=='lowk':
        rk=IBS[U].where(sig).rank(axis=1); sig=rk<=k
    n=sig.sum(axis=1)
    w=sig.div(n.where(n>0),axis=0).clip(upper=maxw).fillna(0)
    # turnover cost: sum |w_t - w_{t-1}| *cost ... since each is 1-day hold, approximates entry+exit each day unless held consecutively
    turn=(w-w.shift(1).fillna(0)).abs().sum(axis=1)
    r=(w*ret[U]).sum(axis=1)-turn*cost/1e4
    return r, float((n>0).mean())
print("               IS16-20 cagr/sh/dd   OOS21-26            full")
for nm,U in [('equityETF',U1),('levered',U2),('tech3',U3)]:
    for thr in [0.1,0.2,0.3]:
        for ex,ret in [('close',cc_r),('nextopen',oo_r)]:
            r,e=port(U,thr,ret=ret)
            print(f"{nm:10s} ibs<{thr} {ex:8s} expo{e:4.2f} {st(r)}")
    r,e=port(U,0.2,maxw=1/3); print(f"{nm:10s} ibs<0.2 cap1/3       expo{e:4.2f} {st(r)}")
    r,e=port(U,0.2,sel='lowk',k=1); print(f"{nm:10s} ibs<0.2 lowest1      expo{e:4.2f} {st(r)}")
print('SPY BH', st(cc_r['SPY'])); print('QQQ BH', st(cc_r['QQQ']))
