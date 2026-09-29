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

> **⚠ Addendum 30 (2026-09-28): every night-leg number before it is overstated by about one
> fifth.** The research night pool used split-adjusted prices, so the $5 floor, the cost tier and
> share rounding saw later reverse splits' inflated prices. Restated on raw prices (2021-26):
> **V7 shipped 47.2% / Sharpe 2.06 / −14 at 3bp** (was 58.0 / 2.33) and **29.4% / 1.41 / −17 at
> tier_hi** (was 39.6 / 1.73); edge-halves at tier_hi 13.3% (was 17.5); Roth M3 35.3% / 22.4%.
> Addendum 39 has every book on the raw pool. Research must use `load_sim(raw_price=True)`.

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

---

# Addendum 25 — micro index futures (MNQ, MES): do our edges carry over? (2026-09-24)

`research/sim/futures.py`. The ask: futures as a real strategy at sane leverage,
not a one-day 5x. **Proxy, not futures data:** QQQ minute bars for NQ and SPY
for ES, regular session only, index = 41 x QQQ / 10 x SPY. No Globex-session
signals, no roll or basis. Overnight holds bear the ETF's close -> open gap, as
a futures holder would. Costs, stated assumptions: $1.00 (tier) / $1.50
(tier_hi) per micro per side plus 1 / 2 ticks. That is 0.25 / 0.41bp per side
on MNQ and 0.58 / 1.03bp on MES at 2026 levels, but ~1.7bp on MNQ in 2016,
when the contract was a quarter the size. ETF comparison at 1bp (the house
noise-leg figure is 0.5bp; both shown). Tax: 30% short-term, 15% long-term;
Section 1256 = 21% blended. 12 pre-registered variants, priors in the docstring.

| tier costs, CAGR / Sharpe / maxDD | 2016-20 | 2021-23 | 2024-26 | bp/day, t (21-23 / 24-26) | placebo |
|---|---|---|---|---|---|
| **MNQ noise leg, vol-target <= 2x** | 8.1 / 0.71 / −23 | 19.4 / 1.52 / −7 | 10.4 / 0.85 / −18 | +5.1 t2.5 / +2.7 t1.3 | beats 10/10 |
| QQQ noise leg (ETF, 0.5bp) | 13.9 / 1.15 / −14 | 19.8 / 1.55 / −7 | 9.2 / 0.76 / −18 | | |
| MES noise leg | −5.0 | 13.5 | −7.5 | +3.0 / −1.3 | 8/10 |
| MNQ ORB30 (the pick on both halves) | **−8.6** | 16.7 | 10.7 | +6.5 t2.0 / +4.3 t1.5 | ORB15 16/20 |
| MES ORB 5/15/30 | −10 to −11 | 4 to 7 | −0.7 to −4.7 | | 17/20 |
| MNQ IBS < 0.2, 15:59 close -> next open | 4.2 / 0.72 / −7 | 4.7 / 0.69 / −14 | 7.2 / 1.13 / −8 | +8.3 t1.2 / +17.3 t1.9 | 19/20 |
| MES IBS, -> next open | 3.3 | 1.8 | 2.9 | t0.6 / t1.0 | 20/20 |
| MNQ / MES IBS, -> next close | 20.0 / 7.7 | 2.6 / 2.7 | 13.2 / 6.6 | exit pick flips between halves on MNQ | 20/20 |

Stress, CAGR 2016-20 / 2021-23 / 2024-26. "+1 tick" means $1.50 + 3 ticks; "fill 1 min late" means filling one minute after the signal.

| Rule | +1 tick | Fill 1 min late |
|---|---|---|
| MNQ noise | −0.8 / +14.9 / +7.8 | +7.6 / +18.2 / +9.5 |
| MNQ ORB15 | −12.7 / +11.4 / +6.6 | −10.1 / +11.7 / +6.1 |
| MES noise | dead | dead |

**Verdicts.**
- **MNQ noise leg: passes.** It is positive in both halves at both cost
  tiers, beats every placebo, and survives both stresses in 2021-26. But it
  is **the live QQQ noise leg in another wrapper, not a new edge.** Running
  both doubles one bet.
- **ORB on the index: dead.** NQ is negative in 2016-20 at every range and
  both cost tiers, which repeats addendum 24's SOXL ORB. ES is dead outright.
- **MES noise: dead.** 2024-26 is negative.
- **IBS overnight: passes the sign test but is weak.** MNQ -> open is
  positive in every period, but t is below 2 in each half. It is also small:
  4-7%/yr at 1x, in the market ~18% of nights. It is the IBS leg's bet again.

**Is futures a better vehicle than the ETF?** Only slightly, and only
recently. At 2026 contract sizes MNQ costs half of QQQ at 0.5bp. In 2016-20
it was worse, because the contract was small. Tax does more: the same MNQ
noise series taxed as short-term earns 10.6% after tax (2021-26), versus
11.9% under 1256. Against QQQ at 0.5bp, futures come out about +1.6pp/yr
after tax (11.9% vs 10.3%), roughly half from cost and half from tax. There
is also no wash-sale rule, which matters next to the Roth.

**Account size is the real constraint.** One MNQ is $61k of Nasdaq and one
MES is $39k of S&P. MC: 1 year, 21-day blocks from 2021-26, whole contracts
at 2026 notional, at least 1 contract when margin allows. "Tradable" means
the account covers the assumed margin: 25% of a 7%-of-notional initial
margin intraday, the full 7% overnight.

| MNQ noise | $1k | $5k | $10k | $25k | $50k |
|---|---|---|---|---|---|
| leverage of 1 contract | 61x | 12x | 6.1x | 2.4x | 1.2x |
| tradable | no | yes | yes | yes | yes |
| median 1y / P(−50%) / P(ruin) | — | +122% / 13% / 3% | +61% / 1% / 0% | +24% / 0 / 0 | +12% / 0 / 0 |

| MNQ IBS (overnight margin) | $5k | $10k | $25k | $50k |
|---|---|---|---|---|
| median 1y / P(−50%) / P(ruin) | −15% / 1% / **51%** | +41% / 8% / 5% | +16% / 0 / 0 | +8% / 0 / 0 |

Under ~$30k (MNQ) or ~$20k (MES), one contract is already more than 2x
leverage. The small-account medians are just forced leverage on a history
that includes the strong 2021-23. MES at $1k runs at 39x: median −37%,
P(ruin) 74%. At <= 2x, MNQ needs **>= $30k per contract**.

**Built:** `swingtrader/leap/signals.py` has `FUTURES` specs and
`futures_contracts()`. It sizes whole contracts, returns 0 rather than force
one past `max_lev`, and has a test. No new signal: a futures book would call
`daily.signals.noise_*`. Nothing is scheduled, no live code changed, and no
order path exists. Going live would need Schwab futures approval (a separate
futures account). There is no PDT rule, and the market runs nearly 24 hours,
with Globex moves the proxy never saw.


# Addendum 26 — second hostile review: two Sharpe levers dead, the ops holes closed (2026-09-24)

A "leave no money idle, +1 Sharpe" review. The honest arithmetic first: leverage does not
move Sharpe, and an uncorrelated stream of Sharpe S2 lifts the book to about sqrt(S1^2 + S2^2),
so +1 on a ~1.7-2.0 book needs an independent ~2.0 stream. The two candidates that could
plausibly add Sharpe without new data were tested; both are dead. What shipped is
operational: the dead-man switch and review reporting.

**Shipped (no strategy change):**
- **Watchdog.** Every trading-day run stamps `state/heartbeat*.json`; the 16:10 run emails if
  today is missing the open, the close, the flatten, or more than 2 of the intraday runs (half
  days: only what falls before the bell). Catches lock timeouts, crashes before the failure
  email, and timers that did not fire.
- **`HEALTHCHECK_URL`** (optional, `.env`): every run pings it (`/fail` if an account failed),
  so a dead server pages you. Nothing on the box can report its own death.
- **Lever gate: a 95% upper bound on the mean open-sell cost**, in the `[lever]` log line and
  `make review` §2b. Reporting only: the pre-registered gate (mean <= 10bp over 50 exits) is
  unchanged. Opening it early on a sequential test after seeing a good mean would be loosening a
  rule after the fact.
- **`make review` §6: night cost by price bucket** (the addendum 21 `night_price_min: 3.0`
  check) and **§7: intraday fill hygiene** per day (flat by the close, no fills after 15:58),
  the evidence `conviction_mode: auto` waits on.

## 26a — regime-conditional budget between legs: dead (2026-09-24)

Question (hostile review): the intraday leg is the crash hedge (+114bp on SPY −3% days)
and the night leg the crash risk (−42bp). On high-risk days, move budget from the
overnight legs to the intraday leg? Not portfolio vol targeting (dead, add. 9): total
risk is moved, not scaled. Script: `research/sim/regime_tilt.py`.

**Mechanics that constrain it.** V7's intraday cap is margin-bound: (1 − 0.5·IBS − 0.75·conv)/0.5
= 0.75, and on regime days the vol-target leverage (median 1.06) still exceeds it. The
night leg is bought at the close and sold at the open, so cutting it frees **no** daytime
margin. Only IBS (held through the day) and the conviction trade free room for the
intraday leg.

**Pre-registered** (nothing searched; all reported). Flag R = SPY 20d realised vol above its
trailing 252d 80th percentile, closes through d−1 (17% / 19% / 24% of days in 2016–20 /
2021–23 / 2024–26). Flag D = SPY d−1 ≤ −2%. IBS bought at the d+1 open uses closes through d.
Placebo = T3's action on random 20-session blocks, same day count, 20 seeds.

CAGR / Sharpe / maxDD, time-weighted; 2021–26 is the dollar replay ($3k + $1k/21, whole shares);
2016–20 is the holdout returns book (night half in bills before 2020, bias-corrected rebuild in 2020).

| | 2021–23 | 2024–26 | 2021–26 tier | tier_hi | 2016–20 holdout | NW t of daily diff 21–26 / ho |
|---|---|---|---|---|---|---|
| V7 shipped (cap 0.75) | 48.6/2.23/−10 | 46.4/1.80/−13 | 47.5/1.99/−13 | 39.6/1.73/−14 | 15.5/1.05/−21 | |
| T1 R: night ×0.5 (cut-only control) | 47.6/2.21/−10 | 42.6/1.80/−11 | 45.2/2.00/−11 | 38.3/1.75/−12 | 15.5/1.08/−17 | −1.29 / −0.12 |
| T2 R: IBS → bills, cap 1.25 | 48.5/2.22/−10 | 38.9/1.61/−14 | 43.8/1.89/−14 | 35.9/1.62/−15 | 15.2/1.03/−19 | −1.57 / −0.14 |
| T3 R: night ×0.5 + IBS → bills (the transfer) | 47.8/2.22/−10 | 34.8/1.57/−12 | 41.4/1.89/−12 | 34.6/1.63/−13 | 15.2/1.06/−19 | −2.07 / −0.16 |
| T4 R: T3 + conviction off, cap 2.0 | 39.0/2.08/−10 | 35.7/1.66/−12 | 37.4/1.86/−12 | 30.9/1.59/−13 | 15.9/1.24/−10 | −2.65 / −0.00 |
| T5 D: T3 on SPY d−1 ≤ −2% | 44.2/2.13/−10 | 44.2/1.77/−13 | 44.2/1.93/−13 | 36.6/1.66/−14 | 13.4/0.93/−18 | −1.93 / −1.04 |

Placebo, Sharpe change vs V7: T3 −0.01 / −0.23 / +0.02 (2021–23 / 2024–26 / holdout) vs
placebo mean −0.04 / −0.08 / −0.02; T3 beats 11/20, 3/20, 15/20. Indistinguishable from
random, and worse than random in 2024–26.

Episodes (%): COVID crash V7 −12.9, T1 −10.7, T3 −10.8, **T4 −2.4**; COVID rebound V7 +13.3,
T3 +3.0, T4 +5.1; 2022 bear V7 +39.3, T3 +41.1, T4 +21.7; Aug 2024 V7 −2.7, T3 −0.3;
Apr 2025 V7 +12.8, T3 +7.7.

**Why it fails.** The premise holds on crash *days* but not in a high-vol *regime*. On R days
(2021–26) every leg earns more, not less: night +6.6bp/day of equity (sd 100) vs +4.9 (sd 77)
otherwise, IBS +3.5 vs +3.1, intraday +11.4 vs +6.4. Per unit of risk the night and IBS legs
are about as good on R days as on other days, so taking them off gives up edge. The −42bp
night average is concentrated in a few gap days that a lagged vol flag does not isolate
(the same lesson as add. 18's rejected vol > 30% halving: it gives back the rebound).
Moving IBS to bills to free margin doesn't help either: the intraday leg's extra leverage
earns less than the IBS trades it replaces (T2).

**Verdict: dead.** No variant raises Sharpe in both halves. T3 (the actual hypothesis) costs
6pp/yr and −0.23 Sharpe in 2024–26 (t −2.07). The one tempting row, T4 (holdout Sharpe +0.19,
maxDD −21 → −10, COVID −2%), gives up 10pp/yr and Sharpe in both 2021–26 halves: it is a
drawdown-for-return trade, not a Sharpe gain. T1 is neutral (Sharpe +0.00/+0.01, maxDD −2pp,
−2.3pp/yr) and adds nothing over the weekend/dedupe guards already live. Do not retest
cross-leg tilts on lagged realised-vol or prior-day-drop flags.

## 26b — a cross-asset trend sleeve as a diversifier: dead as a Sharpe lever (2026-09-24)

`research/sim/trend_sleeve.py` (36 s). Question from the hostile review: the book is all US
equity, short-horizon. Does a genuinely different stream, time-series momentum across asset
classes, raise its Sharpe?

**Setup (pre-registered).** Universe fixed before looking: every non-sector, non-leveraged,
non-VIX ETF in `etf_daily.parquet`: SPY QQQ IWM EFA EEM TLT IEF GLD SLV USO HYG (total-return
prices; no UUP/DBC in the cache). Signals at close t, traded at the close of t+1, monthly.
A = 12-1 sign, long-only 1/N; B = 3/6/12 sign blend, long-only; C = B inverse-vol at 10%
ex-ante vol, gross ≤ 1; D = C long/short (brokerage only; 0.5%/yr borrow). Costs 2bp (tier)
and 5bp (tier_hi) per side on turnover. Idle sleeve cash earns BIL. Placebo: scores shuffled
across assets at each rebalance, 200 seeds.

**Standalone** (CAGR / Sharpe / maxDD, tier; tier_hi within 0.02 Sharpe, turnover 1–6x/yr):

| | 2017-20 holdout | 2021-23 | 2024-26 | full | placebo beats (3 periods) |
|---|---|---|---|---|---|
| A 12-1 long-only | 4.0 / 0.45 / −21 | 2.0 / 0.31 / −8 | 18.7 / 1.58 / −9 | 7.3 / 0.78 / −21 | – |
| **B 3/6/12 long-only** | 5.6 / 0.86 / −10 | 2.4 / 0.44 / −6 | 14.6 / 1.56 / −6 | **7.0 / 0.99 / −10** | 94% / **38%** / **10%** |
| C vol-scaled | 7.0 / 0.86 / −13 | 1.2 / 0.17 / −15 | 12.2 / 1.43 / −7 | 6.6 / 0.77 / −15 | 74% / 49% / 20% |
| D long/short | 4.7 / 0.73 / −9 | −0.3 / 0.00 / −18 | 8.6 / 1.20 / −5 | 4.2 / 0.60 / −18 | 90% / 40% / 5% |
| C weekly (robustness) | 6.9 / 0.93 / −14 | 1.7 / 0.23 / −17 | 13.0 / 1.57 / −7 | 6.9 / 0.85 / −17 | |
| equal-weight buy & hold, 11 ETFs | 10.2 / 0.83 / −26 | 3.3 / 0.33 / −20 | 21.8 / 1.71 / −11 | 11.1 / 0.91 / −26 | |

The timing adds nothing in the two periods that judge the book: shuffled scores (same
exposure, wrong assets) match or beat the real signal in 2021-23 and 2024-26. The 2024-26
Sharpe is beta (gold, equities and credit all rose); equal-weight buy-and-hold does as well.
Only the 2017-20 holdout (COVID) shows trend timing, the classic crisis-alpha case. With 11
ETFs, 5 of them equity, there is too little breadth: TSMOM's published Sharpe comes from 50+
futures markets.

**Against V7 (2021-02 → 2026-09, tier).** Correlation +0.18 (B), +0.08 (D). It is **not a crash
hedge**: on the 11 SPY ≤ −3% days correlation rises to +0.3 and the sleeve loses 15–31bp
while V7 makes +166bp (the intraday leg). Monthly trend is too slow for one-day crashes. The
ceiling at that correlation, max Sharpe = √((S₁² + S₂² − 2ρS₁S₂)/(1 − ρ²)) with S₁ = 1.99 and
S₂ = 1.03, is **2.11: +0.12 at the very best**. √(S₁² + S₂²) at zero correlation is 2.24.

**Combined** (2021-23 / 2024-26 | full, CAGR / Sharpe / maxDD):

| | tier | tier_hi |
|---|---|---|
| V7 shipped | 48.6/2.23/−10 · 46.4/1.80/−13 · **47.5/1.99/−13** | **39.6/1.73/−14** |
| B in the IBS half's idle SGOV cash, up to 0.25 (free capacity) | 47.2 / 1.97 / −13 | 38.6 / 1.68 |
| B in idle cash, up to 0.50 | 46.8 / 1.94 / −13 | 37.6 / 1.63 |
| carve 0.2 of ibs+night → B (overnight 1.0x) | 43.7/2.24/−9 · 42.0/1.88/−11 · **42.9/2.05/−11** | 36.8 / 1.81 / −11 |
| carve 0.3 → B | 39.6 / 2.03 / −9 | 34.9 / 1.83 / −11 |
| carve 0.5 → B | 34.5 / 2.02 / −9 | 31.2 / 1.86 / −10 |
| V7 at 1.3x overnight (the budget in ibs+night) | 53.4 / 1.93 / −16 | 43.3 / 1.64 / −17 |
| V7 + 0.15 B on margin (the budget in the sleeve) | 45.3 / 1.96 / −13 | 37.6 / 1.69 / −14 |
| edge-halves, tier_hi: V7 / carve 0.3 → B | 17.5 / 0.89 / −20 vs 16.3 / 0.97 / −17 | |

- **Idle cash: worse** in every variant, cost and half. Same verdict as addendum 16's idle IBS
  half: SGOV stays.
- **Carve-out:** Sharpe +0.04 to +0.08 (tier_hi +0.08 to +0.13), positive in both halves for B,
  maxDD −13 → −9/−11. It costs 4.6pp/yr (0.2) to 8pp/yr (0.3). That is a de-risking dial, not
  an edge: the sleeve earns about BIL + beta, and the gain matches what any low-vol,
  low-correlation holding would give. C and D do no better than B.
- **Overlay:** at the same 1.3x budget the sleeve earns 8pp/yr less than levering ibs+night,
  for +0.03 Sharpe.

**Verdict: dead as a Sharpe or return lever.** Placebo fails in both judged halves, the
correlation ceiling is +0.12, and the realized best is +0.06 at −4.6pp/yr. Keep in mind: a
B carve of 0.2–0.3 is an honest drawdown dial (edge-halves maxDD −20 → −17) if the book ever
needs to be de-risked for a reason other than Sharpe; it beats simply cutting leverage only
marginally. Conditional: re-test only with real breadth (micro futures across rates, FX,
metals, energy, ags, 20+ markets), which needs the ~$30k futures account from addendum 25.
Nothing changed in live code or config.


# Addendum 27 — pattern hunt: one small survivor (oversold overnight, SHADOW), three dead (2026-09-25)

A broad scan of daily-bar patterns (calendar, day-of-week, Friday dips, chase, 52w highs, fear
spikes, breadth, flight-to-quality, multi-day oversold) found one lead; four deep tests followed.
The scan itself: Friday dips held over the weekend are the WORST down days to buy (SPY Friday
<= -1%: -22 / -10 / -18bp to Monday open, vs Mon-Thu down days +4 / +6 / +7); turn of month dead
(2021-23 negative); after an up day the next day is ~0; buying a +1.5% day loses (SPY -53bp
2016-20); strong Mondays are 2024-26 only; pre-holiday +14..+31bp 2021-26 but ~9 days/yr, never
significant (watch only). Scripts were scratch; the deep tests below are in `research/sim/`.

| | idea | verdict |
|---|---|---|
| R1 | multi-day oversold SPY/QQQ in the idle IBS half | V1-V5 dead; **V6 (15:40 signal, close -> next open) +2.4pp/yr, Sharpe 1.99 -> 2.04, post-hoc: built SHADOW** |
| R2 | 2/3/5-day losers in the idle night capacity | dead (continuation, not overshoot) |
| R3 | last-half-hour momentum (Gao et al. 2018) | dead (sign flips; noise leg already holds trend days into the close) |
| R4 | sector-loser reversal, pairs, international overnight | dead as additions (the sector bounce is the IBS bet again) |

**Built:** `daily.oversold_mode: shadow` (config.yaml). At 15:40 each book scores last night's shadow
entries against the official open, then logs `[oversold] SHADOW: would buy SPY $X at the close (3 down
closes / RSI(2) n)`. No order path. `make daily-status` shows `oversold SPY/QQQ (shadow) nights n  win  avg`.
The live trigger (`signals.oversold_trigger`) matches the research formula on 100% of 2017-26 days.
Decide after ~3-6 months of shadow nights (it fires on ~11% of days, so ~15-30 nights).

## multi-day oversold trigger for the idle IBS half (2026-09-25)

`research/sim/oversold.py` (~70 s). Lead from the pattern scan: after 3 down closes in a row or
RSI(2) < 10, SPY/QQQ earn +30..60bp close-to-close the next day in 2021-26, also on days the
IBS leg is not in. The IBS leg's half sits in T-bills on **67%** of 2021-26 sessions (it
deploys fully on days it has a pick, not at all otherwise). Put that idle money into the trigger?

**Setup.** Only idle IBS money (ibs_w × equity minus what the IBS picks use), equal over triggered
names the IBS leg does not hold, whole shares; it replaces T-bills, so overnight gross stays
≤ 1.0x (measured max 1.00-1.01x) and daytime margin is unchanged. Baseline V7 as shipped
(47.5 / 1.99 / −13). Costs 1bp/side (tier), 3bp/side (tier_hi). Placebo: same entry count per
symbol on random dates, 50 seeds. Holdout 2016-02 → 2020-12 via addendum 26a's returns book.

**Pre-registered V1-V5 (IBS timing: signal at d's close, buy d+1 open, sell d+2 open): dead.**

| standalone, bp per position-day (NW t, n) | 2016-20 | 2021-23 | 2024-26 |
|---|---|---|---|
| V1 SPY+QQQ 3-down | −12.1 (−0.9, 125) | +31.0 (+1.9) | +27.3 (+1.4) |
| V2 SPY+QQQ RSI2<10 | −7.6 | +6.9 | +40.8 (+2.1) |
| V3 SPY+QQQ either | −8.1 | +20.3 | +31.0 |
| V4 either, hold ≤ 5 | −7.3 | +21.3 | +30.4 |
| V5 IBS top-3 momentum, either | +8.4 | +15.7 | +47.6 (+2.4) |

In the book: Sharpe change vs V7 (2021-23 / 2024-26 / holdout) V1 +0.01/−0.01/−0.08, V2 −0.14/+0.06/−0.07,
V3 −0.02/+0.02/−0.03, V4 −0.01/+0.02/−0.03, V5 −0.04/+0.14/+0.07. None positive in both halves; fit
2021-23 picks V1 (judges −0.01 / holdout −0.08), fit 2024-26 picks V5 (judges −0.04). All negative
in 2016-20 except V5. Placebo: V1-V4 beat ≤ 40/50 somewhere and fail the holdout (5-20/50).

**Why: the edge is overnight, and next-open entry misses it.** Splitting the trigger's next-day return
(either, bp): close→open SPY +10 / +9 / +30, QQQ +16 / +13 / +38 (2024-26 t ≈ 3.4); the open→open
hold the IBS timing buys is −13 / +18 / +36 (SPY), negative in 2016-20.

**V6, added AFTER V1-V5 (post-hoc; judge on placebo and holdout).** SPY+QQQ, either trigger evaluated at
**15:40 with the 15:40 price** (minute data; agrees with the close signal on 97.9% of symbol-days),
bought at the close auction, sold at the next open (the night leg's timing), idle IBS money only.

| per night, net of 1bp/side (t, n) | 2016-20 | 2021-23 | 2024-26 |
|---|---|---|---|
| SPY triggered | +6.8 (0.8, 101) | +7.9 (1.0, 102) | +25.6 (2.8, 80) |
| QQQ triggered | +16.6 (1.4, 82) | +10.2 (1.1, 102) | +34.1 (3.1, 76) |
| SPY / QQQ every night (control) | +2.4 / +4.1 | −1.0 / −1.8 | +4.0 / +6.5 |

Standalone leg (overnight when triggered, T-bills otherwise): 3.2 / 0.71 / −8 (2016-20), 6.5 / 1.14 / −5,
15.1 / 2.58 / −7.

| book | 2021-23 | 2024-26 | 2021-26 tier | tier_hi | edge-halves tier_hi | 2016-20 ho |
|---|---|---|---|---|---|---|
| V7 shipped | 48.6/2.23/−10 | 46.4/1.80/−13 | 47.5/1.99/−13 | 39.6/1.73/−14 | 17.5/0.89/−20 | 15.5/1.05/−21 |
| **V7 + V6** | 49.3/2.23/−9 | 50.6/1.89/−13 | **49.9/2.04/−13** | **41.4/1.76/−14** | 18.2/0.91/−19 | 16.5/1.09/−22 |

- Sharpe change 2021-23 / 2024-26 / holdout: **−0.00 / +0.09 / +0.04**; NW t of the daily difference
  +1.91 (2021-26), +1.08 (holdout). Placebo beats **45/50, 48/50, 34/50**.
- Deployed on 8% of sessions at ~0.49 of equity; adds **+1.8pp/yr** simple (tier_hi +1.4pp); CAGR +2.4pp.
- Calendar years V7 → V7+V6: 2021 51→52, 2022 69→72, 2023 24→23, 2024 31→36, 2025 62→63, 2026 32→37%.
- Episodes: 2018 Q4 +24.3 → +24.0, COVID crash −12.9 → −14.1, 2022 bear +39.3 → +41.4, Aug 2024 −2.7 → −2.2,
  Apr 2025 +12.8 → +10.6. It buys index weakness, so it adds a little to crash-day losses.
- Margin: overnight gross ≤ 1.01x (the money was in T-bills); no daytime use.

**Verdict: V1-V5 dead. V6 borderline-positive, a small free return add, not a Sharpe lever.** Conditional
nights beat every-night by +4..+13bp (2016-20), +9..+12 (2021-23), +22..+28 (2024-26), and the placebo
passes in both judged halves, but 2021-23 is Sharpe-flat (t ≈ 1 per night) and the variant is post-hoc.
Worth ~+1.5-2pp/yr on idle money at no extra leverage. If built: shadow first (log the 15:40 decision,
no orders), reuse the night leg's close-auction path (SPY/QQQ MOC, sell at the open auction). Live notes:
QQQ held overnight is sold at 09:30, before the intraday leg's first decision (10:01), so no conflict;
a Roth copy would need the wash-sale guard vs the brokerage book.

Series (tier): scratchpad/r1_series.pkl {"v7", "v7_plus" (V7+V6), "leg_unit" (V6 standalone from 2016-02)}.

## multi-day losers for the night leg's idle capacity: dead (2026-09-24)

`research/sim/multiday_night.py` (~12 min, 300 placebo replays). NEXT.md's one untested structural
fix for the night leg's ~half utilisation was "multiple formation horizons". Addendum 20 killed
the plain −6..−8% single-day band. Question: does a big MULTI-DAY drop rescue those names?

**Pre-registered** (nothing searched, all reported): a name that is NOT down 8% today, but whose
p50 (15:50) vs the close n days ago is
M2: 2-day ≤ −12% · M3: 3-day ≤ −15% · M5: 5-day ≤ −20%.
Same live filters (IBS < 0.1 at 15:50, vol20 ≥ 60%, ADV ≥ $10M, price ≥ $5), 0.7 dedupe against the
regular names, 10% each, spare capacity only (never crowds out ≤ −8% picks), deepest multi-day drop
first, buy the close / sell the open, weekend half size, V7 otherwise. Pool = the honest 15:50
reconstruction used by addendum 20 (`depth.candidates`, 2021-02 on); no 2020 rebuild exists for
the −6..−8% band, so no holdout. Placebo = the same count per night drawn at random from the
same −6..−8% pool, 50 seeds. Rule: adopt only if both halves beat V7 at tier and tier_hi AND beat
the placebo.

**Screen (daily bars, close-based: biased, gate only), close → next open, gross:**

| pool | 2021–23 | 2024–26 |
|---|---|---|
| regular (day ≤ −8%) | +10.3bp (10.0/day) | +50.7bp (14.5/day) |
| any name near its low, day > −8% | +2.9 | +21.3 |
| M2 | −8.9 | +27.0 |
| M3 | −16.9 | +19.4 |
| M5 | −11.6 | +36.9 |

Already failing the gate: every multi-day pool is negative in 2021–23 and no better than a random
near-its-low name in 2024–26. A multi-day drop is momentum, not overreaction.

**Honest book test** (15:50 data; CAGR/Sharpe/maxDD; V7 here is the depth pipeline's V7, 49.8/1.98,
as in addendum 20):

| | 2021–23 | 2024–26 | full | tier_hi full | per trade net, 21–23 / 24–26 (tier) | placebo beats (Sharpe, 21–23/24–26/full) |
|---|---|---|---|---|---|---|
| V7 | 51.3/2.21/−10 | 48.2/1.79/−14 | 49.8/1.98/−14 | 42.3/1.75 | — | — |
| M2 | 49.6/2.14/−10 | 48.6/1.78/−13 | 49.1/1.94/−13 | 41.2/1.70 | −35.0bp / +11.0bp | 26% / 82% / 66% |
| M3 | 50.9/2.20/−10 | 45.1/1.68/−13 | 48.1/1.92/−13 | 40.4/1.67 | −3.2 / −73.7 | 34% / 0% / 0% |
| M5 | 50.8/2.19/−10 | 44.5/1.67/−14 | 47.7/1.90/−14 | 40.2/1.66 | −13.0 / −108.3 | 24% / 4% / 10% |

- Utilisation barely moves: 46% → 48% (+0.2–0.3 names/night). After the IBS and vol filters and
  the dedupe, few nights have a multi-day loser at 15:50.
- Edge-halves at tier_hi: V7 18.6/0.90/−21; M2 18.1/0.87, M3 17.7/0.86, M5 17.6/0.86.
- Episodes (2022 bear, Aug 2024, Apr 2025): within ±0.7pp of V7, so no crash cost and no benefit.

**Verdict: dead.** No variant beats V7 in either half at either cost. M3/M5 do worse than random
−6..−8% names in 2024–26. M2 beats the placebo in 2024–26 only, after losing 35bp/trade in 2021–23,
the half-flipping pattern the bar exists to reject. The screen already shows why: a slide over
several days, without a capitulation day, is continuation, not overshoot. The night edge lives in
the single-day ≤ −8% capitulation. Do not retest multi-day horizons on the night leg; the idle
half stays in cash/T-bills.

## end-of-day intraday momentum (Gao et al. 2018): dead (2026-09-25)

`research/sim/late_momentum.py` (9 s). Claim: the first half-hour (prev close → 10:00) and the
15:00–15:30 return predict the last half-hour; leveraged-ETF rebalancing and hedging push into
the close in the direction of the day. Bot timing: signal from the 15:30 bar, entry at 15:31
(+1 min delay test), exit at the 15:57 flatten or the close auction (MOC sent with the entry).
Costs 0.5bp/side (the repo's intraday tier) and 2bp stressed. Placebo: random side on the same
days, 100 seeds. SPY / QQQ / SMH minute bars, 2016-01 → 2026-09.

**Pre-registered** (all reported): V1 sign(prev close → 10:00); V2 sign(open → 15:30);
V3 sign(15:00 → 15:30); V4 sign(prev close → 15:30) when |move| > 1σ (20d, known at d−1);
V5 same when > 2σ (the LETF-rebalancing version).

**Standalone, MOC exit, tier cost: per trade bp (t) / placebo beats** — 2016-20 | 2021-23 | 2024-26

| | SPY | QQQ | SMH |
|---|---|---|---|
| V1 first half-hour | −1.4 (−1.6) 38% · −1.8 (−1.8) 26% · −0.9 62% | +1.0 96% · **−3.2 (−2.9) 2%** · −0.3 | +1.6 100% · **−3.5 (−2.4) 1%** · −1.3 |
| V2 open → 15:30 | −1.2 · +0.5 · **−2.2 (−2.7)** | −0.5 · +0.4 · −1.9 (−2.0) | +1.5 · +0.4 · −3.1 |
| V3 15:00 → 15:30 | −0.9 · +1.8 (1.9) 100% · −0.3 | −0.5 · +0.7 · −1.2 | −0.7 · +1.7 · −2.1 |
| V4 > 1σ | 0.0 · −1.3 · 0.0 | +4.1 (1.4) · −0.1 · −2.0 | +7.8 (2.7) · −0.3 · −3.6 |
| V5 > 2σ (n ≈ 40–85/period) | +2.6 · −9.6 (−2.2) · +9.6 | +13.6 (1.8) · **−14.8 (−3.2)** · +6.6 | +11.4 · −7.2 · +16.7 (2.2) |

At 2bp/side every variant is negative in every period on every ETF. The 15:57 exit is worse
than MOC nearly everywhere (the last three minutes carry part of the move). The +1 min delay
changes little: there is no edge to lose.

**Fit/judge (QQQ, Sharpe):** best on 2016-20 = V5 → 2021-23 −1.72, 2024-26 +0.75. Best on
2021-23 = V3 → 2016-20 −0.20, 2024-26 −0.74. Nothing survives out of sample.

**Overlap with the live noise leg** (QQQ position held from the 15:30 decision). Late-leg
trades on days the noise leg is flat (the only incremental ones; "same" is just more leverage
on a position already held): V1 +0.1 / −2.8 (t −2.1) / −0.3bp; V3 +0.3 / +1.1 / −1.7;
V4 +9.3 / +5.3 / −5.3 (n 55–87); V5 n = 4–8 per period. V2 and V4 are never opposite the noise
leg: once the day has trended, the noise leg is already in that direction, which is why the
remaining late-day drift is priced.

**Book: V7 + late leg on QQQ in the free daytime margin at 15:30** (cap 0.75 minus noise gross):

| | 2021-23 | 2024-26 | full tier | tier_hi | edge-halves tier_hi |
|---|---|---|---|---|---|
| V7 shipped | 48.6/2.23/−10 | 46.4/1.80/−13 | 47.5/1.99/−13 | 39.6/1.73/−14 | 17.5/0.89/−20 |
| + V5 (fit winner) | 48.4/2.23/−10 | 46.2/1.79/−13 | 47.3/1.99/−13 | 39.3/1.72/−14 | 17.4/0.88/−20 |
| + V4 | 49.6/2.26/−9 | 44.6/1.74/−13 | 47.1/1.98/−13 | 38.4/1.68/−14 | 17.0/0.87/−21 |
| + V1 (Gao's headline) | 42.4/1.95/−13 | 45.6/1.77/−13 | 43.9/1.85/−13 | 31.0/1.40/−15 | 13.8/0.72/−21 |

Free margin on trade days averages 0.14x (V5) to 0.53x (V1): capacity exists; the edge does not.

**Verdict: dead.** The published effect (SPY 1993–2013) is gone or reversed in 2016–26: no
variant is positive in all three periods on any ETF, the fit winner flips sign out of sample
(QQQ V5 2021-23 t −3.2, placebo 0%), and every combination leaves V7's Sharpe flat or lower.
Consistent with the known post-publication decay and with the live noise leg already holding
the day's direction into the close on trend days. Do not retest last-half-hour momentum on
index ETFs; the live noise leg is the version of this idea that still works.

## ETF cross-sectional reversal, pairs, international overnight: nothing adds (2026-09-25)

`research/sim/etf_xsec.py` (20 s). Patterns the IBS leg does not trade, pre-registered, all reported.
Signal on d's bar, bought at the d+1 open (IBS timing). Costs/side: tier 1bp (2bp international),
tier_hi 3bp (5bp). Placebo: same number of names drawn at random from the same universe, 100 seeds.

**Standalone** (CAGR / Sharpe / maxDD, t; leg fully invested when active):

| | 2016-20 holdout | 2021-23 | 2024-26 | placebo beats (3 periods) |
|---|---|---|---|---|
| X1 2 worst 1-day sector ETFs (of 11), hold 1 | 21.2/0.92/−38 t2.1 | 17.5/0.77/−35 t1.3 | 32.1/1.37/−25 t2.2 | **99% / 95% / 97%** |
| X1 tier_hi | 12.0/0.59 | 8.7/0.46 | 21.8/1.00 | |
| X2 2 worst 5-day, hold 5 | 17.0/0.81 | 5.6/0.35 | 32.4/1.46 | 91% / **15%** / 100% |
| X3 pairs laggard (QQQ/SPY, SMH/QQQ, XLK/SPY, z ≤ −2), hold 3 | 4.4/0.52/−12 | 10.2/0.97/−14 | 5.5/0.63/−13 | 97% / 59% / 85% |
| X4 EFA/EEM/FXI/KWEB close→open, net tier | 2.0/0.20 | **−19.4/−0.90** | 1.3/0.16 | — |
| *equal-weight sectors / SPY, open→open* | 14.8/0.84 · 14.8/0.89 | 10.7/0.66 · 10.2/0.64 | 20.8/1.37 · 21.3/1.29 | |

X1 grid (k 1-3, hold 1-5): positive everywhere, holdout Sharpe 0.63-0.96; not picked from.

- **X1 is a real effect:** sector-ETF 1-day losers beat random sector picks by ~4-6bp/day in all three
  periods. **X2** fails placebo in 2021-23. **X3** is weak (placebo 59% in 2021-23, t < 2 everywhere).
- **X4 is dead:** international ETFs' overnight returns are not a premium net of two auction trips
  (EFA/EEM/FXI net tier −16 to −29%/yr in 2021-23); KWEB's +36%/yr overnight in 2016-20 is the only
  cell with t > 2 and it vanished after. SPY/QQQ overnight beat the international ones.

**Why X1 adds nothing to the book: its edge is on the IBS leg's days.** Split by whether the IBS
leg holds a position (next-day bp, tier):

| | 2017-20 | 2021-23 | 2024-26 |
|---|---|---|---|
| X1 on IBS-flat days (the free capacity) | +6.0 (t1.0) | **+0.5 (t0.1)**; tier_hi −2.6 | +9.7 (t1.6) |
| X1 on IBS-active days | +11.2 | +21.7 | +16.9 |
| BIL it would replace | 0.4 | 0.8 | 1.7 |

It is the same market-wide oversold bounce IBS already harvests, seen through sectors. On the days
the IBS half sits in SGOV there is little left.

**Against V7 (2021-02 → 2026-09).** ρ with V7 +0.10 to +0.15; not a crash hedge (X1 +36bp vs V7
+166bp on SPY ≤ −3% days).

| full 2021-26, CAGR / Sharpe (2021-23 · 2024-26) | tier | tier_hi | edge-halves tier_hi |
|---|---|---|---|
| V7 shipped | **47.5 / 1.99** (48.6/2.23 · 46.4/1.80) | 39.6 / 1.73 | 17.5 / 0.89 |
| + X1 in idle IBS cash (free capacity) | 49.7 / 1.97 (44.5/1.94 · 55.6/2.01) | 36.3 / 1.54 | 16.0 / 0.79 |
| + X2 in idle IBS cash | 44.8 / 1.79 | 34.7 / 1.46 | 15.3 / 0.76 |
| + X3 in idle IBS cash | 46.2 / 1.94 | 36.5 / 1.60 | 16.2 / 0.83 |
| + X4 in idle IBS cash | 40.2 / 1.58 | 26.1 / 1.12 | 11.4 / 0.58 |
| V7 at 1.3x overnight (levering ibs+night) | 53.4 / 1.93 | 43.3 / 1.64 | 18.6 / 0.84 |
| V7 + 0.3 X1 on IBS-active days, on margin (same budget) | 52.3 / 1.98 (54.3/2.20 · 50.2/1.78) | 43.1 / 1.70 | 18.7 / 0.87 |

- In free capacity every variant **lowers** Sharpe; X1 loses a half (2021-23 −4pp) and all of
  tier_hi. SGOV stays (same verdict as add. 16/26b).
- As a use of the 1.3x leverage budget, X1 on IBS-active days ≈ levering ibs+night: same return,
  Sharpe +0.05 (tier) / +0.06 (tier_hi), better 2021-23, worse 2024-26. It is a different wrapper on
  the IBS bet, not a new edge. Borderline; would only matter once the lever gate opens, and a
  second executor path is not worth +0.05 Sharpe.

**Verdict: dead as additions.** X1 is a genuine cross-sectional reversal but redundant with IBS;
X2/X3 fail placebo or significance; X4 has no net overnight premium. Series (X1 overlay, borderline)
in scratchpad/r4_series.pkl. No live code or config changed.



# Addendum 28 — theme-explosion sleeve ("catch the next quantum"): dead (2026-09-25)

`research/sim/theme_explosion.py`. Goal: catch explosive new-theme runs (quantum 2024-25,
AI, nuclear, crypto) without naming tickers. Survivorship-aware panel: 14,697 symbols,
1,958 delisted (delisting returns counted), ~800-2,450 liquid names/day. Next-open entry,
10 slots, trail 25% / below 50d MA / 126d max hold, idle cash in BIL. Four pre-registered rules:
V1 52-week-high breakout on 3x volume; V2 top 1% 63-day return above the 50d MA; V3 "theme
cluster" (>= 3 correlated names breaking out together); V4 residual momentum vs SPY.

| standalone, CAGR / Sharpe / maxDD (tier) | 2016-20 | 2021-23 | 2024-26 | beats vol-matched random picks |
|---|---|---|---|---|
| V1 breakout | 5.0 / 0.34 / −44 | −7.3 / −0.01 / −65 | 4.6 / 0.30 / −51 | 22% / 48% / 44% |
| V2 top-1% momentum | 13.9 / 0.56 / −61 | −24.8 / −0.35 / −81 | −2.6 / 0.20 / −57 | 88% / 16% / 36% |
| V3 theme cluster | 0.7 / 0.12 / −41 | −7.9 / −0.32 / −37 | 5.6 / 0.34 / −28 | 10% / 16% / 40% |
| V4 residual momentum | 1.0 / 0.19 / −68 | −31.5 / −0.52 / −86 | −21.6 / −0.18 / −66 | 28% / 4% / 2% |
| SPY | 15.2 / 0.87 / −34 | 10.0 / 0.63 / −24 | 21.1 / 1.31 / −19 | |

- **No rule beats random stocks of the same volatility** in the judged periods: the "explosion"
  selection adds nothing over just owning volatile names, and SPY beats every rule in every
  period. Win rates 25-45%; the top 5 trades are 100-2,400% of P&L (GME, AMC, PTON, ASTS...):
  the lottery-stock (MAX-effect) result, not a theme edge.
- **Quantum was caught, badly.** V1 entered RGTI on 2024-12-30 (after a 0.69 → ~15 run) and was
  stopped −37%; QUBT −34%, QBTS −18%. V2/V4 caught IONQ +95% and QUBT +93/+132%, but those rules lose
  −25..−32%/yr in 2021-23 on the meme/SPAC busts. By the time a rule can see an explosion, most of
  the move is done and the reversal risk is at its peak.
- **Exits:** a 50% trail looks good in 2024-26 (V1 36%/yr) and loses in 2021-23: regime, not edge.
- **Against V7:** correlation −0.09, but the sleeve loses 276bp on SPY <= −3% days (V7 +166).
  Carving 0.1 / 0.2 of ibs+night into V1: 47.5/1.99 → 42.7/1.95 → 38.2/1.86; edge-halves 17.5 →
  16.2 → 14.9%. (The run's "sleeve in idle IBS cash" rows, 54-61%/yr, are a combination bug: the
  sleeve's mean day is −3.6bp, and V7 + 0.1 x sleeve done directly is 46.2 / 1.96.)

**Verdict: dead.** Momentum on explosive, high-attention stocks is volatility exposure with a
lottery tail, and after costs and delistings it trails SPY. The bot already harvests these names'
volatility the profitable way: the night leg buys their one-day crashes (RGTI/IONQ/QBTS/QUBT all pass
its filters). A long-term thematic bet is a personal allocation (a small position held by hand; the
bot never trades a symbol the account holds), not a rule.


# Addendum 29 — live costs are ~0bp: what changes (2026-09-28)

`research/sim/cost_resweep.py` (~4 min). After 26 live night round trips (Schwab, $1k cap):
buys **−0.5bp**, open sells **−1.0bp/side** vs the official auction prints (95% upper bound
+11.7bp). The research tiers assumed 5-15bp (tier) and 7.5-25bp (tier_hi). The night edge is
~20bp/trade gross, so costs were eating 25-75% of it. Re-tested at flat 0 and 3bp (3bp = the
conservative stand-in for "measured"); tier_hi stays the planning floor.

**A. The book, and the lever gate** (2021-23 / 2024-26 / full, CAGR / Sharpe / maxDD):

| | 3bp | tier | tier_hi |
|---|---|---|---|
| V7 1.0x | 56.9/2.52 · 59.2/2.17 · **58.0/2.33/−12** | 47.5/1.99/−13 | 39.6/1.73/−14 |
| V7 1.3x | 62.5/2.49 · 74.8/2.22 · **68.3/2.32/−15** | 53.4/1.93/−16 | 43.3/1.64/−17 |

At measured costs 1.3x adds +10pp/yr at the same Sharpe in both halves (at tier_hi it costs
Sharpe). The gate opens itself at 50 exits <= 10bp; this says it is a good trade when it does.

**B/C. Rejected ideas re-checked:** shallower night depth (−7%/−6%) is even at 0bp and worse at
3bp: addendum 20's rejection was the signal, not cost. vol20 >= 0.40-0.50 instead of 0.60:
+1pp / +0.02 Sharpe at 0-3bp, worse at tier and tier_hi: too small; revisit at 50+ exits.

**D. Sizing at measured costs** (history | edge-halves | 5y MC $3k + $1k/month under EH):

| profile | 3bp history | 3bp EH | median | P(DD>30%) / >50% | tier_hi EH, P(DD>30%) |
|---|---|---|---|---|---|
| V7 1.0x, cap 0.10 | 58.0 / 2.33 / −12 | 25.1 / 1.19 / −18 | $120k | 11% / 0% | 17.5, 23% |
| V7 1.3x (gate) | 68.3 / 2.32 / −15 | 28.6 / 1.18 / −17 | $132k | 21% / 0% | 18.6, 39% |
| **1.3x, cap 0.15** | **85.5 / 2.42 / −18** | **34.3 / 1.23 / −22** | **$153k** | 32% / 1% | 21.4, 56% |
| aggressive (1.3x, cap 0.20, intraday 0.6) | 93.7 / 2.39 / −20 | 36.7 / 1.21 / −26 | $163k | 44% / 2% | 22.2, 68% |
| 1.5x, cap 0.10 | 74.4 / 2.28 / −17 | 30.4 / 1.15 / −19 | $138k | 32% / 1% | 18.8, 54% |
| 1.5x, cap 0.15 | 93.7 / 2.35 / −20 | 36.5 / 1.18 / −24 | $162k | 48% / 3% | 21.3, 72% |
| 1.3x, no conviction | 62.6 / 2.33 / −15 | 26.6 / 1.19 / −17 | $125k | 14% / 0% | 16.7, 32% |

- **A 15% night-name cap is the best Sharpe of every profile at measured costs** (2.42), and the
  EH frontier's knee: +5.7pp/yr over the gated 1.3x for +11pp of P(DD>30%). Beyond it
  (aggressive, 1.5x) return rises ~2pp for +12-16pp of drawdown odds. At tier_hi it loses Sharpe,
  so it is a bet that live costs stay low: the reason addendum 17 rejected 0.15 at tier costs.
- Conviction is worth +5.7pp/yr at 1.3x (62.6 → 68.3) at the same Sharpe.
- **Built:** `daily.profiles.moderate` (night_max_name_pct 0.15, nothing else; leverage still
  only through the gate). `DAILY_LIVE_PROFILE=moderate` in `.env`. Not enabled.


# Addendum 30 — the night pool used split-adjusted prices: every night number restated (2026-09-28)

> **Read this before any earlier night-leg number.** Every night-leg level in addenda 5-29 (and the adjusted-pool
> levels quoted in addenda 31-38) is overstated by about one fifth. Restated baseline on the raw pool, 2021-26:
> **V7 shipped 47.2% / 2.06 / −14 at 3bp** (was 58.0 / 2.33), **29.4% / 1.41 / −17 at tier_hi** (was 39.6 / 1.73),
> edge-halves at tier_hi **13.3%** (was 17.5); live today (no conviction) 40.6% at 3bp / 23.7% at tier_hi;
> Roth M3 (live-accurate) 35.3% / 22.4%. Addendum 39 gives every program book on the raw pool.

(The pre-registration block below was written and stamped BEFORE any floor-test number was computed.)

## Pre-registration: night_price_min floor test (stamped: Mon Sep 28 22:13:28 PDT 2026)

SHADOW-ONLY by construction: 2024-26 (and 2021-23, via the verifier's per-trade diagnostic)
has already been seen for sub-$5 names, so no outcome can make this ADOPT.

- Pool: honest 15:50 candidates on RAW prices (book.night_days(raw_price=True), corr 0.7), floor
  night_price_min in {5 (live), 3, 2, 1}; everything else as shipped.
- Cost model (price-aware, primary): "tier+tick" = book.TIERS tier on the RAW price, floored at half
  a $0.01 tick / raw price per side. Sensitivity: "tier_hi+tick", "flat3+tick".
- Books: V7 shipped (1.0x, cap .10, conviction .5) and moderate (1.3x, cap .15); $3k + $1k/21 sessions.
- Report: CAGR/Sharpe/maxDD per half (2021-23, 2024-26), EH, per-trade net of the ADDED names
  (raw price in [floor, 5)) by half.
- Placebo: per half, the mean net (tier+tick) of the added trades vs 500 draws of the same number
  of raw >= $5 pool trades from the same vol20 decile (deciles over the whole pool);
  report the percentile.
- Shadow bar (all must hold, at tier+tick): book CAGR gain > 0 in BOTH halves for V7; added-trade
  mean net > 0 in both halves; placebo percentile >= 95% in both halves; and gain >= 0 at
  tier_hi+tick in 2024-26. Otherwise dead. Addendum 21's existing conditional (night_price_min 3.0
  if live sub-$10 costs <= ~20bp/side) stands either way and is the only path to live.

---

    PYTHONPATH=. .venv/bin/python -m research.sim.rawprice --cache   # heavy lock: pools + 2020 rebuild + sim_cache_raw.pkl
    PYTHONPATH=. .venv/bin/python -m research.sim.rawprice           # ~6 min, no panel
    output: scratchpad/rp/main2.log, scratchpad/rawprice_res.pkl

**Every night-leg number published before this addendum is too high.** The research panel and
`data.night_candidates()` use Alpaca `adjustment='all'` prices, adjusted as of the 2026-09 fetch. A name
that reverse-split later shows its old prices scaled up: TDIC on 2025-10-16 was $66.81 in the research
data and $0.535 on the tape. The live executor sees real quotes. So three things in the backtest used the
wrong price:
- the $5 `night_price_min` floor (and the $2,000 ceiling),
- the price tier in `book.cost_bps`,
- whole-share rounding.

Returns are split-invariant, so they were right. The pool they were computed on was not. The new_listings
verifier found this (addendum 36, V6). This addendum fixes it and restates the numbers.

**Fix (opt-in; every default and every published script is unchanged).**
- `data/research/night/raw_close.parquet` holds raw and 'all'-adjusted SIP daily open and close from the
  same request batch. It covers every `night_candidates()` symbol from 2020-10 to 2026-09 (3,518 symbols),
  plus every 2020 close-signal candidate symbol in panel2020 from 2019-10 to 2020-11 (2,122 symbols).
- `data.night_candidates(raw=True)` adds `raw_f`, `raw_p50`, `raw_C` and `raw_src`.
- `book.night_days(raw_price=True)`, `Sim(raw_price=True)`, and `validate.load_sim(raw_price=True)`
  (cached separately in `sim_cache_raw.pkl`).
- `cost_bps` gains `"<model>+tick"`: a floor of half a $0.01 tick divided by the price, per side.
- Tests: `tests/test_rawprice.py`.
- Check: the adjusted column below reproduces addendum 29 and addendum 39's adjusted column to the decimal.

**Coverage.**
- 20,501 candidates. The raw factor is exact on the date for 99.9%.
- 0.1% (25 rows) are "rebased": a corporate action between the two fetches put the two adjusted series on
  different bases, so the factor is raw close / our close. 0% needed the nearest-date fallback, and 0%
  had no raw data.
- 16.3% of V7-pool trades (2020-11 to 2026-09) were really under $5 raw. By year: 8% (2020), 11%, 15%,
  20%, 24% (2024), 21%, 11%.
- Up to 8% of trades per year were under $1 raw.
- The raw pool drops 1,858 trades, and adds 235 trades from forward splits (adjusted < $5, raw >= $5).

## Restated books (adjusted → RAW)

$3k + $1k/21 sessions. Columns are CAGR/Sharpe/maxDD for 2021-23 | 2024-26 | full. EH = edge-halves.
MC = 5-year bootstrap under EH (P(DD>30%) / P(DD>50%)).

| book | cost | adjusted (published) | RAW | EH adj → raw | MC P30/P50 adj → raw |
|---|---|---|---|---|---|
| V7 shipped 1.0x cap .10 | 3bp | 56.9 · 59.2 · 58.0/2.33/−12 | 50.2 · 44.1 · **47.2/2.06/−14** | 25.1 → 20.8 | 11/0 → 11/0 |
| | tier | 48.6 · 46.4 · 47.5/1.99 | 41.2 · 32.7 · **37.0/1.70/−16** | 20.8 → 16.5 | 17/0 → 19/0 |
| | tier_hi | 42.0 · 37.1 · 39.6/1.73 | 34.4 · 24.3 · **29.4/1.41/−17** | 17.5 → 13.3 | 23/0 → 26/1 |
| gate 1.3x cap .10 | 3bp | 62.5 · 74.8 · 68.3/2.32 | 53.2 · 53.6 · **53.4/2.04/−18** | 28.6 → 23.0 | 21/0 → 22/0 |
| | tier | 51.4 · 55.6 · 53.4 | 41.3 · 37.9 · **39.7/1.62/−19** | 22.8 → 17.4 | 30/1 → 33/1 |
| | tier_hi | 43.3 · 43.3 · 43.3 | 32.7 · 26.8 · **29.8/1.29/−20** | 18.6 → 13.1 | 39/2 → 44/3 |
| moderate 1.3x cap .15 | 3bp | 75.2 · 97.2 · 85.5/2.42 | 61.2 · 67.5 · **64.2/2.10/−23** | 34.3 → 26.7 | 32/1 → 35/1 |
| | tier | 58.4 · 72.1 · 64.8 | 45.4 · 46.3 · **45.8/1.63/−24** | 26.6 → 19.4 | 45/3 → 50/4 |
| | tier_hi | 48.0 · 55.3 · 51.4 | 33.9 · 31.4 · **32.7/1.25/−25** | 21.4 → 13.9 | 56/5 → **60/8** |
| moderate as built 1.0x cap .15 | 3bp | 67.2 · 75.6 · 71.2/2.46 | 56.5 · 54.5 · **55.5/2.15/−18** | 29.8 → 23.9 | 15/0 → 18/0 |
| | tier | 54.4 · 58.2 · 56.2 | 44.4 · 39.4 · **42.0/1.73/−20** | 24.0 → 18.4 | 24/0 → 28/1 |
| | tier_hi | 46.3 · 46.4 · 46.3 | 35.7 · 28.2 · **32.1/1.39/−21** | 20.0 → 14.2 | 32/1 → 38/2 |
| aggressive 1.3x cap .20 i.6 | 3bp | 83.6 · 105.2 · 93.7/2.39 | 69.0 · 75.7 · **72.2/2.11/−25** | 36.7 → 29.3 | 44/2 → 46/3 |
| | tier | 65.9 · 77.0 · 71.1 | 49.7 · 50.8 · **50.2/1.61/−26** | 28.5 → 20.7 | 58/5 → 60/7 |
| | tier_hi | 51.5 · 58.1 · 54.6 | 36.2 · 33.5 · **34.9/1.23/−28** | 22.2 → 14.4 | 68/9 → **71/14** |
| live today 1.0x cap .10, no conviction | 3bp | 45.8 · 57.2 · 51.2/2.38 | 39.6 · 41.6 · **40.6/2.08/−14** | 22.6 → 18.3 | 4/0 → 5/0 |
| | tier | 37.9 · 43.8 · 40.7 | 31.4 · 30.4 · **30.9/1.67/−15** | 18.3 → 14.2 | 8/0 → 11/0 |
| | tier_hi | 32.9 · 35.2 · 34.0 | 25.0 · 22.2 · **23.7/1.33/−16** | 15.4 → 11.0 | 12/0 → 18/0 |
| Roth b1 as modelled (asis) | 3bp | 43.0 · 55.0 · 48.7/2.29 | 37.2 · 39.7 · **38.4/1.99/−14** | 21.6 → 17.4 | 5/0 → 6/0 |
| | tier | 35.5 · 41.8 · 38.5 | 29.0 · 28.6 · **28.8/1.57/−15** | 17.4 → 13.3 | 9/0 → 13/0 |
| | tier_hi | 29.1 · 33.1 · 31.0 | 22.9 · 20.6 · **21.8/1.24/−16** | 14.1 → 10.1 | 14/0 → 20/0 |
| Roth live-accurate M3 | 3bp | 39.3 · 52.0 · 45.3/2.25 | 33.6 · 37.1 · **35.3/1.97/−10** | 20.3 → 16.2 | 4/0 → 3/0 |
| | tier | 33.3 · 42.4 · 37.6 | 27.1 · 28.4 · **27.7/1.61/−11** | 17.1 → 12.9 | 6/0 → 7/0 |
| | tier_hi | 28.1 · 34.9 · 31.3 | 22.5 · 22.3 · **22.4/1.34/−12** | 14.4 → 10.5 | 9/0 → 11/0 |

Change in full-period CAGR, raw − adjusted, in pp (EH change in parentheses):

| book | 3bp | tier | tier_hi |
|---|---|---|---|
| V7 shipped | −10.8 (−4.3) | −10.5 (−4.3) | −10.2 (−4.3) |
| gate 1.3x | −14.9 (−5.6) | −13.8 (−5.4) | −13.5 (−5.5) |
| moderate 1.3x cap .15 | −21.3 (−7.6) | −19.0 (−7.2) | −18.8 (−7.5) |
| moderate as built 1.0x cap .15 | −15.6 (−5.9) | −14.3 (−5.6) | −14.3 (−5.9) |
| aggressive | −21.5 (−7.4) | −20.9 (−7.8) | −19.7 (−7.7) |
| live today (no conviction) | −10.6 (−4.3) | −9.8 (−4.1) | −10.4 (−4.5) |
| Roth b1 | −10.3 (−4.2) | −9.7 (−4.1) | −9.2 (−4.0) |
| Roth M3 | −10.0 (−4.1) | −9.9 (−4.2) | −9.0 (−3.9) |

What this means:
- **The loss is almost all pool membership, not cost.** At 3bp flat the cost tier plays no part, and the
  drop is the same ~10pp. The names that were really under $5 were the pool's best trades in the
  adjusted data: in 2024-26, +69.5bp per trade vs −2.4bp for the rest (section D).
- **2024-26 takes most of the hit.** V7 at 3bp drops 15pp in 2024-26 vs 7pp in 2021-23. The "holdout
  held up" reading of 2024-26 was partly lookahead: later reverse splits are concentrated in names that
  crashed during 2024-25.
- **Leverage and a wider name cap amplify it.** Moderate loses 19-21pp and aggressive 20-22pp. Moderate's
  edge over V7 shrinks from +27.5pp to +17.0pp at 3bp, and from +11.8 to +3.3pp at tier_hi.
- **Moderate now misses the taxable frontier's own risk bar at tier_hi.** Its P(DD>50%, EH, pre-tax)
  is 8%, against a bar of ~5%. At 3bp it is 1%.
- **Aggressive at tier_hi** now has P(DD>30%) of 71% and P(DD>50%) of 14%.
- Addendum 29's claim that a 15% cap has the best Sharpe no longer holds as stated. At 3bp on raw
  prices the Sharpe ranking is: moderate as built (1.0x, cap .15) 2.15, aggressive 2.11, moderate 2.10,
  V7 2.06, gate 2.04. The differences are small.
- Addendum 39 section G (raw-$5 exclusion only, with costs and shares still on adjusted prices) was a
  close lower-fidelity version of this: V7 3bp 46.7 vs 47.2 here, tier_hi 31.1 vs 29.4.

**2020 close-signal rebuild (panel2020, COVID).** Night leg at unit weight, cap .10, 10bp,
bias-corrected:
- 2020-01..11 CAGR: −9.4% adjusted vs −6.2% raw.
- COVID drawdown: −11.1% adjusted vs −7.7% raw.
- 196 of 1,765 picks leave the pool and 165 enter.

In 2020 the removed (really sub-$5) names were losers, so the COVID stress numbers published before this
were slightly pessimistic. The 2016-19 holdout night half is T-bills and is unaffected.

## D. The verifier's diagnostic, restated (POST-HOC)

Trades in the ADJUSTED V7 pool (corr .7, cap .10) split by raw price. Mean net per trade in bp.

| cost model | 2021-23 raw < $5 (n 703) | raw ≥ $5 | 2024-26 raw < $5 (n 1,100) | raw ≥ $5 |
|---|---|---|---|---|
| tier on ADJUSTED price (as published) | +10.1 (<$1 +109, $1-5 −0.9) | +0.4 | **+69.5** (<$1 +44.6, $1-5 +82.9) | −2.4 |
| tier on RAW price | −4.2 | −1.2 | +56.3 | −3.2 |
| tier+tick on RAW price | −37.4 ($1-5 −32.0) | −1.2 | −106.4 ($1-5 **+47.7**) | −3.2 |
| tier_hi+tick on RAW price | −46.3 ($1-5 −41.9) | −11.2 | −112.2 ($1-5 +38.8) | −13.8 |

- The verifier's +49.7bp vs −12.8bp was the new_listings (add. 36) "not F1" subset. Across all trades it is +69.5 vs −2.4.
- The tick floor uses a $0.01 tick, as pre-registered. Sub-$1 names quote in $0.0001 (Rule 612), so its
  <$1 rows overstate cost. That does not affect the floor test, whose added names are all ≥ $1.
- The sub-$5 edge appears only in 2024-26, and only before a realistic spread. In 2021-23 the $1-5 names
  lose money at every cost model.

## E. Floor test (pre-registered above; SHADOW-ONLY at most)

Raw prices throughout. Book gain is the change in CAGR vs the $5 floor, in pp, for 2021-23 / 2024-26.

| floor | V7 tier+tick gain | V7 tier_hi+tick | V7 flat3+tick | moderate tier+tick | added trades, net tier+tick 21-23 / 24-26 | placebo pct 21-23 / 24-26 |
|---|---|---|---|---|---|---|
| $3 | −1.7 / +0.7 | −2.3 / −0.7 | −1.8 / +0.9 | −2.5 / +0.4 | −72.9 (n 334) / +21.1 (n 463) | 2% / 76% |
| $2 | −2.2 / +2.6 | −3.0 / +0.8 | −2.3 / +2.6 | −3.0 / +3.1 | −53.1 (n 523) / +34.2 (n 645) | 3% / 87% |
| $1 | +0.7 / +0.6 | −0.1 / −0.8 | +0.4 / +0.3 | +2.7 / −2.5 | −33.2 (n 730) / +28.4 (n 943) | 7% / 82% |

(V7 at the $5 floor, raw: tier+tick 41.2 · 32.7 · 37.0/1.70; tier_hi+tick 34.4 · 24.3 · 29.4.)

**Verdict: DEAD at every floor.**
- The only floor with a positive V7 tier+tick gain in both halves is $1 (+0.7 / +0.6). It fails every
  other condition: its added trades lose 33bp in 2021-23, its placebo percentiles are 7% and 82%, and
  its tier_hi+tick gain in 2024-26 is −0.8.
- In 2021-23 the added names do worse than same-volatility names above $5 (placebo 2-7%). The 2024-26
  gain is inside the placebo band (76-87%).
- **Addendum 21's conditional stands** (night_price_min 3.0 only if live sub-$10 costs ≤ ~20bp/side vs the
  official open). It is not reinforced: at $3 the book gain is −1.7 / +0.7 even at tier+tick.

## What changes

- **Nothing in the live code.** Live already uses raw prices. This was a research-only error, and the live
  $5 floor is what the raw column models.
- **Every expectation derived from the night leg is about one fifth lower.** V7 at 3bp is 47% CAGR, not
  58%. Under EH it is 21%, not 25%.
- **The pre-planned moderate profile needs a new sign-off.** At tier_hi it now breaks the ~5% P(DD>50%)
  bar (8%). It is still fine at the measured ~0-3bp.
- Aggressive at tier_hi is now 14% P(DD>50%).
- **New research should call `load_sim(raw_price=True)` / `night_days(raw_price=True)`.** The adjusted path
  is kept only so the published numbers reproduce.
- The addenda from this program (31 roth_opt, 32 taxable_frontier, 33 macro_events, 34 index_mechanics,
  35 opex, 36 new_listings, 37 regime_robust, 38 ops_capital) all quote adjusted-pool levels.
  - Their **increments** measured on the IBS, noise and ETF legs are unaffected.
  - Their **night-leg levels** and night-sized increments should be read as about one fifth too high.
  - None of them was re-run on the raw pool, except the combine: addendum 39 restates every program book on the
    raw pool, and its numbers are the headline.


# Addendum 31 — Roth IRA optimization inside the IRA's rules: SHADOW (Roth-first wash guard G4s, M2L sizing, A2) (2026-09-28)

## Pre-registration (written before any 2024-26 number was computed)

Stamp: `Mon Sep 28 20:53:38 PDT 2026` (output of `date`).

Baseline = the shipped Roth book (addendum 20 "b1", research/sim/roth.py): IBS 0.5 + night 0.5
at 1.0x overnight, live tilt, weekend x0.5, corr 0.7, name cap 0.10; intraday QQQ/SMH noise leg
held as TQQQ/SQQQ/SOXL/SOXS on the night half's daytime cash, cap 1.5x underlying, no conviction,
+0.3bp/side leveraged-ETF extra. Judged at 3bp flat / tier / tier_hi; fit 2021-23 judge 2024-26 and
the reverse; 2016-20 holdout via the 2020 rebuild (regime_tilt.holdout_legs) where the leg exists.

Mechanism check found BEFORE running (live code, executor.py): the Roth places its close-auction
night buys at 15:40 while the 3x-ETF intraday position is held until the 15:57 flatten. An IRA
under limited margin has no debit: buying power at 15:40 = cash, and the 3x ETFs hold up to the
whole night half. So the as-coded Roth cannot fund both on a day the noise leg is in at 15:31 and
the night leg has picks. Every Roth variant below is run under the PRECISE constraint, two ways:
  M1 flatten the 3x ETFs at 15:40 (minute 370) instead of 15:57, proceeds fund the MOC buys;
  M2 hold to 15:57; the night leg only gets the cash not in 3x ETFs at 15:40.
The better of M1/M2 becomes the "precise baseline" all other variants are measured against.

(a) Idle cash. Measure: fraction of Roth equity-days idle overnight (night-leg unused + IBS half in
SGOV) and in the daytime. Mechanism: the multi-day-oversold overnight bounce in SPY/QQQ (V6,
addendum 27, shadow) is an index-level liquidity-provision premium at the close; in the Roth it
costs nothing in tax or margin because it only uses money already idle overnight.
  A1  V6 (15:40 either-trigger, SPY/QQQ, close -> open) in the IBS idle half only (as add. 27)
  A2  V6 funded by ALL idle overnight money (IBS idle half + night-leg unused), cap 1.0x total
(b) 3x-ETF sizing, underlying-leverage cap L for the Roth intraday leg (precise constraint):
  B1  L 0.75   B2  L 1.0   B3  L 1.5 (shipped)   B4  L up to 3.0 using ALL daytime cash
  (night half + IBS half when the IBS leg has no pick and SGOV is sold at the open)
  B5  B3 + TQQQ/SQQQ conviction 0.5 of equity from the IBS idle daytime cash (no-pick days only)
  Kelly: report the EH x tier_hi growth vs L.
(c) IBS structural: after a night the night leg held NOTHING (known at 09:15), the IBS leg takes
  C1  1.0 of equity (the night half's cash) for that open->open hold; next day's night leg and
      intraday leg get only the cash IBS leaves free
  C2  same at 0.75
(d) Asset location / wash sales. Legs are 100% short-term in taxable (holds <= 1 day), so tax drag
  is proportional to each leg's gain; wash-sale exposure is counted per leg: same-account (deferral)
  and cross-account taxable-loss-sale with a Roth purchase of the same symbol within +-30 days
  (permanent, Rev. Rul. 2008-5). Guard designs, both books run V7-taxable / Roth-precise-baseline:
  G0  no guard (count the permanently disallowed losses in $)
  G1  current live guard: symmetric 31-day lockout, taxable runs first each phase (priority)
  G2  Roth IBS on account-disjoint look-alikes (SPY->SPLG/IVV, QQQ->QQQM, IWM->VTWO, MDY->IJH,
      XLK->VGT, XLF->VFH, XLE->VDE, XLV->VHT, XLI->VIS, XLY->VCR, XLP->VDC, XLU->VPU, XLB->VAW,
      SMH->SOXX, XBI->? (none, locked), DIA->? (none), EEM->IEMG, EFA->IEFA); night names still G1
  G3  G2 + loss-aware night guard: the Roth skips a name only if taxable holds/orders it or sold it
      at a LOSS in the last 30 days; taxable unrestricted (count residual permanent disallowance)
  Metric: combined after-tax $ (taxable at 32% on net short-term gain, disallowed losses added back;
  Roth tax-free) at $3k taxable + $7.8k Roth and at $100k each.

PASS BAR (a, b, c): vs the precise baseline, CAGR and Sharpe higher in BOTH 2021-23 and 2024-26 at
3bp AND tier_hi; 2016-20 holdout not worse (Sharpe) where the leg can be rebuilt; Newey-West t
(lag 5) of the daily difference >= 2.0 over 2021-26; placebo (same count of trigger nights on random
dates per symbol, 50 seeds) beaten >= 45/50 in both halves where a trigger exists; EH 5y MC
($3k+$1k/mo and $10k lump) P(DD>30%) <= 15%. Sizing (b): choose the L with the best EH x tier_hi
growth subject to P(DD>30%) <= 15%; change from 1.5 only if that L also wins both halves.
(d): pick the guard with the highest combined after-tax $ at the user's size; a design that needs
look-alike ETFs is flagged "substantially identical" uncertain (IRS has never ruled on
same-index-different-issuer funds; different-index funds, e.g. XLK vs VGT, are the safer pairs).
Anything added after results is POST-HOC and at most SHADOW.

Interpretation fixed before the C runs: "the night leg held nothing" = the night leg had NO PICKS
(a no-cash night would make C1 self-perpetuating, since full-weight IBS leaves the next night no cash).

## How to run

    # heavy lock, once (~10 s): live-guard night leg, conviction series, 2016-20 holdout legs
    PYTHONPATH=. .venv/bin/python -m research.sim.roth_opt_extract
    PYTHONPATH=. .venv/bin/python -m research.sim.roth_opt            # ~2 min, no panel
    PYTHONPATH=. .venv/bin/python -m research.sim.roth_opt --only-d   # guards only, ~1 min

Roth $7,800 + $7,500/yr ($625 every 21 sessions), whole shares, 2021-02 .. 2026-09. Replication:
the addendum-20 model ("asis") gives 38.5/1.90/−13 at tier vs 39.0/1.88/−13 in roth.py (the
$ size and deposits differ); the steppable taxable V7 matches `Sim.replay` to 4 decimals.

## 0. A live mechanics gap: the 15:40 cash conflict

The executor sizes the Roth's close-auction night buys at 15:40 on equity (0.5 E) while the
TQQQ/SQQQ/SOXL/SOXS position is held until the 15:57 flatten. In an IRA under limited margin there is
no debit: buying power at 15:40 is cash. The noise leg is still in at 15:40 on 32% (QQQ) / 30% (SMH)
of sessions, so on those days the as-coded Roth would try to spend cash it does not have (rejected or
partial MOC orders at Schwab). Addendum 20's model silently assumed both.

| CAGR/Sharpe (maxDD) | 3bp 21-23 | 3bp 24-26 | 3bp full | tier full | tier_hi 21-23 | tier_hi 24-26 | tier_hi full |
|---|---|---|---|---|---|---|---|
| asis (add. 20 b1; infeasible) | 43.0/2.45 | 55.0/2.21 | 48.7/2.29/−12 | 38.5/1.90/−13 | 29.1/1.77 | 33.1/1.48 | 31.0/1.59/−14 |
| M1 flatten 3x at 15:40 | 41.5/2.41 | 55.9/2.26 | 48.3/2.29/−12 | 38.3/1.91/−13 | 28.1/1.74 | 33.6/1.51 | 30.7/1.59/−14 |
| **M2 hold to 15:57, night on the free cash** | 43.8/2.55 | 54.1/2.26 | **48.7/2.36/−10** | 39.7/2.01/−11 | 30.9/1.91 | 34.2/1.57 | **32.5/1.70/−11** |

The fix costs nothing: sizing the Roth night leg to `min(0.5 E, cash at 15:40)` (M2) is as good as
the infeasible model (the smaller night leg on trend days even trims drawdown; that part is post-hoc,
not claimed). **M2 is the precise baseline below.** Needed in code before the Roth goes live.

## (a) Idle cash

Precise baseline: mean overnight gross 0.38x. The night half's money is idle 57% of the time, the IBS
half sits in SGOV 67% of sessions; together **62% of Roth equity-nights are idle**.

## Results, all pre-registered variants (Roth, precise baseline M2)

| variant | 3bp 21-23 | 3bp 24-26 | 3bp full | tier full | tier_hi 21-23 | tier_hi 24-26 | tier_hi full | NW t | holdout 16-20 (dSh) | placebo beats | EH tier_hi | MC $3k+1k P(DD>30/50) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **baseline M2 = B3 (L 1.5)** | 43.8/2.55 | 54.1/2.26 | 48.7/2.36/−10 | 39.7/2.01 | 30.9/1.91 | 34.2/1.57 | 32.5/1.70/−11 | – | 16.1/1.30 | – | 14.8/0.88/−17 | 11% / 0% |
| A1 V6 in IBS idle half | 44.6/2.56 | 58.2/2.36 | 51.0/2.42/−10 | 42.4/2.08 | 31.5/1.92 | 38.0/1.69 | 34.6/1.77/−11 | +2.23 | 16.7/1.33 (+0.03)* | 48/50, 49/50 | 15.7/0.91/−16 | 10% / 0% |
| **A2 V6 on all idle overnight money** | 45.3/2.56 | 61.5/2.46 | 52.8/2.47/−10 | 44.4/2.15 | 32.6/1.95 | 40.1/1.76 | 36.1/1.82/−11 | +2.86 | 17.4/1.38 (+0.08)* | 50/50, 50/50 | 16.3/0.94/−15 | 10% / 0% |
| B1 L 0.75 | 37.6/2.54 | 50.3/2.29 | 43.6/2.36/−10 | 33.5/1.91 | 24.6/1.77 | 31.0/1.55 | 27.6/1.62/−12 | −2.27 | 11.9/1.22 (−0.08) | n/a | 12.8/0.84/−15 | 9% / 0% |
| B2 L 1.0 | 39.9/2.53 | 52.8/2.31 | 46.0/2.38/−10 | 36.4/1.96 | 27.0/1.82 | 32.7/1.58 | 29.7/1.66/−12 | −1.93 | 13.6/1.26 (−0.04) | n/a | 13.7/0.86/−16 | 10% / 0% |
| B4 L ≤ 3.0 on all day cash | 46.0/2.58 | 58.0/2.31 | 51.6/2.40/−11 | 42.5/2.06 | 33.7/1.99 | 37.5/1.64 | 35.5/1.77/−12 | +2.17 | 18.0/1.23 (**−0.07**) | n/a | 16.1/0.92/−18 | 12% / 0% |
| B5 L 1.5 + conviction 0.5 (IBS idle cash) | 71.3/2.87 | 64.9/2.27 | 68.2/2.54/−12 | 57.0/2.23 | 54.8/2.36 | 43.5/1.67 | 49.3/1.99/−16 | +4.31 | 19.4/1.20 (**−0.10**) | n/a | 21.5/1.02/−24 | **18%** / 0% |
| C1 IBS 1.0 after a no-pick night | 45.0/2.60 | 53.7/2.25 | 49.1/2.38/−10 | 40.1/2.02 | 31.9/1.96 | 34.1/1.57 | 33.0/1.72/−11 | +0.53 | 16.1/1.30 (0.00) | 38/50, **16/50** | 15.0/0.89/−16 | 11% / 0% |
| C2 IBS 0.75 after a no-pick night | 44.2/2.57 | 53.9/2.26 | 48.8/2.37/−10 | 39.8/2.01 | 31.3/1.93 | 34.2/1.57 | 32.7/1.71/−11 | +0.24 | 16.1/1.30 (0.00) | 38/50, **15/50** | 14.9/0.88/−16 | 11% / 0% |

$10k-lump MC P(DD>30%) under EH x tier_hi: baseline 11%, A1 10%, A2 10%, B4 12%, B5 18%. P(DD>50%) 0% for all.
Placebo: A = same V6 trigger count per symbol on random dates; C = 58 random full-IBS days. 50 seeds each.

Crash episodes (tier_hi; COVID from the 2016-20 returns book) / worst day / worst month:
baseline COVID −2.5%, 2022 +15.5%, Apr 2025 +4.8%, −6.2% / −9.1%. A2 −3.7% / +17.5% / +3.7%, −6.2% / −9.3%.
B4 −2.4% / +15.4% / +4.7%, worst month −11.7%. B5 **−11.3%** / +46.7% / +4.7%, −6.2% / −9.8%.

Kelly dial (EH x tier_hi full CAGR vs intraday cap L): 0 → 8.5%, 0.5 → 11.3, 0.75 → 12.8, 1.0 → 13.7,
1.5 → 14.8, 2.0 → 15.7, 3.0 → 16.1 (P(DD>30%) 11-12% throughout). The growth curve is still rising
but flattening at 1.5-3.0: the Roth is below its Kelly peak, but the extra (B4) comes with a worse
holdout Sharpe and a worse worst month.

Verdicts:
- **A2 (V6 on all idle overnight money) passes every pre-registered bar** (both halves up at 3bp and
  tier_hi, t 2.86, holdout +0.05 Sharpe, placebo 50/50 both halves, P(DD>30%) 10%). A1 also passes
  (t 2.23, placebo 48/49). But the V6 RULE was itself found post-hoc on 2021-26 in addendum 27 and is
  in shadow; the gain is lopsided (2021-23 +0.01 Sharpe, 2024-26 +0.19), the same pattern that killed
  the unconditional index filler. **SHADOW**: when V6 graduates, the Roth should fund it from all idle
  overnight money (A2), not only the IBS idle half.
- B1/B2 (smaller intraday): **dead** — lower growth, the Roth is under-levered, not over.
- B4 (≤ 3.0x on all daytime cash): **borderline** — +2.8pp tier_hi, t 2.17, but 2016-20 Sharpe −0.07
  and worst month −11.7%. Keep L 1.5.
- B5 (TQQQ/SQQQ conviction in the Roth from the IBS idle daytime cash): **borderline** — +24pp/yr
  tier_hi, t 4.31, but 2024-26 3bp Sharpe +0.00, 2016-20 Sharpe −0.10, EH P(DD>30%) 18% > 15%,
  COVID −11.3%. Revisit only with the taxable conviction trade's live shadow record.
- C1/C2 (full IBS after a no-pick night): **dead** — 2024-26 negative, placebo 15-16/50.

## (d) Asset location and wash sales

Tax drag per leg (taxable V7, tier_hi, pre-tax contribution x 32%): night 8.1pp/yr → 2.6pp, IBS
8.1 → 2.6pp, intraday 9.3 → 3.0pp. Every leg holds ≤ 1 session, so 100% short-term; no leg is
"better located" in taxable on tax grounds. What differs is what each account CAN do: only taxable
can lever overnight or short; only the Roth is tax-free. Loss sales are frequent: 48% of night
round trips and 41% of intraday days close at a loss.

Guards, both books running side by side (taxable $3k + $1k/mo, Roth $7.8k + $625/21d; after-tax
end $ with 32% on each year's net gain and permanently disallowed losses added back):

| guard | cost | taxable CAGR 21-23/24-26/full | Roth CAGR 21-23/24-26/full | perm. disallowed, % of taxable gross losses (+ if same-index look-alikes count) | end $ taxable + Roth (user) | at 100k-scale |
|---|---|---|---|---|---|---|
| G0 none | 3bp | 38.0/52.2/44.7 | 43.8/54.1/48.7 | **82%** | −$100k + $238k = $138k | $1.72M |
| G1 live guard (symmetric, taxable first) | 3bp | 38.5/52.1/44.9 | **18.3/9.2/13.8** | 0% | $175k + $73k = $248k | $3.19M |
| G2 Roth IBS on look-alikes | 3bp | 38.6/52.1/45.0 | 26.8/17.0/22.0 | 0% (+1.7%) | $175k + $95k = $270k | $3.49M |
| G3 G2 + loss-aware night guard | 3bp | 38.0/52.2/44.7 | 28.3/17.2/22.8 | 0.1% (+1.8%) | $175k + $97k = $272k | $3.50M |
| G4 Roth first, owns night names (POST-HOC) | 3bp | 22.6/17.1/19.9 | 45.3/49.1/47.1 | 0.7% (+10.6%) | $101k + $221k = **$322k** | **$4.15M** |
| G0 | tier_hi | 26.4/30.8/28.5 | 30.9/34.2/32.5 | 81% | −$61k + $144k = $83k | $1.03M |
| G1 | tier_hi | 26.3/30.7/28.4 | 17.9/9.4/13.8 | 0% | $125k + $73k = $197k | $2.52M |
| G2 | tier_hi | 26.4/30.7/28.4 | 26.5/17.3/22.0 | 0% (+2.1%) | $124k + $96k = $220k | $2.83M |
| G3 | tier_hi | 26.4/30.8/28.5 | 27.2/17.6/22.5 | 0.1% (+2.2%) | $125k + $97k = $221k | $2.82M |
| G4 | tier_hi | 22.3/17.3/19.9 | 32.2/30.1/31.2 | 0.7% (+9.6%) | $101k + $134k = **$235k** | **$3.00M** |

EH x tier_hi at user size (CAGR): G1 taxable 13.1% / Roth 7.2%; G4 taxable 9.8% / Roth 14.3%.

What this shows:
1. **Without a guard the Roth destroys the taxable book** (G0): both books buy the same night names at
   the same close, so 82% of taxable's realized losses have a Roth purchase within 30 days and are
   gone for good (Rev. Rul. 2008-5). On a book whose gross losses are several times its net gain, that
   turns the taxable account's tax bill larger than its profit. The expected $ drag of running the same
   legs in both accounts unguarded is the whole taxable book and more.
2. **The live guard (G1) avoids that but starves the Roth**: the taxable book runs first each phase and
   its QQQ/SMH intraday trades touch QQQ and SMH nearly every day, so the Roth IBS leg can almost never
   trade QQQ/SMH or any name taxable traded in 31 days, and the Roth night leg only gets names taxable
   could not afford (whole shares at $3k). The Roth falls from 48.7% to 13.8% CAGR (3bp), below SPY.
3. Look-alike IBS (G2) and a loss-aware night guard (G3) recover only part (Roth 22-23%): the night
   names collide on the SAME DAY, which no loss-aware rule can fix.
4. **Giving the Roth priority on the night names (G4) is the best household outcome at both cost
   levels and both sizes** (+$74k / +30% combined after-tax end $ at 3bp, +$38k at tier_hi vs G1). The
   taxable book gives up most of its night leg (44.7 → 19.9%) and keeps IBS + intraday. G4 was added
   after seeing G1-G3, so it is POST-HOC; its logic (the scarce shared names go to the tax-free, larger
   account) is structural, not a fitted parameter.

Look-alike caveat: SPY/SPLG, QQQ/QQQM, IWM/VTWO, MDY/IJH track the SAME index; the IRS has never ruled
whether that is "substantially identical". If they count, G4's taxable book loses a further ~10% of its
gross losses (end $ $101k → $95k at 3bp). Safer pairs track a different index: XLK→VGT, XLF→VFH,
SMH→SOXX (already the live stand-in), sector SPDRs → Vanguard sector funds (MSCI vs S&P); for SPY use a
different-index large-cap fund (VV / SCHX), for QQQ ONEQ (thin), else let the Roth skip QQQ/SPY IBS days.
Also: the taxable noise leg's stand-in QQQ → QQQM (`noise_alt_symbol`) is same-index and would collide
with a Roth QQQM; and a live taxable conviction trade (TQQQ/SQQQ) would collide with the Roth's intraday
TQQQ/SQQQ under the current guard (whichever book trades first locks the other out for 31 days).

## Verdict

- ~~Mechanics fix required~~ (verifier: live already cash-bounds the night buys, greedily; pro-rata
  sizing on the 15:40 cash is an optional refinement, see Verifier notes 1).
- **Guard: the live symmetric guard costs the Roth ~35pp/yr.** Recommend Roth-priority (G4) in SHADOW:
  log daily which names each book would take/skip under G4 vs the current guard before switching.
  Proposed config: `daily.wash_guard: symmetric | roth_first` (default symmetric), plus
  `daily.roth_ibs_lookalikes: {XLK: VGT, XLF: VFH, ...}`.
- A2 (V6 funded by all idle overnight Roth money): passes its bars, SHADOW with V6.
- (Add. 39: on raw prices M2L is worth +1.2pp EH and A2 +0.8pp; G4s must run with Roth F3 off.)
- B4 and B5 borderline; B1, B2, C1, C2 dead. Keep the Roth intraday cap at 1.5x.

## do NOT redo

| idea | verdict | why |
|---|---|---|
| Roth: smaller intraday cap (0.75 / 1.0x underlying) | **dead** | lower growth both halves; the Roth is below its Kelly peak (add. 31) |
| Roth: full-weight IBS after a no-pick night | **dead** | 2024-26 negative, placebo 15/50 (add. 31) |
| Roth: 3x ETFs up to 3.0x on all daytime cash | **borderline** | +2.8pp but 2016-20 Sharpe −0.07, worst month −11.7% (add. 31) |
| Roth: TQQQ/SQQQ conviction from the IBS idle cash | **borderline** | +24pp hist but 2016-20 Sharpe −0.10, EH P(DD>30%) 18% (add. 31) |
| Both accounts running the same legs without a wash guard | **dead** | 82% of taxable losses permanently disallowed (add. 31) |
| Loss-aware / look-alike guard with taxable first | **weak** | same-day night-name collisions: Roth still 22% vs 47% with Roth priority (add. 31) |

\* holdout corrected by the verifier (see below).

## Verifier notes (adversarial re-check, 2026-09-28)

Re-ran `roth_opt` end to end: every number in the tables reproduced exactly. Pre-registration stamp
(20:53:38) precedes the first cache (20:54) and the results; A1-A2, B1-B5, C1-C2 and G0-G3 are in the
pre-registered list, G4 is correctly labelled post-hoc. Findings:

1. **Section 0 overstates the live gap (major, corrected).** The executor already cash-bounds the
   Roth's night buys: `phase_close` skips a name when `book.cash - qty*px < floor`, and for the Roth
   `floor = 0` (weights sum to 1.0); `book.cash` is debited by the 3x-ETF fills and by SGOV. So live
   does NOT send orders it cannot pay for; it truncates greedily (picks in `day_ret` order, biggest
   losers first). Also, live parks the idle IBS half in SGOV all day, so at 15:40 that money is not
   cash; M2 treats it as cash. Re-modelled (verifier mechs, post-hoc sensitivity):

   | Roth, CAGR/Sharpe | 3bp 21-23 | 3bp 24-26 | 3bp full | tier full | tier_hi 21-23 | tier_hi 24-26 | tier_hi full |
   |---|---|---|---|---|---|---|---|
   | M3 = live rule (SGOV held, greedy skip) | 39.3/2.38 | 52.0/2.21 | 45.3/2.25/−12 | 37.6/1.94 | 28.1/1.80 | 34.9/1.61 | 31.3/1.67/−12 |
   | M2L = pro-rata on the live 15:40 cash | 42.8/2.67 | 48.9/2.24 | 45.7/2.40/−11 | 38.7/2.09 | 33.1/2.14 | 33.4/1.64 | 33.2/1.84/−12 |
   | M2 (study baseline; needs SGOV sold before 15:40) | 43.8/2.55 | 54.1/2.26 | 48.7/2.36/−10 | 39.7/2.01 | 30.9/1.91 | 34.2/1.57 | 32.5/1.70/−11 |

   So M2 is not a "correctness fix": it is a small sizing refinement (pro-rata instead of greedy;
   M2L beats the live M3 by +1.9pp / +0.17 Sharpe at tier_hi, but trails it in 2024-26 at tier_hi
   and 3bp). Downgrade to SHADOW/optional, not "required before DAILY_ROTH=on". The realistic live
   Roth baseline is ~45% (3bp) / ~31% (tier_hi), not 48.7 / 32.5.
2. **Holdout bug (minor, fixed).** `holdout()` gave A2 exactly A1's pool (both 17.1/1.35) and
   charged V6 1bp. Fixed to A2's all-idle pool at 3bp: A1 16.7/1.33 (+0.03), A2 17.4/1.38 (+0.08);
   NW t of the 2016-20 daily difference 0.71 (A1) / 1.25 (A2) — positive but not significant.
3. **A2 is one-half driven.** NW t of the daily difference: 2021-23 **0.75**, 2024-26 3.47; mean
   gain by year 2021 −0.09, 2022 +0.96, 2023 +0.36, 2024 +1.93, 2025 +1.04, 2026 +2.96 bp/day.
   On the live-like M2L base A2 still adds (3bp 42.8→43.6 / 48.9→51.6, tier_hi 33.1→33.9 /
   33.4→35.4, t 2.58 / 2.33). Placebo matches symbol counts but draws dates from all of 2016-26 and
   is not volatility-matched (V6 fires after down closes). With V6 itself post-hoc, SHADOW stands.
4. **Same-index look-alike risk is avoidable (G4s, post-hoc).** G4 with look-alikes only for
   different-index pairs (SPY/QQQ/IWM/MDY/EEM traded as themselves by the Roth when taxable has not
   touched them in 31 days, else skipped): 3bp taxable 19.8% / Roth 49.0%, permanent disallowance
   0.8% (+0.0% same-index), combined end $335k (G4 $322k, G1 $248k); tier_hi $240k (G4 $235k);
   EH x tier_hi Roth 14.7% vs G4 14.3%. Recommend G4s over G4 in the shadow spec.
5. Costs: as everywhere in the repo, the 3bp/tier/tier_hi dial moves only the night leg (IBS 1bp,
   noise 0.5bp + 0.3bp 3x extra, V6 3bp); under G4 the taxable book is almost cost-insensitive for
   that reason. Guard numbers were not re-run on the M3 live base (G1-vs-G4 gap is ~35pp, far
   larger than the ~3pp base difference).
6. No lookahead found: V6 uses the 15:40 decision (`honest_1540`), noise pos40 is the position after
   the 15:30 decision, IBS/no-pick-night flags are known by 09:15, guards use only past trades.

Verifier verdict: **SHADOW** (unchanged). The M2 item is downgraded from "required fix" to an optional
sizing refinement; G4s replaces G4 as the proposed guard; A2 stays shadow behind V6. Variants tried
incl. verifier sensitivity: 30.


# Addendum 32 — the after-tax frontier for the taxable book: moderate BORDERLINE (verifier downgrade from adopt) (2026-09-28)

## Pre-registration (stamped `Mon Sep 28 20:54:07 PDT 2026`, before any 2024-26 number was computed in this study)

**Question.** Every leg of the brokerage book is short-term. Which sizing profile gives the most
AFTER-TAX growth with P(DD>50% in 5y, edge-halves) <= 5%, is the moderate profile (1.3x, 15% name
cap) still the right next step after tax, and when does moving the QQQ intraday leg (and index IBS
legs) to Section 1256 micro futures pay?

**Mechanisms.**
1. Tax is a ~35% haircut on each year's net gain, paid the next April. Drawdowns are not cut
   (the loss carries forward and only offsets later gains), so after tax the return per unit of
   drawdown risk falls and the growth-optimal leverage should fall too; with a symmetric
   carry-forward the "government as partner" effect partly offsets this. Expect the ranking of
   profiles to hold with every CAGR ~0.6x, and the knee to move toward less leverage only if
   P(DD) rises materially after tax.
2. Paying in April instead of Dec 31 lets ~3.5 months of the tax money compound: worth ~ rate x
   CAGR x 0.3 per year (a few pp at 50-80% pre-tax CAGR).
3. Wash sales: the night leg repeats names and the IBS/intraday legs repeat the same ETFs daily,
   so almost every loss is "disallowed" and rolled into the next lot. Positions close in 1-2 days,
   so it is a timing effect; it only matters across Dec -> Jan (a late-December loss re-bought in
   January moves to next year). Expect a small NEGATIVE effect (losses pushed a year later).
4. Section 1256 (MNQ/MES): 60/40 blend (0.6 x LT + 0.4 x ST), no wash sale, MTM. Lower rate on
   the QQQ noise leg's P&L, but whole contracts (~$61k notional MNQ) and cash parked in a separate
   futures account as margin (it stops earning the book's return). Expect a gain only at large size.

**Tax model (fixed now).** ST rate 35% (sensitivity 25% / 45%), LT 20% (1256 blend = 26%).
Annual netting with ST/LT character; net losses carry forward with character; $3k/yr of net
loss deducted against ordinary income (at the ST rate); tax paid out of the account on the first
session on/after Apr 15 of the next year; the final partial year taxed on the last day (liquidation-
fair, as roth.py). Wash sales from the simulated trade list (forward window: a loss is disallowed
pro rata by shares if the same symbol is bought again within 30 calendar days after the sale; the
disallowed loss is added to that lot's basis). Section 475(f) is a NOTE only.

**Variants (all pre-registered; all reported).**
- Leverage schedule axis (A): reuse add. 29's seven profiles (V7 1.0x; 1.3x gate; 1.3x cap 0.15
  "moderate"; aggressive 1.3x cap 0.20 intraday 0.6; 1.5x cap 0.10; 1.5x cap 0.15; 1.3x no
  conviction) re-run only to obtain daily series and trades for tax. NEW:
  - A5 vol-target: overnight gross g_t = clip(tv / sigma20_{t-1}, 0.5, 1.5), sigma20 = trailing
    20-session std of the 1.0x cap-0.15 book (through the prior session), cap 0.15, conviction 0.5,
    intraday cap from growth.cfg(g_t). tv = median over 2021-23 ONLY of 1.3 x sigma20 (so the
    fit-half median gross is 1.3, the gate). Reverse check: tv fit on 2024-26, judged on 2021-23.
    Placebo: 20 random permutations of the same g_t series (same exposure distribution).
- Conviction axis (C): A5 with conviction 0; moderate with conviction 0; aggressive with conviction 0.
- Tax-model axis (T): T1 Dec-31 payment (roth.py style) / T2 April payment + carry + $3k /
  T3 = T2 + wash-sale deferral; rate 25 / 35 / 45%.
- 1256 migration axis (M): M1 QQQ half of the noise leg -> MNQ, floor(target/contract);
  M2 the same, round to nearest contract; M3 = M1 + IBS legs in SPY/QQQ/IWM/DIA -> MES/MNQ/M2K/MYM
  (floor). Parked margin cash per contract: MNQ intraday 1.5 x day margin, overnight initial for
  IBS; it earns BIL instead of the book. Account sizes $10k / 30k / 60k / 100k / 200k / 300k / 1M
  (constant 2026 dollars, 2026 contract notional).

**Pass bars (fixed now).**
- Frontier: after-tax (T3, 35%) CAGR vs P(DD>50%) of the 5y MC ($3k + $1k/mo) under edge-halves,
  at 3bp and tier_hi. The bound is P(DD>50%) <= 5% at tier_hi EH. The KNEE = the profile with the
  highest after-tax EH tier_hi CAGR inside the bound, stepping back one profile if the last step
  buys < 1pp after-tax EH CAGR per +3pp of P(DD>30%).
- "Moderate is still the right next step" if it sits at or beyond the knee after tax and beats
  the gated 1.3x after tax at 3bp in BOTH halves.
- A5 vol-target "adopt" requires: pre-registered tv from 2021-23; beats the fixed moderate
  (1.3x cap 0.15) on after-tax Sharpe in BOTH halves at 3bp AND tier_hi, reverse-fit also better,
  beats >= 18/20 shuffles on full-period Sharpe, and MC P(DD>30%) not higher. Else shadow/dead.
- 1256 migration "worth doing at size X" if the after-tax gain (net of parked-margin drag and
  granularity) is positive in BOTH halves at X; report the break-even size.

---

## How to run

    # once, under the heavy lock (night_days needs the SIP panel, COVID legs need panel2020; ~20 s):
    PYTHONPATH=. .venv/bin/python -m research.sim.taxable_frontier cache
    # everything else (~40 s, no lock):
    PYTHONPATH=. .venv/bin/python -m research.sim.taxable_frontier

`research/sim/taxable_frontier.py` exports `after_tax(r, rate, lt, trades=, r1256=, pay=, ded=, start=, monthly=, wash=)`
(daily after-tax returns, NET of the accrued tax liability, so tax is charged in the year it is earned and an April
payment is not a drawdown; `info["r_account"]` is the raw balance), `mc_tax(...)` (growth.mc's draws with per-path
yearly tax, April payment, carry-forwards, $3k deduction; reports P(DD) on net equity and on the raw balance),
`replay(...)` (Sim.replay plus the per-lot trade list, reconciles to the sim's daily P&L to 1e-17), `Wash`, `migrate`.
$3k + $1k/month, the add. 29 profiles, 35% ST / 20% LT (1256 = 26%) unless stated.

## Results

**1. Tax mechanics** (3bp; CAGR/Sharpe 2021-23 · 2024-26 · full CAGR/Sharpe/maxDD):

| | pre-tax | T1 Dec 31 | T2 April | T3 + wash | T3 25% | T3 45% |
|---|---|---|---|---|---|---|
| V7 1.0x | 56.9/2.52 · 59.2/2.17 · 58.0/2.33/−12 | 37.4/2.30/−9 | 38.5/2.29/−9 | 37.1 · 39.5 · **38.2**/2.23/−9 | 43.9 | 32.5 |
| moderate 1.3x cap .15 | 75.2 · 97.2 · 85.5/2.42/−18 | 55.3/2.39/−13 | 57.6/2.37/−13 | 49.3 · 66.0 · **57.1**/2.32/−13 | 65.3 | 48.8 |
| aggressive | 83.6 · 105.2 · 93.7/2.39/−20 | 60.6 | 63.4 | 55.1 · 71.8 · **62.9**/2.29/−15 | 71.8 | 53.9 |
| V7 1.0x, tier_hi | 39.6/1.73/−14 | 25.7 | 26.2 | 27.3 · 24.4 · **25.9**/1.64/−11 | 29.9 | 22.0 |
| moderate, tier_hi | 51.4/1.67/−20 | 33.5 | 34.3 | 31.3 · 37.0 · **34.0**/1.59/−14 | 39.0 | 29.0 |

- Tax at 35% takes ~20pp/yr at 3bp (58 → 38 for V7, 85.5 → 57 for moderate): after-tax ≈ 0.66x pre-tax, the
  ranking of profiles unchanged.
- Paying in April instead of Dec 31 is worth +1.1pp (V7) to +2.8pp (aggressive): the tax money compounds 3.5 more
  months. Legal only if the prior-year safe harbor is met (100/110% of last year's tax through withholding or
  estimates); with a fast-growing account that is easy, and it is what T2/T3 assume.
- **Wash sales are a timing cost of −0.3 to −0.5pp/yr.** Trade list (moderate, 3bp): 10,449 night lots on 2,480
  names, 35% of losing night lots re-bought within 30 days; the IBS ETFs (87%) and intraday legs (100%) almost
  always. Inside a year it nets out; across Dec → Jan it pushes losses out: reported ST income was +$4-6k above
  economic in 2023 (+27-67% of that year's gain, depending on profile/cost) and came back in 2024-25. A bad December
  = tax on phantom gain, refunded a year later.
- **Tax lowers drawdowns measured net of the liability** (the government shares losses once the year is up):
  full maxDD −12 → −9 (V7), −18 → −13 (moderate). The raw balance is worse: an April payment right after a good year
  looks like a 10-20% drop (V7 after-tax raw balance maxDD −21%).

**2. The after-tax frontier** (T3 35%; history; edge-halves (EH) after tax; 5y MC $3k + $1k/mo under EH with tax,
P(DD) on net equity, raw balance in brackets):

| profile | cost | after-tax 21-23 · 24-26 · full | EH after-tax CAGR/Sh/DD | MC median | P(DD>30%) | P(DD>50%) |
|---|---|---|---|---|---|---|
| V7 1.0x cap .10 | 3bp | 37.1 · 39.5 · 38.2/2.23/−9 | 16.4/1.10/−15 | $96.9k | 6% (21%) | 0% (0%) |
| 1.3x gate cap .10 | 3bp | 40.7 · 50.2 · 45.2/2.23/−11 | 18.8/1.10/−15 | $103.1k | 13% (37%) | 0% (0%) |
| **moderate 1.3x cap .15** | 3bp | 49.3 · 66.0 · **57.1/2.32**/−13 | 22.8/1.15/−18 | $114.7k | 21% (54%) | 0% (2%) |
| aggressive 1.3x .20 i.6 | 3bp | 55.1 · 71.8 · 62.9/2.29/−15 | 24.5/1.13/−21 | $119.9k | 31% (68%) | 1% (4%) |
| 1.5x cap .10 | 3bp | 42.5 · 57.3 · 49.4/2.18/−12 | 20.1/1.07/−15 | $106.7k | 21% (52%) | 0% (2%) |
| 1.5x cap .15 | 3bp | 51.4 · 76.3 · 62.9/2.26/−15 | 24.4/1.11/−20 | $119.6k | 35% (71%) | 1% (5%) |
| 1.3x cap .10 no conv | 3bp | 34.9 · 49.7 · 41.8/2.28/−11 | 17.8/1.15/−12 | $99.4k | 9% (26%) | 0% |
| A5 vol-target cap .15 (new) | 3bp | 43.6 · 52.4 · 47.8/2.22/−11 | 19.6/1.10/−17 | $106.2k | 18% (47%) | 0% (1%) |
| A5 vol-target no conv (new) | 3bp | 36.2 · 51.6 · 43.4/2.28/−11 | 18.3/1.15/−13 | $101.2k | 11% (33%) | 0% (1%) |
| moderate no conv (new) | 3bp | 41.1 · 65.7 · 52.5/2.33/−13 | 21.4/1.17/−15 | $109.9k | 16% (45%) | 0% (1%) |
| aggressive no conv (new) | 3bp | 40.3 · 66.4 · 52.3/2.20/−14 | 21.3/1.11/−15 | $108.7k | 23% (55%) | 1% (2%) |
| V7 1.0x cap .10 | tier_hi | 27.3 · 24.4 · 25.9/1.64/−11 | 11.4/0.80/−17 | $85.2k | 14% (33%) | 0% (0%) |
| 1.3x gate cap .10 | tier_hi | 28.1 · 28.7 · 28.4/1.55/−12 | 12.2/0.76/−17 | $86.9k | 28% (53%) | 1% (3%) |
| **moderate 1.3x cap .15** | tier_hi | 31.3 · 37.0 · **34.0/1.59**/−14 | **14.2**/0.77/−21 | $91.8k | 42% (72%) | **3% (7%)** |
| aggressive 1.3x .20 i.6 | tier_hi | 33.9 · 39.1 · 36.4/1.54/−16 | 14.9/0.74/−25 | $93.5k | 54% (83%) | 6% (12%) |
| 1.5x cap .10 | tier_hi | 27.6 · 31.5 · 29.4/1.48/−14 | 12.3/0.71/−20 | $87.5k | 41% (69%) | 3% (7%) |
| 1.5x cap .15 | tier_hi | 30.1 · 40.9 · 35.2/1.49/−16 | 14.2/0.71/−24 | $92.3k | 59% (86%) | 7% (14%) |
| 1.3x cap .10 no conv | tier_hi | 22.5 · 28.2 · 25.2/1.54/−12 | 11.1/0.77/−14 | $83.9k | 22% (43%) | 1% (2%) |
| A5 vol-target cap .15 | tier_hi | 27.6 · 30.7 · 29.1/1.53/−13 | 12.4/0.75/−21 | $87.8k | 36% (65%) | 2% (4%) |
| A5 vol-target no conv | tier_hi | 21.8 · 30.2 · 25.8/1.54/−13 | 11.3/0.76/−19 | $84.5k | 27% (52%) | 1% (2%) |
| moderate no conv | tier_hi | 25.2 · 36.9 · 30.7/1.57/−14 | 13.1/0.78/−18 | $88.5k | 35% (63%) | 2% (5%) |
| aggressive no conv | tier_hi | 22.0 · 34.6 · 27.9/1.39/−15 | 11.8/0.68/−23 | $85.3k | 46% (73%) | 4% (8%) |

($10k lump MC in the script output: same ordering, P(DD) within 1-2pp.) Pre-tax EH MC for reference (add. 29
method): moderate tier_hi P(DD>30%) 56%, P(DD>50%) 5%.

- **The knee.** Efficient frontier at tier_hi EH (after-tax CAGR vs P(DD>30%)): V7 (11.4%, 14%) → gate (12.2%, 28%) →
  moderate no conv (13.1%, 35%) → **moderate (14.2%, 42%)** → aggressive (14.9%, 54%). Inside the P(DD>50%) ≤ 5%
  bound (net measure) the highest is **moderate at 3%**; aggressive (6%) and 1.5x cap .15 (7%) are out. The
  pre-registered step-back rule (< 1pp per +3pp of P(DD>30%)) flags the last step, moderate no conv → moderate
  (+1.1pp for +7pp, 0.47 per 3pp): by the letter the knee is **moderate without conviction**. On the raw-balance
  measure moderate is at 7% (out) and moderate no conv 5% (the edge). Both readings say: the 15% name cap is the
  knee; conviction is the marginal, weakest piece after tax.
- **Is moderate still the right next step after tax? Yes.** It beats the gated 1.3x after tax in both halves at 3bp
  (49.3 vs 40.7, 66.0 vs 50.2; pre-tax daily-diff NW t +3.0 / +3.4) and at tier_hi (31.3 vs 28.1, 37.0 vs 28.7; NW t
  +1.5 / +2.3). As built (`daily.profiles.moderate` = cap 0.15 only; 1.0x until the gate opens; conviction in shadow)
  vs live today (POST-HOC descriptive rows, no fitting): after tax 35.0 vs 29.6 / 50.0 vs 38.9 at 3bp, 23.9 vs 21.2 /
  29.5 vs 23.8 at tier_hi; EH tier_hi after tax 11.8% vs 10.2%; MC P(DD>30%) 13% vs 7%, P(DD>50%) 0%.
- **Conviction after tax fails the both-halves test.** It adds 8pp after tax in 2021-23 (49.3 vs 41.1) and +0.3pp in
  2024-26 (66.0 vs 65.7; tier_hi 37.0 vs 36.9). The trade itself: +32bp/trade t 2.35 in 2021-23, +17bp t 1.21 in
  2024-26, +10bp t 0.98 in 2016-20. Not a reason to change anything (it is in shadow), but after tax the
  switch-on case rests on 2021-23; `make review` §7 should also clear a live-edge bar, not only fill hygiene.
- **A5 vol-targeted leverage: dead.** tv = 1.475%/day (fit 2021-23) gives median gross 1.29 in 2021-23 but 1.03 in
  2024-26 (the cap-0.15 book is more volatile lately), so it de-levers in the better half: after tax 43.6 / 52.4 vs
  moderate 49.3 / 66.0 (3bp); daily-diff NW t −1.84 / −2.39. Reverse fit (tv 1.86%) 45.3 / 64.2, still below.
  Placebo: 20 permutations of the same g_t series: real Sharpe 2.34 vs shuffle median 2.39, beats 9/20. Timing adds
  nothing; it is just less average leverage. At tier_hi also below moderate in both halves (27.6 / 30.7 vs 31.3 / 37.0).
- Crash episodes (pre-tax, 3bp): COVID 2020-02-19..03-23 (rebuilt as growth.py) V7 −12.9% (DD −17.5%), gate −14.7%,
  moderate −17.1% (DD −23.0%, worst day −8.6%), aggressive −17.0%, A5 −16.2% (DD −18.6%), 1.5x cap .15 −18.7%.
  2022: all positive (+80% V7 … +134% aggressive; maxDD −10 to −12%). Apr 2-8 2025: +5.5 to +9.0%. Worst month
  −9.6% (V7) to −11.9% (A5); worst day −5.9% (V7), −8.9% (moderate), −13.2% (aggressive).

**3. Section 1256: QQQ intraday half → MNQ** (after-tax CAGR gain in pp vs all-ETF, constant account in 2026 $,
MNQ ≈ $61k notional; full (21-23 / 24-26)):

| account | V7 3bp M1 floor | M2 nearest | M3 +IBS index | M4* hybrid (post-hoc) | ideal (tax only) |
|---|---|---|---|---|---|
| $10k-60k | −3.53 (no contract: leg dropped) | −3.53 | −3.6 to −5.1 | 0.00 (stays ETF) | +0.37 |
| $100k | −3.53 | +2.97 (1 contract = 1.6x the target: leverage, not tax) | −4.64 | 0.00 | +0.37 |
| $200k | −0.30 | −0.29 | −1.68 | **+0.36 (+0.52/+0.19)** | +0.37 |
| $300k | −1.38 | +0.79 | −2.54 | +0.24 (+0.34/+0.13) | +0.37 |
| $1M | +0.35 | +0.34 | −1.00 | +0.44 (+0.63/+0.23) | +0.37 |

Moderate (intraday cap 0.6 → QQQ half ≤ 0.3x): ideal +0.31; hybrid 0 below $300k, +0.15 (+0.29/−0.02) at $300k,
+0.18 (+0.35/−0.02) at $1M — fails the 2024-26 half. tier_hi slightly smaller everywhere.

- The ceiling is **+0.3-0.4pp/yr**, not add. 25's +1.6pp: in the book the QQQ half runs at ≤0.375x of equity
  (0.3x moderate), not the 2x standalone leg. One MNQ needs the QQQ-half target ≥ $61k, i.e. an account of
  ~$165k (V7) / ~$200k (moderate), not "$30k per contract". Below that it is zero at best.
- Parked futures margin (1.5x day margin ≈ $1.6k per MNQ; 4x in the stress row) earns BIL instead of the book:
  −0.3 to −0.7pp at the sizes where one contract fits. The IBS index legs (M3) never pay: 7% overnight initial margin
  parked and most IBS picks are sector ETFs with no micro future.
- **Verdict: not before ~$200k-300k; then only as "whole contracts + remainder in QQQ" (M4, post-hoc = SHADOW
  spec), worth ~+0.2-0.4pp/yr.** Revisit when the brokerage book passes $200k.

**4. Section 475(f) — NOTE for the CPA, not modelled.** With trader tax status and a timely election (by the prior
year's return due date; for a new taxpayer entity within 75 days), all gains and losses on securities in the
business are ordinary: wash sales stop applying (the Dec → Jan shift above disappears), the $3k loss cap goes
away (a losing year offsets wages), positions are marked to market Dec 31. Rate on gains is unchanged (already all
ST at ordinary rates), so for this book it is mostly the loss treatment and the paperwork; it also converts any
1256 futures in the business to ordinary, removing the 60/40 benefit unless they are held outside it. Trader
status needs substantial, frequent, continuous trading (this book qualifies on frequency; the IRS tests it).

## Verdict

- **Moderate profile (15% name cap): ADOPT as the next step, after tax** (study verdict; the verifier below
  downgrades it to BORDERLINE, and addendum 39 on raw prices prefers the as-built 1.0x cap .15) (pre-registered question, both halves at
  3bp and tier_hi after tax, P(DD>50%) ≤ 5% at tier_hi EH on net equity; as built at 1.0x it is 0%). It is the knee:
  +5.4 / +11.1pp/yr after tax in the halves at measured costs vs live today, +1.6pp under EH at tier_hi. Enabling it
  stays conditioned on `make review` §2b (open sells near 0bp), as in add. 29.
- Beyond the knee (aggressive, 1.5x cap .15): after tax +0.7pp EH for +12-17pp P(DD>30%) and P(DD>50%) 6-7%: no.
- Vol-targeted leverage (A5): DEAD. Conviction after tax: 2021-23-only; keep in shadow, add a live-edge bar.
- MNQ migration: nothing below ~$200k; hybrid SHADOW spec for later (+0.2-0.4pp/yr).
- Tax planning facts for the book: April payment (with safe harbor) +1-3pp/yr vs paying at year end; wash sales
  −0.3 to −0.5pp/yr, concentrated in a losing December.

## Do NOT redo

| idea | verdict | why |
|---|---|---|
| vol-targeted overnight gross (tv / trailing 20d book vol, 0.5-1.5x) | dead | de-levers in 2024-26 (median 1.03x), −1.8/−2.4 NW t vs fixed 1.3x cap .15, placebo 9/20 (add. 32) |
| QQQ noise half → MNQ below ~$200k | dead | one MNQ ≈ $61k > the leg's 0.3-0.375x of equity; floor drops the leg (−3.5pp), ceiling is +0.3pp (add. 32) |
| IBS index legs → MES/MNQ/M2K/MYM | dead | always negative: 7% overnight margin parked, remainder lost, most picks are sector ETFs (add. 32) |
| aggressive / 1.5x profiles for the taxable book after tax | dead | +0.7pp EH after tax for +12-17pp P(DD>30%), P(DD>50%) 6-7% at tier_hi EH (add. 32) |

## Verifier notes (adversarial pass, 2026-09-28)

- **Reproduced.** A fresh re-run (profile cache rebuilt from scratch, ~32 s) matches every number above exactly.
  The replay matches `Sim.replay` exactly (max |diff| 0.0), and the per-lot trade list sums to the leg P&L to
  about 3e-17. The vol-target schedule has no lookahead (sigma20 is shifted one day and tv is fit on 2021-23 only).
  Costs are reported at 3bp and tier_hi. Tier is not reported for the frontier; the add. 29 tier numbers still apply.
- **Placebo added by the verifier, cap 0.15 vs 0.10.** Scripts: `scratchpad/verify_tf/checks.py`. The name cap mostly
  changes exposure: the per-name fraction rises on 76% of nights, by 1.35x on average. So I took the day-by-day
  cap-0.15/0.10 exposure ratio, shuffled it across days (20 draws), and applied it to the cap-0.10 book at 1.3x,
  3bp. That keeps the frequency and exposure distribution and randomises the timing. Placebo median 81.5% CAGR
  (max 86.6%) and Sharpe 2.21, against the real 85.5% and 2.42. The real book beats 19/20 on CAGR and 20/20 on
  Sharpe; on halves CAGR it beats 19/20 and 17/20. Most of the gain over the gate (68.3%) is simply more money
  deployed, but the timing is not luck. The daily diff vs the gate survives dropping the 10 best days
  (4.2 -> 2.5 bp/day, NW t 4.5 full).
- **Why the verdict drops from ADOPT to BORDERLINE:**
  1. The pre-registration was not blind for the moderate question. Add. 29's pre-tax 2021-23 and 2024-26 numbers
     for these same profiles were published earlier the same day, and after-tax is close to a monotone ~0.66x
     transform. So "moderate beats the gate after tax in both halves" confirms add. 29. It is not an independent
     out-of-sample result.
  2. The bound depends on the measure. For moderate 1.3x at tier_hi EH, P(DD>50%) is 3% on net-of-liability equity
     but 7% on the raw account balance, and 5% pre-tax by the add. 29 method. The pre-registration did not say which
     measure; the raw balance is what the account will show. Taken literally, the pre-registered step-back rule also
     puts the knee at moderate without conviction, not moderate.
  3. The "as built" 1.0x rows (the thing that would actually be switched on) are POST-HOC descriptive rows.
  4. There is no 2016-20 holdout for the book's night leg, and no 2016-20 test of the cap either.
  None of this is a bug, and the evidence for the 15% cap is positive (both halves, t 3 at 3bp and 1.5-2.3 at
  tier_hi, placebo 19/20). But it does not clear every bar for a fresh "adopt". Enabling `moderate` should stay
  where add. 29 put it: gated on `make review` §2b open-sell costs. This addendum is after-tax support for that
  step, not a new adoption.
- **Minor, not fixed.** The wash-sale window only looks forward (the rule also covers buys in the 30 days before a
  sale). Being timing-only, it probably understates the Dec -> Jan shift a little. Section 1256 is modelled on
  QQQ as a proxy for MNQ.
- Unchanged: A5 vol-target DEAD, IBS index legs to futures DEAD, MNQ below ~$200k DEAD, hybrid MNQ SHADOW
  (post-hoc), aggressive and 1.5x cap .15 dead after tax.


# Addendum 33 — scheduled macro events (FOMC / CPI / NFP / claims): F3 FOMC-eve QQQ filler ADOPT (small; taxable only, add. 39), rest dead (2026-09-28)

    PYTHONPATH=. .venv/bin/python -m research.sim.macro_events          # (first run builds the holdout cache under the heavy lock)
    PYTHONPATH=. .venv/bin/python -m research.sim.event_calendar        # calendar sanity print

Calendars: `research/sim/event_calendar.py` (reusable): FOMC scheduled decision days 2016-2026
(federalreserve.gov, unscheduled 2020 actions kept apart and never used), CPI and Employment
Situation release days 2015-2026 (BLS release archives, incl. the 2025 shutdown reschedules),
weekly claims (Thursday, Wednesday when Thursday is a federal holiday), monthly opex and triple
witching by rule. Every date was public well before 15:40/15:50 ET the prior day.

## Pre-registration (stamped Mon Sep 28 20:54:52 PDT 2026, before any 2024-26 number was computed)

Why events are different from the calendar effects addendum 27 killed: those had no mechanism.
Scheduled macro releases do: (i) the announcement premium (Savor & Wilson 2013: market and
high-beta returns are concentrated on CPI/NFP/FOMC days, compensation for risk resolved at a
known time), (ii) the pre-FOMC drift (Lucca & Moench 2015: SPX +~49bp in the 24h before the
14:00 statement, much of it overnight/morning; reported weaker after 2015), (iii) scheduled
shocks create intraday trends (14:00 FOMC, the 08:30 gap) that a noise-band breakout rule may
harvest, or whipsaws that it may lose. The night leg (high-vol losers, close -> next open) and
IBS (open d+1 -> open d+2) both span the 08:30 release when the release is on the exit morning.

Timing conventions (event day e, a trading day):
- night leg keyed d spans a release on e if e is the next trading day after d (08:30 inside close->open)
- IBS keyed d (bought open d+1, sold open d+2) spans a release on e if e = d+2 (08:30 inside the hold's last night)
- noise leg on day e trades the post-release session (08:30 events) or the 14:00 FOMC shock
- "FOMC eve" = the trading day before a scheduled FOMC decision day

Variants (every one is reported):

Q1 standalone pre-FOMC leg (the at-most-one event leg)
- F1 SPY close(e-1) -> open(e) with the night leg's UNUSED cash on FOMC eves (auction to auction; fits taxable and Roth, 1bp/side like the filler)
- F2 SPY close(e-1) -> 13:59(e) (Lucca-Moench window, minute bars; standalone only: holding into the day takes daytime margin the noise leg uses)
- F3 QQQ close(e-1) -> open(e), as F1

Q2 night-leg sizing on nights that span a release
- N1 CPI or NFP on the exit morning: night x0.5
- N2 CPI or NFP on the exit morning: night x1.5 (taxable: Reg T room; Roth: only up to the leg's own unused cash, 1.0x never exceeded)
- N3 claims-only Thursday mornings (no CPI/NFP): night x0.5
- N4 FOMC eve (night into the decision morning): night x1.5

Q3 IBS across a release
- B1 IBS positions whose last night spans CPI/NFP: x1.5 (taxable only; the Roth has no room)

Q4 intraday noise leg on event days
- I1 FOMC days: noise off
- I2 FOMC days: vol-target leverage x1.5, still capped at the V7 margin cap (0.75 taxable / 1.5 Roth)
- I3 CPI/NFP days: noise off
- I4 CPI/NFP days: leverage x1.5, capped as I2

Controls: placebo = the same action on random non-event days, same count, matched by weekday and
by SPY 20d-realised-vol tercile known at d-1, 1000 draws (linear leg-scaling approximation, applied
identically to the real flags for the percentile). Leg-level: event-day minus non-event-day mean of
the affected leg, Newey-West t (lag 5).

Pass bar (a variant is "adopt" only if ALL hold):
1. V7 book (Sim.replay, $3k + $1k/21 sessions) Sharpe AND CAGR up in BOTH 2021-23 and 2024-26, at 3bp and at tier_hi;
2. same sign in the 2016-20 holdout (returns book as in regime_tilt.holdout; night leg only in 2020);
3. full-sample book dSharpe above the 95th percentile of the matched placebo;
4. leg-level event effect |t| >= 2 in the direction of the action;
5. edge-halves and 5y MC P(DD>50%) no worse than V7; Roth book not worse.
Shadow: passes 1 and 3 but not 2 or 4. Borderline: passes 1 at 3bp only. Otherwise dead.
Standalone F-legs: mean per trade > 0 in 2016-20, 2021-23, 2024-26, NW t >= 2 full, above the 95th placebo pct, and the book bar 1.

## Results (all 12 pre-registered variants + 1 sensitivity; runtime ~13 s after a 9 s locked cache build)

Event counts (2021-02..2026-09 / 2016-02..2020-12): CPI/NFP nights 134 / 118, claims-only Thursday
nights 275 / 241, FOMC eves 45 / 38, CPI/NFP days 131 / 116.

### Leg-level: event days minus other days (bp of equity per day, Newey-West t, lag 5)

| leg | event | 2021-23 | 2024-26 | all | 2016-20 |
|---|---|---|---|---|---|
| night (book) | CPI/NFP morning | +18.7 (t 2.44) | +9.0 (t 0.74) | +14.0 (t 1.99) | 2020 rebuild +19.6 (t 0.69, n 22) |
| night (book) | claims-only Thursday | −11.1 (t −1.50) | −6.5 (t −0.69) | −8.9 (t −1.50) | — |
| night (book) | FOMC eve | +15.0 (t 1.16) | +18.8 (t 0.79) | +16.9 (t 1.26) | 2020 rebuild +81.7 (t 2.32, n 6) |
| IBS (book) | last night spans CPI/NFP | +8.6 (t 1.25) | +9.6 (t 1.21) | +9.0 (t 1.74) | unit −7.6 (t −0.26) |
| noise (book) | FOMC day | −4.3 (t −0.30) | −1.7 (t −0.06) | −3.1 (t −0.20) | −2.2 (t −0.53) |
| noise (book) | CPI/NFP day | −8.1 (t −0.81) | **+37.8 (t 2.22)** | +14.0 (t 1.41) | +0.2 (t 0.06) |

Variance: event-night sd of the night leg is the same as other nights (60 vs 61bp in 2021-23,
94 vs 102bp in 2024-26), so the "cut risk on release nights" idea has nothing to cut. The night
leg EARNS more across CPI/NFP (the announcement premium sign) but it is concentrated in 2021-23.

### Q1 standalone pre-FOMC legs (per trade, net 3bp/side)

| leg | 2016-20 | 2021-23 | 2024-26 | all, t (trades) | vs other nights, NW t | placebo pct |
|---|---|---|---|---|---|---|
| F1 SPY close → open | +13.8 (38) | +11.8 (24) | +7.3 (22) | +11.5, 2.39 | +14.1, 2.80 | 99 |
| F2 SPY close → 13:59 | +13.3 | +15.5 | +3.2 | +11.3, 1.64 | +11.9, 1.65 | 78 |
| **F3 QQQ close → open** | **+25.3** | **+19.4** | **+20.2** | **+22.3, 3.26** | **+23.9, 3.39** | **100** |

F3 by year (bp, n): 2016 −1.6 (7), 2017 +19.8, 2018 −1.4, 2019 +24.5, 2020 +90.0 (7), 2021 −18.4,
2022 +76.2, 2023 +0.4, 2024 +27.6, 2025 +10.4, 2026 +23.5 (6). Hit rate 68% vs 52% on other nights;
median +13.2bp; mean without the top 3 +15.0bp; worst −111bp, best +221bp. Other non-event QQQ
nights net of 6bp: −0.9bp. The Lucca-Moench drift survives in its OVERNIGHT part (F1/F3); the day
part to 13:59 has faded in 2024-26 (F2 +3.2bp, placebo pct 78).

### Book effect: V7 dollar replay ($3k + $1k/21 sessions), CAGR/Sharpe/maxDD %

| variant | 3bp 2021-23 | 3bp 2024-26 | tier 2021-23 | tier 2024-26 | tier_hi 2021-23 | tier_hi 2024-26 | 2016-20 HO | Roth b1 3bp / tier_hi | placebo pct |
|---|---|---|---|---|---|---|---|---|---|
| V7 base | 56.9/2.52/−10 | 59.2/2.17/−12 | 48.6/2.23/−10 | 46.4/1.80/−13 | 42.0/1.99/−10 | 37.1/1.51/−14 | 15.5/1.05/−21 | 49.3/2.27 · 31.4/1.58 | — |
| F1 SPY FOMC-eve filler | 57.5/2.55/−9 | 59.5/2.17/−12 | 48.9/2.25/−10 | 46.6/1.80/−13 | 42.3/2.00/−10 | 37.0/1.51/−14 | 15.8/1.07/−21 | 49.6/2.28 · 31.4/1.58 | 98 |
| **F3 QQQ FOMC-eve filler** | 57.7/2.55/−9 | 59.7/2.18/−12 | 49.1/2.25/−9 | 46.6/1.80/−13 | 42.4/2.00/−10 | 37.2/1.51/−14 | 16.1/1.08/−21 | 49.7/2.29 · 31.6/1.59 | 99 |
| N1 night ×0.5 CPI/NFP | 51.6/2.35/−9 | 56.1/2.13/−12 | 44.5/2.10/−10 | 44.2/1.77/−13 | 39.0/1.88/−10 | 35.4/1.48/−13 | 15.3/1.04/−20 | 45.6/2.18 · 29.2/1.52 | 2 |
| N2 night ×1.5 CPI/NFP | 60.8/2.62/−10 | 62.7/2.20/−13 | 50.6/2.27/−11 | 48.9/1.83/−14 | 44.9/2.07/−11 | 38.2/**1.50**/−15 | 15.7/1.05/−21 | 50.9/2.30 · 32.4/1.60 | 98 |
| N3 night ×0.5 claims Thu | 58.4/2.63/−10 | **57.5**/2.19/−12 | 50.4/2.35/−11 | 45.8/1.84/−13 | 44.6/2.13/−11 | 37.6/1.57/−13 | 17.3/1.18/−18 | 49.0/2.35 · 32.9/1.71 | 100* |
| N4 night ×1.5 FOMC eve | 58.1/2.55/−10 | 60.9/2.18/−12 | 49.3/2.25/−10 | 47.8/1.81/−13 | 42.7/2.00/−11 | 38.1/1.52/−14 | 15.8/1.06/−21 | 49.6/2.27 · 31.6/1.58 | 67 |
| B1 IBS ×1.5 spans CPI/NFP | 58.6/2.56/−10 | 60.5/2.20/−12 | 49.9/2.26/−10 | 47.5/1.83/−13 | 43.7/2.03/−11 | 38.1/1.54/−14 | 15.3/**1.04**/−21 | n/a (no room) | 99 |
| I1 noise off FOMC day | **56.7**/2.53/−9 | 61.1/2.23/−12 | 48.1/2.23/−10 | 47.6/1.84/−13 | 41.9/1.99/−10 | 38.1/1.55/−14 | 15.5/1.05/−21 | 49.8/2.30 · 31.9/1.61 | 76 |
| I2 noise lev ×1.5 FOMC | 56.9/2.52/−10 | 59.2/2.17/−12 | 48.6/2.23/−10 | 46.4/1.80/−13 | 42.0/1.99/−10 | 37.0/1.51/−14 | 15.6/1.05/−21 | 49.1/2.26 · 31.2/1.57 | 22 |
| I3 noise off CPI/NFP day | 54.7/2.47/−10 | 54.4/2.09/−13 | 46.8/2.19/−11 | 41.9/1.71/−14 | 40.7/1.95/−11 | 32.8/1.41/−14 | 15.0/1.04/−21 | 45.0/2.15 · 27.5/1.44 | 9 |
| I4 noise lev ×1.5 CPI/NFP | 56.9/2.52/−10 | 59.4/2.18/−12 | 48.5/2.23/−10 | 46.5/1.80/−13 | 42.1/1.99/−10 | 37.1/1.51/−14 | 15.5/1.05/−21 | 50.4/2.29 · 32.4/1.60 | 14 |

(*) N3's weekday-matched placebo is degenerate: claims come out nearly every Thursday, so after
excluding the flagged nights only 7 Wednesday nights remain in the pool. Vol-only placebo
(sensitivity): pct 97. N3 is a Wednesday-night rule in disguise (day-of-week: dead, add. 27),
and it cuts 2024-26 CAGR at 3bp (−1.7pp).

dSharpe 2021-23 / 2024-26: F3 +0.029/+0.006 at 3bp, +0.018/+0.002 at tier_hi; F1 +0.012/−0.002 at
tier_hi; N2 +0.080/−0.009 at tier_hi; B1 +0.045/+0.028 at tier_hi, holdout −0.011.
I2/I4 do almost nothing: the V7 intraday cap (0.75) binds on nearly every day, so ×1.5 on the
vol-target leverage cannot add exposure; the only honest way to add intraday size on release days
would be to take it from IBS/conviction (regime_tilt T2-style), not pre-registered here.

### Stress (tier_hi): edge-halves, 5y block-bootstrap MC (21-day blocks), episodes

| book | EH CAGR/Sh/DD | MC $3k+$1k/mo median | P(DD>30%) | P(DD>50%) | $10k lump median | worst day | worst month | 2022 bear | Aug 2024 | Apr 2-8 2025 | COVID 2020 (HO) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| V7 base | 17.5/0.89/−20 | $99,748 | 22.9% | 0.4% | $22,583 | −6.0% | −10.3% | +34.2% | −3.0% | +6.0% | −12.9% |
| F3 | 17.7/0.89/−20 | $100,125 | 22.1% | 0.4% | $22,693 | −6.0% | −10.3% | +36.1% | −2.8% | +6.1% | −12.9% |
| F1 | 17.6/0.89/−20 | $99,888 | 22.5% | 0.4% | $22,655 | −6.0% | −10.3% | +35.4% | −2.9% | +6.0% | — |
| N2 | 18.3/0.90/−20 | $101,359 | 25.3% | 0.6% | $23,156 | −6.0% | −11.4% | +36.3% | −3.8% | +5.5% | −13.2% |
| B1 | 18.1/0.91/−19 | $101,046 | 23.1% | 0.4% | $23,026 | −6.0% | −10.5% | +31.1% | −3.2% | +8.0% | — |

EH extra return vs base (taxable, tier_hi): F3 +0.09%/yr, F1 +0.04, N2 +0.74, B1 +0.53.
Roth b1 extra: F3 +0.29%/yr at 3bp (+0.13 at tier_hi; EH-halved +0.14 / +0.07); N2 +1.09 / +0.78.

## Verdict

- **F3 (QQQ close → open with the night leg's unused cash on FOMC eves): passes every
  pre-registered bar — adopt, but it is small.** +20-25bp per trade in all three periods, NW t 3.4,
  placebo pct 100, both halves up at 3bp and tier_hi (the 2024-26 tier_hi margin is thin: +0.002
  Sharpe / +0.10pp CAGR), holdout +0.033 Sharpe, Roth up, EH and MC no worse. It uses only cash the
  night leg did not use (no margin, Roth-legal, auction to auction). Worth ~0.1-0.3%/yr of the book:
  8 nights a year on ~27% of equity. Negative years exist (2016, 2018, 2021).
- F1 (SPY instead of QQQ): borderline — same sign, half the size, 2024-26 tier_hi slightly negative. F3 dominates.
- F2 (the Lucca-Moench window into 13:59): dead — the day part has faded (2024-26 +3.2bp, placebo pct 78).
- N2 (night ×1.5 on CPI/NFP mornings): borderline — right sign (announcement premium), placebo
  pct 98, but tier_hi 2024-26 Sharpe −0.009, leg t 0.74 in 2024-26, P(DD>30%) 22.9 → 25.3%.
- B1 (IBS ×1.5 across CPI/NFP): shadow at most — both halves up at every cost, placebo pct 99,
  but the 2016-20 holdout is negative (unit IBS −7.6bp) and leg t 1.74. Taxable only.
- N1, N3, N4, I1-I4: dead (see rows below).

## Do NOT redo

| idea | verdict | why |
|---|---|---|
| Cut the night leg on CPI/NFP nights (×0.5) | dead | the night leg earns MORE across 08:30 releases (+14bp/day, t 2.0) with the same variance; Sharpe falls both halves |
| Night ×1.5 on CPI/NFP nights | borderline | right sign, placebo 98th pct, but gone in 2024-26 at tier_hi (−0.009 Sharpe), more DD>30% |
| Night ×0.5 before weekly claims (Thursdays) | dead | really a Wednesday-night rule (claims ≈ every Thursday); cuts 2024-26 CAGR |
| Night ×1.5 on FOMC eves | dead | book up but placebo pct 67: indistinguishable from 1.5x on random nights |
| Pre-FOMC drift in the day session (close → 13:59) | dead | faded after 2023 (+3bp), placebo pct 78; the overnight part carries it |
| Noise leg off / up on FOMC days or CPI/NFP days | dead | FOMC-day noise ≈ 0 effect; turning it off on CPI/NFP days costs 2-5pp CAGR; ×1.5 is a no-op under the 0.75 margin cap |
| IBS ×1.5 when its last night spans CPI/NFP | shadow | both halves up but 2016-20 holdout negative, t 1.7 |

## F3 live spec (proposed; NOT implemented — nothing that trades live was touched)

- Rule: on the trading day before a scheduled FOMC decision day (`event_calendar.fomc_dates()`,
  published a year ahead; unscheduled actions never count), after the night leg is sized at 15:50,
  put spare = night budget − planned night notional into floor(spare / QQQ price) QQQ at the close
  auction; sell at the next open auction with the night exits. Same in the Roth (cash only, never
  over 1.0x). At $3k this is often 0-1 share; that is in the replay.
- Config key: `night.fomc_eve_filler: {enabled: false, symbol: QQQ}`.
- Log per event: date, spare $, shares, close print, open print, gross bp, cost vs the auction prints.
- Self-score: running mean net bp vs the ~−1bp baseline of other QQQ nights; switch off if the
  mean is below 0 after 16 events (2 years).

## Verifier notes (adversarial check, 2026-09-28)

- The full script was re-run from the cache and every number matched (20 s). An independent recompute of
  F3 from `etf()` in `scratchpad/me_verify.py` also matched: n=84 FOMC eves, gross +28.3bp (median +19.2)
  vs +4.4bp on other QQQ nights. Bootstrap 95% CI of the gross mean is +15.6..+41.9bp.
- Lookahead: none found. The calendar holds scheduled decision days only; the 2018/2020/2024 Thursday
  meetings are correct, and the cancelled 2020-03-18 meeting is excluded, which was known on Mar 15. The
  signal is the calendar alone, and the spare cash is fixed at the 15:50 sizing (`Sim.day_pnl` filler).
  The trades are whole shares at close/open prints, with no margin. The Roth path goes through
  `roth_day` -> `day_pnl` at 1.0x.
- Robustness: the effect shows up on every index tested, per-trade gross on FOMC eves vs other nights:
  SPY +17.5 vs +3.4, IWM +18.7 vs +5.7, SMH +44.6 vs +10.6, TQQQ +83.1 vs +11.6. Against random other
  Tuesday nights (81 of 84 eves are Tuesdays) the percentile is 99.6. Dropping the 7 eves that also
  span a CPI/NFP morning leaves +27.6bp gross.
- Weak spots (these do not break the pre-registered bar):
  - Concentration. Without 2020 and 2022 the gross mean is +15.2bp (n=69): +9bp net at 3bp, about 0 at
    tier_hi (7.5bp/side).
  - The largest trade (2020-11-04, +227bp) is the post-election night, not an FOMC effect.
  - Two nights before FOMC is also elevated (+13.2bp), so part of the drift is a broader pre-FOMC week effect.
  - The 2024-26 tier_hi book margin is +0.002 Sharpe / +0.10pp CAGR. It passes on sign, but economically
    it is noise-level. At the live cost (~0bp) the margin is clearly positive.
- Prior work: the unconditional index filler was ruled dead in add. 16. F3 is a pre-registered,
  mechanism-backed conditional subset of it, so it is not a redo, but the do-NOT-redo row should say so.
- Minor: the caveats say "11 pre-registered tests"; the list has 12. The verifier's extra sensitivity
  runs (4 other ETFs, overlap exclusion, ex-2020/22, 2-nights-before, random-Tuesday placebo, bootstrap)
  bring the total to 21 variants.
- Verdict upheld: **F3 adopt (small)**. Recommend enabling it with the per-event log and the pre-registered
  auto-disable rule. Expected value is about $5-15/yr at current size and about $60-90/yr at $100k.


# Addendum 34 — index mechanics (S&P 500 changes, Russell recon, LETF rebalancing, month-end flows): dead / borderline (P2 downgraded from shadow) (2026-09-28)

## Pre-registration (stamped `Mon Sep 28 20:53:38 PDT 2026`, before any 2024-26 number was computed)

Four structural, ticker-agnostic flows. All variants below are fixed now; everything added
after results is POST-HOC (max verdict SHADOW). Costs everywhere: 3bp/side flat ("measured"),
tier and tier_hi (single names by book.cost_bps; ETFs 1bp/3bp as in add. 27). Periods: 2016-20
holdout (where data exists), 2021-23, 2024-26; fit on one half, judge on the other, both ways.
t-stats day-clustered (events on the same date averaged first) or Newey-West (daily series).

**Common pass bar (every question).** A variant is a candidate only if (a) net of tier cost it is
positive in 2021-23 AND 2024-26 (and not negative in 2016-20 where data exists), (b) it beats its
matched placebo in >= 80% of seeds in both halves, (c) day-clustered |t| >= 2 on the pooled
2021-26 sample, and (d) added to V7 (growth.V7, Sim.replay) it raises Sharpe in both halves at 3bp
AND at tier_hi, with edge-halves (growth.eh) and 5y MC P(DD>30%) not worse. "adopt" needs all four.

### Q1. S&P 500 additions / deletions (the index-fund close-auction flow)
Mechanism: index funds must buy adds / sell deletes at the close of the last session before the
effective date (T). Announcement (A) is after the close; its date is the S&P DJI press release
date (Wikipedia "Historical components of the S&P 500" changes table, `ref |date=`/URL date).
First tradable auction after the news: close of A+1. T = last session before the effective date
(volume check between the two candidate sessions, since Wikipedia mixes the two conventions;
the true date is in the press release, so this is data cleaning, not lookahead).
Only names with bars on the event days count (acquired deletions drop out naturally; delisted
later names count). Placebo: for each event, random names from the same vol20 decile and price
> $5 on the same dates, 50 seeds. Returns are raw (also shown SPY-adjusted).
- S1 additions run-up: long at A+1 close -> T close (auction). Roth-able.
- S2 additions post-effective reversal: SHORT at T close -> cover T+5 close. Taxable only.
- S3 deletions overnight reversal: long at T close -> T+1 open (night-leg timing).
- S4 deletions 5-day reversal: long at T close -> T+5 close.
- S5 deletions pre-effective selling: SHORT at A+1 close -> T close. Taxable only.
Prior: the effect shrank after ~2010 (Patel & Welch 2017; Greenwood & Sammon 2022 find the
addition effect ~0 recently). Expect dead.

### Q2. Russell reconstitution
Membership lists are not in the repo and the panel has no shares outstanding, so a market-cap
rank crossing cannot be computed without lookahead or a data source we do not have.
**Declared untestable for single names.** Ticker-agnostic descriptive check only (not eligible
for adoption, n = 10-11 events): IWM minus SPY on recon day (fourth Friday of June; public
calendar) close T-1 -> close T and close T -> open T+1; and the night leg's recon-day trades.
- R1 IWM-SPY recon-day close->close;  R2 IWM (and IWM-SPY) recon close -> next open.
Verified: FTSE Russell goes semi-annual from 2026 (June 26 2026; December 11 2026, rank day Oct 30).

### Q3. Leveraged-ETF rebalancing flow (build on add. 27 R3)
R3 killed sign-of-day last-half-hour momentum, including the > 2 sigma version (sign flips).
Here only the FLOW SIZE is conditioned on: |instrument move prev close -> 15:30| > 2%
(LETF rebalance notional ~ L(L-1) x AUM x day return), and only as a modification of existing legs:
- L1 noise leg: on flow days, flatten the noise position at 15:30 instead of holding to the close
  (per instrument, QQQ and SMH, own move). Pass if V7 Sharpe rises in both halves. (If the flow is
  momentum into the close L1 hurts; R3's sign flips suggest it may not.)
- L2 night leg entry: on days QQQ prev close -> 15:30 <= -2% (LETF selling into the close auction
  the night leg buys at), night per-name fraction x1.5 (cap 0.15/name). Pass as above.
Mechanism diagnostics reported: QQQ/SMH 15:30->close and close->next open on flow days vs others.

### Q4. Month-end pension rebalancing
Mechanism: balanced funds rebalance to fixed weights near month end; large equity outperformance
vs bonds month-to-date -> equity selling into the last days (Harvey, Mazzoleni, Melone 2025).
Signal at the IBS decision (d close): rel = SPY MTD - TLT MTD (both through d's close; month-to-date
from the prior month's last close). Window: IBS trades whose entry (d+1 open) is one of the last
3 sessions of the month. Threshold fixed: |rel| > 3%.
- M1 IBS sizing: in the window, IBS leg x1.5 when rel < -3% (pension buying), x0.5 when rel > +3%.
- M2 IBS gate: in the window, skip IBS trades when rel > +3% (idle money to BIL).
- M3 mechanism test (standalone, taxable): SPY d+1 open -> last-session close, long if rel < -3%,
  short if rel > +3%, flat otherwise (signal at the close 4 sessions before month end).
Placebo: same number of windows drawn from random non-month-end 3-day windows with the same sign
distribution, 200 seeds.

Variants pre-registered: 5 + 2 + 2 + 3 = 12.

---

## How to run

```
# heavy lock, once (~30 s total): S&P event windows + vol-decile placebo pools; V7 night picks; 2020 rebuild
PYTHONPATH=. .venv/bin/python -m research.sim.index_mechanics_data
PYTHONPATH=. .venv/bin/python -m research.sim.index_mechanics_data night
PYTHONPATH=. .venv/bin/python -m research.sim.index_mechanics_data d2020
# no lock, ~20 s
PYTHONPATH=. .venv/bin/python -m research.sim.index_mechanics q1 q2 q3 q4 q5 q6 q7
```
`research/sim/index_mechanics.py`, `research/sim/index_mechanics_data.py` (hardcoded S&P change
list with press-release dates, Russell recon calendar). Book = V7 as shipped (growth.V7, 1.0x,
cap 0.10, max_corr 0.7), Sim.replay $3k + $1k/21 sessions; V7 reproduces 47.5/1.99/−13 at tier.

## Results (all 12 pre-registered variants + 3 post-hoc)

### Q1 S&P 500 changes: dead

234 changes 2015-09 → 2026-09 with a press-release date (median announcement → effective 7 days,
3 sessions from A+1 to T); 188 adds and 132 deletes have bars (deletes are mostly acquisitions,
which stop trading; ~9% of adds missing are ticker renames). T-day volume is 28x ADV (adds),
14x (dels): the auction flow is real. **The price effect is at the announcement gap, which is
not tradable** (A close → A+1 open, adds): +48bp 2016-20, +271bp 2021-23, +517bp 2024-26.

Per event, bp, net of cost (t = day-clustered, tier; placebo = beats same-vol-decile random names, 50 seeds):

| variant | 2016-20 tier | 2021-23 3bp / tier / tier_hi | 2024-26 3bp / tier / tier_hi | t (21-23 / 24-26) | placebo 16-20 / 21-23 / 24-26 |
|---|---|---|---|---|---|
| S1 adds run-up A+1c→Tc long | −54.7 (n86) | −4.6 / −9.0 / −14.1 (n42) | +122 / +118 / +113 (n39) | +0.62 / +0.35 | 0% / 82% / 64% |
| S2 adds post T→T+5 SHORT | −123 (n98) | +64 / +60 / +55 (n47) | +53 / +49 / +44 (n42) | +0.87 / +0.04 | 0% / 74% / 62% |
| S3 dels T close→T+1 open long | −189 (n44) | −136 / −147 / −156 (n23) | +7.5 / +2.2 / −3.5 (n30) | −2.81 / −0.92 | 0% / 0% / 2% |
| S4 dels T→T+5 long | −108 (n44) | −137 / −148 / −157 | +59 / +54 / +48 | −0.94 / +0.01 | 12% / 2% / 76% |
| S5 dels pre A+1c→Tc SHORT | +64 (n56) | +179 / +169 / +161 (n28) | +69 / +63 / +58 (n30) | +0.80 / −0.16 | 96% / 56% / 84% |

Fit 2021-23 → S5 (+169bp) judges 2024-26 +63bp but t −0.16; fit 2024-26 → S1 (+118) judges 2021-23 −9bp.
S5 pooled 2016-26 (P3, post-hoc robustness): mean +90bp but **median −7bp, 49% positive, t +0.97**;
without the 5 largest moves −28bp. Every mean is a handful of outliers. Deletions keep falling
after the effective date (S3 2021-23 t −2.8): there is no post-deletion reversal to buy. ~18 adds
and ~13 deletes a year, clustered on 4 rebalance dates: even a real edge would be tiny in the book.
**Dead**: nothing clears t 2; S1/S2/S4 flip sign across periods; S5 is a mean made by outliers.

### Q2 Russell reconstitution: untestable for single names; ETF proxy is noise

No membership lists and no shares outstanding in the repo, so the ~1000/3000 rank crossing cannot
be built without lookahead. FTSE Russell is semi-annual from 2026 (June 26; December 11, rank day
Oct 30). ETF proxy, 11 recon Fridays 2016-26: R1 IWM−SPY close→close +7.1bp (t +0.40; all Fridays
+1.5bp, sd 70bp); R2 IWM−SPY close→next open −6.7bp (t −0.37). Night leg on recon Fridays
(2021-26, 3-10 names): −114, +26, +79, +143, +652, +6bp/name, noise at n = 6. **Untestable / dead.**

### Q3 LETF rebalancing flow (|move at 15:30| > 2%): dead as pre-registered

Mechanism check, flow days (QQQ ~30/yr, SMH ~64/yr), in the direction of the day:

| | QQQ 15:30→close | QQQ close→open | SMH 15:30→close | SMH close→open |
|---|---|---|---|---|
| 2016-20 | +9.9bp (t 1.2) | −14.0 (−0.8) | +12.1 (2.3) | −12.7 (−1.0) |
| 2021-23 | +4.5 (1.4) | −3.7 (−0.4) | +4.6 (1.6) | −2.4 (−0.3) |
| 2024-26 | +5.2 (1.2) | +12.4 (0.8) | +0.4 (0.1) | +12.8 (1.1) |

The flow does push the close in the day's direction (small, all positive, fading on SMH), and the
noise leg already holds that direction 60-77% of flow days: it is the version of this that is
already earning. The overnight reversal flips sign in 2024-26.

| V7 book | 2021-23 | 2024-26 | 2021-26 | dSharpe 21-23 / 24-26 | NW t | pp/yr |
|---|---|---|---|---|---|---|
| V7 @3bp | 56.9/2.52/−10 | 59.2/2.17/−12 | 58.0/2.33/−12 | | | |
| L1 flatten noise 15:30 @3bp | 54.5/2.47/−10 | 58.4/2.19/−12 | 56.3/2.31/−12 | −0.06 / +0.01 | −1.54 | −1.14 |
| L2 night x1.5 on QQQ≤−2% @3bp | 56.2/2.44/−10 | 58.4/2.12/−12 | 57.2/2.26/−12 | −0.08 / −0.05 | −0.51 | −0.44 |
| V7 @tier | 48.6/2.23/−10 | 46.4/1.80/−13 | 47.5/1.99/−13 | | | |
| L1 @tier | 46.4/2.18/−11 | 45.7/1.81/−13 | 46.1/1.98/−13 | −0.05 / +0.01 | −1.47 | −1.09 |
| L2 @tier | 46.8/2.12/−11 | 45.4/1.75/−13 | 46.1/1.91/−13 | −0.11 / −0.05 | −1.04 | −0.92 |
| V7 @tier_hi | 42.0/1.99/−10 | 37.1/1.51/−14 | 39.6/1.73/−14 | | | |
| L1 @tier_hi | 40.4/1.95/−11 | 36.0/1.50/−14 | 38.2/1.70/−14 | −0.04 / −0.01 | −1.49 | −1.07 |
| L2 @tier_hi | 40.2/1.87/−11 | 35.7/1.45/−14 | 38.0/1.64/−14 | −0.11 / −0.06 | −1.25 | −1.09 |

Why L2 fails: the night leg's names do WORSE on market-selloff days, not better. Per name, tier:
QQQ ≤ −2% at 15:30 nights −9.8bp (n 63) vs +10.2 other nights (2021-23); −33.9 (n 35) vs +26.9
(2024-26). On those days a −8% name is mostly beta, not an idiosyncratic capitulation, and the
LETF/de-risking selling keeps going overnight.

### Q4 month-end pension rebalancing: mechanism visible, book effect ~0 (borderline)

IBS trades entered in the last 3 sessions, by rel = SPY MTD − TLT MTD (bp net 1bp/side):

| | rel < −3% | mid | rel > +3% | all IBS days |
|---|---|---|---|---|
| 2016-20 | +62.6 (n10) | +9.0 (15) | +6.9 (16) | +19.7 |
| 2021-23 | +48.7 (7) | +40.9 (23) | +20.7 (12) | +17.6 |
| 2024-26 | +99.0 (7) | +34.6 (16) | −15.4 (10) | +23.6 |

Right order in all three periods, but 7-16 trades per cell.
M3 (SPY open L−2 → close L, long rel < −3%, short rel > +3%, net 3bp): +11.2bp (t 0.68, n38, placebo
78%) / +67.6 (t 1.80, n15, 97%) / +32.3 (t 1.43, n16, 96%); pooled 2016-26 +34bp gross t **1.94**
(n 69). By rel bucket 2016-26: ≤−3% +76bp (20), −3..−1% +96 (13), ±1% +5 (23), +1..+3% +9 (23),
>+3% −17 (49): a real dose-response, consistent with Harvey-Mazzoleni-Melone.

| V7 book | 2021-23 | 2024-26 | 2021-26 | dSharpe | NW t | pp/yr |
|---|---|---|---|---|---|---|
| M1 IBS x1.5/x0.5 (35 days) @3bp | 56.9/2.53/−10 | 59.9/2.18/−12 | 58.3/2.34/−12 | +0.01 / +0.01 | +0.59 | +0.19 |
| M1 @tier | 48.4/2.23/−10 | 47.2/1.82/−13 | 47.8/2.00/−13 | +0.00 / +0.02 | +0.55 | +0.18 |
| M1 @tier_hi | 41.9/1.99/−10 | 37.6/1.52/−14 | 39.8/1.73/−14 | +0.00 / +0.01 | +0.42 | +0.14 |
| M2 skip IBS rel>+3% (21 days) @3bp | 56.4/2.52/−10 | 59.8/2.20/−12 | 58.0/2.34/−12 | −0.01 / +0.02 | −0.06 | −0.02 |
| M2 @tier | 47.8/2.21/−10 | 46.9/1.82/−12 | 47.3/1.99/−12 | −0.02 / +0.02 | −0.42 | −0.16 |
| M2 @tier_hi | 41.6/1.97/−10 | 37.5/1.53/−13 | 39.6/1.73/−13 | −0.01 / +0.02 | −0.10 | −0.04 |
| P1 (post-hoc) + M3 SPY sleeve w0.5, taxable @3bp | 56.5/2.51/−9 | 60.7/2.20/−13 | 58.5/2.33/−13 | −0.01 / +0.03 | +0.43 | +0.29 |
| P1 @tier | 48.2/2.22/−9 | 48.2/1.85/−14 | 48.2/2.01/−14 | −0.01 / +0.05 | +0.67 | +0.46 |
| P1 @tier_hi | 41.6/1.97/−10 | 38.5/1.55/−14 | 40.1/1.74/−14 | −0.01 / +0.04 | +0.52 | +0.35 |

Placebo (same multipliers on random non-window IBS days, 30 seeds): M1 beats 63% / 83%, M2 43% / 80%.
Edge-halves tier_hi: V7 17.5/0.89/−20, M1 17.6/0.89/−20, M2 17.5/0.89/−20, P1 17.7/0.89/−20; MC
P(DD>30%) 23% → 22% for all three. **Borderline**: the flow is there, but it touches ~6 trades a
year; M1 is +0.15pp/yr, inside the placebo in 2021-23. M3 needs a short (taxable only) and costs
the noise leg daytime margin on those days; P1 is Sharpe-flat in 2021-23. Watch, not build.

### POST-HOC P2: night leg x0.5 on LETF-selloff days (QQQ prev close → 15:30 ≤ −2%) — study SHADOW, verified BORDERLINE

Added after L2 failed in the opposite direction (so post-hoc: the rule is L2 with the sign flipped).

| | 2021-23 | 2024-26 | 2021-26 | dSharpe | NW t | pp/yr |
|---|---|---|---|---|---|---|
| V7 + P2 @3bp | 57.8/2.58/−9 | 60.3/2.22/−12 | 59.0/2.37/−12 | +0.05 / +0.04 | +0.67 | +0.57 |
| V7 + P2 @tier | 49.1/2.26/−9 | 47.5/1.85/−13 | 48.3/2.03/−13 | +0.03 / +0.05 | +0.57 | +0.50 |
| V7 + P2 @tier_hi | 44.1/2.08/−10 | 38.3/1.56/−14 | 41.2/1.79/−14 | +0.09 / +0.05 | +1.29 | +1.11 |
| Roth b1 @tier | 36.3/2.07/−8 | 42.0/1.77/−13 | 39.0/1.88/−13 | | | |
| Roth b1 + P2 @3bp | 45.3/2.53/−7 | 55.5/2.22/−12 | 50.1/2.33/−12 | +0.09 / +0.04 | +0.61 | +0.52 |
| Roth b1 + P2 @tier | 37.5/2.17/−8 | 43.0/1.82/−13 | 40.1/1.95/−13 | +0.10 / +0.04 | +0.88 | +0.76 |
| Roth b1 + P2 @tier_hi | 31.9/1.89/−8 | 34.1/1.51/−14 | 32.9/1.66/−14 | +0.13 / +0.05 | +1.26 | +1.10 |

- 2020 holdout (close-signal rebuild, per name, 10bp/side): flag nights −83bp (n 26) vs +54bp (n 162).
  Same sign in all three periods.
- Placebo (x0.5 on 97 random night-leg days, 30 seeds): beats 83% / 80%.
- Edge-halves tier_hi 18.2/0.92/−21 vs 17.5/0.89/−20; MC $3k+$1k/mo P(DD>30%) 21% vs 23%, P(DD>50%) 0%;
  $10k lump median $23.3k vs $22.6k. COVID crash (Feb 19-Mar 23) −12.9% → −9.5% (maxDD −17.5 → −14.1;
  12 of 24 night days flagged); 2022 +61.4 → +67.6%; Apr 2025 +6.0 → +7.1%; worst day −6.0% both;
  worst month −10.3 → −10.0%.
- Fires on ~7% of night-leg days (97 in 2021-26). Only lowers exposure: no new margin, Roth-safe.

**Study verdict P2: SHADOW** (downgraded to borderline by the verifier below; post-hoc, t < 2, bar (c) fails). It is the one result here with a
consistent sign in 3 periods, a working placebo, and a risk reduction in every crash episode.
Addendum 26a's lagged SPY-vol / prior-day-drop tilts were dead; this is a same-day,
15:30-known flag on the night leg alone, and the per-name gap is large (−34 vs +27bp).

## Verdict

| question | verdict |
|---|---|
| Q1 S&P 500 adds/deletes (S1-S5) | **dead**: the effect is in the untradable announcement gap; windows after it flip sign or are outlier means (S5 median −7bp) |
| Q2 Russell recon | **untestable** for single names (no membership / shares); IWM−SPY proxy noise (t ±0.4, n 11) |
| Q3 LETF flow L1/L2 | **dead**: flow = small momentum into the close the noise leg already holds; night leg does worse on flow-down days |
| Q4 month-end pension M1-M3 | **borderline / watch**: dose-response is right in all periods (M3 pooled t 1.94) but ~6 trades/yr, book +0.15pp/yr, placebo 63% |
| P2 night x0.5 on QQQ ≤ −2% at 15:30 (post-hoc) | **borderline** (verifier downgrade from shadow): +0.5pp/yr at tier, but the 2020 holdout is 3 outlier nights (median flag night +56bp = other nights), 3 of 6 years negative, not direction-specific (|QQQ| ≥ 2% does better), high-vol placebo 92%/72% |

Shadow spec (P2): at the night leg's 15:40 decision, read QQQ's 15:30 minute close vs the
prior official close (the noise leg already streams QQQ minutes). If ≤ −2%, log
`[night] SHADOW flow-down: would size names x0.5` with the day's picks; the next morning score
the halved-vs-full P&L against the official open. Config key proposal `daily.night_flowdown_scale`
(shadow: log only; 1.0 = off, 0.5 = on) with `daily.night_flowdown_move: -0.02`. Decide after
~20 flagged nights (≈ 1 year at 7% of days, sooner in a selloff).

## Do NOT redo

| idea | verdict | why |
|---|---|---|
| S&P 500 add/delete trades after the announcement (run-up, post-effective reversal, deletion bounce) | **dead** | the move is in the after-close announcement gap (+271..+517bp adds 2021-26); tradable windows flip sign; deletions keep falling (add. 34) |
| Russell recon reversal | **untestable** | no membership/shares data; IWM−SPY recon-day proxy t ±0.4, n 11 (add. 34) |
| LETF-flow conditioned last half hour / night size-up after big down days | **dead** | flow is small momentum the noise leg already holds; night names are worse on QQQ ≤ −2% days (add. 34) |
| Month-end pension rebalancing (SPY−TLT MTD) as IBS sizing | **watch** | right sign all periods, ~6 trades/yr, +0.15pp/yr, placebo 63% (add. 34) |


## Verifier notes (adversarial pass, 2026-09-28)

`research/sim/index_mechanics_verify.py` (~15 s, no lock). Reproduced every P2 number exactly
(tier dSharpe +0.029/+0.046, +0.50pp/yr, NW t +0.57; tier_hi +1.11pp/yr). No lookahead found:
minute column 360 is the 15:30 bar (closes 15:31, before the 15:40 decision); the night dict is keyed
by the buy day; S&P announcement dates are press-release dates; T chosen by volume between the two
public candidate sessions is cleaning, not signal. Q1-Q4 verdicts stand.

P2 does not survive as a shadow candidate:

| check (V7 book) | tier dSharpe 21-23 / 24-26 | tier pp/yr | tier_hi pp/yr |
|---|---|---|---|
| P2 repro (≤ −2%, x0.5) | +0.029 / +0.046 | +0.50 | +1.11 |
| threshold ≤ −1.5% | +0.017 / +0.048 | +0.31 | +1.09 |
| threshold ≤ −2.5% | +0.021 / +0.013 | +0.29 | +0.59 |
| threshold ≤ −3.0% | +0.023 / **−0.005** | +0.19 | +0.31 |
| x0.0 / x0.75 on ≤ −2% | +0.052/+0.082 ; +0.041/+0.025 | +1.17 ; +0.39 | +2.16 ; +0.65 |
| x0.5 on QQQ ≥ +2% (same vol, other sign) | −0.024 / +0.038 | −0.17 | +0.08 |
| x0.5 on \|QQQ\| ≥ 2% (both signs) | **+0.054 / +0.094** | +0.80 | +1.17 |
| x0.5 on lagged QQQ d−1 ≤ −2% (26a-style) | −0.053 / −0.019 | −1.23 | −1.01 |

- **2020 holdout is outliers.** Flag nights: mean −83bp but **median +56bp** vs other nights median
  +55bp; dropping the 3 worst flag nights (COVID Feb/Mar) the flag mean is **+81bp**, better than other
  nights. "Same sign in all three periods" was a mean artifact.
- **Concentration.** P2's gain by year (tier, pp): 2021 −0.85, 2022 +3.08, 2023 −1.21, 2024 −0.09,
  2025 +2.81, 2026 −0.92: 3-4 of 6 years negative; the top-5 days are 63% of the total gain.
- **Not direction-specific.** Cutting on |QQQ| ≥ 2% either way does better than the down-only rule,
  so it is mostly a vol cut on big-move days (26a/add. 18 family), not an LETF-selling mechanism.
- **Exposure-matched placebo** (x0.5 on random days drawn from the trailing high-vol-quintile pool,
  same count per half, 50 seeds): beats 92% / **72%** (the random-day placebo's 83/80% was not
  exposure-matched).
- 2021-26 book NW t 0.57 (tier); threshold at −3% flips 2024-26 negative.

**Verifier verdict P2: borderline** (post-hoc, outlier-driven holdout, fails exposure-matched
placebo in 2024-26, not monotone in threshold). Not worth a shadow build on its own; if the
night leg ever gets a crash-day guard it should be judged together with the |move| family.
Study overall: **borderline** (Q4 month-end also borderline/watch). Variants: 15 study + 12 verifier = 27.

Do-NOT-redo row (replaces the P2 shadow row):

| idea | verdict | why |
|---|---|---|
| Night leg x0.5 on QQQ ≤ −2% at 15:30 (LETF-selloff flag) | **borderline** | post-hoc; +0.5pp/yr tier but 2020 holdout = 3 COVID nights (median flag night = other nights), 3/6 years negative, \|move\| ≥ 2% both signs does better, high-vol placebo 72% in 2024-26 (add. 34) |


# Addendum 35 — the options calendar (OPEX, witching, 0DTE) as a timing input: dead (2026-09-28)

## Pre-registration (stamped Mon Sep 28 20:51:36 PDT 2026, before any 2024-26 number was computed)

**Mechanism.** Dealers who are net long gamma near large open interest hedge against the move
(sell rallies, buy dips): intraday moves are damped and pinned into monthly expiry, and the
damping is released after expiry (the "OPEX week vol expansion" folk claim). Intraday momentum
(the noise-band leg, QQQ/SMH) is the opposite of pinning, so it should earn LESS on OPEX
Friday / OPEX week and MORE the week after. Since 2022 daily SPX expiries (0DTE, M/W/F from
2022-05, every day from 2022-11) make every day an expiry day; if intraday dealer hedging now
dominates, the noise leg's per-day edge should be lower in the 0DTE era. Witching close
auctions are 2-4x normal size; an imbalance-driven close print could move the night leg's entry.

**Calendar (ex-ante).** Monthly OPEX = 3rd Friday; if the exchange is closed that Friday
(Good Friday 2019/2022/2025-type cases), the prior trading day. Witching = OPEX in Mar/Jun/Sep/Dec.
OPEX week = the trading days Mon..OPEX of that calendar week. Post-OPEX week = the next 5
trading days after OPEX. All of these are known years ahead. 0DTE era = 2022-11-14 onward.

**Variants (5; nothing else will be adopted):**
- **V1** noise leg x0.5 on OPEX Friday (book variant).
- **V2** noise leg x1.5 in the post-OPEX week (book variant). Leverage is scaled BEFORE the
  daytime margin cap (V7 taxable intraday cap 0.75, Roth 1.5 via 3x ETFs), so it is feasible;
  also reported uncapped as a diagnostic of the signal (not deployable).
- **V3** 0DTE split (diagnostic / edge-decay input): noise per-day net return and Sharpe in
  2016-20, 2021-01..2022-11-11, 2022-11-14..2026-09; and within-era slope.
- **V4** IBS and night legs, OPEX week vs post-OPEX week vs rest (diagnostic). Only if the
  difference passes the bar below does a book variant run: that leg x0.5 in the weaker window.
- **V5** witching-day night entry (diagnostic): the night leg's per-trade close->open return,
  and SPY/QQQ close->open (2016+), on witching days vs others.

**Pass bar (all required for adopt; shadow if the signal passes but the book gain < +1pp CAGR
or < +0.03 Sharpe at 3bp):**
1. event-vs-rest difference has the pre-registered sign in 2016-20, 2021-23 AND 2024-26
   (noise leg; night leg has no 2016-20 honest data, so both 2021-23 / 2024-26 halves);
2. pooled Newey-West (5 lags) t >= 2.0 on the event dummy;
3. beats the 95th percentile of a placebo: the same number of random non-event Fridays (V1)
   or random non-event weeks (V2/V4), drawn within the same QQQ 20d realized-vol tercile;
4. V7 book (growth.V7 via Sim.replay) improves CAGR and Sharpe in both halves at 3bp, tier and
   tier_hi; edge-halves and 5y MC P(DD>30%) not worse; Roth book (roth.py b1) not worse.
V5 has ~22 witching days in 5.6 years of honest night data: pre-declared "cannot pass; watch at
best" unless |t| > 3.

## Results

`research/sim/opex.py` (~10 s once `cache_opex.pkl` holds the V7 night days; building that
cache needs the heavy lock, ~2 min). Calendar: `event_calendar.opex_dates()` snapped to the
research sessions: 129 OPEX days 2016-01..2026-09 (4 Thursday expiries: 2019-04-18,
2022-04-14, 2025-04-17, 2026-06-18), 43 witching.

**Noise leg (QQQ+SMH, V7 taxable cap 0.75), per-day net return at unit equity, event minus rest
(NW t), and the vol-tercile-matched placebo percentile of the event mean:**

| window | 2016-20 | 2021-23 | 2024-26 | pooled | placebo pct 16-20 / 21-23 / 24-26 |
|---|---|---|---|---|---|
| V1 OPEX Friday (expect <0) | −3.3bp (t −1.34) | +0.0 (0.00) | −0.2 (−0.02) | −1.6 (−0.50) | 5% / 26% / 36% |
| OPEX week Mon..Fri (diag) | −3.8 (−2.18) | −0.7 (−0.22) | −3.6 (−0.94) | −2.9 (−1.84) | 3% / 38% / 17% |
| V2 post-OPEX 5 sessions (expect >0) | +1.5 (0.76) | +1.8 (0.50) | **−2.8 (−0.87)** | +0.5 (0.31) | 80% / 80% / 20% |
| witching day (diag) | +2.8 | +2.1 | −11.3 | −1.0 (−0.21) | — |

The dealer-pinning story shows up only in 2016-20 (OPEX week −3.8bp, t −2.2). Since 2021 it is
noise, and the post-OPEX "release" flips sign in 2024-26. No window passes the bar.

**V3, the 0DTE era (edge-decay input).** Noise leg net per day: 2016-20 +2.1bp (Sharpe 1.00),
2021..2022-11-11 +6.7bp (2.31), 2022-11-14+ +2.2bp (0.82). The 0DTE-era dummy is −4.5bp vs
2021-22 (NW t −2.02) but −1.2bp (t −0.80) vs all of pre-0DTE: 2021-22 was the unusually trendy
period (the 2022 bear), and the 0DTE era is back at the 2016-20 level. Unlevered by year:
2023 +3.3, 2024 +3.5, 2025 +5.2, 2026 YTD −0.1bp/day. **No evidence that daily expiries killed
intraday momentum**; the leg is a Sharpe ~0.8-1.0 thing in normal years, and 2021-22 is the
outlier the book's history leans on. Use +2bp/day (not +4-5) as the planning edge for the noise leg.

**V4, IBS and night legs** (unit weight; night at 3bp; post-OPEX minus OPEX week):

| leg | 2016-20 | 2021-23 | 2024-26 |
|---|---|---|---|
| IBS: OPEX week vs rest | −1.4bp (t −0.09) | −39.5 (−1.48) | −33.5 (−1.14) |
| IBS: post-OPEX vs rest | +28.1 (1.51) | +21.8 (0.82) | **−30.1 (−1.29)** |
| IBS: post minus OPEX week | +22.0 (1.07) | +47.2 (1.36) | +2.8 (0.08) |
| night: post minus OPEX week | — | +3.4 (0.21) | +5.0 (0.21) |

Nothing has |t| >= 2 or a stable sign, so the conditional x0.5 book variant was not run.

**V5, witching close auction and the night entry** (23 witching days in the honest night data):
night per-day −19.1bp vs +18.8bp on other days (NW t −2.29; halves −24.7 / −13.1bp, t −1.6 /
−1.7; placebo of random vol-matched Fridays: 12% / 29% / 14% pooled, so not beyond the 95th).
The mechanism is visible: on witching days the night names' 15:50 -> close drift is +38.5bp
vs +10.1bp normally (t +1.04), i.e. the giant MOC buy imbalance lifts our entry print and it
gives back overnight. SPY/QQQ/IWM close->open on witching days: −8 to −17bp in 2016-20 and
2021-23, but +43 to +62bp in 2024-26 (n 11): not a stable index effect. Pre-declared bar |t| > 3
not met: **watch**, not shadow-worthy on its own (4 days/yr; skipping would be worth ~+0.4pp/yr
of book CAGR if real).

**Book effect (V7 taxable, `growth.V7` + `cfg(1.0, 0.5, 2)`, 2021-23 / 2024-26 / full, CAGR/Sharpe/maxDD):**

| variant | 3bp | tier | tier_hi | EH 3bp, MC $3k+1k median, P(DD>30/50) |
|---|---|---|---|---|
| V7 baseline | 56.9/2.52 · 59.2/2.17 · 58.0/2.33/−12 | 47.5/1.99/−13 | 39.6/1.73/−14 | 25.1/1.19, $120.4k, 11%/0% |
| V1 noise x0.5 OPEX Fri | 56.5/2.52 · 59.1/2.18 · 57.7/2.33/−12 | 47.1/1.98 | 39.2/1.72 | 24.9/1.19, $119.7k, 10%/0% |
| V2 x1.5 post-OPEX (margin-capped) | 57.0/2.53 · 59.2/2.17 · 58.1/2.33/−12 | 47.5/1.99 | 39.7/1.73 | 25.1/1.19, $120.3k, 11%/0% |
| V2u x1.5 post-OPEX (uncapped, infeasible) | 59.7/2.52 · 59.2/2.15 · 59.4/2.32/−12 | 48.6/1.99 | 40.8/1.73 | 25.5/1.18, $122.0k, 12%/0% |
| post-hoc: noise x0.5 OPEX week | 54.9/2.49 · 59.8/2.23 · 57.2/2.34/−12 | — | 38.9/1.73 | 24.8/1.20 |

In the taxable book the V7 intraday cap (0.75) binds on most days (QQQ vol-target lev median
1.9), so V2 can barely act; uncapped it is +1.4pp all from 2021-23 and a Sharpe loss in
2024-26. Crashes: 2022 window +46.6% baseline vs +46.5/+46.5/+48.1; Apr 2-8 2025 +6.3% in all;
worst day −5.9% all; COVID (noise leg, additive) V1 −0.24pp, V2u +0.06pp.

**Roth b1** (intraday 1.5x via 3x ETFs, full CAGR/Sharpe/maxDD): baseline 3bp 49.3/2.27/−12,
tier_hi 31.4/1.58; V1 48.7/2.26 (worse); V2 capped 50.3/2.27 (3bp; halves +1.8pp / 0.0pp),
tier_hi 32.3/1.59 (halves +1.7 / 0.0). The Roth gain is 2021-23 only, and V2's signal fails in
2024-26 and against the placebo: not adoptable.

**Verdict: dead** for V1, V2, V3-as-a-rule and V4. V5 (witching-day night entry) was reported as a
**watch** item, but the verifier downgraded it to dead / weak watch (see Verifier notes): measured
against other pre-weekend entries it is t −1.3. V3 is an edge-decay input: the 0DTE era did not decay the noise
leg vs 2016-20; 2021-22 was the outlier, so plan on ~+2bp/day.

Variants evaluated: 16 (V1 taxable/Roth, V2 capped taxable/Roth, V2u, OPEX-week diag, witching
noise diag, V3 eras, V4 IBS week/post/diff, V4 night week/post/diff, V5 night/drift/index, and
post-hoc OPEX-week x0.5 book + witching night placebo).

**do NOT redo:**

| idea | verdict | why |
|---|---|---|
| Options calendar (OPEX Fri / OPEX week / post-OPEX week) as a sizing input for noise, IBS, night | **dead** | pinning effect only in 2016-20; post-OPEX "vol release" flips sign 2024-26; book ±0.3pp (add. 35) |
| Witching-day night entry (MOC imbalance lifts our close print) | **dead (weak watch)** | −19bp vs other pre-weekend entries +4bp: diff −23bp, NW t −1.3 (halves −0.7/−1.2), placebo 14th pct; the raw t −2.3 vs all days was the Friday/weekend effect (add. 35) |
| 0DTE era as edge decay for the noise leg | **no evidence of decay** | 0DTE era +2.2bp/day ≈ 2016-20 +2.1bp; 2021-22 (+6.7bp) was the outlier: plan on ~+2bp/day (add. 35) |

## Verifier notes (adversarial re-run, 2026-09-28)

Re-ran `research.sim.opex` from `cache_opex.pkl`. Every number above reproduces exactly, and the
V7 baseline matches addendum 29 (58.0/2.33/−12). Checks:

- **Lookahead / calendar:** the OPEX dates are rule-based (3rd Friday, or the Thursday before if
  that Friday is an NYSE holiday), so they are known years in advance. The 4 Thursday dates are
  right (Good Friday ×3, Juneteenth 2026). The vol-tercile matching uses QQQ 20-day vol shifted by
  1 day, so no lookahead. The study depends on `research/sim/event_calendar.py`, which is another
  study's untracked file; it must be committed with this one.
- **Mechanics:** V1 scales the return (an exact down-scale). V2 scales the leverage before the
  0.75 cap (the taxable cap from `cfg(1.0,0.5,2)`: room 0.375 / 0.5), so it is margin-feasible.
  The Roth replay goes through `roth.replay`, whose cap is min(1.5, 3×freed cash). The noise leg's
  cost is fixed at 0.5bp per trade in `noise_days`, so the three cost tiers move only the night
  leg. That is the repo convention.
- **V5 is confounded (downgraded).** 22 of the 23 witching nights are Friday entries, i.e. weekend
  holds at `weekend_scale` 0.5. The headline "−19bp vs +19bp, t −2.29" compares them with all days,
  and non-gap nights average +22.5bp. Against other pre-weekend/holiday entries (n 305, now printed
  by the script) the numbers are: witching −19.1bp vs +4.2bp, diff −23bp, **NW t −1.32**; halves
  −16bp (t −0.66) and −31bp (t −1.23). The placebo of vol-matched random Fridays stays at the 14th
  percentile. The "mechanism" (15:50→close drift of +38.5bp vs +10.1bp) has t 1.04 (vs other
  Fridays +43.6 vs +5.5, t 1.31; median +22bp), so it is not established either. This is **dead /
  weak watch** at most, not a watch item.
- **V1 vs other Fridays (sensitivity):** OPEX Friday's noise edge is below other Fridays in all
  three periods (−6.1 / −7.8 / −3.1bp; t −1.78 / −1.14 / −0.26; pooled −5.8, t −1.51). That is
  consistent with mild pinning, but it misses t ≥ 2 and the placebo bar, and the book loses money
  when it halves a leg whose edge is still positive. Dead stands.
- **Placebo:** it is matched on frequency (same count) and on exposure only through the vol
  tercile. The V2 blocks may overlap post-OPEX days after their first day; that is conservative
  and does not change the verdict.
- **Variant count:** 16 reported, +2 verifier sensitivities (V5 vs pre-gap entries, V1 vs other
  Fridays) = 18.
- **Dollars:** $0, since nothing is adopted.


# Addendum 36 — future-agnostic universe (rule-based IBS ETFs, new listings, new ETF launches): dead; found the split-adjustment bug (add. 30) (2026-09-28)

## Pre-registration

Stamped `Mon Sep 28 20:52:50 PDT 2026`, written before any 2024-26 number of
this study was computed. Script: `research/sim/new_listings.py` (same list in
its docstring). Everything below is fixed; anything added later is POST-HOC.

### Q1. Rule-based IBS universe (replace the hand-listed 18 ETFs)

Mechanism: the IBS leg earns a short-horizon liquidity-provision premium in
liquid, broad equity baskets (a close near the day's low in a diversified fund
is flow, not news). The hand list EQ18 was written in 2026 knowing which
funds exist and stayed liquid — it carries hindsight. A rule that sees only
what was knowable at each month-end should reproduce it if the edge is
structural, and keeps working when the fund landscape changes.

Rule (evaluated at each month-end, data strictly before the month):
- US-listed ETF: asset name contains "ETF" or an ETF issuer token
  (iShares, SPDR, Invesco, Vanguard, Schwab, VanEck, Global X, ...), on
  ARCA/NASDAQ/NYSE/BATS/AMEX; single-stock, levered and inverse funds excluded
  by name (2X/3X/ULTRA/BULL/BEAR/SHORT/INVERSE/DAILY/LEVERAGED/-1X/single-stock
  issuer tokens) AND by structure (252d beta to SPY > 1.6 -> excluded).
- equity: name has no bond/treasury/muni/credit/commodity/gold/silver/oil/
  crypto/bitcoin/currency/volatility/VIX/T-bill token AND 252d daily-return
  correlation with SPY >= 0.5.
- age >= 252 sessions of bars; price >= $10; 60d median SIP $volume >= X.
- dedupe: sort by 60d median $volume descending; greedily keep a fund unless
  its 60d daily-return correlation with an already-kept fund >= c.
- then exactly the live rule: top-3 by 12-1 momentum, held for the month;
  IBS < 0.2 on the last complete bar -> hold from next open to next open.

Variants (4): U1 X=$100M c=0.95 (primary); U2 X=$25M c=0.95; U3 X=$500M c=0.95;
U4 X=$100M c=0.90. Reference: EQ18 through the same code and data.
Placebo: 18 funds drawn at random each month from the rule's eligible,
deduped set (50 seeds), then the same momentum/IBS — asks whether the rule's
universe is special or any 18 liquid equity ETFs do it.

Pass bars. "Replace" (the rule reproduces the hand list): on the shipped V7
book (Sim.replay with s.I swapped) CAGR within -1.0pp of EQ18 in BOTH 2021-23
and 2024-26 at tier_hi, Sharpe within -0.05, EH 5y MC P(DD>50%) not higher by
more than 1pp, and the standalone leg positive in 2016-20. "Beat": > +1pp both
halves, standalone Sharpe > EQ18 in all three periods, and above the placebo's
90th percentile. Only U1 can be adopted; U2-U4 are sensitivity.

### Q2. New listings in the night leg (sizing input)

Mechanism: new listings have no price history, thin analyst coverage, lockup
and SPAC-redemption float dynamics. Two opposite stories: (a) more
uninformed/retail flow -> larger overreaction -> bigger bounce; (b) de-SPACs
and recent IPOs fall on information (redemptions, lockup expiry, dilution)
-> a -8% day continues. Prior: (b) for de-SPACs, unsigned for IPOs.

"New" = first bar in the combined 2016-01..2026-09 SIP daily data after
2021-01-04 for the 15:50 night pool (2016-20 holdout: first bar after
2017-01-03, daily-bar proxy trigger close <= -8%, IBS(close) < 0.1, price >= $5,
vol20 >= 0.60, close -> next open).
Flags (3): F1 age < 252 sessions; F2 age < 63 sessions; F3 de-SPAC = new
symbol whose first bar follows within 5 sessions the last bar of a symbol
whose name contains "Acquisition" and whose last close is within 20% of the
new symbol's first open.
Per flag two book actions on the shipped V7 night pool (night_days
max_corr=0.7, cap 0.10, tilt live): EXCLUDE flagged names; UP-WEIGHT flagged
names 2x (before the 0.10 name cap). = 6 book variants.
Statistic: per-trade next-open return net of tier cost, flagged minus
seasoned, day-clustered t (regression of trade returns on the flag with
clustered SE). Placebo: exclude the same number of random unflagged names
each day from the same vol20 decile (200 seeds).
Pass bar (any action): flagged-minus-seasoned difference has the same sign
in 2021-23, 2024-26 and the 2016-20 proxy, pooled 2021-26 |t| >= 2, book CAGR
gain at tier_hi > 0 in both halves and above the placebo 90th percentile.
Otherwise dead (the night leg keeps new names at equal footing).

### Q3. New ETF launches (at most 2 variants; prior: dead)

Why add. 28 failed: by the time a theme is visible in prices it is late; ETF
issuers launch thematic funds at theme peaks (Ben-David, Franzoni, Kim &
Moussawi 2022: specialised ETFs lose ~30% risk-adjusted in 5 years). A
new-launch "signal" is the same late signal. Overnight/intraday split: new
funds are held by retail; retail buys at the open -> overnight premium may be
larger in young funds.
L1: equal-weight overnight (close -> open) basket of equity ETFs (Q1 name and
beta rules, no correlation-to-SPY floor) aged 10-252 sessions, price >= $10,
20d median $volume >= $1M, 3bp/side; vs a placebo of seasoned (age > 756)
ETFs matched on 20d-vol decile, same count per day (50 seeds).
L2: descriptive, not a trade: new equity ETFs' return from session 21 to 252
after launch minus SPY over the same window (cohort mean, by launch year).
Pass bar L1: Sharpe > 0 after 3bp in all three periods AND above placebo
90th percentile in both 2021-23 and 2024-26. L2 cannot be adopted (no shorts
in Roth; young thematic ETFs are hard to borrow); a strongly negative L2
supports the age >= 252 filter in Q1.

All costs reported: 3bp flat ("measured"), tier, tier_hi. Fit 2021-23 / judge
2024-26 and the reverse; 2016-20 holdout.

## How to run

```
# once, under the heavy lock (panel + 2016-20 SIP daily + night pool -> slim cache, ~30 s, 4.4 GB peak)
PYTHONPATH=. .venv/bin/python -m research.sim.new_listings --cache
PYTHONPATH=. .venv/bin/python -m research.sim.new_listings --segments
# everything else from the cache (~11 min)
PYTHONPATH=. .venv/bin/python -m research.sim.new_listings
```

Data: ETF identification from `asset_meta.json` names (5,965 ETF-like symbols;
3,866 unlevered equity by the name rule). 2016-01..2020-09 from the add. 28
SIP daily fetch, 2020-10+ from `panel.pkl`. Parity check: EQ18 rebuilt from
this data reproduces the simulator's own IBS leg exactly (corr 0.99999, V7
book 48.6/46.4 in both builds).

Data hygiene (fixed after the FIRST Q1 run, before any result was used; reported
so nobody repeats it): `panel.pkl` carries delisted names forward at volume 0
(INFO sat at $108.05 from 2022-02 to 2024-10), and tickers get reused (INFO:
IHS Markit -> a Harbor ETF; FB -> a ProShares buffer ETF; PCLN). Using the
CURRENT asset name on OLD bars made IHS Markit an "ETF" in 2019. Fix: a bar
exists only with volume > 0; a listing is split at gaps > 60 sessions or (for
unlevered funds) a |daily return| > 40%; only the last listing carries the
current name. 296 ETF listings were split. **Any future study that classifies
by asset name must do the same.**

## Q1 — rule-based IBS universe: DEAD (the hand list wins, and not only by hindsight)

Picks differ from EQ18 most months (overlap 12-42%). The rule reaches for
narrow thematic funds at their momentum peaks: ARKK/ARKG/TAN in Jan 2021,
ICLN/XME in Jan 2023, JETS/QTUM in 2025. The deduped eligible set has only ~30
funds at $100M ADV. Also, the pre-registered beta <= 1.6 levered-fund guard
removes SMH in 2023-24 (beta ~1.7); U1b (cap 2.0) is the post-hoc fix.

Standalone IBS leg (unit weight), CAGR / Sharpe / maxDD:

| universe | 2016-20 @3bp | 2021-23 @3bp | 2024-26 @3bp | 2021-23 @tier_hi | 2024-26 @tier_hi | NW t (3bp) | Sharpe pct vs random-18 placebo 16-20/21-23/24-26 |
|---|---|---|---|---|---|---|---|
| U1 $100M c.95 (primary) | 3.5 / 0.33 / -21 | -11.3 / -0.50 / -37 | 16.5 / 0.99 / -26 | -18.6 / -0.92 | 7.2 / 0.50 | 0.69 | 28 / 8 / 84% |
| U2 $25M c.95 | 8.5 / 0.65 / -19 | -4.5 / -0.10 / -24 | 25.1 / 1.34 / -20 | -13.3 / -0.54 | 13.8 / 0.81 | 1.90 | 82 / 54 / 100% |
| U3 $500M c.95 | 8.0 / 0.71 / -16 | 1.1 / 0.15 / -24 | 9.8 / 0.73 / -22 | -6.3 / -0.32 | 1.9 / 0.20 | 1.65 | 88 / 84 / 58% |
| U4 $100M c.90 | 3.3 / 0.33 / -20 | -9.3 / -0.39 / -31 | 14.9 / 0.87 / -26 | -16.6 / -0.82 | 5.7 / 0.40 | 0.75 | 30 / 20 / 76% |
| U1b beta<=2.0 (POST-HOC) | 4.6 / 0.38 / -18 | -10.6 / -0.45 / -36 | 31.8 / 1.44 / -29 | -18.0 / -0.88 | 21.5 / 1.05 | 1.38 | 40 / 10 / 100% |
| **EQ18 hand list** | **9.7 / 0.83 / -16** | **11.0 / 0.77 / -19** | **15.9 / 1.04 / -15** | 2.7 / 0.25 | 7.7 / 0.56 | **2.89** | **92 / 98 / 88%** |

(IBS legs here are charged the night tier table by fund price/ADV: 5 / 7.5bp per
side for liquid funds at tier / tier_hi, vs the shipped 1bp. Harsh on every row equally.)

V7 book with the IBS universe swapped (night pool as shipped), CAGR / Sharpe / maxDD:

| universe | 2021-23 @3bp | 2024-26 @3bp | 2021-23 @tier | 2024-26 @tier | 2021-23 @tier_hi | 2024-26 @tier_hi | EH 5y MC $3k+1k: median, P(DD>30), P(DD>50) |
|---|---|---|---|---|---|---|---|
| U1 | 40.6 / 1.85 / -10 | 57.3 / 2.12 / -12 | 30.2 / 1.44 | 42.1 / 1.67 | 22.8 / 1.15 / -13 | 30.0 / 1.28 / -14 | $86.9k, 33%, 1% |
| U2 | 43.9 / 1.94 / -12 | 63.2 / 2.24 / -11 | 33.2 / 1.54 | 45.8 / 1.75 | 25.5 / 1.25 / -16 | 33.7 / 1.38 / -12 | $89.9k, 29%, 1% |
| U3 | 46.8 / 2.14 / -11 | 52.6 / 2.02 / -11 | 37.5 / 1.79 | 38.0 / 1.57 | 29.2 / 1.46 / -12 | 26.8 / 1.19 / -14 | $87.8k, 34%, 2% |
| U4 | 41.0 / 1.86 / -12 | 56.7 / 2.11 / -12 | 31.5 / 1.50 | 40.7 / 1.63 | 23.5 / 1.18 / -14 | 28.8 / 1.24 / -15 | $86.7k, 34%, 2% |
| U1b (POST-HOC) | 41.2 / 1.86 / -10 | 68.2 / 2.34 / -11 | 30.6 / 1.46 | 50.8 / 1.88 | 23.1 / 1.16 / -13 | 38.3 / 1.51 / -14 | $90.6k, 30%, 1% |
| **EQ18 (shipped list)** | **54.2 / 2.43 / -10** | 56.7 / 2.10 / -13 | **43.6 / 2.05** | 41.6 / 1.66 | **34.8 / 1.70 / -11** | 30.3 / 1.29 / -14 | **$92.2k, 29%, 1%** |

Roth b1 at tier_hi: EQ18 23.2 / 25.8, U1 10.7 / 25.7, U2 13.6 / 29.5, U3 17.5 / 22.7.
Crash windows (standalone IBS leg, tier_hi): COVID EQ18 -0.8% vs rules -7.6 .. -14.1%;
2022 EQ18 -18.3% vs -10.2 .. -19.1%.

Against the pre-registered bar: "replace" needs every half within -1pp of EQ18
at tier_hi — every rule loses 5.6-12pp in 2021-23. U2 wins 2024-26 (+3.4pp)
and U1b wins more (+8pp), but both have the 2021-23 hole. **Dead.**

Why: the IBS premium lives in BROAD, diversified baskets, where a close at
the day's low is flow, not news. A rule on liquidity + momentum over every
equity ETF promotes narrow theme funds exactly when their momentum peaks (the
add. 28 failure again), and a close at the low in ARKK or TAN is information.
The hand list's hindsight is real but mild: its 18 funds are the oldest, most
liquid broad and sector index funds, and would have been listed the same way in
2016. What it does embed is a *breadth* rule (index or GICS-sector funds only)
that this pre-registration did not state. A future-agnostic version would have
to write down the breadth rule (e.g. "S&P/MSCI/Russell index or Select Sector
fund", or holdings >= 100) — untested, and it would need its own pre-registration.

## Q2 — new listings in the night leg: EXCLUDE dead (harmful); UP-WEIGHT dead after verification (was borderline; see Verifier notes: the effect is a split-adjustment lookahead)

1,876 of 11,169 V7 night-pool trades (16.8%) are in names less than 252
sessions old; 743 of 9,338 post-2017 new symbols match the de-SPAC rule.

Per trade, next-open return net of tier (bp), flagged vs seasoned, day-clustered t:

| flag | 2021-23 | 2024-26 | 2021-26 pooled | 2017-20 proxy (close signal) | 2021-26 proxy |
|---|---|---|---|---|---|
| F1 age < 252 | +20.2 vs +1.4 (diff +18.8, t 0.68) | +57.1 vs -1.5 (+58.6, t 2.05) | +45.1, t 2.07 | 87.0 vs 104.0 (**-16.9**, t -0.39) | +48.3, t 2.04 |
| F2 age < 63 | +3.3 vs +3.7 (-0.4, t -0.01) | -2.4 vs +11.2 (-13.6, t -0.30) | -8.0, t -0.26 | -18.4, t -0.30 | +1.9, t 0.07 |
| F3 de-SPAC | +30.2 vs +3.0 (+27.2, t 0.68) | +17.6 vs +10.2 (+7.3, t 0.19) | +15.8, t 0.55 | n = 2 | +29.1, t 1.21 |

V7 book, CAGR / Sharpe / maxDD (2021-23 | 2024-26):

| variant | 3bp | tier | tier_hi | EH 5y MC $3k+1k (tier_hi): median, P(DD>30), P(DD>50) |
|---|---|---|---|---|
| shipped V7 | 58.2 / 2.57 / -9 \| 60.8 / 2.21 / -12 | 49.7 \| 47.6 | 43.4 / 2.04 / -10 \| 38.1 / 1.54 / -14 | $101.1k, 22%, 0% |
| F1 EXCLUDE | 52.2 \| 42.7 | 44.6 \| 32.1 | 38.8 \| 24.3 / 1.15 / -16 | $91.2k, 26%, 1% |
| F1 UP-WEIGHT 2x | 59.1 \| 67.2 | 49.2 \| 53.7 | 43.8 / 2.02 / -11 \| 44.1 / 1.64 / -13 | $103.6k, 23%, 0% |
| F2 EXCLUDE | 56.4 \| 58.4 | 48.1 \| 46.1 | 42.4 \| 36.9 | $99.9k, 19%, 0% |
| F2 UP-WEIGHT 2x | 59.6 \| 61.3 | 49.8 \| 47.7 | 44.1 \| 38.6 | $101.2k, 24%, 0% |
| F3 EXCLUDE | 55.9 \| 58.4 | 47.8 \| 45.5 | 41.7 \| 36.6 | $98.9k, 22%, 0% |
| F3 UP-WEIGHT 2x | 59.2 \| 61.2 | 49.9 \| 47.7 | 44.3 \| 38.1 | $102.0k, 22%, 0% |

Exclusion placebo (drop the same number of random same-vol-decile names, 200
seeds, tier_hi, CAGR change 2021-23 / 2024-26): F1 real -4.6 / -13.9pp vs
placebo p50 -2.3 / -0.6 (real at the 2nd / 0th percentile); F2 -1.1 / -1.2 vs
-0.4 / -0.7; F3 -1.7 / -1.6 vs -0.2 / -0.1. Roth b1 tier_hi: shipped 31.3 / 33.9,
F1 exclude 27.0 / 20.4. Worst day / month: F1 up-weight -6.8% / -10.2% vs
shipped -6.0% / -10.3%. 2022 window +37.2% vs +34.9%; Apr 2025 +5.9% vs +6.1%.

POST-HOC diagnostics on F1 (can at most be shadow):
- by year, flagged-minus-seasoned (bp): 2021 +66, 2022 -8, 2023 -17, 2024 +17,
  2025 +38, **2026 +87 (t 2.16)**. The effect is mostly 2025-26.
- winsorised at +-20%: +11.5bp (t 0.46) 2021-23, +48.5bp (t 2.04) 2024-26. The
  top-10 flagged names hold 83% of flagged P&L in 2024-26 (TDIC, FCHL, ZDAI,
  RBNE, SMCL, IBO: tiny foreign IPOs plus a levered single-stock ETF).
- the age 63-252 band alone: +27bp (t 0.84) / +79bp (t 2.59). The first 63
  sessions (lockup, IPO-window flow) are not special.
- matched up-weight placebo (2x on random same-decile names, 200 seeds):
  real +0.38 / +5.96pp vs placebo p90 +0.36 / +1.27 (90th / 100th pct).
- EH CAGR taxable 18.1 -> 19.2%; Roth b1 (history, tier_hi) 32.5 -> 35.5%
  (31.3 / 33.9 -> 31.8 / 39.7).

Against the pre-registered bar: F1 up-weight passes the pooled |t| >= 2 test,
gains at tier_hi in both halves (+0.4 / +6.0pp) and beats the placebo. It FAILS
on sign: the 2017-20 holdout proxy is -17bp, 2021-23 is t 0.7, and at tier the
2021-23 book gain is negative (-0.5pp). So **borderline**, not adopt.
EXCLUDE is **dead**. The finding worth keeping: in 2024-26 the seasoned night
pool nets about 0 at tier (-1.5bp per trade). **The 2024-26 night edge is
carried by names listed in the last year** — the 2025-26 wave of tiny foreign
IPOs. That is a concentration risk for the night leg (a listing-rule change,
e.g. the 2025 Nasdaq proposals to tighten small-IPO listing standards, could
remove it), not a reason to size up.

## Q3 — new ETF launches: L1 passes only at 3bp, and the pattern is bid-ask bounce: DEAD in practice; L2 confirms the attention story

Equity ETFs aged 10-252 sessions with price >= $10 and ADV >= $1M (7 / 26 / 52 of
them a day in 2016-20 / 2021-23 / 2024-26).

| L1 overnight basket | 2016-20 | 2021-23 | 2024-26 | NW t |
|---|---|---|---|---|
| @3bp | 13.8 / 1.16 / -30 | 8.4 / 0.88 / -14 | 14.6 / 1.29 / -12 | 3.75 |
| @tier | -9.6 / -0.80 / -61 | -15.4 / -1.66 / -43 | -9.7 / -0.87 / -29 | -3.45 |
| @tier_hi | -21.8 / -2.03 / -78 | -27.0 / -3.17 / -62 | -21.4 / -2.13 / -50 | -7.81 |
| POST-HOC ADV >= $10M @3bp | 11.3 / 0.89 / -20 | **-2.5 / -0.16** / -25 | 12.3 / 0.92 / -20 | (6 funds/day) |
| POST-HOC ADV >= $50M @3bp | 9.6 / 0.72 / -13 | **-2.1 / -0.24** / -14 | 11.6 / 0.77 / -16 | (0.7 funds/day) |

Placebo (seasoned funds, same vol20 decile, 50 seeds, 3bp) Sharpe p90: 0.23 /
-0.82 / 0.60, so the real basket is at the 100th percentile in every period;
the same holds against a post-hoc $volume-decile placebo (p90 0.12 / -0.76 / 0.32).
Gross bp per fund-day: overnight new +13.8 / +9.2 / +11.7 vs seasoned +5.7 /
+2.2 / +6.4; intraday new -4.9 / -9.3 / -6.2 vs seasoned +0.2 / +0.2 / +0.6.

That is the signature of bid-ask bounce in thin funds (the daily "open" of a
$1-10M-ADV fund is often a first trade at the ask; the close prints near the
bid). Overnight and intraday roughly cancel, the effect disappears in 2021-23
once ADV >= $10M, and a 3bp cost is not credible for these funds: the 3bp was
measured on liquid night-leg auctions. The pre-registered bar is met only at
3bp and fails at tier and tier_hi, so the verdict is **dead**. No shadow orders.
L2 (descriptive): session 21 -> 252 return after launch minus SPY, 1,947 funds
2016-25: mean -4.2%, median -5.2%, 29% beat SPY; the 2023 cohort was worst
(-10.5% mean, 15% beat). The Ben-David et al. result reproduces. It supports
the age >= 252 filter; there is no long-only trade in it.

## Verdict

- Q1 rule-based IBS universe: **dead.** Keep EQ18. The future-agnostic
  replacement has to encode breadth, not liquidity + momentum.
- Q2 new listings, night leg: EXCLUDE **dead** (costs 4.6 / 13.9pp at tier_hi).
  UP-WEIGHT 2x **dead** (verifier downgrade from borderline). It fails the pre-registered
  sign bar, and the pre-registration says "otherwise dead". Its 2024-26 gain comes from
  names that were under $1-$2 raw at the time and look like $10-$1,600 stocks only
  because of later reverse splits. On a raw-price pool it loses 2021-23 (-1.5pp tier_hi).
  Logging `listing_age_sessions` costs nothing and is optional, not a shadow test.
- Q3 new ETF launches: **dead** (a bid-ask-bounce artifact; passes only at 3bp).

Variants evaluated: 18 (Q1 4 + 1 post-hoc; Q2 6 + 3 post-hoc diagnostics
(winsorised, age band, by-year) + matched placebo; Q3 2 + 2 post-hoc floors).
Q1 was rerun twice for the hygiene fixes, with the same numbers to 0.1pp after
the second.

## do NOT redo

| idea | verdict | why |
|---|---|---|
| Rule-based IBS universe (all liquid equity ETFs, corr-dedupe, momentum top-3) | **dead** | picks narrow theme funds at momentum peaks; -6..-12pp book CAGR 2021-23 vs EQ18; EQ18's edge is breadth, not only hindsight (add. 36) |
| Night leg: exclude new listings (< 252 / < 63 sessions, de-SPACs) | **dead** | young names carry the 2024-26 night edge; excluding them costs -14pp CAGR (placebo 0th pct) (add. 36) |
| Night leg: up-weight new listings 2x | **dead** | 2017-20 sign negative. The 2024-26 +6pp came from 5 names, 16 trades, that were sub-$2 raw (reverse-split adjusted): on a raw-price pool it is -1.5 / +1.9pp at tier_hi, 2024-26 t 1.8 (add. 36) |
| New-ETF overnight basket (first year) | **dead** | bid-ask bounce in thin funds: +10bp overnight / -7bp intraday; positive only at 3bp, gone at ADV >= $10M (add. 36) |
| Night pool price >= $5 filter on split-ADJUSTED bars (adjustment='all') | **bug (repo-wide)** | 16% of shipped V7 night-pool trades were raw < $5 at the time; they are lookahead winners. Removing them cuts V7 tier_hi 43.4/38.1 -> 36.1/28.2 (add. 36 verifier; fixed in add. 30) |
| Classify by CURRENT asset name on old bars | **bug** | the panel keeps delisted names at volume 0 and tickers get reused (INFO, FB, PCLN): split listings first (add. 36) |

## Verifier notes (adversarial pass, 2026-09-28)

Re-ran Q2 from the study's cache: every Q2 number reproduces exactly. Added
`research/sim/new_listings_verify.py` (POST-HOC checks; `--raw` runs V6). It reads
raw SIP daily closes for the pool symbols (2,545 returned), fetched once to
`scratchpad/nl_rawclose.pkl` (alpaca `adjustment='raw'`).

1. **Clustering.** F1 2024-26: t by day 2.05, by symbol 2.29, two-way 2.00. Pooled
   two-way is 2.04. Clustering does not change the picture.
2. **Concentration (fatal for up-weight).** Take the flag off only the top-5 flagged names
   (TDIC, FCHL, ZDAI, RBNE, SMCL; 16 trades out of 1,260). The 2024-26 diff drops to 22bp
   (t 0.80), and the up-weight book gain falls to +0.17pp at tier_hi. Without the top-10
   it is -0.1bp and -2.9pp. Removing those 5 names from the SHIPPED pool alone costs V7
   9.4pp of 2024-26 tier_hi CAGR (38.1 -> 28.7); removing the top-10 costs 13.9pp.
3. **Split-adjustment lookahead (fatal; a repo-wide bug).** The panel and the night
   pool come from bars fetched with `adjustment='all'`, which applies later reverse
   splits back to old bars. The top names were penny stocks at the time. TDIC was
   $0.54 raw on 2025-10-16 but $66.88 in the panel (x125). FCHL was $0.23-1.46 (x30),
   ZDAI $1.65 (x16), IBO $0.87 (x12.6), IVF $1.21 (x5), RBNE $5.52 (x75). The live $5
   floor would have rejected them. Of all shipped V7 night-pool trades 2021-26, 16.3%
   had a raw close under $5, and 27.7% carry an adjustment factor above 1.5. Those
   sub-$5 trades net +50bp (seasoned) and +154bp (flagged) per trade at tier in 2024-26.
   The rest of the pool nets -12.8bp (seasoned) and +36.9bp (flagged).

   | V7 CAGR 2021-23 / 2024-26 | 3bp | tier | tier_hi |
   |---|---|---|---|
   | shipped (adjusted-price pool) | 58.2 / 60.8 | 49.7 / 47.6 | 43.4 / 38.1 |
   | raw price >= $5 pool | 49.5 / 46.4 | 42.0 / 35.9 | 36.1 / 28.2 |
   | raw pool + F1 up-weight 2x | 48.0 / 48.0 | 40.5 / 37.7 | 34.6 / 30.1 |
   | raw pool + F1 exclude | 47.2 / 34.3 | 40.5 / 25.9 | 35.2 / 19.3 |

   On the raw pool the F1 diff is +5.0bp (t 0.20) in 2021-23 and +49.7bp (two-way
   t 1.84) in 2024-26. The up-weight loses 1.5pp in 2021-23 at every cost, so it fails
   "both halves positive". **Q2 up-weight: dead.** Exclude stays dead: it is still
   harmful in 2024-26. The raw close stands in for the 15:50 decision price, and 0.8%
   of trades have no raw bar.
4. **Pre-registration.** The stamp (20:52:50) precedes the cache build (20:55) and every
   output file (20:58+). The up-weight was pre-registered. But its bar reads "Otherwise
   dead", and the study's "borderline" label overrode that bar. Downgraded.
5. **Q1 / Q3.** Both are dead and stay dead. The ETF listing split cuts all history before
   a symbol's LAST break, including breaks that happen after the decision date. That
   is mild lookahead, and it shrinks the rule universes, which does not flip a dead
   result. The Q1 $10 and Q3 $10 price floors also use adjusted prices; ETFs rarely
   reverse-split, so the effect is small.
6. **Action for the orchestrator (outside this study's scope).** Rebuild
   `night_candidates()` / `book.night_days` with an as-of RAW price for the $5 floor and
   the price-based cost tier. Then re-state the 2024-26 night-leg numbers in every addendum
   that relies on them. The live bot sees raw prices, so its night edge should be expected
   to look like the raw-pool row (tier_hi 36 / 28), not the shipped row (43 / 38).

Verifier variants: 6 (two-way clustering, drop top-5, drop top-10, drop names from the
shipped pool, raw-price pool, raw pool x F1 actions). Study total: 18 + 6 = 24.


# Addendum 37 — regime robustness (walk-forward refits, edge-decay detectors, drift monitor): report; auto de-risk dead (2026-09-28)

## Pre-registration (stamped `Mon Sep 28 20:52:14 PDT 2026`, before any 2024-26 number was computed)

**Mechanism / why ask.** Every shipped parameter was chosen by someone who had seen most of
2021-26. If the edges are structural (liquidity provision into the close for night/IBS,
intraday momentum from hedging flows for noise/conviction), the shipped values should sit on a
flat plateau and an honest annual refit that only sees the past should land on or near them. If
the shipped values carry hindsight, the walk-forward book trails the fixed book and the gap is an
honest haircut for the whole book. Separately, every edge can decay (crowding, 0DTE flow
changes); the live kill rules (`signals.KILL_*`: cumulative t < -1 with a losing mean after
100/120/60/60 round trips) only fire on a *losing* leg judged over *all* live history, so a leg
that halves or goes to zero after a good start may never trip them.

**Q1. Walk-forward refits** (expanding window; the value for year Y is chosen on data <= Y-1;
selection criterion fixed now: highest **Sharpe of the unit leg's daily return** at 3bp night
cost (ETF legs at their sim costs); ties within 0.02 Sharpe go to the shipped value). One
parameter at a time, others at shipped, then all refit together. Grids (5 values max):
- night depth `day_ret_max`: -0.06, -0.07, -0.08*, -0.09, -0.10 (honest 15:50 pool, 2021-02+)
- night IBS max: 0.05, 0.075, 0.10* (the pool was built at IBS < 0.10, so only tighter values exist)
- night vol20 min: 0.40, 0.50, 0.60*, 0.70, 0.80
- night tilt k: 0, 0.125, 0.25*, 0.375, 0.50
- ETF IBS max: 0.10, 0.15, 0.20*, 0.25, 0.30
- ETF IBS top_k: 2, 3*, 4, 5, 6
- noise lookback (QQQ and SMH separately): 7, 10, 14*, 20, 28
Trade years: night 2022-2026 (first fit on 2021 only); ETF legs 2018-2026 (IBS signals start
2017; minutes 2016). Report per-leg pp/yr WF minus fixed, and the V7 book (Sim.replay, 3bp /
tier / tier_hi) with WF-stitched legs vs fixed over 2022-26. **Reading:** |book WF - fixed| <=
2pp/yr in both 2022-23 and 2024-26 = robust; WF worse by more = hindsight haircut of that size.

**Q2. Edge-decay detectors**, per leg (night per-night leg return; IBS per held day; noise QQQ,
noise SMH per active session; conviction per trade; oversold V6 per trade):
- D1 one-sided CUSUM: S_t = max(0, S_{t-1} + (mu0/2 - x_t)/sd0), mu0/sd0 = fit-period mean/sd;
  warn at h/2, alarm at h. h = smallest of {2,3,4,6,8,10,12,16,20,25,30} with <= 1 false alarm per
  5 years (with reset) on 21-day-block-bootstrapped intact fit-period paths (500 paths).
- D2 rolling-N t-stat vs mu0: N = 60 events; alarm when t < -c, c = smallest of
  {1.5, 2.0, 2.5, 3.0, 3.5} with the same false-alarm target.
- K  live kill emulation: cumulative t < -1 with mean < 0 after n_min (100/120/60/60) events
  (per-name trades for night, as live).
Calibrate on 2021-23 (night, oversold: history too short otherwise) / 2016-2020 (ETF legs),
judge false alarms on the other span, and detection delay (median / P(detect within 1y)) when
the edge is set to 0 or halved at a random changepoint (subtract the full-sample mean, or half
of it, from every event after tau), 200 random taus.
**Pass bar for a de-risk rule:** out-of-sample false alarms <= 1 per leg per 5 years AND median
delay to alarm for edge -> 0 under 1 year AND, on the V7 book 2021-26, the rule costs <= 1pp/yr
when nothing decayed. Adopt-able at most as SHADOW (it never fired on real data by construction
of the pass bar; its value is insurance).

**Q3. Is any leg already decaying?** Calendar-year Sharpe per leg 2016-2026 (night 2021+),
OLS trend of daily return on time with Newey-West (21 lags) t-stat; noise legs also 2016-21 vs
2022-26 (0DTE era) mean difference with NW t. Decay flagged if slope t < -2.

**Q4. Live vs backtest drift monitor**: a spec only (the logs are on the server).

No new leg is proposed; nothing here changes live trading. Variants: 7 parameter grids x their
values (34) + joint WF + 3 detectors x 6 legs + de-risk rule on the book (1).

---

## How to run

    # once, under the heavy lock: 20d returns for the depth pool's symbols (the dedupe input)
    PYTHONPATH=. .venv/bin/python -m research.sim.regime_robust --extract
    PYTHONPATH=. .venv/bin/python -m research.sim.regime_robust        # ~6 min with legs cached (~9 min cold)

`research/sim/regime_robust.py`. Legs are rebuilt through the live `signals` functions (night from the
honest 15:50 pool `depth_cands.pkl`, 0.7 dedupe, crowding, weekend half size; IBS via `book.ibs_days`;
noise via `book.noise_days`). Book = shipped V7 (`growth.V7` + `cfg(1.0, 0.5, 2)`: overnight 1.0x, TQQQ at 75%
-> intraday cap 0.75, conviction 0.5).

## Q1. Walk-forward refits: the shipped values carry ~6pp/yr of hindsight

Value chosen per year (expanding window, highest leg Sharpe up to Y-1; shipped value in brackets) and the
unit leg, WF minus fixed, over the trade years:

| parameter | choices by year | leg WF vs fixed | full-sample leg Sharpe by value |
|---|---|---|---|
| night depth [-8%] | 22:-6 23:-7 24:-7 25:-7 26:-8 | 50.3 vs 53.3%, **-3.0pp** | -6:1.35 -7:1.49 **-8:1.54** -9:1.38 -10:1.30 |
| night IBS [0.10] | 22:.075 23:.10 24-25:.075 26:.10 | 40.9 vs 53.3%, **-12.4pp** | .05:1.07 .075:1.56 **.10:1.54** |
| night vol20 [0.60] | 22-25: 0.40, 26: 0.60 | 53.3 vs 53.3%, 0.0 | .4:1.56 .5:1.55 **.6:1.54** .7:1.54 .8:1.42 |
| tilt k [0.25] | 22:.25 23:.50 24:.25 25-26: 0 | 47.0 vs 53.3%, **-6.4pp** | 0:1.59 .125:1.53 **.25:1.54** .375:1.51 .5:1.49 |
| ETF IBS max [0.20] | 18:.3 19-20:.1 21-22:.2 23-26:.25 | 20.3 vs 20.7%, -0.4pp (2018-20 -6.5, 2024-26 +8.0) | .1:1.16 .15:1.15 **.2:1.24** .25:1.35 .3:1.22 |
| IBS top_k [3] | 18:5 19-20:4 21-25:3 26:4 | 18.5 vs 20.7%, -2.2pp (all in 2018-20) | 2:1.20 **3:1.24** 4:1.27 5:1.18 6:1.20 |
| noise lookback QQQ [14] | 18-19:7 20:14 21-22:7 23:20 24-26:14 | 8.3 vs 9.0%, -0.7pp | 7:1.10 10:0.94 **14:1.19** 20:1.13 28:1.08 |
| noise lookback SMH [14] | 18:20 19-26:10 | 8.0 vs 7.8%, +0.3pp | 7:1.01 10:1.04 **14:0.95** 20:0.88 28:0.92 |

**V7 book 2022-26 with the walk-forward legs stitched in** (CAGR/Sharpe per half, full CAGR/Sharpe/maxDD):

| | 3bp 2022-23 | 3bp 2024-26 | 3bp 2022-26 | tier 2022-26 | tier_hi 2022-26 |
|---|---|---|---|---|---|
| fixed (shipped) | 52.8/2.30 | 59.7/2.19 | **56.7/2.23/-12** | 45.9/1.89/-13 | 38.2/1.63/-14 |
| WF night depth | 52.8/2.28 | 59.1/2.16 | 56.4/2.20/-12 | 44.5/1.83/-13 | 36.3/1.56/-14 |
| WF night IBS | 50.2/2.22 | 50.4/1.94 | 50.3/2.05/-12 | 41.1/1.75/-13 | 34.1/1.51/-14 |
| WF night vol20 | 55.0/2.37 | 59.8/2.20 | 57.8/2.26/-12 | 46.1/1.89/-13 | 37.9/1.62/-14 |
| WF tilt k | 52.0/2.26 | 55.5/2.19 | 54.0/2.22/-13 | 43.6/1.87/-14 | 35.5/1.59/-15 |
| WF ETF IBS max | 51.5/2.26 | 64.3/2.31 | 58.8/2.28/-12 | 47.8/1.94/-13 | 40.3/1.70/-14 |
| WF IBS top_k | 52.8/2.30 | 59.5/2.19 | 56.6/2.23/-12 | 45.7/1.89/-12 | 38.1/1.63/-13 |
| WF noise QQQ | 50.6/2.21 | 59.2/2.18 | 55.5/2.19/-12 | 44.8/1.85/-13 | 37.3/1.60/-14 |
| WF noise SMH | 51.8/2.26 | 61.1/2.23 | 57.1/2.23/-12 | 46.3/1.90/-13 | 38.4/1.64/-14 |
| **WF all (joint)** | **46.2/2.00** | **54.5/2.16** | **50.9/2.09/-15** | **38.8/1.69/-18** | **30.2/1.38/-21** |
| placebo: random grid value per year (20 draws) | 49.9 | 46.1 | 47.6/2.00 (range 37.1..54.8) | | |
| POST-HOC WF by mean return, joint | 44.0/1.91 | 57.6/2.12 | 51.7/2.03/-15 | | 31.7/1.38/-21 |
| Roth b1 fixed | 40.0/2.25 | 54.6/2.18 | 48.2/2.18/-12 | | 30.0/1.49/-14 |
| Roth b1 WF joint | 31.1/1.72 | 50.2/2.17 | 41.8/1.99/-13 | | 23.0/1.22/-18 |

- **Robust (|WF - fixed| <= 2pp in both halves):** night depth, night vol20 (WF slightly better), IBS top_k,
  noise SMH lookback. **Not robust:** night IBS (-2.6 / -9.3pp: a 2021-only fit picks 0.075, which deploys less),
  tilt k (-0.8 / -4.2: the history never clearly preferred 0.25 over 0), noise QQQ lookback (-2.2 / -0.5; the
  grid is jagged: 10 is worse than both 7 and 14), and ETF IBS max (-1.3 / **+4.6**: history keeps preferring
  0.25; see post-hoc note).
- **Honest haircut for the whole book: -5.8pp/yr at 3bp (both halves: -6.6 / -5.2), -7.1 at tier, -8.0 at
  tier_hi; Sharpe -0.14 / -0.20 / -0.25; maxDD -12 -> -15% (3bp), -14 -> -21% (tier_hi). Roth: -6.4pp (3bp),
  -7.0pp (tier_hi).** The random-value placebo loses 9.1pp, so a refit recovers only ~1/3 of the distance
  from "random" to "shipped": the parameters are neither pure luck nor learnable year to year. Plan on the
  shipped book at ~90% of its backtest CAGR (on top of edge-halves, which already cut far more).
- POST-HOC, not a change: a mean criterion gives the same haircut (-5.0pp at 3bp, -6.5 tier_hi), so the
  night-IBS gap is not a Sharpe-criterion artifact. ETF IBS max 0.25 beats 0.20 over 2016-26 (1.35 vs 1.24)
  and WF adopted it from 2023 (+4.6pp on the 2024-26 book); it is a candidate for a future pre-registered
  test, not a change (one parameter, found by looking).

## Q2. Edge-decay detectors: the information is slow, and the legs earn most right after a drawdown

Per-event t-stats are small (mu/sd per event: night 0.086, IBS 0.130, noise QQQ 0.093, SMH 0.035, conviction
0.052, oversold 0.106), so any detector at <= 1 false alarm per 5 years needs ~1-3 years to see the edge gone.

| leg | events/yr | fit mu / sd (bp) | CUSUM h (P any FA in 5y) | OOS FA/5y | roll-60 t c | OOS FA/5y |
|---|---|---|---|---|---|---|
| night (per night, 3bp) | 241 | +12.1 / 141 | 20 (54%) | 0.0 (reverse 0.0) | 2.5 | 0.0 |
| IBS (per held day) | 82 | +19.7 / 151 | 12 (66%) | 1.7 (reverse 1.3) | 2.5 | 0.0 |
| noise QQQ (per session) | 148 | +6.2 / 67 | 16 (54%) | 0.9 (reverse 1.0) | 3.0 | 0.9 |
| noise SMH | 143 | +2.8 / 80 | 20 (58%) | 0.0 (reverse 2.0) | 2.0 | 0.0 |
| conviction (per trade) | 74 | +9.7 / 188 | 16 (61%) | 0.0 (reverse 1.0) | 2.0 | 0.0 |
| oversold V6 (per trade) | 37 | +9.7 / 92 | 12 (46%) | 0.0 (reverse 1.5) | 1.5 | 0.0 |

Detection delay, years from the changepoint to the first alarm (real data, 200 random changepoints |
bootstrap: 1y intact then 5y decayed): median, P(within 1y)

| leg | edge -> 0: CUSUM | roll-t | live KILL | halved: CUSUM | edge flips to -mu: CUSUM | live KILL |
|---|---|---|---|---|---|---|
| night | 0.95y 52% / 0.62y 70% | never 55% | **never (100%)** | 1.6y 4% / 1.4y 37% | 0.33y 100% | never 55% / 2.1y |
| IBS | 1.2y 38% / 0.8y 60% | 1.4y 34% | never 95% | 1.6y 28% | 0.55y 91% | 4.4y / 2.2y |
| noise QQQ | 1.6y 32% / 0.9y 62% | 2.8y 14% | never 100% | 2.3y 6% | 0.49y 84% | never 58% / 2.0y |
| noise SMH | 1.3y 37% / 1.4y 35% | 1.5y 35% | never 98% | 2.0y 19% | 0.70y 72% | never 52% / 2.6y |
| conviction | 2.7y 20% / 1.8y 30% | 1.5y 28% | never 100% | 2.8y 16% | 0.96y 54% | never 56% / 2.7y |
| oversold | 3.1y 14% / 2.6y 10% | 1.8y 18% | never 91% | never | 0.98y 51% | 4.4y / 2.0y |

- **The live kill rules (`KILL_*`) cannot see an edge that goes to zero or halves** (they need a losing
  cumulative mean), and when a leg starts LOSING as much as it used to make they take a median ~2-4 years
  (or never, on real data with a good prefix) because they judge cumulative live history. CUSUM sees the
  same flip in 0.3-1.0 years. They are not too tight; they are slow and blind to decay by construction.
- The night kill counts per-name round trips: 10,819 names (1,865/yr), mean +16.4bp, naive t 2.8 vs the
  day-clustered per-night t 3.6 (tilted weights) -- not over-stated here, but `min_trades=100` names is only
  ~3 weeks of nights: a kill verdict at 100 names is noise either way.

**De-risk rule (pre-registered `derisk_step`: 0.5 at CUSUM >= h/2, 0 at h, latched, recover when shadow S
returns to 0, then 60 events at 0.5) on V7 2021-26:**

| | 2021-23 | 2024-26 | full | EH full | MC $3k+1k/mo (EH): median, P(DD>30/50) | $10k lump median |
|---|---|---|---|---|---|---|
| V7 3bp | 57.0/2.53 | 59.3/2.17 | 58.1/2.33/-12 | 25.1/1.19/-18 | $120k, 10% / 0% | $30.7k |
| + de-risk 3bp | 48.0/2.30 | 40.6/1.84 | 44.4/2.06/-11 | 14.2/0.81/-19 | $91k, 17% / 0% | $19.5k |
| V7 tier_hi | 42.1/1.99 | 37.1/1.51 | 39.7/1.73/-14 | 17.6/0.89/-20 | $100k, 23% / 0% | $22.6k |
| + de-risk tier_hi | 34.4/1.75 | 21.1/1.10 | 27.8/1.42/-12 | 7.6/0.49/-22 | $77k, 32% / 2% | $14.5k |
| POST-HOC soft (0.5 only while S >= h) 3bp | 56.0/2.51 | 57.7/2.15 | 56.8/2.31/-13 | 24.0/1.16/-18 | $117k, 11% / 0% | $29.4k |
| POST-HOC soft tier_hi | 41.2/1.97 | 35.7/1.48 | 38.5/1.70/-14 | 16.6/0.85/-20 | $97k, 23% / 0% | $21.6k |

Crash episodes: 2022 bear +46.8% -> +45.3% (3bp); Apr 2-8 2025 +6.3% -> +2.9%; worst day -5.9 -> -5.5%, worst
month -9.6 -> -10.5%. COVID 2020 not scored (the night detector has no pre-2021 honest history to run on).
With a leg's edge set to exactly 0 from 2024-01-02, de-risking still LOSES (3bp, 2024-26 CAGR): night 21.3 ->
18.8%, IBS 44.8 -> 43.5, noise QQQ 56.0 -> 55.5, SMH 54.1 -> 51.5, conviction 51.0 -> 48.1. **Why: every leg
earns more right after its own drawdown** (mean contribution while the rule is de-risked vs at full size,
bp/day: night +19.0 vs +6.9, IBS +4.3 vs +0.8, SMH +5.2 vs +1.9, conviction +8.9 vs +3.3; QQQ +0.3 vs +1.7).
These are liquidity/reversal edges: their losing streaks are the stress that pays the next rebound, so a
statistical de-risk sells the rebound. It fails the pass bar (-13.7pp/yr at 3bp when nothing decayed, vs
<= 1pp); the soft variant costs 1.3pp/yr and saves nothing either. **Dead.**

## Q3. Is any leg already decaying? No (none with trend t < -2)

Calendar-year Sharpe of the unit leg; OLS trend of daily return on time, Newey-West(21) t; 2022-26 minus
2016-21 mean:

| leg | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 | 26 | trend t | post-2022 diff bp/day (t) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| night | | | | | | 1.17 | 1.84 | 0.99 | 1.49 | 2.44 | 1.09 | +1.37 | +7.8 (+0.88) |
| IBS | | -0.04 | 0.45 | 1.40 | 2.43 | 1.65 | 0.24 | 1.56 | -0.11 | 1.40 | 3.15 | +1.44 | -0.4 (-0.10) |
| noise QQQ | -0.10 | 0.33 | 3.02 | 0.23 | 1.46 | 0.98 | 1.60 | 2.09 | 1.04 | 0.58 | 0.39 | -0.13 | +0.3 (+0.22) |
| noise SMH | 1.61 | 0.83 | 1.17 | -0.93 | -0.05 | 2.98 | 1.67 | 0.37 | 0.77 | 1.49 | -0.81 | +0.13 | +0.4 (+0.22) |
| conviction | 0.67 | 0.48 | 1.84 | -0.05 | -1.12 | 1.40 | 1.92 | 0.52 | 1.36 | -0.29 | 1.03 | +0.19 | +3.4 (+0.84) |
| oversold V6 | | 1.70 | 0.71 | 0.45 | 0.48 | 1.40 | 0.65 | 1.24 | 3.08 | 0.77 | 3.18 | +2.25 | +1.9 (+1.61) |

The 0DTE era did not hurt the noise legs on average (post-2022 +0.3bp/day). One **watch** item (POST-HOC,
descriptive): noise QQQ inside 2022-26 alone trends down (-1.41bp/day per year, NW t -1.81; Sharpe 2023 2.09
-> 2024 1.04 -> 2025 0.58 -> 2026 0.39; 2021-23 1.48 vs 2024-26 0.72). Below the pre-registered flag, and the
CUSUM for noise QQQ has not alarmed; but it is the leg to watch. Every leg has had a Sharpe < 0.3 year
(IBS 2024, SMH 2019/2026, conviction 2020/2025) and recovered: a bad year is normal, not decay.

## Q4. Live vs backtest drift monitor (for `make review`; logs are on the server)

Reference: `regime_robust.drift_report(live, backtest)`. Per leg, from `logs/daily-*-live.jsonl` (fills) and
the book's closed round trips:
1. **Pair every live round trip with its backtest twin**: replay `research.sim` for the same entry dates
   (night: the same 15:40 pool through `signals.loser_picks` / `night_sizing`; IBS: `ibs_days`; noise: `noise_days`
   on that session's minutes; conviction: `breakout_days`), key `(leg, entry_date, sym)`. Report n paired, mean
   live, mean backtest, **paired gap (bp) with t**, and the unmatched share (live-only or backtest-only names =
   selection drift, reported separately from execution drift).
2. **Split the gap**: buy cost + sell cost vs the official auction prints (review section 4 already does this for
   night), and the residual (price/signal drift). A residual |t| > 2 after >= 50 pairs is a bug hunt, not a verdict.
3. **Place live in the backtest distribution**: live per-event mean vs the leg's `CAL` mu0/sd0 (this file), as a
   z = (live mean - mu0) / (sd0 / sqrt(n)); and the CUSUM S/h as a **review-only warning line** (no trading effect).
4. Per leg, show the `KILL_*` status next to it (unchanged; nothing here loosens it).

## Verdict

- Walk-forward: **report**. Depth, vol20, top_k, SMH lookback are robust; night IBS, tilt k and QQQ lookback
  carry hindsight. Book haircut ~-6pp/yr (3bp) to -8pp/yr (tier_hi), Sharpe -0.14 to -0.25.
- Automatic de-risk (pre-registered and the post-hoc soft version): **dead** (costs 1-14pp/yr, saves nothing
  even when an edge truly dies, because leg P&L mean-reverts after drawdowns).
- Kill rules: keep as they are (they are a floor against a *losing* leg, not a decay detector). A CUSUM line in
  the review is a free diagnostic; a faster kill (CUSUM referenced at 0) would need its own pre-registration.
- No leg is decaying; noise QQQ 2024-26 is a watch.

Do NOT redo:

| idea | verdict | why |
|---|---|---|
| Walk-forward annual refit of leg parameters (depth, IBS, vol20, tilt k, top_k, noise lookback) | **report / dead as a method** | joint WF book -5.8pp/yr (3bp), -8.0 (tier_hi) vs shipped; random-value placebo -9.1: refits recover 1/3; use as a haircut (add. 37) |
| Automatic de-risk on leg CUSUM / rolling-t (0.5 on warn, 0 on alarm, or 0.5 on alarm) | **dead** | costs 1.3-14pp/yr with nothing decayed: per-event t is 0.04-0.13, so a CUSUM at <=1 FA/5y still false-alarms on ~half of intact 5y paths, and the latched version then needs 2-8y of shadow P&L to re-arm (IBS off 69% of days 2021-26 with no decay) (add. 37) |
| Any leg decaying 2016-26 (0DTE era for noise) | **no** | all NW trend t > -2; noise post-2022 +0.3bp/day; noise QQQ 2024-26 a watch (t -1.8 inside 2022-26) (add. 37) |

## Verifier notes (adversarial check, 2026-09-28)

- **Reproduced:** a clean rerun of `research.sim.regime_robust` gives output identical to the study's log line for line.
  The V7 baseline matches add. 29 (3bp 58.1/2.33/-12, tier_hi 39.7/1.73/-14). No lookahead found: the de-risk scale
  for day d uses only events before d (a night event is known at the next open; IBS/noise/conviction events are
  known at the close). The walk-forward for year Y uses data before Y only. Pre-reg stamp 20:52; the first run log is from 21:03.
- **The WF haircut is not robust in size (POST-HOC sensitivity, `research/sim/regime_robust_verify.py`).** The
  night-IBS grid is one-sided, so any refit there deploys less. Leaving it out of the joint refit:

| joint WF 2022-26 | 3bp 2022-23 | 3bp 2024-26 | 3bp full | tier_hi full |
|---|---|---|---|---|
| fixed | 52.8/2.30 | 59.7/2.19 | 56.7/2.23/-12 | 38.2/1.63/-14 |
| all (study) | 46.2/2.00 | 54.5/2.16 | 50.9/2.09/-15 (-5.8) | 30.2/1.38/-21 (-8.0) |
| ex night IBS | 46.5/2.00 | 60.0/2.31 | 54.1/2.18/-13 (-2.6) | 30.7/1.39/-19 (-7.5) |
| ex night IBS and tilt k | 46.5/2.03 | 66.2/2.34 | 57.5/2.22/-12 (+0.8) | 35.3/1.51/-18 (-2.9) |

  So the haircut ranges from about 0 to 8pp/yr, depending on the cost and on which one or two parameters are refit.
  Only the 2022-23 half is consistently negative (about -6pp), and there the first refit had 11 months of data. Treat
  "~90% of backtest CAGR" as one plausible haircut, not a measured constant. Edge-halves stays the binding planning stress.
- **The de-risk rule: "dead" stands, but the stated reason is overstated.** It fails its own pre-registered bars
  twice: IBS OOS false alarms are 1.7 per 5y (the bar is 1), and the cost with nothing decayed is 13.7pp/yr (the bar
  is 1pp). Most of that cost comes from the design, not from the market. Recovering from a latch needs S to walk from
  h back to 0 at the intact drift (mu0/2)/sd0 = 0.017-0.065 per event. That takes 1.9y (night), 2.2y (IBS), 2.3y (QQQ),
  8.0y (SMH), 8.4y (conviction) and 6.2y (oversold). So a false alarm switches a healthy leg off for years (IBS was
  below 1.0 on 69% of days).
- The "edge set to 0 and de-risk still loses" test removes the in-sample post-2024 mean. With a fixed in-sample mean,
  a drawdown forces a better-than-average remainder, so the "earns more after its drawdown" effect is partly built into
  the test. The conditional bp/day figures (night +19 vs +7, etc.) do not appear anywhere in the script output, so
  they are unverified. The soft, unlatched variant (-1.3pp/yr, POST-HOC) is the fairer test of "de-risk on
  evidence", and it is also dead.
- The detector calibration target (mean <= 1 FA per 5y) still allows P(any FA in 5y) of 46-66%. That is fine for a
  review-only warning line, and too loose for anything that trades.
- The detector and kill-rule findings hold: KILL_* cannot fire on an edge that drops to 0 or halves, by construction.
- The variant count rises by 4 (2 joint subsets x 2 costs; the latch arithmetic is not counted as a variant): 63 -> 67.


# Addendum 38 — operations that add money (capital ramp, live cost model, earlier gate, Roth settlement): SHADOW (G1 gate log), ramp dead (2026-09-28)

## Pre-registration (stamped Mon Sep 28 20:52:24 PDT 2026, before any 2024-26 number of this study was computed)

No rule of the book changes here. The question is what the WAITING costs and whether it can be
shortened at the same error rate. Mechanism: capital that sits idle, or a lever that opens late,
earns the parked rate instead of the book's; the cost is (book - parked) x idle $ x time. The
risk of deploying early is that 26 live exits cannot yet rule out an execution problem.

**Q1. Capital deployment (Roth $7.8k, $1k cap; brokerage $3k at a $3k cap, $1k/mo deposits).**
Books: Roth b1 (IBS + night 1.0x, intraday via 3x ETFs on the night half's daytime cash, roth.py)
and taxable V7 (growth.V7, Sim.replay). Costs 3bp | tier | tier_hi. Stress = edge-halves (EH)
and "edge-zero" (every leg's mean contribution removed; variance kept) — the "live execution is
broken" scenario. Parked money: BIL (cash) and SPY (the Roth's existing ETFs), both reported.
Variants (5):
  C0 status quo: Roth cap $1k indefinitely
  C1 wait until 10-08, then deploy all
  C2 deploy all now (next close)
  C3 pre-registered ramp: cap $1k -> $2k -> $4k -> all; each step after 15 MORE night exits whose
     day-clustered 95% UB on the mean open-sell cost is <= 10bp AND whose live-minus-replay P&L
     over those days is above the 10th percentile of its simulated null band
  C4 deposits: to the book at the next close vs held for the next ramp step
Metrics: expected $ per month of the idle money at EH tier_hi (and 3bp), per half 2021-23 /
2024-26; for C1-C3 over the next 63 sessions: expected $ at EH, and $ loss P10/P5 and
P(loss > 10%) under edge-zero, bootstrap with 21-day blocks.
Pass bar for recommending C3 over C1: expected $ (EH, tier_hi) >= C1's AND the edge-zero P5
loss <= C2's. C0 vs C2 is reported as the value of the cap per month, both halves.

**Q2. cost_fit.py.** Bayesian linear model per side: bps ~ 1 + log(price) + log(ADV) +
quoted half-spread + sell + auction; prior on the intercept = the measured pooled mean, slopes
shrunk to 0 (ridge prior); day-clustered residual variance; 95% bounds on the prediction.
Emits cost(price, adv) with book.cost_bps's signature and registers "live" / "live_hi" tier
tuples. Pass: on a synthetic fixture with known coefficients it recovers them inside its 95%
bounds at n = 400, and at n = 26 it returns ~the pooled mean with a wide bound (graceful).

**Q3. An earlier lever gate at the same error rate.** Per-exit cost sd from live (~39bp),
intra-day correlation rho in {0, 0.3}. Variants (3):
  G0 the pre-registered rule: 50 exits, mean <= 10bp
  G1 G0 plus an early look at every exit day from 20 exits: open if the day-clustered mean's
     UB (critical value c calibrated by simulation) <= 10bp; c chosen so P(open by 50 | mu)
     <= G0's at mu = 10, 15, 20bp
  G2 Wald SPRT on day means, H0 mu = 15bp vs H1 mu = 3bp, alpha matched to G0's P(open|15)
Bar: false-open rate <= G0's at each bad mu, expected exits-to-open at mu = -1bp, and the $
value of opening that many days earlier (1.3x vs 1.0x, EH tier_hi and 3bp). Proposal only.

**Q4. Roth settlement** (Schwab docs): are 09:30 sale proceeds usable intraday / at the close
the same day under limited margin; can good-faith violations arise; schedule changes that avoid
them. Documentation, no numbers.

Everything else is post-hoc and at most shadow.

---

## How to run

    PYTHONPATH=. .venv/bin/python -m research.sim.ops_capital [--refresh]   # ~1.2 min, no heavy data, no lock
    PYTHONPATH=. .venv/bin/python -m research.sim.cost_fit                  # ON THE SERVER (reads logs/)
    PYTHONPATH=. .venv/bin/python -m research.sim.cost_fit --selftest DIR   # synthetic fixture, PASS/FAIL

Series cached at `<scratchpad>/cache_ops_capital.pkl`. Roth = roth.py b1 (IBS + night 1.0x,
intraday through 3x ETFs on the night half's daytime cash) replayed at a FIXED size, so whole
shares at $1k are honest. EH = growth.eh (half of each leg's mean removed); edge-zero = all of it.

## Q1. What the Roth cap costs (Roth $7.8k, $1k deployed, $6.8k idle)

Roth b1 at fixed size (2021-23 | 2024-26 | full CAGR/Sharpe/maxDD):

| size | 3bp hist | 3bp EH | tier_hi hist | tier_hi EH |
|---|---|---|---|---|
| $1,000 | 37.7/2.51 · 43.7/2.28 · 40.6/2.37/−8 | 16.2 · 21.3 · 18.6/1.23/−14 | 28.9 · 29.8 · 29.4/1.81/−10 | 13.4 · 14.2 · 13.8/0.94/−15 |
| $7,800 | 41.7/2.48 · 53.6/2.32 · 47.3/2.37/−11 | 16.5 · 26.3 · 21.2/1.21/−14 | 29.1 · 33.5 · 31.2/1.68/−13 | 12.5 · 16.4 · 14.3/0.87/−16 |

(tier: $7.8k 38.0/1.98/−12 hist, 17.3/1.02 EH.) Whole shares cost ~7pp/yr of history at $1k vs $7.8k (3bp).

$ per month of the $6.8k left idle (mean daily excess x 21, tax-free):

| parked in | cost | history 21-23 / 24-26 | **EH 21-23 / 24-26** | edge-zero |
|---|---|---|---|---|
| cash/BIL | 3bp | +192 / +230 | **+81 / +119** | −12 |
| cash/BIL | tier | +162 / +185 | +69 / +92 | −12 |
| cash/BIL | tier_hi | +139 / +150 | **+61 / +72** | −12 |
| SPY (the Roth's ETFs) | 3bp | +138 / +141 | +27 / +31 | −82 |
| SPY | tier_hi | +85 / +62 | **+7 / −16** | −82 |

So the cap costs **~$66/month (~$790/yr) if the $6.8k sits in cash**, and **~$0 if it sits in
SPY/VTI** at EH tier_hi: under edge-halves at planning costs the Roth book earns about what SPY
did (14.3% vs 15.3%) — its case over an index is the drawdown (−16% vs −24%; 2022 bear +12.9%
vs SPY −24.1%; Apr 2-8 2025 +4.8% vs −11.5%), not the return. At 3bp EH it is +$28/mo over SPY.
Full deployment, 5y MC (21-day blocks) EH: $7.8k + $625/mo median $83k (3bp) / $69k (tier_hi),
P(DD>30%) 4% / 12%, P(DD>50%) 0% / 0%; $10k lump P(DD>30%) 4% / 12%. Worst day −6.0%, worst
month −8.6% (EH tier_hi). COVID not re-run (needs the heavy panel; addendum 20's Roth crash check stands).

Next 63 sessions, $ P&L of the whole $7.8k Roth (3000 block-bootstrap paths; E = mean, P5):

| tier_hi, idle in BIL | C0 cap $1k | C1 wait to 10-08 | C2 all now | C3 ramp |
|---|---|---|---|---|
| EH world | +$89 / P5 −$26 | +$272 / −$695 | **+$295** / −$748 | +$225 / −$644 |
| edge-zero world | +$57 / −$58 | +$34 / −$933 | +$27 / −$1,016 | +$26 / −$855 |
| EH, 2021-23 blocks only (vs C0) | — | +$185 | +$210 | +$145 |
| EH, 2024-26 blocks only (vs C0) | — | +$198 | +$226 | +$148 |

(3bp: C2 +$407, C1 +$370, C3 +$305, C0 +$99. Idle in SPY: all four within $15 of each other in the EH world.)

- **C1 vs C2 (wait to 10-08 vs now): $23 per quarter.** Waiting 8 sessions costs nothing that matters.
- **C3, the evidence ramp, FAILS its pre-registered bar** (E[$] $225 < C1's $272). Why: exits
  arrive at ~6.5/day, so the cost half of the test passes almost at once; the P&L half cannot
  tell a working book from a dead one over 2-3 days — it held the ramp on 47% of EH paths and
  54% of edge-zero paths. It only buys tail protection by being slower. The cost evidence is
  already in (26 exits at −1bp); the remaining risk — the edge being smaller than the backtest —
  is not detectable in weeks at any cap. Size is a risk-appetite choice, not an evidence one.
- **C4 deposits:** a $1,000 deposit waiting w sessions loses $0.46·w (Roth, EH tier_hi) or
  $0.39·w after tax (taxable). Rule: deposits deploy at the next close (the bot already sizes
  from free equity); just don't let a `DAILY_*_CAPITAL` below the balance hold them back.

## Q2. `research/sim/cost_fit.py`

Bayesian linear model per side on official-print costs, features log price, log ADV, quoted
half-spread (from daily-decisions), sell, directed-route; intercept prior = measured −0.75bp
(sd 5), slopes prior N(0, 3²); observations down-weighted by intra-day correlation (ANOVA ICC);
day-clustered 95% UB on the pooled mean. `cost_fn(fit)` has book.cost_bps's (price, adv)
signature; `register(fit)` adds `TIERS["live"]` (mean, floored at 0) and `["live_hi"]` (95% UB)
so `Params(night_cost="live")` runs in the unmodified sim. Fills without an official print are
flagged and excluded (vs ref_px they measure drift). Self-test (synthetic fixture in the
executor's exact jsonl schema): 836 fills recover all 6 true coefficients inside their 95%
intervals; 52 fills on 4 days (the live sample) return a pooled mean −1.1bp with ±13-17bp
bounds and ~equal cost per name; empty logs return the prior. **PASS.** The laptop has no live
logs; run it on the server. Until ~200 exits it is a pooled mean — slopes need the data to insist.

## Q3. The lever gate: sooner, at the same error rate?

At 6.5 exits/day the pre-registered gate (G0: 50 exits, mean <= 10bp) reaches 50 on about the
**4th exit morning from now (~10-02)** if costs stay near −1bp — before the 10-08 checkpoint.
Simulation (per-exit sd 39bp, 6.5/day, 1500 paths, 60 sessions; P(open) | median exits):

| rule | mu −1bp | +10bp | **+15bp (bad)** | +20bp |
|---|---|---|---|---|
| G0 rolling 50, mean <= 10 (rho 0.3) | 100%, 53 | 100% | **99%** | 91% |
| G1 day-clustered UB z=1.645 <= 10, from 20 exits (rho 0.3) | 98%, 46 | 32% | **11%** | 5% |
| G1 z=1.645 (rho 0) | 100%, 28 | 32% | 6% | 2% |
| G2 SPRT 15 vs 3bp, A = ln 19 (rho 0.3) | 99%, 100 | 28% | 3% | 0% |

G0 is not a 5%-error test: because it re-checks a rolling window every day it opens AT LEAST ONCE at a true
15bp cost 95-99% of the time. (Verifier: the live gate is not latched - `lever_ok` re-runs every
check - so G0 is actually OPEN on 15% (rho 0) / 26% (rho 0.3) of sessions at 15bp, vs G1's 0-1%.) Every G1/G2 variant is stricter than G0 at bad costs, so
"calibrate to G0's error" pins c at 0; the useful one is G1 z=1.645, which is both **stricter
(11% vs 99% false-open at 15bp) and ~1 session faster** at the live cost. Value of opening
earlier: 1.3x over 1.0x is worth **$0.09/session at $3k (EH tier_hi, after tax; 2021-23 −0.09,
2024-26 +0.29)**, $0.24 at 3bp EH; $3-8/session at $100k. **Speed is worth ~$0; the case for
G1 is that it closes G0's leniency.** Proposal only: log G1 next to G0 in `make review` §2b.

## Q4. Roth settlement (Schwab, limited margin)

Sources: Schwab "Unsettled funds" (StreetSmart help): unsettled proceeds can buy "as long as the
new purchase is not sold prior to the settlement date of the original sale"; Schwab "Trading in
cash accounts: avoid these violations": a GFV is buying with unsettled proceeds and selling
before they settle, T+1 since May 2024; brokerage-review.com on Schwab's limited margin IRA:
"trade with unsettled funds", "without worrying about good-faith violations", no borrowing,
no shorting, no minimum to enroll — and "If the IRA does day trade, it will need the standard
$25,000 minimum" (pre-2026-06-04 wording; the repo records PDT retired — **confirm with Schwab**
that a <$25k limited-margin IRA may day trade the 3x ETFs). Schwab's own agreement page refused
automated fetches.

- **Same-day use: yes.** Under limited margin the 09:30 open-sell proceeds fund the 10:01+
  3x-ETF buys and the 15:40 MOC buys the same day with no GFV. Without limited margin the
  intraday leg is Schwab's textbook GFV (buy with the morning's unsettled proceeds, sell the
  same afternoon); the close-buy -> next-open-sell chain is fine even then (the next-open sale
  is ON the funding sale's T+1 settlement date, not before). The executor already refuses to
  trade the Roth unless `ROTH_LIMITED_MARGIN=yes`: keep that.
- **GFVs with the current schedule: none expected** under limited margin. The real risks are
  buying-power rejections, not violations (POST-HOC, from executor.py):
  1. **09:15 IBS buys** are sent while the night OPG sells and BIL sells are still pending.
     At a $1k cap the Roth's idle cash covers them; at full deployment a buy can exceed IRA
     buying power (Schwab does not credit unexecuted sells) — ~72 entries/yr. Fix: in the
     Roth only, send IBS entry buys at the 09:50 reconcile run; cost −1.1bp mean (sd 64bp,
     n 197): free.
  2. **15:40 MOC buys while 3x ETFs are still held (flattened 15:57).** The book ledger
     (`book.cash = capped equity − positions`, floor 0 at 1.0x) already skips night names when
     cash is short: 41% of days carry a position at 15:40, tying 26% of the night half on
     average. Research assumed full funding. Measured: 3bp hist 47.3/2.37 -> 44.5/2.46, EH
     21.2 -> 20.1; tier_hi 31.2/1.68 -> 32.5/1.89. Flattening the Roth at 15:31/15:38
     instead: 46.3 / 46.9 (3bp), 30.2 / 30.8 (tier_hi). Keeping a 1/3 cash buffer: EH 15.2
     (3bp) / 10.9 (tier_hi) — worst. **No change: the starvation costs ~1pp at 3bp, helps at
     tier_hi, lowers Sharpe risk.** Note it so live-vs-backtest reviews don't flag it.
  3. Same effect in the **taxable** book as live today (conviction in shadow, intraday cap
     1.5): a net-long intraday position at 15:40 (22% of days) blocks the night leg entirely
     on 19% of days. 3bp 46.5/2.42 -> 45.0/2.50 (2021-23 +0.7pp, 2024-26 −4.1pp); tier_hi
     32.1/1.78 -> 33.1/1.94. Also no change, but verify in the 15:40 log (`skip X: book cash
     exhausted` on long-QQQ/SMH days) and let the replay in `make review` §4 know.

## Verdict

- **C3 capital ramp: dead** (fails its bar; the P&L check cannot discriminate in days).
  **C1 stands**: deploy the rest of the Roth at the 10-08 checkpoint if §2b is clean. The
  cap costs ~$66/mo if the $6.8k is in cash, ~$0 if it is in VTI/SPY (EH tier_hi).
- **Deposits: next close.** Remove or raise `DAILY_ROTH_CAPITAL`/`DAILY_LIVE_CAPITAL` so they are
  not held behind a cap; waiting costs ~$0.4-0.7 per $1k per session.
- **Sequential gate: shadow proposal** (G1 z=1.645 day-clustered UB, logged beside G0): it
  mainly fixes G0's 95-99% false-open at 15bp; ~1 session faster, worth ~$0.
- **cost_fit.py: built, unit-tested on a fixture; run on the server** once ~100 exits exist.
- **Roth sequencing: document, don't change** (item 1 is free to fix before full deployment).

| idea | verdict | why |
|---|---|---|
| Evidence-keyed capital ramp (cap doubles per 15 exits with cost UB and P&L-band checks) | **dead** | costs pass at once; a 2-3 day P&L band can't tell a live edge from none (holds 47% vs 54%); slower than just deploying at the checkpoint |
| Sequential lever gate for speed | **dead as a money lever** | opens ~1 session earlier; 1.3x is worth $0.09/session at $3k. G1 (95% day-clustered UB) is worth logging because G0's rolling mean is open on 15-26% of sessions at a true 15bp (ever-opens 95-99%) |
| Flatten the Roth intraday leg before the 15:40 close buys | **dead** | −0.4..−1pp/yr; the ledger's night starvation is neutral-to-better at tier_hi |

## Verifier notes

Re-ran `ops_capital --refresh` (under the heavy lock) and `cost_fit --selftest`: every number above
reproduces exactly; self-test PASS. Corrections and caveats:

1. **Dollars.** The ~$66/mo (~$790/yr) is the cost of the existing $1k cap, i.e. of a deployment the
   repo had already planned (add. 20 "switch on", add. 29 "raise capital in steps"); it is not value
   created by this study. It also assumes the idle $6.8k is in cash; add. 20 has the user's Roth in ETFs,
   where the cap costs ~$0 (EH tier_hi −$4/mo; C0 vs C2 over 63 sessions +$289 vs +$295). The study's
   own increment is "deploy at the checkpoint instead of in steps": C1 − C3 = +$47/quarter (BIL) /
   +$14/quarter (SPY) at EH tier_hi, i.e. ~$60-190/yr at $7.8k; gate speed and deposit timing add ~$0.
2. **Gate framing.** The G0/G1/G2 table reports P(opens at least once in 60 sessions). The live gate
   re-evaluates the rolling-50 mean every check (not latched), so the relevant exposure is the share of
   sessions open. Share of sessions open (1000 paths, 60 sessions):

   | true cost | G0 rho 0 | G1 rho 0 | G0 rho 0.3 | G1 rho 0.3 |
   |---|---|---|---|---|
   | −1bp | 86% | 88% | 77% | 67% |
   | +10bp | 43% | 5% | 44% | 6% |
   | +15bp | 15% | 0% | 26% | 1% |
   | +20bp | 3% | 0% | 13% | 0% |

   G1 is still clearly stricter at bad costs, but at the live cost with rho 0.3 it is open on FEWER
   sessions than G0 (67% vs 77%), so "~1 session faster" holds only for the median first-open.
3. **G1 is not a 5% test either:** at the boundary (true 10bp) it opens at least once 32% of the time.
   A day-clustered SE from 3-5 exit days is unreliable (cost_fit's self-test at 5 days gives a clustered
   UB of +4.0bp vs ~+6.9bp iid). If G1 is logged, use a t(G−1) critical value or require >= 8 exit days.
4. `--refresh` loads `night_candidates()` (via `book.night_days`) but the docstring said no lock needed;
   docstring fixed. No 2016-20 holdout (Roth replay starts 2021) and COVID not re-run.
5. Exit sd 39bp is backed out of add. 29's UB assuming an iid bound; if that UB was clustered, the
   per-exit sd is smaller and every gate opens a little sooner (conclusions unchanged).

Verdict stands at **shadow** (G1 logging only; no rule changes; C3 ramp dead).


# Addendum 39 — program combine: shipped books vs every verified survivor, on raw prices: no new edge survives deflation (2026-09-28)

    PYTHONPATH=. .venv/bin/python -m research.sim.program_books --raw              # ~12 min: RAW-price pool (primary numbers)
    PYTHONPATH=. .venv/bin/python -m research.sim.program_books --joint-eh --raw   # ~10 min: joint books under edge-halves, RAW pool
    PYTHONPATH=. .venv/bin/python -m research.sim.program_books [--joint-eh]       # adjusted pool, as first published (secondary column)
    no heavy lock (scratchpad caches; --raw reads addendum 30's cache_rawprice.pkl)
    output: scratchpad/program_books_out_rawpool.txt, program_books_joint_eh_rawpool.txt, program_books_res_rawpool.pkl
            (adjusted: program_books_out.txt, program_books_joint_eh.txt, program_books_res.pkl)

This is the combine stage of a 9-study program with **543 variants**, plus 3 from addendum 30's floor test (**N = 546**). It adds **no new rule variants**. It
re-runs 22 book configurations built only from verified survivors (final verdict shadow or adopt),
by importing the studies' own code (macro_events.flags / ETF_COST, roth_opt.Roth / run_pair /
holdout / taxable_end, taxable_frontier.after_tax / mc_tax / covid_series / day_trades).

**Primary numbers use the RAW-price night pool (addendum 30).** The night pool's $5 floor, $2,000 ceiling, cost tier and whole shares are applied to raw
(as-traded) prices: `book.night_days(raw_price=True)`, corr 0.7, caps .10/.15. The 2020 COVID/holdout night leg uses addendum 30's raw panel2020
rebuild; its adjusted twin reproduces the cached legs exactly. The adjusted pool, as first published, is kept as a secondary column. It is too
high by roughly a fifth on every night-leg level. The adjusted column reproduces the first draft to the decimal, and the raw T0 / T2 / R0 / R0L rows
reproduce addendum 30's restated table (47.2, 64.2, 38.4, 35.3 at 3bp).

**Survivors**
- **F3** (add. 33 macro_events, ADOPT): QQQ close->open with the night leg's unused cash on scheduled FOMC eves.
- **roth_opt** (add. 31, SHADOW), three parts:
  - M2L: Roth night sizing pro-rata on the real 15:40 cash, with SGOV held.
  - A2: V6 oversold overnight on all idle Roth overnight money.
  - G4s: Roth-first wash guard with different-index look-alikes only.
- **ops_capital** (add. 38, SHADOW): logging and operations only (G1 lever-gate log, Roth IBS entry at 09:50). It has no book effect.

**Not survivors:** taxable_frontier (add. 32, borderline), index_mechanics P2 (add. 34, borderline), opex (35), new_listings (36) and regime_robust (37) (dead).
The taxable book's leverage stays at the frontier's knee, **moderate 1.3x with name cap .15**, as the pre-planned profile.
On raw prices it no longer earns that place at tier_hi (see B-C).

**Books**
- **TAXABLE shipped:** V7 1.0x, cap .10, conviction 0.5. References: "live today" (no conviction), the 1.3x gate, moderate, and moderate as built (1.0x cap .15).
- **TAXABLE proposed:** moderate 1.3x cap .15 + F3.
- **ROTH shipped:** roth.py b1 as modelled (roth_opt `asis`). Increments are measured from the live-accurate
  M3 (the executor's greedy skip, with SGOV held at 15:40).
- **ROTH proposed:** M2L + A2 + F3.
- **JOINT:** both books stepped side by side under the live symmetric guard G1 vs G4s. Taxable $3k + $1k/mo,
  Roth $7.8k + $625/21d. 35% ST tax, with permanent cross-account wash disallowance applied.

## A. Books: CAGR / Sharpe / maxDD (RAW pool)

Columns: 2016-20 holdout | 2021-23 | 2024-26 | full 2021-26 | after-tax full. Taxable after-tax is T3 35% (April payment, carry, $3k, wash).
The last column is the same full / after-tax CAGR on the adjusted pool.

| book | cost | 2016-20 HO | 2021-23 | 2024-26 | full | after-tax full | adj: full / AT |
|---|---|---|---|---|---|---|---|
| T0 V7 shipped 1.0x .10 conv.5 | 3bp | 15.9/1.08/-19 | 50.2/2.26/-9 | 44.1/1.87/-14 | **47.2/2.06/-14** | 30.9/1.97/-10 | 58.0 / 38.2 |
| | tier_hi | | 34.4/1.66/-10 | 24.3/1.16/-17 | **29.4/1.41/-17** | 19.2/1.31/-13 | 39.6 / 25.9 |
| T0L live today (no conv) | 3bp | 16.8/1.31/-12 | 39.6/2.27/-7 | 41.6/1.94/-14 | **40.6/2.08/-14** | 26.7/2.04/-10 | 51.2 / 34.0 |
| | tier_hi | | 25.0/1.55/-8 | 22.2/1.16/-16 | **23.7/1.33/-16** | 15.5/1.28/-12 | 34.0 / 22.5 |
| T1 gate 1.3x .10 | 3bp | 12.8/0.85/-24 | 53.2/2.18/-10 | 53.6/1.92/-18 | **53.4/2.04/-18** | 35.0/1.95/-13 | 68.3 / 45.2 |
| | tier_hi | | 32.7/1.48/-12 | 26.8/1.12/-20 | **29.8/1.29/-20** | 19.4/1.19/-16 | 43.3 / 28.4 |
| T2 moderate 1.3x .15 | 3bp | 12.8/0.85/-24 | 61.2/2.19/-11 | 67.5/2.03/-23 | **64.2/2.10/-23** | 42.5/2.01/-17 | 85.5 / 57.1 |
| | tier_hi | | 33.9/1.38/-13 | 31.4/1.14/-25 | **32.7/1.25/-25** | 21.4/1.14/-22 | 51.4 / 34.0 |
| T2b moderate as built 1.0x .15 | 3bp | 15.9/1.08/-19 | 56.5/2.30/-9 | 54.5/2.01/-18 | **55.5/2.15/-18** | 36.6/2.05/-13 | 71.2 / 47.2 |
| | tier_hi | | 35.7/1.60/-11 | 28.2/1.20/-21 | **32.1/1.39/-21** | 21.0/1.29/-17 | 46.3 / 30.5 |
| **TP proposed moderate + F3** | 3bp | 13.6/0.90/-24 | 62.0/2.21/-11 | 67.7/2.04/-23 | **64.7/2.11/-23** | 42.8/2.02/-17 | 85.9 / 57.4 |
| | tier_hi | | 34.2/1.39/-14 | 31.4/1.14/-25 | **32.8/1.26/-25** | 21.6/1.15/-22 | 51.4 / 34.0 |
| R0 Roth shipped b1 (asis) | 3bp | 14.9/1.18/-12 | 37.2/2.15/-7 | 39.7/1.87/-14 | **38.4/1.99/-14** | tax-free | 48.7 |
| | tier_hi | | 22.9/1.43/-8 | 20.6/1.09/-16 | **21.8/1.24/-16** | | 31.0 |
| R0L Roth live-accurate M3 | 3bp | 16.5/1.35/-8 | 33.6/2.09/-8 | 37.1/1.88/-10 | **35.3/1.97/-10** | | 45.3 |
| | tier_hi | | 22.5/1.48/-8 | 22.3/1.23/-12 | **22.4/1.34/-12** | | 31.3 |
| **RP proposed M2L+A2+F3** | 3bp | 18.5/1.47/-8 | 38.1/2.43/-8 | 40.7/2.11/-9 | **39.3/2.25/-9** | | 47.5 |
| | tier_hi | | 27.4/1.83/-9 | 25.9/1.44/-11 | **26.7/1.62/-11** | | 34.6 |

Survivor steps on the Roth, full-period tier_hi:

| step | full (raw) | EH (raw) | adj: full / EH |
|---|---|---|---|
| M3 | 22.4 | 10.5 | 31.3 / 14.4 |
| + F3 | 22.4 | 10.5 | 31.5 / 14.4 |
| M2L | 25.0 | 11.7 | 33.2 / 15.3 |
| + A2 | 26.8 | 12.5 | 34.6 / 15.8 |
| + F3 | 26.7 | 12.4 | 34.6 / 15.8 |

On raw prices the Roth survivors are worth more than on adjusted prices: M2L +1.2pp EH (adjusted +0.9) and A2 +0.8pp (adjusted +0.5). Their legs do not depend on the pool's
sub-$5 names, while the baseline did. F3 is worth about 0 in the Roth either way.

The 2016-20 taxable holdout has no night leg before 2020; that money sits in T-bills. The 1.3x rows there
mostly pay margin on T-bill money, so the holdout says nothing about 1.3x. It is informative for F3: +0.6pp (raw 15.9 → 16.5 for V7).

## B. Edge-halves, crashes, worst day/month (RAW pool)

COVID is 2020-02-19..03-23, from addendum 30's raw 2020 rebuild. 2022, Apr 2-8 2025, worst day and worst month are at tier_hi.

| book | EH 3bp | EH tier_hi | EH-AT tier_hi | COVID | 2022 | Apr 2-8 2025 | worst day | worst month | adj: EH 3bp / EH th / EH-AT th / COVID |
|---|---|---|---|---|---|---|---|---|---|
| T0 V7 shipped | 20.8/1.06/-18 | 13.3/0.73/-21 | 8.6 | -11.4% | +47.3% | +6.0% | -6.4% | -11.2% | 25.1 / 17.5 / 11.4 / -12.9% |
| T0L live today | 18.3/1.07/-16 | 11.0/0.70/-18 | 7.2 | -2.0% | +21.9% | +4.1% | -6.6% | -8.5% | 22.6 / 15.4 / 10.2 / -3.7% |
| T1 gate 1.3x | 23.0/1.04/-21 | 13.1/0.67/-25 | 8.5 | -12.7% | +42.6% | +6.3% | -8.1% | -12.1% | 28.6 / 18.6 / 12.2 / -14.7% |
| T2 moderate 1.3x .15 | 26.7/1.07/-25 | 13.9/0.64/-32 | 9.1 | -14.1% | +47.8% | +7.3% | -9.8% | -12.0% | 34.3 / 21.4 / 14.2 / -17.1% |
| T2b moderate as built 1.0x .15 | 23.9/1.10/-21 | 14.2/0.72/-25 | **9.3** | -12.5% | +51.8% | +6.8% | -7.7% | -11.0% | 29.8 / 20.0 / 13.2 / -14.8% |
| **TP proposed** | 26.9/1.07/-25 | 14.0/0.65/-33 | 9.1 | -14.1% | +49.5% | +7.3% | -9.8% | -12.0% | 34.5 / 21.4 / 14.2 / -17.1% |
| R0 Roth b1 | 17.4/1.02/-16 | 10.1/0.65/-18 | - | -2.1% | +20.2% | +4.1% | -6.6% | -8.6% | 21.6 / 14.1 / - / -3.8% |
| R0L Roth M3 | 16.2/1.02/-15 | 10.5/0.70/-18 | - | -0.1% | +26.9% | +4.8% | -6.6% | -7.9% | 20.3 / 14.4 / - / -2.5% |
| **RP proposed** | 17.9/1.15/-14 | 12.4/0.84/-16 | - | -1.5% | +29.1% | +6.3% | -6.6% | -8.2% | 21.3 / 15.8 / - / -3.8% |

- **Moderate loses its tier_hi edge on raw prices.** At tier_hi the as-built 1.0x cap .15 (EH-AT 9.3) beats 1.3x moderate and the proposed book (9.1), with a smaller EH drawdown (-25 vs -32/-33) and worst day (-7.7% vs -9.8%).
  1.3x only pays at low cost: at 3bp the EH-AT figures are 17.7 (moderate), 15.7 (as built), 13.6 (V7) and 12.1 (live today).
- **Crashes are milder on raw prices**, because the removed names were losers in 2020: V7's COVID is -11.4% vs -12.9%, and moderate's is -14.1% vs -17.1%. Worst day is slightly worse (-6.4% vs -6.0% for V7).

## C. 5y block bootstrap (21-day blocks), under EH, $3k + $1k/mo (RAW pool)

Taxable is after tax. Its P(DD) is shown on equity net of the tax liability, with the raw account balance in brackets.

| book | 3bp median / P30 / P50 | tier_hi median / P30 / P50 | adj: 3bp / tier_hi |
|---|---|---|---|
| T0 V7 shipped | $88.8k / 7% (19%) / 0% (0%) | $78.0k / 17% (35%) / 0% (1%) | $96.9k 6%/0% / $85.2k 14%/0% |
| T0L live today | $84.8k / 3% (9%) / 0% (0%) | $74.9k / 11% (22%) / 0% (0%) | $92.3k 2%/0% / $81.7k 7%/0% |
| T1 gate 1.3x | $92.0k / 14% (33%) / 0% (0%) | $77.8k / 33% (54%) / 1% (3%) | $103.1k 13%/0% / $86.9k 28%/1% (3%) |
| T2b moderate as built 1.0x .15 | $94.1k / 11% (29%) / 0% (0%) | $79.5k / 27% (49%) / 1% (2%) | - / $89.4k 22%/0.4% (1.5%) |
| T2 moderate 1.3x .15 | $98.8k / 25% (52%) / 1% (2%) | $79.3k / 49% (72%) / **5% (9%)** | $114.7k 21%/0% (2%) / $91.8k 42%/3% (7%) |
| **TP proposed** | $99.2k / 24% (51%) / 1% (2%) | $79.4k / 49% (72%) / **5% (9%)** | $115.1k 21%/0% (2%) / $91.8k 42%/3% (7%) |
| R0 Roth b1 | $97.1k / 6% / 0% | $80.8k / 20% / 0% | $109.7k 5%/0% / $91.1k 14%/0% |
| R0L Roth M3 | $94.7k / 3% / 0% | $81.9k / 11% / 0% | $106.1k 4%/0% / $91.5k 9%/0% |
| **RP proposed** | $97.9k / 3% / 0% | $85.5k / 9% / 0% | $107.7k 4%/0% / $93.9k 10%/0% |

- At tier_hi the proposed taxable book's P(DD>50%) is 5% net and **9% on the raw balance**. It is at the ≤5% bound on net equity and fails it on the balance (adjusted: 3% / 7%).
- It also buys almost nothing at tier_hi: the 5y median is $79.4k, vs $79.5k for the as-built 1.0x cap .15 and $78.0k for V7. P(DD>30%) is 49%, vs 27% and 17%.

## D. $ projections at the user's capital (RAW pool)

EH MC; each cell is p10 / median / p90 in $k. Taxable is after 35% tax. The last column gives the adjusted-pool medians (lump 5y / +$1k 5y).

| book | cost | lump 1y | lump 5y | +$1k/mo 1y | +$1k/mo 5y | adj median: lump 5y / +1k 5y |
|---|---|---|---|---|---|---|
| Taxable $3k, live today | tier_hi | 2.82 / 3.20 / 3.69 | 3.15 / 4.26 / 5.85 | 13.4 / 14.6 / 16.0 | 61.8 / 74.9 / 91.9 | 4.95 / 81.7 |
| Taxable $3k, live today | 3bp | 2.94 / 3.34 / 3.87 | 3.89 / 5.30 / 7.33 | 13.8 / 14.9 / 16.5 | 69.8 / 84.8 / 105.3 | 6.13 / 92.3 |
| Taxable $3k, V7 shipped | tier_hi | 2.79 / 3.25 / 3.85 | 3.23 / 4.59 / 6.66 | 13.3 / 14.7 / 16.4 | 62.2 / 78.0 / 99.9 | 5.28 / 85.2 |
| Taxable $3k, V7 shipped | 3bp | 2.91 / 3.39 / 4.04 | 3.99 / 5.74 / 8.40 | 13.7 / 15.1 / 16.9 | 70.6 / 88.8 / 114.9 | 6.58 / 96.9 |
| Taxable $3k, proposed | tier_hi | 2.67 / 3.26 / 4.06 | 3.02 / 4.71 / 7.67 | 13.0 / 14.8 / 17.0 | 58.8 / 79.4 / 109.6 | 6.02 / 91.8 |
| Taxable $3k, proposed | 3bp | 2.87 / 3.51 / 4.40 | 4.31 / 6.88 / 11.44 | 13.6 / 15.4 / 17.9 | 72.9 / 99.2 / 140.5 | 8.73 / 115.1 |
| Roth $7.8k, M3 | tier_hi | 7.18 / 8.56 / 10.46 | 8.49 / 12.82 / 19.55 | 17.6 / 20.1 / 23.3 | 68.9 / 89.9 / 119.8 | 15.58 / 101.3 |
| Roth $7.8k, M3 | 3bp | 7.54 / 8.98 / 11.03 | 10.90 / 16.45 / 25.05 | 18.3 / 20.8 / 24.2 | 79.6 / 104.8 / 141.0 | 20.02 / 118.5 |
| Roth $7.8k, proposed | tier_hi | 7.28 / 8.69 / 10.62 | 9.04 / 13.83 / 21.11 | 17.8 / 20.3 / 23.6 | 71.5 / 94.0 / 125.8 | 16.39 / 104.3 |
| Roth $7.8k, proposed | 3bp | 7.63 / 9.11 / 11.12 | 11.46 / 17.43 / 26.71 | 18.4 / 21.0 / 24.4 | 82.2 / 108.8 / 146.9 | 20.56 / 120.4 |

- The Roth projections are standalone. That matches the Roth under G4s (EH tier_hi 13.0% vs 12.4% standalone). It does not match
  the Roth under the live G1 guard (EH 7.5-8.8%; see F).
- At tier_hi the proposed taxable book has the widest spread for about the same median as V7. Its lump-sum 5y p10 ($3.02k) is below V7's ($3.23k) and live today's ($3.15k).

## E. Deflated Sharpe

Method: Bailey & Lopez de Prado (2014), on daily 2021-26 returns at 3bp unless marked tier_hi.
- SR0 = sqrt(V) * ((1-g) * Phi^-1(1-1/N) + g * Phi^-1(1-1/(N e))), with g = 0.5772.
- DSR = Phi((SR - SR0) * sqrt(T-1) / sqrt(1 - skew*SR + (kurt-1)/4 * SR^2)).
- Inputs: V[SR] = 1/T (all trials pure noise).
  - N = 543 gives SR0 = 1.30 annualised for T ≈ 1,420. E[max] ≈ sqrt(2 ln N) = 3.55 null t, or 3.10 after the Euler correction.
  - **N = 546** adds addendum 30's three floor variants. It moves no DSR by more than 0.001.

| daily series (RAW pool) | SR ann | t | skew | kurt | PSR(0) | DSR N=543 | **DSR N=546** | DSR N=50 | adj: DSR N=543 |
|---|---|---|---|---|---|---|---|---|---|
| F3 taxable increment | 0.75 | 1.78 | 13.9 | 307 | 0.994 | 0.035 | 0.035 | 0.25 | 0.064 |
| F3 taxable increment, tier_hi | 0.41 | 0.98 | 11.8 | 275 | 0.874 | 0.007 | 0.007 | 0.07 | 0.005 |
| F3 Roth increment | 0.31 | 0.74 | 14.1 | 356 | 0.804 | 0.004 | 0.004 | 0.04 | 0.020 |
| M2L - M3 (Roth sizing) | 0.39 | 0.93 | 10.6 | 224 | 0.853 | 0.007 | 0.007 | 0.06 | 0.001 |
| A2 increment | 1.13 | 2.68 | 1.9 | 60 | 0.997 | 0.343 | 0.342 | 0.66 | 0.217 |
| A2 increment, tier_hi | 1.17 | 2.77 | 2.0 | 60 | 0.998 | 0.375 | 0.374 | 0.70 | 0.166 |
| moderate - V7 (borderline; leverage) | 1.43 | 3.38 | -0.1 | 23 | 1.000 | 0.616 | 0.615 | 0.86 | 0.894 |
| moderate - V7, tier_hi | 0.43 | 1.02 | -0.1 | 24 | 0.846 | 0.020 | 0.020 | 0.11 | - |
| as built 1.0x .15 - V7 | 1.49 | 3.54 | 0.1 | 32 | 1.000 | 0.673 | 0.672 | 0.89 | - |
| TAXABLE proposed - shipped | 1.46 | 3.45 | -0.1 | 23 | 1.000 | 0.641 | 0.640 | 0.87 | 0.903 |
| ROTH proposed - M3 | 0.79 | 1.87 | 8.9 | 178 | 0.989 | 0.070 | 0.070 | 0.31 | 0.008 |
| TAXABLE shipped book | 2.06 | 4.88 | 1.2 | 9.7 | 1.000 | 0.973 | 0.973 | 1.00 | 0.996 |
| TAXABLE proposed book | 2.11 | 5.01 | 0.6 | 9.4 | 1.000 | 0.975 | 0.975 | 1.00 | 0.998 |
| ROTH M3 book | 1.97 | 4.67 | 0.5 | 8.3 | 1.000 | 0.947 | **0.947** | 0.99 | 0.990 |
| ROTH proposed book | 2.25 | 5.32 | 0.6 | 8.2 | 1.000 | 0.989 | 0.989 | 1.00 | 0.998 |

- No survivor's increment clears DSR 0.95 at N=546. The best is still A2 (0.34, up from 0.22). F3's whole-book increment is t 1.8 (1.0 at tier_hi).
- The moderate increment falls from DSR 0.89 to 0.62. At tier_hi it is t 1.0 (DSR 0.02). What remains is leverage on our own edge, and it survives only at low cost.
- The books themselves still pass, except that the Roth M3 book now sits just under 0.95 (0.947). They were mostly shipped before this program, so their DSR is not a test of the program.

## F. Joint books under the wash guards (RAW pool)

Settings: tier_hi. EH end $ is the after-tax end value (2021-02..2026-09, deposits included) with each book's edge halved.

| config (tier_hi) | taxable CAGR | Roth CAGR | EH taxable / Roth | perm. disallowed | EH end AT, user | EH end AT, 100k | adj: EH T / R, end user / 100k |
|---|---|---|---|---|---|---|---|
| J0 shipped, live G1 | 23.8 | 14.3 | 11.0 / 7.5 | 0.0% | $144.5k | $1.853M | 15.5 / 7.1, $153.5k / $1.967M |
| J1 proposed, G1, Roth F3 on | 32.9 | 17.1 | 14.0 / 8.7 | 1.1% | $150.6k | $1.932M | 21.5 / 8.6, $166.3k / $2.133M |
| J1b proposed, G1, Roth F3 off | 32.7 | 17.3 | 13.9 / 8.8 | 0.0% | $153.4k | $1.967M | 21.5 / 8.6, $169.9k / $2.180M |
| J2 proposed, G4s, Roth F3 on | 34.0 | 27.7 | 15.6 / 12.9 | **8.8%** | - | - | 14.9 / 16.4, 7.9% disallowed |
| J3 shipped, G4s | 23.0 | 22.6 | 11.0 / 10.7 | 0.4% | - | - | 9.9 / 15.4 |
| **J2b proposed, G4s, Roth F3 off** | 34.1 | 27.8 | 15.7 / 13.0 | 0.7% | **$166.1k** | **$2.114M** | 15.0 / 16.4, $172.9k / $2.221M |
| J4 shipped taxable + proposed Roth, G4s | 25.2 | 27.8 | 12.0 / 13.0 | 0.5% | $159.8k | $2.043M | 11.6 / 16.5, $168.3k / $2.153M |

**At 3bp (raw)**, EH end AT at user size is: J0 $159.0k, J1 $178.1k, J1b $181.5k, J2b $181.5k, J4 $175.0k. At 100k it is J0 $2.039M, J1b $2.326M, J2b $2.325M, J4 $2.246M.
- J1b and J2b tie at 3bp (adjusted: J1b $204k vs J2b $192k).
- At tier_hi J2b is best by $12.7k (adjusted: $3.0k).
- On raw prices G4s no longer costs the taxable book anything: its EH is 15.7 under G4s vs 13.9 under G1 at tier_hi (adjusted: 15.0 vs 21.5).

**Roth F3 wash finding (post-hoc), confirmed on raw.** Roth F3 buys QQQ, and taxable's noise leg sells QQQ at a loss almost every day.
Any Roth QQQ purchase within ±30 days of those loss sales is a permanent disallowance: 1.1% of taxable losses under G1, and 8.8% (tier_hi) to 9.9% (3bp) under G4s.
**The Roth must not run F3 in QQQ.** Roth F3 is worth about $0 anyway.

## G. Adjusted pool vs the first draft's $5-exclusion shortcut vs the full raw pool

The first draft approximated the bug by dropping names whose raw close was < $5. It did not re-tier costs or re-round shares on raw prices. The full raw pool is lower again at tier_hi.

| book | 3bp full: adj / $5-excl / raw | tier_hi full: adj / $5-excl / raw | EH-AT or EH tier_hi: adj / $5-excl / raw |
|---|---|---|---|
| T0 V7 shipped | 58.0 / 46.7 / **47.2** | 39.6 / 31.1 / **29.4** | EH-AT 11.4 / 9.1 / **8.6** |
| T0L live today | 51.2 / 39.9 / **40.6** | 34.0 / 25.7 / **23.7** | EH-AT 10.2 / 7.8 / **7.2** |
| TP proposed taxable | 85.9 / 64.4 / **64.7** | 51.4 / 36.4 / **32.8** | EH-AT 14.2 / 10.2 / **9.1** |
| R0L Roth M3 | 45.3 / 35.1 / **35.3** | 31.3 / 23.6 / **22.4** | EH 14.4 / 11.0 / **10.5** |
| RP proposed Roth | 47.5 / 39.0 / **39.3** | 34.6 / 27.8 / **26.7** | EH 15.8 / 13.0 / **12.4** |

Every survivor's sign is unchanged on the raw pool: M2L +1.2pp EH, A2 +0.8pp, F3 +0.1pp taxable and -0.1pp Roth at tier_hi.

## Recommendations

**Ranking.** Items are ranked by EH × tier_hi after-tax $/yr on the RAW pool, with the adjusted pool in brackets.
- **User size:** Roth $7.8k + taxable $3k.
- **"100k":** $100k in each account.
- **$/yr:** Δ EH CAGR × capital. Taxable pre-tax deltas are × 0.65; the standalone taxable items use EH-AT directly.

| # | change | $/yr user, raw (adj) | $/yr at 100k, raw (adj) | risk added | status / gate |
|---|---|---|---|---|---|
| 0 | Research on raw prices (`load_sim(raw_price=True)`, `night_days(raw_price=True)`); restate every night-leg number | n/a: expect about -20% on night-leg levels vs published backtests | n/a | none; the live bot already sees raw prices | **done in addendum 30**; new studies must use it |
| 1 | Wash guard G4s (Roth first, different-index look-alikes, Roth skips taxable loss names), with Roth F3 OFF (J1b → J2b) | **≈ +$363** (+$481): Roth +4.2pp × $7.8k, taxable +1.8pp × $3k × 0.65 | **≈ +$5.3k** (+$4.1k) | tax-structure risk: 0.7% of taxable losses permanently disallowed | post-hoc: SHADOW. Gate: switching DAILY_ROTH on. Under the live G1 the Roth earns EH ~8.8% instead of ~13% |
| 2 | Roth M2L sizing (pro-rata on the real 15:40 cash) | ≈ +$94 (+$70) | ≈ +$1.2k (+$0.9k) | none (sizing only) | SHADOW: log requested vs funded. DSR 0.007 |
| 3 | Ops: deploy the rest of the Roth at the 10-08 checkpoint; log lever-gate G1 | ≈ +$100, adjusted only; **not re-run on raw**, expect about 20% less | ≈ +$1k (adj) | 63-session P5 loss -$748 (adj) | gated on make review §2b clean |
| 4 | Taxable moderate as built, 1.0x cap .15 (vs live today) | ≈ +$63: EH-AT 7.2 → 9.3 (+$90: 10.2 → 13.2) | ≈ +$2.1k (+$3.0k) | P(DD>50%) 0 → 1% net (2% balance); COVID -2.0 → -12.5%; worst day -7.7% | preferred over 1.3x on raw prices; lever gate still applies |
| 5 | Roth A2 (V6 oversold overnight on idle money) | ≈ +$62 (+$40) | ≈ +$0.8k (+$0.5k) | overnight SPY/QQQ ≤1.0x gross; COVID -0.1 → -1.5% | SHADOW until V6 leaves shadow; DSR 0.34 |
| 6 | Taxable moderate 1.3x cap .15 (vs live today) | ≈ +$57 (+$120); ≈ +$72 (+$66) if G4s is also adopted | ≈ +$1.9k (+$4.0k); ≈ +$2.4k (+$2.4k) under G4s | P(DD>30%) net 11 → 49% (balance 22 → 72%); **P(DD>50%) 0 → 5% net / 9% balance** (fails ≤5% on the balance); COVID -2.0 → -14.1%; worst day -9.8% | **downgraded:** below the as-built 1.0x .15 at tier_hi (EH-AT 9.1 vs 9.3) with 5× the P(DD>50%). Pays only at low cost: +$168/yr at 3bp (as built +$108). Needs a new sign-off (add. 30); keep gated on the lever gate + make review §2b measured open-sell cost |
| 7 | F3 FOMC-eve QQQ filler, taxable only | ≈ +$3 (+$3) | ≈ +$0.1k (+$0.1k) | ~8 nights/yr QQQ beta on spare cash, no margin | ADOPT per study, but DSR 0.035: run with the pre-registered auto-disable (mean < 0 after 16 events). Roth F3 **off** (wash) |

**All survivors combined**, J0 → J2b at tier_hi under EH:
- **User size:** Roth +5.5pp and taxable +4.7pp pre-tax ≈ **+$520/yr**, or +$21.6k of EH end value over 2021-26 ($144.5k → $166.1k). Adjusted pool: ≈ +$715/yr.
- **100k scale:** Roth +5.3pp and taxable +4.8pp ≈ **+$8.4k/yr** ($1.853M → $2.114M). Adjusted pool: +$9.3k.
- **Source:** most of the gain is the guard (#1) and the Roth mechanics (#2, #5), not new edges.
- **Taxable delta:** on raw prices the taxable delta turns positive (adjusted: -0.5pp). The as-built/moderate profile no longer loses to G4s's night-leg exclusions.

## Verdict

No new edge survives multiple-testing deflation. At N=546 the best survivor increment is A2, with DSR 0.34.

What the program changes is structure:
- which account owns which names (the guard);
- Roth mechanics;
- leverage.

On raw prices the ranking shifts toward the Roth mechanics. The Roth survivors are worth more, while leverage is worth much less.

- **Adopt:** F3 in taxable only, with auto-disable. Addendum 30's raw-price research switch is already done.
- **Shadow:** G4s, M2L and A2.
- **Taxable leverage:** prefer the **as-built 1.0x cap .15** over 1.3x moderate. On raw prices 1.3x fails the P(DD>50%) ≤5% bar on the account balance at tier_hi (9%), sits at the bound on net equity (5%), and trails as-built on after-tax EH.
  - 1.3x is worth reconsidering only if make review's measured open-sell cost stays near addendum 29's ~0bp. At 3bp it leads as-built by +2.0pp EH-AT.

## Do NOT redo

| idea | verdict | why |
|---|---|---|
| Stacking the program's survivors as if additive edges | **report** | no increment clears DSR 0.95 at N=546 (best A2 0.34, F3 0.035). The combined gain is structural (guard, mechanics): +$520/yr at user size on raw prices (add. 39) |
| Roth F3 (FOMC-eve filler) in QQQ beside a taxable QQQ noise leg | **dead** | Roth QQQ buys land within 30 days of taxable QQQ intraday loss sales. 1.1% (G1) / 8.8-9.9% (G4s) of taxable losses are permanently disallowed, for ~$0 of edge (add. 39) |
| Quoting split-adjusted night-leg backtests as expectations | **bug** | on the raw pool V7 falls 58.0 → 47.2% at 3bp and Roth M3 falls 31.3 → 22.4% at tier_hi. The $5-exclusion shortcut understates the drop at tier_hi (add. 30, 39) |
| 1.3x moderate as the taxable knee at tier_hi costs | **borderline → dead at tier_hi** | on raw prices: EH-AT 9.1 vs as-built 1.0x .15 at 9.3; P(DD>50%) 5% net / 9% balance; increment t 1.0 (add. 39) |

## Caveats

- **Raw pool:**
  - It comes from addendum 30's `cache_rawprice.pkl`: `night_days(raw_price=True)` for 2021-26, plus the raw panel2020 rebuild used for COVID and the 2020 part of the holdouts.
  - The roth_opt / macro_events 2020 legs are rebuilt from it and truncated at 2020-11-05, like the originals.
  - Of the candidates, 0.1% use a "rebased" factor and none use nearest-date.
- **Other addenda:** the other program addenda still quote adjusted night-leg levels. Only this addendum and addendum 30 are restated.
- **Joint model:**
  - The joint taxable book is roth_opt.Taxable generalised to moderate (0.65/0.65, noise cap 0.6, conviction 0.5, name cap .15 via a copied night_leg with a cap parameter).
  - Margin interest is 12% on night + IBS value above equity.
  - Tax is a flat 35% (roth_opt.taxable_end, no carry of the $3k rule). This differs slightly from taxable_frontier's T3 in sections A-D.
- **Look-alikes:** as in roth_opt, look-alike ETF returns equal the originals.
- **2016-20 holdouts:**
  - The Roth holdout uses mech M2 for M2L/M3, because roth_opt.holdout has no M2L.
  - F3 in the holdouts uses the 2021-26 mean spare share (raw 0.58).
  - Taxable holdouts use the 2020 night rebuild at cap .10 only.
- **COVID:** the taxable COVID figures come from taxable_frontier.covid_series and include conviction.
- **"100k scale":** both accounts' starts and deposits are scaled by 100k/7.8k. $/yr at 100k uses the Δ EH CAGR from those runs × $100k per account.
- **Ops item (#3):** it comes from ops_capital on the adjusted pool and was not re-run.
- **Post-hoc items:** G4s itself, the Roth-F3 wash finding, the as-built-vs-1.3x comparison and every J-row are post-hoc combinations of survivors. They are not new pre-registered tests.


# Addendum 40 — intraday buying power after the PDT rule (Schwab ~4x since 2026-07-13): SHADOW (Kelly x1.5 noise target, multiplier on conviction books), multiplier DEAD on moderate10 (2026-09-29)

**Verified verdict: SHADOW.** Schwab now grants up to ~4x intraday (4x maintenance excess), but the live code reads 2.48 and
the broker multiplier is not the binding constraint. 3-4x adds +0.5-0.6pp after-tax EH at tier_hi on the conviction books
(NW t 1.6-1.7, fails the t >= 2 bar) and ~0 on moderate10 (dead). Kelly x1.5 on the noise leg (noise_target_vol 0.02 -> 0.03)
at 4x adds +1.2-1.4pp EH-AT (NW t 2.0, placebo 98th pct) and met the pre-registered bar on V7/moderate10, but it is
downgraded: DSR 0.10, 2024-26 NW t 0.64, t 1.1-1.3 without the 5 best days, 2026 YTD negative, every increment turns
negative at 2x the tier_hi intraday costs (break-even ~2bp per noise fill), P(DD>30%) doubles, and moderate10c + Kelly
fails P(DD>50%) (5.4%). Variants: 5 pre-registered + 2 post-hoc = 7. Switch: spec only, default OFF (NEXT.md).

    PYTHONPATH=. .venv/bin/python -m research.sim.intraday_bp          # no heavy lock (reads caches)

## 1. Facts (established before any number was computed)

**The rule.** FINRA's Rule 4210 amendments (SR-FINRA-2025-017; SEC approval 2026-04-14; Regulatory
Notice 26-10, effective 2026-06-04, optional phase-in to 2027-10-20) delete the pattern-day-trader
definition, the $25k minimum, and the "day-trading buying power" computation (maintenance excess x 4).
They replace them with an *intraday margin deficit*: after every IML-reducing trade (a purchase or a
short sale), equity must cover the **maintenance** requirement of paragraph (c) on what is then held.
The rule "does not change the regular maintenance margin requirements ... but rather supplements them".
Firms may monitor in real time (block the trade) or compute once at the end of the day.
Sources: [FINRA Regulatory Notice 26-10](https://www.finra.org/rules-guidance/notices/26-10);
[Federal Register, approval order 2026-07485](https://www.federalregister.gov/documents/2026/04/17/2026-07485/self-regulatory-organizations-financial-industry-regulatory-authority-inc-notice-of-filing-of);
[SEC release 34-105226](https://www.sec.gov/files/rules/sro/finra/2026/34-105226.pdf);
[WilmerHale client alert 2026-04-23](https://www.wilmerhale.com/en/insights/client-alerts/20260423-sec-approves-amendments-to-finra-rule-4210-replacing-day-trading-margin-requirements-with-a-modernized-intraday-margin-standard).

**Schwab.** Stopped counting day trades on 2026-06-08. From **2026-07-13** it offers *Intraday Margin
Buying Power* to margin accounts with >= $2,000 in cash or eligible securities: "the dollar amount a
client can trade during the day in eligible securities with a 25% margin requirement ... This can
provide up to four times the buying power intraday". It is computed in real time from open positions
and their requirements; positions above overnight (Reg T) buying power must be closed the same day
(8 p.m. ET) or a margin call may follow; Schwab blocks trades that would create an intraday deficit.
Source: [Schwab, "Schwab Updates Day Trading and Margin Rules"](https://www.schwab.com/learn/story/schwab-changes-rules-around-day-trading)
(fetched 2026-09-29; the page text is quoted above). Securities with higher maintenance get less than
4x. 3x ETFs (TQQQ/SQQQ) carry 75% (FINRA/Cboe 3 x 25%; Schwab's house figure per secondary sources:
[Cboe RG09-097](https://cdn.cboe.com/resources/regulation/circulars/regulatory/RG09-097.pdf),
[Schwab margin requirements](https://www.schwab.com/margin/margin-rates-and-requirements)); Schwab's
house maintenance on ordinary equities is often quoted at 30% (-> 3.33x), and it may raise any
requirement for a concentrated position.

**What the live code sees.** `brokers.SchwabBroker.account()` sets
`multiplier = clip(max(dayTradingBuyingPower, buyingPower) / liquidationValue, 2, 4)`, and
`executor._gate` sets `noise_lev_cap = min(noise_max_lev 3.5, mult x (1 - conv x 0.75) - w_ibs)`.
The only multiplier ever recorded for the live Schwab account is **2.48** (addendum 22, 2026-09-24,
i.e. after 07-13); the repo's local logs (`logs/*.log`) contain no multiplier line. So the Trader
API fields the code reads do **not** show the 4x intraday figure (dayTradingBuyingPower is the old
PDT field; buyingPower is Reg T). The live cap today is therefore ~2.48 x ..., not what Schwab allows.
Whether a Trader-API field exposes Intraday Margin Buying Power is unverified (needs a live
`make daily-live-check` dump of `currentBalances`).

**Roth (limited margin IRA).** Not a margin account: no borrowing, no shorting; Intraday Margin Buying
Power is for margin accounts only. The Roth's intraday leg is settled cash + unsettled proceeds in 3x
ETFs (cap = 1 + (1 - w_ibs) x 2). No change is possible from the rule. (A larger 3x share of daytime
cash was already tested: borderline, add. 31.)

## 2. Pre-registration (stamped below; written before any 2024-26 or book number was computed)

Books (RAW night pool, add. 30; $3k + $1k/21 sessions; baselines of add. 39):
- **B1 V7**: 1.0x, name cap .10, conviction 0.5.
- **B2 moderate10**: 1.0x, name cap .15, conviction off (as built today).
- **B3 moderate10c**: 1.0x, name cap .15, conviction 0.5.

Intraday cap for the taxable book: `cap = min(3.5, mult x (1 - 0.75 conv) - ibs_w)`; noise leverage and
conviction weight as shipped. Baseline = **mult 2** (the current research assumption).

Variants (5 in total, each evaluated on B1-B3):
- **V1 mult 3**
- **V2 mult 4** (Schwab's stated default: 25% -> up to 4x)
- **V3 Kelly-scaled**: mult 4, noise leverage x 1.5 inside the cap
- reference rows (reported, not adoptable on their own): **R1 mult 2.48** (what the live code reads
  today), **R2 mult 3.33** (30% house maintenance)

Costs: night leg 3bp flat / tier / tier_hi. Intraday legs: as shipped (noise 0.5bp/fill, conviction
1.5bp/side) at 3bp and tier; at tier_hi noise 1.5bp/fill and conviction 3bp/side.

Measures (for every row): CAGR/Sharpe/maxDD 2021-23, 2024-26, full; after-tax (35%, add. 32 T3 with
wash sales); edge-halves (EH, growth.eh) pre- and after-tax; 5y 21-day block bootstrap under EH,
$3k + $1k/mo, after tax: median, P(DD>30%), P(DD>50%) on net equity and on the raw balance;
2016-20 holdout (noise/conviction legs from 2016 minutes; night leg in T-bills before 2020);
COVID 2020-02-19..03-23, 2022, 2025-04-02..04-08; worst day / month; **worst intraday path** of the
intraday legs from 1-minute bars (trough of mark-to-market within the session, % of equity) on
2020-03-09/12/16, 2025-04-03/04/07/09 and the worst over 2016-26. Increment vs mult 2: day-level NW t
(5 lags), and a placebo matched on frequency and exposure (the variant's extra leverage times the
noise leg's day return with a random sign, 500 draws; report the percentile of the actual mean).

Pass bar for a variant on a book (all at tier_hi unless stated):
1. after-tax EH CAGR >= baseline + 0.5pp;
2. 5y MC under EH after tax: P(DD>50%) <= 5% on net equity (the taxable account's bound);
3. increment positive in 2021-23 AND 2024-26 (pre-tax) and in the 2016-20 holdout;
4. increment NW t >= 2.0 and placebo percentile >= 95;
5. worst intraday path of the intraday legs no worse than -15% of equity.
Verdict: all pass on the mult Schwab actually grants -> adopt (as a switch the user turns on after
confirming the API/account value); 1-3 pass but 4 or 5 fails -> shadow; 1 fails -> dead. V3 is
judged against V2 (its incremental 1.5x) as well as against mult 2.

**Pre-registration stamped: Tue Sep 29 00:11:55 PDT 2026**  (no 2024-26 or book number computed before this line)


## 3. Results (computed after the stamp; `research/sim/intraday_bp.py`, output
`data/research/program/intraday_bp_out.txt`; follow-ups `intraday_bp_extra.py` -> `intraday_bp_extra_out.txt`)

Parity: B1 M2 at 3bp reproduces addendum 39's T0 exactly (47.2/2.06/-14, after-tax 30.9, 2016-20 15.9/1.08/-19).
The tier_hi rows are lower than add. 39 (B1 24.1 vs 29.4) because this study also charges the
pre-registered tier_hi intraday costs (noise 1.5bp/fill, conviction 3bp/side).

Rule variants: **5** (V1, V2, V3, R1, R2) x 3 books = 15 book rows + 3 baselines; post-hoc: 2 (P1, P2) x 3.

### A. Books (tier_hi unless marked). cap = intraday noise cap; EH-AT = after-tax edge-halves CAGR;
MC = 5y EH after-tax, $3k+$1k/mo: P(DD>30%) / P(DD>50%) net (raw balance)

| book | row | cap | 3bp full | tier_hi 21-23 / 24-26 / full | EH-AT | MC P30 | MC P50 | 2016-20 HO | worst intraday path |
|---|---|---|---|---|---|---|---|---|---|
| B1 V7 | M2 base | 0.75 | 47.2/2.06/-14 | 28.6 / 19.5 / 24.1/1.20/-17 | 7.1 | 23 (42) | 0.3 (0.9) | 11.3/0.80 | -5.2% |
| | R1 2.48 (live) | 1.05 | 50.4/2.06/-15 | 30.9 / 20.1 / 25.6/1.19/-18 | 7.4 | 28 (49) | 0.6 (2.1) | 12.2/0.80 | -5.6% |
| | V1 m3 | 1.38 | 52.6/2.05/-15 | 32.3 / 20.5 / 26.5/1.19/-18 | 7.6 | 31 (53) | 0.9 (2.8) | 12.7/0.78 | -5.6% |
| | R2 3.33 | 1.58 | 53.6/2.05/-15 | 33.0 / 20.6 / 26.9/1.18/-18 | 7.6 | 32 (54) | 1.1 (3.1) | 13.0/0.78 | -5.6% |
| | V2 m4 | 2.00 | 54.8/2.04/-15 | 33.6 / 20.7 / 27.2/1.17/-18 | 7.7 | 34 (57) | 1.4 (3.7) | 13.0/0.75 | -5.6% |
| | V3 m4 Kelly | 2.00 | 61.3/2.01/-16 | 39.7 / 21.7 / 30.7/1.18/-22 | 8.5 | 46 (71) | 3.7 (7.3) | 14.1/0.74 | -6.7% |
| B2 moderate10 | M2 base | 1.50 | 48.6/2.15/-18 | 19.8 / 20.1 / 19.9/1.04/-21 | 6.0 | 27 (45) | 0.9 (1.9) | 11.3/0.89 | -4.1% |
| | R1 2.48 | 1.98 | 50.1/2.15/-18 | 20.6 / 20.5 / 20.6/1.04/-21 | 6.2 | 28 (46) | 1.0 (2.1) | 11.6/0.85 | -4.2% |
| | V1 m3 | 2.50 | 50.9/2.15/-18 | 21.1 / 20.6 / 20.9/1.04/-21 | 6.2 | 29 (48) | 1.1 (2.4) | 11.5/0.80 | -4.2% |
| | R2 3.33 | 2.83 | 50.9/2.14/-18 | 21.0 / 20.4 / 20.7/1.03/-21 | 6.2 | 30 (49) | 1.1 (2.5) | 11.5/0.78 | -4.2% |
| | V2 m4 | 3.50 | 50.7/2.12/-18 | 21.0 / 19.9 / 20.5/1.02/-21 | 6.1 | 31 (50) | 1.1 (2.8) | 11.6/0.76 | -4.2% |
| | V3 m4 Kelly | 3.50 | 61.3/2.13/-19 | 29.1 / 22.1 / 25.7/1.08/-23 | 7.2 | 44 (66) | 3.3 (6.2) | 13.0/0.72 | -6.2% |
| B3 moderate10c | M2 base | 0.75 | 55.5/2.15/-18 | 29.9 / 23.4 / 26.7/1.20/-21 | 7.7 | 33 (55) | 1.7 (3.3) | 11.9/0.82 | -5.2% |
| | R1 2.48 | 1.05 | 59.0/2.15/-18 | 32.0 / 24.1 / 28.2/1.20/-22 | 8.0 | 38 (61) | 2.1 (4.7) | 12.8/0.82 | -5.6% |
| | V1 m3 | 1.38 | 61.2/2.15/-18 | 33.5 / 24.3 / 29.0/1.20/-22 | 8.2 | 41 (64) | 2.5 (5.5) | 13.3/0.80 | -5.6% |
| | R2 3.33 | 1.58 | 62.3/2.14/-18 | 34.2 / 24.6 / 29.5/1.20/-22 | 8.3 | 42 (65) | 2.7 (5.7) | 13.6/0.79 | -5.6% |
| | V2 m4 | 2.00 | 63.5/2.14/-18 | 34.9 / 24.6 / 29.8/1.19/-22 | 8.3 | 43 (67) | 3.0 (6.3) | 13.7/0.76 | -5.6% |
| | V3 m4 Kelly | 2.00 | 70.4/2.12/-20 | 41.0 / 25.6 / 33.4/1.20/-24 | 9.0 | 54 (78) | **5.4 (10.9)** | 14.7/0.76 | -6.7% |

### B. Increments vs mult 2 (tier_hi): dCAGR 2021-23 / 2024-26 / 2016-20 HO, EH-AT, NW t, placebo pct, DSR (N=553)

| book | row | d 21-23 | d 24-26 | d HO | d EH-AT | NW t | placebo | DSR tier_hi / 3bp |
|---|---|---|---|---|---|---|---|---|
| B1 | R1 2.48 | +2.3 | +0.6 | +0.9 | +0.32 | 1.77 | 97.6 | 0.07 / 0.39 |
| B1 | V1 m3 | +3.7 | +1.0 | +1.4 | +0.50 | 1.70 | 96.8 | 0.06 / 0.35 |
| B1 | R2 3.33 | +4.4 | +1.1 | +1.7 | +0.56 | 1.67 | 96.2 | 0.05 / 0.35 |
| B1 | V2 m4 | +5.1 | +1.1 | +1.7 | +0.60 | 1.59 | 95.0 | 0.05 / 0.33 |
| B1 | V3 Kelly | +11.2 | +2.2 | +2.8 | +1.40 | 2.05 | 98.4 | 0.10 / 0.47 |
| B1 | V3 vs V2 | +6.1 | +1.0 | +1.0 | +0.80 | 2.19 | 98.4 | |
| B2 | R1 2.48 | +0.9 | +0.4 | +0.2 | +0.13 | 1.25 | 85.4 | 0.03 / 0.15 |
| B2 | V1 m3 | +1.3 | +0.5 | +0.2 | +0.18 | 1.12 | 82.6 | 0.02 / 0.12 |
| B2 | R2 3.33 | +1.3 | +0.3 | +0.2 | +0.13 | 0.90 | 77.4 | 0.01 / 0.08 |
| B2 | V2 m4 | +1.2 | -0.2 | +0.3 | +0.03 | 0.57 | 69.0 | 0.01 / 0.04 |
| B2 | V3 Kelly | +9.4 | +2.0 | +1.7 | +1.17 | 2.02 | 98.2 | 0.10 / 0.46 |
| B2 | V3 vs V2 | +8.1 | +2.2 | +1.4 | +1.14 | 2.45 | 99.0 | |
| B3 | R1 2.48 | +2.1 | +0.8 | +0.9 | +0.32 | 1.74 | 97.6 | 0.06 / 0.40 |
| B3 | V1 m3 | +3.5 | +1.0 | +1.4 | +0.46 | 1.61 | 96.8 | 0.05 / 0.35 |
| B3 | R2 3.33 | +4.3 | +1.2 | +1.7 | +0.55 | 1.65 | 96.2 | 0.05 / 0.35 |
| B3 | V2 m4 | +4.9 | +1.2 | +1.7 | +0.58 | 1.56 | 95.0 | 0.04 / 0.32 |
| B3 | V3 Kelly | +11.1 | +2.2 | +2.8 | +1.30 | 2.03 | 98.4 | 0.10 / 0.47 |

### C. Crashes and paths (tier_hi)
- COVID 2020-02-19..03-23 (2016-20 rebuild): B1 -11.7% (base) .. -10.9% (V3); B2 -3.5% .. -3.3%; B3 -12.8% .. -12.0%. More intraday room *helps* in crashes (the noise leg is trend-following).
- 2022: B1 +40.3% -> +44.6% (V2) / +54.0% (V3). Apr 2-8 2025: +5.8% -> +6.2% / +7.0%.
- Worst book day unchanged (2026-04-27: B1 -6.4% -> -6.6% V2 / -6.9% V3; B2 -7.9% -> -8.2%). Worst month B1 -11.6% -> -12.6% (V2) / -13.9% (V3).
- **Worst 1-minute intraday path** of the intraday legs (adverse extreme of each minute, % of equity): 2020-03-16 0.0% in every row (vol-targeting cut the noise size to ~0.4x and there was no strong TQQQ breakout); 2020-03-18 -4.4% (conviction books) / -4.7% V3; 2025-04-04 -2.0 .. -2.4%; 2025-04-07 -2.8 .. -3.6%; 2025-04-09 -3.6 .. -4.3%. Worst session 2016-26: -5.2% (base, 2018-02-09) -> -5.6% (V2) -> -6.7% (V3, 2018-10-11). 1st percentile of sessions -2.1% -> -2.8% (V2) -> -3.2% (V3). Every row is far inside the -15% bar. The noise leg's vol targeting shrinks it on exactly the days a 4x book would otherwise blow through.

### D. POST-HOC (labelled; at most shadow): Kelly x1.5 without any multiplier change
| book | row | cap | tier_hi full | d EH-AT | d halves | NW t | MC P30 / P50 net (raw) |
|---|---|---|---|---|---|---|---|
| B1 | P1 Kelly at 2.48 (live) | 1.05 | 27.0/1.21/-18 | +0.68 | +4.9/+0.8 | 2.38 | 30 (52) / 0.9 (2.6) |
| B1 | P2 Kelly at 2 | 0.75 | 24.4/1.20/-17 | +0.07 | +0.4/+0.1 | 1.45 | 23 (41) / 0.3 (1.1) |
| B2 | P1 Kelly at 2.48 | 1.98 | 24.1/1.09/-22 | +1.05 | +6.7/+1.5 | 2.30 | 37 (59) / 2.1 (4.9) |
| B2 | P2 Kelly at 2 | 1.50 | 22.6/1.09/-22 | +0.74 | +4.2/+1.0 | 2.13 | 34 (53) / 1.6 (3.4) |
| B3 | P1 Kelly at 2.48 | 1.05 | 29.5/1.22/-22 | +0.68 | +4.8/+0.9 | 2.34 | 40 (63) / 2.4 (5.3) |
| B3 | P2 Kelly at 2 | 0.75 | 27.0/1.21/-21 | +0.06 | +0.3/+0.2 | 1.23 | 33 (55) / 1.7 (3.4) |

## 4. Reading

1. **The binding constraint is not the broker.** Schwab allows ~4x intraday (25%) since 2026-07-13, but
   the code reads 2.48 (Reg T buying power). For the conviction books the extra room is worth
   +0.3pp (2.48, already live) to +0.6pp (4x) after-tax EH at tier_hi, positive in both halves and
   2016-20, placebo 95-98th pct, **NW t 1.6-1.8 (bar 2.0: fails)**, DSR 0.05. For moderate10 (no
   conviction) it is worth nothing (+0.03pp at 4x). *Corrected by the verifier:* the 1.5 cap does bind
   (QQQ vol-target lev > 1.5 on 67% of days, median 1.89), but the extra exposure a higher cap adds lands
   on calm days, where the noise leg nets ~0 after tier_hi costs.
2. **The size that matters is the noise leg's target, not the cap.** Kelly x1.5 (= noise_target_vol
   0.02 -> 0.03) adds +1.2..+1.4pp after-tax EH at tier_hi, NW t 2.0 (V3 vs V2 t 2.2-2.45), placebo
   98th pct, both halves and 2016-20 positive; it passes all five pre-registered bars on B1 and B2, and
   fails bar 2 on B3 (P(DD>50%) 5.4% net, 10.9% raw balance). But it is a leverage dial on an existing
   edge: 2024-26 increment is 1/5 of 2021-23's (+2.2 vs +11.2pp), tier_hi Sharpe does not rise, DSR at
   N=553 is 0.10, and P(DD>30%) goes 23% -> 46% (B1) / 27% -> 44% (B2): the same trade (+~1pp EH-AT for
   +15-20pp P(DD>30%)) that addendum 32 called dead for the overnight gross.
3. The worst intraday path at 4x + Kelly is -6.7% of equity (2018-10-11); no crash day comes close. A
   margin call from an intraday leg is not the risk; drawdown depth over months is.
4. **Roth**: limited margin, no Intraday Margin Buying Power; no change is possible.

## 5. Verdict: SHADOW (V3 meets the pre-registered bar on B1/B2 but is downgraded; V1/V2 shadow on conviction books (t < 2), dead on moderate10)

Downgrade reasons: (a) the precondition — the code actually seeing ~4x — is unverified (it reads 2.48);
(b) DSR 0.10 and a 2024-26 increment of +2.2pp; (c) P(DD>30%) doubles, the add. 32 precedent.

Switch (off by default, taxable margin book only, never paper/Roth):
- `daily.intraday_mult: broker | <float>` + `.env DAILY_INTRADAY_MULT=3.33` -> `executor._gate` uses
  `min(that, 4)` instead of the API ratio when the account is MARGIN and equity >= $2,000. Gate: Schwab.com
  Balances shows Intraday Margin Buying Power >= 3.5x equity (or `make daily-live-check` finds the API
  field); 3.33 (30% house) gives 96% of 4x's effect with headroom for the real-time blocker.
- `noise_target_vol: 0.03` (the Kelly x1.5 row) as a separate opt-in profile key; only with the
  multiplier at >= 3.33 on conviction books; kill if the live noise leg's 60-session drawdown exceeds 15%
  of equity, or if Schwab rejects >= 3 intraday orders for margin in 20 sessions (revert to `broker`).
- Shadow first: log the 0.03-target leg's P&L beside the live 0.02 leg (the executor already keeps a
  shadow equity per noise instrument) for 60 sessions.

Do NOT redo (final wording after verification):

| idea | verdict | why |
|---|---|---|
| More intraday buying power (3 / 3.33 / 4x) for a book WITHOUT the conviction trade (moderate10) | **dead** | the extra exposure lands on calm days, where the noise leg nets ~0 after tier_hi costs: +0.03..+0.18pp EH-AT, NW t 0.6-1.1, placebo 69-83 (add. 40) |
| Intraday cap at 3-4x for the conviction books (V7, moderate10c) | **shadow at most** | +0.5-0.6pp EH-AT tier_hi, both halves + 2016-20 positive, placebo 95-97, but NW t 1.6-1.7 (2024-26 t 0.5-0.6), DSR 0.05; negative at 2x tier_hi intraday costs (add. 40) |
| Noise leg Kelly x1.5 (noise_target_vol 0.03) at 4x | **shadow** (downgraded from a pre-registered pass on V7/moderate10) | +1.2-1.4pp EH-AT, NW t 2.0, placebo 98, but DSR 0.10, 2024-26 t 0.64, t 1.1-1.3 without the top 5 days, 2026 YTD -3.8pp, negative at 2x tier_hi intraday costs, P(DD>30%) 23->46%; moderate10c P(DD>50%) 5.4% fails (add. 40) |
| Roth intraday leg sized up after the PDT change | **not possible** | a limited-margin IRA gets no Intraday Margin Buying Power (add. 40; 3x on all daytime cash already borderline, add. 31) |

## Verifier notes (adversarial pass, 2026-09-29; scripts scratchpad/ibp_verify.py, ibp_rerun.py; no study file changed)

**Verdict stays SHADOW. Nothing here supports going live, and the multiplier is DEAD on moderate10.**

1. **Reproduction.** Re-running `replay` for B1 M2 base, B1 V3 and B2 V2 at tier_hi reproduces the
   pickled daily returns exactly (max |diff| 0.0). The executor's cap formula
   `mult*(1-conv*0.75)-w_ibs` (executor.py:1205-1206) is algebraically identical to `growth.cfg`
   (R3X 0.75). Kelly x1.5 is exactly noise_target_vol 0.03, because the sim's `lev` is uncapped (noise_leverage(...,1e9)) and the
   cap is applied later. It uses prior-14-day closes only, so there is no lookahead.
2. **Broker facts.** The schwab.com learn page refused automated fetch ("unable to authorize"). The
   same wording is confirmed by Schwab's July 2026 account-agreement amendments
   (disclosures.schwab.com REG91216): "Intraday Margin Buying Power generally reflects up to four
   times your margin maintenance excess for eligible securities that typically have a 25% margin
   maintenance requirement". Note it is 4x *maintenance excess*, not 4x equity. With IBS holdings at 25%
   that equals the study's `4 - w_ibs` formula, and at 30% house it equals R2. thinkorswim notes that
   higher-maintenance names get less. Whether the Trader API exposes the figure is still unverified,
   so adopt is impossible regardless.
3. **The mechanism in section 4.1 is wrong.** It says the moderate10 multiplier is null because the
   noise leverage "rarely exceeds the 1.5 cap". In fact QQQ vol-target lev (target 0.02) is > 1.5 on
   **67%** of days, with a median of 1.89. The cap binds most days. The extra exposure it would add is on
   calm days, and that earns ~0 net at tier_hi. The dead row should read "the extra exposure is on calm
   days, where the noise leg nets ~0 after tier_hi costs". The Kelly x1.5 row earns because it also scales
   the high-vol days, where lev < cap.
4. **Cost fragility (post-hoc stress).** With intraday costs at noise 3bp/fill and conviction 5bp/side
   (2x tier_hi), every increment turns negative:
   - B1 V2: -0.72pp EH-AT, t -0.32.
   - B1 V3: -0.84pp, t 0.14.
   - B2 V2: -0.56pp, t -0.90.
   - B2 V3: -1.05pp, t -0.01.
   - 2024-26 is -1.7 to -2.9pp/yr for all four.

   Break-even is roughly 2bp per noise fill. The whole case rests on live QQQ/SMH fills staying at or below ~1.5bp.
5. **Significance is thin and front-loaded.** V3 vs M2 at tier_hi, NW t by lag: 2.05 (5 lags), 2.08 (10), 2.21 (21).
   - By half, NW t is 2.35 in 2021-23 but **0.64 in 2024-26**.
   - The 2016-20 holdout increment is positive but NW t is only 0.72-1.13.
   - **Dropping the 5 best increment days** (2025-10-10, 2025-04-09, 2024-12-18, 2021-02-25, 2026-06-05) cuts the t to 1.26 (B1) and 1.06 (B2).
   - By year (B1): +11.7, +10.9, +6.1, +5.0, +6.2, and **-3.8 in 2026 YTD** (pp ann.).

   The multiplier rows (V1/V2/R2) have a 2024-26 t of 0.5-0.6 at tier_hi.
6. **Other checks.**
   - Pre-registration: the addendum was created at 00:11:46 and stamped 00:11:55. Outputs are timestamped 00:13:54 or later. The ordering is consistent, but I cannot prove no earlier unsaved run.
   - Variant count: 5 pre-registered plus 2 post-hoc (P1/P2) = 7 rule variants, x3 books.
   - The placebo is sign-randomisation of the increment, which is roughly a t-test. It is not a test of the noise edge.
   - The DSR uses iid t, which is 1.85 for V3 at tier_hi, below the NW 2.0.
7. **Switch conditions (tightened).** Keep both keys default OFF. Before any live use:
   - The shadow must show realised noise fills <= 1.5bp all-in over >= 60 sessions.
   - The shadow Kelly increment must be positive over that window.
   - The Intraday Margin Buying Power figure must be confirmed from the account or the API.
   - The multiplier override is useful only on conviction books, and V7 is the only one of those whose P(DD>50%) budget absorbs Kelly.


# Addendum 41 — the live noise-area rule on the most liquid single stocks (top 5/10/20 by dollar volume): DEAD (2026-09-29)

**Verified verdict: DEAD, no switch.** Every pre-registered variant lowers V7 and moderate10c in both halves at the measured
spread (C2 ~1.65bp/side), at 3bp and tier_hi, and still at zero stock cost. Best S10t: -3.3pp CAGR at 3bp night, -0.8pp EH-AT,
-$24/yr at $3k, -$802/yr at $100k. The top megacaps carry QQQ's gross trend-day edge; names outside the top 40 carry none;
the basket is 0.72 correlated with the QQQ leg and costs 3x more per side. Variants: 5 pre-registered + 1 control = 6.

## Pre-registration (stamped `Tue Sep 29 00:17:12 PDT 2026`, before any return of the stock rule, in any period, was computed)

Status at stamp: the universe (research/sim/stock_noise_univ.py) is built (ranks only, no returns);
the minute fetch (research/sim/stock_noise_fetch.py) is running. No noise-rule return, book number
or 2024-26 statistic of any stock has been computed.

### Hypothesis
The noise-area momentum rule works on QQQ (and SMH in 2021+) and fails on SPY after costs and on
IWM entirely (add. 6). One reading: intraday trend persistence comes from flows that concentrate in
the most traded, most optioned names (dealer gamma hedging, LETF rebalancing, retail attention);
QQQ is dominated by exactly those names, SPY dilutes them, IWM has none. If so, the rule should work
on the top names by dollar volume, and less on liquid names outside the top (control C2).
Against: megacaps are ~70% correlated with QQQ intraday, so a basket may just re-buy the QQQ bet
at a higher cost per side (the rule is cost-sensitive: QQQ 14.7% at 0.5bp, 9% at 1bp; add. 6).

### Universe (fixed rule, no tickers)
First session of each month: rank common stocks by the median of close x volume over the 63
sessions ending the previous session (SIP daily: add. 28 sipd1520 2016-01..2020-09, then the
research panel). Common stock = asset_meta on a US exchange, not ARCA, not an ETF/ETN/fund by
new_listings.etf_kind or by fund-issuer / levered / FUND/ETF/ETN/LP words, not a warrant / unit /
right / preferred / note; one share class per company (the more traded); duplicate histories
removed. Top N for the month; first month 2016-05. Distinct names: top5 20, top10 35, top20 80.
Known limit: asset_meta is the current listing file, so names delisted before it (TWTR, ATVI) are
missing from the ranking (survivorship: reported, not fixed).

### Rule per name (identical to the live leg, through swingtrader.daily.signals)
sigma = noise_sigma(14 prior sessions' |close_m/open - 1|); bands = noise_bounds(day open, prev close)
with prev close on the day's basis (adjusted daily close x today's raw/adjusted factor = what the
live adjustment='all' daily bar shows); decisions noise_decide at minutes 30, 60, ..., 360 on the
completed minute bar (the :01/:31 decision), flat at minute 389's close; leverage
noise_leverage(adjusted daily closes, 0.02, cap). 1-minute SIP bars adjustment='raw' (prices and
costs on raw prices; splits handled by the raw/adjusted daily factor). Half days dropped as for QQQ.

### Book variants (5; the basket shares the existing intraday budget and cap)
Each name gets min(lev_i, cap) x share / N_avail of equity; cap = the live intraday cap (0.75 with
conviction on, 1.5 with conviction off, from growth.cfg: TQQQ 75% margin, IBS half held).
- **S5r**  N=5, basket replaces the SMH half (QQQ 0.5, basket 0.5)
- **S10r** N=10, replaces SMH half
- **S20r** N=20, replaces SMH half
- **S10t** N=10, third stream at equal share (QQQ 1/3, SMH 1/3, basket 1/3)
- **S20t** N=20, third stream
Baselines (raw prices, load_sim(raw_price=True), night pools from cache_rawprice corr 0.7):
**V7 1.0x cap .10 conviction 0.5** (T0) and **moderate10c = 1.0x cap .15 conviction 0.5** (T2b), both
primary; conviction-off twins (T0L live today, moderate10) reported.

### Costs (per side, stock trades)
- C1 flat 3bp
- C2 spread-aware (primary): max(0.5bp, half the median quoted spread + 0.25bp), the median over
  sampled SIP quotes (4 sessions x 2 ten-second windows per symbol-year, 11:00 and 14:30 ET)
- C3 tier_hi on raw price and 63d dollar volume (book.cost_bps: 7.5bp for >$20 names)
QQQ/SMH keep 0.5bp (as every published book). Night leg at 3bp and tier_hi as in add. 39.

### Controls
- P1 placebo: the same trades (entry/exit minutes, sizes, costs) with each segment's direction drawn
  at random; 200 draws; the actual book increment must beat the 95th percentile.
- C2 control: the same rule on 10 random liquid names outside the top (ranks 41-100, drawn each
  January, seed 7), same budget as S10r; reported (answers "does attention matter").
- Diagnostic D1: per-name gross edge (bp/day, unit leverage) for the stocks and QQQ/SMH/SPY/IWM;
  cross-section of name-year gross edge on log dollar volume and trailing vol.

### Periods and tests
2021-23 / 2024-26 halves; 2016-20 holdout (book: IBS + noise + conviction, night leg 2020 only from
the raw rebuild, as program_books.tax_holdout); fit 2021-23 / judge 2024-26 and the reverse
(the variant with the best increment in one half, judged in the other); Newey-West (5 lags) t of
the daily book increment and day-clustered t of the per-name returns; edge-halves (growth.eh);
5y block bootstrap (21-day blocks) $3k + $1k/mo after 35% tax (taxable_frontier.mc_tax):
P(DD>30%), P(DD>50%); COVID 2020-02-19..03-23, 2022, Apr 2-8 2025, worst day / month;
after-tax (taxable_frontier.after_tax, 35%, wash sales from the trade list, basket as one lot).
Deflated Sharpe at N = 546 + this study's variants.

### Pass bar
ADOPT (a variant, on BOTH primary baselines):
1. book increment > 0 in 2021-23, 2024-26 and the 2016-20 holdout at C2 (night 3bp and tier_hi);
2. NW t >= 2.0 of the daily increment, 2021-26, C2;
3. beats P1 (>= 95th pct);
4. EH-AT (night tier_hi, C2) +0.3pp or more, and 5y P(DD>50%) up by <= 1pp;
5. increment >= 0 at C1 (3bp flat) full period;
6. the walk-forward pick (best in one half) is positive in the other half both ways.
SHADOW: 1-3 hold but 4, 5 or 6 fails. BORDERLINE: full-period positive but a half, the holdout
or P1 fails. DEAD: increment <= 0 in either half at C2, or P1 below the 80th pct.
Any post-hoc variant: SHADOW at most.

### Implementability (reported, not a gate)
The book is simulated fractional (as the QQQ leg). A whole-share replay at $3k + $1k/mo (floor of
each name's target / raw price) is reported: at user size a name's slice is ~$50-150, below one
share of most megacaps, and Schwab shorts need whole shares.

## How to run

    until mkdir $SCR/heavy.lock 2>/dev/null; do sleep 10; done; \
      PYTHONPATH=. .venv/bin/python -m research.sim.stock_noise_univ; rmdir $SCR/heavy.lock   # ~1 min, panel
    PYTHONPATH=. .venv/bin/python -m research.sim.stock_noise_fetch            # 525 symbol-years, 34 min (API limit 200/min)
    PYTHONPATH=. .venv/bin/python -m research.sim.stock_noise_fetch --quotes   # 433 symbol-years x 8 windows, ~6 min
    PYTHONPATH=. .venv/bin/python -m research.sim.stock_noise [--rebuild]      # 45 s; legs cache 35 s
    output: data/research/program/stock_noise_out.txt, res_stock_noise.pkl; scratchpad stock_noise_run.txt

Data: 135 symbols (top-20 members 2016-05..2026-09 plus the control draws), 124,256 name-days,
102,632 trade segments. Splits checked (NVDA 2021/2024, AAPL/TSLA 2020, AMZN/GOOGL 2022): prev close
on the day's basis matches the raw open. Baselines reproduce addendum 39 to the decimal (V7 47.2/2.06
at 3bp, 29.4/1.41 tier_hi; moderate10c 55.5/2.15, 32.1/1.39; EH-AT tier_hi 8.6 / 9.3).
Deviation (data collection only, before any result): the quote sampler first ran with Alpaca's
default 1,000-record pages and hit the 200 req/min limit; it was restarted with 10,000-record pages
(`limit=10000`), same windows. Quoted spreads: median 3.2bp over all sampled symbol-years; AAPL
0.6-0.7bp, MSFT/NVDA ~0.7-0.8bp, BKNG/MSTR 20-30bp. 73% of records carry different bid and ask
exchanges (NBBO-like); if some are single-exchange BBOs, C2 is slightly high.
C2 per side, median over top-20 name-days 1.65bp (p90 4.3); control 2.05bp (p90 6.7); C3 7.5bp.

## Results (every variant: 5 pre-registered + CTRL10r control; 4 baselines x 2 night costs x 3 stock costs)

### Q1. The rule per name (unit leverage), mean bp/day, day-clustered t: 2016-20 | 2021-23 | 2024-26

| series | gross | C1 3bp | C2 spread | C3 tier_hi |
|---|---|---|---|---|
| QQQ (ETF) | +4.4 (3.1) / +6.1 (3.0) / +3.2 (1.6) | | 0.5bp: see book-wtd | |
| SMH (ETF) | +2.4 (1.4) / +9.2 (3.2) / +4.7 (1.5) | | | |
| SPY (ETF) | +1.8 (1.5) / +5.0 (3.1) / 0.0 (0.0) | | | |
| IWM (ETF) | -0.4 / -0.4 / -1.6 | | | |
| top 5 | +4.0 (2.6) / +6.8 (2.7) / +3.6 (1.5) | -0.8 / +1.6 / -1.0 | +1.4 (0.9) / +4.5 (1.8) / +1.4 (0.6) | -8.0 / -6.1 / -8.1 |
| top 10 | +3.9 (2.8) / +6.4 (3.1) / +1.9 (0.9) | -1.0 / +1.3 / -2.8 | +0.7 / +3.6 (1.8) / -0.9 | -8.6 / -6.4 / -9.8 |
| top 20 | +2.7 (2.5) / +3.9 (2.4) / +1.9 (1.1) | -2.2 / -1.2 / -2.8 | -0.5 / +0.4 / -2.4 | -9.7 / -8.8 / -9.9 |
| control (ranks 41-100) | -0.2 / +1.2 / +0.3 | -5.2 / -3.8 / -4.6 | -3.5 / -5.7 / -6.7 | -13.1 / -12.1 / -12.8 |

Book-weighted (min(lev, 0.75) x net, the unit the book actually holds): QQQ at 0.5bp +2.9 / +3.9 / +1.8;
SMH +1.4 / +6.0 / +2.8; top 5 at C2 +1.4 / +3.1 / +0.9; top 10 +0.7 / +2.3 / -0.7; top 20 -0.2 / +0.1 / -1.5.
The vol-target sizing (2%/day) gives the high-vol names, where the gross bp/day is, less weight.

**D1 (why QQQ works, SPY/IWM don't).** Gross, the top-5 megacaps carry the same trend-day
persistence as QQQ (4.0/6.8/3.6 vs 4.4/6.1/3.2bp/day); the random liquid names outside the top carry
none (-0.2/+1.2/+0.3, and its random-direction placebo percentile is 71%). SPY dilutes the megacaps
and fades to 0 in 2024-26; IWM (no megacaps) is negative. So the edge is concentrated in the most
traded names, consistent with the attention/hedging story. But across 378 name-years the gross
edge is explained mainly by the name's volatility (logvol +5.7bp per log unit, t 6.8), dollar volume
adds +0.5 (t 1.3). The basket is 0.72 correlated with the QQQ leg day by day: it is the QQQ bet
again, bought at 1.6bp/side instead of 0.5bp, with less weight on the names that carry it.
QQQ is the cheapest wrapper of the same effect; SMH adds a different one (semis, 2021+).

### Q2. Book increments (pp CAGR vs baseline), stock cost C2 (primary)

| variant | V7 3bp: HO / 21-23 / 24-26 / full, NW t | moderate10c 3bp: HO / 21-23 / 24-26 / full | V7 tier_hi full | m10c tier_hi full |
|---|---|---|---|---|
| S5r | +0.3 / **-6.2** / **-2.9** / -4.6, t -1.9 | +0.3 / -6.1 / -3.2 / -4.7 | -3.9 | -3.9 |
| S10r | -0.6 / -7.2 / -5.8 / -6.5, t -2.9 | -0.6 / -7.2 / -6.2 / -6.7 | -5.6 | -5.6 |
| S20r | -1.8 / -11.2 / -7.0 / -9.1, t -4.3 | -1.8 / -11.4 / -7.5 / -9.5 | -7.9 | -8.0 |
| S10t | -1.2 / -3.3 / -3.3 / -3.3, t -3.5 | -1.2 / -3.4 / -3.6 / -3.5 | -2.9 | -2.9 |
| S20t | -2.0 / -6.2 / -4.1 / -5.2, t -5.6 | -2.0 / -6.2 / -4.5 / -5.4 | -4.5 | -4.5 |
| CTRL10r | -4.7 / -18.3 / -11.1 / -14.8, t -6.4 | -4.7 / -19.0 / -11.9 / -15.6 | -13.0 | -13.3 |

C1 (3bp flat), V7 3bp full: S5r -7.9, S10r -9.1, S20r -10.6, S10t -5.2, S20t -6.2, CTRL10r -12.8pp. C3 (tier_hi): S10t -11.0 ... S20r -18.7, CTRL10r -21.7pp.
Conviction off (T0L / moderate10, cap 1.5): worse, S5r -6.7 / -7.1pp full at 3bp, S10t -5.2 / -5.4.
Post-hoc diagnostic (not a variant): at ZERO stock cost, V7 3bp increments are still negative in both halves
(S5r -3.4 / -0.4, S10r -4.0 / -2.7, S10t -1.2 / -1.2, S20t -3.3 / -1.2): cost is not the only problem;
the basket earns less per unit of intraday budget than the SMH half it displaces.

Baselines: V7 HO 15.6/1.06/-19 | 50.2/2.26/-9 | 44.1/1.87/-14 | 47.2/2.06/-14 (3bp), 29.4/1.41/-17 tier_hi;
moderate10c HO 16.3/1.07/-23 | 56.5/2.30/-9 | 54.5/2.01/-18 | 55.5/2.15/-18, 32.1/1.39/-21 tier_hi.

### P1 placebo (200 random-direction draws, mean daily increment 2021-26, C2, night 3bp)
Top variants beat their placebos (pct 100% for all five, both baselines: e.g. V7 S10t actual -0.94bp/day,
placebo median -1.80, p95 -1.50): the direction carries information. It is still a loss: the placebo
bar compares against a random-direction basket that also pays the costs, not against SMH.
Control CTRL10r: 71% (no direction information outside the top names).

### Walk-forward pick (C2, night 3bp)
V7: fit 2021-23 -> S10t (-3.3pp) -> 2024-26 -3.3pp; fit 2024-26 -> S5r (-2.9) -> 2021-23 -6.2pp.
moderate10c: S10t (-3.4) -> -3.6; S5r (-3.2) -> -6.1. The best variant is negative in both halves both ways.

### EH, after tax, MC, crashes (C2; night tier_hi unless noted)

| book | EH-AT | 5y MC median / P(DD>30%) net (acct) / P(DD>50%) | COVID | 2022 | Apr 2-8 2025 | worst day / month |
|---|---|---|---|---|---|---|
| V7 base | 8.6 | $78.0k / 17% (35%) / 0% (1%) | -11.4% | +47.3% | +6.0% | -6.4 / -11.2 |
| V7 S5r | 7.5 | $76.0k / 17% (33%) / 0% (0%) | -11.6% | +43.7% | +5.2% | -5.9 / -11.3 |
| V7 S10r | 7.0 | $75.0k / 18% (35%) / 0% (1%) | -12.1% | +43.4% | +4.9% | -6.0 / -11.7 |
| V7 S20r | 6.3 | $73.7k / 19% (35%) / 0% (1%) | -11.1% | +36.9% | +5.3% | -6.0 / -11.7 |
| V7 S10t | 7.8 | $76.4k / 17% (34%) / 0% (0%) | -12.6% | +45.5% | +5.5% | -6.3 / -11.3 |
| V7 S20t | 7.3 | $75.5k / 18% (35%) / 0% (0%) | -11.9% | +41.0% | +5.7% | -6.3 / -11.3 |
| V7 CTRL10r | 4.7 | $70.8k / 25% (42%) / 1% (1%) | -12.0% | +29.4% | +5.4% | -6.0 / -11.2 |
| m10c base | 9.3 | $79.5k / 27% (49%) / 1% (2%) | -12.5% | +51.8% | +6.8% | -7.7 / -11.0 |
| m10c S5r | 8.1 | $77.5k / 25% (46%) / 1% (2%) | -12.7% | +48.3% | +6.0% | -7.3 / -11.2 |
| m10c S10r | 7.6 | $76.6k / 27% (48%) / 1% (2%) | -13.2% | +47.7% | +5.7% | -7.3 / -11.5 |
| m10c S20r | 7.0 | $75.3k / 28% (49%) / 1% (2%) | -12.2% | +41.0% | +6.1% | -7.3 / -11.6 |
| m10c S10t | 8.5 | $78.0k / 28% (49%) / 1% (2%) | -13.7% | +49.9% | +6.3% | -7.5 / -11.2 |
| m10c S20t | 8.0 | $77.2k / 28% (49%) / 1% (2%) | -13.0% | +45.5% | +6.5% | -7.6 / -11.2 |

At 3bp night: V7 EH-AT 13.6 -> 12.3 (S5r) ... 11.1 (S20r), 12.7 (S10t); moderate10c 15.7 -> 14.4 ... 13.2, 14.8.
The basket slightly lowers the worst day (-6.4 -> -5.9%) and nothing else.

### $/yr (delta EH-AT x capital, night tier_hi, C2)
Best (least bad) variant S10t: V7 -0.80pp = **-$24/yr at $3k, -$802/yr at $100k**; moderate10c -0.81pp
(-$24 / -$812). S5r -$34 / -$1,145; S10r -$48 / -$1,584; S20r -$68 / -$2,261; S20t -$38 / -$1,270 (V7).

### DSR (N = 552): every increment has negative Sharpe (t -2.0 .. -5.5); DSR 0.000.

### Implementability
Whole shares at $3k + $1k/mo (V7 3bp, C2): the basket fills 76-81% of its target over the path (growing
equity); S10r -7.1pp, S10t -3.8pp vs base. At the user's current $3k a name slice is ~$40-110, under one
share of most top names; Schwab shorts need whole shares. Moot: the fractional book already loses.

## Verdict: DEAD

Every pre-registered variant lowers the book in BOTH halves on BOTH primary baselines at the realistic
spread cost (C2), at 3bp and at tier_hi, and in the walk-forward pick both ways; NW t -1.9 to -5.6.
Only S5r's 2016-20 holdout is marginally positive (+0.3pp). It fails pass-bar items 1, 2, 4, 5, 6
(it passes 3, the placebo, which shows the direction is informative but not enough to pay for itself).
Even at zero stock cost the increment is negative. The attention story holds for the GROSS edge
(top names ~ QQQ, random liquid names ~0), which is exactly why QQQ already captures it; the single
names add cost, lower vol-targeted weight on the names that carry it, and displace SMH. No switch.

## Do NOT redo

| idea | verdict | why |
|---|---|---|
| Noise-area rule on the top 5/10/20 stocks by dollar volume, replacing the SMH half or as a third intraday stream | **dead** | book -3 to -9pp in both halves at the measured spread (C2), -5..-11pp at 3bp; negative even at zero stock cost; basket corr 0.72 with the QQQ leg; best S10t -$24/yr at $3k, -$0.8k at $100k (add. 41) |
| Same rule on liquid stocks outside the top 40 (ranks 41-100) | **dead** | gross ~0 bp/day, placebo 71%: the trend-day persistence lives only in the most traded names, which QQQ already holds (add. 41) |
| Single-stock intraday legs as an "attention" diversifier to QQQ | **dead** | gross edge scales with name vol (t 6.8), dollar volume adds little (t 1.3); QQQ is the cheapest wrapper of the same effect (add. 41) |

## Caveats
- Survivorship: asset_meta is today's listing file; names delisted before it (TWTR, ATVI) never enter the
  ranking. Few top-20 months are affected; the verdict does not hinge on them.
- The day open is the first 1-minute bar's open (as the QQQ/SMH sim); live uses Schwab's official open.
- Quote samples: 8 ten-second windows per symbol-year; records are ~73% NBBO-like. C1 (3bp flat) and the
  zero-cost diagnostic bracket the cost question: the verdict is the same at any cost.
- The basket is one lot in the wash-sale model (after-tax figures approximate); pre-tax verdict is unaffected.
- Placebo increments use the variant's daily return with the basket swapped (no re-replay); rounding effects
  on the night/IBS legs are ignored there.

## Verifier notes (adversarial check, Tue Sep 29 2026)

Verdict upheld: **DEAD**. No bug was found and no file of the study was changed.

- **Independent rule re-implementation.** I wrote a separate loop from the raw 1-minute parquet (scratchpad/snv_indep.py) that does not call the study's code or swingtrader.signals. For NVDA, TSLA, AAPL and AMZN (2,677 name-days each) it matches the cached per-name-day gross exactly: max |diff| 0.0 and 0 trade-count mismatches. Decisions use C[m] at m = 30..360, the completed-bar close, and exit at minute 389, the same as book.noise_days for QQQ. Leverage uses only prior daily closes. No lookahead.
- **Splits.** On the split days (NVDA 2021-07-20 and 2024-06-10, TSLA 2020-08-31 and 2022-08-25, AAPL 2020-08-31, AMZN 2022-06-06) the open-vs-prev-close gap is 0.2 to 2.4%, i.e. correctly rebased. The largest |gaps| are real events (NVDA 2023-05-25 +26%). Sigma uses intraday ratios, which splits do not affect.
- **Universe.** It is point in time. The rank uses med.iloc[i-1], the 63-session median ending the previous session. Survivorship (current asset_meta) is disclosed. It would bias toward the variant, not against it, so it cannot rescue the result.
- **Cap and margin model.** p.noise_cap is 0.75 with conviction and 1.5 without, for all four bases. That matches CAPS, so the basket dict lookup never silently drops the basket. In the design, the basket shares the existing intraday budget. This matches the live cap (executor: room = mult x (1 - conv x conviction_margin), split across legs).
- **Decisive book numbers re-run** (scratchpad/snv_book.py). Increments at 3bp night, V7 / moderate10c, 2021-23 / 2024-26, are reproduced exactly:
  - S5r C2: -6.2/-2.9 and -6.1/-3.2
  - S10t C2: -3.3/-3.3 and -3.4/-3.6
  - zero stock cost: S5r -3.4/-0.4, S10t -1.2/-1.2
  - baselines: 50.2/44.1 and 56.5/54.5
- **Mechanism check.** On book-weighted net bp/day the result is simple arithmetic. The top-5 basket at C2 (+1.4/+3.1/+0.9) is below both QQQ (+2.9/+3.9/+1.8) and SMH (+1.4/+6.0/+2.8) in every period, so any budget-neutral swap loses.
- **Diagnostic only, not a variant.** I added the top-5 basket (share 0.5) ON TOP of QQQ/SMH .5/.5, which breaks the live margin cap. This gives +5.2/+1.3pp (V7) and +5.4/+1.3pp (moderate10c). That is extra leverage on a positive-but-inferior stream. It is infeasible under the broker multiplier, and the same room would be better spent on QQQ/SMH. It is not a path to adoption, and I count it as a post-hoc diagnostic.
- **Pre-registration.** The stamp is 00:17:12. The leg cache is dated 00:49 and the debug and output files 00:50-01:06, so the stamp comes first. Variants: 5 pre-registered plus 1 control = 6. Post-hoc diagnostics (zero cost, whole shares, the verifier's additive run) are not variants.
- **Placebo.** It randomizes segment direction and holds costs fixed, so it only tests "gross edge > 0". Beating it (100th pct) does not bear on the book-effect verdict.
