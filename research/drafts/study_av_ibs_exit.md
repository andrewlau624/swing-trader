# Study AV (Round 19) — the IBS leg's exit: hold until a state exit — DEAD (N 680)

Pre-registration: `round1_prose.md` Round 19 (commit dc53fcb, before any number). Script:
`research/sim/max_edge.py` (Study AV half). Output: `data/research/program/max_edge_out.txt`.
Sources: Pagonidis, "The IBS Effect" (NAAIM 2014: IBS > 0.5 / 0.8 exits); the
[idousse/mean-reversion-strategy](https://github.com/idousse/mean-reversion-strategy) repo (read, clean, costed:
exit on a close above yesterday's high).

## What was tested
Entry unchanged (month's momentum top-3 of the 18 ETFs, IBS < 0.2 → buy at the next open). The
shipped leg re-holds only while IBS < 0.2. The variants keep a name until a state exit (5-session cap,
or the name leaves the top-3), open → open:
- AV1: sell at the next open after the first close with IBS > 0.5.
- AV2: sell at the next open after the first close above the prior session's high.

## Results (2.5bp/side night cost judged; tier_hi reported; fixed capital)

| | unit IBS leg %/yr 2016-20 / 21-23 / 24-26 | V7 $10k inc (21-23 / 24-26) | NW t | placebo | Roth $10k inc |
|---|---|---|---|---|---|
| shipped | +12.4 / +14.9 / +19.2 (1,386 leg-days) | — | | | |
| AV1 IBS > 0.5 | +14.3 / +1.7 / +16.8 (1,797) | **−5.90pp** (−7.13 / −1.55) | −2.30 | 2% | −5.39pp |
| AV2 close > prior high | +23.4 / +11.5 / +24.8 (3,028) | −0.82pp (−2.60 / +1.96) | −0.13 | 45% | −0.76pp |

Same picture at $2.3k / $25k and at tier_hi (AV1 −4.5..−5.9pp; AV2 −0.7..−1.7pp).

## Verdict: DEAD
- **AV1 loses in both halves (t −2.3).** Holding the bounce past the first session adds day-session
  exposure after the overnight part of the reversion is spent. This agrees with the repos and papers'
  own note that IBS returns fall as the hold gets longer, and with add. 27: "the edge is in the overnight gap".
- **AV2 is a different leg, not a better exit.** It raises the unit leg's return (more than double the
  leg-days, much more time in the market), and its 2016-20 holdout is +11pp/yr (t 2.0). But the
  equal-weight budget is then spread over more simultaneous names. Inside the book it loses in 2021-23 and
  is t −0.1 overall. At most it is a "more IBS exposure" dial, and the program already has that dial
  (leg weights / Kelly, add. 31-32).
- Keep the shipped "hold while IBS < 0.2" exit.

$/yr at $2.3k / $10k / $25k (V7, 2.5bp): AV1 −$126 / −$590 / −$1,478; AV2 −$38 / −$82 / −$205.
Capacity is not the issue (IBS ETFs scale to low single-digit $M).
