# Study Lab-BA — short the reopening after a halt: DEAD, all three variants (program N 705 -> 708)

Stamp: `round1_prose.md` Lab Round 25 (commit 415eaad); plan `daytrade/plans/halt_short.md`. Script
`daytrade/research/ba_replay.py` (the lab's `HaltResume(side="sell")`; Lab-AY's data and detection, corrected fill
model). Costs 20/40bp per side; 2022-01 to 2026-09.

| variant | n | gross | 1x net (median) | t | 1x H1 / H2 | 2x H1 / H2 | without top 20 | winsor 1/99 | placebo |
|---|---|---|---|---|---|---|---|---|---|
| Lab-BA1 short after halt UP | 1,153 | +83 | +43 (**−308**) | 1.2 | +21 / +57 | −24 / +12 | **−32** | +41 | 100 |
| Lab-BA2 BA1 on easy-to-borrow names only | 193 | **−70** | −110 (−273) | −1.5 | −14 / −223 | −46 / −280 | −339 | −116 | 66 |
| Lab-BA3 short after halt DOWN, no SSR | 668 | +80 | +40 (−100) | 0.8 | +35 / +43 | −6 / +6 | **−88** | +44 | 99.7 |

## Reading
- After a halt these names do drift down (the placebo is at the 99.7-100th pct). But the short's profit is a handful
  of 40-55% collapses inside 30 minutes (OST $40 -> $18, GMEX $49 -> $24, JBDI $37 -> $18). The typical trade is
  stopped by the next spike: medians −100 to −308bp.
- Without the 20 best trades both BA1 and BA3 lose, and both fail 2x in H1. **t is only 0.8-1.2.**
- **On the names a broker can lend (BA2, the locate proxy) there is no edge at all (−70bp gross).** The collapses
  happen in names nobody can short.
- **DEAD**, all three variants: they fail the pre-registered outlier check, t, and 2x in both halves.

## What the halt family leaves
- Long after a halt: −130bp (Lab-AY).
- Short after a halt: a lottery on unborrowable names (Lab-BA).
- The direction is real but untradable for a retail account. Closed: no more halt variants.
