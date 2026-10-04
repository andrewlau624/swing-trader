# Contest hunt log (prompt: `prompt_contest_hunt.md`, started 2026-10-04)

## Morning summary
(pending)

## Steps
- [x] Step 1: strategy-family table, top 3 picked (T1 noise 0DTE overlay, T2 0DTE credit spreads, T3 pre-earnings straddle)
- [x] Step 2: data (Databento OPRA cbbo-1m, signal-driven, $2.00)
- [ ] Step 3: pre-register + test (N 791 at start)
- [ ] Step 4: build, test, deploy small

## Open questions for the user (logged, not blocking)

## Step 1
### Server state (read-only check, 2026-10-04 ~02:00 PDT)
- Server HEAD 320eaf6 = origin/main; local main is 2 ahead (db80f87, 155cee9, not pushed).
- Roth IS trading live on Schwab: 35 fills 09-29..10-02 (book capped at $1,000 of a $7,880 account; ~$6.9k idle).
  Taxable live: 95 fills 09-23..10-02, book $2,267 (Schwab account $3,459). Alpaca = paper only.
- daytrade/ lab only records (no `daytrade.py run` service); the daily book's intraday leg is live (`daytrade_mode: auto`).
- Real-money switches live in server .env (DAILY_LIVE, DAILY_ROTH, DAILY_ROTH_CAPITAL), not config.yaml.
- Q for user: measured slippage on 10-02 fills vs reference looks like +65..+240bp on several fills; config comments say ~0bp. Worth an audit (not this hunt's scope).
### Repo dead list (audit 2026-10-04)
All stock/ETF versions of the prompt's families are already DEAD or already live: ORB in-play (RESULTS:648, Lab-AU), SPY
noise / VWAP-trend (Lab-AW), LETF flow (Q3, Lab-BK, Study W, Lab-CA), gap-up shorts (RESULTS:652, Lab-BA/BI), PEAD proxy
(Lab-BH), MES/MNQ (Add. 25; MNQ noise = live QQQ noise leg rewrapped). G2 EV2-big = NEAR, shadow-only. TQQQ conviction = shadow.
**Untested anywhere: options of any kind** (no options data or code in the repo). The new ground is options.
Live noise leg: QQQ+SMH, 30-min decisions 10:00-15:30, vol-target 2%, cap 3.5x, taxable long/short (signals.py:676, executor.py:1431).

### Strategy-family table (web research + repo dead list; est. columns are rough, from the cited figures)
| # | Family | Public evidence | Repo status | Est. 3-mo @$2.3k/$10k | P(-30%) | Data |
|---|---|---|---|---|---|---|
| 1 | 0DTE QQQ/SPY long premium on intraday breakouts | Retail lost $241k/day 2021-23, $350k/day after daily expiries, mostly single-leg debit (Beckmeyer-Branger-Gayda 2023); Cboe-funded study: customers ~break even (t 0.29) | untested | -15..-30% unconditional; conditional on a real breakout signal: unknown | 50-70% at friend-like size | Databento OPRA cbbo-1m (real NBBO, 2013+, ~$0.001/day for near-ATM 0DTE) |
| 2 | Convex overlay on the repo's live QQQ noise breakout (0DTE calls/puts instead of shares) | Noise area: 19.6%/yr levered, Sharpe 1.33 (Zarattini-Aziz-Barbon 2024); repo QQQ 14.7% both halves | signal LIVE in shares; options untested | unknown; this is the test | set by premium-at-risk sizing | same as 1 |
| 3 | 0DTE defined-risk short spreads (VRP; counterparty = retail 0DTE buyers) | multi-leg/premium-selling retail trades "significantly more profitable" (BBG 2023); delta-hedged 0DTE VRP dissipates after daily listings (Almeida-Freire-Hizmeri) | untested | -3..+3% | 15-25% (gap tail) | same as 1 |
| 4 | Pre-earnings straddle (t-3 to announcement, exit before) | +3.34%/straddle 1996-2013, strongest in small names (Gao-Xing-Zhang JFQA 2018) | untested | 0..+4% | ~10% | needs earnings dates (EDGAR 8-K 2.02) + single-name NBBO |
| 5 | Option overlay on EV2-big insider buys | none published; delta 0.5 x 50bp ~ 11% of a 5-day ATM premium vs 5-10% spread | G2 NEAR (shares) | ~0 +/- large | 20-30% | few events (~40/yr), thin chains |
| 6 | ORB on stocks in play (Zarattini-Barbon-Aziz 2024: 41.6% IRR, Sharpe 2.81, no slippage) | | DEAD x2 (RESULTS:648, Lab-AU -23.5bp/trade) | - | - | - |
| 7 | Intraday TS momentum SPY/QQQ via TQQQ/futures (GHLZ 2018; ZAB 2024) | | QQQ = the live noise leg; SPY dead; TQQQ conviction in shadow | - | - | - |
| 8 | LETF rebalancing / EOD flow (Shum et al. 2016; BDLM 2021) | | DEAD (Q3, Lab-BK, Study W, Lab-CA) | - | - | - |
| 9 | Short gap-up low-float runners | net-of-borrow short returns 22-29% of gross; Schwab: no paid locates, buy-ins | DEAD (RESULTS:652, Lab-BA/BI) | - | 30%+ | - |
| 10 | MES/MNQ intraday | 97% of persistent futures day traders lose (Chague-De Losso-Giovannetti); Schwab margin figures conflict ($530 vs ~$2,500 day margin); IRA futures need $25k | DEAD (Add. 25; MNQ noise = QQQ leg rewrapped) | - | 40%+ | - |
| 11 | Crypto perps 10x (Coinbase nano) | no published retail edge | crypto-lab 35/35 dead | - | - | - |

**Friend most likely runs family 1:** 0DTE SPY/QQQ long premium on breakout triggers (leverage, near-daily, occasional big
wins). A 2x lead over 3 months is consistent with positive skew plus luck; the unconditional mean of that family is negative.

**Top 3 to test (all options: the only ground the repo has not covered; real NBBO, fill at the far side):**
- **T1 = family 2**: QQQ 0DTE long call/put on the live noise-leg breakout signal. Leverage on the one intraday signal with
  an edge, and convexity on trend days. Directly the friend's instrument, with a tested trigger instead of a guess.
- **T2 = family 3**: 0DTE QQQ defined-risk credit spreads (the other side of the friend's trade).
- **T3 = family 4**: pre-earnings straddles, if earnings dates + single-name NBBO can be had for the remaining credit.
Splits: select 2023-01..2024-12 (daily QQQ expiries from 2022-11), untouched judge 2025-01..2026-09.
Data: Databento OPRA cbbo-1m, near-ATM 0DTE only, inside the remaining free credit (~$9 of $125). No purchase needed.

## Step 2 (data)
- Alpaca options historical API (probed): minute bars + trades from 2024-02 only, **no historical quotes** (404). Too thin for far-side fills.
- Databento OPRA.PILLAR cbbo-1m (real consolidated NBBO, 2013+) via the existing key. A full +/-3% 0DTE chain would be ~$22
  (over the ~$9 left of the free credit). Signal-driven pull (only the contracts T1/T2 trade): **$2.00** for 2023-01..2026-09,
  865 signal trades + 690 condor days. Paid from the existing credit; no purchase, so no question for the user.
- Pre-registered T1a/T1b/T1c/T2a in round1_prose.md (0dc72d6), N 791 -> 795, before any option price was loaded.
- Small-account note: a 10:00 ATM QQQ 0DTE costs ~$300-500/contract, above the 5% ($115) max loss at $2.3k, so T1a will
  mostly skip at $2.3k; the $2 vertical (T1b) is the version that fits whole-contract rounding.
- T3 (pre-earnings straddle): parked. A straddle on a typical large cap costs $1,000+; at $2.3k with a 5% max loss only sub-$30
  names fit, and the remaining credit (~$7) may not cover single-name NBBO. Tested only if T1/T2 all die.

## Step 3 results
### T1/T2 (QQQ 0DTE on the noise signal): DEAD, all four; N 791 -> 795. `study_contest_t1t2.md`
Judge 2025-01..2026-09 return on risk per trade: T1a -4.9%, T1b -15.5%, T1c -11.4%, T2a -9.5%. 3-mo median at $2.3k -15..-42%.
Underlying signal +4.5bp/trade (2023-24), +2.6bp (2025-26, t 0.77): too small to carry 0DTE theta and spread.
Next: T3 pre-earnings straddle (GXZ 2018) and T4 overnight short QQQ condor (Muravyev-Ni 2020: delta-hedged option
returns are negative overnight, positive intraday).
### T4 (overnight short QQQ 1DTE condor/fly): DEAD, all three; N 795 -> 798. `study_contest_t4.md`
Judge return on risk per night: T4a -29.8%, T4b -18.6%, T4c -57.7%. Mid-to-mid P&L ~0: no overnight premium; spreads kill it.
### T7 (EV2-big insider buy -> call, open->close): DEAD; `study_contest_t7.md`
270 priced events; judge -31.5% of premium per trade (select -28.7%). Median 09:35 spread 23% of the ask on these chains.

## Step 4 status (2026-10-04 ~04:20 PDT)
- Drafted `swingtrader/daily/zero_dte.py` (T1a mirrored onto the live noise leg's QQQ position: long 0DTE call/put,
  1 contract, premium <= 5% of $2,300, daily stop 10%, HALT kill switch at 30% cumulative loss, flat 10 min before the
  close, live only with ZERO_DTE_LIVE=on). **Not committed, no tests, no timer, not deployed.**
- The Claude Code auto-mode permission classifier denied a further edit to this live-order module. Per the rules I did
  not work around it. Live deployment of an options leg is left for the user to approve and finish by hand.
- Separately: T1a FAILED its judge (-4.9% of premium per trade). Shipping it would be shipping a measured loser,
  not an unproven idea.
### T6 (QQQ 0DTE long straddle 09:45->15:50): DEAD; `study_contest_t6.md`
Judge -9.2% of premium per trade (select -8.7%), win 30%; $313/contract never fits 5% of $2.3k.
### T3 (pre-earnings straddle t-3 -> t-1): DEAD, both; N 798 -> 800. `study_contest_t3.md`
Judge -35.4% (>= $2B) / -44.4% ($2-10B) of premium per trade. Mid-to-mid +1.5% (half of GXZ); straddle spread ~20% of mid.
**All three top families (T1, T2, T3) are now tested and dead.** Extra families tested: T4 (overnight VRP), T6 (intraday
straddle), T7 (insider calls); T5 (short earnings fly) data loading.
