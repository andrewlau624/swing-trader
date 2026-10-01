# Study BD (Round 26) — closing-auction imbalance on the night picks: DEAD (N 701)

Pre-registration: `round1_prose.md` Round 26 (commit d0d8e9a, before any data). Data: Databento `imbalance` schema,
the first closing-auction message 15:50:00-15:52:00 ET for every night pick 2021-26 on its listing exchange
(`research/sim/imbalance_fetch.py`, ~75 min, ~$15 of the shared credit). Script `research/sim/imbalance_study.py`;
output `data/research/program/imbalance_study_out.txt`. Night returns from the official crosses (Study AW).
Source: Bogousslavsky & Muravyev (JFM 2023), closing-cross price pressure reverts overnight. This was the parked
Round 13 AC idea, the last untested mechanism with a named payer.

## Coverage
- 9,546 picks; 90% have a closing message (Cboe BZX listings, 10%, have no feed).
- Sides: buy imbalance 4,359, sell 2,532, none 1,696.
- Feeds: Nasdaq 5,757, NYSE 2,047, Arca 654, American 129.
- SIR (signed imbalance / ADV shares) is nearly orthogonal to TOW (−0.02), vol20 (+0.09) and depth (+0.10).

## Per-pick net (2.5bp/side)
| | sell imbalance | buy imbalance | none | SIR T1 / T2 / T3 |
|---|---|---|---|---|
| 2021-23 | +27.5bp | +1.7bp | −7.1bp | +17.2 / −23.9 / +14.7 |
| 2024-26 | −4.8bp | +9.1bp | +15.9bp | +2.3 / +22.1 / +3.9 |

Every pattern flips between the halves; nothing is monotone.

## Book (2.5bp/side judged)
- **BD1** (tilt toward sell imbalance): +0.2..+0.4pp/yr, NW t 0.5-0.8, placebo 67-78%, shuffle 62%, DSR 0.01.
  **DEAD.**
- **BD2** (drop buy-imbalance picks): −5.3..−6.4pp/yr, t −2.2. The within-night shuffle sits at the 60th pct,
  so dropping a random 46% of picks costs the same. It is lost exposure to a profitable leg, not selection.
  **DEAD.**
- At tier_hi, BD2 is +0.8..+1.3pp (t 0.3): the familiar cost gate (less night exposure when the leg nets ~0),
  not a signal.

## Verdict
The published imbalance at 15:50 carries no ex-ante information about which night picks bounce. The
auction-pressure reversion in the literature is either already in the price by the time it is published, or
it is in large caps; the night leg trades high-volatility small names. No live imbalance feed is worth
buying for this leg.
