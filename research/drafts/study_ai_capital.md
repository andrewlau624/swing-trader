# Study AI — how much daytime capital the conviction trade can take: DEAD as variants; "turn it on" priced (N 630 -> 634)

Stamp: `round1_prose.md` Round 16 AI (commit d07e24b). Script: `research/sim/conviction_ai.py` (~10 s).
Output: `data/research/program/conviction_ai_out.txt`. Brief idea #7.

## The binding constraint is margin, not the broker multiplier
- TQQQ/SQQQ carry 75% maintenance. The live gate reserves conv × 0.75 at the open, so every extra unit of conviction
  weight comes out of the QQQ/SMH noise leg's cap.

| weight | noise cap, mult 2 | noise cap, mult 4 |
|---|---|---|
| 0 | 1.50 | 3.50 |
| 0.5 | 0.75 | 2.00 |
| 0.75 | 0.38 | 1.25 |
| 1.0 | 0 | 0.50 |

- The noise leg earns about as much per unit of margin, so moving margin from noise to conviction is ~a wash.

## Results (tier_hi: conviction 3bp/side, noise 1.5bp/fill; increment vs w 0.5 at the same mult)
| row | 2016-20 | 2021-23 | 2024-26 | NW t | placebo | B3 maxDD (base) | P(DD>50%) (base) | P(DD>30%) | worst trade, % equity |
|---|---|---|---|---|---|---|---|---|---|
| **turn it on (0 → 0.5), mult 2** | +0.5pp | +8.2 | +3.3 | +1.5 | 93 | −21.3 (−20.9 off) | 1.7% (0.9% off) | 33% (27%) | −3.9% |
| turn it on (0 → 0.5), mult 4 | +2.1 | +11.2 | +5.1 | +2.3 | 99 | −22.1 (−21.0) | 3.0% (1.1%) | 43% (31%) | −3.9% |
| AI1 w 0.75, mult 2 | −0.1 | +1.4 | +1.1 | +0.5 | 69 | −20.7 | 1.9% | 37% | −5.9% |
| AI2 w 1.0, mult 2 | +0.0 | +2.4 | +2.0 | +0.5 | 69 | −20.5 | 3.1% | 44% | −7.9% |
| AI3 w 1.0, mult 4 | −0.7 | +4.5 | +2.0 | +0.6 | 72 | −22.0 (−22.1) | **5.2%** | 52% | −7.9% |
| AI4 w 2.0 via MNQ (noise kept) | +7.3 | +34.8 | +14.9 | **+2.2** | 98 | **−36.3** | **37.9%** | 93% | −15.7% |

- AI1-AI3 fail the t bar (≈ 0.5), and AI3 also fails P(DD>50%).
- AI4 passes t and the placebo but fails the drawdown bars by a mile (maxDD +15pp, P(DD>50%) 38%).
- **All four are DEAD.** DSR ≤ 0.16 at N 634.

## What this says about the conviction trade itself
- AI4 is 1.5 extra units of the pure trade, so it measures the trade's own edge.
- At 3bp/side it earns about +11%/yr per unit of equity, 2016-26, with NW t ≈ 2.2. That covers the full decade:
  the threshold was fixed on 2016-23, and 2024-26 is held out. Held out it still earns +10pp per unit.
- The edge is real at the book level. Its problem is size: at one unit it is a −7.9%-of-equity worst trade.
- Turning it on at 0.5 in TQQQ (the switch already built) adds **+3.3pp/yr in 2024-26 at mult 2**, +5.1pp at mult 4.
  - Taxable $/yr (2016-26 mean, tier_hi, pre-tax / after 35%): $2.3k +$78 / +$50; $25k +$844 / +$549;
    $100k +$3.4k / +$2.2k; $500k +$16.9k / +$11.0k.
  - At mult 4: $100k +$5.5k, $500k +$27.3k pre-tax.
  - The cost: P(DD>50%) 0.9 → 1.7% (mult 2) and P(DD>30%) 27 → 33%. Both stay inside the 5% bound.
  - Its NW t at mult 2 is 1.5, below the program's 2.0 bar for NEW variants. But this is the already-built shadow
    switch (add. 19), whose on-rule is live fill evidence, not a new test.
- **Capacity (2024-26):** at w 1.0, the TQQQ order is a median 0.08% / 0.33% / 1.6% of the entry minute's $ volume
  at $25k / $100k / $500k, and the 95th pct is 4.3% at $500k. It is not capacity-bound below ~$1M. Split the order
  over a few minutes at $500k.

## Reading
- Do not raise the weight in TQQQ. It only moves margin from the noise leg to the conviction leg for ~0 net gain.
- The trade's edge is worth more if it does NOT compete with the noise leg for TQQQ's 75% margin. That points to
  futures (MNQ, taxed 60/40, no wash sales against the Roth's TQQQ). That is Study AJ, pre-registered next, at
  sane weights (AI4's 2.0 is far past the drawdown bound).
