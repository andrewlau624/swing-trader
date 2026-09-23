import sys,os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from intra import load
import pandas as pd, numpy as np
def first_breakouts(sym, cost_bps):
    M=load(sym); C=M['close'].values; O=M['open'].values[:,0]; V=M['volume'].values; days=M['close'].index
    move=np.abs(C/O[:,None]-1); prevc=np.r_[np.nan,C[:-1,389]]
    pv=np.cumsum(C*V,axis=1)/np.maximum(np.cumsum(V,axis=1),1); rows=[]
    for i in range(15,len(days)):
        sig=move[i-14:i].mean(axis=0); ub=max(O[i],prevc[i])*(1+sig); lb=min(O[i],prevc[i])*(1-sig)
        pos=0
        for m in range(30,390,30):
            p=C[i,m]
            if pos==0:
                if p>ub[m]: pos=1; e=p; em=m; stren=(p/ub[m]-1)/sig[m]
                elif p<lb[m]: pos=-1; e=p; em=m; stren=(1-p/lb[m])/sig[m]
            else:
                if (pos==1 and p<max(ub[m],pv[i,m])) or (pos==-1 and p>min(lb[m],pv[i,m])):
                    break
        if pos==0: continue
        x=p if m<389 and ((pos==1 and p<max(ub[m],pv[i,m])) or (pos==-1 and p>min(lb[m],pv[i,m]))) else C[i,389]
        rows.append((days[i],pos,em,stren,pos*(x/e-1)-2*cost_bps/1e4))
    return pd.DataFrame(rows,columns=['date','dir','entry_m','strength','ret']).set_index('date')
for sym,cost in [('QQQ',0.5),('TQQQ',1.5)]:
    t=first_breakouts(sym,cost); t['half']=np.where(t.index<'2024-01-01','IS','OOS')
    print(f"\n=== {sym}: first noise-area breakout of the day, one round trip, {cost}bp/side")
    q=t[t.half=='IS'].strength.quantile([0,0.5,0.8]).values
    for lab,lo in zip(['all','top50%','top20%'],q):
        h=t[t.strength>=lo]
        for hf in ['IS','OOS']:
            r=h[h.half==hf].ret
            print(f"  {lab:7s} {hf:3s} n={len(r):4d} ({len(r)/(len(set(h[h.half==hf].index.year))*52):.1f}/wk) mean {r.mean()*1e4:6.1f}bp  win {100*(r>0).mean():4.1f}%  t {r.mean()/r.std()*np.sqrt(len(r)):4.1f}")
    # enforce PDT: max 3 round trips per rolling 5 sessions, greedy in time, strength >= IS median
    allidx=load(sym)['close'].index
    for lab,lo in [('all',-1),('top50%',q[1])]:
        cand=t[t.strength>=lo]; taken=[]
        for d in cand.index:
            pos=allidx.get_loc(d); recent=[x for x in taken if pos-allidx.get_loc(x)<5]
            if len(recent)<3: taken.append(d)
        r=cand.loc[taken,'ret'].reindex(allidx).fillna(0)
        for hf,sl in [('IS',slice('2016','2023')),('OOS',slice('2024','2026'))]:
            v=r[sl]; y=len(v)/252; c=(1+v).prod()**(1/y)-1; eq=(1+v).cumprod(); dd=(eq/eq.cummax()-1).min()
            print(f"  PDT-capped ({lab}) {hf}: {int((v!=0).sum()/y)} trades/yr, CAGR {c*100:5.1f}%, Sharpe {v.mean()/v.std()*np.sqrt(252):4.2f}, maxDD {dd*100:5.1f}%  (100% of equity, no margin)")

# ---- add to the current no-daytrade book: uses the night half's idle daytime cash (50% of equity)
S=pd.read_pickle(f'{os.path.dirname(os.path.abspath(__file__))}/series2.pkl')
base=0.5*S.night_new+0.5*S.ibs_new+0.5*(1-S.ibs_on)*S.bil
def capped(sym,cost,top):
    t=first_breakouts(sym,cost); idx=load(sym)['close'].index
    q=t[t.index<'2024-01-01'].strength.quantile(0.5) if top else -1
    cand=t[t.strength>=q]; taken=[]
    for d in cand.index:
        p=idx.get_loc(d)
        if len([x for x in taken if p-idx.get_loc(x)<5])<3: taken.append(d)
    return cand.loc[taken,'ret'].reindex(S.index).fillna(0)
def st(r,lab):
    out=[]
    for sl in [slice('2021','2023'),slice('2024','2026'),slice('2021','2026')]:
        v=r[sl]; y=len(v)/252; c=(1+v).prod()**(1/y)-1; eq=(1+v).cumprod(); dd=(eq/eq.cummax()-1).min()
        out.append(f"{c*100:5.1f}%/{v.mean()/v.std()*np.sqrt(252):4.2f}/{dd*100:4.0f}")
    print(f"{lab:46s} "+"  ".join(out))
print(f"\n{'combined, 2021-26':46s} {'2021-23':>14s}  {'2024-26':>14s}  {'full':>14s}")
st(base,'no-daytrade book now')
for sym,cost in [('QQQ',0.5),('TQQQ',1.5)]:
    x=capped(sym,cost,True)
    print(f"   corr with book: {np.corrcoef(x,base)[0,1]:+.2f}")
    st(base+0.5*x,f'  + {sym} PDT-capped top50%, 50% of equity')
