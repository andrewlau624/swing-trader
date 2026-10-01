# Study AX (Round 20) — auction-share tilts on the night leg: DEAD; AU3 robustness R1/R2 hold (N 684)

Pre-registration: `round1_prose.md` Round 20 (commit df4f8c6, before any number). Data: Alpaca
`/v2/stocks/auctions` (SIP, free): opening and closing cross price + size for all 2,273 night-pick symbols,
2020-09..2026-09 (`research/sim/auction_hist_fetch.py`, ~27 min). Script `research/sim/auction_share.py`;
output `data/research/program/auction_share_out.txt`. Night returns from the official crosses (Study AW).
This is the free stand-in for closing-imbalance data. The user chose not to open a Databento account, so
AC stays parked.

## AX: trailing 20-session cross share of SIP daily volume (raw volume = adjusted / raw factor)

| | 2021-23 T1 / T2 / T3 | 2024-26 T1 / T2 / T3 | V7 $10k inc (halves) | t | placebo / shuffle |
|---|---|---|---|---|---|
| AX1 closing share (Bogousslavsky-Muravyev 2023) | +10.2 / +7.8 / +11.6bp | +14.5 / +14.1 / −3.3bp | +0.19pp (+1.09 / −1.08) | 0.06 | 52% / 45% |
| AX2 opening share (Berkman et al. 2012) | +2.5 / +14.8 / +11.6bp | +11.7 / +7.8 / +0.2bp | +1.34pp (+1.14 / +0.91) | 1.51 | 94% / 94% |

- **AX1 is DEAD.** It flips sign between halves, and the closing share mostly measures low volatility
  (Spearman vs vol20 −0.52).
- **AX2 is DEAD, and close.** It is positive in both halves at every size and book (+0.8..+1.3pp), but
  t 1.2-1.5, placebo 87-94% and DSR 0.03. Its terciles are not monotone, and the high-share tercile is the
  worst in 2024-26. The book gain comes from the tilt's shape, not from a clean gradient. Do not retest
  with a new window or cut.
- **Both are nearly orthogonal to TOW** (−0.05 / +0.06).

## R1: AU3 with TOW computed from the official crosses (report)
TOW from crosses correlates with TOW from vendor bars at +0.96. Terciles −13.2 / +12.9 / +19.1bp (2021-23)
and −10.3 / +0.9 / +22.9bp (2024-26). Book: V7 +2.9 / +2.6 / +2.7pp at $2.3k / $10k / $25k, t 2.5-2.6,
placebo 99%; Roth +2.7 / +2.4 / +2.4pp. **AU3's input is not a vendor-open artifact.** The live build
reads Alpaca SIP daily bars, which is the vendor version and backtests marginally better.

## R2: AU3 combined with other settings (report; V7 $10k, 2.5bp, auction returns)
- **Under the `moderate` profile's 15% name cap:** +4.40pp (+2.03 / +4.25), t 2.97, placebo 100%, dDD +1.4.
  A larger name cap gives the tilt more room. The concern in study_au_tow.md was the opposite: a hard
  post-tilt cap. This rules out a conflict with `moderate`.
- **On top of tilt v2:** +2.66pp (+0.94 / +3.13), t 2.53. Additive with v2.
