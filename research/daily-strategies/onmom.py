from panel import *
P=panel(); O,C,V=[P[k].astype('float64') for k in ['open','close','volume']]
C1=C.shift(1); advp=(C*V).rolling(20).mean().shift(1)
elig=(C1>=5)&(advp>=10e6)&(C1<=2000)
on=O/C1-1                         # overnight return ending at today's open (known at 9:30)
on_next=O.shift(-1)/C-1           # tonight: close -> next open (what we'd earn)
intr=C/O-1
for lb in [21,63]:
    sig=on.clip(-.5,.5).rolling(lb,min_periods=int(lb*.8)).mean().where(elig)   # includes today's open
    rk=sig.rank(axis=1,pct=True)
    mkt=on_next.where(elig).mean(axis=1)
    print(f"\n=== signal: mean overnight return, past {lb} sessions | outcome: tonight's close->open, bp (excess over eligible avg)")
    rows=[]
    for q in range(10):
        m=(rk>q/10)&(rk<=(q+1)/10)
        ex=on_next.where(m).sub(mkt,axis=0).clip(-.2,.2)
        dm=ex.mean(axis=1)                      # per-night decile mean
        yr=dm.groupby(dm.index.year).mean()*1e4
        rows.append([q+1, round(dm.mean()*1e4,1), round(dm['2021':'2023'].mean()*1e4,1), round(dm['2024':].mean()*1e4,1)]+list(yr.round(0).values))
    print(pd.DataFrame(rows,columns=['decile','all','21-23','24-26']+[str(y) for y in yr.index]).to_string(index=False))
    # top decile raw overnight return (what you actually earn, before cost)
    top=on_next.where(rk>0.9).clip(-.2,.2).mean(axis=1)
    print(f"top decile RAW overnight: {top.mean()*1e4:.1f}bp/night  (21-23 {top['2021':'2023'].mean()*1e4:.1f}, 24-26 {top['2024':].mean()*1e4:.1f}); names/night {(rk>0.9).sum(axis=1).mean():.0f}")
    # what does the top decile do intraday tomorrow? (the reversal that makes it overnight-only)
    t2=intr.shift(-1).where(rk>0.9).clip(-.2,.2).mean(axis=1)
    print(f"   ...and next-day open->close: {t2.mean()*1e4:.1f}bp")
