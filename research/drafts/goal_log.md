# Goal hunt log (`prompt_strategy_goal.md`, session llm-trader-ec)

## STATE (update every iteration)
- round 2 · ideas written 20 (G1-G20) · k (judged) 10 · program N 774 (next free 775)
- NEAR: G2 (forward G2-F = ev2_big gate); G1 bound NEAR at $10k / FOUND-level at $2.3k if Schwab rounds B1 (VIVK ~10-07;
  check llm-trader state/roundup-orders.json after 10-07). Forward-only: G3 = `id3_big` gate.
- round-2 quota (40 = G1-G40): T1 5/8 (G2,G3,G11,G12,G20), T2 5/8 (G4,G5,G6,G14,G15), T3 6/8 (G7,G8,G9,G13,G16,G17),
  T4 3/8 (G10,G18,G19), T5 1/4 (G1) -> G21-G30 need T1 3, T2 3, T3 2, T4 5, T5 3
- NEXT: G11 data check (pre-2016 daily bars: Tiingo free tier key? Stooq? coverage of delisted names, raw vs adjusted),
  since G11 + G20 hinge on it; then G12 acceptance-time count.

## Notes carried in from other hunts (read 2026-10-02)
- Index-beat (llm-trader-ee): HAIRCUT: at edge-halves the live bot ~= SPY in both accounts; the only thing that beat the
  index at edge-halves was beta under the bot (R6-5 stacked on a SPY core, near miss). So any Goal book should be an
  overlay on an index core, not a replacement of it. No N registered there.
- EV2-big's >= $500k cut saw 2024-26; it can't be judged on 2024-26. Insider data here starts 2020-01 (events 2022+),
  so 2016-21 is untouched for every insider rule: that is the only honest holdout left for T1.
- llm-trader-3e's N = 593 message is stale (pre-Round 17); program N is 768 per llm-trader-51 / -ee.

## Log
- 2026-10-02 16:30 setup: read NEXT.md (dead list), prompt_hidden_edges.md, prompt_index_beat.md death map, EV2 study,
  index_beat_log STATE. Messaged all 6 peer sessions. Round 1: G1-G10 written before any outcome (T1 x2, T2 x3, T3 x3,
  T4 x1, T5 x1). Round quota so far: T1 2/8, T2 3/8, T3 3/8, T4 1/8, T5 1/4.
- 2026-10-02 16:45 G2 pre-registered (e6316e8, N 768 -> 772: G2a, G2b, two report rows). Correction to the
  registration text: "2016-20 has never been looked at for any insider rule" is not quite right: the Jump hunt's J2
  (insider buy after a 30% fall, +20% within 5 sessions) used 2016-23 insider buys on its select half. Different rule
  (conditioned on a crash, 5-day jump target), different exit; the EV2-big open->close rule was never computed on 2016-21.
  Using llm-trader-51's 2014-19 Form 345 zips (data/research/jump/insider/, read-only); my own duplicate downloads in
  night/insider were deleted so `outside_box.insider_buys()` (which globs that folder) can't change.
- 2026-10-02 17:00 **G2 judged: NEAR** (study_goal_g2.md). Holdout 2016-20, 195 trades: +68.7bp/trade (tier_hi +55.4),
  every year > 0, NW t 3.48, ex-best-5%-days +0.33 / ex-best-5-trades +0.46 (lottery test passes), null 100th pct, G2a
  after tax vs SPY +11.3pp ($2.3k and $10k, no deposits; +12.5 / +12.2 with $1k/mo), tier_hi +9.0-9.1pp, maxDD 31%,
  worst month −9.5% (2020-03), worst trade SPG −5.9% of equity; G2b (1.0x) +16.5..+21pp, maxDD 33-34%. Missed bar: a
  clean judge half (2024-26 saw the cut; untouched 2021 was −10bp/trade, t 0.09). DSR 0.553. Reported rows: EV2 all
  sizes ~0 (+7.9bp), ID3 >= $500k without silence +35.7bp x 1,788 trades, 2021 +23.8bp: the SIZE cut carries it.
  Follow-up G2-F registered (forward ev2_big gate, no new N). First judge run crashed on a dsr() dict print after the
  per-trade lines; rerun = same code, print fixed. Checked a suspicious 2021 IRR (+10.5pp on a ~0 overlay): deposit
  timing (all wins in Q4 on a larger account), not a bug; time-weighted numbers lead the write-up.
