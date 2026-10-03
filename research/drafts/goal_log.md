# Goal hunt log (`prompt_strategy_goal.md`, session llm-trader-ec)

## STATE (update every iteration)
- round 3 · ideas written 46 (G1-G46) · k (judged) 33 · program N 782 (next free 783)
- Open: G2 (NEAR; forward G2-F = `ev2_big` gate), G3 (forward `id3_big` gate), G21 (combined ~+21pp at today's balances;
  waits on Schwab rounding B1: VIVK ~10-07, check llm-trader state/roundup-orders.json after 10-07), G23 / G26 (wait on
  the forward gates). BLOCKED: G11 / G20 (pre-2016 bars). Everything else dead (see Log + NEXT.md dead rows).
- NEXT: G41/G46 (13F cache), G45 (CEF activist FTS count), G44 count. Check VIVK as soon as it settles (~10-07).

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
- 2026-10-02 18:50 G11/G20 data check: BLOCKED (see STATE). G12 count: of 300 random >= $500k officer/director buys
  2016-21, 13% accepted 09:30-15:30 (7% pre-market, 79% after 16:00) -> ~46/yr same-session candidates. G12 registered
  (N 774 -> 775).
- Index-beat hunt (llm-trader-ee) reports FOUND (structure, no N): SPY 1.0x + live legs on margin in taxable, Roth 1/3
  UPRO + 2/3 book; shadow swingtrader/daily/stack_shadow.py. My G1/G2 SPY-core overlays should be read as add-ons to
  that stack, not a second core.
- 2026-10-02 19:10 **G16 RSP equal-weight rebalance: KILLED (bound).** 4 events a year x a 5-session hold. Even at +1% per
  event on full equity, that is +4%/yr pre-tax, ~+2.6pp after tax: below the +5pp add-on bar, before any test. The flow is
  real (the biggest quarterly losers need ~10-20% of a day's ADV from RSP at ~$60B AUM) but too infrequent to matter at
  the book level. Also confounded with quad-witching closes (witching-day nights dead).
- **G17 SCHD reconstitution prediction: KILLED (bound).** One event a year: +5% on full equity once a year would be ~+3.3pp
  after tax with perfect prediction, below the add-on bar; prediction error and the GAP at announcement cut it further.
- **G15 due-bill specials: KILLED (count).** FTS 8-K "due bill" + "special dividend" 2016-26: 42 filings, ~25 issuers,
  ~3/yr. TOO RARE.
- 2026-10-02 19:20 **G14 spin-off regular-way vs when-issued pieces: KILLED (data + mechanism).** Alpaca SIP has spinco WI
  bars under mixed naming (GEHCV 12 bars, SOLV.WI 3, KD.WI 9, GEV.WI 3; VLTOV/SOLVV/KDWI none), and the parent's ex-distribution
  WI line almost never (GE.WD/GEWD/MMM.WD/DHR.WD none; JNJ.WD 3 bars). Without both legs the contractual sum can't be
  computed. Mechanism: both WI legs are shortable for arbs, so regular-way below the sum is arbitraged by people with
  capacity. A long-only small account has no advantage here (fails edge-test question 3).
- 2026-10-02 19:45 **G12 same-session insider buys >= $500k filed during market hours: DEAD on select** (registered
  41b08ed, N 775). 12,398 accessions >= $500k 2016-26 -> 1,286 accepted 09:30-15:20 -> 455 events with price >= $5 and
  ADV >= $20M. Select 2021-23: n 128, mean **+32.6bp** net (tier_hi + 5bp entry), median −5.3bp, hit 48%, t **+1.75**
  (2021 +24 / 2022 +91 / 2023 −5). The gate needs t >= 2: FAIL. The mean is carried by 2022 and a right tail; the typical
  trade loses. Judge / holdout not run. The insider edge looks like a next-day attention effect, not an intraday one.
- 2026-10-02 19:55 **G18 pre-deal SPAC warrant basket: KILLED (bound: REGIME + LOTTERY).** The only era with enough
  SPACs is 2020-23: ~600 IPOs in 2021, most liquidated in 2022-23 (their warrants went to 0), and after 2021 deal
  announcements stopped lifting warrants. Any 2021-23 select half is dominated by liquidations; a 2024-26 judge half has
  few new SPACs. A strategy whose sign depends on whether SPACs are in fashion fails "why would this work in 2017 AND
  2025?". Not run.
- **G19 warrants distributed to holders: KILLED (count).** FTS 8-K "warrants will be distributed" / "distribution of
  warrants" + record date, 2016-26: genuine warrant dividends to common holders ~3-6 a year (OXY 2020, CHK 2021, TGI 2022,
  SAVA 2023, GME / OPEN / ENVX / BBBY 2025, XRX / PSKY 2026), the rest SPAC / REIT boilerplate. TOO RARE for a book. Each
  outcome is option-like (OXY warrants went ~10x, others to 0): LOTTERY by construction. The 2025-26 uptick (meme-stock
  warrant dividends) is noted, not acted on.
