# Results — walk-forward backtest, 2021-01 → 2026-09

Universe: 14,765 symbols (12,757 active + 2,008 delisted), 11,530 with usable
history. 30 folds of 126-day formation → 42-day trading, disjoint. Slippage 20bps
per side, 8 concurrent positions, $100k start, no leverage.

## Headline

| run | CAGR | Sharpe | maxDD | Calmar | trades | win% | avg/trade |
|---|---|---|---|---|---|---|---|
| **highvol, long, −10% stop** | **11.77%** | **0.77** | **−14.6%** | **0.81** | 207 | 51.7% | +2.46% |
| highvol, long, −15% stop | 10.22% | 0.65 | −18.9% | 0.54 | 184 | 57.6% | +2.49% |
| highvol, long, **no stop** | 8.62% | 0.56 | −21.2% | 0.41 | 163 | 62.0% | +2.30% |
| broad, long, no stop | 5.19% | 0.37 | −22.6% | 0.23 | 213 | 61.0% | +1.09% |
| broad, long, −10% stop | 1.64% | 0.18 | −29.4% | 0.06 | 260 | 49.2% | +0.40% |
| highvol, **long/short** | −2.41% | 0.03 | −50.4% | −0.05 | 336 | 62.5% | +0.06% |
| broad, long/short | −9.76% | −0.28 | −53.9% | −0.18 | 412 | 59.0% | −0.79% |

## Controls — these decide the question, not the table above

| control | CAGR | Sharpe | reading |
|---|---|---|---|
| **strategy** (highvol, no stop) | 8.62% | 0.56 | baseline |
| **shuffle** — same stocks, same entry rate, *random days* | **0.82%** | 0.13 | timing rule carries the edge |
| **flip** — every signal inverted | −6.77% | −0.90 | engine is not self-flattering |
| buy & hold the same candidates | 6.47% | 0.36 | strategy beats holding them, mostly on drawdown (−21% vs −51%) |
| **SPY buy & hold** | **12.88%** | **0.81** | **SPY wins on return and Sharpe** |

The shuffle control is the important one. Entering the *same selected stocks* at
the *same frequency* on random days earns 0.82%; entering on z < −2 earns 8.62%.
So the dip-buying rule is doing real work — this is not just "volatile stocks
that went up".

But SPY buy-and-hold beat the best configuration on both CAGR (12.88% vs 11.77%)
and Sharpe (0.81 vs 0.77). The strategy wins decisively on drawdown (−14.6% vs
−24.5%) and therefore Calmar (0.81 vs 0.53).

## Findings

**1. Cutting losses beats waiting — the opposite of the current method.**

| stop | CAGR | Sharpe | maxDD | avg hold |
|---|---|---|---|---|
| none ("wait it out") | 8.62% | 0.56 | −21.2% | 12.5 d |
| **−10%** | **11.77%** | **0.77** | **−14.6%** | **7.1 d** |
| −15% | 10.22% | 0.65 | −18.9% | 9.0 d |

The −10% stop improves return, Sharpe and drawdown simultaneously. Note the win
rate *falls* (62.0% → 51.7%) while everything that matters improves — a clean
illustration of why win rate is the wrong statistic for this strategy.

**2. The edge needs high volatility.** Broad-market: 5.19% CAGR / 0.37 Sharpe,
and 1.64% / 0.18 with the stop. Mega-cap mean reversion has ~2–4% amplitude,
which 40bps round-trip slippage eats. The RGTI species is where this lives.

**3. Shorting the top of the range destroys it.** Every long/short configuration
is negative. These names trend up violently; shorting an overbought speculative
is uncompensated risk.

**4. The diversification premise holds.** Mean pairwise correlation among selected
candidates is 0.219, only 2% of pairs above 0.5. Eight positions really are
closer to eight bets than one — the compounding logic is sound.

**5. Sample size is adequate now, but live validation is slow.** Bootstrapped
P(mean trade ≤ 0) = 0.00 (iid), 0.00 (block), 0.01 (stationary) on 207 trades.
Edge survives +10bps of extra slippage (+2.46% → +2.26% per trade). But
`months_to_significance` = **40.5 months** — live results would need ~3.4 years
to be statistically distinguishable from luck.

## Bugs found that were inflating results

