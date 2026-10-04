# Goal L1 / L2: concentration and leverage on the proven legs only — DEAD (all three registered variants)

Pre-registered `round1_prose.md` (db80f87, N 788 -> 791) before any outcome. Runner `research/sim/goal_l.py`
(`PYTHONPATH=. .venv/bin/python -m research.sim.goal_l`, ~3 s on the cached raw sim). Book = IBS ETF leg + night leg
only (noise/conviction off: no holdout). Night tier_hi, IBS 3bp/side, margin 12.5%/yr on the overnight debit (Schwab
small-balance rate assumed; SCHWAB.md has none), idle cash in BIL, 30% tax on each year's net gain paid Dec 31.
Margin only at equity >= $2,000; L2 stop: -15% from peak -> B0 until a new peak.

Cited, not redone: add. 22/29 (leverage profiles), add. 24 D (night top-1 at 100%: dead, Kelly), add. 32 (frontier knee
1.3x), add. 39 (raw pool; T0L live-today book 23.7% pre-tax at tier_hi, most of it the noise leg), index-beat stack.

## Kelly (2016-20 holdout, 1.0x book)
mu 2.23bp/day, sigma 0.50%/day: f* = mu/sigma^2 = 8.8x, half-Kelly 4.4x (not binding; Reg T 2x binds first).
Net of the 12.5% borrow rate f* is negative (-10.8x): the book's average day earns less than a day of margin interest.
Per leg: IBS f* 7.2 (2016-20), 6.0 (2021-26). **Night leg f* -0.2 in the 2020 holdout and -0.2 in 2021-26 at tier_hi**:
at tier_hi costs Kelly says no night leg at all, let alone a levered one. (At 3bp/side the night leg is +24.8%/yr alone.)

## Judge: 2016-20 holdout (returns engine, after interest + tax; L1 on 2020 only)
| variant | CAGR | maxDD | worst month | COVID | 2020 |
|---|---|---|---|---|---|
| B0 0.5/0.5 | 3.9 | -13.8 | -6.2 | -3.0 | 16.0 |
| L1 spill to 1.0x | 3.7 | -22.9 | -12.1 | -5.5 | 16.6 (+0.6 vs B0; needs +2) |
| L2a 1.5x | 3.8 | -19.0 | -9.3 | -6.5 | 15.6 |
| L2b 2.0x | 2.2 | -16.3 | -11.4 | -3.0 | 14.1 |
Same at $2.3k and $10k. Before 2020 the night half is in bills, so the holdout is mostly the IBS leg (mean gross 0.16).

## 2021-26 shipped simulator, whole shares, tier_hi, after interest + tax (descriptive)
| variant | $2.3k CAGR / maxDD / wm | $10k | $25k | 2021-23 / 2024-26 at $10k |
|---|---|---|---|---|
| B0 | 6.1 / -14.0 / -8.0 | 5.0 / -15.4 / -9.0 | 5.0 / -15.4 / -9.2 | 2.0 / 8.5 |
| L1 | 5.0 / -25.8 / -9.9 | 4.1 / -25.9 / -9.8 | 4.1 / -26.3 / -9.9 | 0.0 / 8.7 |
| L2a 1.5x | 6.4 / -19.1 / -12.9 | 5.1 / -20.5 / -12.5 | 4.8 / -20.6 / -12.8 | 0.5 / 10.3 |
| L2b 2.0x | 6.3 / -23.3 / -15.5 | 3.1 / -23.7 / -12.1 | 2.7 / -24.0 / -12.3 | -3.9 / 11.2 |

## Ruin, 3-yr 21-day block bootstrap of 2016-26, edge-halves, 2000 paths
P(equity < 50% of start): B0 0.0%, L1 1.1%, L2a 0.0%, L2b 0.1% (2020-26 pool: 0.1 / 2.8 / 0.2 / 0.4%). P(< $2,000) from
$2.3k: 31 / 63 / 45 / 51% (0% from $10k/$25k): at today's balance the floor switches margin off on most paths anyway.

## Verdict: DEAD, all three (L1, L2a, L2b)
None beats B0 by 2pp on the holdout; L1 and L2 also fail 2021-23 at $10k. Not a blowup risk (ruin <= 3%, Reg T caps it),
just a loss: leverage multiplies a night leg that is ~0 at tier_hi and pays 12.5% on the debit. The stop whipsaws:
without it the holdout L2b is 6.5% (-27% DD) — post-hoc, not a rescue.

Where leverage bites: single nights, not trends. Worst unit night-leg nights: 2020-06-10 -13.4%, 2026-04-27 -12.5%,
2023-08-23 -11.6%, 2020-03-11 -9.6%. At 2x the night leg is 1.0 of equity, so one such gap is -12..-14% of the account
overnight, past any stop (worst day L2b -14.2% in 2021-26). Weekend nights are already half-sized and average -12.7bp
(weekday +2.6bp). COVID Feb-Apr 2020 trough: B0 -12.9%, 1.5x -17.7%, 2x -21.2% (stop hit). Schwab house requirements
on 60%+-vol night names are often above Reg T's 25-30%; at 2x a -13% night leaves equity at 42% of positions.

## Post-hoc rows (not judged; next registration at most)
- Night cost 3bp/side (live measured ~0bp): 2021-26 $10k B0 15.4, L1 22.1, L2a 19.3, L2b 21.0, IBS-only 1.5x 16.9; holdout
  B0 4.7, L1 5.1, L2a 5.2, L2b 3.5. Leverage pays in-sample only if live night costs stay near 0, which is what the
  existing `lever_weight: 0.65` re-arm rule (~100 live night trades) already waits for.
- IBS-only leverage (ibs 0.75 / night 0.5), tier_hi: holdout 5.6 (+1.7 vs B0), 2021-26 7.2 / 5.8 / 5.6 at $2.3k/$10k/$25k
  (+1.1 / +0.8 / +0.6), maxDD -15..-17, P(<50%) 0.0%. The one leg with a holdout; below the +2pp bar and post-hoc.

Options overlay: no option-chain history in the repo (NEXT.md, Study AR): not testable.