- 2026-10-02 20:05 Round 2 part 2: G21-G30 written before any outcome (G29 killed at writing: calls cannot tender).
- 2026-10-02 20:20 **G21 combine: conditional FOUND-level (report, no N), study_goal_g21.md.** At today's balances (~$10.8k
  combined), 2024-26 after tax over SPY: index-beat stack +6.6pp + B1 round-ups +5.6pp + B2/tenders in the Roth +9.1pp =
  ~+21pp (+2.3pp more if G2 passes forward). Without the best 5 contract events ~+13pp. Conditional on (1) Schwab rounding
  B1 (VIVK ~10-07; without B1 ~+16pp) and (2) index-beat's edge-halves assumption (break-even 25%). Falls to ~+13-17pp at
  $25k and ~+10-15pp at $50k (per-holder caps). **G22 (contract payoffs in the Roth): already the default** in
  splitoff_buy.py / tender_buy.py (Roth cash first). **G28 (margin on B2 in taxable): dominated** by G22, dropped.
- 2026-10-02 20:40 **G30 transfer-agent fractional-share sales: KILLED (bound).** The aggregate fraction is < 1 post-split
  share per beneficial account (often netted at the DTC participant), ~$0.1-0.3M even in heavy-retail micro caps: a few % of
  ONE day's ADV, spread over days. No forced flow worth trading.
- **DL-G27 mutual bank conversions at $10: PAYS on its history but not usable as a bot strategy** (study_goal_dl27.md).
  18 standard/second-step conversions with data (2019-25): day-1 median +21.2%, hit 83%, worst −9.2%; 2023-25 weak. Fails
  >= 5/yr on the deals with data (~2.6/yr; ~7-12/yr exist), and eligibility needs a deposit account 1-2 years ahead at each
  mutual (residency limits, proration). A human project for the user, not a FOUND. First run had a bug (second steps'
  old minority shares counted as the IPO); fixed before the write-up.
- 2026-10-02 20:50 **G25 listed CVRs: KILLED (count).** FTS "contingent value rights" + "listed" + "Nasdaq" (8-K/S-4/425)
  2016-26: most hits are biotech reverse-merger CVRs that are NON-transferable ("will not be listed"); tradable listed CVRs
  ~1/yr (BMY-RT 2019, a few others). TOO RARE.
- **G24 deep-ITM SPY LEAPs vs UPRO for the Roth's beta: KILLED (bound).** UPRO: ~0.9% expense + swap financing + daily-reset
  drag. A 0.8-delta LEAP: financing at the implied rate + an IV-over-RV premium (~1-2%/yr of notional at 3x) + roll spreads.
  Under fair pricing the convexity the call buys roughly offsets the reset drag it avoids; the net is within ~1%/yr either
  way, sign unclear, and it can't be tested without SPY option history before 2024 (not free). Not an edge; a wrapper choice.

