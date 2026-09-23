from gapsim import *
res={}
# --- S1: gap-up fade short. wait for first N-min candle to be red; short at its close; stop = high of day so far (+buffer); exit EOD
def fade(gmin=0.15, N=5, stopmode='hod', confirm=True, pmin=3):
    T=[]
    for i in np.where(ok&(meta.gap>=gmin)&(meta.pc>=pmin))[0]:
        if confirm and not (Cl[i,N-1]<Op[i,0]): continue
        e=Cl[i,N-1]; hod=Hi[i,:N].max()
        stop= hod*1.01 if stopmode=='hod' else e*(1+stopmode)
        x=trade(i,-1,N,e,stop); T.append((meta.date[i],-1,e,x,stop,meta.gap[i]))
    return T
# --- S2: stocks-in-play ORB (Zarattini/Aziz): rv5>1, top-K by rv5, dir of 5m candle, stop 10% ATR, EOD
def sip_orb(K=20, atrf=0.10, longonly=False, gmin=0.0, N=5):
    T=[]
    m=ok&(meta.rv5>1)&(meta.gap.abs()>=gmin)
    sub=meta[m].copy(); sub=sub.sort_values('rv5',ascending=False).groupby('date').head(K)
    for i in sub.index:
        o=Op[i,0]; c=Cl[i,N-1]
        if c>o: d=1; lvl=Hi[i,:N].max()
        elif c<o and not longonly: d=-1; lvl=Lo[i,:N].min()
        else: continue
        # stop-entry: triggered when price crosses OR level after minute N
        em=None
        for mm in range(N,389):
            if (d==1 and Hi[i,mm]>=lvl) or (d==-1 and Lo[i,mm]<=lvl): em=mm; break
        if em is None: continue
        e=max(lvl,Op[i,em]) if d==1 else min(lvl,Op[i,em])
        stop=e-d*atrf*meta.atr[i]
        x=trade(i,d,em,e,stop); T.append((meta.date[i],d,e,x,stop,meta.rv5[i]))
    return T
# --- S3: gap-down reclaim long: gap<=-g, buy when price crosses above N-min OR high; stop at OR low
def reclaim(gmax=-0.04, N=15):
    T=[]
    for i in np.where(ok&(meta.gap<=gmax))[0]:
        lvl=Hi[i,:N].max(); low=Lo[i,:N].min()
        em=None
        for mm in range(N,380):
            if Hi[i,mm]>=lvl: em=mm; break
        if em is None: continue
        e=max(lvl,Op[i,em]); x=trade(i,1,em,e,low); T.append((meta.date[i],1,e,x,low,-meta.gap[i]))
    return T
tests={
 'FADE gap>=15% 5m-red, stop HOD':lambda:fade(0.15),
 'FADE gap>=10% 5m-red, stop HOD':lambda:fade(0.10),
 'FADE gap>=20% 5m-red, stop HOD':lambda:fade(0.20),
 'FADE gap>=15% no confirm, stop HOD':lambda:fade(0.15,confirm=False),
 'FADE gap>=15% 15m-red, stop HOD':lambda:fade(0.15,N=15),
 'FADE gap>=15% stop +10%':lambda:fade(0.15,stopmode=0.10),
 'SIP-ORB top20 (paper)':lambda:sip_orb(),
 'SIP-ORB top20 long-only':lambda:sip_orb(longonly=True),
 'SIP-ORB top10':lambda:sip_orb(K=10),
 'SIP-ORB top20 stop 5%ATR':lambda:sip_orb(atrf=0.05),
 'SIP-ORB top20 stop 25%ATR':lambda:sip_orb(atrf=0.25),
 'RECLAIM gap<=-4% 15m high':lambda:reclaim(),
 'RECLAIM gap<=-8% 15m high':lambda:reclaim(-0.08),
 'RECLAIM gap<=-4% 30m high':lambda:reclaim(N=30),
}
import pickle
for k,f in tests.items():
    T=f()
    for c in [10,20]:
        r,df=portfolio(T,cost_bps=c); print(stats(r,f"{k} c{c}"), tstats(df))
    res[k]=T
pickle.dump(res,open(f"{SP}/gap1_trades.pkl","wb"))
