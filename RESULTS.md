# Results — walk-forward backtest, 2021-01 → 2026-09

Universe: 14,765 symbols (12,757 active + 2,008 delisted), 11,530 with usable
history. 30 folds of 126-day formation → 42-day trading, disjoint. Slippage 20bps
per side, 8 concurrent positions, $100k start, no leverage.

## Headline

> **Read this first — the table below is the ORIGINAL run, not the current
> strategy.** It leaves idle cash earning nothing (the book is in cash 86% of
> the time). With idle cash in T-bills (Lever 1, below) the same rules give
> **15.1% CAGR / Sharpe 0.95 / maxDD −14.4%** against SPY's **12.9% / 0.81 /
> −24.5%**: ahead on return, Sharpe and drawdown. The version that matches the
> live executor (re-selects daily instead of every 42 days) is weaker: see
> addendum 14. The real-money book is the daily book (addenda 6–14), not this.

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

---

# Addendum 5 — the candidate cap was discarding good signals

`selection.top_n: 8` keeps only the 8 best-ranked survivors of the hard
filters each fold. Mean concurrent positions was 1.29, so the cap was never
about slot pressure: it simply threw away candidates. Removing it
(`top_n: 999`, i.e. every name that clears the gates) — highvol, −10% stop,
cash in BIL, 20bps/side:

| | top_n 8 (live) | uncapped | uncapped, `position_pct` 0.10 |
|---|---|---|---|
| trades | 207 | 370 | 370 |
| CAGR | 15.1% | 26.6% | 22.3% |
| Sharpe | 0.95 | **1.13** | **1.16** |
| max drawdown | −14.4% | −18.0% | −15.3% |
| avg per trade | +2.46% | +2.63% | +2.63% |
| win rate | 51.7% | 55.4% | 55.4% |
| **risk-matched CAGR** | 15.1% | **21.0%** | 20.9% |

The last column is deployable as-is, no leverage.

### Why it is believable

- **The rank carries no information.** Trades from ranks 9+ average +2.60% vs
  +2.58% for ranks 1–8 (Welch p = 0.99; Spearman rank-vs-P&L +0.08, p = 0.17).
  Ranks 9+ are significant on their own (p = 0.024). Uncapping is close to
  parameter-free: it stops discarding signals as good as the kept ones.
- **Controls pass.** Uncapped shuffle (same names, same entry rate, random
  days): 3.0% / 5.8% CAGR over two seeds, avg trade ≈ 0. Flip: −7.9%. The
  extra trades carry timing edge, not selection luck.
- **Every year at least matches baseline:** 2021 1.3 vs 0.8, 2022 **11.6 vs
  −0.3**, 2023 44.3 vs 27.3, 2024 23.3 vs 23.3, 2025 46.3 vs 25.4, 2026 YTD
  15.2 vs 4.9. 24 of 32 folds profitable.
- **Costs:** at 30bps/side 18.3% risk-matched, at 40bps 16.8% — both still
  above the baseline *at 20bps*.
- **Plateau:** top_n 12/16/24/40/80 → 19.8/18.8/25.4/23.3/21.0. Trades
  saturate at ~370 by top_n ≈ 30. 24 is the peak; report the uncapped 21.0,
  not the cherry-picked 25.4.
- **Gates are not fragile once uncapped:** halflife_max 25, amplitude 4%,
  hurst 0.55, drift_t 3.5 all land at 19.5–21.0 risk-matched.

### What is weak about it

- **Does not replicate in the broad cohort** (2.4% → 1.2%). Consistent with
  "the edge needs high volatility", but it is a failed replication.
- **Does not stack with the overnight filter.** top8+ovn 22.7%, uncapped+ovn
  24.7%; with the filter on, ranks 9+ add only +1.11%/trade (p = 0.46). They
  are partial substitutes — pick one, or accept a small combined gain.
- **Refresh cadence matters and live does not match the backtest.** The
  backtest re-selects every 42 days; `live/executor.py` re-selects daily on a
  rolling window. An honest 21/21 walk-forward scored only 9.5% risk-matched.
  Until a short-refresh backtest agrees, live results may not track these
  numbers regardless of top_n.

### Trap found and fixed

`step_days < trade_days` made trade windows overlap and the loop walked the
same dates twice, "returning" 91% CAGR / Sharpe 1.86. `make_folds` now refuses
that configuration (test: `test_overlapping_trade_windows_are_refused`).

Other results this round: `z_window` 10 → 8.6%, 40 → 8.3% (20 stays);
formation 63 → 4.1%, 252 → 4.6% (126 stays); `position_pct` 0.15 uncapped →
20.1% (more size, lower Sharpe).

---

# Addendum 6 — daily-cadence strategies (2026-09-22)

Goal: something that trades every day and is more consistent than a ~36
trades/year swing book. Data re-pulled from the **SIP** feed (consolidated
tape). IEX-only bars have wrong opens (RGTI 2026-09-18: IEX 16.31, official
16.25) and ~5% of true volume, so they are unusable for gap, auction or volume work.
Scripts are in `research/daily-strategies/`.

## Honest head-to-head, Feb 2021 – Sep 2026

| leg | CAGR | Sharpe | maxDD | +months | active days |
|---|---|---|---|---|---|
| swing (current, for reference) | 15.1 | 0.95 | −14.4 | — | ~14% capital used |
| **IBS tech ETFs** (QQQ/SMH/XLK, IBS<0.2, enter next open, hold 1 day) | 20.1 | 1.27 | −14.9 | 59% | 43% |
| **QQQ intraday "noise area" momentum** (flat every night) | 13.8 | 0.98 | −24.8 | 69% | 60% |
| **Overnight loser bounce** (signal at 15:50, MOC in / MOO out, 7.5bp/side) | 20.3 | 0.79 | −29.3 | 62% | 97% |
| **combo: QQQ day + ½ night + ½ IBS** | **38.4** | **1.58** | **−17.8** | **72%** | 99% |

Pairwise correlations between the three legs: |ρ| ≤ 0.06. Combo by year:
14 / 34 / 52 / 46 / 43 / 28 (2026 YTD). Capital does not stack beyond 1×
overnight. Intraday it can reach ~4.5× if noise is at max leverage while IBS
is held, so live needs noise leverage capped at 3.5× (PDT account, ≥ $25k).

### 1. IBS on tech ETFs — most robust
Longer history (2016+). 2016–20 / 2021–26: 19.4% / 19.9% CAGR executing at
the next open. Works on QQQ, SMH, XLK, SOXL, TECL, TQQQ; does nothing on
defensive, bond or commodity ETFs, and weakly on the 18-ETF equity basket (12.7%).
**Weakness:** the tech list was chosen after seeing per-ETF results. With the
signal at 15:50 and an MOC fill, QQQ degrades (13.9 → 8.8%) and SMH holds
(28 → 23%). Trade it at the next open, not MOC.

### 2. QQQ noise-area momentum (Zarattini/Aziz/Barbon 2024)
Reproduces the paper gross. 14.7% / 14.7% CAGR in both halves at 0.5bp/side.
Robust to a 1–5 minute fill delay (13.7–13.9%). Also works on TQQQ (1×: 25%)
and on SMH/SOXL in 2021+. **Fails on SPY after costs and on IWM entirely.**
Cost-sensitive: at 1bp/side it drops to 9%. Needs a liquid Nasdaq instrument.

### 3. Overnight loser bounce — biggest raw edge, most fragile
Stocks with day return ≤ −8% that close within 10% of the day's low (IBS < 0.1),
price ≥ $5, ADV ≥ $10M. Buy at the close auction, sell at the open auction.
The daily close *is* the 16:00 auction print (exact match 90%). Controls pass:
random names with the same count earn 11% (market overnight drift); the same
losers closing off the low (IBS > 0.5) lose 20%/yr. Not outlier-driven:
winsorised at ±10%/night it still gives 40% CAGR.
**The trap:** with the signal computed from the close (lookahead) it shows
58% CAGR / Sharpe 1.75. Recomputed at 15:50, when an MOC order must be sent,
it is **31% / 1.08** at 5bp and **20% / 0.79** at 7.5bp. Nearly all of the
honest return is 2024+ (2021–23: −1 / 0 / 7%). Strongest subsets: vol20 >
120% (+81bp/trade) and names up >20% in the prior 20 days (+87bp, positive
all 7 years). vol20 < 60% is negative.

## Dead (do not redo)

| idea | verdict |
|---|---|
| Mobius **TMO** as entry | **negative edge**: cross-up from oversold lags −20bp/5d (t −7.5), losing all 7 years; high-vol −54bp. It fires after the bounce |
| TMO as swing veto | +1.8pp risk-matched, but it is the overnight-share filter by another name (counts close<open); adds nothing on top of it |
| **TTM Squeeze** | fire → ~0 or negative; "in squeeze" −11bp/10d. No edge; ETF versions lose to buy-and-hold |
| IBS + TMO/TTM hybrids on ETFs | flip sign between 2016–20 and 2021–26 = noise |
| Stocks-in-play 5-min ORB (Zarattini/Aziz) | negative **gross** (−12bp/trade, 10% win) |
| QQQ / SPY 5-min ORB | QQQ 3–13% decaying post-2021; SPY ≈ 0 |
| Gap-down reclaim long | negative every variant |
| Gap-up ≥ 15% fade short | +55bp gross, 3.8% CAGR at 20bp, needs HTB borrow |
| RSI(2) Connors on ETFs | flat 2016–20, works only 2021+ |

