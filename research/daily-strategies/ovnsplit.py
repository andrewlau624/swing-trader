exec(open(__file__.replace('ovnsplit.py','ovnport.py')).read().split("rules={")[0])
import sys; sys.path.insert(0,SP); from tos import tmo
main,sg,ob=tmo(O,C)
sig=(day<=-0.08)&(ibs<0.1)
spyd=day['SPY']; mk=pd.DataFrame(np.repeat(spyd.values[:,None],C.shape[1],1),index=C.index,columns=C.columns)
vol20=np.log(C/C1).rolling(20).std()*np.sqrt(252); ret20=C/C.shift(20)-1
rv=(C*V)/advp
def ex(m,lab):
    x=on.where(sig&elig&m).stack(); x=x[np.isfinite(x)].clip(-.9,3)
    yr=x.groupby(x.index.get_level_values(0).year).mean()*1e4
    print(f"{lab:32s} n/day {len(x)/1499:5.1f} mean {x.mean()*1e4:6.1f}bp  win {100*(x>0).mean():4.1f}  yrs "+" ".join(f"{v:4.0f}" for v in yr.values))
ex(C>0,'ALL')
ex(main>ob,'TMO overbought'); ex((main<=ob)&(main>=-ob),'TMO neutral'); ex(main<-ob,'TMO oversold')
ex(mk<-0.01,'SPY day < -1%'); ex((mk>=-0.01)&(mk<=0.01),'SPY flat'); ex(mk>0.01,'SPY > +1%')
ex(vol20<0.6,'vol20<60%'); ex((vol20>=0.6)&(vol20<1.2),'vol20 60-120%'); ex(vol20>=1.2,'vol20>120%')
ex(ret20>0.2,'ret20>+20% (was running)'); ex((ret20<=0.2)&(ret20>=-0.2),'ret20 flat'); ex(ret20<-0.2,'ret20<-20%')
ex(rv<1.5,'rel$vol<1.5'); ex((rv>=1.5)&(rv<4),'rel$vol 1.5-4'); ex(rv>=4,'rel$vol>=4 (news?)')
wd=pd.DataFrame(np.repeat(C.index.dayofweek.values[:,None],C.shape[1],1),index=C.index,columns=C.columns)
for k,n in enumerate('Mon Tue Wed Thu Fri'.split()): ex(wd==k,f'weekday {n}')
