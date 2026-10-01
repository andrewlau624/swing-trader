# Study Lab-AV — opening L1 imbalance + trade flow on historical SIP ticks (QQQ, SPY): DEAD, underpowered (program N 673 -> 674 lab-local)

Stamp: round1_prose.md Lab Round 20. The lab's `OpenImbalance` strategy code through the engine. SIP NBBO (thinned to
the last quote per second) and every SIP trade 09:30:00-09:34:59, NBBO 09:35:00-05 and 10:05:00-05, minute bars for
the stop. 1,188 of 1,190 sessions 2022-01 .. 2026-09; 2 days lost to a hung download, skipped, not patched.

| | n | 1x net (t) | H1 / H2 1x | 2x H1 / H2 | by symbol 1x | placebo |
|---|---|---|---|---|---|---|
| Lab-AV | **89** | +3.3 (t 1.35) | +8.5 / +1.2 | +6.9 / **−0.3** | QQQ +7.9, SPY −2.2 | 91.4 |

Gross mid -> mid +4.8bp.

## Reading
- The registered QI threshold (|QI| >= 0.20) was set for a single-venue L1 feed. On consolidated NBBO sizes, the 5-minute
  mean QI of QQQ/SPY sits within about ±0.15, so the rule fired on 89 of ~2,400 symbol-days. Far too few to tell
  +3bp from 0.
- **DEAD** as registered (2x H2 negative, t < 2, placebo < 95). Nothing re-tuned.
- **Consequence for Lab-AT** (the same rule on the recorder's Schwab L1): expect few signals. Its first look (after
  40 clean sessions) stays as registered; any threshold change would be a new variant.