## Bugs caught during the research
- Minute fetch: an API error on "recent SIP data" left the previous year's
  frame in scope, and it was saved as 2026. Caught before use.
- Gap minute fetch used fixed UTC offsets, which drop the last hour in winter (EST).
  Re-fetched with America/New_York.

---

# Addendum 7 — structural optimisation of the daily book (2026-09-23)

Rules set before looking: an economic prior for every idea, honest 15:50
signals only, both halves (2021–23 / 2024–26) must agree, parameters must
sit on a plateau, controls where possible. **About 50 variants were tested
this round**, so a lone t≈2 result means nothing. Everything adopted below
has t ≥ 4 or a monotone relationship, plus a written prior.

## Adopted

| change | why (prior) | evidence |
|---|---|---|
| **Night leg: skip names with 20d vol < 60%** | in quiet names a −8% day is news, not overreaction | those trades −33bp (t −8); the same 60% cut the swing cohort uses |
| **Night leg: on days with >30 raw signals, exposure × 30/n** | a market-wide liquidation is beta, not liquidity provision | per-day: ordinary days +20 to +52bp every year 2021–25; crowded days −24/−156/−37bp in 2022/24/25. Cutoff plateau 20–60 |
| **IBS leg: top-3 of 18 equity ETFs by 12-1 momentum (monthly)** replaces hand-picked QQQ/SMH/XLK | same idea as "tech", but chosen by rule, so it rotates | 15.0% / Sharpe 1.08 2016–26, both halves; control (bottom-3) 7.8%. Lower than tech3's 19.7%, which was hindsight |
| **Idle IBS half parked in SGOV** | free | +1.3pp/yr |

Night leg alone (7.5bp/side): Sharpe 0.78 → 0.98; weak half 1.1% → 6.9%.

| book (7.5bp/side, honest) | CAGR | Sharpe | maxDD |
|---|---|---|---|
| no-daytrade, before | 21.8 | 1.30 | −11.5 |
| **no-daytrade, now** | **23.8** | **1.46** | −14 |
| full (with QQQ intraday), before | 38.4 | 1.58 | −18 |
| **full, now** | **40.7** | **1.70** | −20 |

## Found, NOT yet adopted: the swing strategy as a third leg

Correlation with the night leg −0.03, with IBS +0.22. Equal thirds, no margin:
Sharpe 1.46 → **1.58–1.74**, maxDD −14% → **−9%**. At an equal −14% max
drop that is **24.6% → 30.6–34.3%/yr**. The low end uses the *honest*
21-day-refresh swing (9.9%/yr alone). The benefit survives even that.
**Blocked on:** the swing executor re-selects daily, and no backtest yet matches
that cadence (NEXT.md item 0). Resolve that, then give the live account a swing sleeve.

## Dead (do not redo)

| idea | verdict |
|---|---|
| portfolio vol targeting | Sharpe 1.30–1.38 vs 1.39 flat: no help |
| IBS only above 200d SMA (Connors) | hurts: 12.3% → 4.9% |
| crypto trend (BTC/ETH SMA 20/50/100, basket) | = buy-and-hold Sharpe, −60% DDs; basket negative after 25bp fees |
| crypto IBS | negative on BTC and ETH |
| overnight momentum (Lou-Polk-Skouras) | replicates, monotone deciles, but top decile +8.7bp/night < 15bp auction round trip |
| entering the night leg at 15:50 instead of MOC | +8bp into the close ≈ the spread you pay: no gain |
| depth ≤ −12% only | monotone, but halves trades; worse as a portfolio |

---

# Addendum 8 — high-conviction day trades under the PDT limit (2026-09-23)

Question: under $25k a margin account gets **3 day trades per rolling 5
business days** (not per day). Is there a rare, high-conviction intraday
setup worth spending them on? Protocol: pick on 2016–23 (ETFs) / 2021–23
(stocks), judge once on the 2024–26 holdout, intraday costs (1–3bp ETFs,
10bp stocks), rank by net expectancy, not win rate.

**No "90% winner" exists.** The highest win rates are traps: TQQQ gap-fill
longs win 62.7% of the time and lose money on average.

| family | result |
|---|---|
| ETF gap-fill, last-half-hour momentum (Gao), afternoon capitulation, midday trend, opening-drive fade — 6 ETFs × 4 strength tiers | **nothing reaches t ≥ 2.5 even in-sample**; best in-sample cells collapse out of sample |
| stocks: gap-and-go, gap-down squeeze, pm capitulation long, 15:30 losers → close | **all negative, both halves** (t −2 to −8) |
| stocks: gap-up fade short | in-sample t 0.5–0.7: fails |
| stocks down ≥25% by 15:00 keep falling into the close (~−1.5% gross) | real, both halves, but **untradable**: SEC Rule 201 short-sale restriction applies at −10%, and these are usually hard to borrow |
| **QQQ noise-area, FIRST breakout only, strength ≥ 0.341σ (in-sample median), ≤3 per 5 days** | QQQ ~5%/yr Sharpe 0.93 IS / 0.97 OOS. **On TQQQ, 1× equity (no margin)**: 9.7% IS / 13.1% OOS |

## The finding

The capped TQQQ breakout uses the night half's idle *daytime* cash (50% of
equity). Correlation with the book is −0.02.

| 2021–26 | CAGR | Sharpe | maxDD |
|---|---|---|---|
| no-daytrade book | 23.8 | 1.46 | −14 |
| **+ TQQQ PDT-capped, 50% of equity** | **36.0** | **1.84** | **−14** |
| + QQQ version instead | 28.3 | 1.67 | −13 |

Profile: ~70 trades/yr, win rate ~40% (trend-following: small frequent
losses, larger wins). 59% of entries at 10:00. Shorts slightly better than
longs; a down signal can be taken as a long SQQQ, so no shorting is needed.

Confidence: moderate. The leg itself was validated before this round (so
not mined here), and the threshold was fixed on 2016–23 and held out of
sample. But per-trade OOS t is only 1.2–1.4. Paper-shadow it before real money.

---

# Addendum 9 — the PDT rule is gone (2026-09-23)

FINRA's Rule 4210 amendments (SEC approval 2026-04-14, effective
2026-06-04) removed the pattern-day-trader designation, day-trade counting,
and the $25k minimum. Alpaca implemented them 2026-06-04: 4x intraday buying
power from $2,000 on leverage-enabled accounts; `daytrade_count` and
`pattern_day_trader` were removed from the API on 2026-07-06. Schwab
implemented them 2026-06-08. Brokers have until 2027-10-20.

Consequences, now in the code:
- `daily.daytrade_min_equity` $25,000 -> **$2,000** (the Reg T margin
  minimum). The $3k book qualifies, so the QQQ intraday leg places orders
  from the next 09:15 run.
- intraday leverage capped at broker multiplier − IBS weight (4x account
  -> 3.5x, 2x -> 1.5x, cash -> 0.5x)
- when the IBS leg holds QQQ, the intraday leg trades QQQM (same index)
- `make daily-live-check` no longer reads the removed `daytrade_count`

Addendum 8's 3-per-5-days cap no longer binds. Without it (2021–26, same book):

| intraday leg added | CAGR | Sharpe | maxDD |
|---|---|---|---|
| none | 23.8 | 1.46 | −14 |
| **full QQQ noise-area, up to 3.5x (now live)** | **40.7** | 1.70 | −20 |
| TQQQ strongest first-breakouts, 50% equity | 35.7 | 1.82 | −13 |
| TQQQ strongest first-breakouts, 100% equity | 47.5 | 1.79 | −16 |
| half and half | 44.4 | 1.83 | −17 |

---

# Addendum 10 — post-PDT improvements (2026-09-23)

| question | answer |
|---|---|
| **Night-leg decision time** (live scans 15:40; research used 15:49) | 15:35 37.8% / 15:40 34.8% / 15:45 26.1% / 15:49 28.4% CAGR: **no monotone relation, so no change needed**. The spread (±5pp) is this leg's real uncertainty |
| **Night-leg exit time** (not a day-trade question since the PDT rule went) | **open auction is decisively best**: +20.1bp/trade; 9:35 +1.9bp, 10:00 −9.3bp, 10:30 −21.5bp. The whole edge is in the opening auction, so OPG fills matter most |
| **Second intraday stream: QQQ + SMH in the same 3.5x budget** | ρ 0.60. Book 40.7%/1.70/−20 → **40.3%/1.78/−16**. Adopt when the QQQ leg has a few weeks of live fills |
| **Swing refresh cadence** (NEXT.md item 0) | 42d 16.8%/1.22 · 21d 10.8%/0.81 · 5d 16.1%/1.17 · **1d (matches live) 12.3% / 0.87 / −13.2%** |
| **Swing as a sleeve, using the honest 1d version** | with the QQQ/SMH split: Sharpe 1.78 → 1.82, maxDD −16 → −13, **CAGR 40.3 → 36.0–37.8**. Mostly a drawdown trade; **not worth a second executor on the live account** |

**Warning:** the intraday momentum leg alone did ~20%/yr in 2021–23 but only
~7%/yr in 2024–26, on both QQQ and SMH. It is the most likely leg to
disappoint live. Judge it by its first few months of fills.

---

# Addendum 11 — first live scan: duplicate bets (2026-09-23)

The first real-money 15:40 scan bought 20 names, and 7 of them were **2x long
SpaceX ETFs** from different issuers (SPCU, SPCF, SPCH, SPCM, SPAL, SPAX,
LOFF): one leveraged bet counted seven times, ~35% of the night leg. It barely
existed in the 2021–26 backtest, because single-stock leveraged ETFs have only
recently multiplied.