Each of these made the strategy look better than it is, and each was caught by a
control or a test rather than by inspection:

1. **Immortal positions.** Positions in symbols dropped from the candidate set
   were never managed — the exit check was gated on a z-score that only existed
   for current candidates. Eight never-closed positions supplied **99% of total
   profit** while `avg_bars_held` read 143 against a 20-day time stop. Fixing it
   cut CAGR 11.6% → 8.6%.
2. **Shorts minted equity.** Short proceeds were credited to cash *and* the
   position valued positively, so a $25k short created $50k of equity. Long/short
   runs reported Sharpe 1.09 alongside −24% CAGR and −100.07% drawdown.
3. **Trend filter rejected its own targets.** Plain OLS drift t-stats are
   inflated by the autocorrelation that mean-reverting series have by
   construction — |t| up to 5.9 on synthetic series with a true slope of zero.
   The |t| ≤ 2.5 screen was rejecting exactly the stocks it should select.
   Newey-West HAC correction fixed it (median |t| 5.5 → 1.08).

Two more that would have faked results but were prevented by design: raw
(unadjusted) bars show NVDA's split as **−89.9%** vs +0.9% adjusted — a phantom
crash a dip-buyer would buy; and the delisted 13.6% of the universe is
disproportionately the dips that never bounced.

## Verdict

The strategy is real, generalises beyond RGTI, and survives falsification. It is
**not** a money machine: it did not beat SPY on return or Sharpe over this period.
Its genuine advantage is drawdown — roughly SPY's return at 60% of SPY's pain.

**What this cannot tell us:** 2021–2026 is a single regime containing a small-cap
speculative boom unusually kind to dip-buying. A clean backtest is evidence the
edge existed recently, not proof it persists.

---

# Addendum — can news sentiment improve it?

Tested on the 207 trades from `highvol_long_stop-10`, using Alpaca's news API
(available back to 2021, `created_at` timestamps only — `updated_at` drifts and
would leak). News counted strictly in the 72h **before the 09:30 fill**, so the
pre-market window the idea calls for is included and nothing post-fill leaks in.

## The test

58% of trades had ≥1 article in the prior 72h (median 1, mean 3.0).

| bucket | n | avg | median | win% |
|---|---|---|---|---|
| quiet dip (≤1 article) | 120 | +2.87% | +4.69% | 57.5% |
| news dip (≥2 articles) | 87 | +1.89% | −10.18% | 43.7% |

| contrast | observed | permutation p |
|---|---|---|
| mean P&L difference | +0.97 pp | **0.629** |
| median difference | +14.87 pp | 0.029 |
| win-rate difference | +13.82 pp | 0.062 |

**Not significant where it counts.** Portfolio returns are driven by the *mean*,
and the mean difference is +0.97pp at p = 0.63 — indistinguishable from noise.
The median difference is nominally significant, but medians don't compound, and
~9 bucket contrasts were tested on one sample, so a Bonferroni threshold of
~0.006 is the honest bar. It doesn't clear it.

Tone (crude keyword lexicon) ran *backwards* from intuition — negative-tone dips
averaged +4.43% vs +1.51% for positive-tone. Directionally that fits contrarian
mean reversion (buy when people are scared), but n = 34 and 28. Not evidence.

Applying the filter would have removed 42% of trades to gain 17% per trade — a
net loss to compounding.

## Why this cannot currently be settled

Trade returns have a standard deviation of **14.3pp**. Required sample to detect
an improvement at 80% power:

| effect to detect | trades needed per arm | have |
|---|---|---|
| +0.5 pp/trade | 12,760 | 207 |
| +1.0 pp/trade | 3,190 | 207 |
| +2.0 pp/trade | 797 | 207 |

And enlarging the sample costs the edge it would be measuring:

| config | trades | CAGR | Sharpe | avg/trade |
|---|---|---|---|---|
| z<−2.0, top 8 | 207 | 11.8% | 0.77 | 2.46% |
| z<−1.75, top 16 | 450 | 9.8% | 0.61 | 1.49% |
| z<−1.5, top 24 | 699 | 8.7% | 0.54 | 1.13% |

So: any sentiment overlay that "improves" results on this sample is
unfalsifiable. The constraint is statistical power, not data quality or
lexicon sophistication.

