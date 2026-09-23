import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intra import *
def orb(sym, orm=5, R=10, risk=0.01, maxlev=4, cost_bps=0.5, longonly=False, exit_m=389):
    M=load(sym); O=M['open'].values; H=M['high'].values; L=M['low'].values; C=M['close'].values
    days=M['close'].index; out=np.zeros(len(days)); tr=np.zeros(len(days))
    for i in range(len(days)):
        o=O[i,0]; c=C[i,orm-1]; hi=H[i,:orm].max(); lo=L[i,:orm].min()
        if c>o: d=1; e=O[i,orm]; stop=lo
        elif c<o and not longonly: d=-1; e=O[i,orm]; stop=hi
        else: continue
        rps=abs(e-stop)/e
        if rps<=0: continue
        lev=min(maxlev, risk/rps)
        tgt=e*(1+d*R*rps)
        px=C[i,exit_m]
        for m in range(orm,exit_m+1):
            if d==1:
                if L[i,m]<=stop: px=min(stop,O[i,m]); break
                if H[i,m]>=tgt: px=max(tgt,O[i,m]); break
            else:
                if H[i,m]>=stop: px=max(stop,O[i,m]); break
                if L[i,m]<=tgt: px=min(tgt,O[i,m]); break
        out[i]=lev*(d*(px/e-1)-2*cost_bps/1e4); tr[i]=1
    return pd.Series(out,index=days), tr
if __name__=="__main__":
    for s in sys.argv[1].split(','):
        for kw in [dict(),dict(cost_bps=0),dict(cost_bps=1),dict(longonly=True),dict(orm=15),dict(orm=30),dict(R=3),dict(maxlev=1),dict(risk=0.005,maxlev=2)]:
            r,t=orb(s,**kw); print(stats(r,f"{s} ORB {kw}"), f"tr/day {t.mean():.2f}")