Fix (`daily.night_max_corr: 0.9`): picks are walked most-beaten first, and
one whose last-20-day returns correlate above 0.9 with an already-kept pick
is dropped. On that day's real data: 20 -> 14 bets, the 6 SpaceX duplicates
collapse into SPCU, and nothing unrelated is touched. It also catches a
stock alongside its own leveraged ETF. No name parsing, so new products are
covered as they launch. Crowding is now counted on distinct bets.

---

# Addendum 12 — news filters on the overnight leg: dead (2026-09-23)

Point-in-time Alpaca/Benzinga headlines, published between the previous close
and the 15:40 decision, for 17,432 honest overnight trades (vol ≥ 60%). 34%
had news. Categories were fixed before looking; the exclusion rule was t < −3
AND negative in both halves.

| news | n | mean | 2021–23 | 2024–26 | excess vs same night |
|---|---|---|---|---|---|
| none | 66% | +18.3bp | +20.9 | +16.5 | +2.0 (t 0.8) |
| FDA / trial | 0.9% | −8.2 | **−60** | **+68** | +8.5 (t 0.4) |
| legal / fraud | 0.4% | −35.6 | −77 | +18 | −37.8 (t −0.9) |
| dilution / offering | 1.4% | **+72.4** | +42 | +94 | +38.1 (t 1.6) |
| earnings | 9.2% | +19.7 | +28 | +12 | +0.6 |
| downgrade | 4.8% | +3.5 | −2 | +10 | +0.3 |

Nothing passes: bad-news categories flip sign between halves, and after
controlling for the night, every category is ≈ 0. The only outlier runs
against intuition (dilution bounces most, consistent with a stock recovering
toward its offering price) and is not significant. The leg buys *after* the
market has priced the news; its edge is whether the selling overshot, which
headlines do not measure. Same verdict as the swing strategy's news test.
Binary-event risk is handled by sizing (10% per name, duplicate-bet filter).

---

# Addendum 13 — signal sweep round 2: one robust finding, a pile of dead ends
(2026-09-23)

A second, broader signal sweep. Method: the validated engine, unmodified for
entry gates (the same monkeypatched `overnight_share` hook prior research used)
and a byte-identical research copy for portfolio-level hooks. The research copy
reproduces the package baseline exactly (15.11% / 0.95 / −14.4 / 207 trades),
and every gate window is pinned (the engine passes `overnight_window`=5 as the
gate's second argument, which silently mis-windows any feature with a different
natural window — a trap that produced one round of garbage before it was caught).

**The control that matters here is not shuffle/flip.** Every filter below works
by discarding trades, and discarding trades lowers drawdown mechanically. A
random gate that keeps the same *number* of trades reaches **risk-matched CAGR
~20** on its own:

| top8, random gate | n | CAGR | Sharpe | DD | risk-matched |
|---|---|---|---|---|---|
| keep 55% | 138 | 8.0% | 0.85 | −15.8 | 7.3 |
| keep 40% | 105 | 11.6% | 1.03 | −8.0 | **20.7** |
| keep 25% | 78 | 8.3% | 1.23 | −8.3 | 14.6 |

So a filter only has information if it beats ~20 at matched trade count. The
published overnight filter (22.3) barely does. Most of what follows does not.

## Feature audit — what actually separates winners from losers

207 baseline trades, Spearman(feature, P&L) on the decision bar, both halves:

| feature | rho | p | 21–23 | 24–26 | monotone in buckets? |
|---|---|---|---|---|---|
| **overnight share (5d)** | **+0.158** | **0.023** | +0.144 | +0.233 | **yes** |
| 20d volume z | +0.120 | 0.086 | +0.133 | +0.104 | ~ |
| 5d volume z | +0.066 | 0.348 | +0.053 | +0.079 | no |
| 5d close location | +0.079 | 0.255 | +0.007 | +0.201 | — |
| shock share (5d) | +0.047 | 0.504 | +0.094 | +0.011 | **no** |
| 52w-high distance | −0.055 | 0.432 | −0.029 | −0.109 | — |
| z-depth (20d) | −0.095 | 0.175 | −0.006 | −0.176 | — |
| down-day count (5d) | −0.121 | 0.083 | −0.094 | −0.208 | ~ |
| IBS of the last bar | +0.008 | 0.910 | −0.034 | +0.054 | — |

Overnight-share buckets are monotone, which is why it is the one feature worth
believing: `<0` → −0.11% (n 38), `0–0.3` → +0.16 (75), `0.3–0.6` → +3.60 (49),
`>0.6` → **+7.21** (45). That independently re-confirms addendum 4.

## Entry gates (top8, −10% stop, cash BIL; baseline 15.1 / 0.95 / −14.4 / rm 15.1)

| gate | n | CAGR | Sharpe | DD | risk-matched | avg/trade | 21–23 / 24–26 |
|---|---|---|---|---|---|---|---|
| overnight ≥ 0.3 *(known)* | 111 | 17.2 | 1.34 | −11.1 | **22.3** | +5.00 | 15.5 / 18.7 |
| vol z (5d) ≥ 1 | 127 | 15.4 | 1.14 | −12.0 | 18.5 | +3.94 | 12.6 / 18.2 |
| vol z (20d) ≥ 1 | 112 | 15.6 | 1.16 | −11.0 | 20.4 | +4.47 | 15.0 / 16.2 |
| vol z (20d) ≥ 2 | 65 | 12.8 | 1.39 | −7.9 | 23.4 | +5.84 | 13.3 / 12.4 |
| shock share ≥ 0.5 | 144 | 16.9 | 1.28 | −8.8 | 27.7 | +3.81 | 18.4 / 15.5 |
| 5d close loc ≤ 0.3 | 81 | 11.0 | 1.23 | −8.2 | 19.4 | +3.84 | 12.6 / 9.5 |
| z rising (turn up) | 70 | 9.7 | 1.18 | −6.7 | 20.7 | +3.73 | 12.7 / 7.1 |
| 52w dist ≤ −0.5 | 95 | 11.4 | 0.91 | −9.7 | 16.9 | +3.61 | 8.0 / 14.7 |
| IBS ≤ 0.10 (closed at the low) | 99 | 4.4 | 0.56 | −11.5 | 5.4 | +0.56 | — |

**shock share looked like the discovery, then failed.** `max daily drop ÷ total
5-day drop` ≥ 0.5 scored rm 27.7 (better than the overnight filter) and is
economically clean — one idiosyncratic down day should overreact, a multi-day
grind is informed selling. But the threshold surface is a **spike, not a
plateau**: 0.3→16.0, 0.4→17.9, **0.5→27.7**, 0.6→18.0, 0.7→6.7. The per-trade
buckets are non-monotone (`0.3–0.5` +0.20, `0.5–0.7` +6.47, `>0.7` +0.87) and
the continuous Spearman is 0.05 (p 0.50). Its portfolio result is a drawdown
artifact of one lucky threshold. **Rejected.**

**Everything else is at or below the random-gate bar.** 20d volume z (20.4) and
overnight (22.3) are barely distinguishable from a random 40% drop (20.7);
volume-5d, close-location, z-shape, 52w and IBS are weaker still. IBS has one
useful *negative* reading: buying when the decision bar closed at its low is the
worst bucket (+0.56%/trade), i.e. closing at lows is a falling-knife signal, not
a reversal signal — but the complement is nearly all trades, so it filters
nothing.

**Regime gates** re-confirmed as unhelpful: SPY>200dma buys Sharpe for return
(9.3 / 1.06 / −7.8, known); SPY 5d-return filters and a VIXY fear proxy are
unstable across halves (e.g. "only crash days" 3.0% in 21–23 vs 17.5% in 24–26).

## Structural knobs

| knob | verdict |
|---|---|
| **time stop** | 20d is optimal: 5d→11.2, 10d→11.9, 15d→15.0, 20d→15.1; ≥25d never binds (reversion exits first) |
| **fixed take-profit** | worse at every level: +5%→6.6, +8%→8.2, +10%→10.6, +15%→12.6 vs 15.1. Cutting winners is the same mistake as trailing |
| **slippage** | 0bps→16.9, 5→16.4, 20→15.1. Earning the bid instead of paying the ask is worth ~+2pp CAGR — real but modest, and not modelable without spread data |
| **inverse-vol sizing** | uncapped 22.3/1.16 → 22.9/1.24: a small Sharpe gain, no clean plateau |
| **size by overnight share** | top8 15.1 → 20.0 at tilt 4, but Sharpe only 0.95→1.07 and *no* gain on the uncapped config. Not worth adopting |

## The one robust finding — a correlation cap on new entries

Eight slots can be eight copies of one bet. Addendum 11 found seven different
issuers' 2× SpaceX ETFs in one night leg; the same happens in the swing book
(three uranium names, a stock and its own leveraged ETF). The fix is the
night-leg rule ported to the swing engine: walk candidates best-ranked first,
drop any whose trailing 20-day returns correlate above `max_corr` with an
already-held (or same-bar pending) name.

Deployable config (`top_n 999`, `position_pct 0.10`), cash BIL, −10% stop:

