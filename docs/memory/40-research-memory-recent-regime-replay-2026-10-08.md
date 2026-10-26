# Research memory — recent-regime replay (2026-10-08)

- Night leg exact 15:40 replay through 2026-10-07 (`research/sim/recent_night.py`, data `data/research/recent/`, `research/drafts/recent_regime_2026-10-08.md`): 2026-06..10-07 +113bp/trade gross (+98 at 7.5bp/side, day-clustered t 1.8-2.3) vs 2021-26 baseline +26 (+11); last 10 live-window sessions -55bp. Live fills match replay on 67 shared trips (corr .998, +-11bp), so the live shortfall is a 2-week sample, not execution or a regime break.
- Noise leg (QQQ+SMH) ~0/negative all 2026 (YTD -0.5 no-lag / -1.1 lag at 0.5bp/fill, Sharpe -0.7/-1.0 vs +0.6..0.8 in 2021-25); no sizing change on either leg.
