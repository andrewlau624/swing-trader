import sys,os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from panel import *; from tos import *
P=panel(); O,H,L,C,V=[P[k].astype('float64') for k in ['open','high','low','close','volume']]
C1=C.shift(1); adv=(C*V).rolling(20).mean()
vol20=np.log(C/C1).rolling(20).std()*np.sqrt(252)
elig=(C>=5)&(adv>=10e6)
main,sig,ob=tmo(O,C); up=(main>sig)&(main.shift()<=sig.shift())
sq,mom=ttm(H,L,C); fire=(~sq)&sq.shift(1).fillna(False)
IBS=(C-L)/(H-L)
fwd={h:(O.shift(-1-h)/O.shift(-1)-1) for h in [1,5,10]}   # enter next open
def ev(mask, lab, base):
    s=f"{lab:42s}"
    for h,f in fwd.items():
        ex=(f-f.where(base).mean(axis=1).values[:,None]).where(mask&base)
        x=ex.stack(); x=x[np.isfinite(x)].clip(-1,2)
        yr=x.groupby(x.index.get_level_values(0).year).mean()*1e4
        t=x.mean()/x.std()*np.sqrt(len(x))
        s+=f" | {h}d ex {x.mean()*1e4:6.1f}bp t{t:5.1f} yrs+{(yr>0).sum()}/{len(yr)}"
    print(s+f" n/day {mask[base].sum().sum()/1499:5.1f}")
for bn,base in [('liquid',elig),('highvol',elig&(vol20>0.6))]:
    print('=== base',bn)
    ev(up&(main.shift()< -ob),'TMO cross-up from oversold',base)
    ev(up&(main.shift()> ob),'TMO cross-up while overbought',base)
    ev(main< -ob,'TMO oversold state',base)
    ev(main> ob,'TMO overbought state',base)
    ev(fire&(mom>0),'TTM squeeze fire, mom>0',base)
    ev(fire&(mom<0),'TTM squeeze fire, mom<0',base)
    ev(sq,'TTM squeeze on',base)
    ev(IBS<0.1,'IBS<0.1 (reference)',base)
    ev((IBS<0.1)&(main< -ob),'HYBRID IBS<0.1 & TMO oversold',base)
    ev((IBS<0.1)&(main>ob),'HYBRID IBS<0.1 & TMO overbought',base)
