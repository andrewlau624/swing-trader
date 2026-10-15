# EXPLORATORY (touched data, no N): night-leg per-trade ret by same-day market state
import pandas as pd, numpy as np
from sharadar import prices
m = prices(['SPY','QQQ'], '2015-12-01', '2026-10-08', adjust="split", source="funds")
m['date']=pd.to_datetime(m['date'])
w = m.pivot(index='date', columns='ticker', values='close').sort_index()
o = m.pivot(index='date', columns='ticker', values='open').sort_index()
st = pd.DataFrame({'spy_d': w.SPY.pct_change()*1e4, 'qqq_d': w.QQQ.pct_change()*1e4,
                   'spy_gap': (o.SPY/w.SPY.shift()-1)*1e4,
                   'spy_on_next': (o.SPY.shift(-1)/w.SPY-1)*1e4})
a = pd.read_parquet('data/research/program/night_exact_pre2021.parquet').reset_index()
a['ret']=a['ret']*1e4; a['date']=pd.to_datetime(a['date'])
b = pd.read_parquet('data/research/recent/night_replay.parquet'); b['date']=pd.to_datetime(b['date'])
b = b[b.date>='2021-01-01']
t = pd.concat([a[['date','sym','ret']].assign(era='16-20'), b[['date','sym','ret']].assign(era='21-26')])
t = t.merge(st, left_on='date', right_index=True, how='left')
n = t.groupby('date').size().rename('ncand'); t = t.join(n, on='date')
cost=15  # 7.5bp/side
def clus(g):
    d = g.groupby('date')['ret'].mean()
    return pd.Series({'trades':len(g),'days':len(d),'mean':g.ret.mean(),'med':g.ret.median(),
        'daymean':d.mean(),'t_day':d.mean()/(d.std()/np.sqrt(len(d))) if len(d)>2 else np.nan,
        'net_day':d.mean()-cost,'spy_on':g.groupby('date').spy_on_next.first().mean()})
t['spyb']=pd.cut(t.spy_d,[-1e9,-150,-75,-25,25,75,1e9],labels=['<=-1.5%','-1.5..-.75','-.75..-.25','flat','+.25..+.75','>+.75'])
t['nb']=pd.cut(t.ncand,[0,2,5,10,1e9],labels=['1-2','3-5','6-10','11+'])
pd.set_option('display.width',200); pd.set_option('display.float_format','{:.1f}'.format)
for era in ['16-20','21-26']:
    x=t[t.era==era]
    print(f'== {era}: by SPY same-day close-to-close'); print(x.groupby('spyb',observed=True).apply(clus))
    print(f'== {era}: by # candidates that day'); print(x.groupby('nb',observed=True).apply(clus))
    x2=x.assign(q=np.where(x.qqq_d<=-100,'QQQ<=-1%','other'))
    print(f'== {era}: QQQ<=-1% days'); print(x2.groupby('q').apply(clus))
print('== SPY overnight after SPY day buckets (all days 2016-26)')
st['spyb']=pd.cut(st.spy_d,[-1e9,-150,-75,-25,25,75,1e9])
print(st.groupby('spyb',observed=True).spy_on_next.agg(['count','mean','median']))
