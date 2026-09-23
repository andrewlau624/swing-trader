import sys,os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from noise import *
d=pd.read_parquet(f'{SP}/etf_daily.parquet')
d['date']=d.timestamp.dt.tz_convert('America/New_York').dt.normalize().dt.tz_localize(None)
P={f:d.pivot(index='date',columns='symbol',values=f) for f in ['open','high','low','close']}
O,H,L,C=P['open'],P['high'],P['low'],P['close']
IBS=(C-L)/(H-L)
U=['QQQ','SMH','XLK']
sig=IBS[U]<0.2; n=sig.sum(axis=1); w=sig.div(n.where(n>0),axis=0).fillna(0)
oo=O.shift(-2)/O.shift(-1)-1
# IBS executed next open -> return realized over day t+1..t+2; attribute to day t+1 (the day the position is held)
ibs_r=((w*oo[U]).sum(axis=1)-(w-w.shift(1).fillna(0)).abs().sum(axis=1)*1/1e4).shift(1)
cc=C.shift(-1)/C-1
ibs_c=((w*cc[U]).sum(axis=1)-(w-w.shift(1).fillna(0)).abs().sum(axis=1)*1/1e4).shift(1)
nz,_=noise('QQQ',cost_bps=0.5)
df=pd.concat([ibs_r.rename('ibs_open'),ibs_c.rename('ibs_close'),nz.rename('noise')],axis=1).dropna()
print('corr\n',df.corr().round(3))
print(stats(df.ibs_open,'IBS tech3 @nextopen'))
print(stats(df.ibs_close,'IBS tech3 @close(MOC)'))
print(stats(df.noise,'QQQ noise 0.5bp'))
for a in [0.5]:
    print(stats(a*df.ibs_open+(1-a)*df.noise,f'50/50 blend(open)'))
    print(stats(df.ibs_open+df.noise,'stacked 1+1 (IBS open + noise)'))
    print(stats(df.ibs_close+df.noise,'stacked 1+1 (IBS MOC + noise)'))
