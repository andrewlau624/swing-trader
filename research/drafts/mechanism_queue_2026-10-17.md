# Mechanism queue — desk research, 2026-10-17 (no backtests, no N consumed)

Method: brainstormed ~90 forced-participant / contractual / structural ideas, then grepped NEXT.md and research/drafts/* for each.
The ledgers are close to saturated: only 6 ideas survive dedupe, and none clears the +8pp gate with confidence.
Gate formula: ceiling = events/yr x net edge/event x share of account deployable x capture (50% unless noted).
Sources: only papers confirmed by web search today are cited; everything else is marked UNVERIFIED.

## Ranked queue

### 1. TAIL-BID — resting far-from-market GTC bids to catch opening/flash dislocations (new; grep "stink|erroneous|flash" = no prior test)
- Mechanism: at the open or during LULD/flash events, liquid ETFs and large caps print 10-40% below fair value because market-maker quotes vanish and auction/pause collars are inconsistent. A cash limit bid placed in advance fills only on those prints.
- Other side: stop-loss and market sell orders (forced, price-insensitive) and market makers who withdraw. They must act because stops trigger mechanically.
- Persistence: the sellers are retail stops and risk-limit systems. LULD (2013) shrank the tail but did not remove it. SEC Aug-24-2015 staff note: 20 of the 50 largest ETPs fell >= 10%, 40%+ of US-equity ETFs paused, behavior was idiosyncratic. Confirmed in SEC Research Note "Equity Market Volatility on August 24, 2015" (Dec 2015; via CRS R45318). Comment letters cite inconsistent clearly-erroneous rules, i.e. bust risk is real and is the key unknown.
- Shape: rare trigger, large asymmetric payoff, near-zero cost when unfilled (capital sits in cash/BIL, so a Reg-T/cash-lock check is needed).
- Ceiling: 2 qualifying events/yr x 12% x 50% of account x 25% capture (busts, queue, broker rejecting far limits) = ~1.5pp at every size. Full capture ~6pp. Honest: below the gate.
- Data: TAQ 2003-26 in hand. The `corr` field should flag cancelled trades (UNVERIFIED code values); Alpaca minute bars 2016+.
- Cheapest kill: count first-print and flash prints >= 10% below the prior close or last-5-min reference in names with ADV >= $100M, 2010-2025. Then check what share were cancelled in TAQ and how fast they recovered. If < 1 event/yr survives busting, kill.
- Gate: no (about 1-3pp), but it is the only candidate with a true asymmetric shape.

### 2. MF-STALE — stale-NAV trading in open-end international / high-yield funds (new; grep "stale NAV|mutual fund NAV" = 0)
- Mechanism: funds strike NAV at 4pm from last-trade prices that are stale for foreign and thin securities, so the next NAV change is predictable from the US market's move.
- Other side: the fund's buy-and-hold shareholders, who are diluted. The fund must strike NAV by rule.
- Evidence (verified): Chalmers-Edelen-Kadlec, J. Finance 56(6), 2209-2236 (2001), predictability in domestic and foreign equity funds. Boudoukh-Richardson-Subrahmanyam-Whitelaw, Financial Analysts Journal 58(4), 53-71 (2002). Both say fair-value updating removes most of it, so the prior is that it is mostly gone after the 2003 scandal and fair-value pricing.
- Shape: daily conditional (only on days the S&P moves > ~1%, ~50-80 days/yr).
- Ceiling: 60 days x 20bp x 100% x 50% = 6pp, if any residual exists. After fair-value, likely 0. Schwab frequent-trading and redemption-fee rules would cap it further (UNVERIFIED per fund).
- Data: CRSP mutual fund daily NAV/returns in hand (to 2024-12).
- Cheapest kill: regress daily NAV return of international and high-yield funds on same-day and prior-day SPY and Asia/Europe ETF returns, split pre-2003 vs 2010-24. If post-2010 lagged-beta t < 3 or the implied edge < 10bp/event, kill.
- Gate: no, probably dead. A 1-day test.

### 3. BK-EMERGE-GV — Chapter 11 emergence equity, re-run with a clean old->new link (previous test: n=4, "data-limited"; reopen on low power)
- Mechanism: creditors (CLOs, banks and funds that cannot hold equity) receive new shares and must sell. The new stock is thin and often OTC/pink first, then re-rates.
- Evidence: Eberhart-Altman-Aggarwal, J. Finance 1999 (cited in jump_ideas R2-14). Ledger status: R2-14 explored-dead on n=4, golden_egg and NEXT:152 say DATA-LIMITED (no old->new link). Compustat gvkey and CRSP delisting codes now give the link, so n becomes ~150+ over 1990-2024.
- Shape: ~15-30 listed emergences/yr, 3-6 month hold, lottery tails.
- Ceiling: 15 events/yr x 0.5yr hold means ~100% deployed. A net median of +4% per 6 months gives ~8pp; +8% gives ~16pp. A pink-sheet or OTC fill is not guaranteed on Schwab, so apply a 50% haircut.
- Data: CRSP + Compustat in hand; Sharadar actions.
- Cheapest kill: median 120-day excess return vs size-matched controls, day-clustered, ex-top-5, 2x spread shock, on listed (NYSE/Nasdaq) names only.
- Gate: only plausible if the median is >= +4% net. The prior is low-moderate. Highest upside of the six.

### 4. MAND-CONV — mandatory convertible preferreds (DECS/PEPS/ACES) as a yield-plus-capped-equity substitute (new; only a stray mention in prompt_hidden_edges)
- Mechanism: the contract fixes the payoff at a known conversion date. Holders get a high coupon vs the common dividend but a capped upside. Whether the pref is priced rich or cheap against its replicating payoff is testable only with option inputs.
- Evidence: Arzac, J. Applied Corp. Finance 10(1), 54-63 (1997), covers valuation and rationale, not underpricing. No direct evidence found, so UNVERIFIED as an edge.
- Ceiling: ~20 listed issues alive at once, few liquid. 20 x 1.5% x 20% x 50% = 0.3pp. Roth-friendly but tiny.
- Data: SFP/ETD price data exist; there is no PIT term-sheet database (EDGAR text is needed).
- Cheapest kill: 10 issues, pref return vs replicating basket. Likely kill on ceiling alone.
- Gate: no.

### 5. DEBT-X — debt-ceiling X-date bill kink (new; grep "debt ceiling|X-date" = 0)
- Mechanism: bills maturing just after an X-date traded ~100bp or more above neighbors in 2011/2023 because money funds must avoid them. Treasury has always paid, only a few days late.
- Shape: ~0.3 events/yr (2025 limit raised, next X-date likely 2027+).
- Ceiling: 0.3 x 12bp (100bp annualized over 6 weeks) x 100% x 50% = ~0.02pp. Dead on ceiling. Note only as a standing watch item when the next limit approaches.
- Gate: no.

### 6. FUND-OCT — Oct-31 fiscal-year-end fund tax-loss selling -> November rebound in losers (new variant; adjacent to the closed December-loser class "TL-JAN / CEF-TL2: closed at prices-only data forever")
- Mechanism: funds with October fiscal years sell losers to harvest losses before the distribution date. A paper on this probably exists, but I could not verify it, so none is cited.
- Ceiling: 1 event/yr x 2-3% x 100% x 50% = ~1pp. Dead on ceiling and adjacent to a closed class.
- Gate: no.

## Verdict
- Nothing here clearly clears +8pp at $10k. Only BK-EMERGE-GV (if the median is large) and MF-STALE (if a residual exists) could, and both have low priors.
- TAIL-BID is the most novel in shape, with a cost of ~0 when it is wrong. Its ceiling is ~1-3pp.
- Suggested test order, by cost: MF-STALE (1 day, CRSP), TAIL-BID count (TAQ), BK-EMERGE-GV (CRSP/Compustat).
- The free-data space is exhausted, as the 10-08 events scan and the 10-16/17 overnight loop concluded. Further mechanism hunting is better aimed at new data classes than new mechanism lists.

## Considered and dropped (duplicates / closed)
- Lockup expiry: dead, Round 30 #7 -122bp (NEXT:1462, event_edge_candidates #26).
- Nasdaq-100 December recon, IPO quiet-period, covered-call ETF roll: ceiling-swept (deep_loop_ledger item 14).
- Index share/IWF updates, quarterly rebalance, Russell recon: region_ledger Z, Vb; shadow_russell_recon.
- CVRs: discovery_ideas_c5 I12 kill (non-transferable).
- ADR terminations: NEXT:1272 (killed by count). ADR vs home share: needs home prices; closed as the ETF premium/discount class.
- Treasury-closed/equity-open holidays, intl-holiday ETF mismatches: ETF premium/discount family closed (BSPD, ETC).
- Wash-sale rebuy: NEXT:1459 dead. Round-number clustering, $5 cliff: region_ledger C and K.
- Special dividends with due bills: goal_ideas G15, index_beat_log R3-2 (dead). Dividend initiations: event_edge_candidates #33.
- Going-private odd-lot cash-outs and all tenders: NEXT:1474, user ruling 10-17 (capital lock).
- Rights offerings: I6, small/manual. Cash/stock election proration: I11 low prior. Bankruptcy rights offerings: idea_scan_events #19.
- Bank sign-up bonuses, I-bonds, T-bill ladders: discovery_ideas_c5 C14, index_beat_ideas_r4 R4-4 (not market edges). Broker funding bonuses: loop_night FUND-LADDER.
- Congress (STOCK Act) trades: NEXT:1276 (no data, 403).
- Fire-sale / fund-flow selling via 13F: F13C-CAP killed; Coval-Stafford-style flows are blocked at the daily tier.
- 10b-18 blackout, SG-CTA, GSCI roll, FND, futures roll, basis: killed (region_ledger, parts 10-11).
- MMF-yield lag: ceiling about 5bp, not tested.
- Sell-to-cover on RSU vest days: ceiling < 0.5pp, no data.
- Warrant redemption triggers (de-SPAC): ~5-10 events/yr, arbitraged, ceiling < 0.3pp.
- Margin cascades, vol-ETP rebalance, SOQ/OPEX pin: closed (region_ledger M, VX, O).
- Treasury clearing mandate (Dec 2026 / Jun 2027): dealer-side, not retail-accessible.
- Sub-penny/tick-size and odd-lot round-lot reform: execution quality, not an edge.
