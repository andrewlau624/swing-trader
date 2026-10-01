# Study Lab-BD — QQQ early closing imbalance every day: DEAD on the H2 holdout (program N 711 -> 712)

Stamp: round1_prose.md Lab Round 28 (commit 7b7283f). Script `daytrade/research/bd_replay.py`. Designed on H1 (QQQ
quintiles of r = signed imbalance / paired at 15:54:30: −2.4 / +1.9 / +1.8 / +4.1bp, mid -> close). Rule: long
r >= 0.2585, short r <= −0.2824 (the H1 quintile edges); NBBO at 15:54:31 -> official close.

| | trades / days | gross | 1x net (t) | 2x | without top 20 | placebo | by year (1x) |
|---|---|---|---|---|---|---|---|
| **H2 holdout (judged)** | 247 / 584 | +1.3bp | +0.17 (t 0.2) | −1.0 | −2.3 | 93 | 2024 +0.05, 2025 +0.08, 2026 +0.43 |
| H1 (in-sample) | 243 / 606 | +3.2bp | +2.1 (t 2.3) | +0.9 | −0.5 | 100 | 2022 +1.4, 2023 +1.3, 2024 +4.4 |

**DEAD.** QQQ's spread is tiny (0.27bp), but the H2 gross shrinks to 1.3bp, below the 1bp in fees and slippage plus
half-spread. Closing-imbalance family closed: the signal exists in single stocks (Lab-BC, +6bp) but costs as much,
and in QQQ it is too small since mid-2024.
