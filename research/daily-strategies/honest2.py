import sys,os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from noise import *
import noise as N
# 1) noise with 1-minute fill delay: decide on bar m close, fill at bar m+1 close
def noise_delay(sym,cost_bps=0.5,delay=1,**kw):
    M=load(sym); C=M['close'].values; O=M['open'].values[:,0]; V=M['volume'].values
    days=M['close'].index; n=len(days); move=np.abs(C/O[:,None]-1)
    dclose=C[:,-1]; prevc=np.r_[np.nan,dclose[:-1]]
    vol14=pd.Series(dclose,index=days).pct_change().rolling(14).std().shift(1).values
    pv=np.cumsum(C*V,axis=1)/np.maximum(np.cumsum(V,axis=1),1); out=np.zeros(n)
    for i in range(15,n):
        sig=move[i-14:i].mean(axis=0); ub=max(O[i],prevc[i])*(1+sig); lb=min(O[i],prevc[i])*(1-sig)
        lev=min(4,0.02/vol14[i]); 
        if not np.isfinite(lev): continue
        pos=0; pnl=0; tr=0
        for m in range(30,390,30):
            p=C[i,m]; f=C[i,min(m+delay,389)]
            if pos==1 and p<max(ub[m],pv[i,m]): pnl+=f/e-1; pos=0; tr+=1
            elif pos==-1 and p>min(lb[m],pv[i,m]): pnl+=1-f/e; pos=0; tr+=1
            if pos==0 and m<389-delay:
                if p>ub[m]: pos=1; e=f; tr+=1
                elif p<lb[m]: pos=-1; e=f; tr+=1
        p=C[i,389]
        if pos==1: pnl+=p/e-1; tr+=1
        elif pos==-1: pnl+=1-p/e; tr+=1
        out[i]=lev*(pnl-tr*cost_bps/1e4)
    return pd.Series(out,index=days)
for dl in [0,1,2,5]:
    print(stats(noise_delay('QQQ',delay=dl),f'QQQ noise fill delay {dl}min'))
# 2) IBS with 15:50 signal, MOC fill, next close exit (and next-open exit)
for s in ['QQQ','SMH']:
    M=load(s); C=M['close']; H=M['high']; L=M['low']; O=M['open']
    c50=C.iloc[:,379]; h50=H.iloc[:,:380].max(axis=1); l50=L.iloc[:,:380].min(axis=1)
    dc=C.iloc[:,389]; dh=H.max(axis=1); dl_=L.min(axis=1); do=O.iloc[:,0]
    ibs_c=(dc-dl_)/(dh-dl_); ibs50=(c50-l50)/(h50-l50)
    cc=dc.shift(-1)/dc-1
    for lab,sg in [('close IBS',ibs_c<0.2),('15:50 IBS',ibs50<0.2)]:
        r=(cc*sg-2e-4*sg).shift(1)
        print(stats(r,f'{s} {lab}<0.2 MOC->nextMOC'))
