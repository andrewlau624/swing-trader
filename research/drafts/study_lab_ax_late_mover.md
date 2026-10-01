# Study Lab-AX — +25% movers at 15:00, held to 15:55, long only: DEAD (lab N +1; program N 697 total)

Stamp: `round1_prose.md` Lab Round 22 (commit a971435); plan `daytrade/plans/late_mover.md`.
Script: `daytrade/research/ax_replay.py` (the lab's `LateMover` code through the engine; SIP minutes, 2022-01 to 2026-09).

| | n | net bp/trade | median | win | t (day) |
|---|---|---|---|---|---|
| 1x (20bp/side), all | 2,373 | **−33.7** | −43.6 | 42% | −2.63 |
| 1x H1 / H2 | 822 / 1,551 | +3.9 / **−53.6** | | | +0.16 / −3.63 |
| 2x H1 / H2 | | **−35.7 / −93.2** | | | |
| 1x, 60s latency | | −35.7 | | | |

- Gross +6.3bp/trade: no late-day continuation worth the spread.
- **Placebo 0th percentile.** A random 55 minutes earlier in the day on the same names averages +148bp net. That is
  look-ahead (the names were selected for being +25% by 15:00), and it says the run-up is over by 15:00.
- Losers' mirror (diagnostic, <= −25% at 15:00): −34.6bp gross from 15:00 to 15:55 (n 2,226). Real but much smaller
  than the RESULTS.md table's ~−1.5% (that study's window and definition differ).
- $/day (lab limits, 1x): −$0.49 / −$1.92 / −$4.90 at $2.3k cash / $10k / $25k.

**DEAD** (2x negative in both halves; t negative; placebo 0th). Nothing re-tuned.
