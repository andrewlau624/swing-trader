import sys,os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from gapload import *
meta,A=build()
ok=(meta.pc>=3)&(meta.pc<=1000)&(meta.adv>=5e6)&np.isfinite(meta.atr)
Op,Hi,Lo,Cl=A[:,0],A[:,1],A[:,2],A[:,3]
def trade(i, d, em, e, stop, tgt=None, xm=389):
    """d=+1 long/-1 short; enter at price e at minute em (fill), stop checked from em onward (em bar itself after fill uses its H/L conservatively)."""
    for m in range(em,xm+1):
        if d==1:
            if Lo[i,m]<=stop: return min(stop,Op[i,m]) if m>em else stop
            if tgt is not None and Hi[i,m]>=tgt: return max(tgt,Op[i,m])
        else:
            if Hi[i,m]>=stop: return max(stop,Op[i,m]) if m>em else stop
            if tgt is not None and Lo[i,m]<=tgt: return min(tgt,Op[i,m])
    return Cl[i,xm]
def portfolio(trades, risk=0.01, maxlev=4.0, cost_bps=10, maxn=None):
    """trades: list of (date, d, e, x, stop). risk-sized; per-day leverage cap."""
    df=pd.DataFrame(trades,columns=['date','d','e','x','stop','score'])
    df['r']=df.d*(df.x/df.e-1)-2*cost_bps/1e4
    df['rps']=(df.e-df.stop).abs()/df.e
    df['w']=np.minimum(risk/df.rps.clip(lower=1e-4), maxlev)
    if maxn: df=df.sort_values('score',ascending=False).groupby('date').head(maxn)
    tot=df.groupby('date').w.transform('sum'); df['w']=df.w*np.minimum(1,maxlev/tot)
    daily=(df.w*df.r).groupby(df.date).sum()
    idx=pd.DatetimeIndex(sorted(meta.date.unique()))
    return daily.reindex(idx).fillna(0), df
def tstats(df):
    r=df.r; return f"n={len(r)} ({len(r)/1474:.1f}/day) avg {r.mean()*1e4:.0f}bp win {100*(r>0).mean():.0f}%"