| config | n | CAGR | Sharpe | DD | risk-matched | 21–23 / 24–26 |
|---|---|---|---|---|---|---|
| uncapped baseline | 370 | 22.3 | 1.16 | −15.3 | 21.0 | 18.5 / 26.1 |
| **+ max_corr 0.7** | 311 | 20.2 | **1.33** | **−10.3** | 28.4 | 17.0 / 23.4 |
| + max_corr 0.6 | 281 | 20.5 | **1.47** | **−8.0** | **37.2** | 17.4 / 23.6 |
| + max_corr 0.5 | 246 | 16.1 | 1.33 | −7.8 | 29.5 | 12.9 / 19.2 |
| + max_corr 0.9 / 0.8 | 358 / 344 | 20.7 / 21.3 | 1.10 / 1.21 | −13.8 / −15.8 | 21.6 / 19.4 | — |
| top8 + max_corr 0.7 | 183 | 13.8 | 1.02 | −11.5 | 17.2 | 12.5 / 15.0 |

**Why it is believable**

- **It beats the matched random-drop control decisively.** Uncapped random keep
  67% (n 303) → rm 12.0; keep 50% (n 265) → rm 15.6. max_corr 0.6 (n 281) → 37.2.
  The gain is the *correlation*, not the trade count.
- **Plateau in the threshold** over 0.6–0.7 (Sharpe 1.33–1.47); 0.8 is the one
  soft point. **Plateau in the window**: at 0.7, win 10/30/40 → rm 28.9 / 27.5 /
  26.9.
- **Controls falsify:** flip → −4.2% CAGR / −0.72 Sharpe; shuffle → +1.4% / 0.21.
- **Survives costs:** mean trade +2.74% → +2.54% at +10bps/side extra.
- **Bootstrap** P(mean trade ≤ 0) = 0.000 (iid/block), 0.0004 (stationary), n 311.
- **Mechanism is a risk control, not a return forecast** — it lowers drawdown by
  making the 8 slots more independent, exactly as the night-leg duplicate filter
  does. It does not raise avg/trade much (+2.63 → +2.74).

**What is weak about it**

- **The broad cohort only half-replicates:** 4.5/0.36/−29.1 → 4.3/0.38/−22.9.
  Drawdown improves, Sharpe barely moves — consistent with "the edge needs high
  volatility", but it is a partial replication.
