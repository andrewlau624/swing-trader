# BETA-HEDGE (N 1103-1105, 2026-11-06): per-leg QQQ/SPY/PSQ hedge of the book — KILL

- Rule: short 60d close-close OLS beta (clip ±4) x leg notional of QQQ (SPY arm; Roth = long PSQ at a/(1+b)) over the exact
  holding window. Judge IBS 2017-20, night on live fills; 2021-26 descriptive. Runner `research/sim/beta_hedge.py`, out
  `data/research/program/beta_hedge_out.txt`.
- **IBS is ~100% same-window QQQ beta** (beta 0.99 t 28, alpha 0.0 on 2017-20; beta share 120%). Hedged: -1.24bp/day t -0.97,
  maxDD worse (-16.8 vs -13.5). SPY arm leaves +2.7bp t 1.8 = the picks' tech tilt. The IBS premium IS a timed market bounce;
  hedging removes the edge, not the drawdown.
- **Night backtest** beta 0.49, alpha 35.8%/yr t 3.5 (beta = 34% of raw); hedging halves return and RAISES maxDD (-28.8 vs -20.6,
  worst stretch was a 2026 rally). **Live night leg is different:** position beta median 2.45, regression beta 4.5 / corr 0.82 to
  QQQ overnight over 17 sessions (single-stock 2x LETFs dominate picks). That is the live drawdown source; 17 sessions = underpowered.
- Book 0.5/0.5 2021-26: unhedged MAR 3.04 beats every hedged form (best: IBS unhedged + night hedged, MAR 1.85).
- QQQ $656/share is too lumpy at $2.3k (night hedge rounds to 0 on 32% of nights); PSQ/SH work at any size.
- Open branches: beta cap / LETF exclusion in the live night leg; hedged-night forward log (>= 60 sessions); MNQ / options;
  regime-conditional hedge.
