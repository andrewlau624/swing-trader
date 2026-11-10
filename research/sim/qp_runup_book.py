"""QP-RUNUP book replay (descriptive, no N): 2002-26 events from qp_init.py --runup, capital split across concurrent events,
idle cash at 0. Out: data/research/program/qp_runup_book_out.txt (python research/sim/qp_runup_book.py | tee ...)."""
import pandas as pd, numpy as np, pathlib
S=pathlib.Path.home()/'data'/'sharadar'
J=pd.read_parquet('data/research/program/qp_runup_out.parquet')
st=pd.read_parquet(S/'stocks.parquet',columns=['ticker','date','closeadj'],filters=[('ticker','in',list(J.ticker.unique()))])
st['date']=pd.to_datetime(st.date)
spy=pd.read_parquet(S/'funds.parquet',columns=['ticker','date','closeadj'],filters=[('ticker','in',['SPY'])]); spy['date']=pd.to_datetime(spy.date)
spy=spy.set_index('date').sort_index().closeadj.pct_change()
C=st.pivot(index='date',columns='ticker',values='closeadj').sort_index(); R=C.pct_change()
cal=spy.index[(spy.index>=J.de.min())&(spy.index<=J.dx.max())]
for costmult in (1,2,3):
  pos={}  # date -> list of (ticker, weight) daily returns
  rows=[]
  for r in J.itertuples():
    days=R.index[(R.index>r.de)&(R.index<=r.dx)]
    for i,d in enumerate(days):
        rows.append((d,r.ticker,R.at[d,r.ticker], r.c1*costmult/len(days)))
  D=pd.DataFrame(rows,columns=['d','t','r','c'])
  D['n']=D.groupby('d').t.transform('count')
  for cap in (1.0,0.5):
    # each active event gets cap/n of capital (fully deployed at 'cap' when any event active); rest earns 0
    port=(D.assign(x=(D.r-D.c)*cap/D.n).groupby('d').x.sum()).reindex(cal).fillna(0)
    eq=(1+port).cumprod(); yrs=len(cal)/252
    cagr=eq.iloc[-1]**(1/yrs)-1; dd=(eq/eq.cummax()-1).min(); sh=port.mean()/port.std()*np.sqrt(252)
    act=(port!=0).mean()
    b=np.polyfit(spy.reindex(cal).fillna(0),port,1)
    print(f"cost x{costmult} share {cap:.0%}: CAGR {cagr*100:+.1f}%  maxDD {dd*100:.1f}%  Sharpe {sh:.2f}  days active {act*100:.0f}%  beta {b[0]:.2f} alpha/yr {b[1]*252*100:+.1f}%")
    yr=port.groupby(port.index.year).apply(lambda s:(1+s).prod()-1)
    if cap==1.0 and costmult==1: print('  by year %:', ' '.join(f"{y}:{v*100:+.0f}" for y,v in yr.items()))
