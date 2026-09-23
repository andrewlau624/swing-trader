import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intra import *
def noise(sym, lookback=14, vm=1.0, step=30, first=30, cost_bps=2.0, sizing='vol', target=0.02, maxlev=4, longonly=False, vwapstop=True):
    M=load(sym); C=M['close'].values; O=M['open'].values[:,0]; V=M['volume'].values
    days=M['close'].index; n=len(days)
    move=np.abs(C/O[:,None]-1)
    dclose=C[:,-1]; prevc=np.r_[np.nan,dclose[:-1]]
    dret=pd.Series(dclose,index=days).pct_change()
    vol14=dret.rolling(14).std().shift(1).values
    pv=np.cumsum(C*V,axis=1)/np.maximum(np.cumsum(V,axis=1),1)  # approx vwap using close
    out=np.zeros(n); ntr=np.zeros(n)
    for i in range(lookback+1,n):
        sig=move[i-lookback:i].mean(axis=0)*vm
        ub=max(O[i],prevc[i])*(1+sig); lb=min(O[i],prevc[i])*(1-sig)
        lev=min(maxlev,target/vol14[i]) if sizing=='vol' else 1.0
        if not np.isfinite(lev): continue
        pos=0; entry=None; pnl=0.0; trades=0
        for m in range(first,390,step):
            p=C[i,m]
            # exits
            if pos==1 and (p< (max(ub[m],pv[i,m]) if vwapstop else ub[m])): pnl+=p/entry-1; pos=0; trades+=1
            elif pos==-1 and (p> (min(lb[m],pv[i,m]) if vwapstop else lb[m])): pnl+=1-p/entry; pos=0; trades+=1
            if pos==0:
                if p>ub[m]: pos=1; entry=p; trades+=1
                elif p<lb[m] and not longonly: pos=-1; entry=p; trades+=1
        p=C[i,389]
        if pos==1: pnl+=p/entry-1; trades+=1
        elif pos==-1: pnl+=1-p/entry; trades+=1
        out[i]=lev*(pnl-trades*cost_bps/1e4); ntr[i]=trades
    return pd.Series(out,index=days), ntr
if __name__=="__main__":
    syms=sys.argv[1].split(',')
    for s in syms:
        r,nt=noise(s); print(stats(r,f"{s} noise base (paper)"), f"trades/day {nt.mean():.2f}")
        r,nt=noise(s,cost_bps=0); print(stats(r,f"{s} noise gross"))
        r,nt=noise(s,sizing='fixed'); print(stats(r,f"{s} noise 1x lev"))
        r,nt=noise(s,longonly=True); print(stats(r,f"{s} noise longonly"))
        r,nt=noise(s,step=15,first=15); print(stats(r,f"{s} noise step15"))
        r,nt=noise(s,vm=1.5); print(stats(r,f"{s} noise vm1.5"))
