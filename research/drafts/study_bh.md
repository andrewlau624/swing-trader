# Study BH — Asymmetric Bottom Hunter (pre-registered N 818 → 819)

Registered before any drawdown-conditioned forward return was read (`round1_prose.md`, append). One judged primary;
everything else pre-specified report-only. Runner `research/sim/bottom_hunter.py`; output
`data/research/program/bottom_hunter_out.txt`; one look, 2026-10-04.

## Verdict: KILL

Extreme price depression does **not** carry a favorable forward asymmetry. It carries the opposite: a falling knife
with a lottery tail. Every judged gate failed. There is no systematic edge here; the apparent "buy the bottom" payoff
is (a) a small handful of repeat-rebound names, (b) survivorship/illiquidity, or (c) plain long-beta dip-buying in a
bull market — none of which is the idea the study set out to test.

## Primary (judged) result
Sleeve: `DD252 <= -70%`, close >= $3, 10 slots, conviction sizing, 25% trail / close<MA50 / 126d exit, tier_hi costs,
vs the same-day same-vol-decile random placebo (30 seeds), 2021-10..2026-09.

| gate | result | pass |
|---|---|---|
| mean excess vs placebo > 0 | +20.5 bp/day | yes |
| day-clustered t >= 2 | **t 1.32** | **no** |
| ex-best-5-day excess > 0 | +4.1 bp/day | marginal |
| 2016-20 extension excess > 0 | +9.5% mean but **median -14.3%** (survivorship-limited) | no |

**FAIL (2 of 4).** The ex-best-5 result is the tell: the entire positive mean lives in a few days.

## Why: the asymmetry is exactly backwards (R1/R2)

Forward excess return vs that day's eligible universe, by `DD252` bucket, entry next open (2021-26):

| bucket | H=126 excess mean / median | P(-50 further) | recover prior 252d high <=252d |
|---|---|---|---|
| DD -30..-50 | -1.1% / -5.8% | 6.9% | — |
| DD -50..-70 | -0.4% / -11.5% | 13.7% | — |
| **DD -70..-85** | **-5.4% / -20.7%** | 20.1% | — |
| **DD <=-85** | **-17.0% / -35.5%** | 38.1% | — |
| DD <=-70 (extreme) | -8.6% / -24.2% | 25.0% | **2.4%** (base 40.3%) |

Deeper drawdown -> worse forward return, monotonically. The right tail is real but small and does not pay for the
left: at H=252 extreme names still show P(+100)=10.3%, P(+500)=0.8%, yet excess mean is -6.5% and excess median -35.5%.

**Falling knife (R2):** after `DD<=-70`, the median *additional* drawdown (min future low / entry open - 1) is -18.0%
at 21d, -32.3% at 63d, **-44.6% at 126d**, -56.2% at 252d. P(another -50%) = 42% at 126d, 58% at 252d.
"It can't go lower" is false, and the recovery rate to the old high within a year is 2.4% vs 40.3% for the average name.

## Cheap vs broken (R3): no survival filter rescues it
126d excess mean, conditioned on the extreme signal:

| filter | excess mean | excess median | note |
|---|---|---|---|
| price >= $10 | **-26.2%** | -33.2% | expensive fallen angels are the worst |
| price $1-3 ("broken") | +19.8% | **-11.9%** | lottery/microcap; median negative, P(-50)=16% |
| ADV >= $10M | -5.5% | -19.2% | liquidity does not help |
| close > MA20 ("stabilizing") | -8.3% | -24.1% | waiting for the bounce *lowers* the payoff |
| not a new 252d low | -9.6% | -25.9% | no help |
| insider buy <= 60d (Form 4) | -3.4% | -20.2% | mild, still negative |

The only positive-mean cell is sub-$3 names, and it is a right-tail lottery (mean +19.8, median -11.9). Every filter's
placebo (same day, same vol decile, random) is between -2.6 and -4.2 bp — i.e. the signal adds nothing durable.

