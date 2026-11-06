"""BOATS-PREM/BOATS-LETF post-hoc checks (NOT judged): PX at the BOATS mid instead of the bid; LETF rich side per pair and ex-SOXL/SOXS. usage: PYTHONPATH=. python3 research/sim/boats_asia_posthoc.py"""
import numpy as np, pandas as pd
import research.sim.boats_asia as M
M.log=lambda *a: print(*a)
cal=M.calendar(); O,C=M.crosses(); ci=pd.DatetimeIndex(cal); O=O.reindex(ci); C=C.reindex(ci); nO=O.shift(-1)
B,A=M.quotes("2300",cal); B=B.reindex(ci); A=A.reindex(ci); Mq=(B+A)/2; lv=B["QQQ"].dropna().index
Dm=(Mq-nO)/C*1e4
a=[s for s in M.ASIA]; c=M.CONTROL
M.stats(Dm.loc[lv,a].mean(1)-Dm.loc[lv,c].mean(1),"PX at MID (post-hoc)")
M.stats(Dm.loc[lv,a].mean(1),"D_ASIA at mid"); M.stats(Dm.loc[lv,c].mean(1),"D_CONTROL at mid")
for ex in [set(), {"SOXL","SOXS"}]:
  rows=[]
  for le,u,L in M.PAIRS:
    if le in ex: continue
    fair=C[le]*(1+L*(Mq[u]/C[u]-1)); db=B[le]/fair-1
    exh=(B[le]-nO[le])/nO[le]-L*(Mq[u]-nO[u])/nO[u]; raw=(B[le]-nO[le])/nO[le]
    for d in lv:
      if np.isfinite(db[d]) and np.isfinite(exh[d]) and db[d]>=M.X_LETF: rows.append((d,le,exh[d]*1e4-1,raw[d]*1e4-1))
  R=pd.DataFrame(rows,columns="d pair exc raw".split())
  print("excl",ex, R.groupby("pair").exc.agg(['size','mean','median']).round(1).to_dict('index'))
  s=R.groupby("d").exc.mean(); s.index=pd.DatetimeIndex(s.index); M.stats(s,"rich hedged")
  s=R.groupby("d").raw.mean(); s.index=pd.DatetimeIndex(s.index); M.stats(s,"rich UNHEDGED (sell bid vs open)")
# SOXX quote sanity: spread & D of SOXX itself
print("SOXX half-spread med", ((A.SOXX-B.SOXX)/Mq.SOXX*1e4/2)[lv].median(), "SOXX mid-open D", Dm.SOXX[lv].mean(), Dm.SOXX[lv].median(), "QQQ", Dm.QQQ[lv].median())