### After 20 judged: what came closest and why it failed
Closest: **G21/G1** (the shipped contract stack in the Roth + index-beat's stack): ~+21pp at today's balances, waiting on one
live fact (Schwab rounding B1). Then **G2** (EV2-big overlay, holdout pass, no clean judge) and **DL-G27** (thrift
conversions: +21% median per deal, but needs depositor eligibility years ahead). Since round 1 the failures were: TOO RARE
(G15, G19, G25), book-level too small (G16, G17), no data / arbitraged (G14, G24), weak t (G12: right mean, wrong median),
REGIME (G18), BLOCKED (G11/G20, pre-2016 bars). **Gap for G31-G40:** (1) breadth: mechanisms that fire >= 50 times a
year (only the insider family does so far), from broad free data (SEC XBRL frames, Form 345, FTS); (2) payoffs that scale
with capital, since every contract payoff caps per holder; (3) no more one-event-a-year index ideas.
- 2026-10-02 21:05 **G13 repurchase intensity >= 2%/quarter: DEAD on select** (registered dbb87bc, N 776). XBRL companyfacts
  for 8,008 CIKs -> 8,711 reported repurchase quarters (1,422 filers) -> 811 events with bars, price >= $5, ADV >= $5M.
  Filings 2021-23, hold 63 vs SPY, calendar-time: 260 positions, monthly excess +0.20%, NW t +0.34; per trade mean +0.26%,
  median −1.43%, hit 45% (2021 +0.78%/mo, 2022 +0.66, 2023 −0.71). Gate (>= +0.5%/mo, t >= 2) fails: the published
  actual-repurchase effect isn't there after 2020 (TEXTBOOK). Caveats: current filers only (company_tickers), split-hold
  events skipped. Program N is now 778 (llm-trader-ee PQ1 took 777-778). Jump hunt (llm-trader-51) STOPPED, not found.
- 2026-10-02 21:15 Round 2 part 3: G31-G36 written (follow-on stabilization floor, ATM exhaustion, SPY-core tax-loss harvest, preferreds / $25 notes below the change-of-control payoff, RSU vest selling). Stopped at 36: the remaining slots would be filler.
- 2026-10-02 21:25 **G34 preferreds below change-of-control par: KILLED (count).** FTS hits are issuance boilerplate. The
  real list (Alpaca cash-merger records whose root has a listed preferred, 2020-26): JCAP.PRB, CAI.PRA/B, QTS.PRA,
  MNR.PRC, NAV.PRD, KSU.PR, AHL.PRC, EFC.PRE/PRA, C.PRJ, FHN.PRB, CUBI.PRF, NLY.PRI (the last few are plain calls, not
  mergers): ~2-3 merger-driven $25 redemptions a year, and preferreds trade near par + accrued once the deal is public.
  TOO RARE, and the payoff per deal is ~1-3%. **G35 baby bonds with a 101% CoC put: KILLED (count).** FTS hits are 8-Ks for
  institutional note issuance (APH, CTAS, EA ...), not exchange-listed $25 notes; the put also needs a downgrade; the
  qualifying listed-note events are rarer still.
- 2026-10-02 21:45 **G31 follow-ons at the stabilization floor: DEAD on select** (registered b9ccd52, N 779). 3,077 FTS hits
  -> 1,029 common-stock follow-ons with bars and a parsed offer price (2016-26), 147 opening within 1% of the offer.
  Select 2021-23: conditional n 34, mean −1.22%, median −1.76%, hit 44%, t −1.51 (fails n >= 40 and the mean). All events
  bought at the open (report): n 281, +0.37%, median −0.42%, t 0.73. Stocks that open AT the offer price are the weak deals
  (stabilization fails); the floor isn't a floor.
- 2026-10-02 21:55 **G33 tax-loss harvesting the taxable SPY core: KILLED as a strategy (bound; a free habit, user's call).**
  Harvesting a loss L saves 35% x L now against the legs' ST gains but lowers the basis, so ~20% x L comes back as LT tax
  later: net ~15% x L plus deferral. SPY >= 5% below a rising (deposit-fed) basis happens ~once a year with L ~5-10% of the core
  -> ~+0.5-1.5pp/yr of the core. Real but small, and the SPY->IVV/VOO "substantially identical" question is the user's
  (or a tax adviser's), not research. Not pursued.
- **G32 ATM program exhaustion: KILLED (count).** FTS 10-Q "at-the-market" + "sales agreement" + "remaining available":
  34 (2018) .. ~125 (2022, 2025) filings a year, and the explicit exhaustion phrase ("no shares remain") only ~218 filings in
  10 years, repeated quarter to quarter: ~10 unique exhaustions a year, most followed by a new ATM. TOO RARE as an event,
  and too noisy to parse "% sold" reliably from free text.
- 2026-10-02 22:10 **G36 RSU vest selling (code-F clusters): DEAD on select** (registered 06716e0, N 780). 449,379 code-F
  filings -> 28,093 clusters (>= 5 owners in 2 days) -> 9,743 events at ADV >= $50M (2016-26). Select 2021-23: n 2,979 on
  617 dates, mean +0.03% vs SPY, median −0.12%, date-level −0.16%, t −1.00. Large caps absorb the vest-day selling.

### After 30 judged (round 2 closed): what came closest and why it failed
Nothing new came close in round 2. The best remain the **combinations of what already works** (G21 ~+21pp, conditional on
one live Schwab fact) and the **insider size effect** (G2 holdout pass, G3 breadth; both forward-only now). Every new
mechanism with breadth died on select with ~0 means (G8, G12, G13, G31, G36: forced or scheduled flows in liquid names are
absorbed), and every contract payoff was too rare (G4-G6, G15, G19, G25, G34, G35). The one positive new payoff, DL-G27
(thrift conversions), needs a human setup years ahead. **Gap for round 3:** (1) the only family with both breadth and
an effect is own-money insider buying. Find independent own-money signals with long free history (13F new positions by
small concentrated funds; issuer self-tenders; director buys in other documents) or a clean test window for the insider
size effect (pre-2016 data; a paid source). (2) Small names where flow / ADV is large: every liquid-name flow idea was
absorbed.
- 2026-10-02 22:20 Round 3 part 1: G41-G46 written before any outcome.
- 2026-10-02 22:40 **G42 / G43 insider size in thin names / vs market cap: both DEAD on select** (registered c1e1259,
  N 781-782). 19,507 officer/director buy events with bars (2016-26). **G42** (>= $500k, ADV $1-20M, hold 5 vs SPY): n 842,
  mean −0.13%, median −0.49%, date-t +0.23 (next-session report +0.05%). **G43** (>= 0.5% of market cap, ADV >= $2M): n 181,
  mean +0.89%, median +0.70%, date-t +0.96 (2021 −0.06 / 2022 +0.18 / 2023 +3.35%). The insider size effect lives in
  liquid names (ADV >= $20M: G2's holdout +68.7bp next session) and doesn't extend to thin names; G43's mean is one year.
