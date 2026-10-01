# Study Lab-AS — gap + premarket volume, pullback to VWAP, reclaim: DEAD (N 669 -> 670)

Stamp: `round1_prose.md` Lab Round 18 (commit b9ff156); plan `daytrade/plans/gap_vwap_reclaim.md`.
Script: `daytrade/research/as_replay.py` (the lab's own strategy code and engine; SIP minutes).
Output: `data/daytrade/research/as/results.json`, `trades_1x_1s.csv` (not in git).

## Data
- 1,190 regular sessions, 2022-01-03 to 2026-09-30. Halves: 606 sessions (H1, to 2024-05-31) and 584 (H2).
- 6,506 common stocks, active and inactive.
- 3,308 trades in 782 names, 2.8 trades/day.
- The engine and an independent per-trade simulator agree to 0.04bp mean abs (300 trades).

## Result (registered test, 1s latency = the next minute's open)
| cost / latency | all: n, net bp/trade (median), win %, t (day-clustered) | H1 net bp (t) | H2 net bp (t) |
|---|---|---|---|
| **1x (10bp/side), 1s** | 3,308, **−18.9** (−126), 35%, **t −3.2** | −11.7 (−1.3) | −24.3 (−3.1) |
| **2x (20bp/side), 1s** | −36.1, t −6.0 | **−28.8** | **−41.5** |
| 1x, 0s | −19.6, t −3.3 | −12.5 | −24.9 |
| 1x, 60s | −23.4, t −4.1 | −15.9 | −29.0 |

- **Placebo** (random entry minute 09:36-11:30, same symbol-days, same % stop and 2R target, 1,000 draws):
  mean −19.9bp. The rule is at the **59th percentile**: indistinguishable from entering at random.
- **Gross before costs: −1.7bp/trade.** The pattern has no edge. The loss is the spread and slippage of
  ~2.8 round trips a day.
- **Exits.** Stop 60% (−232bp avg), target 27% (+411bp), flat by 15:55 13% (+64bp). The mean R is
  −0.11 (1x).
- Latency hardly matters (0s vs 1s is 0.7bp; 60s costs another 4.5bp). Speed is not the problem; the
  entry has no information.

## Pass bar: fails every part
2x net > 0 in both halves: no (−29 / −42). t ≥ 2 at 1x: no (−3.2). Placebo ≥ 95th pct: no (59th).
**DEAD.** No re-tuning (plan): X, Y, the cutoff, R and the target stay frozen. Any variant is a new
pre-registration with its own N.

## Money (through the lab's risk layer: 0.5% risk per trade, 2% daily loss limit, 3 positions, cash T+1)
| account | 1x: $/day | 1x: end of 4.7 yrs | 2x: $/day | 2x: end |
|---|---|---|---|---|
| $2.3k cash | −$1.46 | $2,300 -> $568 (−26%/yr) | −$1.77 | -> $199 |
| $2.3k margin | −$1.51 | -> $508 | −$1.79 | -> $165 |
| $10k margin | −$7.19 | -> $1,442 (−34%/yr) | −$8.12 | -> $341 |
| $25k margin | −$18.23 | -> $3,309 (−35%/yr) | −$20.41 | -> $713 |

Capacity is irrelevant: it loses at every size. At $100k / $500k it would lose ~−$73 / −$365 a day,
scaled.

## Reading
- This is the popular retail pattern written down without discretion. It behaves like the population
  studies in the lab README: it has no gross edge, so costs make it a steady loser.
- It agrees with AE (nothing at the open predicts direction) and add. 41 (single-stock intraday momentum
  has no edge after costs).
- The selection (gap ≥ 4%, premarket ≥ 250k) finds loud names. On loud names a VWAP test followed by a
  reclaim is a coin flip with a wide spread.
