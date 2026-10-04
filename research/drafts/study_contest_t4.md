# Contest hunt T4: overnight short QQQ 1DTE condor / iron fly (Muravyev-Ni) — DEAD (all three)

Pre-registered `round1_prose.md` (9e5e172, N 795 -> 798). Runner `research/sim/contest_options.py` (`fetch4` / `run4`).
Data: Databento OPRA cbbo-1m, one window per night (15:49 -> 09:37 next session), $0.09 total; 931 nights 2023-01..2026-09,
55 variant-nights unpriced. Sell on the 15:51 NBBO at the bid, buy back on the 09:35 NBBO at the ask, $0.65/leg.

| variant | n sel / judge | return on risk sel / judge | win judge | P(mean<=0) | 3-mo median / p10 / p90 @ $2.3k | P(-30% in 3 mo) @ $2.3k / $10k | judge CAGR @ $2.3k / $10k / $25k | maxDD @ $10k |
|---|---|---|---|---|---|---|---|---|
| T4a 0.5% OTM, $1 wings | 491 / 422 | -20.8% / **-29.8%** | 18% | 1.00 | -48% / -55% / -40% | 100% / 100% | -53 / -80 / -88% | -93% |
| T4b 1.0% OTM, $1 wings | 490 / 418 | -13.8% / **-18.6%** | 17% | 1.00 | -31% / -38% / -25% | 59% / 95% | -39 / -73 / -83% | -89% |
| T4c ATM fly, $2 wings | 493 / 424 | -34.9% / **-57.7%** | 5% | 1.00 | -73% / -77% / -67% | 100% / 100% | -63 / -85 / -91% | -96% |

Why: **mid-to-mid the overnight condor earns nothing** (mean -0.003..-0.004 $/share, mid win rate 59-65%, 2023 0.000,
2025 -0.009): no overnight option premium is left in QQQ 1DTE wings. Each crossing costs ~0.03-0.06 $/share in half-spreads
across four legs (wider at 09:35), so a ~0.5 credit on $1 wings loses 15-60% of risk per night after friction.
