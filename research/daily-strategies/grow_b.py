from grow import *
def twr(df):
    r = ((df.E.diff() - df.dep.diff()) / df.E.shift()).dropna()
    return r
def line(lab, **kw):
    r = twr(replay(**kw)); y = r.groupby(r.index.year).apply(lambda v: (1+v).prod()-1)*100
    yrs=len(r)/252; t=(1+r).prod()**(1/yrs)-1
    print(f"{lab:44s} TWR {t*100:5.1f}%  Sharpe {r.mean()/r.std()*np.sqrt(252):4.2f} | " + " ".join(f"{a}:{b:5.1f}" for a,b in y.items()))
base = dict(whole=True, resplit=False)
for nc in [7.5, 12.5, 17.5, 27.5]:
    line(f"night cost {nc}bp/side, intraday 0.5bp", night_cost=nc, nz=noise_series(0.5,1.5), **base)
for ic in [0.5, 1.0, 1.5, 2.0]:
    line(f"night 7.5bp, intraday cost {ic}bp/side", nz=noise_series(ic,1.5), **base)
line("intraday leg ALONE (1.5x, 0.5bp)", nz=noise_series(0.5,1.5), ibs_w=0, night_w=0, **base)
line("night+IBS only (no intraday)", nz=None, intraday_on=False, **base)
