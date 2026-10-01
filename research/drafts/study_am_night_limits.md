# Study AM — limit orders at the bid/ask for the night leg (Round 17)

`research/drafts/round1_prose.md` Round 17, Study AM (pre-registered before any number).
Code: `research/sim/night_limit.py`. Output: `data/research/program/night_limit_out.txt`.
N = 642 -> 654 (6 variants). Data: `data/research/night/lm1`+`lm6` (15:50-16:00) and `am1`
(09:30-10:31); 9,412 of 9,546 raw-pool picks have the close window (99%), 71% the next-open window.

## The model (and its bound, stated up front)

The repo has **no quotes/order-book data**: only SIP trade prints. The limit is therefore modelled
on the trade path with the repo's per-name tick cost. A close-auction buy limit at
`L = p50 x (1-b)` fills at L if the 15:50-15:59 trade low reaches it, else at the official close if
`close <= L`, else the name is skipped and its budget is redeployed pro-rata to the filled names.
Open-auction sell variants rest on the shipped close buy.

## Results (2021-23 / 2024-26 pp/yr of the book; NW t 2021-26)

| variant | fill | adverse sel. | tier inc | tier_hi inc | NW t (th) | placebo |
|---|---|---|---|---|---|---|
| AM1 limit buy b=5bp | 84.0% | +39bp | +0.31 / −0.52 | +0.44 / −0.43 | −0.09 | 46% |
| AM2 limit buy b=10bp | 79.3% | +33bp | +0.18 / −0.36 | +0.36 / −0.24 | +0.11 | 52% |
| AM3 limit buy b=20bp | 71.4% | +41bp | +0.70 / −0.01 | +0.96 / +0.15 | +1.74 | 97% |
| AM4 buy at the window low (upper bound, look-ahead) | 98.6% | +122bp | +7.58 / +8.71 | +7.59 / +8.72 | +35.9 | 100% |
| AM5 sell at/above the prior close else 09:59 | 55.1% | — | +0.19 / −1.58 | same | −2.60 | — |
| AM6 sell at open+1 tick else 09:59 | 91.5% | — | −1.49 / −2.60 | same | −12.3 | — |

## Verdict: DEAD

- No implementable variant clears the bar. AM3 (the best realistic buy) is +0.96pp in 2021-23 but
  **+0.15pp in 2024-26** and NW t 1.74 < 2. AM1/AM2 flip sign by half.
- The **"adverse selection" is actually favourable** (+33..41bp): names that dipped to the limit
  bounced *more*, which is why the limit helps at all — but the fill loss (16-29% skipped, capital
  redeployed) eats the gain in 2024-26.
- The sell side loses outright: a limit-on-open with a floor (AM5) is −1.58pp in 2024-26, and
  resting for one tick (AM6) is −1.5/−2.6pp with t −12.
- The AM4 upper bound (+7.6/+8.7pp) buys at the 15:50-15:59 low, which is only known after the fact;
  it is not implementable and confirms only that the ceiling is real but unreachable without quotes.
  Addendum 13's ~+2pp bound was optimistic: implementable limits deliver **well under +1pp** and only
  in one half.
- $/yr: +$10 at $2.3k, +$110 at $25k for AM3 (pre-tax); negative in 2024-26. Not worth live code.

## What would change it

A per-name quoted spread at 15:40-15:55 (Schwab L1 / ThetaData) to place the limit at the true bid,
and a maker-rebate venue. Without quotes this is a trade-path approximation.
