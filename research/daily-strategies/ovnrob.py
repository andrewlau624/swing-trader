exec(open(__file__.replace('ovnrob.py','ovnport.py')).read().split("rules={")[0])
rng=np.random.default_rng(0)
def yr(r): 
    y=r.groupby(r.index.year).apply(lambda x:(1+x).prod()-1)*100; return " ".join(f"{v:5.0f}" for v in y.values)
print("grid: day<=D & ibs<I, maxw .1, cost 5 | full cagr/sh/dd | yearly % 2020..2026")
for D in [-0.05,-0.08,-0.12]:
    for I in [0.05,0.1,0.2,0.3]:
        r,n=port((day<=D)&(ibs<I),-day,maxw=0.1,cost=5)
        print(f"D{D:+.2f} I{I:.2f} {stats(r)[41:]}  yrs {yr(r)}")
sig=(day<=-0.08)&(ibs<0.1)
print("--- controls (day<=-8% & ibs<0.1 set)")
r,n=port(sig,-day,maxw=0.1,cost=0); print(stats(r,'gross'), yr(r))
r,n=port((day<=-0.08)&(ibs>0.5),-day,maxw=0.1,cost=0); print(stats(r,'anti: day<=-8% but IBS>0.5, gross'), yr(r))
# shuffle: same number of names per day, random eligible stocks
rand=pd.DataFrame(rng.random(elig.shape),index=elig.index,columns=elig.columns).where(elig)
k=(sig&elig).sum(axis=1)
rk=rand.rank(axis=1); rsig=rk.le(k,axis=0)
r,n=port(rsig,rand,maxw=0.1,cost=0); print(stats(r,'shuffle random names, same count, gross'), yr(r))
# SPY overnight benchmark
print(stats(on['SPY'].shift(1),'SPY overnight gross'))
# price/liquidity splits
for lab,m in [('price>=10',C>=10),('price 5-10',C<10),('adv>=50M',(C*V).rolling(20).mean().shift(1)>=50e6),('adv 10-50M',(C*V).rolling(20).mean().shift(1)<50e6)]:
    r,n=port(sig&m,-day,maxw=0.1,cost=5); print(stats(r,'split '+lab+' c5'), f"names {n[n>0].mean():.1f}")
