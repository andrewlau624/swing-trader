# Study AU (Round 19) — night picks tilted by trailing overnight persistence: AU3 (tug of war) SHADOW, AU1/AU2 DEAD (N 680)

Pre-registration: `round1_prose.md` Round 19 (commit dc53fcb, before any number). Scripts:
`research/sim/max_edge.py` (registered run), `research/sim/auction_audit.py` (post-hoc verification).
Outputs: `data/research/program/max_edge_out.txt`, `auction_audit_out.txt`.

## Sources and mechanism
- Aboody, Even-Tov, Lehavy & Trueman, JFQA 2018: overnight returns as firm-specific retail sentiment.
- Akbas, Boehmer, Jiang & Koch, JFE 2022: the daily "tug of war" (positive overnight, negative intraday).
- CXO Advisory's overnight-momentum summary.

Names whose price is repeatedly bid up overnight and sold off during the day have a persistent
clientele that buys at the open. The night leg sells at the open auction, so it sells into that demand.
- **Who pays:** retail and attention buyers at the open, who keep paying because they keep coming back.
- **How it differs from add. 7:** add. 7 killed overnight momentum as a *standalone* strategy, because
  +8.7bp/night does not cover an auction round trip. Here it is a weight inside picks that already pay
  the cost.

## Variants (all known at 15:50 on d; SIP daily panel)
- **AU1:** ON20, the 20-day mean overnight gap (including d's own open), as a z-tilt on the live tilt.
- **AU2:** drop picks with ON20 < 0.
- **AU3:** TOW, the count of the last 20 sessions with gap > 0 and close < open, as a z-tilt (k 0.25,
  clip [0.25, 2], renormalised to the live tilt's mean).
- z constants are fixed from the 2021-23 picks: ON20 +15.9 / 126.3bp; TOW 5.14 / 2.10.

## Per-pick evidence (net at 2.5bp/side, 2021-23 tercile cut points)

| feature | 2021-23 T1 / T2 / T3 | 2024-26 T1 / T2 / T3 |
|---|---|---|
| ON20 | +2.2 / −0.1 / +36.5bp | −7.2 / +10.6 / +26.3bp |
| **TOW** | **−5.1 / +8.6 / +26.2bp** | **−13.3 / +10.6 / +24.0bp** (monotone in both halves) |

TOW is nearly orthogonal to the existing inputs (Spearman: vol20 −0.02, day return −0.01, yesterday's
return −0.04, log price +0.04, log ADV +0.04; ON20 +0.36). The tercile spread holds inside every price
tercile and in the low- and high-vol terciles.

## Book results (fixed capital, whole shares; judged at 2.5bp/side)

| AU3 | V7 inc (21-23 / 24-26) | NW t | placebo (sign / within-night shuffle) | dDD | Roth inc |
|---|---|---|---|---|---|
| $2.3k | +3.06pp (+1.08 / +3.59) | 2.62 | 99% / — | +1.8 | +2.80pp |
| $10k | +3.23pp (+1.28 / +3.57) | 2.99 | 100% / 100% | +1.5 | +2.96pp |
| $25k | +2.82pp (+1.04 / +3.19) | 2.62 | 100% / — | +1.5 | +2.58pp |

- P(DD>50%) 5y: 0.0% for both books.
- tier_hi: +2.5..+2.9pp, t 2.7-3.0.
- AU1: +2.0..+2.3pp but t 1.5-1.7. AU2: −1.3..−1.7pp at 2.5bp. AU2's tier_hi "gain" (+5-6pp) is the
  night-leg cost gate again: less exposure when the leg nets ~0, the same pattern as Study AS.
- **Verdict as registered: AU1 DEAD, AU2 DEAD, AU3 passes all 7 checks → SHADOW.**

## Post-hoc verification of AU3 (no new variant, no N)
1. **Auction prints (Study AW).** TOW is built from vendor opens, and so is the backtest return. A
   persistent first-print bias in a name would make TOW "predict" it mechanically. Re-judged with every
   return taken from the official crosses, AU3 passes **6/6 judged cells**: V7 $10k +3.15pp (+1.32 / +3.48),
   t 3.01; Roth $10k +2.88pp. The effect is not the artifact.
2. **Second implementation** (fractional per-pick contributions, no `Sim`, the live sizing rule
   `target = per x w`): +1.55 / +3.25pp/yr, NW t 2.87 on vendor returns; +1.63 / +3.18, t 2.88 on auction
   returns. It agrees with the simulator.
   - **Caveat found:** with a hard 10% name cap applied *after* the tilt, the gain falls to +0.44pp, t 1.0.
     The money comes from leaning harder (up to 20% of the leg) into high-TOW names on nights with
     ≤ 10 picks (83% of nights). Live has no post-tilt cap today. A `moderate` profile (cap .15)
     needs its own check before the two are combined.
3. **By year (V7 $10k):** 2021 +3.7, 2022 −0.0, 2023 +0.3, 2024 +1.5, 2025 +4.0, 2026 +5.8pp. Weak in
   2022-23, so 2021-23 is carried by 2021.
4. **DSR at N 680:** the increment's own Sharpe is 1.29 vs SR0 1.33, so **DSR 0.46**. It is not
   significant after 680 trials, which is why this is SHADOW, not ADOPT.

## Money (V7 taxable, 2.5bp/side, pre-tax; Roth tax-free)

| | $2.3k | $10k | $25k |
|---|---|---|---|
| V7 | +3.1pp = **+$70/yr** | +3.2pp = **+$323/yr** | +2.8pp = **+$705/yr** |
| Roth cash IBS+night | +2.8pp = +$64 | +3.0pp = +$296 | +2.6pp = +$645 |

**Capacity:** this is a re-weighting inside the night leg, so it breaks where the night leg breaks
(Study V: $/yr peaks near $250k). It concentrates up to 20% of the leg per name, so impact arrives a
little earlier: at $100k ≈ +$2.8k/yr if the leg's level holds; at $500k it is moot (the night leg is
capped in dollars).

## Round 20 robustness (study_ax_auction_share.md)
- R1: TOW computed from the official crosses (corr +0.96 with the vendor version): +2.4-2.9pp, t 2.5-2.6.
- R2: under the moderate 15% name cap +4.4pp (t 3.0); on top of tilt v2 +2.7pp (t 2.5). No conflict with either.

## Switch — BUILT 2026-10-01, OFF (shadow logging only)
Built on the user's instruction after the round. Code: `signals.tug_of_war` / `night_tilt_tow` / `tow_gate`,
`marketdata.eligibility` (adds `tow`), executor 15:40 `[night] tow shadow:` line + `tow` in
`daily-decisions*.jsonl`, `make review` section 9 (the gate), config `daily.night_tilt_tow: false`, 7 tests.
The spec it implements:
- `daily.night_tilt_tow: false`. When true, multiply the live v1 tilt by
  `clip(1 + 0.25 · (TOW − 5.14) / 2.10, 0.25, 2)` and renormalise to the v1 mean.
- **Inputs:** TOW = the count of the 20 completed sessions before d with open_t > close_{t−1} and
  close_t < open_t, from **regular-hours** daily bars. The open is the 09:30 cross and the close the
  16:00 cross: use `marketdata.rth_minutes` or official auction prints, never a vendor "day" that starts
  the evening before; label by `marketdata.trade_date`. A name with < 15 valid sessions gets z = 0.
- **Shadow first:** log the TOW weights beside v1 in the 15:40 `[night]` line (like the v2 line).
- **Gate to turn on:** ≥ 300 live picks with the weight logged. The high-TOW tercile's live net
  (auction fills) must exceed the low tercile's.
- **Kill rule:** after ≥ 300 picks, if the high-minus-low TOW tercile net ≤ 0, switch off.
- **Tests:** TOW counts on a synthetic bar series; z = 0 on a short history; the weights' mean equals
  the v1 mean; no effect when off.
