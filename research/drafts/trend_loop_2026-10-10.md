# Trend-filter research loop (started 2026-10-10)
Queue: 1 TREND-NIGHT, 2 IBS 200d/10m SMA filter, 3 SPY 10m SMA book gate, 4 ETF category TSMOM sleeve, 5 pivot. Program N at start: 916.

## Idea 1 — TREND-NIGHT (N 916 -> 919)
- Dedupe: not killed (20d/52w distance tilts dead add.23; IBS trend filter AT harmful; ma200 state of the loser left OPEN in idea_scan 10-08).
- Ceiling: 140 nights/yr x +10bp x 0.5 weight = +7pp/yr proxy (~+4pp exact rule) > +1pp filter gate. Cheap (daily bars).
- Pre-registered in round1_prose.md (3 arms TA/TB/TC: 200d SMA, 126d ret, 252d ret on bars before the shock day). Judge 1999-2015, report 2016-26.
- Result: **FAIL x3, wrong-signed.** 1999-2015 diff vs base: SMA200 -21.1bp t -3.74 (halves -27/-15, ex-top5 -25), 126d -16.0 t -2.96 (-19/-13, -20),
  252d -23.4 t -3.86 (-33/-14, -22); 2016-26 all -12..-16 (t -1.5..-2.0). Uptrend picks earn <= downtrend picks per trade. Class closed: trend-conditioning on MR legs
  (TREND-NIGHT + AT on IBS). Bug caught: cumsum SMA lost precision (Sharadar adjusted closes up to ~1e10); fixed with per-ticker rolling mean, TB/TC unaffected.
- Lead (peeked, descriptive): young listings (< 252 prior bars) +83/+74 (mean/median) vs +43/+41 old in 1999-2015; +66/+55 vs +26/+22 in 2016-26; positive in
  11/15 and 7/10 years. Queue as YOUNG-NIGHT (pre-register as a peeked lead; dedupe IPO/listing-age first; strip ticker-change contamination via permaticker).
- Program N = 919.

## Idea 2 — IBS leg 200d / 10-month SMA trend filter
- Dedupe: AT (NEXT ~line 619) already killed a 50d trend-slope filter on IBS picks (-7pp/yr, t -3.1, "never add a short trend filter to an MR leg"); SHAR-IBS
  pre-2016 and TREND-NIGHT both say downtrend dips revert as much or more. A 200d/10m filter is the same idea at a longer lookback = re-tuning a failed idea.
- Verdict: SKIP (killed by dedupe + class closure). No N consumed.


## Idea 3 — REGIME-10M: SPY 10-month SMA gate on the whole book (N 919 -> 922)
- Dedupe: 200dma gate only judged on 2021-26 (add. 37, "buys Sharpe for return"); never run through 2000-02/2007-09 on the delisted-complete book. Allowed.
- Ceiling: ~30% of months OFF; adds return only if OFF nights earn <= 0 (prior: the legs earn more in bear/high-vol -> likely costs return). Cheap (SHAR-CRASH harness).
- Arms: G1 book OFF, G2 night OFF, G3 IBS OFF. Gate: no CAGR cost (>= base - 0.5pp), maxDD 2000-02 and 2007-09 both >= 5pp better, Sharpe up, OFF nights earn <= 0 in both halves.
- Result: **FAIL x3.** OFF sessions earn +4.9bp/day (t 1.95, halves +4.3/+5.6) in 1999-2015 and +5.3 in 2016-26. G1 book-OFF: CAGR 12.1 vs 16.0 (-3.9pp), maxDD
  -13.6 vs -25.7 (2000-02 +19.4pp, 2007-09 +6.3pp). G2 night-OFF: worse on everything. G3 IBS-OFF: CAGR 16.3 vs 16.0, Sharpe 1.66 vs 1.41, maxDD -17.9; fails gate d
  and costs 1.4pp/yr in 2016-26 (IBS earns MORE below trend there). Drawdown dial, not edge.
- **CLASS CLOSED: trend/regime conditioning of the MR book** (TREND-NIGHT, AT on IBS, REGIME-10M all die the same way: the legs earn at least as much in downtrends).
- Program N = 922.

