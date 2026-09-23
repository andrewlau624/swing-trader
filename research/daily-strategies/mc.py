import pandas as pd, numpy as np, sys
df=pd.read_pickle(sys.argv[1])
rng=np.random.default_rng(7)
N=10000; YRS=15; D=252*YRS; BLOCK=21
def legs(d):
    return {'A1x':(0.5*d.night+0.5*d.ibs).values,'A2x':(d.night+d.ibs).values,
            'FULL':(d.noise+0.5*d.night+0.5*d.ibs).values}
def haircut(x,f):   # keep volatility, keep only fraction f of the mean
    return x-(1-f)*x.mean()
def paths(src_a, src_b):
    n=len(src_a); nb=D//BLOCK+1
    starts=rng.integers(0,n-BLOCK,(N,nb))
    idx=(starts[:,:,None]+np.arange(BLOCK)).reshape(N,-1)[:,:D]
    ra, rb = src_a[idx], src_b[idx]
    eq=np.empty((N,D)); e=np.full(N,3000.0); hit=np.full(N,np.inf)
    for t in range(D):
        on_b = e>=25000
        hit[(on_b)&np.isinf(hit)]=t
        e=e*(1+np.where(on_b, rb[:,t], ra[:,t])); eq[:,t]=e
    return eq, hit
def pct(x,q): return np.percentile(x,q)
def fmt(v): return f"${v/1e3:,.0f}k" if v<1e6 else f"${v/1e6:,.1f}M"
for scen,d,f in [('BACKTEST AS-IS (2021-26)',df,1.0),('LIVE = HALF THE BACKTEST EDGE',df,0.5),('WEAK REGIME ONLY (2021-23)',df.loc[:'2023'],1.0)]:
    L={k:(haircut(v,f) if f<1 else v) for k,v in legs(d).items()}
    print(f"\n######## {scen}")
    for k,v in L.items():
        yr=(1+v.mean())**252-1; vol=v.std()*np.sqrt(252)
        print(f"   {k:5s} ~{yr*100:5.1f}%/yr mean, vol {vol*100:4.1f}%")
    for A in ['A1x','A2x']:
        eq,hit=paths(L[A],L['FULL'])
        y=hit/252
        reach={t:100*np.mean(y<=t) for t in [2,3,5,7,10,15]}
        print(f"  --- phase 1 = {A} ({'no margin' if A=='A1x' else '2x overnight margin'}), then FULL at $25k")
        print("   years to $25k: 10th %s | median %s | 90th %s" % tuple(
            (f"{pct(y,q):.1f}" if np.isfinite(pct(y,q)) else ">15") for q in (10,50,90)))
        print("   chance of $25k within: " + "  ".join(f"{t}y {p:.0f}%" for t,p in reach.items()))
        for Y in [1,3,5,10]:
            v=eq[:,252*Y-1]; print(f"   after {Y:2d}y: bad(10th) {fmt(pct(v,10)):>8} | typical {fmt(pct(v,50)):>8} | good(90th) {fmt(pct(v,90)):>8}   below $3k: {100*np.mean(v<3000):3.0f}%")
        # worst drawdown in first 2 years
        e2=eq[:,:504]; dd=(e2/np.maximum.accumulate(e2,axis=1)-1).min(axis=1)
        print(f"   worst dip in first 2y: typical {pct(dd,50)*100:.0f}%, bad case {pct(dd,10)*100:.0f}%")
    # phase 2 alone: from 25k
    eq,_=paths(L['FULL'],L['FULL'])
    s=eq/3000*25000
    print("  --- FULL strategy starting at $25k")
    for Y in [1,3,5]:
        v=s[:,252*Y-1]; print(f"   after {Y}y: bad {fmt(pct(v,10)):>8} | typical {fmt(pct(v,50)):>8} | good {fmt(pct(v,90)):>8}")
    t100=np.argmax(s>=100000,axis=1).astype(float); t100[~(s>=100000).any(axis=1)]=np.inf
    print(f"   years 25k->100k: 10th {pct(t100/252,10):.1f} | median {pct(t100/252,50):.1f} | 90th {pct(t100/252,90):.1f}")
