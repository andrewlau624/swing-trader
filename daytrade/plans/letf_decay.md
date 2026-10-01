# Plan: letf_decay (Study Lab-BK)

Written 2026-10-01 before any computation. Pre-registration: `research/drafts/round1_prose.md`, Lab Round 35 (2 variants,
program N 724 -> 726). A multi-day, market-neutral book; it needs a MARGIN account (shorts), so not the Roth and not
a cash account under $2k.

## The idea (mechanical, not a pattern)
A daily-rebalanced L-times ETF loses about (L^2 - L)/2 x sigma^2 a year to volatility drag: 3 sigma^2 for +3x and
6 sigma^2 for -3x. Short BOTH the +3x and -3x ETF on the same index in equal dollars. The book is index-neutral at
each rebalance and earns the drag. The risks: borrow fees (the bear ETFs are often hard to borrow), short gamma between
rebalances (a big one-way week costs), and recalls. Checked: no study of shorting LETF pairs in RESULTS.md / NEXT.md /
round1_prose.md (Study W only weighted LETF night picks).

## Exact rules
- Pairs: Lab-BK1 TQQQ + SQQQ (Nasdaq-100); Lab-BK2 UPRO + SPXU (S&P 500).
- Equity E: short 0.5 E of each leg. Rebalance both legs back to 0.5 E each at every week's last regular close
  (market-on-close). Margin: 3x ETFs carry ~75% maintenance, so 2 x 0.5E x 0.75 = 0.75E fits.
- Data: Alpaca SIP DAILY bars, split-adjusted (the bear ETFs reverse-split often), closes = closing crosses,
  2016-01 .. 2026-09.
- No interest earned on short proceeds (conservative; retail rarely gets a rebate).

## Costs
- 1x: 5bp per side on traded notional at each rebalance; borrow 2%/yr on the bull leg and 4%/yr on the bear leg.
- 2x: 10bp per side; borrow 5%/yr bull, 10%/yr bear.

## Measures
- Weekly return on E, both tiers; halves 2016-2020 / 2021-2026-09; CAGR, max drawdown, worst week, correlation with
  the index.
- Reference (not a pass criterion): the same short pair in 1x/-1x (QQQ + PSQ) with the same costs. Little drag
  there, so it shows what the mechanism adds.

## Pass bar, per variant
Mean weekly net > 0 at 2x in BOTH halves; t >= 2.0 (weekly); mean without the 5 best weeks > 0; max drawdown at 1x
better than -40%.
