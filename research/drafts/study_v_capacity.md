# Study V — night-leg capacity: the leg is a small-account strategy (report, N 611)

Stamp: `round1_prose.md` Round 9 (commit 9673e20). Script: `research/sim/night_capacity.py`.
Outputs: `data/research/program/night_capacity_out.txt` (as stamped),
`night_capacity_diag.txt` (bracket, NOT pre-registered).

## Inputs
- Weighted gross +24.6bp/trade (book weights). Live cost ~0-1bp/side at $2.3k (n 34).
- Auction depth, median across picks: closing bar $1.7M (3.7% of ADV), opening bar $0.74M
  (1.6% of ADV). The exit (open) is the thinner side. Pick ADV median $43M, floor $10M.

## The stamped model is rejected at its own calibration point
Participation vs the 1-minute bar with a mean over picks: 22-44bp round-trip impact at $2.3k,
while live fills measure ~0bp. A few near-empty bars dominate the mean. Kept on file, not used.

## Bracket (square-root law, 1bp/side live cost), night-leg $/yr
| equity | A: sqrt(Q/ADV), Y .5 | A, Y 1 | B: sqrt(Q/auction share of ADV), Y .5 | B, Y 1 |
|---|---|---|---|---|
| $2,300 | $290 | $270 | $179 | $49 |
| $25,000 | $2,652 | $1,939 | −$1,303 | −$5,970 |
| $100,000 | $7,757 | $2,057 | −$23,878 | −$61,213 |
| $250,000 | **$11,111 (peak)** | −$11,417 | − | − |
| $500,000 | $3,560 | −$60,160 | − | − |
| $1,000,000 | −$45,667 | − | − | − |

A is the textbook calibration (order spread over the day) and is OPTIMISTIC for an order that
must clear in one auction; B treats the auction as the only liquidity and is pessimistic (at
$2.3k B/Y=1 predicts ~9.5bp/side, above the live open-sell 95% UB of 8.5bp). Truth: between.

## What it means for the plan (CLAUDE.md: large sums are coming)
1. **Cap the night leg in dollars, not as a share of equity.** Best case its income peaks near
   $250k of equity (~$60k in the leg at 0.5 x w); realistic cases peak far lower. As capital
   grows, route new money to the scalable legs (IBS sector ETFs, QQQ/SMH noise, MNQ past ~$200k).
   The cap is shared: taxable + Roth night legs hit the same auctions.
2. **Measure impact while small.** The live bot can learn Y cheaply: log each night order's
   participation (shares / official auction volume, both auctions) beside the fill-vs-official
   gap already in `make review` §4. At $2.3k, p ~1e-4 carries no signal; from ~$25k (p ~1e-3)
   it starts to. Fit Y before the leg's dollar cap is set.
3. **Untested levers that could raise the cap** (each its own study): split the open exit into
   the auction + the first N minutes (the open bar is the thin side); limit-on-close/open
   prices; drop picks with the thinnest auctions when the order would exceed x% of them.
