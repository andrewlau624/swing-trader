# Study AJ — the conviction trade in MNQ instead of TQQQ: SHADOW (AJ1 w 0.5, AJ2 w 0.75); AJ3 dead (N 634 -> 637)

Stamp: `round1_prose.md` Round 16 AJ (commit 75e2e61). Script: `research/sim/conviction_aj.py` (~10 s).
Output: `data/research/program/conviction_aj_out.txt`. Brief idea #6.

## Setup
- Signal and minutes are the shipped trade's. MNQ is modelled as 3 × QQQ's move (QQQ stands in for NQ, as in futures.py).
- Tracking on the same 785 trades: TQQQ +21.3bp vs 3×QQQ +21.6bp gross, corr 0.999, so the instrument does not
  change the trade.
- Margin: futures taken at 10% of notional (0.30 of equity per unit w), against TQQQ's 0.75.
  - At mult 2 the noise cap at w 0.5 rises from 0.75 (TQQQ) to 1.20 (MNQ).
- Costs per side: 0.5bp (shipped) / 1.0bp (stressed). Commissions of ~$2.25/contract ≈ 0.5bp on a $43k contract.
- Tax: MNQ is Section 1256 (60/40, blended 26% vs 35%), with no wash sales against the Roth's TQQQ/SQQQ.

## Results (stressed costs, mult 2; increment vs the shipped w 0.5 TQQQ)
| variant | 2016-20 | 2021-23 | 2024-26 | NW t | placebo | of which noise-cap relief | B3 maxDD (base −21.3) | P(DD>50%) (base 1.7%) | P(DD>30%) (33%) | DSR (N 637) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| AJ1 w 0.5 MNQ | +3.3pp | +4.1 | +2.5 | 4.3 | 100 | +1.7pp | −21.7 | 2.0% | 37% | 0.79 | **SHADOW** |
| AJ2 w 0.75 MNQ | +5.1 | +9.9 | +5.3 | 4.1 | 100 | +1.3 | −22.1 | 3.5% | 46% | 0.78 | **SHADOW** |
| AJ3 w 1.0 MNQ | +6.6 | +15.6 | +8.0 | 3.6 | 100 | +0.7 | −22.8 | **5.8%** | 56% | 0.63 | dead (DD bound) |

- At mult 4 (Schwab intraday, add. 40 shadow): AJ1 +1.9 / +1.4pp (2016-23 / 2024-26), t 3.1; AJ2 +5.7 / +4.6pp,
  P(DD>50%) 5.1%, just over the bound.
- **Why it works:**
  - The same trade in a cheaper wrapper: ~3bp/side on 0.5E becomes ~1bp.
  - It stops competing with the noise leg for TQQQ's 75% margin.
  - It gets 60/40 tax.
  - The high t reflects that: the increment is mostly a structural saving on identical trades, not a new signal.
    AJ2's extra 0.25 of weight is an ordinary size-up, and its extra drawdown (P(DD>30%) 33 → 46%) is the price.

## Money (tier_hi, mult 2, whole contracts; 2016-26 mean, 2024-26 in brackets; after tax 60/40 on MNQ, 35% on the rest)
| | $2.3k | $25k | $100k | $500k |
|---|---|---|---|---|
| AJ1 | n/a: 0 contracts, keep TQQQ | ~0: w_eff 0.12, keep TQQQ | +$2.7k (+2.0k), AT +$2.3k | +$15.9k (+11.5k), AT +$13.6k |
| AJ2 | n/a | +$0.7k (−0.4k): 1 contract some days | +$5.6k (+4.0k), AT +$4.6k | +$31.5k (+24.7k), AT +$25.3k |

- **Whole contracts:** one MNQ ≈ $43k notional (2024-26), so the trade needs equity ≥ ~$29k at w 0.5, or ~$19k at
  w 0.75. Below that, keep TQQQ.
- **Capacity:** at w 1.0 the trade is 2 / 7 / 35 contracts at $25k / $100k / $500k. MNQ trades ~1-2M contracts a day
  (not measured here: the repo has no futures volume data), so this is no constraint to several $M.

## Blockers (why SHADOW and not adopt)
1. **Schwab's Trader API cannot place futures orders.** Only equities, ETFs and options can be ordered; futures return
   an error. Third-party docs and client libraries agree; the official docs sit behind a login and were not
   checked here.
   - MNQ needs a second broker with a futures API (e.g. IBKR) and a separate account.
   - This also affects every earlier "MNQ past ~$160k" plan in scale_plan.md / Study Y / Round 14.
2. **Parked cash: not simulated.** A separate futures account needs cash parked there: intraday margin plus a buffer
   for the worst trade (−4% of equity at w 0.5), ~5-10% of equity.
   - The sim charges margin as a cut in Schwab's noise cap instead.
   - With a second broker the cost shows up as a ~5-10% smaller Schwab book, or ~5-10% overnight margin at ~8-12%.
   - Estimated haircut: −0.5 to −1.5pp/yr, which leaves AJ1 at ~+1..+2pp in 2024-26.
3. **No live evidence yet.** The TQQQ conviction trade itself has 0 live round trips; add. 19's 60-trade kill rule
   has not started.

## Switch (spec only, NOT built, default off)
- `daily.conviction_instrument: tqqq | mnq` (default tqqq), with `conviction_w` unchanged at 0.5 (AJ1). AJ2's 0.75
  is a later step, only after AJ1's gates hold.
- **Gates**, all required:
  - (a) the TQQQ conviction trade is on (`conviction_mode: auto`) and has ≥ 30 live round trips without firing its kill rule;
  - (b) taxable equity ≥ $30k;
  - (c) a futures-capable API broker account is open and funded with ≥ 10% of equity;
  - (d) a shadow run logs `[conv-mnq]` decisions beside the TQQQ trade for 20 sessions, with fill slippage ≤ 2bp/side.
- **Kill:** revert to tqqq if realised MNQ slippage exceeds 2bp/side over 30 fills. The existing conviction kill rule
  (60 round trips) applies to both instruments.

## Also asked in idea #6, not tested
- **QQQ on margin instead of TQQQ.** Maintenance per unit of exposure is the same (25% × 3 = 75%), so there is no
  margin relief. Only the cost changes: ~0.2bp·E vs ~0.75bp·E per side at w 0.5, about +0.8pp/yr.
  - It needs a short QQQ in taxable, which nets against the noise leg's own QQQ position.
  - Not pre-registered, not run.
- **0DTE QQQ/SPX options.** The repo has no options history.
  - ThetaData's retail options plans are $40 / $80 / $160 a month. Standard ($80) has tick-level NBBO and ~8-10 years.
  - Pricing a 0DTE version of the trade needs the $80 plan for one month of download.
  - Schwab's API can trade options, so this route, unlike MNQ, would run on the existing broker.