## The analyst-ratings trap

Ratings are the most dangerous version of this idea. Free sources (yfinance,
most APIs) return **current** ratings, not what was known on the trade date.
Backtesting 2022 with 2026 ratings is pure lookahead and will produce a
spectacular fake result — the same failure mode as unadjusted split data, but
harder to notice. Point-in-time ratings history is a paid product (Benzinga,
FactSet). Without it, this cannot be tested honestly at all.

## Leverage — the arithmetic alternative

The strategy already beats SPY on Calmar (0.81 vs 0.53), so leverage converts
that into a return advantage without any new signal:

| leverage | CAGR | maxDD | Sharpe |
|---|---|---|---|
| 1.0x | 11.8% | −14.6% | 0.77 |
| 1.6x | 18.1% | −22.6% | 0.77 |
| 2.0x | 21.9% | −27.9% | 0.77 |
| *SPY* | *12.9%* | *−24.5%* | *0.81* |

~1.6x beats SPY's return at comparable drawdown. But **Sharpe is unchanged** —
leverage scales return and risk together, it does not create edge — and it adds
overnight gap and margin-call risk that a daily-bar backtest does not model.

---

# Addendum 2 — making it usable and scalable

## The actual constraint is not signal quality

| | |
|---|---|
| position-days used | 1,480 |
| position-days available (8 slots × 1,302 days) | 10,416 |
| **capital utilisation** | **14.2%** |
| mean concurrent positions | **1.29 of 8** |
| days holding nothing at all | 441 of 1,302 (34%) |

Returns decompose exactly: 40 trades/yr × 2.46% per trade ÷ 8 slots = 12.3%/yr.
Capital earns **zero** 86% of the time. That, not the entry rule, is what caps
this at ~12%.

## Lever 1 — park the idle cash (free, and it beats SPY outright)

Idle cash held in BIL (1–3 month T-bills), using its **actual** daily returns
rather than an assumed flat rate (real path: −0.10% in 2021 → 5.18% in 2024 →
2.52% in 2026, averaging ~3.0%):

| | CAGR | Sharpe | maxDD | Calmar | worst yr |
|---|---|---|---|---|---|
| baseline (cash idle) | 11.8% | 0.77 | −14.6% | 0.81 | −1.4% |
| **+ idle cash in BIL** | **15.1%** | **0.95** | **−14.4%** | **1.05** | **−0.3%** |
| *SPY buy & hold* | *12.9%* | *0.81* | *−24.5%* | *0.53* | *−18.2%* |

This beats SPY on **return, Sharpe, drawdown and worst year simultaneously**.
It is not an optimisation — it is correcting an omission. The strategy really
does sit in cash 86% of the time, and cash really does earn the short rate.

## Lever 2 — sizing is a leverage dial, not an edge

| per-position size | CAGR | Sharpe | maxDD | Calmar |
|---|---|---|---|---|
| 12.5% (baseline) | 15.1% | 0.95 | −14.4% | 1.05 |
| 25% | 22.6% | 0.83 | −27.8% | 0.81 |
| 33% | 29.1% | 0.89 | −36.5% | 0.80 |
| 50% | 39.3% | 0.93 | −41.0% | 0.96 |

Return scales; **Sharpe does not improve and Calmar gets worse**. Pick a number
here based on drawdown tolerance, not on expected return.

## Lever 3 — regime filter buys consistency, and costs return

| | CAGR | Sharpe | maxDD | Calmar | trades |
|---|---|---|---|---|---|
| BIL, no filter | 15.1% | 0.95 | −14.4% | 1.05 | 207 |
| **BIL + only trade when SPY > 200dma** | 9.3% | **1.06** | **−7.8%** | **1.19** | 130 |

Best Sharpe and Calmar of anything tested, and a −7.8% worst drawdown — but a
third less return and a third fewer trades. A genuine preference choice.

## What this strategy actually is

| year | strategy | SPY | diff |
|---|---|---|---|
| 2021 | +0.8% | +10.5% | −9.7% |
| **2022** | **−0.3%** | **−18.2%** | **+17.8%** |
| 2023 | +27.3% | +26.2% | +1.1% |
| 2024 | +23.3% | +24.9% | −1.5% |
| 2025 | +25.4% | +17.7% | +7.6% |
| 2026 | +4.9% | +11.8% | −6.8% |