- **0.8 is off-trend** (rm 19.4, worse than 0.9's 21.6), so the surface is not
  perfectly smooth; 0.6–0.7 is the defensible range, not a single point.
- It trades CAGR for Sharpe/DD. On the *live top8* config the gain is small
  (15.1/0.95 → 13.8/1.02 at 0.7). Its value is on the uncapped config.

**Stacking with the overnight filter** (both robust): uncapped `ovn ≥ 0.3` →
16.8/1.22/−9.7/rm 25.0; adding max_corr 0.7 → 15.4/**1.36**/−8.5/rm 26.0. The
two are complementary but not additive on return.

## Verdict

One adoptable finding: **`max_corr` (~0.7) on the uncapped swing book** —
Sharpe 1.16 → 1.33, drawdown −15.3% → −10.3%, and it clears a control
(random-drop) that the previously-published overnight filter only barely clears.
It needs implementing in `live/executor.py` (the backtest hook alone does not
trade it live). Do **not** adopt shock-share: it is a threshold spike. The
overnight filter remains the best *entry-quality* improvement and still waits
for live fills, as planned.

Research scripts: `research/signals/` (`h.py` harness + `engine.py` validated
copy + `battery_a…m.py` + `feature_audit.py`).

---

# Addendum 14 — external review: what held up, what did not (2026-09-23)

A hostile strategy review (plus a second opinion from another model) was checked
claim by claim against the code and the cached research data. Fixes are in
the code; numbers below replace earlier ones where they differ.

## 1. The night leg was overstated: 26.0% → 18.7% CAGR

Two independent problems, both in the research data, neither in the live code.

- **Candidate lookahead.** `fetch_late.py` pulled 15:30–16:00 minute bars only
  for names whose *final close* was ≤ −6%. A name at ≤ −8% at 15:50 that bounced
  into the close was never considered. ~2.8% of candidates rally ≥ 2.2% in the
  last 10 minutes. Fixed: candidates are now chosen on the day's LOW (≤ −8%),
  a superset with no lookahead; the minute store was topped up (v1 kept as
  `lm1.v1/`). It added 129 trades: **median −94bp overnight**, winsorised mean
  −175bp. Small in count, all on the wrong side.
- **Bad bars.** A handful of split artifacts and renamed-ticker duplicates in
  the SIP daily panel: HIMZ −94% "day" then **+1,250% "overnight"** (2026-03-18),
  RGTX +274% the same night, BYAH/PHH and SWIN/AXG as identical twins. At 10%
  per name one such night adds +125% to the leg. Removed: any overnight move
  beyond ±100%, and same-day twins with identical returns.

Live rules (R6: vol20 ≥ 60%, crowd scaling 30/n, 10% cap), 7.5bp/side:

| | 2021–23 | 2024–26 | full |
|---|---|---|---|
| night leg, published | 5.8% / 0.37 | 52.1% / 1.48 | **26.0% / 0.99 / −25** |
| night leg, corrected | 4.9% / 0.33 | 35.6% / 1.13 | **18.7% / 0.77 / −26** |
| no-daytrade book (live), published | 11.6% / 0.93 | 38.4% / 1.91 | **23.8% / 1.46 / −14** |
| no-daytrade book (live), corrected | 11.2% / 0.89 | 30.6% / 1.60 | **20.1% / 1.27 / −14** |
| full book (+QQQ intraday), corrected | 33.6% / 1.68 | 39.8% / 1.50 | **36.5% / 1.57 / −20** |

The rebuilt v1 series matches the published one exactly (ρ = 1.00), so the
difference is the fixes, not a different pipeline. The book still works; it
works less, and the night leg is still mostly a 2024+ phenomenon.

**Live guard added.** The same split artifact can reach the live scan if our
daily bars have not absorbed a same-day corporate action. The 15:40 scan now
drops any name whose previous close disagrees with the quote feed's own
previous close by > 3% (`signals.prev_close_mismatch`).

## 2. How much of this survives the search

Deflated Sharpe (Bailey & López de Prado; trials treated as independent, so a
floor) and a stationary bootstrap of daily portfolio returns (20-day blocks),
corrected series, 2021-02 → 2026-09:

| | bootstrap P(mean ≤ 0) | DSR, 1 trial | 50 trials | 200 trials |
|---|---|---|---|---|
| no-daytrade book (live) | 0.0005 | 0.998 | **0.75** | 0.58 |
| full book | 0.0000 | 1.000 | **0.93** | 0.82 |
| IBS leg alone | 0.004 | 0.993 | 0.57 | 0.38 |
| night leg alone | 0.021 | 0.965 | **0.33** | 0.18 |

The combined book is robust; the night leg alone is not distinguishable from
a lucky pick out of the variants tried. Its value is diversification.
`report.render` now prints the daily bootstrap, skew, CVaR(5%) and worst month,
and the deflated Sharpe when given `n_trials`.

## 3. The swing book's headline depends on the calendar

Same rules (top8, −10% stop, cash in BIL), fold boundaries shifted by k
trading days — nothing else changes:

| offset | 0 | 7 | 14 | 21 | 28 | 35 |
|---|---|---|---|---|---|---|
| CAGR | **15.1** | 16.3 | 18.9 | 7.7 | 8.3 | 5.4 |
| Sharpe | **0.95** | 0.85 | 1.01 | 0.56 | 0.58 | 0.39 |
| maxDD | −14.4 | −19.0 | −19.8 | −24.3 | −28.4 | −24.5 |

Mean over offsets ≈ **12% / 0.72**; SPY is 12.9% / 0.81 / −24.5%. The published
15.1% / 0.95 was a favourable alignment of the 42-day windows, which is also why
addendum 10's refresh cadences were non-monotone (42d 16.8 · 21d 10.8 · 5d 16.1).
The version that matches the live executor (re-selects every day) is:

| daily re-selection | CAGR | Sharpe | maxDD | trades |
|---|---|---|---|---|
| top8 (live config) | 11.2% | 0.67 | −27.7% | 240 |
| uncapped (`top_n` 999, 10%) | 11.1% | 0.64 | −22.9% | 401 |
| uncapped + `max_corr` 0.7 | 8.5% | 0.58 | −18.3% | 341 |

So: **the swing book does not reliably beat SPY**, and neither NEXT.md item 0
(uncap) nor 0b (`max_corr`) helps at the cadence live actually trades. Both
stay off. The swing book stays paper-only. Any future swing number must be
reported as the mean over fold offsets, not one alignment.

## 4. Claims checked and found not to matter here

- **Delisting returns.** 0 of 207 trades (0 of 370 uncapped) were held when a
  name stopped trading — the −10% stop and 20-day time stop exit first. But a
  position in a name whose bars end would never have closed (every exit needs a
  bar), so the backtest now books it at the last close −30% (Shumway 1997).
- **Halts in the night leg.** 14 of 18,616 signals lack a next-day open (scored
  flat); nearly all are the last date of the data. Negligible.
- **Duplicate-bet filter and new listings.** The night universe needs 20 days
  of bars, so a new leveraged ETF is not eligible before it has a full return
  series; the filter's `len(r) >= 10` guard is never the binding one.
- **Gross cap at entry prices.** Longs cannot spend cash they do not have, so
  the cap cannot be breached by a winner. No fix needed.

## 5. Open, not fixable in code

- **Schwab has no market-on-open order.** The night leg's edge is in the open
  auction (+20.1bp at the auction vs +1.9bp at 09:35, addendum 10); Schwab gets
  a pre-market market DAY order, which a wholesaler may fill off the auction
  print. `make review` compares every open sell with the official open — that
  number, over the first ~50 round trips, decides whether the leg stays on
  Schwab. Alpaca live supports real OPG orders if it does not.
- Research data now lives in `data/research/` (gitignored, ~3 GB) instead of
  `/private/tmp`, and the research scripts point there.

---

# Addendum 15 — what a $3k + $1k/month account can expect (2026-09-23)

Dollar-level simulation of the live daily book (`research/daily-strategies/grow*.py`):
whole shares, the live sizing rules, intraday leg capped at 1.5x (Schwab's 2x
multiplier minus the IBS half), corrected night trades (addendum 14), $1,000
added every 21 sessions. Pre-tax.

**Historical replay, Feb 2021 → Sep 2026** ($70k deposited): $194k end,
time-weighted 33.5%/yr, Sharpe 1.68, maxDD −12.6%. SPY with the same deposits: $114k.

What moves the result, TWR per year:

| lever | TWR |
|---|---|
| as live (whole shares) | 33.5% |
| fractional shares (ideal) | 34.1% — rounding costs ~0.6pp; re-splitting / ETF twins buy nothing |
| intraday leg OFF (what a bot capped under $2k runs) | 19.9% |
| night cost 7.5 → 12.5 → 17.5 → 27.5 bp/side | 33.5 → 25.2 → 17.0 → 1.7 |
| intraday cost 0.5 → 1.0 → 1.5 → 2.0 bp/side | 33.5 → 29.7 → 25.7 → 22.0 |

The two things that matter: **run the intraday leg** (it only turns on when
the bot has ≥ $2k) and **night-leg exit fills at the auction price**. The
intraday leg alone is fading (2025 +2.4%, 2026 +1.6%); it earns its place by
diversifying 2022-type years. The 15:40 run now warns if night open sells
average > 15bp/side worse than the official open over ≥ 10 exits.

**Monte Carlo** (400 paths, 21-session blocks resampled from 2021–26, SPY on
the same days), account value:

| scenario | 1 yr | 3 yr | 5 yr | 10 yr | P(behind SPY) at 5 yr |
|---|---|---|---|---|---|
| deposited | 14,000 | 38,000 | 62,000 | 122,000 | |
| A backtest costs — median (p10–p90) | 16.7k (14.6–19.2) | 62.5k (48–79) | 148k (104–207) | 804k (472k–1.4M) | 6% |
| B +5bp night, 1bp intraday | 15.8k | 52.3k | 107k | 396k | 30% |
| C +10bp night, 1.5bp intraday | 14.8k | 43.7k | 79.8k | 205k | 69% |
| D backtest costs, intraday off | 15.7k | 51.6k | 103k | 362k | 30% |
| SPY, same deposits — median | 15.3k | 47.7k | 91.2k | 271k | |

Read it as a range, not a forecast: the paths resample 2021–26, the period the
rules were built on, and the night leg's return is concentrated in 2024+.
Every trade is short-term: in a taxable account, taxes at ordinary rates take
a large bite out of A–D and less out of buy-and-hold SPY.

---

# Addendum 16 — the hostile review, acted on (2026-09-24)

A second strategy review ranked ten fixes. All ten were done or tested here.
Everything below runs on **one simulator that calls the live code**
(`research/sim/`): `loser_picks`, `dedupe_correlated`, `night_sizing`,
`momentum_top`, `ibs_targets` and the `noise_*` functions from
`swingtrader/daily/signals.py`. Its intraday leg matches `noise.py` at
ρ = 0.9999; the full book comes out at 35.2% vs grow.py's 33.5%, because the
old research copy skipped two live rules (the duplicate-bet filter and the $5
floor at decision time). All numbers are the $3k + $1k/21-session replay,
whole shares, time-weighted: **2021–23 / 2024–26 / full**, CAGR/Sharpe/maxDD.
About 40 variants were run; rule set in advance: both halves must improve,
and a filter or tilt must beat a matched placebo.

## Adopted

| change | 2021–23 | 2024–26 | full |
|---|---|---|---|
| before (live 2026-09-23) | 29.8 / 1.75 / −12 | 41.3 / 1.80 / −13 | 35.2 / 1.76 / −13 |
| **+ night sizing tilt + QQQ/SMH intraday split (shipped)** | **33.7 / 1.93 / −10** | **49.9 / 1.91 / −15** | **41.3 / 1.89 / −15** |
| + 1.3x overnight, when the gate opens | 37.6 / 1.79 / −13 | 63.1 / 1.90 / −19 | 49.3 / 1.82 / −19 |

Same comparison at pessimistic costs (`tier_hi`: 7.5–25bp/side by price and
volume): before 25.0 / 1.33, shipped **31.0 / 1.50**, levered 33.7 / 1.36,
where leverage *loses* in 2021–23 (26.4 → 25.6). That is why it is gated.

- **Night sizing tilt** (`signals.night_tilt`, `daily.night_tilt_k: 0.25`).
  OLS of next-open return on (log vol20, day return), **fitted on 2021–23
  only**. Judged on 2024–26: 41.3 → 46.8%. A placebo with the same weights
  shuffled within each day: 42.9%. Fitted the other way round, 2021–23 goes
  29.8 → 35.0%, placebo 24.9%. The stable driver is depth (−11.5 / −14.7bp per
  sd in the two halves); prior 20-day return flips sign and was dropped. At
  $100k fractional the night leg alone goes 10.4 → 13.2%, Sharpe 0.83 → 0.86:
  it is mostly more return at the same gross, not better risk. Coefficients
  are frozen in the code.
- **QQQ + SMH intraday** (`daily.noise_extra: {SMH: SOXX}`): the budget splits
  equally, and SMH trades SOXX on days the IBS leg holds SMH. Sharpe 1.76 →
  1.89 with better return in both halves; 2024–26 drawdown −13 → −15.
  **Correction (addendum 17):** year by year it trails QQQ alone in 4 of 6
  years. Nearly all of the gain is 2025 (+16pp). Keep it as a
  diversification bet, not a proven gain.
- **Overnight leverage gate** (`daily.lever_weight: 0.65`, `signals.lever_ok`):
  both overnight legs go to 0.65 only after **50 night exits average ≤ 10bp/side
  against the official open**, no kill rule is active and realised drawdown
  is within 10%. It switches off as soon as any of those fails. Margin interest
  (12%/yr on the debit) is in the simulation.
- **Schwab open sells go to the listing exchange** (`daily.schwab_open_route:
  primary`). Schwab has no market-on-open order. A market DAY order sent before
  09:30 with `requestedDestination` set to the stock's listing exchange
  (NASDAQ, NYSE, ECN_ARCA, AMEX, BATS, from Alpaca's asset record) joins that
  exchange's opening auction, which is what MOO does. A refused route is resent
  with Schwab's routing within seconds and directed routing pauses for 5 days.
  Every fill logs its route, and the 15:40 run prints each route's cost and
  **auction hit rate** (fill within half a cent of the official open). That
  hit rate is the direct test of whether the emulation works.
- **Pre-registered kill rules** (`signals.KILL_*`, applied by the bot every
  run, shown in `make review`), fixed before any live result:
  - night leg: ≥ 100 round trips with a losing mean and t < −1, or open
    sells > 25bp/side over ≥ 30 exits
  - intraday leg: ≥ 120 round trips, losing, t < −1
  - IBS leg: ≥ 60 round trips, losing, t < −1
  - everything: realised-P&L drawdown worse than −25% of equity (built from
    P&L, so deposits cannot hide it)

  A killed leg opens nothing new; its exits continue.
  `python scripts/daily.py --unkill LEG --account live` undoes it, on purpose.
- **Swing book quarantined**: it is not scheduled unless `.env` has
  `SWING_BOOK=on`. Its 09:05 run held the account lock the 09:15 open needs.
- **Quoted spreads are now logged**: each 15:40 night pick writes its Schwab
  bid/ask spread to `logs/daily-decisions-live.jsonl`. That is the dataset a
  real per-name cost model needs.

## Dead (do not redo)

| idea | result |
|---|---|
| fill the night leg's unused money with SPY/QQQ close → open | 2021–23 29.8 → 27.5 / 26.6, 2024–26 up: one half only |
| idle IBS half in SPY / QQQ / overnight-only index instead of BIL | every variant lower in 2021–23 (best 29.0 vs 29.8); 2024–26 up: one half only |
| skip night names whose tier cost exceeds 20 / 30bp | 33.0 → 30.3 / 33.0: the cheap, costly names are the best bounces |
| Abdi–Ranaldo spread from daily bars as a cost model | on 60–120%-vol names it measures volatility (median 369bp), not spread; its buckets do not order the edge |

## Not code

- **Tax.** Every trade here is short-term. At a larger balance, micro Nasdaq
  futures (MNQ, 60/40 tax treatment under §1256, ~23 hours a day) are the
  natural home for the intraday leg. At $3k, one MNQ contract (~$50k notional)
  is far too big.
- The Monte Carlo in addendum 15 resamples the fitting period. Treat it as
  the optimistic end of a range, not a forecast.

---

# Addendum 17 — how optimized is it? Versions in dollars (2026-09-24)

Scripts: `research/sim/optimize.py` (sweeps, levers) and `research/sim/versions.py`
(history, Monte Carlo). Same account throughout: $3,000 on 2021-07-06 plus
$1,000 every 21 sessions, whole shares, tiered night costs.

## The parameter surface is flat. Tuning is done

One-at-a-time sweeps around the shipped config (full-period CAGR, shipped = 39.2%):

| knob (shipped) | range tested | CAGR range | verdict |
|---|---|---|---|
| vol20 floor (0.60) | 0.4–0.8 | 37.9–39.6 | plateau |
| crowding cutoff (30) | 15–60 | 38.7–39.8 | plateau |
| duplicate-bet corr (0.9) | 0.7–off | 38.6–39.8 | plateau |
| tilt k (0.25) | 0–0.6 | 34.9 (off) / 38.0–39.2 | plateau once on |
| IBS top-k (3) | 2–5 | 38.8–40.1 | plateau |
| IBS threshold (0.2) | 0.1–0.3 | 36.7–42.5 | 0.25 best cell, within search noise |
| intraday cap (1.5x) | 1.0–3.5x | 36.1–40.3 | **a 4x day-trading account buys ~1pp** |
| night per-name cap (0.10) | 0.06–0.20 | 32.0–48.1 | an exposure dial, see below |
| overnight gross (1.0x) | 1.3–1.8x | 46.3–55.6 | an exposure dial, Sharpe falls 1.82 → 1.56 |

No knob has a whole neighbourhood that beats the shipped value in both
halves by more than ~2pp. After ~60 variants, the best cell of a sweep is
mostly luck. **The rules are optimized. What remains is how much risk to take.**

The one structural inefficiency: the night leg deploys only **52% of its 50%
allocation** on an average day (about 5 names × 10%). Roughly a quarter of the
book is in cash overnight. A higher per-name cap uses that cash (0.15 →
45.3%, Sharpe 1.80, −18%), but it is concentration, not an edge. It is not
adopted, and neither is leverage beyond the gated 1.3x.

## Every version, in dollars ($65k deposited by 2026-09-18)

| version (first live) | 2021-12 | 2022-12 | 2023-12 | 2024-12 | 2025-12 | **2026-09-18** | TWR/yr | Sharpe | maxDD |
|---|---|---|---|---|---|---|---|---|---|
| deposited | 8,000 | 20,000 | 32,000 | 44,000 | 56,000 | 65,000 | | | |
| SPY buy & hold | 8,641 | 18,257 | 36,646 | 59,091 | 83,102 | **103,143** | 13.0% | 0.80 | −24.5% |
| V0 swing book (paper) | 8,052 | 21,560 | 37,050 | 53,195 | 77,939 | **94,661** | 12.4% | 0.87 | −13.2% |
| V1 IBS + night (09-22) | 8,961 | 21,594 | 38,104 | 57,540 | 100,739 | **126,343** | 20.2% | 1.35 | −13.9% |
| V2 + QQQ intraday (09-23) | 9,322 | 25,383 | 49,119 | 78,866 | 136,186 | **170,786** | 35.1% | 1.75 | −13.3% |
| **V3 shipped (09-24)** | 9,514 | 27,189 | 47,448 | 75,972 | 157,376 | **192,653** | 39.7% | 1.81 | −15.2% |
| V4 V3 + gated 1.3x | 9,825 | 28,199 | 48,776 | 80,051 | 187,614 | **235,952** | 46.5% | 1.73 | −19.0% |

Calendar years, V3: 22 / 33 / 25 / 30 / **85** / 16%. SPY: 10 / −18 / 26 / 25 / 18 / 13%.
2025 makes up a large share of every version's dollars. V3 beats V2 in 3 of 6
years: the tilt helps in 5 of 6, the SMH split in 2 of 6.

## Forward from 2026-09-24 ($3k + $1k/month), median (p10–p90)

| | 2027-09 (dep $14k) | 2029-09 (dep $38k) | 2031-09 (dep $62k) | P(ahead of SPY) 2031 |
|---|---|---|---|---|
| SPY | 15.2k (13–17) | 46.8k (38–58) | 87.9k (66–115) | |
| V3, history repeats | 17.4k (15–20) | 69.0k (54–90) | 172k (122–252) | 98% |
| V3, pessimistic costs | 16.8k (14–20) | 62.3k (49–81) | 143k (103–209) | 93% |
| **V3, edge halves** | **16.1k (15–18)** | **55.4k (47–65)** | **117k (95–145)** | **87%** |
| V4, edge halves | 16.5k (15–19) | 59.3k (49–73) | 133k (100–174) | 92% |

These resample 2021–26, the period the rules were fitted on, so treat even
"edge halves" as optimistic. Before tax. First checkpoint: kill-rule verdicts
at ~100 night round trips (about 4–6 weeks in).

---

# Addendum 18 — crashes: where the book breaks, and two guards (2026-09-24)

Question: does the book still work through a real drop (a Minsky moment),
not just the 2021–26 boom? Scripts: `research/sim/crash.py`. IBS and intraday
legs go back to 2016. The night leg's 15:50 data starts in 2020-11, so
**2020 was rebuilt from daily bars** (`panel2020.pkl`, 7,645 symbols) through
the same live picking code. That version reads the close (+9.1bp/day
lookahead on the overlap, correlation 0.76 with the honest leg) and is
bias-corrected.

## Each leg in a crash (unit weight, % over the episode)

| episode | SPY | IBS | night | intraday QQQ/SMH |
|---|---|---|---|---|
| 2018 Q4 selloff | −18.9 | −0.6 | n/a | **+11.8** |
| COVID crash 02-19 → 03-23 | −33.5 | +0.6 | **−35.9** (rebuilt) | +0.9 |
| 2022 bear | −24.1 | −10.3 | −0.8 | **+15.8** |
| Aug 2024 unwind | −7.9 | −9.2 | −3.1 | +3.4 |
| Apr 2025 tariffs | −18.6 | +6.7 | +8.5 | +5.8 |

On SPY −3% days the intraday leg averages **+114bp** (it is trend-following
and shorts), IBS +7bp and the night leg −42bp. The intraday leg is the
book's crash hedge, and the night leg is its crash risk.

## The failure: 2020-03-06

Nine names were held into Monday 03-09 (OPEC's price war, SPY −7.6% at the
open). **Five were oil producers** (NBR, MTDR, VET, OVV, OII), gapping
−33% to −53%: **−26% on the leg in one night**. Three things lined up:
- one theme counted as five bets: 0.9 correlation only catches near-twins
- only 19 signals, so the crowding rule did not fire
- the loss came over a weekend

## Two guards, adopted

- **`night_max_corr: 0.9 → 0.7`**: correlated names (a sector moving together)
  count as one bet.
- **`night_weekend_scale: 0.5`**: half size when held over a weekend or
  holiday. Per-trade weekend returns equal weekday ones (t = 0.04), but they
  swing harder (std 6.2% vs 5.5%), so this is risk parity across nights, not
  a return forecast.

Whole book (0.5 IBS + 0.5 night + QQQ/SMH intraday; before 2020 the night half
sits in T-bills):

| | COVID crash | 2022 bear | Apr 2025 | 2016–26 CAGR / Sharpe / maxDD | 2021–26 (honest data) |
|---|---|---|---|---|---|
| SPY | −33.5 | −24.1 | −18.6 | 15.7% / 0.92 / −34% | 15.3% / 0.94 / −24% |
| V3 as shipped | −17.3 | +10.6 | +14.6 | 27.2% / 1.46 / −24% | 37.5% / 1.71 / −15% |
| **V5 = V3 + both guards** | **−3.7** | **+19.1** | +14.8 | **29.7% / 1.69 / −13%** | **39.8% / 1.90 / −12%** |

The guards were designed after seeing 2020-03-06, so the COVID row is
in-sample for them. The 2021–26 column is not, and it improves. Rejected:
"stress memory" (crowding over 5 days; lower in every period), halving at
SPY 20d vol > 30% (−36% → −22% in the crash, but it gives back the rebound,
15% → 5%), and a leverage floor on the intraday leg (+0.5pp, more risk).

In dollars ($3k 2021-07-06 + $1k/21 sessions, tiered costs): V5 ends at
**$192,880** on 2026-09-18 vs V3's $192,653. Worst month −8.8% vs −11.1%,
maxDD −13.1% vs −15.2%, Sharpe 1.98 vs 1.81. It is insurance: behind V3 in
2024 (23 vs 30%) and 2025 (73 vs 85%), ahead in 2022 (43 vs 33%) and 2026.

## What still breaks it

- A crash that gaps on a weekday night: the night leg is still at full size.
- A slow bear market: IBS lost 10% in 2022, carried by the intraday leg.
  **That hedge is the leg that has been fading** (2025–26 ≈ 0). If it stops
  working, the book has no short side left.
- 2008-length bears and a 1987-style single day are not in any data here.
  The −25% realised-drawdown kill rule is the backstop.

---

# Addendum 19 — a conviction trade: bet big only when the signal is strong (2026-09-24)

Ask: something that does not trade every day, puts more money in when the
signal is confident, and so speeds up a small account.

Tested on the live-code simulator (V5 = shipped with crash guards, tiered costs):

| | 2021–23 | 2024–26 | full | maxDD |
|---|---|---|---|---|
| V5 | 37.9 / 2.23 | 43.8 / 1.84 | 40.7 / 1.98 | −13 |
| spare night cash → names with tilt ≥ 1.2 (cap 20%) | 39.7 / 2.08 | 46.2 / 1.72 | 42.8 / 1.84 | −15 |
| **intraday 1.0x + TQQQ conviction 0.5 of equity (same daytime margin)** | **51.2 / 2.21** | **48.3 / 1.79** | **49.8 / 1.98** | −14 |
| intraday 0.5x + TQQQ 1.0 | 61.8 / 2.06 | 50.5 / 1.66 | 56.3 / 1.86 | −17 |
| intraday 1.5x + TQQQ 0.5 (needs a 4x day-trading account) | 56.0 / 2.25 | 50.6 / 1.77 | 53.4 / 1.99 | −14 |

- **Night-cash overflow: not adopted.** More return, less Sharpe: concentration, not conviction.
- **TQQQ conviction trade: built** (`daily.conviction_*`, **shadow by default**).
  Only the day's FIRST noise-area breakout in TQQQ, and only when it clears the
  band by ≥ 0.341σ (the 2016–23 median, fixed in addendum 8). Long TQQQ for
  up-breakouts, SQQQ bought for down-breakouts. Out when the price falls back
  inside the band or through VWAP, else at 15:57. ~70 trades/yr (about one day
  in four), wins 39%, positive in 8 of 11 years (2016–26: +10, +8, +61, −1,
  −28, +26, +56, +10, +30, −7, +33 bp/trade). It takes 0.5 of the daytime
  buying power, and the regular intraday leg shrinks from 1.5x to 1.0x, so the
  account's margin use is unchanged. Own kill rule: 60 round trips.

In dollars ($3k 2021-07-06 + $1k/21 sessions): V5 **$192,880** → V7
**$228,433** (51.5%/yr, Sharpe 2.01, maxDD −14%). Years: 34 / 76 / 26 / 33 /
65 / 32% vs V5's 24 / 43 / 27 / 23 / 73 / 26%. It adds most in trending,
falling years (2022), so it also strengthens the crash hedge. Forward,
edge-halves case, $3k + $1k/month: $117k → **$133k** by 2031-09; $10k lump:
$30k → **$36k**.

Turn it on (`conviction_mode: auto`) once the regular intraday leg has about a
week of clean live fills.

---

# Addendum 20 — hostile review: what survived, and a Roth IRA book (2026-09-24)

A "leave no money idle" review made seven charges. Each was tested on the
live-code simulator (V7 = shipped + conviction; $3k + $1k/21 sessions, whole
shares; 2021–23 / 2024–26 / full, CAGR/Sharpe/maxDD). **Most of them were wrong.**

| charge | verdict | evidence |
|---|---|---|
| the $1k live test can't measure what it gates on | **true, fixed** | $50/name means every pick above ~$50 rounds to 0 shares, so the exit-cost sample is only cheap names; the capped equity ($1,000) was checked against Reg T's $2,000 *account* minimum, so the intraday leg (and therefore conviction) could never go live |
| cheaper margin (IBKR ~6%) unlocks leverage | **wrong** | the book rarely borrows: mean overnight gross 0.37 at "1.0x". 12% → 6% is worth 0.15–0.35pp/yr. On V7, 1.3x passes the adoption rule at both cost tiers anyway (tier 49.8 → 57.5, Sharpe 1.98 → 1.97; tier_hi 42.2 → 46.6); 1.5x fails at tier_hi, 1.8x everywhere. The gate stays on measured exit cost |
| the auction fill is the money | **true** | each bp/side on the open sell ≈ 0.85pp/yr: 3bp (real MOO) 55.4%, 7.5bp 51.1%, 15bp 45.2%, 25bp 36.9%. Alpaca live has real OPG/CLS; if Schwab's emulated open lands above ~10bp, move the brokerage book to Alpaca |
| idle cash in SGOV | **not worth it** | 26.5% of the book is idle overnight, but T-bill ETFs accrue per night held and a MOC→open cycle costs ~1bp/side: best hysteresis version +0.25pp/yr |
| fill night capacity with −6..−8% losers | **dead** | the band has no gross overnight edge (−8.2bp t −2.3 / −4.9bp t −0.9); the edge model flips sign between halves; −7%/−6% for all lower 2024–26; fill = placebo. `research/sim/depth.py` |
| diversify the intraday leg (TLT, GLD, IWM, XLE, USO, EEM, SPY) | **dead** | no gross edge on non-equity-index instruments; SPY passes 2016–23 but loses 2024–26; every split lowers both halves. The fading hedge is real and still open. `research/sim/intraday_div.py` |
| tax: use the Roth | **true, built** | below |

Not tested yet: ≤−8% names live excludes for volume $5–10M or price $3–5
averaged +38bp gross (vs +10bp traded); costs unmeasured.

## Roth IRA (`research/sim/roth.py`)

Rules (sources in the research log): Schwab offers **limited margin** in an
IRA (no borrowing, no shorting, but unsettled proceeds can be reused without
good-faith violations). Without it, whether sell-open → buy-close → sell-next-open
is a violation is disputed under T+1; intraday round trips certainly are.
Inverse ETFs are allowed. 2026 limit $7,500. A loss sold in a taxable account
and bought back in an IRA within 30 days is a wash sale and the loss is lost for good.

$10k on 2021-02-01 + $583/month ($49k deposited):

| | 2021–23 | 2024–26 | full | worst yr | end $ | tier_hi end $ |
|---|---|---|---|---|---|---|
| **Roth b1: IBS + night 1.0x + intraday via 3x ETFs (limited margin)** | 36.3/2.07 | 42.0/1.77 | **39.0/1.88/−13** | **+21.6%** | **$179k** | $140k |
| Roth a: IBS + night only (limited margin) | 15.6/1.23 | 32.5/1.65 | 23.5/1.44/−11 | +10.4% | $118k | $95k |
| Roth strict cash (legs halved, no intraday) | 7.6 | 15.8 | 11.4/1.47/−6 | +5.4% | $76k | $69k |
| SPY (≈ VTI) | 10.6 | 20.5 | 15.3/0.94/−24 | −18.2% | $85k | |
| QQQ | 10.3 | 23.9 | 16.6/0.80/−35 | −32.5% | $94k | |

2022 bear: b1 +19% vs SPY −24%. Intraday in the Roth: QQQ long → TQQQ, short →
SQQQ; SMH → SOXL/SOXS; notional = underlying leverage / 3 from the cash the
open sells free up (≤ 0.5 of equity = 1.5x underlying); flat by 15:57. At
+1bp/side extra ETF cost b1 is still 34.1%. Tax size: V7 taxed at 32% each
year ends at $149k vs $244k untaxed; b1 in the Roth ($179k) beats taxable V7
after tax. Same caveat as every table here: this replays the fitting period.

## Built

- `daily.night_probe_max_usd: 150` (real money): a pick that rounds to 0 shares
  is bought as 1 share if it costs ≤ $150, so exit costs are measured across the
  backtest's price mix. Logged as `PROBE`.
- Reg T's $2,000 is checked against the **account**; the bot's cap only has to
  clear `live_min_capital`. With a $1,000 cap on a ≥$2k account the intraday leg
  (and later conviction) now goes live.
- **Roth book** (`account: roth`): own Schwab account (`SCHWAB_ROTH_ACCOUNT_NUMBER`,
  never guessed), book file, fills log, cap (`DAILY_ROTH_CAPITAL`), switch
  (`DAILY_ROTH`, `make daily-roth-check/on/off`). Refuses to trade unless
  `ROTH_LIMITED_MARGIN=yes`. Never levers, no conviction trade, intraday
  long-only in 3x ETFs (`daily.roth_etfs`).
- **Wash-sale guard**: each real-money book skips any symbol the other held or
  closed in the last 31 days (SGOV excepted).

---

# Addendum 21 — three more optimizations tested, none adopted (2026-09-24)

V7 base, $3k + $1k/21 sessions, 2021–23 / 2024–26 / full CAGR/Sharpe/maxDD.

| idea | best variant | verdict |
|---|---|---|
| conviction trade on SOXL/SOXS (`research/sim/conv2.py`) | TQQQ 0.25 + SOXL 0.25: 47.7/2.02 · 49.0/1.73 · 48.3/1.85 vs V7 51.2/2.21 · 48.3/1.79 · 49.8/1.98 | **dead**: SOXL 2016–23 t 0.93 (TQQQ 2.31), same direction as TQQQ 95% of shared days, twice the vol |
| slow-bear hedge (`research/sim/hedge.py`): IBS off / night ×0.5 below SPY 200d, SH or SQQQ sleeve below 200d | SQQQ from idle cash: +0.2–1.6pp, inside placebo; sleeve alone −0.8%/yr 2016–23, −0.7% in COVID | **dead**; premise overstated: without the intraday leg 2022 was still +6.3% (with it +45.8%) |
| night names the filters exclude (`research/sim/thin.py`) | price $3–5 at 15bp/side: 52.8/2.26 · 51.6/1.87 · 52.2/2.05; at 30bp: 51.1 · 47.8 · 49.5 | adv $5–10M **dead** (2024–26 falls, maxDD −20%); price $3–5 **conditional** on real cost |

Price $3–5: a 1¢ tick is 25bp of spread on a $4 stock, and break-even is
~25–30bp/side, so the existing 15bp "<$10" tier is not safely conservative
there. Adopt `night_price_min: 3.0` only if live fills show names under $10
cost ≤ ~20bp/side vs the official open (+1–2pp/yr if so).

Lead, untested: IBS trades earn more with SPY below its 200d SMA (2016–23
+37bp n 109 vs +17bp; 2024–26 +138bp n 17 vs +16bp). Too few holdout trades to act on.

Across addenda 17, 20 and 21, ~80 variants have now been run on the rules. The
remaining upside is execution (open-sell cost, ~0.85pp/yr per bp) and the two
gated switches (conviction, 1.3x), not rule changes.

---

# Addendum 22 — maximum growth: faster cadence (dead), growth-optimal sizing, a 3x-ETF margin fix (2026-09-24)

**Cadence** (`research/sim/cadence.py`): deciding the intraday leg every 5 / 10 / 15 / 60 min
instead of 30 cuts edge per trip (5bp → 1.5bp at 5 min) faster than it adds trips; book
44.3 / 49.9 / 45.9 / 47.5 vs 50.0. A 09:45 start is worse everywhere. A second conviction trade
per day: +1.2pp/yr on ~12 trades/yr, holdout t 0.37 — not adopted. The VWAP exit is inert at
30-min checks. Hold-to-close is the best 2024–26 variant but fails 2016–23: watch, don't adopt.

**Margin fix (shipped):** a 3x ETF carries 75% house margin (3 × 25%), so TQQQ/SQQQ at 0.5 of
equity uses 0.375 of the account, not 0.25. The intraday cap is now
`mult × (1 − conviction × conviction_margin) − ibs` (2x account: 0.75, was 1.0). V7 at the
honest cap: **47.5% / 1.99 / −13%** (was reported 49.8%); tier_hi 39.6%.

**Growth-optimal sizing** (`research/sim/growth.py`, 208 configs, $3k + $1k/21 sessions):

| | history, tier | tier_hi | edge halves at tier_hi | MC 5y P(DD>30%) / P(DD>50%) under EH |
|---|---|---|---|---|
| V7 (shipped) | 47.5 / 1.99 / −13 | 39.6 / 1.73 | 18.5 / −21 | 23% / 0% |
| **aggressive profile: 1.3x overnight, 20% name cap, conviction 0.5, intraday 0.6** | **71.1 / 1.97 / −21** | 54.6 / 1.63 | 22.2 / −31 | 68% / 9% |
| 4x daytime version (not available: account multiplier 2.48) | 89.9 / 2.00 / −25 | 70.0 | 26.7 / −34 | 84% / 18% |
| max historical growth (2.0x overnight, 4x day) | 109.5 / 1.89 / −31 | 81.1 | 27.7 / −46 | 98% / 45% |

Scaling every leg by L: history keeps rewarding leverage up to 6x, but with the edge halved at
tier_hi growth peaks at L ≈ 3 (29.9%, maxDD −48%) and falls to 9.8% at 6x. Optimizing on the
historical frontier is how accounts blow up. The aggressive profile is roughly half-Kelly under
edge-halves: +3.7pp/yr there over V7 for ~3x the drawdown odds, and +24pp/yr if history holds.
COVID rebuild: V7 −17.5% maxDD, aggressive −23%. Schwab can raise house margin in a crash.

Built: `daily.profiles.aggressive` in config.yaml, applied to the real-money brokerage book only
when `.env` has `DAILY_LIVE_PROFILE=aggressive` (never paper, so paper stays the control; never
the Roth, which is also capped at 1.0x overnight whatever the weights).

---

# Addendum 23 — better picking signals for the night leg (2026-09-24)

`research/sim/features.py`. Nine features computable at 15:50, a prior written for each
before testing; quintiles of next-open net return per half, then each added to the tilt
OLS (fit 2021–23, judged 2024–26 and reversed) against within-day shuffles and random-noise
features. Baseline V7 at the honest 3x-ETF margin: $260.6k (tier) / $207.8k (tier_hi).

**Accuracy does not move.** Win rate is 42–55% in every bucket of every feature; buckets
differ through the size of wins and losses. Late selling, relative volume, gap share, SPY
context, idiosyncratic move, distance from 20d/52w low, price: none monotone, most flip
between halves. Each adds −$3k to +$3k: dead.

**Yesterday's return: borderline, built OFF.** Names up hard yesterday and down ≥8% today
bounce more (top decile: +92bp net, 52% wins, avg win +589 / loss −449bp). As a third tilt
input (+31bp per sd; day-clustered t 2.0 / 2.6 per half, 3.2 pooled): 47.5 → 50.5%/yr,
Sharpe 1.99 → 2.11, **$260.6k → $283.7k** (tier_hi $207.8k → $226.8k); better in every year
2021–26; the reverse fit holds; beats every shuffle and noise-feature seed. Against it: the
prior predicted the opposite sign, it is the best of 9 on top of ~90 earlier variants, and the
effect is concentrated in the top decile. `daily.night_tilt_model: v2` switches it on; under
v1 the 15:40 log prints the v2 weights.

**IBS up-weighted below SPY's 200d SMA: dead as sizing.** The per-trade edge is real (2016–23
+50bp, t 3.5 vs +18bp) but sizing up takes daytime room from the intraday leg: 2021–23
falls at both cost tiers (×1.5: 48.6 → 48.0; ×2: 46.8).

---

# Addendum 24 — a "leap" book: can a day trade turn $100 into $500? (2026-09-24)

`research/sim/leap.py`. The ask: a separate book for big, fast gains. Five
families were pre-registered with a written prior (in the file's docstring,
before any run): **20 variants**, on top of ~90 earlier intraday variants
(addenda 6, 8, 19, 21, 22). Cash-account rules ($100 cannot use margin): 1.0x
equity, no shorting, a down signal buys the inverse ETF. Costs per side: 3x
ETFs 3 / 5bp intraday, 5 / 7.5bp at the open; stocks on the tier / tier_hi table.

| family (tier costs) | 2021–23 CAGR/Sh/DD | 2024–26 | placebo | verdict |
|---|---|---|---|---|
| A. SOXL opening-range breakout, 15 min (cross-half pick both ways) | 82.1 / 1.27 / −45 | 62.9 / 1.04 / −60 | beats 20/20 | **passes, fragile** |
| A. TQQQ ORB (reference: the conviction trade owns TQQQ) | 35.5 / 0.92 / −34 | 11.5 / 0.48 / −45 | — | weak, collides |
| B. 3x-ETF Donchian breakout, multi-day | best in one half, loses the other | | 10% | dead |
| C. small-cap gap-and-go with a runner | −14 to −54 | −25 to −86 | 65% | dead (as addendum 8) |
| D. night leg concentrated, top 1 at 100% | −39.9 / 0.34 / −96 | −76.3 / 0.37 / −99 | 75% | dead: Kelly |
| D. night leg top 3 | 17.8 / 0.58 / −45 | 83.0 / 1.12 / −59 | — | dead at tier_hi (−1.2%) |
| E. SOXL IBS < 0.2, next open → following open | 52.6 / 1.05 / −39 | 48.0 / 1.03 / −54 | beats 19/20 | **passes** |

**The ORB does not survive stress.** 2016–20 was never used to choose
anything, and there ORB15 makes 3.6%/yr with a −80% drawdown. At 10bp/side it
loses money in 2016–20 and makes 15–28% after. A market order one minute after
the break (what a bar-polling bot gets) takes it to −10 / 52 / 34%. Longs carry
it (inverse-only: −4 / 7 / 19%). Day-clustered t per half ≤ 2.2. By year:
+23 +3 +10 +5 −13 | +37 +41 +17 | +30 +64 −23 bp/trade (2016 … 2026 YTD).
That is a 2021–25 semiconductor-volatility regime more than a rule. ORB5 was
steadier in 2016–20 (25.6%) but choosing it for that would be hindsight.

**SOXL IBS holds up:** 50.1 / 52.6 / 48.0% in 2016–20 / 2021–23 / 2024–26,
36% in each at 15bp/side, t 2.7 / 1.8 / 1.7. It is the daily book's IBS rule
(the same `ibs()` function) on one 3x ETF instead of 18 1x ETFs, so it is the
same bet, concentrated. maxDD −54%.

**The number that was asked for.** Block bootstrap (21-day blocks), whole shares:

| | P(5x in 3 / 6 / 12 months), $100 | P(−50% first, 1y) | median years to 5x (hist) | same, edge halved |
|---|---|---|---|---|
| SOXL ORB15 | 0.0 / 0.7 / 6.7% | 3.5% | 4.3 | not within 8 years (P 42%) |
| SOXL ORB15, fill +1 min | — | — | 7.6 | not within 8 years (P 27%) |
| SOXL IBS < 0.2 | 0.0 / 0.0 / 0.9% | 2.0% | 3.6 | 7.9 |
| night top 1 (the only "lottery" shape) | 0.7 / 3.5 / 9.7% | **66.9%** | — | — |
| aggressive profile (addendum 22), for reference | | | 3.0 | 8.0 |

Nothing tested here turns $100 into $500 in months. The fastest honest rule
takes about as long as the aggressive profile already running on the existing
book, with 2–4x its drawdown. The only shape with a real chance of a 5x year
(concentrated night picks) reaches −50% first two times in three.

**Built, SHADOW ONLY, off:** `swingtrader/leap/` (`signals.py`: `orb_break`,
`orb_fill`, `orb_stopped`, `ibs_entry`, which the research now calls; `shadow.py`:
decide + append to `logs/leap-shadow.jsonl`, with no broker or order code at
all), `config.yaml leap:` (`enabled: false`), and `LEAP_LIVE` / `LEAP_CAPITAL` /
`SCHWAB_LEAP_ACCOUNT_NUMBER` reserved in `.env.example` and read by nothing.
Not scheduled, and there is no make target yet.

Caveats: SOXS is modelled as −1x SOXL's intraday move (close, not exact). The
gap universe is names still listed in 2026 (survivorship flatters longs, and
they still lost). Halts are not modelled. A live leap book in the brokerage or
Roth account would create **wash sales** against the Roth intraday leg, which
also trades SOXL/SOXS; a loss disallowed against an IRA is lost for good.
Every gain is short-term.
