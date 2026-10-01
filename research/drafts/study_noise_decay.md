# Noise leg after publication (Round 21 report, no N) — SPY decayed, QQQ about halved, SMH intact

Script `research/sim/noise_decay.py`; output `data/research/program/noise_decay_out.txt`. Outside prompt: the
codecat-ops replication of Zarattini-Aziz-Barbon (SSRN, May 2024) finds SPY Sharpe ~0 since 2025.
Unlevered rule, net 0.5bp/side.

| | before (2016 – 2024-05) | after (2024-06 – 2026-09, 577 days) | 2025+ | by-year trend |
|---|---|---|---|---|
| QQQ | +4.10bp/day, Sharpe 1.25, t 4.2 | **+2.48bp/day, Sharpe 0.71, t 1.1** | +2.14, Sharpe 0.58 | flat (t 0.0) |
| SMH | +3.79bp/day, Sharpe 0.89, t 2.7 | +5.13bp/day, Sharpe 0.95, t 1.6 | +3.82, Sharpe 0.72 | flat (t 0.3) |
| SPY (not traded) | +1.99bp/day, Sharpe 0.73 | **−0.86bp/day, Sharpe −0.37** | −1.45 | — |

- **The replication's SPY decay shows up here too**, so that finding is confirmed on our data.
- **QQQ is down ~40%** after publication, about McLean-Pontiff's post-publication haircut (−58% on average).
  It is still positive, but 577 days cannot tell decay from noise (QQQ by year: 2.9 / 2.5 / 1.7bp/day for
  2024 / 2025 / 2026).
- **SMH has not decayed**, which supports keeping the QQQ/SMH split.
- **Action: none.** Add. 37 rejected automatic de-risking, and the noise kill rule (120 trades, t < −1) stays.
  For planning, use QQQ at ~2.5bp/day, not 4.