A low-beta, cash-heavy strategy that shines in drawdowns and lags melt-ups. Its
single best year in relative terms was 2022, flat while SPY fell 18%. That is
worth real money in a portfolio — but it is **not** "beats SPY every year", and
anyone expecting that will abandon it during a bull run.

## Capacity — where it stops scaling

Median consolidated ADV of traded names ≈ $118M (IEX volume ÷ ~3%); 10th
percentile ≈ $15M.

| AUM | position size | % of median ADV | % of p10 ADV |
|---|---|---|---|
| $1M | $125k | 0.11% | 0.85% |
| $5M | $625k | 0.53% | 4.2% |
| $25M | $3.1M | 2.6% | 21% |

Staying under ~1% of ADV keeps slippage near the 20bps modelled. **Comfortable
to roughly $5M**; the thin tail of the universe binds well before $25M. Raising
the liquidity floor trades capacity for fewer candidates.

## Fixing the 86% idle at its root — more trade sources

Crypto is the most promising: 24/7 (no overnight gaps, more bars), high
volatility, and Alpaca already supports it. Screened on a current 126-day window:

| | half-life | hurst | \|drift t\| | amplitude |
|---|---|---|---|---|
| AVAX/USD | 14.1 | 0.468 | 1.20 | 25.9% |
| DOT/USD | 17.9 | 0.458 | 2.22 | 32.2% |
| LTC/USD | 20.4 | 0.412 | 0.98 | 17.6% |
| BTC/USD | 39.4 | 0.513 | 1.54 | 20.2% |

A handful qualify at any time, but the tradable universe is only ~20–30 pairs,
so it adds trades without adding much diversification. Other routes: a second
z-score timeframe (weekly), and intraday entries — the dip often reverts within
the session, which daily bars cannot capture.

---

# Addendum 3 — letting winners run instead of selling the bounce

## The upside is real

Currently the strategy captures only **21.7%** of the favourable move during a
hold (avg realised +2.46% vs avg peak +11.32%). Looking at the full forward path
from every entry:

| | mean | median | p90 |
|---|---|---|---|
| realised | +2.52% | +2.44% | +20.6% |
| peak within 20d | +19.9% | +14.5% | +45.7% |
| peak within 60d | **+38.5%** | +24.4% | +90.0% |
| close at 60d | +13.1% | +3.6% | +65.2% |

49% of trades peaked above +25% within 60 days; 24% above +50%. So the big moves
are genuinely there.

## But trailing exits lose on this strategy — every variant

All with idle cash in BIL and a −10% initial stop:

| exit rule | trades | CAGR | Sharpe | maxDD | win% | >25% wins |
|---|---|---|---|---|---|---|
| **reversion at z ≥ 0 (current)** | 207 | **15.1%** | **0.95** | **−14.4%** | 51.7% | 5.8% |
| trail 15% from peak | 208 | −1.1% | 0.02 | −40.5% | 31.7% | 7.2% |
| trail 20% from peak | 197 | 8.6% | 0.46 | −44.2% | 29.4% | 12.7% |
| trail 3× ATR | 210 | 11.7% | 0.60 | −28.5% | 35.2% | 11.0% |
| hybrid: run >15% then trail 20% | 206 | 13.7% | 0.83 | −25.9% | 46.6% | 7.3% |

Trailing does exactly what it promises — average win rises (+13.99% → +15.82%)
and big winners roughly double (5.8% → 12.7% of trades). It just costs more than
it earns: win rate falls 51.7% → ~30%, and drawdown roughly triples.

**Why:** the scanner explicitly selects for half-life 3–15 days, Hurst < 0.5 and
zero drift — stocks that *by construction do not trend*. A trailing stop is a
trend-following exit. The selection rule and the exit rule contradict each other.

## Where the idea does work: a separate momentum sleeve

Screen the **opposite** way (Hurst ≥ 0.55, drift t ≥ +2, efficiency ratio ≥ 0.15
— persistent uptrends), buy pullbacks to z < −1, and exit on a trailing stop:

| | CAGR | Sharpe | maxDD | >25% wins |
|---|---|---|---|---|
| reversion sleeve | 15.1% | 0.95 | −14.4% | 5.8% |
| momentum sleeve (trail 25%) | 20.5% | 0.81 | −36.3% | 13.5% |

