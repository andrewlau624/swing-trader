# Daily-cadence strategy research (2026-09-22)

Scratch scripts behind RESULTS.md addendum 6. Not part of the package; not tested.
Each script expects its data next to it (downloaded by the `fetch_*.py` scripts,
SIP feed, ~2 GB total). `final.py` and `tmoveto.py` hard-code the original
scratchpad paths -- edit the two path constants before rerunning.

| script | what |
|---|---|
| fetch_sip_daily.py | SIP daily OHLCV+VWAP, whole universe incl. delisted, 2020-10 on |
| fetch_m1.py | SIP 1-min bars, SPY/QQQ/IWM/SMH/TQQQ/SOXL 2016 on |
| fetch_gap_m1.py | 1-min bars, top-40 |gap| stocks per day (selected from the open only) |
| fetch_late.py | 15:30-16:00 1-min bars for every stock down >=6% on the day |
| etf.py, etfport.py | IBS / RSI2 / overnight / intraday on ETFs |
| noise.py, orb.py | intraday momentum ("noise area") and opening-range breakout |
| tos*.py, tmoveto.py | Mobius TMO, TTM Squeeze, hybrids; TMO veto in the swing engine |
| ev1.py, gap1.py, gapsim.py | gap event study; gap fade / stocks-in-play ORB / reclaim with intraday stops |
| ovn*.py, t1550.py | overnight loser bounce; t1550 re-derives the signal at 15:50 (the honest version) |
| final.py | honest side-by-side of all legs + combo |
