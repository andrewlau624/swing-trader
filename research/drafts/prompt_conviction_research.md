# Research prompt: make the conviction trade (catching big intraday swings) great

You are working in the `swing-trader` repo. Read CLAUDE.md, NEXT.md (the "Dead (do not redo)" table),
RESULTS.md addenda 6, 8, 19, 24, 40 and research/drafts/study_ae_big_swings.md before anything else.

## Goal
Grow the book by catching big intraday swings with only high-confidence signals, entries and exits set by
rule, and flat by the close, using daytime capital the overnight legs leave idle. Improve the one intraday
edge that already survived, the **conviction trade**, instead of inventing a new strategy from scratch.

## What exists (do not rebuild)
- **Noise leg** (live): QQQ (+SMH), decisions every 30 min from 10:00, a per-minute noise band from 14-day
  |close/open| averages (`signals.noise_sigma/noise_bounds`), long above / short below, exit back through
  the band or VWAP, vol-targeted to 2%/day, cap 1.5x, flat by the close. About +2bp/day planning edge.
- **Conviction trade** (built, `conviction_mode: shadow`, `research/sim/book.py: breakout_days`): only the
  day's FIRST noise-band breakout, only if strength ≥ 0.341σ (fixed 2016-23 median). TQQQ for up, SQQQ for
  down. Out on a return inside the band or through VWAP, else 15:57. 0.5 of equity; ~70 trades/yr; wins 39%;
  +6pp/yr to the book on raw prices; per-trade OOS t only 1.2-1.4; correlation with the book about −0.02.
  Kill rule: 60 round trips.
- **Study AE (2026-09-30):** a 3σ open→close swing is 2-2.7x likelier after a big gap, a wide range
  yesterday, or heavy volume yesterday, **equally up and down**. Size is predictable; direction at the open
  is not.
- Costs measured live: QQQ spread 0.13bp (the sim uses 0.5bp/side), TQQQ ~1.5bp/side, night auctions ~0bp.

## The user's ideas, turned into questions (each one a pre-registered test)
1. **Only very confident signals.** Map breakout strength to expected value, not win rate: EV per trade by
   strength bucket, held out. Then test confirmations measured AT the breakout minute:
   - market breadth (share of NDX-100 names above their own VWAP / noise band);
   - SMH/SPY/IWM breaking the same way;
   - NQ futures leading QQQ;
   - relative volume in the breakout bar;
   - VIX/VIX9D level and change;
   - time of day.
   A confirmation counts only if EV rises monotonically across its buckets in 2016-23 and holds in 2024-26.
2. **Size by predicted magnitude (the Study AE link).** The breakout rule profits from SIZE, not from
   guessing direction, and size IS predictable at the open. Test conviction weight × f(QQQ gap_z, yesterday's
   range_z, yesterday's rvol, VIX), fixed buckets, with the drawdown bound below.
3. **Limits, stops, cash-out targets.** Against the current band/VWAP exit, test:
   - a fixed stop at kσ;
   - a take-profit at mσ;
   - half off at the target with the rest on the band exit;
   - a limit entry on the first pullback to the band (fill-or-skip).
   Prior: fixed targets and trailing exits lost on every earlier leg (add. 3, 13) because they cut the winners
   a 39%-win trend trade lives on. State it and test it anyway.
4. **Live and streaming signals, faster decisions.** Compare 30-min, 5-min, 1-min, and a tick-level trigger
   (Schwab streamer). Add. 24 found a 1-minute fill delay ruined the SOXL ORB, so measure the latency
   sensitivity: EV at entry delays of 0 / 5 / 15 / 60 s. Build a free recorder of Schwab L1 quotes and the
   NASDAQ book for QQQ/TQQQ/SMH/SPY now, so tick-level tests have data in ~3 months.
5. **More setups, still rare.** Second breakouts after a failed first one; breakouts in SMH, IWM, SPY with a
   one-trade-per-day cap across them (correlated duplicates count as one bet). Anything with ≥ 0.7
   correlation to the QQQ conviction trade is the same bet.
6. **Instrument.** TQQQ vs QQQ on margin vs MNQ (60/40 tax, no wash sales, contract size binds below ~$30k)
   vs 0DTE QQQ/SPX calls and puts (convex payoff suits a 39%-win trend trade, but it needs options data:
   price it first and say what it costs).
7. **Extra capital.** How much daytime buying power can the conviction trade take (0.5 → 1.0 → 2.0 of
   equity; Schwab ~4x intraday margin, add. 40) before P(DD > 30%) or P(DD > 50%) breaks the bounds?

## Rules (this program's discipline; results that break them do not count)
- **Pre-register first:** append a dated amendment to research/drafts/round1_prose.md (variants, pass bars,
  what gets reported) and commit it BEFORE computing any result. The program is at N = 619 variants; report
  DSR against the new N.
- **Select on 2016-23, judge once on 2024-26.** Report 2021-23 and 2024-26 separately.
- **Pass bar (SHADOW):**
  - increment > 0 in both halves at the stressed cost (2x measured);
  - Newey-West t ≥ 2.0;
  - placebo ≥ 95th pct (same entry times, random direction or random days);
  - book max DD not worse by > 2pp;
  - P(DD > 50%) ≤ 5%.
- **Money at several sizes:** today's (~$2.3k), $25k, $100k, $500k. Check capacity at each (% of the
  instrument's minute volume at the entry bar).
- **Constraints:**
  - Taxable: short-term tax, wash sales vs the Roth, which trades TQQQ/SQQQ/SOXL.
  - Roth: no shorting, no intraday margin.
  - Sessions: regular session only; take times from `signals.regular_clock`, never a broker clock.
- **Do not redo the dead list** (ORB on ETFs and stocks, gap-and-go, gap fades, in-band fades, last-half-hour
  momentum, single-stock noise, HFT scalping, direction at the open from gap/range/volume, news sentiment,
  options-calendar timing).
- **Live code is untouched** unless a variant passes; then spec a config switch, default off, with a kill rule.

## Deliverable
- One writeup per study in research/drafts/, and a NEXT.md entry for each.
- A final ranked table: idea | verdict | $/yr at the four sizes | what live evidence would change it.
- Say plainly what failed. The best outcome may be "turn the existing conviction trade on and size it by
  predicted magnitude"; that is a fine answer.
