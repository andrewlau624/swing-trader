# Round 18 — Studies AS, AT: two ideas from a quant Discord (both DEAD; N 669 -> 675)

`research/drafts/round1_prose.md` Round 18 (pre-registered and committed in b025d63 before any number).
Code: `research/sim/discord_ideas.py` (14s). Output: `data/research/program/discord_ideas_out.txt`.
Window 2021-02..2026-09 (the honest night pool), fixed capital, whole shares. Costs: night 2.5bp/side
(= the registered 5bp round trip) and tier_hi; IBS 1bp/side.

## Triage of the chat (what was already covered)

| chat idea | status here |
|---|---|
| Order-book / bid-ask imbalance → mid-price move (MemLabs) | needs L2 history; same blocker as the closing-auction imbalance (Round 13 AC) |
| Alpha decay: retrain + track OOS, Monte Carlo drawdown percentile | add. 37 (CUSUM / rolling-t de-risk dead; no leg decaying); `make review` kill rule + §4 same-trade test already compare live to backtest |
| Null model / "excess predictability" E[r\|X] > E[r] | every study's sign-flip / vol-matched-random placebo is this benchmark |
| XGBoost vs linear, feature selection, MSE vs directional accuracy | Study E (local GBM/ridge on the night pool) |
| Data-mining caution, parameter jiggle, Bailey/LdP | DSR at N, both-halves rule, add. 37 walk-forward haircut |
| Blend mean reversion + trend for low correlation | the book is already IBS + night (MR) + noise leg (trend); corr of IBS/night ≈ +0.01 |
| Pairs / ARDL lead-lag | ETF pairs dead (add. 27 R4); crypto perps not on Schwab |
| **Softmax / vol allocation across strategies** (MemLabs, sxssion) | **untested → Study AS** |
| **Vol-contraction filter + regression-slope trend filter for MR** (Whiskey) | **untested → Study AT** |

## Study AS — the overnight budget split IBS / night by trailing metrics: DEAD

Night weight per day (IBS = 1 − it), clipped [.2, .8], from per-unit leg returns lagged 2 sessions.
At 2.5bp/side the legs earn night 26.5%/yr (Sh 1.14), IBS 18.2% (Sh 1.22), correlation +0.01.

| at $2.3k / $10k / $25k, V7 book | 2.5bp/side increment | tier_hi increment | best t | placebo |
|---|---|---|---|---|
| AS1 softmax 63d Sharpe | +0.1 / −1.0 / −1.4pp | +1.9 / +1.1 / +0.8 | +0.61 | 71% |
| AS2 inverse 63d vol | +0.0 / −1.3 / −1.2 | +3.4 / +2.5 / +2.5 | +1.79 | 95% |
| AS3 softmax 252d Sharpe | −0.9 / −1.3 / −1.5 | +1.1 / +1.4 / +1.1 | +0.53 | 71% |

(IBS+night cash mix: same sign pattern.) At the realistic cost every variant is ~0 or negative.
The tier_hi "gains" are not timing: at tier_hi the night leg earns −0.5%/yr, and every variant's
mean night weight drops below 0.5 (AS2 0.40, AS1 0.39, AS3 0.37). Moving money from a ~0 leg to
an 18% leg gains about that much. That is Study AQ's cost crossover again: the night leg's weight
is a cost question, already gated live. AS1 sits at a clip 52-54% of days (the softmax of
63-day Sharpes is near bang-bang), and adds drawdown (−5pp on the cash mix at $10-25k).
With two nearly uncorrelated legs of similar Sharpe, a fixed 50/50 is close to optimal, and
trailing 3-12 month Sharpe does not forecast the next month's.

## Study AT — vol-ratio and trend-slope conditioning of the IBS leg: DEAD (AT3 harmful)

Per-trade gross (open→open, −2bp) of kept vs skipped picks; VR = 10d / 60d stdev, median 0.99.

| | 2016-20 (holdout) | 2021-23 | 2024-26 | book inc (V7, 2.5bp, $2.3k) |
|---|---|---|---|---|
| AT1 skip VR < 0.8 (contracting) | keep +24 / skip +36bp (t −0.8) | +21 / +18 | +26 / −4 (t +1.5) | −0.6pp, t −0.5 |
| AT2 skip VR > 1.25 (expanding) | +27 / +30 | +16 / +39 | +19 / +17 | −3.4pp, t −1.8 |
| AT3 keep only 50d slope > 0 | +22 / **+41** | +16 / **+27** | −1 / **+72** (t −3.0) | **−7.1pp, t −3.1** |

- AT1's 2024-26 split points the hoped-for way, but the 2016-20 holdout points the other way.
  Post-hoc pattern, not an edge.
- **AT3 is the useful negative.** "Only take mean-reversion trades aligned with the trend" is
  backwards here. IBS dips in ETFs that are in a 50-day *down*trend revert the most (+41 / +27 /
  +72bp vs +22 / +16 / −1 for uptrend dips), in every period. The leg's momentum top-3 selection
  already supplies the long-horizon trend. The short-horizon slope only removes the deepest dips.
  It matches the do-not-redo row on regime gates (SPY > 200dma only buys Sharpe for return). Do not add
  a short trend filter to any MR leg.

Every cell fails (0/12 per variant). DSR at N 675: no variant has a positive increment t ≥ 2.

## Side finding: Study AQ's cost labels are per side, not round trip

`B.cost_bps` returns a **per-side** cost: `B.Sim.day_pnl` and `roth_cash.cash_day` both charge
`ret − 2·c`. Study AQ's sweep passed c ∈ {0, 2.5, 5, …} and labelled it "round trip". So:
- AQ's "5bp (2× measured)" row (19.0%/yr cash IRA) is **5bp/side = 10bp round trip**, about 4×
  measured. The brief's real 2× stress (5bp round trip) is AQ's 2.5 row: **22.0%/yr**.
- The night leg's crossover vs IBS-only is **~5-6bp per side (~10-12bp round trip)**, not ~6bp
  round trip.
The error was conservative: AQ's verdict (run IBS+night in the cash-IRA Roth) gets stronger, and
the cost gate is about twice as wide as written. NEXT.md's AQ line is corrected to match.
