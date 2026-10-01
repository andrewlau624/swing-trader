# Study AZ (Round 22) — tax-exempt ex-dividend overnight capture in the Roth: DEAD (N 688)

Pre-registration: `round1_prose.md` Round 22 (commit 4f11550, before any number). Script `research/sim/exdiv_roth.py`;
output `data/research/program/exdiv_roth_out.txt`. Dividends: Alpaca `/v1/corporate-actions` (14,543 regular cash
dividends, free), cached in `data/research/night/dividends.json`. Sources: Elton-Gruber (1970) clientele; against:
Ruan & Ma 2012 (ETFs, so ETFs excluded), Bali-Hite 1998 (ticks).

## The gap exists, but it is smaller than the cost
Top-500 non-ETF stocks going ex the next morning, held MOC → MOO, dividend-inclusive, minus SPY's overnight:

| | events | ex-night return minus SPY | mean yield | implied drop ratio |
|---|---|---|---|---|
| AZ1 yield ≥ 0.25%, 2021-23 | 2,551 | **+7.4bp (t 4.4)** | 73bp | 0.90 |
| AZ1, 2024-26 | 2,281 | +3.9bp (t 1.9) | 69bp | 0.94 |
| AZ2 yield ≥ 0.50%, 2021-23 / 2024-26 | 1,697 / 1,441 | +6.0 / +3.6bp | 92 / 88bp | 0.93 / 0.96 |

Tax-exempt holders do capture part of the dividend: the drop is 90-96% of it, and the gap is shrinking.
But the gap is about the size of one round trip.

## Book (Roth cash IBS+night, the sleeve on idle overnight cash, fixed capital)
- **At 2.5bp/side:** AZ1 −0.1..−0.4pp/yr (halves −2.1 / +2.2pp, t ≈ 0, dDD −3.7..−4.4pp); AZ2 −0.5..−0.8pp.
- **At 5bp/side** (the tier for large caps): −4.8..−6.1pp/yr, t −2.0.
- **Matched placebo** (same names on random nights 20-60 sessions away): 87-90th pct. The ex-night is not
  measurably better than an ordinary night in the same name once the sleeve's market exposure is in.
- **Verdict:** AZ1 0/4 and AZ2 0/4 checks pass. Both DEAD. The idle Roth cash stays in BIL (or V6, shadow).
