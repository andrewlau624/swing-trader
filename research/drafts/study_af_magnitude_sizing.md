# Study AF — size the conviction trade by predicted magnitude: DEAD (N 619 -> 623)

Stamp: `round1_prose.md` Round 16 AF (commit 4b33667). Script: `research/sim/conviction_af.py` (~5 s).
Output: `data/research/program/conviction_af_out.txt`. Brief: `prompt_conviction_research.md` idea #2.

## Setup
- Trade: `book.breakout_days` (TQQQ, first noise-band breakout ≥ 0.341σ, band/VWAP exit, 15:57). The trade list
  is reproduced exactly (785 trades 2016-26, max |diff| 0).
- m̂ = OLS of QQQ |ln(C/O)| on |gap_z|, yesterday's range_z, yesterday's rvol and VIX(d−1). It was fitted on
  2016-23 and frozen. All inputs come from regular-hours minutes plus the Cboe VIX close. Terciles are frozen on 2016-23.
- Weight = 0.5 × multiplier by tercile. The day's allowance is reserved at the open, so a bigger conviction day
  shrinks the QQQ/SMH noise cap that day. At mult 2 the cap goes 0.75 → 0 at weight 1.0.

## Size is predictable; EV is not monotone in it
- m̂ explains 13-24% of QQQ |open→close| in every half: R² 0.24 in 2016-20, 0.13 in 2021-23, 0.18 in 2024-26.
- Its correlation with the trade's own |gross| is +0.22 to +0.31. So Study AE's link holds: the trade moves more
  on loud days.
- EV does not follow. Net EV per trade at 1.5bp/side, by m̂ tercile:

| m̂ tercile | 2016-20 | 2021-23 | 2024-26 | 2016-23 |
|---|---|---|---|---|
| T1 calm | +0.6bp (n 161) | +5.6 (25) | +6.4 (33) | +1.3 (t 0.1) |
| T2 middle | **+40.5** (99) | **+34.1** (97) | **+36.9** (122) | **+37.3 (t 2.75)** |
| T3 loud | −1.0 (95) | +35.8 (117) | **−44.4** (33) | +19.3 (t 1.1) |

- VIX terciles look the same: the middle tercile is best in every half, and the top tercile is −54bp in 2024-26.
- The trade earns in ordinary-vol days. On calm days it breaks out and fails (30% wins). On the loudest days it
  gets whipsawed as often as it rides.
- The prior stated in the pre-registration held. |gross| rises ~2x from T1 to T3 while EV per unit |gross| falls
  after T2, so sizing up on loud days buys variance, not edge.

## Variants (increment vs flat 0.5; tier_hi = conviction 3bp/side, noise 1.5bp/fill; mult 2)
| variant | 2016-20 | 2021-23 | 2024-26 | 2016-23 | NW t | placebo pct | B3 maxDD d | P(DD>50%) | DSR |
|---|---|---|---|---|---|---|---|---|---|
| AF1 m̂ .5/1/1.5 | −1.6pp | +1.0 | −2.0 | −0.6 | −1.0 | 17 | −0.2 | 1.5% | 0.00 |
| AF2 m̂ 0/1/2 | −2.8 | +1.8 | −3.7 | −1.1 | −0.9 | 22 | −0.7 | 1.9% | 0.00 |
| AF3 VIX .5/1/1.5 | −2.0 | +1.1 | −2.5 | −0.9 | −1.4 | 9 | −0.2 | 1.6% | 0.00 |
| AF4 m̂ inverse 1.5/1/.5 | +1.6 | −2.6 | +1.8 | −0.0 | +0.5 | 80 | 0.0 | 1.4% | 0.00 |

- At mult 4 (add. 40, shadow) the noise-cap cost disappears. AF1/AF3 turn +3.5pp in 2021-23 but stay negative in
  2016-20 and 2024-26 (full t +0.2 / −0.2).
- **Every variant fails bar 1 (both halves > 0) and bar 2 (t ≥ 2).** AF1-AF3 also fail the placebo. All four are
  DEAD. AF4 (the risk-parity rival) is the least bad: ~0 in 2016-23.

## Money (tier_hi, mult 2, mean increment × E; 2024-26 in brackets)
| | $2.3k | $25k | $100k | $500k |
|---|---|---|---|---|
| AF1 | −$22 (−47) | −$240 (−508) | −$959 (−2,031) | −$4.8k (−10.2k) |
| AF2 | −$40 | −$436 | −$1,746 | −$8.7k |
| AF4 | +$11 (+42) | +$115 (+453) | +$460 (+1,814) | +$2.3k (+9.1k): not significant |

- **Capacity (2024-26, TQQQ $ volume in the entry minute):** weight 0.5 is a median 0.04% / 0.16% / 0.82% of that
  minute at $25k / $100k / $500k. The 95th percentile is 0.11% / 0.43% / 2.1%, and the worst case at $500k is 4.8%
  (9.6% at weight 1.0).
- So the conviction trade itself scales fine to $500k in TQQQ. At $500k, split entries over 2-5 minutes on loud days.

## Reading
- The user's intuition is half right. The size of the day IS predictable at the open, and the breakout trade DOES
  move more on those days.
- But its expected value peaks on ordinary days, not loud ones. Scaling the bet with predicted magnitude adds
  variance and, at mult 2, also takes margin from the noise leg.
- Keep the flat 0.5. Do not rerun with other cut points or multipliers: the middle-tercile hump is a post-hoc
  shape (N 623).
