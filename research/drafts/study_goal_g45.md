# Study G45: activist 13D on a closed-end fund: PASSES its registered bars, NEAR at the Goal book level

Goal hunt, session llm-trader-ec, idea G45 (`goal_ideas.md`). Pre-registered `round1_prose.md` (cd548ad, N 783) before any
price around these filings was looked at. Runner `research/sim/goal_g45.py` (build / select / judge, one look each).
Per-trade lists: `data/research/program/goal_g45_{judge,holdout}.csv`. k = 34.

**Rule.** Event: the first SC 13D / SCHEDULE 13D by Saba, Karpus, Bulldog, City of London, 1607 or Almitas on a fund-like
listed subject. 156 originals, 151 with bars: Saba 116, Bulldog 16, Karpus 12, City of London 7. Trade: buy the next
session's open, hold 60 sessions. Return is dividend-adjusted, minus PCEF (dividend-adjusted), net of tier costs.

| half | n | mean vs PCEF | median | hit | date-level t | ex best 5 trades | worst |
|---|---|---|---|---|---|---|---|
| select 2021-23 | 60 | **+2.55%** | +1.25% | 57% | **2.48** | — | −8.6% |
| judge 2024-26 | 40 | **+3.57%** | +1.36% | **75%** | **2.67** | **+1.25%** | −8.0% (GF) |
| holdout 2016-20 | 51 | **+2.01%** | +1.40% | 69% | 1.74 | +1.00% | −13.3% (AEF) |

By year (judge): 2024 +1.1% (30 trades), 2025 +7.1% (8), 2026 +27.1% (2: small n).
By year (holdout): 2016 +1.3%, 2017 +4.3%, **2018 −6.2% (4)**, 2019 +2.5%, 2020 +1.3%.
**Every registered study bar passes:** select gate, judge mean > 0 with t >= 2, the lottery test, and holdout >= 0.

**Mechanism.** The activist forces the board to narrow the discount: tender offers at 98-99% of NAV, liquidations, open-ending.
The remaining holders get a NAV-linked payoff. The excess over the CEF index is the discount closing.

## Goal book level (the bar this misses)
Sleeve: 12.5% of equity per open position (max 8 at full weight, scaled down above that), funded from the SPY core.
| half | mean open | sleeve gross | vs SPY | vs PCEF (hedged) |
|---|---|---|---|---|
| judge 2024-26 | 3.5 (max 15) | 39% | **+3.4%/yr** (NW t 1.0; 2024 −3.1, 2025 +6.7, 2026 +5.7) | +6.0%/yr |
| select 2021-23 | 4.2 | 39% | +1.0%/yr | +5.9%/yr |
| holdout 2016-20 | 2.4 | 29% | +0.4%/yr | +2.3%/yr |

Long-only from SPY, the sleeve inherits CEF-vs-SPY beta (CEFs lagged SPY in 2023-24), so the event alpha is mostly
eaten. Hedged (long the fund, short PCEF, taxable only) it is ~+6%/yr pre-tax at 39% gross, ~+3.9pp after tax: still below
the +5pp add-on bar.

## Verdict: NEAR (missed: the Goal add-on bar, +3.4pp vs SPY / ~+3.9pp hedged after tax, needs +5pp)
The event effect is real and consistent across three periods (+2-3.6% per 60-day trade vs the CEF index). It is the first
new mechanism in this hunt to pass its own registered test. It is too small at the book level because ~30 events a year at
12.5% each only keep ~35% of the account in the trade.

**The one NEAR follow-up, G45-F (registered in round1_prose.md with this write-up):** forward only. A log-only watcher records
each new activist 13D on a CEF and scores it at 60 sessions. After 30 forward events: PASS iff mean excess vs PCEF >= +1.5%
and the hedged sleeve (taxable: long fund, short PCEF at equal dollars, 12.5% per position) >= +5pp/yr after tax on those
events; otherwise DEAD. No re-run of history with new sizing.
