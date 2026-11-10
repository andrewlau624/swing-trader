# RGTI-BASKET (N 1190-1195): swing rules on RGTI-like baskets - KILL all six (2026-11-09)

User idea: trade stocks that swing like RGTI. Study CC (N 820, RGTI alone) fixed by a basket over 1999-2026 (Sharadar, delisted).
- Memberships: M1 top-decile 120d vol + VR5 <= 1 (monthly); M2 range-bound vs own history (20d range <= 0.6x 120d range,
  >= 2 touches of each band; user's definition, pre-registered before any outcome). RGTI is M2, not M1 (2026-10-05).
- Rules R1 20d-low then +8% day (15% target / 10% stop / 10d), R2 close in bottom 10% of 20d band -> exit at mid or 15d,
  R3 above SMA50 with 12% 5-day pullback, 10d. Judge 2013-26; control = same-date vol-matched random member, same exit.
- Every cell fails the control or the ceiling. Best: M2R2 +40bp/trade over control (t 3.45, both halves, same size 1999-2012,
  DSR .97) but alpha vs QQQ -34bp, ceiling +4pp/yr, K=5 sim 11.5%/yr vs QQQ 20%. Relative-only (needs a short leg).
- M1R1 (the RGTI bounce shape) is worst in 2024-25 (ex -117bp): Study CC's regime did not generalise.
- Not tested: R4 state machine, parameter variants, hedged/long-short M2R2, intraday entries, retail-attention filter.
Files: research/sim/rgti_basket.py, data/research/program/rgti_basket_out.txt, rgti_basket_today_out.txt.
