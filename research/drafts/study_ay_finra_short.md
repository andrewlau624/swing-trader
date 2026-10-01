# Study AY (Round 21) — FINRA daily short-volume ratio as a night-pick tilt: DEAD, both signs (N 686)

Pre-registration: `round1_prose.md` Round 21 (commit 6a0f535, before any number). Data: FINRA Reg SHO daily
short-sale volume, consolidated off-exchange (CNMS) files, public CDN, 1,499 sessions 2020-10..2026-09, no
missing day (`research/sim/finra_short_fetch.py`). Script `research/sim/finra_short.py`; output
`data/research/program/finra_short_out.txt`. Night returns from the official crosses (Study AW).

## Test
SVR5 = short volume / total volume over the 5 sessions before the pick (d excluded: the file is published after
the close). Coverage 94%. 2021-23 mean 0.479, sd 0.118. Nearly orthogonal to everything (TOW −0.03, vol20 −0.05,
depth −0.03, log price +0.08, log ADV −0.06). Two readings, both registered:
- **AY1, up-weight high SVR:** off-exchange "short" volume is mostly wholesalers filling retail buys, so a
  high ratio means a retail buying clientele.
- **AY2, up-weight low SVR:** Diether-Lee-Werner 2009 and Boehmer-Jones-Zhang 2008 find heavy shorting is
  informed, so those drops would bounce less.

## Result
| net per pick, 2.5bp/side | T1 (low SVR) | T2 | T3 (high SVR) |
|---|---|---|---|
| 2021-23 | +6.0bp | +10.2 | +6.7 |
| 2024-26 | +18.8bp | +17.2 | −10.7 |

- **Not monotone in the select half.** The 2024-26 high-tercile drop was never seen in 2021-23.
- **Book increments are noise:** −0.4..+0.4pp at every size, both books and both costs. NW t ≤ 0.6;
  sign-flip placebo 34-73%; feature shuffle 53-54%; DSR 0.003-0.004.
- **Verdict:** AY1 0/7 and AY2 0/7 checks pass. Both DEAD. The FINRA short ratio adds nothing to the
  night picks in either reading.
