# Study Lab-AW — VWAP trend on QQQ / TQQQ (Zarattini & Aziz 2023): DEAD (N 674 -> 676)

Stamp: `round1_prose.md` Lab Round 21 (commit 236a3f4); plan `daytrade/plans/vwap_trend.md`.
Script: `daytrade/research/aw_replay.py` (the lab's `VwapTrend` code through the lab's engine). 1,190 sessions,
2022-01 to 2026-09, SIP minutes.

## Result (unit = day; bp on a constant notional)
| variant | switches/day | gross bp/day | 1x net (t) | 1x H1 / H2 | 2x H1 / H2 | placebo pct |
|---|---|---|---|---|---|---|
| Lab-AW1 QQQ (0.5bp/side) | 16.0 | **+6.7** | **−9.3** (t −2.7) | −5.8 / −12.9 | −21.9 / −28.9 | **97.1** |
| Lab-AW2 TQQQ on QQQ's signal (1.5bp/side) | 16.0 | +20.5 | −27.7 (t −2.7) | −18.4 / −37.3 | −66.6 / −85.3 | 97.5 |

$/day at the whole equity, 1x: Lab-AW1 −$0.21 / −$5.87 / −$14.63 at $2.3k / $10k / $25k; Lab-AW2 +$0.15 / −$7.34 /
−$19.33 (the $2.3k numbers are whole-share noise).

## Reading
- **The signal is real; the trading is not.** Being on VWAP's side beats a random side on the same switch
  times (placebo 97th pct) and grosses +6.7bp a day on QQQ. Sixteen switches a day at even 0.5bp a side
  cost 16bp a day, more than twice the gross.
- The paper's 671% needs near-zero costs.
- Cutting the switching is exactly what the live noise leg's band does: the same edge, already traded.
- Fails the pass bar (2x negative in both halves; t negative). **DEAD**, no re-tuning: a band variant is
  the noise leg.