- 2026-10-02 17:15 **G1 bound (no N): NEAR at $10k.** From the registered deal tables: judge 2024-26 taxable deal $
  $725 at $2.3k (+20.5pp after tax) / $1,356 at $10k (+8.8pp); holdout +17pp / +13pp; Roth +4.4pp (B1 only). B1 rounding
  at Schwab unverified; without B1, $2.3k is ~+10pp. Nothing to build (all parts live). study_goal_g1.md.
- 2026-10-02 17:25 **G4 ADR terminations: KILLED at the count/mechanism step (no N).** EDGAR FTS 2016-26 (6-K/8-K/25/15F):
  "terminate its ADR program" 6 hits, "termination of its American Depositary" 9 hits, and most are ADR -> ordinary-share
  conversions (WNS, TotalEnergies, Cango: a 1:1 exchange onto a direct listing, no payoff). "termination of the deposit
  agreement" is F-6 boilerplate (1,300-1,900 hits/yr, all F-6 POS/EF). Genuine cash terminations ~1-2/yr, and the contract
  pays the depositary's FUTURE sale price of the local shares net of fees (months later, FX + local price risk): no fixed
  payoff, so by pipeline step 2 it is a price pattern, not a contract. TOO RARE + no contractual payoff.
- 2026-10-02 17:40 **G8 convertible pricing-day hedge shorting: DEAD on select** (registered ff2c554, N 772 -> 774).
  3,157 FTS hits -> 578 pricing press releases with an amount -> 327 events with bars, price >= $5; G8a (size/ADV >= 3)
  222 events 2016-26, G8b (no capped call / concurrent repurchase) 108. Select 2021-23, buy next open, hold 5, minus SPY:
  G8a n 63 mean −0.76% (tier) t −0.92; G8b n 26 −0.66% t −0.65. Gate (>= +1%, t >= 2) fails both: no recovery after the
  hedge is set; the pressure is in the pricing-day close or offset. Judge / holdout never run. 44% of deals carry a
  capped call, 19% a concurrent repurchase/share offering. Coverage: ~30 events/yr vs a market of ~100-200 deals/yr
  (only press releases with the exact phrases); a caveat, not a reason to rerun.
- 2026-10-02 17:50 **G6 issuer odd-lot programs: KILLED (count).** FTS 2016-26 "odd-lot program" 26 hits, mostly CEF
  N-2/POS 8C boilerplate and Canadian issuers (TELUS 2016, Advantage 2018) whose programs let < 100-share holders sell or
  round up AT MARKET without commission: no premium in the terms, ~1/yr. "odd lot sales program" / "small shareholder
  selling program" 0 hits, "odd-lot buyback" 1 issuer. No contract payoff; TOO RARE.
- 2026-10-02 17:55 **G5 dual-class collapses: KILLED (count).** FTS 8-K/proxies "eliminate the dual-class" 15 hits = ~12
  issuers in 10 years (AMSWA, CIX, Ford 2026, Forest City, GoPro, Lionsgate, Lyft, Monro, Nxu ...); "collapse of the dual
  class" 2 issuers. Most have only one listed class (the B class can't be bought), and where both trade (LGF.A/B, Forest
  City) the ratio-implied spread reprices on the announcement (GAP). ~1/yr tradable: TOO RARE.
