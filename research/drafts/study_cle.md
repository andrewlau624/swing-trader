# Study CLE — small-account capital efficiency: IBS leverage financed two ways

**Status:** PRE-REGISTERED, one look, exploratory. NO DEPLOYMENT, NO MARGIN CHANGES, NO LIVE SIZING.
Registered 2026-10-05 before any leveraged account return was read (only the Goal L published
1.5x post-hoc row and the xasset premium scan were known, both cited as priors). Program N 821 -> 822.

Changed objective (user): not institutional capacity, but **small-account capital efficiency** at
$2.3k / $10k / $25k. The question: can moderate leverage on the validated IBS leg raise
**$/yr per account dollar** above the current book without unacceptable drawdown/liquidation risk?

## Why this is not a re-run of Goal L

Goal L (`study_goal_l.md`, dead) charged **retail margin 12.5%/yr on every unit of leverage** and
found leverage loses (`f*<0`: the book's average day earns less than a day of margin interest).
But a small account can obtain leverage two ways:
- **retail margin** (~12.5%/yr, callable, liquidation risk), and
- **3x ETFs** (UPRO/TQQQ/SOXL/TECL/TNA...): cash-purchased, **non-callable** (max loss = the
  position), with institutional swap financing embedded (~2x SOFR + spread ~5.5%/yr), i.e. roughly
  half the retail rate.
Goal L modelled only route (a). The xasset scan (`ibs_xasset_out.txt`) shows the IBS premium on
leveraged ETFs is ~3-4.5x the base (pooled +44.6bp vs +9.8bp) — "leverage only", which is exactly
what capital efficiency needs. This study measures the account economics of route (b) vs (a).

## Frozen design

- Leg: the **live IBS leg only** (top-3 of the 18 EQ18 ETFs by 12-1 momentum, re-ranked monthly,
  IBS(close d)<0.2, bought open(d+1), re-evaluated open(d+2)). Night leg OFF (it is the fragile,
  unproven leg; Goal L's Kelly was negative on it). Unit returns from the shipped simulator
  `book.ibs_days()`; cost 3bp/side already inside. Benchmarks (cited, not re-run): B0 = current
  two-leg book and Goal L's leverage rows.
- Exposure L in {1, 1.25, 1.5, 2, 2.5, 3} of the IBS sleeve.
- Financing routes: **margin** = 12.5%/yr on the borrowed fraction (L-1); **LETF** = 5.5%/yr on the
  borrowed fraction (embedded in the fund; no callability). LETF operational reality: on an IBS
  signal in name X, hold the 3x ETF tracking X (UPRO/TQQQ/SOXL/TECL/TNA/FAS/LABU/UDOW/EDC/MIDU...);
  where no liquid 3x exists, report the hair-cut proxy set. The primary LETF arm uses the **actual
  forward open(d+1)->open(d+2) return of the 3x proxy** from `etf_daily.parquet` (2016-2026), not
  base x 3, so daily-reset decay, expense and spread are inside the number.
- Account: no deposits; whole-share granularity noted as a caveat (it favours the LETF route at
  $2.3k, which this study does not credit). $2,000 Reg T floor: margin route only exists when equity
  >= $2,000.
- Tax: 30% on each year's net gain, paid year-end, loss carried forward (as Goal L).
- Windows: **2016-02..2020-12 (untouched for the IBS rule; the judge)** and 2021-26 (in-sample,
  reported for stability).

## Metrics (per arm, per window, at $2.3k/$10k/$25k)

CAGR, $/yr, maxDD, worst day, 5th-percentile day, P(account DD > 25%), P(DD > 50%), days the
margin route is liquidated (equity < maintenance), and the ratio return/account-dollar.

## Judged primary (one look, 2016-20 untouched)

`CAGR(cheap-financing levered IBS) - max(CAGR(B0), CAGR(same-L margin IBS))` on 2016-20, with
P(DD>50%) <= 5%.

- **CONVICTION CANDIDATE:** the best cheap-financing arm beats both B0 and its margin twin by
  >= +3pp CAGR on 2016-20, is positive on 2021-26, and P(DD>50%) <= 5% (liquidation 0).
- **PROMISING:** beats on one window, or the +3pp margin only on 2021-26.
- **SMALL / NON-SCALABLE:** a real but < +3pp improvement; not worth the complexity.
- **REJECTED:** does not beat B0 on the OOS window, or P(DD>50%) > 5%, or financing kills it.

## Report-only

- The same table for the 2021-26 window.
- LETF-express using the proxy set vs base x3 (tracking check).
- Sensitivity of the LETF arm to the embedded financing assumption (3%, 5.5%, 8%).
- The xasset cross-check: base vs LETF IBS premium (already computed).
- Note on whole-share granularity at $2.3k (why 3x ETFs help a small account beyond financing).

## Hard rules

Leverage only on the validated IBS leg. Never "guaranteed". If no arm clears, the verdict is
REJECTED/SMALL and the answer stands: no small-account leverage edge. Runner
`research/sim/cle.py` -> `data/research/program/cle_out.txt`; one look.
