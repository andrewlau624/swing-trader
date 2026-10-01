# Plan: close_imbalance (Study Lab-BB)

Written 2026-10-01. Lab-AZ's NOII data (top-100 Nasdaq + QQQ/TQQQ, 15:50-15:55, 2022-26) is on disk. Lab-AZ was
untestable (the near price is not published before 15:55; MISTAKES.md). Nothing about returns has been computed. The
only things inspected are the fields' availability (and that the near price is 0 before 15:55).
Pre-registration: `research/drafts/round1_prose.md`, Lab Round 26 (2 variants, program N 708 -> 710).

## The idea
The early closing-imbalance messages (15:50-15:55) give the size and side of the unmatched market-on-close interest.
A large BUY imbalance relative to the shares already paired means index and ETF buyers will have to lift the cross,
so the close prints above the 15:54 price. Buy before 15:55 and exit market-on-close (the cross print). Mirror for
sells. Source: Bogousslavsky & Muravyev (JFM 2023), closing-auction price pressure from passive flows.

## Exact rules
- Universe: Lab-AZ's fixed list (`data/daytrade/research/az/universe.json`).
- At close - 5:30 (15:54:30): each name's latest closing-cross message. r = signed imbalance / paired shares
  (BUY +, SELL -; 0 if paired = 0 or side N).
- Rank by r across names that day. Long the 5 highest with r > 0; short the 5 lowest with r < 0.
- Entry: the SIP NBBO 1s later (buy at the ask / sell at the bid). Exit: market-on-close = the official close (SIP
  regular daily close).
- Holding from ~15:54:31 to the 16:00 cross: the same stated exception to flat-by-15:55 as Lab-AZ.
- Variants: Lab-BB1 long + short; Lab-BB2 long only.

## Costs
As Lab-AZ: 1x = NBBO + 0.5bp in, 0.5bp out; 2x = NBBO + 1bp + half-spread again in, 1bp out.

## Pass bar, per variant
Mean net per trade > 0 at 2x in BOTH halves (split 2024-06-01), AND day-clustered t >= 2.0 at 1x, AND >= 95th pct of a
random-side placebo, AND the mean without the 20 best trades > 0 at 1x.


## Lab-BC (added 2026-10-01, a new variant; round1_prose.md Lab Round 27)
Lab-BB1 restricted to |r| >= 1.6742, the H1 75th percentile of |r|, chosen on H1 only. Judged on H2 (2024-06-03 ..
2026-09-30) alone: 2x net > 0, t >= 2 at 1x, placebo >= 95th, mean without the top 20 > 0.
