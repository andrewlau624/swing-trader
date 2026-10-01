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
| 2026-10-01 | close_cross | created (Study Lab-AZ1 long+short, Lab-AZ2 long only); exits in the 16:00 closing cross (a stated exception to flat-by-15:55) | first study on paid imbalance data (Databento) | program N 699 -> 701 |
