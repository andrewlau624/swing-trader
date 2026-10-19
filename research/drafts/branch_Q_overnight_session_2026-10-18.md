# Branch Q: retail overnight session (Schwab 24/5, BOATS) as a way to trade the after-close news gap (2026-10-18)
Verdict: ZERO surviving cards. KILL at descriptive probe + ceiling. No N consumed, no orders, no purchases, no repo code touched.
Probe script/outputs are scratch only (session scratchpad q_probe*.py/csv); the numbers below are descriptive, period 2024-10..2026-09 (a window the repo has already read for OVX; this probe is on a different object, earnings movers).

## 1. Access facts (Schwab-only)
- Schwab 24/5: ">1,100 securities ... 24/5", added S&P 500 + Nasdaq-100 stocks and ETFs; "via the thinkorswim platform suite"; order type EXTO; EXTO "expire at 8pm ET"; orders after 8:05pm go to the 7:00 pre-market. Press release https://pressroom.aboutschwab.com/press-releases/press-release/2025/Schwab-Announces-Further-Expansion-of-Overnight-Trading/default.aspx (opened 2026-10-18). Venue NOT named there; IRA eligibility NOT stated.
- Search-result summary of schwab.com/stocks/extended-hours-trading (page itself 403/blocked for WebFetch: UNVERIFIED verbatim): limit orders only for EXTO, no market/stop/FOK/IOC/AON; >1,300 stocks and ETFs (S&P 500, NDX 100, Dow 30, 600+ ETFs); thinkorswim only (not Schwab.com/mobile); "last trade price not displayed" for EXTO; best execution not guaranteed.
- UNVERIFIED: whether Schwab routes to Blue Ocean (BOATS). Whether Roth IRAs can place EXTO. Whether EXTO is available on margin vs cash differently. Confirm in the account before anything.
- 2026-12-06: Nasdaq/NYSE Arca (and Cboe EDGX, 24X) add a 9pm-4am exchange Night Session, limit orders only with static price bands, SIPs run 23h; official close stays 4pm. Sources via search results only (nasdaqtrader DN2026-8, Jones Day 2026/09, Troutman); branch_P_ideation row 2 opened Arnold & Porter/Troutman/Jones Day. Effect: more venues and an overnight SIP NBBO (so price discovery becomes observable and competitive); likely narrower spreads and more arbitrageurs, i.e. the mispricing, if any, shrinks. Schwab routing to the new venues UNVERIFIED.

## 2. Data
- Databento `OCEA.MEMOIR` = "Blue Ocean ATS MEMOIR" (publisher 107), 2025-08-24..2026-10-17; schemas mbo, mbp-1/10, tbbo, trades, bbo-1s, bbo-1m, ohlcv-*. Cost via metadata API only (nothing downloaded): trades ALL_SYMBOLS one day $0.05; bbo-1m all symbols one day $0.13; 10 symbols trades 1 year $5.75. So a 1-year NBBO/trade study of ~200 earnings nights is cents to a few dollars. NOT bought. (Only paid, and only 13.5 months deep.)
- Alpaca `feed=boats` 1-min bars (free, key in .env) from ~2024-10 for BOATS 20:00-04:00 (already used by research/sim/ovx.py:1-60; round1_prose.md:4926 OVX). Bars only: no quotes, so no spread. This is what the probe used.
- TAQ (WRDS): not checked for BOATS; ATS prints reach TAQ only via TRF with its session limits. UNVERIFIED; irrelevant given Alpaca + Databento.
- FINRA ATS weekly: volume only (data/research/finra/ats_etf.parquet exists, VENM). No prices.
- Dedupe: OVX/OVX-Q (N 870/872, NEXT.md:43, region_ledger_2026-10-06.md:50): BOATS/pre-market exit for night picks KILL, "premium" was the spread (bid -14bp vs open, half-spread ~24bp). index_beat_ideas R2-14 / B1 (23/5 forward specs) and branch_P row 2 (23/5 launch log) are the same family. Branch Q's new object is after-close NEWS names, not loser picks.

