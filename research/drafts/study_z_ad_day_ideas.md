# Round 13 — the untested "use the day" ideas: Z, AB dead; AA small; AC needs data; AD reframes the taxable plan (N 619)

Stamp: `round1_prose.md` Round 13 (commit b6552d4). Script: `research/sim/day_ideas.py` (~20 s).
Output: `data/research/program/day_ideas_out.txt`. Cboe index files: `data/research/program/cboe/`.
Book = Study Y B2 (CENTRAL, constant equity). All numbers replay the fitting period.

## Study Z — SPX put-write overlay (k = 0.5 x E, 60/40): DEAD (3 variants)
| variant | standalone net excess over BIL, tier_hi (2016-20 / 21-23 / 24-26) | increment, NW t | worst 21d at k .5 | verdict |
|---|---|---|---|---|
| Z1 PUT (monthly ATM) | +4.9 / +6.4 / +8.5 %/yr | +3.7pp/yr, **t 1.93** (tier 2.02) | **−15.5%** (2020-03) | DEAD by a hair on (3) and (4b) |
| Z2 WPUT (weekly) | −0.5 / −2.5 / +3.8 | +0.4pp, t 0.2 | −13.2% | DEAD: weekly rolls eat it |
| Z3 CNDR (iron condor) | −5.3 / −3.3 / −0.4 | −1.0pp | −4.9% | DEAD: negative everywhere |

- Z1 is the real variance premium: positive in every period, +$2.7k/yr after tax at $100k and +$13k at
  $500k had it passed. It fails the registered NW t by 0.07 and the 15% crash bound by 0.5pp (COVID).
  t does not depend on k, so a smaller overlay does not rescue it. **Do not rerun with a new k or a new bar.**
  The honest reading: an index-level premium of this size needs ~15+ years to clear t 2 in-sample, and it
  loses about a sixth of E in a month in a crash, the same month the night leg breaks (addendum 18).
- Roth report (PUT as the destination past the book's capacity): 2016-26 PUT 8.4%/yr, Sharpe 0.71, max DD
  −29% vs SPY 15.2% / 0.90 / −34%. 2007-26 PUT 8.8% / 0.61 / −37% vs SPX price-only 8.9% / 0.53 / −57%.
  In the Roth, PUT loses to a held index on return; it is a drawdown dial, not a better destination.

## Study AA — box-spread financing (report)
Mean overnight debit is small because the legs rarely fill their budgets: **3.6% of equity at 1.3x**
(17% of days), 19.5% at 2.0x. Box rate (BIL + 0.30%) averaged 3.5%.
| | $25k | $100k | $500k | $1M |
|---|---|---|---|---|
| 1.3x, margin 12% | +$79/yr | +$318 | +$1.6k | +$3.2k |
| 2.0x, margin 12% | +$427 | +$1.7k | +$8.5k | +$17k |
At Schwab's large-balance rates (8-10%) the savings are ~25-45% lower. Worth doing only with the MAX / 2x profile
at ≥ $100k (the mean debit is then ≥ $20k, two XSP boxes). At today's settings (lever_weight null) it is $0.

## Study AB — fade QQQ inside the noise band: DEAD (2 variants)
θ 0.5: 266 trades/yr, +1.4bp gross/trade; at 1.0bp/side −4.0pp/yr, 2016-20 −6.6, 2021-23 −8.1, 2024-26 +5.3,
NW t −1.3, placebo 82nd pct. θ 1.0: 67 trades/yr, +0.5bp gross; −2.3pp/yr, NW t −1.1, placebo 41st. The
in-band drift is smaller than one side of the cost; only 2024-26 is positive. Dead with the other intraday
rules (ORB, last half hour, single-stock noise).

## Study AC — closing-auction imbalance: needs paid data (feasibility)
Databento sells the Nasdaq TotalView-ITCH / NYSE imbalance schema from 2018 (usage-priced per GB; new accounts
get $125 of credits; imbalance is "L3", so the $199/mo plan carries only one month of it). Nasdaq sells
NOII-only files from 2010. Live trading would need that feed too (neither Schwab nor Alpaca serves imbalances).
Not tested; no proxy (a 15:50 price move is not an imbalance). To test: pull the closing imbalance at 15:50 /
15:55 for the IBS ETFs + QQQ/SPY + the night pool, 2018-26, and pre-register a fade/follow on 15:50 -> close.

## Study AD — the noise leg as an overlay on SPY held (report): the taxable plan's best shape on this data
Readings (pre-registered): after tax (MOD, MNQ 60/40), 2016-26 and 2021-26:
1. **SPY + noise overlay beats SPY held at every size** (+8.8pp at $2.3k, +7.9 at $100k, +5.6 at $1M, +3.6 at
   $2.5M, Y 1), and **beats B2 at every size on the grid** (2021-26: $25k 22.1 vs 15.9; $100k 21.5 vs 14.5;
   $1M 19.1 vs 11.2; at $2.3k 22.4 vs 21.6 ≈ tie). It holds in both halves pre-tax ($100k: 27.2 / 25.1 vs B2
   23.2 / 17.7), so it is not a 2024-26 artifact.
2. The overlay's increment over SPY halves at ~$2M (Y 1); past $5M under Y 0.5.

What it is and is not (descriptive, not registered):
- **Not a new edge.** It is the shipped noise leg (corr with SPY 0.00, +in 2022) on top of market beta held for
  deferral. It beats B2 after tax because B2's overnight money earns ~10%/yr taxed short-term every year
  while SPY's ~15% compounds untaxed; at size B2's night leg is capped away and IBS is the rest.
- **It carries more risk.** 2021-26 max DD −17% vs B2 −10% (Sharpe 1.32 vs 1.51 at $100k); 2016-26 max DD −31%
  (COVID, SPY −34%). Worst year +3% (2022: the noise leg offset SPY −17%). It depends on the index's future
  return far more than B2 does; the 2016-26 SPY rate (15.7%) is well above its long-run ~10%.
- **Taxable only.** The Roth has no intraday margin, so SPY held leaves no cash for the noise leg.
- Buying power: SPY 1.0x fully paid + noise ≤ 1.5x intraday is inside Reg T day-trade BP (~3x equity after
  SPY's maintenance); live `executor._gate` would need a check that it counts the held SPY correctly.

Consequence for scale_plan.md (a decision for the user, nothing built): for the TAXABLE account past ~$25k,
"SPY held + QQQ noise (MNQ past ~$160k)" dominates the full book on after-tax return at the cost of index-sized
drawdowns. Study Y's crossover ($250k) moves down to ~$25k under this comparison. The Roth keeps the full book.
If adopted it should be pre-registered as a switch with the drawdown stated up front, not slid in.

Program N: 614 + 3 (Z) + 2 (AB) = **619**. Nothing new clears the bar; AD is structural.

## Round 14 addendum (feasibility sensitivity, after AD; decides the trigger, not a new variant)
Live `executor._gate` gives the noise leg `min(noise_max_lev, mult − overnight weight)`: with the index held 1.0x
at mult 2 the cap is 1.0. After tax (MOD, MNQ), 2021-26, B2 vs overlay at cap 1.0 vs cap 1.0 with SPY at 10%/yr:
$25k 15.9 / 20.3 / 15.2; $100k 14.5 / 20.0 / 14.9; $500k 12.5 / 19.2 / 14.1; $1M 11.2 / 18.6 / 13.5. Max DD
−17..−18% at cap 1.0. Pre-tax halves at $100k, cap 1.0: 23.8 / 24.3. -> trigger set at $100k (Round 14).