- 2026-10-02 18:00 **G10 calls instead of shares on EV2-big: KILLED (bound, no N).** Analytic, conservative: a 5-day ATM
  call at IV 40% on a $50 name costs ~2.25% of S; the +69bp holdout drift x delta 0.5 = +15% of premium; theta over the
  session ~ −10% and gamma gives it back only if realized = implied (event days: IV is bid up, so assume no free gamma);
  a weekly single-name round-trip spread of ~5-10% of premium = ~16bp of S per 0.5-delta contract, i.e. ~32bp per
  share-equivalent vs ~5bp for the stock. Per unit of exposure options keep ~+37bp of the +69bp vs ~+64bp for shares:
  strictly worse in taxable. Their only use would be Roth leverage without margin, and the data to price it honestly
  (historical single-name option quotes) starts 2024-02 on Alpaca, inside the contaminated half. Many $20M-ADV names have
  no weeklies. Not worth a study; revisit only if G2-F passes forward and the Roth wants the overlay.
- 2026-10-02 18:05 **G9 S&P 400/600 replacement prediction: KILLED (bound, no N).** Already logged as "no free history"
  (event_edge_candidates #30: S&P DJI announcements are not archived machine-readably for free; the flagship S&P 500 add
  is dead because the move is in the announcement gap). Prediction prior is poor: an acquired SmallCap 600 member is
  replaced from hundreds of eligible names (often a MidCap 400 drop or a recent IPO); with 3 picks and P(hit) ~10%, the
  expected basket gain is ~1/3 x 10% x ~+5% pop = ~+0.2% per event before costs, ~0 after. Not runnable, not worth buying data for.
- 2026-10-02 18:20 **G7 424B2 autocallable barriers: KILLED (bound).** FTS "downside threshold" "common stock of" 424B2:
  ~1,100 (2018), ~3,000 (2022), 10,000+ (2025) supplements. Sample June 2023 (250 docs, 43 parsed): underlyings are mega /
  large caps (BX $61M, BAC $39M, AXP $28M, MSFT, NVDA, MA, XOM, AAPL), $5-60M per note. Even at 10x the parse rate, notional
  per name is ~1-10% of ONE day's ADV per month, and the barrier delta shift is a fraction of that spread over days, with an
  ambiguous sign: <= ~1-3% of a day's volume. No top decile worth trading; a 100k-document build for it is not justified.
- 2026-10-02 18:25 **G3 ID3 size dose-response: no clean window -> forward gate (no N).** 2016-21 was seen by G2's report row
  (ID3 >= $500k, any silence: +35.7bp x 1,788 trades, every year > 0, tier_hi +20.0bp, 2021 +23.8bp) and 2022-26 by the EV2
  diagnostics (buckets +5/+17/+23/+35bp). Every period is positive, but none is untouched. Added a forward-only sub-gate
  `id3_big` (insider_shadow.gate + testing.py REGISTRY entry "ID3 x buy >= $500k (any silence)", 60 trades), log-only.
  If it and G2-F both pass, the overlay would trade ~350/yr instead of ~40/yr (breadth, lower per trade).

### After 10 judged (round 1): what came closest and why it failed
Closest: **G2** (EV2-big intraday overlay on SPY): every registered holdout bar passed (+11pp/yr after tax at $2.3k and
$10k, lottery-proof), and it failed only on validation logistics: no clean judge half (the size cut was found on
2022-26) and a flat untouched 2021. Second: **G1** (contract stack): huge at $2.3k (+20pp) but per-holder caps don't
scale, so $10k misses (+8.8pp). Everything that died died the usual ways: TOO RARE (G4/G5/G6), COST (G10), GAP / no
recovery (G8), no data (G9), flow too small vs ADV (G7). **The gap the next 10 must aim at:** (1) mechanisms in the
own-money / forced-flow family whose history includes a window nobody here has looked at. The cheapest one: Form 345
goes back to 2006, so 2006-15 is untouched for every insider rule, but it needs pre-2016 daily bars (Alpaca starts 2016;
find a free raw-ish source or CRSP-like data). (2) payoffs that scale with the account, not per holder: breadth (many
events/yr) or size that the mechanism itself sets (e.g. issuer buyback EXECUTION disclosed in 10-Q tables, 10b5-1
adoptions by insiders who then buy, issuer self-tenders at a premium sized for all holders, forced index-fund flow in
second-tier indexes where flow/ADV is large).
- 2026-10-02 18:35 Round 2 part 1: G11-G20 written before any outcome (goal_ideas.md).
