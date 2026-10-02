# Reddit round (2026-10-02): r/algotrading sweep -> pre-registered tests

Source: a full read of r/algotrading 2021-01..2026-09 (41,472 posts via Arctic Shift; 1,807 substantive posts
with top comments read by 10 readers against the do-not-redo table). No new edge stood out; the items below are
the only ones not already in the table. **Written and committed before any outcome below was computed.**

Program N before this round: 761. Registered variants here: R1a, R1b, R6, R7 -> **N 765**.
Diagnostics (R2-R5) and engineering tests (R10) carry no N.

## R1 — 8-K "bad-news" items on the night picks (post 1q9fwug: unplanned CFO exits sell off for days)
- Picks: the shipped V7 night pool on raw prices (`book.night_days(raw_price=True, max_corr=0.7)`), as Study T.
- Tag: the issuer (EDGAR CIK, Study T's map and operating/periodic-filer filter) filed an 8-K (or 8-K/A) whose
  `items` include any of **5.02** (officer/director departure), **4.02** (non-reliance / restatement),
  **4.01** (auditor change), **3.01** (delisting notice / listing-rule failure).
- R1a window: accepted in (16:00 ET previous session, 15:40 ET pick day] (what the 15:40 scan could know).
- R1b window: accepted in (16:00 ET five sessions before, 15:40 ET pick day].
- Rule: **DROP** the tagged pick (weight 0; the rest of the night unchanged, no re-allocation).
- Pass (same bar as Study T, at `tier` AND `tier_hi` costs): >= 100 tagged picks 2021-26; within-night excess of
  tagged picks negative in both halves (2021-23, 2024-26); night-clustered t <= -2.0; within-night label
  permutation percentile <= 2.5; DROP book minus baseline > 0 pp/yr in both halves.
- If PASS: 15:40 live filter (EDGAR is already polled by `news_judge.sec_headers`), shadow first per the
  forward-test rule, registry entry in `testing.py`.

## R6 — gold overnight for idle overnight cash (post 1oaueck: LBMA overnight >> intraday for 50 years)
- Book: "T0L live today" (`program_books_res.pkl`, cost 3bp and tier_hi). Idle overnight share = 1 − night_used
  of the night half (the IBS half's idle cash is not changed).
- Rule: the idle share earns GLD close->open (bought in the close cross, sold in the open cross, 2bp/side, i.e.
  4bp a round trip) instead of r_cash on those nights.
- Pass: increment (rule − base, daily) > 0 in 2016-20 (holdout, uses T0L's `ho` series where available, else GLD
  C->O x 0.5 idle), 2021-23 and 2024-26; Newey-West (lag 5) t of the 2016-26 daily increment >= 2.0; book max
  drawdown not worse by more than 2 pp.

## R7 — implied-correlation gate (post 1rfhhw9: high VIX x high implied correlation = suppress single names)
- Signal: Cboe COR1M close at d−1, z-score vs its trailing 252 sessions. Gate on when z >= +1.0.
- Rule: night leg weight x0.5 on gate-on days (cash on the rest at r_cash).
- Pass: book Sharpe higher than base in 2016-20, 2021-23 and 2024-26 (both costs), and CAGR loss < 10% relative
  in 2021-26. (Precedent: SKEW z >= +1 sizing was declined; this is the correlation analogue.)

## Diagnostics (no N, no verdict)
- R2 EV2 tail dependence (post 1w07oen: 147,818 Form 4 buys, top 1% carry 71% of the mean; mean falls with size):
  EV2 / EV2-big judge-half mean with the best 1% / 5% of event-days removed.
- R3 auction cost by regime (post 1txx0zi): measured night exit cost vs the official open, split by SPY day return
  tercile and VIX tercile; does the worst tercile cross 10bp/side?
- R4 leg co-movement on bad days (posts 1udcdfz, 1scmm9t): correlation of r_night, r_ibs, r_noise over all days vs
  the book's worst 10% days; overlap of each leg's worst 50 days.
- R5 Alpaca paper reverse-split contamination (post 1shdc2e): paper night trades held across a split ex-date.

## Dead without a test
- R8 Congress (STOCK Act) trades: the free House/Senate Stock Watcher dumps return 403; no machine-readable source.
- R9 ClinicalTrials Phase 3 registrations: the jump hunt's D9 (first Phase 3) is already explored-dead (lottery).

## Engineering (R10)
- Causality test: the night-pick selector run on data truncated at the decision bar must return the same picks.
- Cost monotonicity: doubling the cost input must lower every leg's net.
