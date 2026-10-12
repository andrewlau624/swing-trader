# Study HD — high-dollar intraday sleeve (separate objective)

Objective (user, 2026-10-06). A separate sleeve, not constrained by IBS/TME/PREF-EX/ETDX:
**high-conviction + short-duration + large $ per opportunity.** Leverage/concentration allowed
ONLY if the edge exists unlevered and is genuinely asymmetric (not manufactured variance).
Must coexist with the compounding book. Account ~$2.3k taxable / $1-3k Roth.

Required report per candidate: expected $/trade, $/day, win rate, loss distribution, EV after
costs, max loss, max historical DD, frequency, capital required, capacity, realistic leverage,
$ P&L at $1k/$2.3k/$5k/$10k, OOS. Favorite numbers, not Sharpe.

## Mechanism audit (prior work; see report)
Recurring finding (`NEXT.md:410-416`): single-stock intraday signals gross 0-10bp, spread costs
5-40bp -> the intraday family is almost entirely DEAD at retail cost.
- big_swings (AE): no feature predicts intraday direction (|t|>=3) -> killed.
- bottom_hunter (BH): "no systematic edge ... a sophisticated way to buy falling stocks" -> dead.
- dealer_gamma_free: free GEX proxy KILL (untouched 2016-20 n 111 mean -1.09bp t -0.13).
- halt reopen (AY/BA/BF): DEAD. imbalance (AV/BD/BE/BF): DEAD/underpowered.
- theme_explosion: no rule beats vol-matched random; SPY beats all -> DEAD.
- close_disloc: weak; imbalance_study flips halves -> dead.
- SSR-LIFT: mechanism CONFIRMED (diff-in-disc -43bp t -6.5) but small (+16.7bp/day short-only).
- LETF-NIGHT: PROMISING (in-sample, ~half beta 2.9) -- overnight, not same-day.

Genuinely-open paths for THIS objective:
1. Signed dealer gamma / options hedging (forced transactor = dealers). Free proxy failed;
   needs paid OPRA OI/gamma (~$180/yr). DATA-TARGET, not funded.
2. Leveraged-ETF close-rebalance pressure, **same-day** expression (forced MOC by LETF desks).
   Distinct from LETF-NIGHT (which is close->open fade). Testable on disk now. -> HD1.
3. One-night forced auction edges (SPLIT-T0, SPIN-T0, PREF-EX/ETDX) DO give large per-event
   returns with a forced counterparty, but are close->open overnight, not same-day.

## Study HD1 — Leveraged-ETF close-rebalance pressure, same-day (pre-register; N 875 -> 876)
`date`: Tue Oct 6 2026, night. Not read: any minute-level result for this rule.
- **Mechanism (forced transactor).** A daily-reset leveraged ETF (SOXL 3x SMH, TQQQ 3x QQQ) must
  rebalance exposure each day by ~(L-1) x AUM x r_underlying, executed into the close. On large
  |r| days this is a large, forced, same-direction MOC flow in the underlying, extending its move
  into the closing auction. The tradable same-day expression: enter the underlying in the
  direction of the day's move before the close, exit at the close.
- **Rule (frozen).** Underlyings SMH, QQQ (map to SOXL, TQQQ). At 15:40 (minute 370):
  `day_ret = c1530/prev_close - 1`. If `|day_ret| >= 2%`, enter in the direction of `day_ret`;
  exit at the closing-auction bar (minute 390). Costs: 2bp/side (liquid ETF) and a 5bp/side shock.
  Control: same rule on non-leveraged ETFs (SPY, EEM, GLD, TLT, USO, XLE).
- **Judge (PASS bar).** gross mean > 0 AND day-clustered t >= 2 AND ex-top-5 > 0 AND both halves > 0,
  AND LETF-underlying effect exceeds the control by >= 2bp. Then leverage 1/1.5/2/3x with $ at
  $1k/$2.3k/$5k/$10k and max intraday DD / worst sequence / P(catastrophic).
- **Kill.** Control >= underlying effect, or gross ~ 0, or cost eats it -> DEAD, region closed.
- Runner `research/sim/study_hd.py` -> `data/research/program/study_hd_out.txt`.

## Result — Study HD1 (DUPLICATE, not run; N stays 875)
The same-day 15:30->close-in-the-day's-direction rule was already tested twice:
add. 27 R3 (`research/sim/late_momentum.py`, V5 "LETF-rebalancing version": QQQ 2021-23
-14.8bp t -3.2; SPY -9.6; fit half flips OOS) and add. 34 Q3 (`research/sim/index_mechanics.py`,
QQQ/SMH 15:30->close: SMH 2024-26 +0.4bp; all cells t<2). Every variant negative at 2bp/side in
every period. `NEXT.md:1315` — "LETF-flow conditioned last half hour ... dead." HD1 differs only by
a 15:40 entry; not a distinct test. No runner written.
