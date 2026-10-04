# Trading book dossier for independent review (2026-10-04)

Purpose: give a reviewer everything needed to judge how good this retail trading program really is. All numbers are
from the repo's own studies and the live server; file references are relative to the repo root. Nothing here is
rounded up; caveats are part of the numbers.

## 1. Who and what
- One retail trader. Accounts: Schwab taxable margin (~$3.43k account, bot book ~$2.27k), Schwab Roth IRA (~$7.9k
  account, bot book capped at ~$1k; +$7,500/yr guaranteed contributions), Alpaca paper ($3k, for testing).
- Goal: maximise % return at $2k-25k after costs and 30% short-term tax. Capacity above $100k is secondary.
- Program: ~818 pre-registered strategy variants tested since 2026 (fixed rule + pass gates written before results).
  Nearly all are dead. Live since 2026-09-23 (taxable) and 2026-09-29 (Roth).

## 2. The live strategies (three legs)
| leg | rule | instruments | sizing |
|---|---|---|---|
| **IBS ETF reversal** | Of 18 liquid ETFs, take the top 3 by 12-1 month momentum (monthly); buy any with IBS = (close-low)/(high-low) < 0.2; buy the open auction, sell the next open | SPY, QQQ, IWM, DIA, MDY, 9 sector SPDRs, SMH, XBI, EEM, EFA; idle cash in SGOV | 50% of book |
| **Night (overnight loser bounce)** | At 15:40: stocks down >= 8% on the day, IBS < 0.10, price $5-2000, $ADV >= $10M, 20d vol >= 60%; buy the 16:00 close auction, sell the 09:30 open auction | single US stocks | 50% of book, 10% name cap, crowding and correlation caps, half size over weekends; 1.0x overnight (no leverage) |
| **Noise intraday momentum** | Zarattini-Aziz-Barbon "noise area": bands = max/min(open, prev close) x (1 +/- mean intraday move by minute, 14d); enter on a break at 30-min decision points, exit on a re-cross of the band or VWAP; flat by close | QQQ and SMH (long/short in taxable; Roth via 3x bull/bear ETFs) | vol target 2%/day, cap 3.5x, live caps 1.79x taxable / 1.5x Roth |
Shadow-only (log, no orders): TQQQ conviction trade, oversold V6, FOMC-eve filler, insider-buy day trades, CEF
activist 13D, news judge, and others (`swingtrader/daily/testing.py` REGISTRY).

## 3. Backtest results
### 3a. Combined book (RESULTS.md addendum 30, raw prices, 2021-26, IN-SAMPLE: rules were chosen on this period)
CAGR / Sharpe / max drawdown, $3k start + $1k per month, at three cost levels:
| book | 3bp/side | tier | tier_hi (pessimistic) |
|---|---|---|---|
| **Live today (3 legs)** | 40.6% / 2.08 / -14% | 30.9% / 1.67 / -15% | **23.7% / 1.33 / -16%** |
| Roth version | 35.3% / 1.97 / -10% | 27.7% / 1.61 / -11% | 22.4% / 1.34 / -12% |
- "Edge-halves" stress (every edge cut in half, addendum 39): **18.3% (Sharpe 1.07) at 3bp, 11.0% (0.70) at tier_hi.**
- Earlier figures were ~1/5 too high (split-adjusted prices distorted price floors and costs; addendum 30); the table is corrected.
- Deflated Sharpe ratio (addendum 22): IBS alone 0.57 at 50 trials, night alone 0.33, full book 0.93.
- The repo's own realistic forward estimate: **~8-15%/yr pre-tax** (CLAUDE.md).
- Capacity (study_y_scale_book.md): 22.6%/yr at $25k, 20.5% at $100k, 17.8% at $500k, 15.9% at $1M.

### 3b. Per leg, with out-of-sample status
| leg | in-sample | genuinely out-of-sample | verdict |
|---|---|---|---|
| IBS | 2021-26: +21.6bp/trade, t 3.45, hit 58%, n 829 | **2016-20 (never used to choose the rule): +29.8bp, t 4.02, hit 59%, n 557, ex-top-5 +23.9bp**; 2017-19 ex-2020 +14.3bp, t 2.09 | the one leg with a real OOS pass; premium scales with volatility (partly beta); 2024 was -7.3bp |
| Night | 2021-26: strong (+24.8%/yr alone at 3bp) | exact 15:40 rule on 2016-20 minute data: 2016-18 +3.0bp gross (t 0.25), **-12bp after 7.5bp/side costs**; 2016-19 ex-2020 +26bp gross (t 2.57), +11bp net (t 1.10); 2019-20 strong | **weakest leg**: looks like a high-volatility-regime effect; Kelly fraction negative at pessimistic costs; survivorship-free 2003-15 judge (Study NX) registered but frozen (needs paid data) |
| Noise | 2021-24 +4..+11bp/day | 2016-20 by year: -2.6, +2.3, +19.8, +0.3, +11.1bp; 2025 +0.1, 2026 +2.5 | real factor-independent alpha (unlevered 10.2%/yr, t 4.29; QQQ beta ~0; long-volatility) but **entirely inside execution cost**: Sharpe 1.07 at 0.5bp/fill, 0.78 at 1bp, 0.19 at 2bp, -0.94 at 4bp; 1.65 fills/day |

