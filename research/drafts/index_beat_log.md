# Index-beat hunt log (session llm-trader-ee, prompt_index_beat.md)

## STATE (update after every idea)
- program N: 761 (Jump hunt J1 took 761 on 2026-10-02; my next would be 762; none registered by this hunt yet)
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
- A20 (new, refill-in-round-1; track A, DD of "night exit later than the open" dead add. 7: never tested EARLIER): sell night
  picks in the PRE-MARKET instead of the open auction. Who pays: pre-market buyers (retail dip-buyers whose orders arrive
  04:00-09:28, before the open cross aggregates the day's sellers). Small account: pre-market depth is thin but a $100-1k
  order fits. Explore spec (written before any pre-market bar is fetched): picks = the raw night pool (Ns[0.10]) on
  select nights 2021-01..2023-12; Alpaca SIP minute bars 04:00-09:29 ET, raw. Exits vs the official open (1 + ret):
  V1 = sell at the VWAP of 09:00-09:28 minutes, minus 10bp extra (crossing a wide pre-market spread);
  V2 (the one further variant) = resting limit from 04:00 at close x 1.03, filled at the limit if any later pre-market
  minute high >= limit + $0.01, else the open. Per-pick improvement in bp (exit / open - 1), equal-weight and book-weighted
  (frac x tilt); pre-market $ volume after the fill time must be >= $1k or the fill is void. Select bar: mean improvement
  >= +5bp/pick with NW t >= 2 (by night) AND >= +5bp in each of 2021, 2022, 2023, AND ex-top-5-nights > 0.
- Killed by bound (no data run; counted as "killed", not "explored"):
  - A4 CEF->ETF conversions: residual discount ~1-3% over 2-6 months on <= the idle ~$1k at $2.3k, minus BIL foregone: <= ~$40-80/yr (< $150 deal bar).
  - A6 SPAC redemption below trust: annualized ~T-bill + 1-3% on idle cash -> +$10-30/yr at $2.3k; L16 closed for the same reason.
  - A12 insider 20-session hold in the Roth: L19 20d drift ~0 -> 0.
  - A13 13F first buys: TEXTBOOK (13F cloning decayed; 45-day stale) and heavy data; prior ~0.
  - A17 Hartzmark-Solomon dividend days: +3-6bp on ~10-20 days/yr on idle cash -> ~0.1pp.
  - A19 reverse-split names as night blacklist: ~75 names/yr, a few pick-nights a year -> ~0.
  - B8 night pool own-bounce dial: same family as AS (trailing-Sharpe/inverse-vol budget, dead) and the A5 vol-target; REFIT.
  - B10 capacity line, B11 IWM noise (AK dead), B14 fixed mechanism weights (AS family): no run by construction.
  - C6 0% LT gain harvesting: needs an index core held > 1y and the 0% bracket (C5 question); <= LT tax on the index gain, ~$0 at these sizes for years.
  - C7 December loss timing: wash deferral is timing-only and the book's Dec losses are small (add. 32 mech. 3) -> < 0.3pp.
  - C8 Treasury-only idle cash for CA tax: CA rate x yield x idle share ~ 4% x 4% x 0.4 -> < 0.1pp.
  - C10 broker IRA match (3%): the bot can't run at that broker; +$225/yr but loses the Roth book (worth ~+$400-1,100/yr over an index at $8.5k EH) -> negative.
  - C11 1256 index options for the noise leg: XND ~$21k notional > the noise leg at $2.3k; ~2-4bp/round trip vs the leg's ~+2bp/day gross -> dead on COST.
  - C13, C16: duplicates of C1/C2/C3 (done).
  - W2 Roth basis for April tax: allowed (contributions out tax-free) but no re-contribution: shrinks the tax-free account -> negative. W4 (price pattern, banned), W6 (#14 dead).
- A8 ID3 in the Roth's idle daytime cash: REPORT by bound (ID3's 2024-26 is already judged, so never FOUND): EH ~+3.5pp tax-free on $8.5k (~$300/yr) vs taxable ~+3.4pp after tax on $2.3k (~$80/yr); run ID3 in ONE account (wash) -> the Roth first, if ID3 passes its forward gate
