import pandas as pd, numpy as np, sys
x=pd.read_pickle(sys.argv[1]); x['yr']=x.date.dt.year
x['r']=x.ret.clip(-0.1,0.1)
def row(m,lab):
    g=x[m]
    if len(g)<200: print(f"{lab:34s} n={len(g)} (too few)"); return
    h1=g[g.yr<=2023].r.mean()*1e4; h2=g[g.yr>=2024].r.mean()*1e4
    yrs=g.groupby('yr').r.mean()
    t=g.r.mean()/g.r.std()*np.sqrt(len(g))
    print(f"{lab:34s} n/day {len(g)/1415:5.1f}  mean {g.r.mean()*1e4:6.1f}bp  t {t:5.1f} | 21-23 {h1:6.1f}  24-26 {h2:6.1f} | yrs+ {(yrs>0).sum()}/{len(yrs)}  win {100*(g.r>0).mean():4.1f}%")
row(x.r==x.r,'ALL honest signals')
print('-- kind (prior: LETF close rebalancing reverses overnight)')
for k in ['stock','levETF','ETF']: row(x.kind==k,k)
print('-- vol20 (prior: overreaction scales with vol)')
for lo,hi in [(0,.6),(.6,1.2),(1.2,99)]: row((x.vol20>=lo)&(x.vol20<hi)&(x.kind=='stock'),f'stock vol20 {lo}-{hi}')
for lo,hi in [(0,.6),(.6,1.2),(1.2,99)]: row((x.vol20>=lo)&(x.vol20<hi)&(x.kind=='levETF'),f'levETF vol20 {lo}-{hi}')
print('-- prior 20d run-up (prior: forced selling of recent winners overshoots)')
for lo,hi in [(-9,-.2),(-.2,.2),(.2,99)]: row((x.ret20>=lo)&(x.ret20<hi)&(x.kind=='stock'),f'stock ret20 {lo}..{hi}')
print('-- market day (prior: market-wide liquidation days overshoot more)')
for lo,hi in [(-1,-.01),(-.01,.01),(.01,1)]: row((x.spy_day>=lo)&(x.spy_day<hi),f'SPY day {lo}..{hi}')
print('-- crowding: many signals same day')
for lo,hi in [(0,10),(10,30),(30,1e9)]: row((x.n_day>=lo)&(x.n_day<hi),f'n signals/day {lo}-{hi}')
print('-- depth of drop')
for lo,hi in [(-1,-.2),(-.2,-.12),(-.12,-.08)]: row((x.day50>lo)&(x.day50<=hi),f'day50 {lo}..{hi}')
print('-- liquidity')
for lo,hi in [(10e6,30e6),(30e6,100e6),(100e6,1e13)]: row((x.adv>=lo)&(x.adv<hi),f'adv {lo/1e6:.0f}-{hi/1e6:.0f}M')
