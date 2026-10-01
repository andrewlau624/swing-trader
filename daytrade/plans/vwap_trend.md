# Plan: vwap_trend (Study AW)

Written 2026-10-01, before any data for it was fetched. Code: `daytrade/strategies/vwap_trend.py`.
Pre-registration: `research/drafts/round1_prose.md`, Round 21, Study AW (2 variants, N 674 -> 676).

## Source
Zarattini & Aziz, "Volume Weighted Average Price (VWAP) The Holy Grail for Day Trading Systems", SSRN 4631351
(2023, rev. 2025). QQQ 2018-01 to 2023-09: +671%, Sharpe 2.1, max DD 9.4%. TQQQ: +8,242%. Costs are commissions
only. The authors say it is not a finished system.

## Why it could work, and why it might not
- Could: intraday time-series momentum in the index (the same family as the live noise leg, which this repo
  measured at ~+2bp/day). Volume-weighted price is where the day's flow sits; being on its side rides
  trend days.
- Might not: it is the noise leg without the band, so it whipsaws on quiet days. Add. 22 found faster
  cadences dead for the noise leg. QQQ costs ~0.1-0.5bp/side, so the switches must earn more than that.
- Checked: RESULTS.md and NEXT.md have no VWAP-trend study (VWAP is only the noise leg's exit).

## Exact rules (regular session from the calendar; SIP minute bars)
- Signal instrument: QQQ. Session VWAP from 09:30 = cumulative (h+l+c)/3 x volume / cumulative volume.
- At each 1-minute close from 09:31 (the 09:30 bar) through the entry cutoff: desired side = long if the
  close > VWAP, short if < VWAP (equal: keep the current side).
- When the desired side differs from the held side: exit and reverse, market, at the next minute's open
  (the 1s latency). Flat by 15:55 (the lab's rule; the paper holds to 16:00).
- Protective catastrophe stop 2% from each entry (engine-managed); size from it.
- Variants: AW1 trades QQQ; AW2 trades TQQQ on QQQ's signal.

## Costs
- QQQ 0.5bp/side (1x), 1.0bp (2x).
- TQQQ 1.5bp/side (1x), 3.0bp (2x).

## Replay (Study AW)
- SIP minute bars 2022-01-03 .. 2026-09-30, halves split at 2024-06-01 (H2 is out of sample for the paper).
- The unit is the DAY: the day's summed net bp on a constant notional. t = day-level.
- Placebo: each holding segment's direction flipped at random (same switch times and costs), 1,000 draws.
- Also report the overlap with the live noise leg: the correlation of daily P&L.

## Pass bar, per variant
Mean net per day > 0 at 2x in BOTH halves, AND t >= 2.0 at 1x, AND >= 95th pct of the placebo.

## Drop condition
Fails: dead, nothing re-tuned (no bands, no filters; those are the noise leg).
Paper: drop after 40 sessions if the mean net/day <= 0 or the drift exceeds the replay edge.
