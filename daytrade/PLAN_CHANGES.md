# Plan changes

Every change to a plan in `daytrade/plans/`, dated, with why. A changed plan is a new variant: it gets its
own name (e.g. `gap_vwap_reclaim_v2`), its own pre-registration in `research/drafts/round1_prose.md`, and it
adds to the program N. Results of the old variant are never deleted.

| date | strategy | change | why | new variant / N |
|---|---|---|---|---|
| 2026-10-01 | gap_vwap_reclaim | created (Study Lab-AS) | first plug-in, the brief's popular pattern | N 669 -> 670 |
| 2026-10-01 | open_imbalance | created (Study Lab-AT) | first idea that needs the L1 recording | N 670 -> 671 |
| 2026-10-01 | orb_in_play | created (Study Lab-AU1 long+short, Lab-AU2 long only) | published ORB on Stocks in Play (SSRN 4729284), tested at real costs and out of sample | N 671 -> 673 |
| 2026-10-01 | gap_vwap_reclaim | clarification, written before any result: a signal skipped for R outside 0.2-5% does not end the day for that name; a later valid reclaim may still trade (still one entry per name per day). The ETF/fund name filter is the list in `daytrade/research/as_replay.py` (`NOT_COMMON`); it was narrowed once before the data was used (it had dropped real common stocks such as "Strategy Inc") | the plan's wording was ambiguous; code and plan must agree | not a new variant (nothing computed) |
| 2026-10-01 | open_imbalance | new variant Lab-AV: the same plan and code on historical SIP ticks, QQQ and SPY only (Lab-AT itself still waits for recordings) | Alpaca's free plan has historical SIP NBBO and trades | N 673 -> 674 |
| 2026-10-01 | vwap_trend | created (Study Lab-AW1 QQQ, Lab-AW2 TQQQ) | published VWAP trend (SSRN 4631351) at real costs, out of sample | N 674 -> 676 |
| 2026-10-01 | late_mover | created (Study Lab-AX) | the long mirror of a measured, untradable short effect (RESULTS.md: losers ≥ 25% by 15:00) | N 676 -> 677 |
| 2026-10-01 | halt_resume | created (Study Lab-AY1 halt-up long, Lab-AY2 halt-down long) | untested event class where small size is an advantage | program N 697 -> 699 |
| 2026-10-01 | close_cross | created (Study Lab-AZ1 long+short, Lab-AZ2 long only); exits in the 16:00 closing cross (a stated exception to flat-by-15:55) | first study on paid imbalance data (Databento) | program N 701 -> 703 |
| 2026-10-01 | halt_short | created (Study Lab-BA1/2/3: short the reopening after a halt) | Lab-AY: post-halt drift is down either way | program N 705 -> 708 |
| 2026-10-01 | halt_short | clarification before any result: Lab-BA3's "no SSR" test uses the last pre-halt price (> 0.9 x previous close), since the order is sent during the halt and the reopening print is not yet known | code and plan must agree | not a new variant |
| 2026-10-01 | close_cross | Lab-AZ untestable: the near price is 0 before 15:55 | registration error | N stays |
| 2026-10-01 | close_imbalance | created (Study Lab-BB1 long+short, Lab-BB2 long only): imbalance/paired rank at 15:54:30 | the observable part of the early NOII | program N 708 -> 710 |
| 2026-10-01 | close_imbalance | Lab-BB DEAD (gross +3.4bp < the 7.5bp spread); new variant Lab-BC: |r| >= the H1 q75, judged on H2 only | monotone dose-response in H1 | program N 710 -> 711 |
| 2026-10-01 | close_imbalance | new variant Lab-BD: QQQ every day, long r >= 0.2585 / short r <= -0.2824 (H1 quintiles), judged on H2 | cheapest instrument for a real but spread-bound signal | program N 711 -> 712 |
| 2026-10-01 | open_cross_reversal | created (Study Lab-BE1 long+short, Lab-BE2 long only) | the cross is entered at no spread; auction pressure reverts | program N 712 -> 714 |
| 2026-10-01 | open_cross_reversal | Lab-BE untestable (near price 0 before 09:28); new variant Lab-BF: decision 09:28:30, 30 names, top/bottom 2 | registration error; Databento budget | program N 714 -> 716 |
| 2026-10-01 | close_imbalance | new variant Lab-BG: Lab-BC signals with a passive limit at the touch until 15:55 (queue-aware fills from SIP trades) | test whether passive entry captures the real +6bp | program N 716 -> 717 |
| 2026-10-01 | event_drift | created (Study Lab-BH1 hold 20d, Lab-BH2 hold 5d) | multi-day drift after big announcement-day moves; costs paid once | program N 719 -> 721 |
| 2026-10-01 | event_drift | Lab-BH DEAD long (20d excess −185bp, every year); new variant Lab-BI: short + SPY hedge, judged on unseen 2017-2021 | the drift is a reversal in 2022-26 | program N 721 -> 723 |
