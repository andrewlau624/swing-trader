import sys,pickle; sys.path.insert(0,"/Users/andrewlau/documents/code/projects/swing-trader/data/research/swing"); sys.path.insert(0,"/Users/andrewlau/documents/code/projects/swing-trader/data/research/night")
__file__="/Users/andrewlau/documents/code/projects/swing-trader/data/research/night/t1550.py"; exec(open("/Users/andrewlau/documents/code/projects/swing-trader/data/research/night/t1550.py").read().split("for lab,sig,sc in")[0])
from noise import noise
night,_=port(S50,SC,maxw=0.1,cost=7.5)            # honest 15:50 signal, MOC in / MOO out, 7.5bp/side
qn,_=noise('QQQ',cost_bps=0.5)
e=pd.read_parquet("/Users/andrewlau/documents/code/projects/swing-trader/data/research/night/etf_daily.parquet"); e['date']=e.timestamp.dt.tz_convert('America/New_York').dt.normalize().dt.tz_localize(None)
EP={f:e.pivot(index='date',columns='symbol',values=f) for f in ['open','high','low','close']}
U=['QQQ','SMH','XLK']; I=(EP['close']-EP['low'])/(EP['high']-EP['low']); sg=I[U]<0.2; nn=sg.sum(axis=1); w=sg.div(nn.where(nn>0),axis=0).fillna(0)
oo=EP['open'].shift(-2)/EP['open'].shift(-1)-1
ibs=((w*oo[U]).sum(axis=1)-(w-w.shift(1).fillna(0)).abs().sum(axis=1)*1e-4).shift(1)
sw={}
for nm in ['res_base','res_all+ovn']:
    try:
        r=pickle.load(open(f"/Users/andrewlau/documents/code/projects/swing-trader/data/research/swing/{nm}.pkl","rb")); eq=r.equity if hasattr(r,'equity') else r[1].equity; sw[nm]=eq.pct_change()
    except Exception as ex: print('load',nm,ex)
df=pd.concat([night.rename('NIGHT losers@15:50'),qn.rename('DAY QQQ noise'),ibs.rename('IBS tech3 @open')]+[v.rename('SWING '+k) for k,v in sw.items()],axis=1,sort=True).loc['2021-02-01':'2026-09-18'].fillna(0)
df['COMBO day+0.5night']=df['DAY QQQ noise']+0.5*df['NIGHT losers@15:50']
df['COMBO day+night+IBS/2']=df['DAY QQQ noise']+0.5*df['NIGHT losers@15:50']+0.5*df['IBS tech3 @open']
print(df.corr().round(2).to_string())
print()
print(f"{'strategy':28s} {'CAGR':>6s} {'Sharpe':>6s} {'maxDD':>6s} {'+months':>7s} {'worstMo':>7s} {'+days':>6s} {'active days':>11s}")
for c in df:
    x=df[c]; yrs=len(x)/252; cagr=(1+x).prod()**(1/yrs)-1; sh=x.mean()/x.std()*np.sqrt(252); eq=(1+x).cumprod(); dd=(eq/eq.cummax()-1).min()
    pm=x.resample('ME').apply(lambda y:(1+y).prod()-1); act=(x!=0)
    print(f"{c:28s} {cagr*100:6.1f} {sh:6.2f} {dd*100:6.1f} {100*(pm>0).mean():6.0f}% {pm.min()*100:6.1f}% {100*(x[act]>0).mean():5.0f}% {100*act.mean():10.0f}%")
yr=df.groupby(df.index.year).apply(lambda y:(1+y).prod()-1)*100
print(); print(yr.round(0).to_string())
