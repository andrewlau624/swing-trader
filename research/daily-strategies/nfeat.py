__file__="/Users/andrewlau/documents/code/projects/swing-trader/data/research/night/t1550.py"
exec(open("/Users/andrewlau/documents/code/projects/swing-trader/data/research/night/t1550.py").read().split("S50=pd.DataFrame")[0])
import json, re
meta=json.load(open("/Users/andrewlau/documents/code/projects/swing-trader/data/research/night/asset_meta.json"))
def kind(s):
    n=(meta.get(s,{}).get('name') or '')
    if re.search(r'([123](\.5)?|-[123])[xX]\b|Ultra|Leveraged|Inverse|Bull\b|Bear\b|Daily .*(Bull|Bear|Target)|2x|3x', n): return 'levETF'
    if re.search(r'\bETF\b|ETN\b|Exchange Traded', n): return 'ETF'
    return 'stock'
vol20=np.log(C/C1).rolling(20).std()*np.sqrt(252)
ret20=C1/C1.shift(20)-1          # prior 20d, known before today
spyd=(C['SPY']/C1['SPY']-1)
advp_=advp
x=x[(x.day50<=-0.08)&(x.ibs50<0.1)].copy()
x=x[[ (C1.at[d,s]>=5) and (advp_.at[d,s]>=10e6) for d,s in zip(x.date,x.sym)]]
x['ret']=[O.shift(-1).at[d,s]/C.at[d,s]-1 for d,s in zip(x.date,x.sym)]
x['ret_from50']=[O.shift(-1).at[d,s]/p-1 for d,s,p in zip(x.date,x.sym,x.p50)]
x['vol20']=[vol20.at[d,s] for d,s in zip(x.date,x.sym)]
x['ret20']=[ret20.at[d,s] for d,s in zip(x.date,x.sym)]
x['adv']=[advp_.at[d,s] for d,s in zip(x.date,x.sym)]
x['spy_day']=[spyd.at[d] for d in x.date]
x['close_move']=[C.at[d,s]/p-1 for d,s,p in zip(x.date,x.sym,x.p50)]   # 15:50->close (NOT known at decision; diagnostics only)
x['kind']=[kind(s) for s in x.sym]
x['n_day']=x.groupby('date').sym.transform('count')
x=x[np.isfinite(x.ret)]
x.to_pickle("/Users/andrewlau/documents/code/projects/swing-trader/data/research/night/night_trades.pkl")
print(len(x), x.kind.value_counts().to_dict(), 'per day', round(len(x)/x.date.nunique(),1))
