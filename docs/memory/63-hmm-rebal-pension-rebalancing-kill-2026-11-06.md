# HMM-REBAL (2026-11-06, N 1080-1081): 60/40 balanced-fund rebalancing front-run, published form, KILL

- Source: Harvey-Mazzoleni-Melone, NBER w33554 (sample 1997-09..2023-03, ES vs TY): 1 SD calendar/threshold signal -> -17/-16bp next-day
  equity; strategy 10.2%/yr, Sharpe 1.11, skew 5.23 (GFC + Mar-2020 carry much of it).
- Tested exactly their weight (threshold averaged over d 0-2.5% /1.5%, + sign calendar signal in last 5 sessions + day-1 reversal) and the
  calendar-only arm, on SPY-IEF (2002+) and ^SP500TR vs a ^TNX-built 10y par bond (1988+), close->close, 2bp/side/leg.
- Judged on periods the paper never used: post 2023-03-20 (A1 +0.1%/yr t 0.03; A2 +0.9% t 0.21; 2025+ negative in both) and pre 1988-97
  (A1 -1.1% t -0.98; A2 -2.3% t -1.22). Pooled t -0.71 / -0.80. KILL.
- In the paper's window the replication works (ETF 2002-15 +7.4%/yr t 3.4; ex-GFC/Mar-20 +3.1% t 2.2): an in-sample effect that did not
  survive publication. Add. 34 (2016-26 MTD SPY-TLT as IBS sizing, M3 t 1.94) is the same phenomenon in a touched window; do not revive it.
- Not tested: ES/TY futures, intraday last-hour execution, quarter-end-only / |signal|-gated / high-VIX-gated subsets, the reversal leg alone,
  international, AUM-scaled signal.
- Files: pre-reg + result `research/drafts/round1_prose.md` (Study HMM-REBAL); runner `research/sim/hmm_rebal.py`; data
  `data/research/hmm_rebal/`; out `data/research/program/hmm_rebal_out.txt`; NEXT.md row; paper text-extracted copy not kept.
