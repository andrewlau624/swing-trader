"""LEG-HEALTH (pre-reg round1_prose.md, N 937->938): own-P&L 63-session kill switch on night and IBS legs. Frozen design.
Night: night_exact_pre2021 (2016-20, ret fraction) + night_replay (2021+, ret bp), 7.5bp/side. IBS: recent_ibs rule (top-3 EQ18 by
momentum_top, IBS<0.2, open d+1 -> open d+2), 5bp/side, adjusted panel = data/research/night/etf_daily (2016..09-21) spliced to
recent etfd adj (price-ratio rescaled at the last common date).  Run: python3 research/sim/leg_health.py"""
import sys, os
REPO="/Users/andrewlau/Documents/Code/Projects/swing-trader"; sys.path.insert(0,REPO); os.chdir(REPO)
import numpy as np, pandas as pd
from swingtrader.daily import signals as sg
EQ18=["SPY","QQQ","IWM","DIA","MDY","XLK","XLF","XLE","XLV","XLI","XLY","XLP","XLU","XLB","SMH","XBI","EEM","EFA"]
W=63; SEED=20261012; NP=200
def norm(e):
    e=e.copy(); e["date"]=e.timestamp.dt.tz_convert("America/New_York").dt.normalize().dt.tz_localize(None); return e
# ---- IBS
a=norm(pd.read_parquet("data/research/night/etf_daily.parquet")); b=norm(pd.read_parquet("data/research/recent/etfd/etf_adj.parquet"))
a=a[a.symbol.isin(EQ18)]; b=b[b.symbol.isin(EQ18)]
last=a.date.max(); ca=a[a.date==last].set_index("symbol").close; cb=b[b.date==last].set_index("symbol").close
k=(ca/cb).rename("k"); b=b.join(k,on="symbol"); 
for f in["open","high","low","close"]: b[f]=b[f]*b.k
e=pd.concat([a,b[b.date>last]])[["date","symbol","open","high","low","close"]]
P={f:e.pivot(index="date",columns="symbol",values=f) for f in["open","high","low","close"]}
O,H,L,C=P["open"],P["high"],P["low"],P["close"]; days=C.index; closes=C[EQ18]
rows=[]; mc={}
for j in range(260,len(days)-2):
    d,t=days[j],days[j+1]; m=t.to_period("M")
    if m not in mc: mc[m]=sg.momentum_top(closes[closes.index<t],t,3)
    uni=mc[m]
    tg=set(sg.ibs_targets({s:{"high":H.at[d,s],"low":L.at[d,s],"close":C.at[d,s]} for s in uni},0.2))
    for s in uni:
        o1,o2=O.at[t,s],O.at[days[j+2],s]
        if np.isfinite(o1) and np.isfinite(o2) and s in tg and abs(o2/o1-1)<0.5: rows.append((t,o2/o1-1))
I=pd.DataFrame(rows,columns=["entry","ret"])
ibs_pnl=(I.ret-2*5e-4).groupby(I.entry).mean()          # per-trade net, mean across the day's picks
ibs_cal=days[days>=days[261]]; ibs_cal=ibs_cal[ibs_cal<=days[-3]]
# ---- night
n1=pd.read_parquet("data/research/program/night_exact_pre2021.parquet").reset_index()[["date","ret"]]; n1=n1[n1.date<"2021-01-01"]
n2=pd.read_parquet("data/research/recent/night_replay.parquet")[["date","ret"]]; n2=n2[n2.date>="2021-01-01"]; n2["ret"]=n2.ret/1e4
N=pd.concat([n1,n2]); night_pnl=(N.ret-2*7.5e-4).groupby(N.date).mean()
night_cal=days[(days>=pd.Timestamp("2016-02-03"))&(days<=night_pnl.index.max())]
def stats(x,ppy=252):
    eq=(1+x).cumprod(); dd=(eq/eq.cummax()-1).min()
    r12=(1+x).rolling(252).apply(np.prod,raw=True)-1
    return dict(ann=x.mean()*ppy*100,vol=x.std()*np.sqrt(ppy)*100,sh=x.mean()/x.std()*np.sqrt(ppy) if x.std()>0 else np.nan,mdd=dd*100,w12=r12.min()*100)
