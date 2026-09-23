import pandas as pd, numpy as np, sys
x=pd.read_pickle(sys.argv[1])
days=pd.read_pickle(sys.argv[2]).index
def port(m, cost=7.5, maxw=0.1, crowd_scale=None):
    g=x[m].copy(); n=g.groupby('date').sym.transform('count')
    g['w']=np.minimum(1/n,maxw)
    if crowd_scale: g['w']*=np.minimum(1,crowd_scale/g.n_day)
    g['pnl']=g.w*(g.ret-2*cost/1e4)
    r=g.groupby('date').pnl.sum().reindex(days).fillna(0)
    return r, g.groupby('date').w.sum().reindex(days).fillna(0)
def st(r,lab,expo):
    out=[]
    for sl in [slice('2021','2023'),slice('2024','2026'),slice('2021','2026')]:
        v=r[sl]; y=len(v)/252; c=(1+v).prod()**(1/y)-1; s=v.mean()/v.std()*np.sqrt(252); eq=(1+v).cumprod(); dd=(eq/eq.cummax()-1).min()
        out.append(f"{c*100:6.1f}%/{s:4.2f}/{dd*100:4.0f}")
    yr=r.groupby(r.index.year).apply(lambda v:(1+v).prod()-1)*100
    print(f"{lab:40s} "+"  ".join(out)+f" | avg expo {expo.mean():.2f} | yrs "+" ".join(f"{v:4.0f}" for v in yr.values))
print(f"{'rule (7.5bp/side)':40s} {'2021-23':>15s}  {'2024-26':>15s}  {'full':>15s}")
base=x.ret==x.ret
v6=~((x.kind=='stock')&(x.vol20<0.6))
unc=x.n_day<30
d12=x.day50<=-0.12
R={'R0 baseline (live now)':base,'R1 drop low-vol stocks':v6,'R2 skip crowded days (>=30)':unc,
   'R3 drop <=-12% only':d12,'R4 = R1+R2':v6&unc,'R5 = R1+R2+R3':v6&unc&d12}
for k,m in R.items():
    r,e=port(m); st(r,k,e)
r,e=port(v6,crowd_scale=30); st(r,'R6 = R1, crowded days scaled 30/n',e)
print('--- plateau check on the crowding cutoff (with R1)')
for c in [15,20,30,40,60]:
    r,e=port(v6&(x.n_day<c)); st(r,f'   cutoff {c}',e)
print('--- cost sensitivity of R4')
for c in [5,7.5,10,15]:
    r,e=port(v6&unc,cost=c); st(r,f'   R4 cost {c}bp',e)