### 3c. What the book is long/short of (book_decomp_out.txt, window-matched factors, Newey-West)
| leg | annual return | alpha | alpha t | R^2 |
|---|---|---|---|---|
| night | 11.2% | 7.1% | 1.51 | 0.13 (tech +35.7, size +17.8 loadings) |
| IBS | 8.4% | 5.3% | 1.84 | 0.23 (market beta) |
| noise | 12.8% | 13.0% | 2.99 | 0.07 |
Total book overnight SPY beta 0.31 (t 3.5). Read: the overnight legs are partly levered small-cap/tech/market beta;
the cleanest alpha is the intraday noise leg, which is cost-fragile.

## 4. Live track record (too short to judge)
| account | live since | sessions | realised P&L | fills |
|---|---|---|---|---|
| taxable | 2026-09-23 | 8 | +$41.38 (night +$20.06 on 37 trades, IBS +$25.72 on 3, noise -$1.54 on 4, T-bill -$2.86) | 95 |
| Roth | 2026-09-29 | 4 | +$5.84 | 35 |
| paper (Alpaca) | 2026-09-23 | 8 | +$16.61 | 76 (paper overnight fills are unrealistic; ignore) |
No live Sharpe is computed (fewer than 20 sessions). The book's capital was raised from $1,000 to ~$2,260 on 09-29, so
the book equity log is not a return series.
**Execution cost, measured** (research/drafts/audit_execution_1002.md): all 130 live fills printed exactly at the official
auction price. Open auction 0.0bp (n 59), close auction -0.2bp (n 57), intraday +0.4bp vs mid (n 14). A logged
"slippage" of +65..+240bp is drift from an earlier reference price, not cost.

## 5. Risk controls in code
Halt every leg at a 25% realised drawdown; per-leg kill if t < -1 after 60-120 trades (ibs 60, night 100, noise 120);
night kill if exit cost > 25bp/side over 30 exits; leverage gate off; intraday only above $2,000 equity; noise leverage
caps above; Roth: no shorting, no margin.

## 6. Forward tests in flight (all early)
Night auction cost 15/100; book vs index beta 7/250; insider-day trades 0/300; EV2 insider-buy variants 0/60 each;
CEF activist 13D 0/30; news judge 14/300; others logging. Nothing has reached its gate.

## 7. What has been tried and failed (abridged)
Options of every retail kind (12 variants at real bid/ask: 0DTE, condors, straddles, earnings flies; spreads kill all),
ORB on stocks in play, gap fades, PEAD, leveraged-ETF flow, micro futures, crypto (35 variants), news filters,
leverage/concentration on the proven legs, OPEX/0DTE timing, index add/delete, many SEC-filing events, Reg SHO
threshold forced buy-ins (-9.6% to the deadline), Treasury auctions, ETF creation/redemption, futures roll.
Near / promising, not deployed: insider buys >= $500k after 2 years of silence (holdout +68.7bp/trade, t 3.48, 2021
-10bp: forward test 0/60); CEF activist 13D (+2.5-3.6% per 60 days vs PCEF, ~+3.4%/yr at book level); Treasury
month-end (another session: +32bp/month on untouched 2002-15, t 2.76, ~+4%/yr on capital deployed); CEF discount
mean reversion (secondary, survivorship unhandled); signed dealer gamma (data target, ~$180/yr).

## 8. Known weaknesses a reviewer should press on
1. Most book backtests are 2021-26, a single post-2020 regime; "two halves" splits inside it are not out-of-sample.
2. Only IBS has a clean out-of-sample pass. The night leg's pre-2021 exact-rule result is ~zero after costs outside
   2019-20. The noise leg is real but survives only below ~1.5-2bp per fill.
3. Survivorship: delisted stocks are only partly in the night-leg tests; ETF universes are today's survivors.
4. Multiple testing: ~818 variants; deflated Sharpe of the full book 0.93.
5. A meaningful part of the overnight return is market/tech/small-cap beta, not alpha.
6. Live record is 8 sessions: statistically uninformative.
7. Small account: whole-share rounding and the $2,000 margin floor bind; the book's realistic forward return is
   ~8-15%/yr pre-tax by the repo's own estimate.

Key files: RESULTS.md (addenda 22, 30, 39), CLAUDE.md (research philosophy + memory), study_y_scale_book.md,
data/research/program/{ibs_oos_out.txt, noise_audit_out.txt, book_decomp_out.txt}, research/drafts/study_*.md,
LOOP_LOG.md.
