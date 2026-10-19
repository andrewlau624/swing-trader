import pandas as pd, numpy as np
m=pd.read_parquet('/private/tmp/claude-501/-Users-andrewlau-Documents-Code-Projects-swing-trader/bad619c6-1952-49ad-9cea-d66d4400c09e/scratchpad/j/m.parquet')
m=m.dropna(subset=['open_'])
m['adv']=m.pc*m.volume.fillna(0)  # ex-day volume proxy only
m['yr']=m.date.dt.year
W={'SE':[.15,.30],'ZA':[.15,.20],'AU':[0,.30],'SG':[0,0],'AT':[.15,.275],'IT':[.15,.26],'NL':[.15,.15],'NO':[.15,.25],'DE':[.15,.26375],'JP':[.15,.20]}
for r in ['SE','ZA','AU','SG','AT','IT','NL','NO','DE','JP','GB']:
    g=m[m.region==r]
    if len(g)<30: continue
    ev_yr=g.groupby('yr').size()
    print(f"== {r} n {len(g)} names {g.infocode.nunique()} ev/yr(2015+) {ev_yr[ev_yr.index>=2015].mean():.0f} y_med {g.y.median():.3f} px_med {g.pc.median():.0f} exday-vol$ med {g.adv.median():,.0f} | yrs>0 co_med {(g.groupby('yr').co.median()>0).sum()}/{g.yr.nunique()} | 2019+ co_med {g[g.yr>=2019].co.median()*1e4:.0f}bp drop {g[g.yr>=2019].dr_o.median():.2f} n {len(g[g.yr>=2019])}")
    for w in W.get(r,[]):
        net=g.co-w*g['div']/g.pc-0.0015  # 15bp RT cost placeholder
        print(f"   WHT {w:.3f}: co net(15bp RT) mean(clip) {net.clip(-.05,.05).mean()*1e4:+.0f} med {net.median()*1e4:+.0f}  hit {(net>0).mean():.2f}")
    top=g.groupby(['infocode','dsqtname']).size().sort_values(ascending=False).head(6)
    print('   top:',[(k[1][:28],v) for k,v in top.items()])
