import pandas as pd, os
H=os.path.expanduser('~/data/sharadar/')
t=pd.read_parquet(H+'tickers.parquet')
c=t[(t.table=='SFP')&(t.category=='CEF Preferred')]
print(c[['ticker','name','isdelisted','firstpricedate','lastpricedate']].sort_values('name').to_string())
