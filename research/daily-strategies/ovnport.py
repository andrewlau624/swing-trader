from panel import *
P=panel(); O,H,L,C,V=[P[k].astype('float64') for k in ['open','high','low','close','volume']]
C1=C.shift(1); advp=(C*V).rolling(20).mean().shift(1)
elig=(C>=5)&(advp>=10e6)&(C<=2000)
day=C/C1-1; ibs=(C-L)/(H-L).replace(0,np.nan); intr=C/O-1; gap=O/C1-1
on=O.shift(-1)/C-1
def port(sig, score, maxw=0.2, K=None, cost=5, lev=1.0):
    s=score.where(sig&elig)
    if K: s=s.where(s.rank(axis=1,ascending=False)<=K)
    m=s.notna(); n=m.sum(axis=1)
    w=m.div(n.where(n>0),axis=0).clip(upper=maxw).fillna(0)*lev
    r=(w*on.fillna(0)).sum(axis=1)-w.sum(axis=1)*2*cost/1e4
    return r.shift(1).fillna(0), n   # realized on next day
rules={
 'day<=-12%':(day<=-0.12, -day),
 'day<=-20%':(day<=-0.20, -day),
 'intr<=-8% & ibs<.05':((intr<=-0.08)&(ibs<0.05), -intr),
 'intr<=-8% & ibs<.05 & gap<=0.05':((intr<=-0.08)&(ibs<0.05)&(gap<=0.05), -intr),
 'day<=-8% & ibs<.1':((day<=-0.08)&(ibs<0.1), -day),
 'day<=-8% & ibs<.1 & gap<=.05':((day<=-0.08)&(ibs<0.1)&(gap<=0.05), -day),
}
for k,(sig,sc) in rules.items():
    for mw in [0.2,0.1]:
        for cost in [5,15]:
            r,n=port(sig,sc,maxw=mw,cost=cost); print(stats(r,f"{k} maxw{mw} c{cost}"), f"nights-invested {(n>0).mean()*100:.0f}% avg names {n[n>0].mean():.1f} gross-expo {min(1,mw*n[n>0].mean()):.2f}")