## Idea 4 — ETF category TSMOM standalone sleeve
- Dedupe: Lab-BX (ETF 12-1 momentum tied SPY 2017-26), Lab-BZ (industry momentum + 10m filter: PASS 1963-2015, 5.6% vs 15% in 2016-26), 11-ETF cross-asset TSMOM
  sleeve dead (add. 26b), 'momentum sleeve at 25%' promising-unvalidated. Ceiling: sector/industry momentum premium ~3-5%/yr pre-2016, ~0 since; x 50% capture
  = 1.5-2.5pp/yr standalone < +8pp gate. No genuinely different construction found (12-1 with absolute filter IS Lab-BZ). SKIP, no N.

## Idea 5 — PIVOT: YOUNG-NIGHT (listing-age tilt on the night leg; peeked lead from TREND-NIGHT)
- Pre-registered N 922 -> 924 (Y1 2x weight, Y2 young-only nights; young = < 365d since first price; both windows must pass; placebo 200 draws).
- Result: **FAIL both.** Per-trade gradient monotone (1999-2015: +100/+90/+69/+50/+50 by age bucket; 2016-26: +82/+43/+57/+21/+21) but per night Y1 +0.6 / +1.2bp
  (t 1.0/1.2, inside placebo), Y2 +4.7 / +7.6bp (t 1.7/1.7, placebo 99th +7.7/+19.5), beats levered base by only 2-4bp. Real-small per-trade effect, too diluted
  (17% of picks on a third of nights) to move the leg. Observation kept; no filter.
- Program N = 924. Ideas fully judged: 3 (TREND-NIGHT, REGIME-10M, YOUNG-NIGHT); dedupe-killed: 2 (IBS trend filter, ETF TSMOM sleeve).



## Idea 6 — PIVOT: BREAK-REV, post-deal-break arb liquidation reversal (N 924 -> 927)
- Dedupe: B3 (hold tender targets to completion) dead; the break as an event + the following 1-20 sessions never tested. Chapter 11 emergence = DATA-LIMITED (NEXT 136), skipped.
- Ceiling: ~40 breaks/yr x >= 1% net x 70% deployable x 50% capture ~ +14pp/yr at $10k -> gate bar +1.0%/event.
- Data: EDGAR FTS metadata (works locally via NOTIFY_EMAIL contact), Sharadar prices. Fetch running (break_fetch.py), pre-registered before any price is read.
- Result: **UNDERPOWERED (n 44, 2007-2026).** D0c->D5c +3.04% net (t 1.53, median +2.92, hit 55%, halves +1.2/+3.7, ex-top5 -0.4; control -0.2%); D1c->D10c +2.2 t 0.7
  (median -2.0); D3c->D20c -3.5. Path: +4.4% at day 9 fading to 0 by day 15. Edge unproven, not dead; but free EDGAR identifies <= 6 breaks/yr -> ceiling ~+0.6pp/yr.
  DATA-LIMITED (paid deal DB). Program N = 927. Judged: 4 (TREND-NIGHT, REGIME-10M, YOUNG-NIGHT, BREAK-REV); dedupe-killed: 2.

## Idea 7 — candidate: DRIP pay-date reinvestment pressure (Berkman-Koch 2017)
- Dedupe: DM (ex-date window, monthly spread) dead; DRIP discounts tested; PAY date never examined. Allowed.
- Ceiling: ~20 pay dates/session, close(D-1)->close(D) at auctions; +10bp net x 50% capital daily ~ +12pp/yr; 50% capture of +15bp -> ~+9pp. Marginal pass of the gate.
- Data: Alpaca corporate actions payable_date 2021+ only (none in 2016; Nasdaq calendar thin pre-2018); Sharadar prices + shares for the pressure proxy.
- Pre-registered N 927 -> 930 (P1 all payers, P2 top-tercile cash/ADV, P3 P2 intraday). Placebos D-5/D+5.
- Result: **FAIL x3, wrong sign.** P1 -15.5bp/day t -6.4 (halves -14.9/-16.1, ex-top5 -16.8); P2 top tercile -15.6 t -4.4; P3 intraday -27.8 t -8.7; placebos -12/-11
  (equally negative); no tercile gradient. No pay-date footprint. Dividend-calendar flows on common = closed (DM, EXDIV-OPEN, DRIP-PAY).
- Program N = 930. Judged: 5; dedupe-killed: 2.




## Idea 8 — candidate: proxy record-date short-recall cover (lenders recall to vote; shorts must cover before the record date)
- Dedupe: not in ledgers. Ceiling/data: record dates require parsing ~3k DEF 14A docs/yr (no structured source); literature (Aggarwal-Saffi-Sturgess) documents a
  lending-supply/fee effect, not a price effect; borrow data blocked. KILLED AT GATE (no documented price effect x heavy text build x borrow data blocked). No N.