## 3. Literature (opened)
- Eaton, Shkilko, Werner, "Nocturnal Trading", 2025-03-16 draft (AFA PDF https://afajof.org/management/viewp.php?n=162176, abstract read): effective spreads at night worse than RTH, realized spreads similar or better; "significant price discovery ... between 8 p.m. and 4 a.m., particularly for exchange-traded products". Price discovery that "mostly does not reverse" (search-result summary, not read in the PDF). Implication against the hypothesis: overnight prices are informative, not noise to fade.
- Lim, "Overnight Adverse Selection", SSRN 6610883 (page 403: only search-result summary): ~7 cents higher effective spread overnight, a third adverse selection. UNVERIFIED beyond the summary.
- Nothing opened measures overnight price vs next 09:30 open around earnings.

## 4. Descriptive probe (Alpaca SIP + BOATS minute bars; S&P-500 earnings-event days from Sharadar events code 22, $vol>=$20M, 2024-10-02..2026-09-15)
Measure: "open minus venue" signed in the direction of the after-close SIP move (16:05-20:00 VWAP vs 15:59 close). Positive = venue UNDER-reacted vs the 09:30 open (open went further).
- A biased first cut (selected events with |open gap|>=6%, n=551 confirmed): venue sat ~100-120bp short of the open. This is SELECTION on the outcome (conditioning on the open), a look-ahead artifact; discard.
- Ex-ante version (random sample of 798 earnings-days, no gap filter; flag = |post-close move|>=3%, n=173; BOATS coverage thin, 94 with 02:00 prints):
  - BOATS ~02:00 (+/-30 min VWAP): median +37bp, mean +48, sd 328, share>0 0.60 (n=94). 03:30-04:00: median +28, mean +17, sd 305 (n=76). All-night VWAP: median +29 (n=129). Pre-market 09:28: median +6, sd 192.
  - Up-news only (the only arm a Roth can take long): at 02:00 median +24bp, MEAN -8bp (n=40); all-night median +14, mean -39 (n=60).
  - |post|>=5% (n=108): 02:00 median +41 / mean +60 (n=60); up-news mean -5; liquid BOATS (>=1,000 sh) up-news n=15, median +11, mean -63.
- Read: median under-reaction of tens of bp with dispersion ~300bp; mean near zero for the long arm; venue half-spread on these names unmeasured in bars but OVX-Q measured ~24bp half-spread for pick names and Lim reports wider overnight. A median of ~+30bp is at or below one round-trip cost; no direction-robust mean. Sample too small to tell +30 from 0.
- Nothing here supports "systematic mis-estimate of the open" with a size worth trading.

## Cards
None. Closest is an observation: pre-market 09:28 is nearly unbiased vs the open (+6bp), i.e. price discovery is complete by then, consistent with ESW "does not reverse".

## Ceiling (research-priority gate), for the best-case reading
Large after-close moves >=5% in Schwab-eligible S&P/NDX names: ~13% of ~2,000 earnings/yr, ~250/yr (random-sample rate 108/798 flagged at >=3%... ~21% of events; at >=5% ~14%). Only up-news long arm for Roth (down-news needs short; borrow plus overnight shorting UNVERIFIED). Say ~120 long up-news events/yr, but a limit-only EXTO buy of a news-spiking name at an overnight ask 24+bp above mid fills mostly when the price is moving against you (adverse selection). Best case: 120 x (+30bp - 25bp spread) x 20% of $10k x 50% = ~0.1pp/yr. Even ignoring cost: 120 x 30bp x 20% x 50% = 0.36pp. Gate +8pp: fails by 20x or more at every size ($2.3k/$10k/$25k; whole shares and thinkorswim-only EXTO make small accounts worse). At $100k the same percent edge scales only in dollars, not %/yr.

## Dropped
- Fade-overnight-overshoot / buy-overnight-sell-at-open on earnings: DROP (median +30bp, mean ~0, sd 300bp; ceiling <0.4pp).
- Down-news short arm: DROP (Roth no-short; taxable borrow plus EXTO limit-only; same weak edge).
- Night-pick exit in overnight session: already OVX/OVX-Q KILL.
- Other event types (M&A, upgrades, guidance, S&P adds) in the overnight session: DROP without test; arrival is in the gap but events/yr tradable in Schwab-eligible names x edge small; S&P adds are index-flow class already dead.
- 23/5 forward log (branch_P #2) remains a log-only idea, ~1pp one-time; the only new item is that Databento OCEA.MEMOIR bbo-1m gives retroactive overnight NBBO (cost cents-dollars) if the user ever wants the spread facts first; would not change the verdict absent a median > ~60bp net.

## If the user wants one more look (not recommended)
Pre-register: Databento OCEA.MEMOIR bbo-1m + trades, ~150 names x 2025-09..2026-09 earnings nights with |SIP post-close move|>=5% (flag fixed at 20:00, no outcome conditioning), executable fill = far side of BOATS NBBO at 02:00 limit, exit = official 09:30 cross; PASS = net mean > +60bp, day-clustered t >= 2, ex-top-5 > 0, both halves > 0. Cost est < $10. Judge on 2025-09..2026-09; touched after reading.
