# Study XB — Existing-book optimization: IBS × TME portfolio allocation (pre-registered N 819 → 820)

Registered in `round1_prose.md` before any allocation number was read. One judged question: does allocating the free
sleeve between the IBS overlay and the TME-K (hedge-only Treasury month-end) overlay beat 100%-to-IBS, after tax and at
size? Runner `research/sim/xb_alloc.py`; output `data/research/program/xb_alloc_out.txt`; one look, 2026-10-04.

## Verdict: KILL

No allocation of the free sleeve to the Treasury overlay improves the book. Every w_IBS < 1 is worse in CAGR, dollars
and (mostly) Sharpe; the primary incremental is **-2.5pp/yr**. The existing book should stay **100% to IBS**. Do not
reallocate; do not re-anchor TME into the free-cash sleeve.

## Judged primary
Sleeve = w × IBS-V6 (close→open) + (1-w) × TME-K, equal split when both active, 2016-09..2026-09, 5 bp/side IBS,
2 bp/side Treasury, taxable.

| w_IBS to IBS | CAGR | Sharpe | maxDD | $/yr @ $10k | $/yr @ $25k | $/yr @ $100k |
|---|---|---|---|---|---|---|
| 0.0 (all TME-K) | **-2.22%** | -1.00 | -21.6% | -222 | -555 | -2,218 |
| 0.3 | -0.69% | -0.26 | -12.3% | -69 | -171 | -686 |
| 0.5 | +0.33% | 0.11 | -10.5% | 33 | 82 | 327 |
| 0.7 | +1.33% | 0.31 | -11.0% | 133 | 333 | 1,333 |
| **1.0 (IBS only)** | **+2.83%** | **0.47** | -12.4% | 283 | 706 | 2,826 |

- **Primary incremental (50/50 − 100% IBS-V6): -2.50 pp/yr** (2016-20 -2.26, 2021-26 -2.68). Negative in both halves,
  ex-best-5 months negative (-0.09% vs -0.01%), corr(IBS-V6, TME-K) -0.089. **FAIL all gates.**
- The live IBS stream (open(T+1)→open(T+2), the production implementation) earns **+7.93% CAGR, Sharpe 0.85** full-sample
  — higher than V6, because it keeps the first day-session exposure. The allocation conclusion is unchanged (TME loses
  against either).

## Why: the hedge destroys the validated effect
The only new construction in this study was TME-K (long TLT, short β·IEF). It is what breaks the overlay:

| stream (100% sleeve, 2016-26) | CAGR | Sharpe | maxDD |
|---|---|---|---|
| TME-A (unhedged TLT close(T-3)→close(T)) | **+2.81%** | 0.65 | -6.1% |
| TME-K (β-hedged) | **-2.22%** | -1.00 | -21.6% |
| IBS-V6 | +2.83% | 0.47 | -12.4% |
| IBS-live | +7.93% | 0.85 | -12.2% |

TLT's trailing-252d beta to IEF runs **~1.8-2.2** (mean 1.96 over 2016-26), so shorting β·IEF over-hedges: the month-end
duration bid is a *long-duration / curve* effect, and the IEF short removes more than the Treasury-market beta. The
hedge flips a small positive overlay negative. Empirically (window months): unhedged TLT +43.2 bp (2016-20) / +17.9 bp
(2021-26); hedged -15.3 / -17.9 bp. Even the *unhedged* TME overlay (+2.81%) does not beat IBS-V6 (+2.83%) or IBS-live
(+7.93%), so there is no allocation that helps regardless of the hedge.

## The other phases (per the prescribed order) — all closed, no meaningful opportunity
1. **Audit** — `ibs_oos_out.txt`: IBS<0.2 positive in both halves, +29.8bp OOS (2016-20), beats top-3 (+9.4bp) and
   IBS>0.8 (-2.6bp), not outlier-carried. This is the book's real, durable edge.
2. **Conditional IBS** — dead: AP1-AP3 (xsec rank), AP5 (stricter threshold), AV1 (IBS>0.5 exit), gap-skip,
   IBS>200d SMA, sector/trend gating all below the repo's +2pp adoption bar (`NEXT.md`).
3. **Sizing** — dead: vol-target, signal-strength, fractional/levered Kelly (Goal L). Kelly f* ≈ 6-7 on IBS but the
   leverage variants are below +2pp and post-hoc.
4. **close→open** — V6 is SHADOW/borderline (`study_b_taxable_v6.md`: "concentrated in 2024-26, placebo 53-58th pct,
   DSR 0.16-0.19"). No change; the production live form already earns more than V6 here.
5. **IBS × TME allocation** — **THIS STUDY: KILL.** No allocation helps.
6. **Universe** — `ibs_xasset_scan` + 24-ETF universe both below the +2pp bar; cross-asset premium weak except leverage.
7. **Capacity** — IBS is the slowest-decaying leg; no bottleneck until far above the account's likely size.

## Blunt conclusion
**No modification to the existing book's timing, sizing, allocation, or universe produced a meaningful improvement.**
The one genuinely open lever — allocating the free sleeve between IBS and the validated TME — loses money at every
weight, in both halves, at every capital level. This branch merely confirms the existing book is already at its local
optimum for the levers available. **No live capital reallocation; no new shadow.** IBS stays 100% of its sleeve; TME
remains a standalone, capital-light, small-dollar overlay (its forward shadow already registered) and must not be
re-anchored to the IBS cash.