def mdd(x): eq=np.cumprod(1+x); return (eq/np.maximum.accumulate(eq)-1).min()*100
out=[f"LEG-HEALTH  window {W}, seed {SEED}, placebo masks {NP}\n"]; verdicts={}
for name,pnl,cal in[("NIGHT",night_pnl,night_cal),("IBS",ibs_pnl,ibs_cal)]:
    x=pnl.reindex(cal).fillna(0.0)
    roll=x.rolling(W).sum().shift(1)             # sum of t-63..t-1
    w=(roll>=0).astype(float); valid=roll.notna(); x=x[valid]; w=w[valid]; xc=x*w
    off=(w==0).mean()
    out.append(f"== {name}: sessions {len(x)} ({x.index[0].date()}..{x.index[-1].date()}), first {W} sessions dropped (no trailing window); off share {off*100:.1f}%; pick-days {int((pnl.reindex(x.index).fillna(0)!=0).sum())}")
    res={}
    for h,(lo,hi) in{"all":("2000","2100"),"2016-20":("2000","2020-12-31"),"2021-26":("2021-01-01","2100")}.items():
        s0=stats(x[lo:hi]); s1=stats(xc[lo:hi]); res[h]=(s0,s1)
        out.append(f" {h:8s} always-on ann {s0['ann']:+7.2f}% vol {s0['vol']:5.1f} Sh {s0['sh']:+.2f} maxDD {s0['mdd']:7.2f}% worst12m {s0['w12']:7.2f}% | controlled ann {s1['ann']:+7.2f}% vol {s1['vol']:5.1f} Sh {s1['sh']:+.2f} maxDD {s1['mdd']:7.2f}% worst12m {s1['w12']:7.2f}% | off {(w[lo:hi]==0).mean()*100:.1f}%")
    blk=x.groupby(np.arange(len(x))//W).sum(); blk=blk[:len(x)//W]
    ac=[blk.autocorr(l) for l in(1,2,3)]; out.append(f" non-overlap {W}-session block P&L (n={len(blk)}) autocorr lag1..3: "+", ".join(f"{v:+.2f}" for v in ac))
    rng=np.random.default_rng(SEED); xv=x.values; wv=w.values; cr=xc.sum()*0; cm=mdd(xc.values); cann=xc.mean()*252*100
    pm=[];pa=[]
    for _ in range(NP):
        m=rng.permutation(wv); y=xv*m; pm.append(mdd(y)); pa.append(y.mean()*252*100)
    pm=np.array(pm); pa=np.array(pa)
    pct_dd=(pm<cm).mean()*100   # share of placebos with deeper maxDD than controlled
    pct_ret=(pa<cann).mean()*100
    out.append(f" placebo (day-level permuted mask, same off share): controlled maxDD {cm:.2f}% is shallower than {pct_dd:.0f}% of masks (placebo median {np.median(pm):.2f}, p90-shallow {np.percentile(pm,90):.2f}); controlled ann {cann:+.2f}% above {pct_ret:.0f}% of masks (median {np.median(pa):+.2f})")
    ok=[]
    for h in("2016-20","2021-26"):
        s0,s1=res[h]; r=s1['ann']>=s0['ann']-1; d=s1['mdd']>=0.75*s0['mdd']  # mdd negative: <=0.75x depth
        ok.append(r and d); out.append(f" gate {h}: ret>=on-1pp {r}; maxDD<=0.75x {d} ({s1['mdd']:.2f} vs {0.75*s0['mdd']:.2f})")
    plc=pct_dd>=90; out.append(f" gate placebo: shallower than 90th pct of masks: {plc}")
    v="PASS" if all(ok) and plc else ("WEAK" if (any(ok) and plc) or any(ok) else "KILL"); 
    if sum(ok)==1 and not plc: v="WEAK"
    verdicts[name]=v; out.append(f" VERDICT {name}: {v}\n")
out.append("Deviations: IBS uses the 2016 EQ18 history with 260-session warmup (first IBS entry %s); first 63 sessions per leg dropped; ann = mean daily*252 (arithmetic), maxDD on compounded daily equity; leg P&L = mean net return of the day's picks on entry date, 0 otherwise; placebo permutes the realized weight vector across days (day-level, exact off share); WEAK = one half passes (placebo counted as required for PASS, WEAK if either half passes or placebo alone cannot rescue)."%I.entry.min().date())
t="\n".join(out); print(t); open("data/research/program/leg_health_out.txt","w").write(t+"\n")
