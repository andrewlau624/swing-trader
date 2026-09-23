import sys,os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from gapload import *
import glob
meta,A=build()
ok=((meta.pc>=5)&(meta.pc<=1000)&(meta.adv>=10e6)&np.isfinite(meta.atr)).values
Op,Hi,Lo,Cl,Vo=A[:,0],A[:,1],A[:,2],A[:,3],A[:,4]
c2=2*10/1e4
T=[]
for i in np.where(ok)[0]:
    d=meta.date.iat[i]; s=meta.sym.iat[i]; g=meta.gap.iat[i]; pc=meta.pc.iat[i]; o=Op[i,0]
    # G1 gap-up fade short: gap>=10%, first 15 min red -> short at 9:45, stop at HOD+1%, cover close
    if g>=0.10 and Cl[i,14]<o:
        e=Cl[i,14]; stop=Hi[i,:15].max()*1.01; x=Cl[i,389]
        hh=np.where(Hi[i,15:]>=stop)[0]
        if len(hh): x=stop
        T.append((d,s,'gapup_fade_short',g,1-x/e-c2))
    # G2 gap-and-go long: gap>=10%, first 5 min green & rv5>=10 -> buy 9:35, stop 9:30-9:35 low, exit close
    if g>=0.10 and Cl[i,4]>o and meta.rv5.iat[i]>=10:
        e=Cl[i,4]; stop=Lo[i,:5].min(); x=Cl[i,389]
        ll=np.where(Lo[i,5:]<=stop)[0]
        if len(ll): x=stop
        T.append((d,s,'gap_and_go_long',meta.rv5.iat[i],x/e-1-c2))
    # G3 afternoon capitulation among gap-downs: down >=15% vs prev close at 15:00 -> buy, sell close
    r15=Cl[i,330]/pc-1
    if r15<=-0.15: T.append((d,s,'pm_capitulation_long',-r15,Cl[i,389]/Cl[i,330]-1-c2))
    # G4 gap-down squeeze: gap<=-10%, price above opening 30-min high at 11:00 -> buy, stop OR low, sell close
    if g<=-0.10:
        orh=Hi[i,:30].max(); orl=Lo[i,:30].min()
        if Cl[i,90]>orh:
            e=Cl[i,90]; x=Cl[i,389]; ll=np.where(Lo[i,91:]<=orl)[0]
            if len(ll): x=orl
            T.append((d,s,'gapdown_squeeze_long',-g,x/e-1-c2))
# G5: biggest losers of the day, 15:30 -> close (lm1 data, every stock down >=6%)
P=panel(); C_=P['close']; C1=C_.shift(1); advp=(P['close']*P['volume']).rolling(20).mean().shift(1)
for f in sorted(glob.glob(f'{SP}/lm1/*.parquet')):
    d=pd.Timestamp(f.split('/')[-1][:10]); df=pd.read_parquet(f)
    t=df.timestamp.dt.tz_convert('America/New_York'); df['hm']=t.dt.hour*100+t.dt.minute
    for s,g in df.groupby('symbol'):
        if s not in C_.columns: continue
        pc=C1.at[d,s]; a=advp.at[d,s]
        if not(pc>=5 and a>=10e6): continue
        g=g.set_index('hm'); 
        if 1530 not in g.index: continue
        p30=g.close[1530]; r=p30/pc-1
        if r<=-0.10: T.append((d,s,'eod_loser_1530_close',-r,C_.at[d,s]/p30-1-c2))
df=pd.DataFrame(T,columns=['date','sym','setup','strength','ret'])
df['half']=np.where(df.date<'2024-01-01','IS','OOS'); df.to_pickle(f'{SP}/dt_stk.pkl')
out=[]
for st,g in df.groupby('setup'):
    qs=g[g.half=='IS'].strength.quantile([0.5,0.8,0.95]).values
    for lab,lo in [('all',-9),('top50%',qs[0]),('top20%',qs[1]),('top5%',qs[2])]:
        h=g[g.strength>=lo]; a=h[h.half=='IS'].ret.clip(-.3,.3); b=h[h.half=='OOS'].ret.clip(-.3,.3)
        if len(a)<20: continue
        out.append(dict(setup=st,tier=lab,perweek=round(len(h)/295,1),n_IS=len(a),IS_bp=a.mean()*1e4,IS_win=(a>0).mean()*100,IS_t=a.mean()/a.std()*np.sqrt(len(a)),
            n_OOS=len(b),OOS_bp=b.mean()*1e4,OOS_win=(b>0).mean()*100,OOS_t=b.mean()/b.std()*np.sqrt(len(b)) if len(b)>2 else np.nan))
pd.set_option('display.width',220)
print(pd.DataFrame(out).round(1).to_string(index=False))