It catches the big jumps. Standalone its drawdown is unacceptable — but the two
sleeves correlate only **0.29**, so blending helps both:

| mix | CAGR | Sharpe | maxDD | Calmar |
|---|---|---|---|---|
| 100% reversion | 15.1% | 0.95 | −14.4% | 1.05 |
| **75% / 25% momentum** | **17.3%** | **1.09** | **−11.9%** | **1.46** |
| 50 / 50 | 17.7% | 1.00 | −19.9% | 0.89 |
| 100% momentum | 20.5% | 0.81 | −36.3% | 0.57 |

At 25% weight the blend improves return, Sharpe *and* drawdown simultaneously.

## How much of this to believe

**The momentum sleeve's own numbers are not stable.** Across trailing settings
from 18% to 35% its CAGR runs 1.2% → 43.6% — a 42.5pp spread, non-monotonic
(11.6% at trail 28 sits between 21.7% at 26 and 27.8% at 30). With ~130 trades
dominated by a few large winners, a 2pp change in the trail changes which
winners survive. That is a noise surface, not a parameter surface. Any single
number from it — including the 20.5% above — is cherry-picked.

**The blend is far more robust.** Blended CAGR across the same sweep: 12.1% →
23.2% (sd 3.2 vs 12.3 standalone), and blended Sharpe ≥ reversion-alone at every
trail setting ≥ 20%, blended Calmar higher at *every* setting tested. The
diversification benefit survives parameter choice even though the sleeve's point
estimate does not.

**Defensible claim:** a ~25% momentum sleeve lifts the blend to roughly 15–19%
CAGR, Sharpe ~1.0–1.15, Calmar ~1.2–1.5, for a trail anywhere in 24–32%.
**Not defensible:** any specific configuration, or running the momentum sleeve at
high weight.

## Two more bugs, both of which faked results

1. **The falsification control was silently disabled in momentum mode.** The
   momentum branch built its `Signal` directly instead of routing through
   `apply_control`, so a `flip` run returned *identical* output to the real one
   (18.3% CAGR, 0.74 Sharpe, 131 trades — both). The sleeve looked validated
   while nothing had been tested. With the control connected: real +20.6% vs
   flipped **−0.8%**, which it now genuinely passes.
2. **Results were not reproducible.** Candidate symbols were iterated as a
   `set`, and Python randomises string hashing per process, so which symbols won
   the last free slots varied run to run. The same config returned 18.1%, 18.3%
   and 20.6% CAGR in three processes. Now ordered by scanner rank; three
   consecutive processes return 15.11% / 20.55% identically.

---

# Addendum 4 — signal research: one finding, three failures

Two literature/code surveys were run (academic short-term-reversal research;
open-source stat-arb repos). Both independently named the same top
recommendation. It did not survive testing here. Something else did.

## The finding: filter dips by how they were made

Decompose each day into **overnight** (`prev_close -> open`) and **intraday**
(`open -> close`), then require that the 5-day decline be mostly *overnight*
gaps rather than intraday selling. Mechanism: a gap is a liquidity/sentiment
shock that reverts; a grind down through the session is informed selling that
continues.

| | baseline | overnight share ≥ 0.3 |
|---|---|---|
| trades | 207 | 111 |
| CAGR | 15.1% | **17.2%** |
| **Sharpe** | 0.95 | **1.34** |
| max drawdown | −14.4% | **−11.1%** |
| Calmar | 1.05 | **1.55** |
| avg per trade | +2.46% | **+5.00%** |
| win rate | 51.7% | 61.3% |
| profit factor | 1.50 | 2.27 |
| P(mean trade ≤ 0) | 0.004 | **0.000** |
| months to significance | 40.5 | **19.5** |
| **risk-matched CAGR** | 15.1% | **22.3%** |

Risk-matched (both scaled to −14.4% drawdown) the edge grows **48%**, and the
time needed to prove it live halves.

### Robustness

- **Plateau, not a spike.** Risk-matched CAGR across thresholds 0.0 → 0.7:
  15.6, 18.0, 21.6, **22.3**, 17.9, 16.2, 15.1, 14.8. A smooth hill with a
  broad top, not a knife-edge.
