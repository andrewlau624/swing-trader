from panel import *
P=panel(); O,H,L,C,V=[P[k].astype('float64') for k in ['open','high','low','close','volume']]
C1=C.shift(1); adv=(C*V).rolling(20).mean(); advp=adv.shift(1)
elig=(C>=5)&(advp>=10e6)&(C<=2000)
day=C/C1-1; ibs=(C-L)/(H-L).replace(0,np.nan); rvol=(C*V)/advp; ret5=C/C.shift(5)-1
vol20=np.log(C/C1).rolling(20).std()*np.sqrt(252); gap=O/C1-1; intr=C/O-1
on=O.shift(-1)/C-1
mkt_on=on.where(elig).mean(axis=1)
def tab(feat,bins,lab,base=elig):
    print(f"--- {lab}")
    for lo,hi in bins:
        m=base&(feat>lo)&(feat<=hi); x=on.where(m).stack(); x=x[np.isfinite(x)].clip(-.9,3)
        ex=(on.sub(mkt_on,axis=0)).where(m).stack(); ex=ex[np.isfinite(ex)].clip(-.9,3)
        yr=x.groupby(x.index.get_level_values(0).year).mean()*1e4
        print(f"  {lo:7.2f}..{hi:6.2f} n/day {len(x)/1499:6.1f} mean {x.mean()*1e4:6.1f}bp excess {ex.mean()*1e4:6.1f} win {100*(x>0).mean():4.1f}%  yrs "+" ".join(f"{v:4.0f}" for v in yr.values))
tab(day,[(-1,-.2),(-.2,-.12),(-.12,-.07),(-.07,-.03),(-.03,.03),(.03,.07),(.07,.12),(.12,.2),(.2,5)],'day return')
tab(intr,[(-1,-.15),(-.15,-.08),(-.08,-.04),(-.04,0),(0,.04),(.04,.08),(.08,.15),(.15,5)],'intraday O->C')
tab(ibs,[(-.01,.05),(.05,.15),(.15,.5),(.5,.85),(.85,.95),(.95,1.01)],'IBS')
tab(rvol,[(0,.5),(.5,1),(1,2),(2,4),(4,1e9)],'relative $vol')
tab(vol20,[(0,.3),(.3,.6),(.6,1),(1,1.5),(1.5,99)],'vol20')
print("=== interactions: intraday<=-8% ...")
b2=elig&(intr<=-0.08)
tab(ibs,[(-.01,.05),(.05,.2),(.2,1.01)],'  IBS | intraday<=-8%',b2)
tab(rvol,[(0,1),(1,2),(2,4),(4,1e9)],'  rvol | intraday<=-8%',b2)
tab(gap,[(-1,-.05),(-.05,0),(0,.05),(.05,.15),(.15,9)],'  gap | intraday<=-8%',b2)
