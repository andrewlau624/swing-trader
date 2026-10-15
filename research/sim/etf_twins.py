"""ETF twins: tracking stats of lower-priced execution twins vs IBS signal ETFs (Sharadar SFP, 2y)."""
import os, sys
import pandas as pd, numpy as np
f = pd.read_parquet(os.path.expanduser('~/data/sharadar/funds.parquet'))
SIG = {"SPY":["SPYM","SPLG"],"QQQ":["QQQM"],"IWM":["VTWO"],"DIA":[],"MDY":["IJH","SPMD"],"XLK":["FTEC","VGT"],
       "XLF":["FNCL","VFH"],"XLE":["FENY","VDE","IYE"],"XLV":["FHLC","VHT"],"XLI":["FIDU","VIS"],"XLY":["FDIS","VCR"],
       "XLP":["FSTA","VDC"],"XLU":["FUTY","VPU"],"XLB":["FMAT","VAW"],"SMH":["SOXQ","SOXX","XSD","PSI"],
       "XBI":["IBB","SBIO","PBE"],"EEM":["IEMG","VWO"],"EFA":["IEFA","VEA","SCHF"]}
want = set(SIG) | {t for v in SIG.values() for t in v}
f = f[f.ticker.isin(want)].copy()
f['date'] = pd.to_datetime(f.date)
start = pd.Timestamp('2024-10-06')
o = f.pivot(index='date', columns='ticker', values='open')   # raw open (split-consistent in SFP?) use closeadj ratio
ca = f.pivot(index='date', columns='ticker', values='closeadj'); cu = f.pivot(index='date', columns='ticker', values='close')
adjf = ca/cu
oadj = o*adjf
r = oadj.shift(-1)/oadj - 1                      # open-to-open
r = r[r.index >= start]
vol = f.pivot(index='date', columns='ticker', values='volume')
adv = (cu*vol).rolling(60).median().iloc[-1]
px = cu.iloc[-1]
rows = []
for s, tw in SIG.items():
    rows.append((s, s, px[s], adv[s]/1e6, 1, 0, 0))
    for t in [x for x in tw if x in r.columns]:
        d = pd.concat([r[s], r[t]], axis=1).dropna()
        c = d.corr().iloc[0,1]; te = (d[t]-d[s]).std()*np.sqrt(252)*100; dr = (d[t]-d[s]).mean()*252*100
        rows.append((s, t, px[t], adv[t]/1e6, c, te, dr))
out = pd.DataFrame(rows, columns=['sig','exec','px','advM','corr','TE%/yr','meandiff%/yr'])
pd.set_option('display.width',200); print(out.round(3).to_string())
print('data end', cu.index.max().date(), 'n days', len(r.dropna(how='all')))
