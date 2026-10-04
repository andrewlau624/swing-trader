# Contest hunt T3: pre-earnings long straddle t-3 -> t-1 (Gao-Xing-Zhang) — DEAD (both)

Pre-registered `round1_prose.md` (291f003, N 798 -> 800). Runner `research/sim/contest_straddle.py` (`bars`, `fetch`, `run`).
Events: Nasdaq earnings calendar 2023-01..2026-09, market cap >= $2B: 28,121; priced 25,542. Strike nearest the raw close of
t-4, earliest expiry >= t. Ask on the 15:51 NBBO of t-3, bid on the 15:51 NBBO of t-1, $0.65/leg.

| variant | n sel / judge | return on premium sel / judge | judge median | win judge | P(mean<=0) |
|---|---|---|---|---|---|
| T3a >= $2B | 13,392 / 12,150 | -30.4% / **-35.4%** | -28.9% | 6% | 1.00 |
| T3b $2-10B | 7,236 / 6,723 | -40.2% / **-44.4%** | -40.7% | 3% | 1.00 |
Every year -30..-45%. Market cap >= $50B (report): -13.7% (n 4,213).

Why: **the effect is there mid-to-mid, the spread eats it 13 times over.** On 21,744 events with two-sided quotes both days,
the straddle's mid rose **+1.5% on average** (median -0.7%, 46% up): about half the +3.3% GXZ found in 1996-2013. The
straddle's own bid-ask is **~20% of mid** (median), paid once in and once out. Median premium $588/contract also means
only 7% of events fit 5% of $2.3k. A 6% win rate after costs is low because of the spread, not a look-ahead: the mid
win rate is 46%.
