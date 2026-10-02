# Index-beat hunt log (session llm-trader-ee, prompt_index_beat.md)

## STATE (update after every idea)
- program N: 760 (no registration by this hunt yet)
- k (ideas judged): 0 · ideas explored: 10 (C1 C3 C5 C4 C2 reports; A1 = DL-IB1 conditional PAYS; B3 A9 A18 dead) · idea rounds: 1 (55 ideas)
- current idea: A2/A3 (spin-off / merger fractional round-ups, EDGAR FTS probe running)
- WAITING: DL-IB1 is FOUND only after 2 live rounded deals (VIVK ex 10-05, check ~10-07: state/roundup-orders.json on him)
- next 5: B8 -> killed as dup of AS (trailing-Sharpe budget, dead); A4 CEF->ETF conversions; A6 SPAC redemption; A13 13F first buys; B1/B2/B5 23/5 forward specs
- data sources verified: repo sims (program_books, taxable_frontier.after_tax, roth_opt), etf_daily (dividend-adjusted), night raw pool, roundup_deals.csv, Alpaca SIP daily bars (raw + 'all' adj, CEFs cached in data/research/program/ib/cef), EDGAR FTS (event_fetch.fts_years)
- data sources broken/unverified: E-mini overnight history (not free), option NBBO (paid), 23/5 quotes (forward only)
- why things die (running): HAIRCUT (C1/C2/C5: at edge-halves the taxable night+IBS legs ~= SPY pre-tax; placement wins only if the edge is half the backtest, loses if it is the backtest) / HALF-FLIP (C3, C4) / COST (A9 CEFs) / bound too small (A18) / no sign (B3); plus the prompt's map

## Log
- 2026-10-02 13:20 setup: merged, 356 tests pass, N 760 (last registered: EV2). Messaged llm-trader-51 (Jump hunt), 198-da.
- 2026-10-02 13:40 round 1: 55 ideas written before any outcome (16 C, 19 A incl. 9 deal payoffs, 14 B incl. 7 forward-only, 6 wildcards).
- C1 bot only in Roth + taxable SPY: C1-P -0.1..+0.2pp (2021-23), +3.6..+4.3pp (2024-26), +3.6..+4.8pp full -> NOT FOUND (one half). study_ib_c1_location.md
- C5 rate grid: at EH the taxable book loses to SPY held even at 0% (full $95.9k vs $111.9k); rate matters only without the haircut -> report
- C3 Jan Roth lump: +$296 / -$329 / +$60 per yr (2021-23 / 2024-26 / full) -> dead (half-flip, tiny)
- A1 / DL-IB1 (rule 7da5578): round-up in K accounts PAYS on history, $371/yr per account 2024-26 (ex-top5 $336), qualifying deals not falling; CONDITIONAL on Schwab rounding a 1-share holder -> not FOUND until 2 live rounded deals. study_ib_dl_ib1_roundup_accounts.md
- B3 intraday-margin rule (2026-07-13) close selling: night pool mean bounce post-rule +13.3bp (49 nights, t 0.3) vs 2025 same window +9.4bp; thin names -45bp -> no sign; explored-dead, no forward row. SIDE NOTE: night pool raw bounce 2026-01..07 +1.8bp/night (vs 2021-25 +29.5bp, t 2.7): a weak 2026 (observation only; switch-off rules are a known death)
- A9 CEF IBS — explore spec (written before any bar is fetched): universe U = the fixed list in research/sim/ib_a9.py
  (equity / option-income / multi-asset / bond CEFs), kept if 2020 median daily $ volume >= $2M (decided on 2020 only).
  V1 (primary): the live IBS rule on U (sg.momentum_top top-3 monthly, sg.ibs_targets ibs_max 0.2, buy next open, sell
  the open after), dividend-adjusted ('all') bars for returns, tier costs by price/ADV per side (B.cost_bps 'tier').
  V2 (the one further variant, threshold written now): no momentum filter; the 3 lowest-IBS names of U with IBS <= 0.10.
  Capital: the IBS half's idle cash only (0.5E - IBS used), in the taxable V7 book at $10k and $2.3k (whole shares).
  Select bar (2021-23 only, plus 2016-20 is the HOLDOUT so not used): per-trade net > 0 with t >= 2, AND the book
  increment pre-tax as backtested >= +6pp/yr at $10k (= the FOUND bar of +2pp after tax at edge-halves: 2 / 0.65 / 0.5).
- A9 CEF IBS explore (2021-23): 62 CEFs; V1 173 trades/yr gross +6.0bp, cost 10.9bp/side, net -15.8bp t -2.1 (every year < 0), book -9.6pp; V2 gross -2.4bp, net -25.2bp, book -18pp -> DEAD (COST; no gross reversal in CEFs). ib_a9.py, a9_explore.txt
- C4 475(f) + G0 vs plan G4s: tier -0.69 / +2.42 / +1.18pp (2021-23 / 2024-26 / full), tier_hi -1.33 / +1.06 / +0.08pp -> DEAD (half-flip; G0 would disallow 64-73% of losses without 475). ib_c4.py, c4_out.txt
- A18 whole-share leftovers at $2.3k: bound only (no run of a variant). V7 2021-23 night leg uses 32% of its half at $2.3k whole vs 39% fractional; whole shares EARN MORE (+3.18 vs +1.35%/yr: rounding drops high-priced names, which bounce less). Leftover redeployment prize <= 7% of the leg -> < 0.5pp -> DEAD (bound)
- C2 taxable SPY + noise leg only, Roth without QQQ/SMH IBS: EH $1k/mo +1.19/+2.01pp (tier), +1.29/+2.21 (tier_hi); $2k/mo +2.11/+3.18, +2.21/+3.36; as backtested -1.7..+0.8 in halves -> NOT FOUND (fails 2021-23 at $1k/mo; haircut-dependent). study_ib_c2_spy_noise.md
