# Study ID (Round 31): the session after an insider purchase filing: ID3 (liquid names) PASSES -> SHADOW

Pre-registration: `round1_prose.md` Round 31 (commit b2cdc1c), before any 2024-26 number. Script:
`research/sim/insider_day.py`. Output: `data/research/program/insider_day_out.txt`, cross-print check
`insider_day_crosscheck_out.txt`. Program N 752 -> 755. Exploration (select data, logged before registration): L19-L20
in `outside_box_explore_log.md`.

**Trade.** An officer or director files a Form 4 reporting an open-market purchase (code P, >= $10k). In the first
session after the filing date, buy at the opening cross and sell at the closing cross. The sleeve is 0.45 x equity
of daytime buying power, split equally across the session's events (<= 10% of equity, <= 1% of ADV$ per name),
whole shares on the raw open, raw prior close >= $5. Events: SEC Form 3/4/5 data sets (2020-10 .. 2026-03).

## Results (V7 base, 2.5bp/side judged; book window 2021-02 .. 2026-03)

| variant | trades | net/trade (median gross) | inc $2.3k / $10k / $25k | halves 21-23 / 24-26 ($10k) | NW t | sign-flip | feature placebo | judge half alone | dDD | DSR (N 755) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ID1 all | 15,010 | +18.2bp (+9.9) | +11.5pp $265 / +14.4pp $1,441 / +15.9pp $3,984 | +12.8 / +6.9 | 2.62 | 99% | 100% | +17.2bp, t **1.18** | −2.0 | 0.23 | DEAD (g) |
| ID2 ADV $1-20M | 7,681 | +19.8bp (+11.4) | — | — | 2.95 | 100% | 100% | +14.4bp, t **0.86** | **−2.8** | 0.34 | DEAD (g, e) |
| **ID3 ADV >= $20M** | 7,329 | **+16.6bp** (+9.2) | **+7.8pp +$179 / +10.5pp +$1,048 / +11.9pp +$2,967** | +4.4 / +11.7 | **2.06** | 97% | 100% | **+19.9bp, t 2.31** | −0.2 | 0.105 | **PASS** |

ID3 by year (gross bp/trade): 2020 +70, 2021 +6, 2022 +18, 2023 +28, 2024 +12, 2025 +26, 2026Q1 +49. Correlation
with the noise leg −0.01. P(DD>50%) 0%.

**Placebo.** The same stocks on random non-event sessions lose about −8pp/yr in this sleeve, because small and
mid caps drift down intraday on ordinary days. The event sessions beat all 200 placebo draws.

**Crosses (registered check).** 500 random ID3 judge-half events matched Alpaca official opening and closing crosses
on every event. Median |panel − cross| is 0.0bp at both ends. Mean open -> close is +36.7bp on the panel and +36.5bp
on the crosses.

## Why SHADOW, not ADOPT
- **Cost decides it.** Break-even is 10.8bp/side. At tier_hi (10.4bp/side mean on these names) ID3 is −5pp/yr,
  and tier_hi also takes the base book from 40% to 24%. Live auction fills on the night leg have measured about 0bp
  (add. 29). The live number for MOO/MOC orders in $20M+ ADV names is the one fact that would settle it.
- **DSR 0.105 at N 755**, like every pass in the program, and the full-window t is 2.06, just over the bar.
- 2021 was weak (+6bp gross). ID1/ID2 died on the judge half, so the effect lives in liquid names only, which is
  the reverse of the small-account intuition.
- Live implementation needs a same-day Form 4 feed (the quarterly sets lag 1-3 months): EDGAR's daily Form 4
  filings, parsed after 17:30 ET for code P by officers/directors.

## What it would be worth (judged cost, ID3)
| | $2.3k | $10k | $25k | $100k / $500k |
|---|---|---|---|---|
| %/yr (book increment) | +7.8pp | +10.5pp | +11.9pp | capped by 1% of ADV per name: ~5 events a session × $20M+ ADV, so it scales past $500k |
| $/yr | +$179 | +$1,048 | +$2,967 | — |
