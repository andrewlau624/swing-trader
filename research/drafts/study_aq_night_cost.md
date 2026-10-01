# Study AQ — the night leg's cost crossover, and the cash-IRA Roth at the brief's stressed cost (Round 17c)

> **Correction (Round 18, `study_as_at_discord.md`):** the costs in this study are **per side**
> (`B.cost_bps` is per side; both replays charge `ret − 2·c`), not round trip. "5bp (2x measured)"
> is 10bp round trip; the brief's real 2x stress (5bp RT) is the 2.5 row (22.0%/yr). The crossover
> is ~5-6bp per side. The verdict stands and the gate is about twice as wide.

`research/drafts/round1_prose.md` Round 17c, Study AQ (pre-registered before any number).
Code: `research/sim/night_cost.py`. Output: `data/research/program/night_cost_out.txt`. Report only.

## The correction to Study AL

Study AL judged the night leg at the repo's `tier_hi` (15-50bp round trip). But the brief's cost
instruction is the **measured** costs (buys ~-2.5bp, sells ~0bp; add. 29 measures -0.5/-1.0bp),
**"stressed at 2x" (~5bp round trip)**. `tier_hi` is 5-10x measured, not 2x. The night leg's whole
verdict is a cost question, and the crossover is right at the brief's stress.

## Cash-IRA Roth, fixed $3k, full CAGR by flat night round-trip cost

| cost (bp) | IBS .5 + night .5 | IBS only 1.0 | night only 1.0 |
|---|---|---|---|
| 0 | 25.0% | 18.6% | 31.3% |
| 2.5 (1x measured) | **22.0%** | 18.4% | 25.0% |
| **5 (2x measured)** | **19.0%** | 18.3% | 18.9% |
| 7.5 | 16.2% | 18.2% | 13.1% |
| 10 | 13.4% | 18.1% | 7.6% |
| 15 | 8.0% | 17.9% | -2.5% |
| tier (~10bp) | 13.4% | 18.1% | 7.7% |
| tier_hi (~15-50bp) | 7.5% | 17.9% | -3.4% |

**The crossover is ~5-6bp round trip.** Below it the night leg is the *best* leg (25-31%/yr); above
it the cash-IRA book should be IBS-only. The taxable V7 book shows the same: 39.1% at 0bp, 35.6% at
2.5bp, **32.0% at 5bp**, 28.6% at 7.5bp, 18.6% at tier_hi.

## AL1 (IBS .5 + night .5, cash IRA) at the brief's stressed cost

| night cost | full CAGR | halves 21-23/24-26 | NW t vs BIL | placebo | maxDD | P(DD50) |
|---|---|---|---|---|---|---|
| 2.5bp (measured) | 22.0% / Sh 1.58 | 15.4 / 29.5 | +3.55 | 100% | -12% | 0% |
| **5.0bp (2x measured)** | **19.0% / Sh 1.39** | **13.0 / 26.0** | **+3.06** | **99%** | **-12%** | **0%** |

The IBS-only recommendation in Study AL was an artifact of over-stressing: at the brief's own stress
this book clears every clause — both halves up, t 3.06, placebo 99%, maxDD -12% (equal to the
limited-margin M3), P(DD>50%) 0%.

$/yr vs idle at 5bp: **+$364 at $2.3k, +$1,582 at $10k, +$3,956 at $25k** (tax-free).

## Verdict

**The cash-IRA Roth should run IBS .5 + night .5 (both GFV-safe), not IBS-only, and can start now.**
The gate is the **live night round-trip cost**: the leg pays while it is ≤ ~5-6bp. Live fills are
measured at ~0-2.5bp (add. 29), so the book is expected to earn 19-22%/yr tax-free. If the open-sell
cost drifts above ~6bp, switch to IBS-only (Study AL3); the existing night-leg kill rule (≥100 round
trips, losing, t<-1) already watches this.

The spec is the Study AL `daily.roth_cash_ira` switch, changed from IBS-only to IBS .5 + night .5
(the shipped overnight book), with the cost gate as the named risk.
