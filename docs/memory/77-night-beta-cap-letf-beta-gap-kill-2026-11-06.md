# NIGHT-BETA-CAP (N 1108-1110, 2026-11-06): cap / drop high-beta night picks — KILL; and why live beta looked 5x the backtest

## Step 1: the "live 2.45 vs backtest 0.49" beta gap is mostly a units mismatch, then universe drift, then regime
- (c) units: BETA-HEDGE's backtest 0.49 is ACCOUNT-level (sum account-weight x beta; sleeve gross ~0.4-0.7). The live 2.45 is per
  deployed notional. Like-for-like backtest position beta (60d QQQ, clip 4): mean 0.91/0.78/0.68/0.79/0.84/0.97 for 2021..2026,
  median 1.04 -> 1.33 (2026). No sim bug in the beta itself (3.8% of picks lack 60 obs).
- (a) universe: the backtest DOES include the single-stock 2x ETFs (AAOX, ORCX, IONX, MRVU, DLLL are in night_trades.v2 from listing).
  LETF notional 7% (2021) -> 33% (2026); LETF median beta 0.3-0.4 (2021/2024, inverse/commodity) -> 3.2-3.5 (2025-26, single-stock longs).
- (b) regime/sample: live (17 sessions, 2026-09-23..11-05) LETF 57% of notional, stock picks beta 2.05 (backtest 2025-10..2026-09:
  35%, 1.37); notional with beta > 2 = 72% live vs 37% backtest. Residual ~1.8x gap = more LETFs + elevated 60d stock betas now.
## Step 2 (pre-registered; judge = none clean, in-sample 2021-26 gates both halves)
- CAP (N 1108, scale leg so notional beta <= 1.0, binds 52% of nights): 32.3%/yr maxDD -16.3 MAR 1.98 vs uncapped 45.9%/-20.6/2.23.
  MAR 1.00x (2021-23) / 0.80x (2024-26): G1 fails both halves. Levered back to -20.6 DD: 40.8% < 45.9. Diff -4.4bp/day t -3.3.
- DROP>2 respread (N 1109) 25.8%/-23.6 and DROP>2 cash (N 1110) 22.8%/-20.7: worse DD AND half the return. The high-beta picks
  carry the edge (same lesson as PQ1). 2025-10-29..2026-09: base +41.9% vs cap +20.9 / dcash -2.7.
- Live replay (17 sessions, descriptive only): cap sum +8.0% maxDD -5.9 vs base +0.3% / -19.5 — the recent tech-down weeks; not
  evidence (in-sample says the cap costs return per unit DD).
- Money (floor shares, sleeve 0.5): $2.3k base 37%/-12 vs cap 25%/-9.5; $10k 45%/-17 vs 30%/-14; $25k 46%/-19 vs 31%/-15.
- not tested: caps at other levels (registered 1.0 only), sector/single-name concentration caps, regime-conditional cap (only when
  QQQ below trend / vol high), beta measured on overnight returns instead of close-close, forward live shadow of the cap (only clean
  judge; the live replay is the one hint in favour), futures hedge of the residual.
- Runner `research/sim/night_beta_cap.py`, out `data/research/program/night_beta_cap_out.txt`.
