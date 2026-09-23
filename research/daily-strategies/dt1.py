import sys,os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from intra import load
import pandas as pd, numpy as np, pickle
SYMS=['SPY','QQQ','IWM','SMH','TQQQ','SOXL']
COST={'SPY':1,'QQQ':1,'IWM':1,'SMH':2,'TQQQ':2,'SOXL':3}
T=[]
for s in SYMS:
    M=load(s); O=M['open'].values; H=M['high'].values; L=M['low'].values; C=M['close'].values
    days=M['close'].index; pc=np.r_[np.nan,C[:-1,389]]; o=O[:,0]; gap=o/pc-1
    c2=2*COST[s]/1e4
    for i in range(1,len(days)):
        d=days[i]
        # A1 gap fill long: gap down, buy 9:35, exit at prev close (target) or 16:00
        if gap[i]<=-0.005:
            e=C[i,4]; tgt=pc[i]; x=C[i,389]
            hit=np.where(H[i,5:]>=tgt)[0]
            if len(hit): x=tgt
            T.append((d,s,'gapfill_long',-gap[i],x/e-1-c2))
        # A1b gap fill short: gap up
        if gap[i]>=0.005:
            e=C[i,4]; tgt=pc[i]; x=C[i,389]
            hit=np.where(L[i,5:]<=tgt)[0]
            if len(hit): x=tgt
            T.append((d,s,'gapfill_short',gap[i],1-x/e-c2))
        # A3 Gao et al: prev close -> 10:00 return predicts 15:30 -> 16:00
        r30=C[i,29]/pc[i]-1
        if abs(r30)>=0.005:
            sg=np.sign(r30); T.append((d,s,'lastHalfHour_mom',abs(r30),sg*(C[i,389]/C[i,359]-1)-c2))
        # A4 afternoon capitulation: down >= x from open at 14:30 -> buy, sell close
        r_pm=C[i,300]/o[i]-1
        if r_pm<=-0.01: T.append((d,s,'capitulation_long',-r_pm,C[i,389]/C[i,300]-1-c2))
        if r_pm>=0.01:  T.append((d,s,'meltup_short',r_pm,1-C[i,389]/C[i,300]-c2))
        # A5 strong trend day continuation: up/down >= x from open at 12:00 -> hold to close
        r_md=C[i,150]/o[i]-1
        if abs(r_md)>=0.01: T.append((d,s,'midday_trend',abs(r_md),np.sign(r_md)*(C[i,389]/C[i,150]-1)-c2))
        # A6 opening-drive fade: first 30 min move >= x vs open -> fade to close
        r_od=C[i,29]/o[i]-1
        if abs(r_od)>=0.01: T.append((d,s,'openingdrive_fade',abs(r_od),-np.sign(r_od)*(C[i,389]/C[i,29]-1)-c2))
df=pd.DataFrame(T,columns=['date','sym','setup','strength','ret'])
df.to_pickle(f"{os.path.dirname(os.path.abspath(__file__))}/dt_etf.pkl")
df['half']=np.where(df.date<'2024-01-01','IS 16-23','OOS 24-26')
# strength buckets by within-setup, IS-defined quantiles
out=[]
for (st,sym),g in df.groupby(['setup','sym']):
    qs=g[g.half=='IS 16-23'].strength.quantile([0.5,0.8,0.95]).values
    for lab,lo in [('all',0),('top50%',qs[0]),('top20%',qs[1]),('top5%',qs[2])]:
        h=g[g.strength>=lo]
        a=h[h.half=='IS 16-23'].ret; b=h[h.half=='OOS 24-26'].ret
        if len(a)<20: continue
        out.append(dict(setup=st,sym=sym,tier=lab,n_IS=len(a),IS_bp=a.mean()*1e4,IS_win=(a>0).mean()*100,IS_t=a.mean()/a.std()*np.sqrt(len(a)),
                        n_OOS=len(b),OOS_bp=b.mean()*1e4 if len(b) else np.nan,OOS_win=(b>0).mean()*100 if len(b) else np.nan))
R=pd.DataFrame(out).round(1)
pd.set_option('display.width',200); pd.set_option('display.max_rows',300)
# show the IS-best: t>=2.5 in-sample
good=R[(R.IS_t>=2.5)].sort_values('IS_t',ascending=False)
print("IN-SAMPLE CANDIDATES (IS t>=2.5), with their untouched OOS result:")
print(good.to_string(index=False))
print("\nHighest IS win rates (n_IS>=30):")
print(R[R.n_IS>=30].sort_values('IS_win',ascending=False).head(12).to_string(index=False))