## Idea 9 — candidate: S&P 500 deletion post-effective reversal on 1998-2026 (Sharadar sp500, 744 removals)
- Dedupe: add. 34 S3 already tested the deletion bounce after the effective date (2021-23, t -2.8, "deletions keep falling"); wrong-signed, not underpowered ->
  fails the resurrection bar. SKIP, no N.

## Candidates enumerated and killed without code (dedupe / ceiling / data)
- RSU vest-date sell-to-cover pressure: named mechanical seller but ~4-12 cluster dates/yr x ~10-20bp -> < 3pp/yr; SF2 covers insiders only. Ceiling-kill.
- Proxy record-date short recall: no documented price effect; DEF 14A text at scale; borrow data blocked. Gate-kill.
- Robo tax-loss ETF-twin swaps: already measured (etf_twins_2026-10-08: +0.5-1.7pp/yr, not implemented).
- Mutual-fund Oct fiscal-year-end loser selling -> Nov bounce: TL-JAN/CEF-TL2 class ("December losers permanently dead at prices-only data"), same costume.
- Name/ticker changes, exchange transfers, ETF closures, Form 25 deletions, sector-ETF rebalances, OPEX, TOM, pre-holiday: all in closed classes (NEXT table).
- Remaining open mechanisms are DATA-BLOCKED: deal database with break dates (BREAK-REV), borrow fees, PIT ratings, PIT index/ETF holdings, per-fund NAV,
  OPRA signed gamma ($180, prior lowered).

## LOOP SUMMARY (2026-10-10) — EXHAUSTED (remaining candidates data-blocked or in closed classes); no pass; program N 916 -> 930
| idea | status | key numbers |
|---|---|---|
| TREND-NIGHT (own-trend filter on night picks) | FAIL, wrong-signed | 1999-2015 diff -21/-16/-23bp per night (t -3.7/-3.0/-3.9); uptrend picks earn <= downtrend |
| IBS 200d/10m SMA filter | dedupe-killed | AT: -7pp/yr; class closed |
| REGIME-10M (SPY 10m SMA book gate) | FAIL | OFF sessions earn +4.9bp/day (1999-2015), +5.3 (2016-26); book OFF cuts maxDD 25.7 -> 13.6% but -3.9pp/yr CAGR |
| ETF TSMOM sleeve | dedupe/ceiling-killed | Lab-BX/BZ, add. 26b; ~1.5-2.5pp/yr standalone |
| YOUNG-NIGHT (listing-age tilt) | FAIL; per-trade gradient real-small | per trade young +100/+82 vs old +50/+21bp, monotone; per night +0.6..+7.6bp (t <= 1.7), inside placebo |
| BREAK-REV (deal-break arb liquidation) | UNDERPOWERED, edge unproven | n 44; D0c->D5c +3.0% net (median +2.9, t 1.5, ex-top5 -0.4); free EDGAR finds <= 6/yr -> ~0.6pp/yr |
| DRIP-PAY (pay-date reinvestment) | FAIL, wrong-signed | -15.5bp/day t -6.4; placebos equal; intraday -27.8 t -8.7 |
| record-date recall, SPX deletion reversal, RSU vests | gate/dedupe-killed | see above |
Classes closed this loop: (1) trend/regime conditioning of the mean-reversion book (TREND-NIGHT + AT + REGIME-10M: the legs earn at least as much below trend);
(2) dividend-calendar flows on common stock (DM + EXDIV-OPEN + DRIP-PAY). Leads kept as observations, not candidates: listing-age gradient (per-name sizing
only), deal-break 5-day reversal (needs a deal database; re-run only on new events). Data-buy rule: no purchase justified (deal DB not retail-priced; the
free identifier caps the rate at ~6/yr; OPRA gamma prior lowered). Bug found and fixed in-loop: cumulative-sum SMA lost precision on Sharadar adjusted closes
(~1e10); nx._roll_prior's ADV/vol20 sums are unaffected at their scale. Files: research/sim/{trend_night,regime_10m,young_night,break_fetch,break_rev,
drip_fetch,drip_pay}.py; outputs data/research/program/*_out.txt; prose + NEXT.md rows written for every judged idea. Nothing committed; no live change.
