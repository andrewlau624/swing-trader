"""Replay the LIVE IBS rule (top-3 of EQ18 by 12-1 momentum, IBS(d)<0.2, buy open d+1, sell open d+2) on RAW SIP daily bars
through the latest complete session (data/research/recent/etfd, research/sim/recent_ibs_fetch.py). No tuning. Control = same-day unconditional top-3."""
import sys, os, json, subprocess
REPO="/Users/andrewlau/Documents/Code/Projects/swing-trader"; sys.path.insert(0,REPO); os.chdir(REPO)
import numpy as np, pandas as pd
from swingtrader.daily import signals as sg
EQ18=["SPY","QQQ","IWM","DIA","MDY","XLK","XLF","XLE","XLV","XLI","XLY","XLP","XLU","XLB","SMH","XBI","EEM","EFA"]
LA=sg.WASH_LOOKALIKE
VAR=sys.argv[1] if len(sys.argv)>1 else "adj"   # adj = total-return (primary), raw = price only
e=pd.read_parquet(f"{REPO}/data/research/recent/etfd/etf_{VAR}.parquet")
e["date"]=e.timestamp.dt.tz_convert("America/New_York").dt.normalize().dt.tz_localize(None)
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
        if np.isfinite(o1) and np.isfinite(o2): rows.append((d,t,s,o2/o1-1,s in tg))
R=pd.DataFrame(rows,columns=["sig","entry","sym","ret","ibs"])
R=R[R.ret.abs()<0.5]
ctl=R.groupby("entry").ret.mean().rename("ctl")
T=R[R.ibs].join(ctl,on="entry"); T["exc"]=T.ret-T.ctl
def st(x):  # x: series indexed by entry date, bp
    g=x.groupby(level=0).mean() if x.index.duplicated().any() else x
    return len(x),x.mean(),x.median(),(x>0).mean()*100,(g.mean()/g.std()*np.sqrt(len(g)) if len(g)>2 and g.std()>0 else np.nan)
per=[("2021-25","2021-01-01","2025-12-31"),("2026 YTD","2026-01-01","2026-12-31"),("2026-06..10","2026-06-01","2026-12-31"),("2026-09-23..10-07 (live win)","2026-09-23","2026-12-31")]
out=[]
last=R.entry.max()
out.append(f"last scored entry {last.date()}; signals from 10-07 close (entry 10-08) not scorable; n IBS trades {len(T)}")
for name,a,b in per:
    x=T[(T.entry>=a)&(T.entry<=b)].set_index("entry")
    c=R[(R.entry>=a)&(R.entry<=b)].set_index("entry")
    if not len(x): out.append(f"{name}: none"); continue
    for cb in(0,2.5,5):
        n,mu,md,h,t=st(x.ret*1e4-2*cb); out.append(f"{name:28s} cost {cb}/side: n={n} mean={mu:+.1f} med={md:+.1f} hit={h:.0f}% t={t:.2f}")
    n,mu,md,h,t=st(x.exc*1e4); out.append(f"{name:28s} EXCESS vs same-day top3 basket (0bp): mean={mu:+.1f} med={md:+.1f} hit={h:.0f}% t={t:.2f}; basket all-days mean={c.ret.mean()*1e4:+.1f} (n={len(c)}, {len(x)/len(c)*100:.0f}% of slots fire)")
yr=T.groupby(T.entry.dt.year).ret.agg(["count",lambda s:s.mean()*1e4]); out.append("by year n/mean bp:\n"+yr.to_string())
mo=T[T.entry>="2026-05-01"].groupby(T.entry.dt.to_period("M")).ret.agg(["count",lambda s:s.mean()*1e4]); out.append("2026-05+ by month:\n"+mo.to_string())
# live overlay
fills=[]
for acct in("live","roth"):
    txt=subprocess.run(["ssh","him",f"cat llm-trader/logs/daily-fills-{acct}.jsonl"],capture_output=True,text=True).stdout
    for l in txt.splitlines():
        if not l.strip(): continue
        r=json.loads(l)
        if r.get("leg")=="ibs": r["acct"]=acct; fills.append(r)
F=pd.DataFrame(fills); F["date"]=pd.to_datetime(F.filled_at.str[:10])
inv={v:k for k,v in LA.items()}
b=F[F.side=="buy"].sort_values("date"); s=F[F.side=="sell"].sort_values("date")
trips=[]
for _,r in b.iterrows():
    nx=s[(s.acct==r.acct)&(s.sym==r.sym)&(s.date>r.date)]
    if len(nx): trips.append((r.acct,r.date,r.sym,inv.get(r.sym,r.sym),nx.iloc[0].fill_px/r.fill_px-1))
L_=pd.DataFrame(trips,columns=["acct","entry","sym","base","live"])
rp=R[R.ibs].set_index(["entry","sym"]).ret
L_["replay"]=[rp.get((r.entry,r.base),np.nan) for r in L_.itertuples()]
# raw replay of the exact traded symbol (Roth look-alike) for the same days
ro=lambda r: (O.at[days[days.get_loc(r.entry)+1],r.sym]/O.at[r.entry,r.sym]-1) if r.sym in O and r.entry in O.index and days.get_loc(r.entry)+1<len(days) else np.nan
L_["replay_sym"]=[ro(r) for r in L_.itertuples()]
out.append(f"\nLIVE IBS round trips (buy fill -> next sell fill): {len(L_)}")
out.append(L_.assign(live=L_.live*1e4,replay=L_.replay*1e4,replay_sym=L_.replay_sym*1e4).round(1).to_string(index=False))
mt=L_.dropna(subset=["replay"])
out.append(f"matched to a replay pick {len(mt)}/{len(L_)}: live mean {mt.live.mean()*1e4:+.1f} replay mean {mt.replay.mean()*1e4:+.1f}; corr {mt.live.corr(mt.replay):.3f}; replay picks in window {len(R[R.ibs&(R.entry>=L_.entry.min())])}")
# replay picks lacking a live trade
w=R[R.ibs&(R.entry>=L_.entry.min())]
out.append("replay picks in live window:\n"+w.assign(ret=w.ret*1e4).round(1)[["entry","sym","ret"]].to_string(index=False))
txt="\n".join(out); print(txt); open(f"{REPO}/data/research/recent/ibs_replay_{VAR}_out.txt","w").write(txt)