- **Window is not special.** 3d/5d/8d/10d give 16.7 / 22.3 / 17.8 / 19.2 —
  every one beats the 15.1% baseline; 5d is best of four tested.
- **Replicates in the other cohort.** Broad-market: 2.2% → 5.3% risk-matched.
  Independent confirmation in a universe the parameter was not chosen on.
- **Consistent across folds**, not a few lucky ones: profitable folds go
  65% → 79%, mean fold return +3.45% → +4.39%.
- **Survives costs**: +4.80% per trade even at +10bps extra slippage per side.

### What is weak about it

- The original feature correlation was **nominally** significant only
  (Spearman +0.158, p = 0.020) and did **not** survive Bonferroni correction
  for the 9 features tested.
- The inverse-filter falsification was **inconclusive** — negating the signal
  leaves only 7–15 trades, too few to read. That test needs redesigning.
- Trade count drops 207 → 111, so capital utilisation falls 14.2% → 7.9%. The
  edge per trade nearly doubles, but the idle-capital problem gets worse.
- Both the 0.3 threshold and the 5-day window were the best of several tested.
  That is mild selection even though both surfaces are plateaus.

## Three things the research recommended that did NOT work here

**1. Residualization — the top recommendation of both surveys.** Replace the raw
price z-score with a z-score of cumulative FF3 residual return (market = SPY,
SMB = IWM−IWB, HML = IWD−IWF; betas fitted on formation bars only). Blitz et al.
report Sharpe 0.62 → 1.28 and that plain reversal is dead post-1990 while
residual reversal survives.

Result here, at every threshold tested:

| | trades | CAGR | Sharpe | risk-matched |
|---|---|---|---|---|
| raw z < −2.0 | 207 | 15.1% | 0.95 | **15.1%** |
| residual z < −2.0 | 221 | 13.0% | 0.88 | 9.1% |
| residual z < −1.25 | 732 | 16.3% | 0.66 | 5.3% |

**Why it fails here, measured rather than guessed:** FF3 explains a median of
only **22%** of the variance of names in this universe (p90 = 0.40). There is
little factor contamination to remove, so residualization strips 22% of the
variance while adding the estimation noise of four fitted parameters. The
literature's gains come from large-cap universes where factor exposure
dominates; this screen deliberately selects idiosyncratic, high-volatility
names. The drift filter also already rejects stocks that fell because their
sector fell.

**2. Bertram optimal thresholds.** Bertram (2010) solves analytically for the
entry/exit maximising return per unit *time* — the right objective when capital
is idle 86% of the time. With 40bps round-trip costs it prescribes entry at
**−0.37 to −0.64σ**, not −2σ, and claims ~53% of return per day is forfeited at
−2σ.

Empirically the direction is wrong past a point. Sweeping entry thresholds and
comparing at constant risk:

| z entry | trades | CAGR | Sharpe | maxDD | util | risk-matched |
|---|---|---|---|---|---|---|
| −2.00 | 207 | 15.1% | 0.95 | −14.4% | 14.2% | **15.1%** |
| −1.75 | 381 | 18.2% | 0.85 | −18.1% | 27.0% | 14.5% |
| −1.25 | 655 | 23.3% | 0.85 | −30.6% | 43.5% | 11.0% |
| −0.50 | 962 | 21.2% | 0.75 | −41.6% | 53.9% | 7.4% |

Shallower entries do raise raw CAGR and fix utilisation — but drawdown rises
faster, so risk-matched return falls monotonically. Bertram assumes a true OU
process with known parameters and one position at a time; these are estimated
parameters on stocks that are only approximately OU, held in an 8-slot
portfolio. **−2.0 was already the right answer.**

**3. News sentiment** (addendum 2): mean P&L difference +0.97pp at p = 0.63.

## Standing conclusion

The strategy's entry threshold is already optimal, and its signal cannot be
usefully factor-neutralized in this universe. The one improvement found is a
*quality filter on how the dip formed*, not a better dip detector.

It is **not enabled in the live config.** Changing the strategy mid-experiment
would contaminate the slippage measurement the live run exists to produce, and
the finding rests on a feature whose original correlation was nominal-only.
It is available as `strategy.min_overnight_share: 0.3`.
