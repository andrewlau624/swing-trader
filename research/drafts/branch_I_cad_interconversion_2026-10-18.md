# Branch I - Canadian rate-reset pref interconversion pairs (2026-10-18)
Verdict: NO surviving card. Ceiling-kill (~1pp/yr at $10k) plus access-kill (IBKR/CAD, no shorting for the arb leg). No N consumed, no backtest.

## 1. Mechanics (opened sources)
- prefblog.com/?p=49375 (ENB.PR.F, 2018): elect window closed 2018-05-17 for a 06-01 exchange; 1:1 into floating Series G; if <1,000,000 of either series would result, no conversion (<1M fixed left: all forced to float). Reset = GoC5y + fixed spread; float = 3m T-bill + same spread.
- prefblog.com/?p=40254 (EMA.PR.F, 2020) and ?p=43178 (BPO.PR.E, 2022: 122,460 tendered of 1,000,000 needed): conversion often FAILS, so no floating series is created and no pair exists. Pairs exist only when the float series reaches 1M shares.
- prefblog.com/?p=29268, ?p=29407, ?p=29954 (2015, "Strong Pairs"): Hymas treats the pair as interconvertible at future dates but with different coupons, so the price gap today is the market-implied average bill rate, not a mispricing. IG pairs cluster tightly (implied bill rate 0.31-0.63% in 2015; +1.21% IG / +1.08% junk in 2018); junk pairs scatter more from illiquidity. His only "arb" is swapping in the market instead of electing, for "a small cash take-out".

## 2. Descriptive data (touched: 2017-06..2022-06, one pair; Datastream cached px, `data/research/intl_pref/px.parquet`)
- Datastream names do not encode fixed vs float; only ENB SR.B (fixed-reset) / SR.C (float, created 2017-06-13, delisted 2022-06-02) was mapped by hand. 1,166 CA PREF quotes, 167 live; automatic pair mapping needs TMX/issuer terms (not done).
- Float/fixed price ratio, quarterly means: 0.98 (2017Q2) -> 1.04-1.07 (2017Q3-2018, bills rising) -> 1.02 (2019) -> 0.97 (2020-21) -> 1.00 at the 2022-06-01 exchange (last prints 0.985-1.008). First days after creation: 0.95, then 1.005 within 4 sessions.
- Reading: the gap is the rate view (+/-5% range over 5y), converging to ~1.00 only at the contractual date; no stable pre-deadline mispricing observable beyond bid-ask noise (about +/-1% per print at $19, liquid ENB ~8k shares/day median).
- Not measured: mispricing around reset announcements, forced-conversion events, small-series delistings (needs a mapped pair list). Only n=1.

## 3. Ceiling at $10k (events/yr x payoff x deployable x 50%)
- ~20 reset pairs; ~4-8 exchange dates/yr, ~30-50% yield an actual float series; take-out per swap ~1-1.5% (Hymas "small"). 4 x 1.5% x 30% x 50% = ~0.9pp/yr; generous 8 x 2% x 30% x 50% = 2.4pp. $2.3k/$25k: same % (dollars scale; TSX pref volumes cap above ~$25k). Far under the +8pp gate.
- Downside: float leg is a rate bet (ratio ranged 0.97-1.07); a "long cheap leg only" has no hedge, short leg unavailable (Roth) and no CAD venue (needs IBKR, user decision). Lock: hold to exchange date up to 5y if not market-swapped; the electing form is a share-election lock (excluded by tender ruling).

## 4. Pre-registrable spec (not recommended)
Map all 167 live + delisted TSX fixed-reset/float pairs from issuer press releases; for each exchange date record ratio float/fixed adjusted for next-coupon difference at T-60..T+5 sessions; PASS needs median |adjusted gap| > 2x round-trip (about 100bp) in >=15 pairs. Judge 2005-2015 (untouched), 2016-25 touched only by the ENB pair above.

## Dropped
- Convergence arbitrage between series: coupons differ by design; gap = implied rate, converges only at the date (Hymas, ENB data above).
- Election-based capture: tender-ruling class (share election lock).
- Forced-minimum conversion trade: rare, small, unmeasured, below gate by ceiling.
- Cross-listed US: none exist.
