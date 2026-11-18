# PREF-NOAUC (N 1210-1211, 2026-11-17): PREF-EX on no-auction closes

- 59% of PREF-EX events (2021-26, 4,972) have NO real closing auction ('6' print) on T-1 or T; Alpaca then lists only venue 'M'
  official-close prints (~25bp apart, sometimes sub-penny), and `crosses()` takes the largest = a price no MOC order trades at.
- The backtest edge does not live there: NOAUC cc +29.5bp vs AUC +25.7 (N 1210 not falsified). Ex-ante "had auctions 4/5 prior
  sessions" filter KILL (keeps 24%, lower cc, 2024-26 net +1.6bp).
- Live: '6' sessions cost 0bp (21/21 fills); no-'6' sessions ~+20bp RT real cost (+33/side mean, +11 ex one CDR.PRB outlier). PREF-EX
  net stays positive; the live-vs-backtest "pref fill +27bp" gap is this, not a routing fault. Measured costs on no-'6' days are partly
  measurement error (INN.PRE 11-16: picker took Nasdaq 16.50, NYSE close and our fill were 16.38).
- Not tested: open-auction analogs, MOC venue routing, LOC vs MOC, an M-print choice rule. Runner research/sim/pref_noauc.py.
