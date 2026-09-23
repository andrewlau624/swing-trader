import sys,os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from tos import *
SP=os.path.dirname(os.path.abspath(__file__))
d=pd.read_parquet(f'{SP}/etf_daily.parquet')
d['date']=d.timestamp.dt.tz_convert('America/New_York').dt.normalize().dt.tz_localize(None)
P={f:d.pivot(index='date',columns='symbol',values=f) for f in ['open','high','low','close']}
O,H,L,C=P['open'],P['high'],P['low'],P['close']
nxt=O.shift(-1); 
def st(r):
    out=[]
    for sl in [slice('2016','2020'),slice('2021','2026')]:
        x=r[sl].fillna(0); yrs=len(x)/252
        out.append(f"{((1+x).prod()**(1/yrs)-1)*100:6.1f}%/{x.mean()/x.std()*np.sqrt(252) if x.std()>0 else 0:5.2f}")
    return " ".join(out)
def run_state(pos, U, cost=1):
    # pos decided at close t, executed next open; held open->open
    oo=O.shift(-2)/O.shift(-1)-1
    w=pos[U].astype(float); n=w.sum(axis=1); w=w.div(n.where(n>0),axis=0).fillna(0)
    r=(w*oo[U]).sum(axis=1)-(w-w.shift(1).fillna(0)).abs().sum(axis=1)*cost/1e4
    return r, float((n>0).mean())
def state_from(entry, exit_):
    pos=pd.DataFrame(np.nan,index=entry.index,columns=entry.columns)
    pos[entry]=1; pos[exit_&~entry]=0
    return pos.ffill().fillna(0).astype(bool)
main,sig,ob=tmo(O,C)
up=(main>sig)&(main.shift()<=sig.shift()); dn=(main<sig)&(main.shift()>=sig.shift())
sq,mom=ttm(H,L,C)
fire=(~sq)&sq.shift(1).fillna(False)
IBS=(C-L)/(H-L)
rules={
 'TMO cross-up in OS (<-10), exit cross-dn': state_from(up&(main.shift()< -ob), dn),
 'TMO cross-up anywhere, exit cross-dn': state_from(up, dn),
 'TMO main>signal (state)': main>sig,
 'TMO main<-10 (oversold state)': main< -ob,
 'TTM fire & mom>0, exit mom falls': state_from(fire&(mom>0), mom<mom.shift()),
 'TTM fire & mom>0 hold 10d': fire.pipe(lambda f:(f&(mom>0)).rolling(10).max().astype(bool)),
 'TTM mom>0 & rising (state)': (mom>0)&(mom>mom.shift()),
 'IBS<0.2 1-day (reference)': IBS<0.2,
 'HYBRID IBS<0.2 & TMO main<0': (IBS<0.2)&(main<0),
 'HYBRID IBS<0.2 & TMO main>0': (IBS<0.2)&(main>0),
 'HYBRID IBS<0.2 & TTM squeeze on': (IBS<0.2)&sq,
 'HYBRID IBS<0.2 & TTM mom>0': (IBS<0.2)&(mom>0),
}
Us={'tech3':"QQQ SMH XLK".split(),'equity18':"SPY QQQ IWM DIA MDY XLK XLF XLE XLV XLI XLY XLP XLU XLB SMH XBI EEM EFA".split()}
print(f"{'rule':45s} {'universe':9s} expo   IS16-20 cagr/sh  OOS21-26")
for k,pos in rules.items():
    for un,U in Us.items():
        r,e=run_state(pos,U); print(f"{k:45s} {un:9s} {e:4.2f}  {st(r)}")
for un,U in Us.items():
    oo=O.shift(-2)/O.shift(-1)-1; print(f"{'buy&hold':45s} {un:9s} 1.00  {st(oo[U].mean(axis=1))}")
