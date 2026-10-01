# Research prompt: more %/yr on a small account ($2-25k)

You are working in the `swing-trader` repo (the research data lives here, not on the server).
Read these before running anything:
- CLAUDE.md: priority = % return at small balances.
- NEXT.md: the top section, and the "Things already tested — do NOT redo these" table.
- research/drafts/study_round16_summary.md.
- RESULTS.md addenda 13, 16, 21, 29, 30, 31, 38, 39, 40.

## Goal
Raise the book's **%/yr after costs at $2.3k, $10k and $25k** (the taxable account), and grow the Roth (+$7.5k/yr).
Small size is an advantage here:
- No capacity limit in thin names, auctions or odd lots.
- Whole-share rounding and the $2,000 margin / intraday minimums are the binding constraints. Model them.
Report $100k/$500k as one capacity line only.

## Where things stand (do not rebuild)
- **Live:** night leg, IBS ETFs, QQQ/SMH noise leg, on Schwab, about $2.3k.
- **Built but waiting on gates:**
  - Conviction trade (`DAILY_LIVE_PROFILE=moderate10c`): +3.3pp/yr.
  - `DAILY_INTRADAY_MULT` (Schwab 4x intraday): ~+5pp together with conviction.
  - Overnight leverage (`lever_weight: 0.65`): re-arm at ~100 live night trades.
- **Roth: has never traded.** It is blocked until Schwab approves limited margin (`ROTH_LIMITED_MARGIN=yes`).
- **Round 16 is closed.** Magnitude sizing, confirmations, exits, more setups and more TQQQ weight are all dead
  (N = 642).

## Questions, in priority order (each one a pre-registered study)
1. **The Roth is idle money.** First quantify what the delay costs per month at $1-3k + $7.5k/yr.
   Then test the best Roth book that runs *without* limited margin: a cash IRA, settled cash only,
   no good-faith violations (T+1 settlement). Example: legs that alternate days, or the IBS leg only.
   If one clears the bar, spec it. A switch that starts the Roth now beats waiting for approval.
2. **Limit orders at the bid/ask for the night leg** (NEXT.md "Ideas not yet tested").
   - Model: close-auction limit buys and open-auction limit sells with a price cap. Measure fill rate and adverse
     selection from the SIP data.
   - Addendum 13 bounds the prize at ~+2pp CAGR. That is worth more at small size, where thin names cost nothing
     in impact.
3. **Night-leg pick quality where small size helps.**
   - Study U's foreign-ADR bucket: +41bp gross vs +17bp for US stocks, needs a proper classifier.
   - Study T's side note: mapped operating filers −11bp vs unmapped +15bp.
   - Pre-register each as a tilt or a filter. Thin names are fine at $2-25k: say where they break.
4. **Whole-share drag.** At $2.3k the IBS leg's per-ETF budget (~$380) and the night leg's 10% cap per name round
   badly.
   - Test: fewer, larger IBS picks; a cheaper look-alike per ETF (e.g. QQQM for QQQ, SPLG for SPY); a probe size.
   - Use Study R's method (whole vs fractional, by size).
5. **Multiple formation horizons / cross-sectional ranking** for the idle-capital problem (NEXT.md untested list).
   Only if it raises %/yr at $2-25k.
6. **A 0DTE options version of the conviction trade.** The convex payoff suits a 39%-win trend trade, and Schwab's
   API can trade options.
   - Price the data first (ThetaData Standard $80/mo, tick NBBO).
   - Say whether one QQQ 0DTE contract is even sizeable at $2.3k (premium vs 0.5 of equity).
7. **Tax at small size.** Short-term gains at 35% vs the Roth: which leg belongs in which account? Use the
   G4s wash guard rules.

## Rules (results that break them do not count)
- **Pre-register first:** append a dated amendment to research/drafts/round1_prose.md (variants, pass bars, what
  gets reported) and commit it BEFORE computing any result. Program N = 642; report DSR at the new N.
- **Select on 2016-23 (or 2021-23 for the night pool), judge once on 2024-26.** Report both halves.
- **Use raw prices** (`load_sim(raw_price=True)`).
- **Costs:** the measured ones (night buys ~−2.5bp, sells ~0bp; QQQ 0.13bp; TQQQ ~1.5bp), stressed at 2x.
- **Pass bar (SHADOW):**
  - increment > 0 in both halves at the stressed cost;
  - Newey-West t ≥ 2.0;
  - placebo ≥ 95th pct;
  - book max DD not worse by > 2pp;
  - 5y P(DD>50%) ≤ 5%.
- **Constraints:**
  - Taxable: short-term tax, and wash sales vs the Roth (`wash_guard: roth_first`).
  - Roth: no shorting, no intraday margin, settled cash.
  - Regular session only (`signals.regular_clock`).
- **Do not redo the dead list.**
- **Live code is untouched unless a variant passes.** Then build a switch, default off, with a kill rule and tests,
  and run `make test`.

## Deliverable
- One writeup per study in research/drafts/, and a NEXT.md entry for each. Commit and push each study.
- **A final ranked table:** idea | verdict | %/yr and $/yr at $2.3k / $10k / $25k | capacity line ($100k / $500k) |
  what live evidence would change it.
- Say plainly what failed.
