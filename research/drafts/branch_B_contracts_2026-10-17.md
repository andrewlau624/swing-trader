# Branch B — document-fixed payoffs with quick resolution (desk research, 2026-10-17; no backtest, no N)

Verdict: ZERO cards clear the +8pp gate. Two watch items (ETN issuer-suspension premium, ETN acceleration) have real documented
violations but are shorting/uncapturable or too rare. Method: grepped NEXT/MISTAKES/drafts first (most classes already dead), then
web evidence for the three live-looking classes. Sources opened: web search results only (WebFetch of businesswire 403); every figure
is attributed to the search result it came from. Period touched: none for performance. One descriptive price look: Sharadar SFP XIV daily bars Feb 2018.

## Candidate A (WATCH, not a card): ETN issuer suspends creations -> premium to indicative
- Mechanism: ETN price = indicative value only while the issuer creates units and APs/shorts can arbitrage. When the issuer stops issuing,
  the premium is unbounded. TVIX: Credit Suisse suspended issuance 2012-02-21 (prnewswire release); premium ~0.5% before, ~6% on 02-22,
  ~11% on 02-24, 10-20% for weeks, peak ~89-90% on ~03-21; creation resumed 03-22 and the premium collapsed (-30%, -30% on consecutive days). (etftrends, Forbes/Weinberg, sixfigureinvesting results).
- Violation size: huge (10-90%) but direction is a price ABOVE the contract value. The only capture is SHORT (or selling a held ETN): short was
  impossible (no borrow - the stated cause of the premium). Taxable shorting borrow-limited; Roth cannot short. Long side has nothing to buy.
- Frequency: a few suspensions per decade (TVIX 2012; similar ones for other leveraged ETNs, e.g. unverified). Ceiling at $10k:
  ~0.3 events/yr x short-only (inaccessible) -> 0. If only HELD-and-sell: user would have to already hold the ETN. Dead for this account (same "profitable side unharvestable" pattern as threshold-flow, SSR-LIFT, BORROW-XS).
- Trigger-based watch ONLY: if any issuer announces a creation suspension on an ETN we can short with borrow, premium > 10%. Not testable historically with a rule.

## Candidate B (WATCH): ETN acceleration event (XIV Feb 2018)
- Contract: if intraday indicative <= 20% of prior close, issuer may accelerate; payout = closing indicative value on the accelerated valuation date
  (CS release 2018-02-06, sec.gov ex9901). Indicative 02-02 $108.37; 02-05 close $4.22; final payout $5.99 on 02-15 indicative (two secondary sources, not an official doc I opened).
- Descriptive (Sharadar SFP XIV, my look): closes 02-06 7.35, 02-07 6.23, 02-08 5.10, 02-09 5.38, 02-12 5.34, 02-13 5.30, 02-14 5.93, 02-15 6.04.
  After the first day the price sat 0-15% below the eventual $5.99 payout. That is NOT a riskless violation: the payout floated with the inverse-VIX index through 02-15 (daily inverse
  vol moved 10%+/day), so buyers at 5.1 bore index risk. Premium of 7.35 and 10.49 open on 02-06 shows the opposite sign day 1 (buyers overpaying).
- Frequency: XIV 2018; Citigroup "Acceleration Series" ETNs (2020-03-19 headline only; not opened); Credit Suisse VelocityShares 2020. ~0-2 per year, concentrated in vol/oil crashes when spreads are wide and the product is a coin-flip on the index. Ceiling: 1 x ~10% x 25% of account x 50% = 1.2pp, and the 10% is not riskless. Below gate. No card.
- Caveat: credit risk on the issuer (CS 2023) is a downside of any ETN holding.

## Candidate C (DROPPED, closed already): OCC non-standard / adjusted options
- Real and documented: OCC Info Memo #59862 (2026-09-30, search result) - TORO1 deliverable already 100 TORO + $90 cash (memo #58854, 2026-05-04), to be adjusted again for AI OKTO spin (ex 2026-10-09). OCC itself says
  adjusted series are illiquid with widened spreads (SEC filing in results). Retail confusion and quote lag are documented by brokers (Webull, Merrill, optionstrading.org).
- Dead as an edge: repo index_beat_ideas_r6 R6-11 "Adjusted options after corporate actions: spreads 20%+, paid data -> killed". The prior 10-08 listing: options idea must clear a 2x spread shock; the wide spreads ARE the market
  makers' compensation for non-hedgeability, so a quote that violates deliverable parity by less than the spread is not capturable. Not retested; I have no per-series quote history (OPRA/OptionMetrics filter non-standards: unverified). Cheapest test if ever wanted: OptionMetrics opprcd rows with root suffix digits, far-side vs deliverable-intrinsic, count of days exceeding spread (WRDS, in hand) - ceiling-killed first, so not specified further.

## Dropped (with reference)
- Mandatory convertibles (DECS/PEPS): mechanism_queue item 4, ~0.3pp. Not retried.
- Listed CVRs: goal_log G25 killed (count); discovery_ideas_c5 I12 non-transferable.
- Rights offerings: idea_scan_events #9 dead by prior; I6 small/manual. Bankruptcy rights #19.
- ETN acceleration generically: idea_scan_events #5 <0.3pp (agree; XIV is the one big case and it is index-risk-bearing).
- Convertible prefs below conversion value: ~20 issues, wide spreads, same ceiling class as MAND-CONV (0.3pp). Merger arb final days: user-excluded class; parity gaps in the last 5 days are typically set by deal-risk residual and borrow cost; no document-fixed violation beyond the spread. Not examined with data.
- Stapled/dual-listed units, SPAC unit-vs-parts: no listed stapled pairs with quick convergence I could find; SPAC unit separation is tiny and SPAC floors are dead (idea_scan_events). Not examined with data.
- Called baby bonds/preferreds trading vs (par+accrued)/(1+r t): contract-fixed, but discount is bp-level and capital locks weeks; adjacent to PREF-EX carry (PREF-INDEX ceiling note).

## Honest read
The strongest violations (TVIX 2012, XIV day-1 2018) are prices ABOVE contract value, harvestable only by shorting names that were unborrowable; the tradable-long side
(XIV post day-1) bears index risk and pays ~0-15% once per several years. Document-fixed payoffs with a quick, riskless resolution and an accessible long side were not found.
