from panel import *
P=panel(); O,H,L,C,V,W=[P[k] for k in ['open','high','low','close','volume','vwap']]
C1=C.shift(1)
adv=(C*V).rolling(20).mean().shift(1); elig=(C1>=5)&(adv>=10e6)
vol20=np.log(C/C1).rolling(20).std().shift(1)*np.sqrt(252)
gap=O/C1-1; oc=C/O-1; ow=W/O-1; on_next=O.shift(-1)/C-1; cc_next=C.shift(-1)/C-1; day=C/C1-1
def row(mask, ret, lab):
    x=ret[mask&elig].stack(); x=x[np.isfinite(x)].clip(-0.9,3)
    yrs=x.groupby(x.index.get_level_values(0).year).mean()*1e4
    print(f"{lab:38s} n={len(x):7d} /day={len(x)/1499:5.1f} mean={x.mean()*1e4:7.1f}bp med={x.median()*1e4:6.1f} win={100*(x>0).mean():4.1f}%  by-yr "+" ".join(f"{v:5.0f}" for v in yrs.values))
print("=== GAP DOWN, long open->close (day trade) ===")
for lo,hi in [(-1,-.15),(-.15,-.08),(-.08,-.04),(-.04,-.02)]:
    m=(gap>lo)&(gap<=hi); row(m,oc,f"gap {lo:.2f}..{hi:.2f} O->C"); row(m,ow,f"   exit at VWAP")
print("=== GAP UP, long open->close ===")
for lo,hi in [(.02,.04),(.04,.08),(.08,.15),(.15,5)]:
    m=(gap>lo)&(gap<=hi); row(m,oc,f"gap {lo:.2f}..{hi:.2f} O->C")
print("=== 1-day reversal: today's return bucket -> overnight / next close ===")
for lo,hi in [(-1,-.15),(-.15,-.08),(-.08,-.04),(.08,.15),(.15,5)]:
    m=(day>lo)&(day<=hi); row(m,on_next,f"day {lo:.2f}..{hi:.2f} C->nextO"); row(m,cc_next,f"   C->nextC")
print("=== overnight all eligible ==="); row(C>0,on_next,"all C->nextO"); row(C>0,oc,"all O->C")
hv=vol20>0.6
row(hv,on_next,"highvol C->nextO"); row(hv,oc,"highvol O->C")