## Entry timing (R3/R4): confirmation does not fix it
Requiring `close > MA20` before entry *reduces* the conditional excess (-8.3% vs -8.6% median-adjusted) — you pay the
first leg of the bounce and still own the failure rate. The only sleeve that printed a large CAGR doing this
("conv+MA20 confirm", 207% CAGR) is a single-name artifact: **FFAI averaged +36%/trade over 65 trades**, and the
variant still earns 131% ex-best-5 days. That is the "one 20x winner is not a strategy" failure mode, demonstrated.

## Position sizing (R6) — the one non-trivial finding, but not a fix
Conviction sizing (size ∝ drawdown depth x a stabilization flag, capped 10%/name) beat equal sizing on the sleeve:
CAGR 6.3% -> 9.9% (equal -> conviction), 2021-10+ 7.1% -> 11.6%, Sharpe 0.49 -> 0.54. But both are outlier-carried
(ex-best-5-days CAGR -20.1% equal, -17.3% conviction) and cost-fragile: a flat 25 bp/side charge turns the conviction
sleeve from +9.9% to **-9.6%** CAGR (tier_hi is ~7.5-25 bp by price/ADV). Sizing increases the exposure to the tail;
it does not create the edge.

## Theme / quantum sub-experiment (R5): QTUM is beta, the basket is one survivor
Buy each instrument after its own `DD252 <= -30%`, hold 126 sessions, excess vs SPY:

- Quantum **ETF QTUM**: +17.2% excess, n=15 (2018+). This is the defensible, survivorship-free version and it is just
  a levered-bull-market dip buy (QQQ +4.4%, SMH +22.5%, ARKK +30.3% on the same rule) — not quantum-specific.
- Quantum **basket** (RGTI IONQ QBTS QUBT ARQQ): QBTS +158% excess (n=14) is the entire effect; IONQ -25.6%,
  ARQQ -49.0%, RGTI +5.9%, QUBT +19.4%. The "edge" is hindsight-selecting the survivor. This is exactly the
  survivorship trap the registration warned about and it reproduces the add-28 theme-explosion verdict.

## Robustness summary
- **Best-trade removal:** ex-best-5-days kills the sleeve (-17.3% CAGR); the primary ex-best-5 excess is +4.1 bp/day.
- **Cost shock:** flat 25 bp/side -> -9.6% CAGR (from +9.9%).
- **Placebo:** random same-vol-decile names, -4.2% CAGR; the signal is not attributable to universe/exit.
- **Sub-periods:** excess by year +13 / +69 / -2 / +109 / -46 / +112 (x100 bp) — sign flips; no stable regime.
- **OOS 2016-20** (bars_pre2021, survivorship-limited to today's symbols): raw +22.2% / median -2.6%;
  excess +9.5% / median -14.3% — the survivorship flattery, not OOS support.
- **Recovery base rate** 2.4% (extreme) vs 40.3% (all names): the "bounded downside / eventual repricing" premise
  is empirically false on this panel.

## Capital simulation (conviction sleeve, 2021-10..2026-09, tier_hi, no cross-size compounding)
CAGR 11.6%, Sharpe 0.54, maxDD -83.7%. Dollars: $2.5k -> ~$289/yr; $10k -> ~$1.16k/yr; $25k -> ~$2.9k/yr;
$100k -> ~$11.6k/yr. Average hold ~126d or the trail; ~12.6k trades over 6 yr (~10/day).

## Blunt conclusion
**There is no systematic edge. This is a sophisticated way to buy falling stocks.** The market's extreme pessimism
is warranted more often than not: drawdown depth predicts *lower* forward returns, extreme names almost never recover
their old high within a year, and the positive mean is a lottery carried by a few repeat-rebound tickers (FFAI) and by
survivorship in the pre-2021 extension. Conviction sizing helps relative to equal sizing, but only by levering the
same tail. **No live capital.** Do not re-run this as a bottom-fishing sleeve; the class is dead. Consistent with
`NEXT.md`'s long-term-reversal, falling-knife, going-concern-relief and theme-explosion verdicts.
