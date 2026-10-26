# Treasury frontier (2026-10-04, Study TME)

- **Treasury auction concession: KILLED** (Study TAC 2016-26: dip real, no tradable bounce, +2.4bp t 0.9). No variants.
- **Treasury month-end duration extension: VALIDATED on untouched 2002-15** (pre-reg 003e176, one look): TLT
  close(T-3) -> close(T), +32bp/month net, t 2.76, 13/14 years, duration-monotonic (TLT > IEF > SHY), move on T-1/T.
  The program's first non-equity, untouched-window pass. Real and scalable, but ~+4%/yr on deployed capital: small
  dollars at $2-25k. Not deployed. Stop Treasury variants; scaling it (leverage over 3 sessions) is the only open
  Treasury question. Russell Dec-2026 and signed dealer gamma are forward-shadow SPECS only
  (`research/drafts/shadow_*.md`); no paid data.
- **Month-end 60/40 rebalancing (Study RB6040, 2002-15): ARTIFACT.** The registered abnormal-return statistic was
  inflated by its own benchmark (other sessions of the month = the signal's inputs; 69% of the effect). Executable
  spread +27bp net, t 1.2, gone after 2015. Rule for all future studies: gate on executable raw P&L; never benchmark an
  event window against sessions that define the signal. No more month-end variants.
