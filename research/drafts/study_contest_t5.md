# Contest hunt T5: short earnings iron fly t-1 -> t+1 — DEAD as registered (far-side fills); real effect mid-to-mid

Pre-registered `round1_prose.md` (8a3935e, N 800 -> 803). Runner `research/sim/contest_straddle.py` (`fetch5` / `run5`).
Events as T3 (Nasdaq calendar, >= $2B). Short ATM call + put, long wings nearest +/-10%, earliest expiry >= t+1; sell on
the 15:51 NBBO of t-1 (bid), buy back on the 15:51 NBBO of t+1 (ask), $0.65/leg. Data fix before the verdict (no rule
change): a short leg with no bid at entry is no trade; a missing long-wing bid at exit counts 0.

| | n | return on risk (far side) | median | win |
|---|---|---|---|---|
| select 2023-24 | 9,746 | -54.9% | | |
| judge 2025-26 | 8,369 | **-64.8%** | -64.1% | 11% |

**Mid-to-mid it works** (4,191 events with two-sided quotes on all legs both days): **+20.5% of risk per trade**, median
+15.1%, 68% win; select +19.4% / judge +21.4%; ex-top-5 +17.0% / +19.8%. Named counterparty: buyers of event premium
(retail lottery demand), the IV crush is real. But four legs crossed twice cost a median **63% of risk** in half-spreads.
At half of the half-spread (a mid-ish complex-order fill): -26% / -64% (mean; spread outliers dominate).
Market cap >= $50B (690 events, not registered): mid +19.3%, half-spread 17.7% of risk, **+3.5% at half the spread**.

Lead, not a pass: a short earnings fly on mega caps lives or dies on passive complex-order fills, which no backtest
here can measure. The only honest test is forward: post the fly at mid on Schwab and log fill rate and fill price vs mid
(1 contract, defined risk). All 2023-26 data has now been looked at; a rule cut on it needs a forward judge.
