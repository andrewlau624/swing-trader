# Overnight 2026-10-01: what got built, tested and learned (read this first)

## The one number that matters
**The next switch, `moderate10c` (conviction trade + 15% night name cap), is the biggest lever left.**
Simulated alone at today's 2.48x margin, on official-cross night returns:

| | live today | moderate10c | change |
|---|---|---|---|
| $2.3k, 2.5bp/side | 37.6%/yr, maxDD −13% | **54.0%/yr**, maxDD −17% | **+16.4pp** |
| $10k, 2.5bp/side | 39.4% | 55.4% | +16.0pp |
| $10k, tier_hi | 22.3% | 31.5% | +9.2pp |

It adds in both halves (2021-23 / 2024-26) at both costs. Gate: ~5 clean intraday days (`make review` §7; the
digest's "Next step"). Switch: `DAILY_LIVE_PROFILE=moderate10c` in `.env`.

## Everything on, as one simulation (study_everything_on.md)
At 2.5bp/side, live today 39% → + tug-of-war 43 → + 15% cap 51 → + conviction 60 → + 4x intraday 65 →
+ 1.3x overnight **77%** (Sharpe 2.2, maxDD −21%, 5y P(DD>50%) 0%). At tier_hi: 22 → 42%.
With the program's edge-halves haircut: 17.8 → 31.1%. The night-leg levers (15% cap, 1.3x) are cost-sensitive:
turn them on only after live night costs confirm ≤ ~3bp/side.

## The weekly digest's numbers were corrected
- **Plan lines** = edge-halves from that simulation:
  - brokerage 17.8% (as is) → 31.1% (all on);
  - Roth 10.0% → 14.5%. The Roth was 15%, a guess that was too high.
- **Backtest lines** = the simulation itself. They had been a sum of separate estimates, which came out too low.
- All lines shrink with balance (Study Y) and include $1k/month (brokerage) and $625/month (Roth).
- The index fund is taxed fairly, and the comparison runs in two market scenarios.

## Tested with the Databento data (~$16 of the shared $125 credit; the lab used ~$92)
- **BD, closing-auction imbalance on night picks: DEAD.** The patterns flip between halves. The filter only
  removes exposure.
- **BE, skip IBS entries indicated to gap up at 09:28: DEAD.** Gap-up entries actually earn more.
The closing-imbalance idea that had been parked since Round 13 is now settled with real exchange data.

## Earlier today
- **AU3 tug-of-war tilt:** built, OFF, logging.
- **LLM news judge** (OpenCode Go deepseek-v4-flash): live, shadow, forward test to 300 picks.
- **15:40 quote-imbalance logging:** forward test.
- **Weekly digest email:** redesigned, with backtest and plan pace.
- **Auction-print audit:** the night leg is ~2pp/yr lower on official prices.

## What to do this morning
1. `make pull` on the server.
2. Optionally `make weekly-send`, to see the corrected digest.
3. When the digest says **Ready: Conviction trade on**, add `DAILY_LIVE_PROFILE=moderate10c` to `.env`.
4. Rotate the Databento key in its portal. It was pasted in chat; it is stored only in the Mac's `.env`.
