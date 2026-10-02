# Study G2: EV2-big as an intraday overlay on a SPY core, judged on the 2016-20 holdout: NEAR

Goal hunt (`prompt_strategy_goal.md`, session llm-trader-ec), idea G2 (`goal_ideas.md`, track T1). Pre-registered in
`round1_prose.md` (e6316e8, N 768 -> 772) before any 2014-21 insider file was parsed. Runner `research/sim/goal_g2.py`
(build 3cbe7cf; one judge look; the first judge run crashed on a DSR print after the per-trade lines, and the rerun is
the same code with that print fixed). Output: `data/research/program/goal_g2_out.txt`. k = 1.

## Rule
- **The event (EV2-big):** officer/director code-P Form 4 purchases summing to >= $500k at one issuer on one filing date. Nobody bought that
  issuer's stock in the open market in the previous 730 days. Prior raw close >= $5, 20d ADV$ >= $20M. The ticker-reuse guard (Form 4 price
  within 0.67-1.5x the prior close) drops 732 of the 30,608 candidates.
- **The trade:** buy the opening cross and sell the closing cross of the first session after the filing date.
- **The book:** 100% SPY in taxable (total return; dividends taxed when paid). The overlay is intraday only: G2a puts 0.5x of equity in each
  event and G2b puts 1.0x, with the overlay gross capped at 1.0x. Overlay gains are taxed short-term at 35% each year; the SPY gain is taxed
  at 20% at the end. Shares are whole.

## Result on the 2016-20 holdout (untouched for this rule)
195 trades (39 a year: 22 / 30 / 59 / 39 / 45 by year).

| | net per trade | median | hit | by year (bp) |
|---|---|---|---|---|
| 2.5bp/side | **+68.7bp** | +38.2 | 61% | +95 / +57 / +31 / +111 / +76 |
| tier_hi | +55.4bp | +27.0 | 58% | +83 / +44 / +18 / +98 / +61 |

G2a overlay (0.5x per event):
- NW t **+3.48**. The overlay is positive in every one of the 5 years.
- Lottery test: the overlay sum is +0.688 in all. Without its best 5% of days it is still +0.329; without its best 5 trades, +0.455. **Passes.**
- Random-pick null (1,000 draws, same sessions, ADV >= $20M, price >= $5): the real result is at the **100th percentile** (null mean +0.027).
- DSR at N 772: overlay 0.553, SPY+overlay 0.435.

After-tax CAGR vs SPY (time-weighted, no deposits; the +$1k/month money-weighted IRR is in brackets):

| | $2.3k 2.5bp | $10k 2.5bp | $2.3k tier_hi | $10k tier_hi | max DD | worst month | worst trade |
|---|---|---|---|---|---|---|---|
| **G2a 0.5x** | 24.0% vs 12.7% **+11.3pp** (+12.5) | +11.3pp (+12.2) | +9.1pp (+9.9) | +9.0pp (+9.7) | 31-32% | −9.5% (2020-03) | SPG 2020-03-18 −5.9% of equity |
| G2b 1.0x | +20.9pp (+23.7) | +21.0pp (+23.0) | +16.5pp (+18.8) | +16.5pp (+18.2) | 33-34% | −10.7% (2018-12) | EQIX 2020-04-07 −8.2% of equity |

Every registered holdout bar passes for G2a at the primary 2.5bp cost: (1) per trade > 0 at both costs, (2) NW t >= 2, (3) the lottery test,
(4) null >= 95th percentile, (5) >= 4 of 5 years positive, (6) >= SPY+10pp at $2.3k and $10k with max DD <= 35% and >= 100 trades.
At tier_hi, G2a misses +10pp by about 1pp; G2b clears it at both costs.

