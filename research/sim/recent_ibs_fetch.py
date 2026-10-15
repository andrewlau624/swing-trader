"""Extend EQ18 (+Roth look-alikes) raw SIP daily bars 2019-12-01..END into data/research/recent/etfd."""
import sys, os
REPO="/Users/andrewlau/Documents/Code/Projects/swing-trader"; sys.path.insert(0,REPO); os.chdir(REPO)
import pandas as pd
from swingtrader.data import _clients
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
S=["SPY","QQQ","IWM","DIA","MDY","XLK","XLF","XLE","XLV","XLI","XLY","XLP","XLU","XLB","SMH","XBI","EEM","EFA",
   "VGT","VFH","VDE","VHT","VIS","VCR","VDC","VPU","VAW","SOXX","IEFA"]
c,_=_clients()
for adj,nm in(("raw","etf_raw"),("all","etf_adj")):   # adj=all is total-return (dividends): what a holder across an ex-date receives
    df=c.get_stock_bars(StockBarsRequest(symbol_or_symbols=S,timeframe=TimeFrame.Day,start=pd.Timestamp('2019-12-01'),end=pd.Timestamp(sys.argv[1]),feed='sip',adjustment=adj)).df
    df.reset_index().to_parquet(f"{REPO}/data/research/recent/etfd/{nm}.parquet")
print(df.reset_index().groupby('symbol').timestamp.max().min(), len(df))