## Why NEAR and not FOUND
1. **2021, the sixth untouched year, was flat.** 58 trades, **−10.0bp** a trade at 2.5bp (median −39, hit 45%), overlay NW t +0.09, and
   negative without its best days or trades. The +10.5pp money-weighted IRR printed for 2021 at $2.3k is deposit timing: every win came in
   Q4, when the deposits had made the account several times larger. With no deposits, 2021 is −0.6pp vs SPY.
   The EV2 rule at all sizes was also −10bp in 2021; ID3 >= $500k without the silence filter was +24bp.
2. **The goal's FOUND bar needs a clean 2024-26 judge half, and this rule has none.** The >= $500k cut was found on 2022-26. Its
   in-sample numbers are strong (EV2 $500k-1M +72bp, >= $1M +101bp a trade) but can't count. The holdout replaced the judge half by
   registration, and the prompt says not to redefine FOUND.
3. **DSR 0.55 < 0.95**, the program's best level but not past deflation at N 772.

So the bar it missed is **"a clean judge half"**. The only clean test left is forward. It also misses +10pp at tier_hi by about 1pp.

## What the reported rows say (the size cut, not the silence filter, carries it)
- **EV2 at all sizes, holdout:** +7.9bp a trade (2.5bp), −6.4bp at tier_hi; 2018 and 2020 negative. Without the size cut it is ~0.
- **ID3 >= $500k without the silence filter, holdout:** **+35.7bp** a trade, 1,788 trades (358 a year), positive in every year; tier_hi
  +20.0bp; 2021 +23.8bp. A broader and more stable version: half the edge per trade, nine times the trades.
  Reported only; any rule built on it needs its own registration.

## Caveats
- **Survivorship:** 13,088 of 43,696 candidates have no Alpaca bars, mostly delisted symbols, and those events are lost. The random-pick
  null draws from the same surviving-symbol pool, and its mean is about 0, so survivorship doesn't by itself make a one-day open->close pick
  look good. But the lost names are not a random sample.
- **Price data:** 2016-20 opens are Alpaca SIP first prints, not verified against the official opening cross. ID3 checked that on 2021+
  (0.0bp); it was not re-checked for 2016-20.
- **One small lookahead in the build:** an event is dropped when no session exists within 7 days of the filing (halts and delistings).
- **Whole SPY shares are not modelled** (fractional SPY in the core). At $2.3k that is about 5-7 SPY shares, and the cash drag is under 1pp.
- **Concentration:** G2a puts 0.5x of equity in one stock for one session. The worst single trade was −5.9% of equity (SPG in March 2020).
  A halt or a gap after a bad headline intraday is the tail.

## Follow-up (the one NEAR follow-up; pre-registered here before any forward outcome)
The live ID3 shadow already logs EV2-big trades: `testing.py` "EV2 x buy >= $500k", 60-trade gate, `make forward-status`.
**G2-F:** when that gate reaches 60 scored EV2-big trades (about 1-1.5 years at 40-60 a year):
- **PASS:** mean net per trade (at the measured live cost) >= +30bp and NW t >= 1.5, and the G2a book on those trades (SPY core,
  0.5x per event) beats SPY by >= +10pp a year after tax at $2.3k and $10k.
- **Otherwise DEAD,** and EV2-big goes back to being a weight inside ID3.
- **No interim decisions** (FALSE-ALARM death).

On PASS: build G2a behind an `.env` switch, default OFF, with a testing.py entry. Nothing is built now.

## Money (if the holdout is the truth; G2a, 2.5bp, after tax)
- **$/yr vs holding SPY:** about +11pp a year → **~+$260 at $2.3k, ~+$1,130 at $10k, ~+$2,800 at $25k.**
- **Capacity:** at $100k, an event gets $50k in a $20M+ ADV name, which is fine. At $500k, $250k per event is about 1% of ADV in the
  thinnest names and is where impact starts (not tested).
- **What it needs:** intraday buying power (taxable margin account; the Roth can't run it on top of a SPY core) and one MOO + MOC pair on
  the event day. The server can do both.
