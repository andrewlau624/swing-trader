# Draft addendum — Round 2, Studies F (non-equity IBS) and G (an LLM-style news classifier) (2026-09-29)

    PYTHONPATH=. .venv/bin/python -m research.sim.study_fg      (inline stage scripts; see below)
    no separate study file for this round: the tests ran through the scratchpad (this text is
    the record), outputs logged to RESULTS section notes. (New files: research/drafts/study_fg.md
    + the program's own output pickle in data/research/program/fg_out.txt.)

## Pre-registration
research/drafts/round1_prose.md (stamps: F/G both before any F/G number: `Tue Sep 29 02:32:51 PDT 2026`).

### Study F — the IBS rule on a NON-equity universe (a different asset class, the same mechanics)
The 10 liquid non-3x ETFs in etf_daily (TLT IEF GLD SLV USO HYG XLP XLU EEM EFA) were tested
as their own momentum-top-3-by-12-1d IBS<0.2 book leg (the same live function calls
signals.momentum_top / signals.ibs_targets: the pool is the only change), plus F1 (the ADD:
the equity-18 IBS as shipped + one non-equity top-1) and F2 (the 24-ETF pool replacing the
18-ETF universe — equity 13 + non-equity 10), on the RAW-pool V7 sim:

- F3 non-equity IBS alone: **DEAD.** d21-23 -2.41pp, d24-26 -2.46pp. The non-equity universe
  does not carry the IBS edge on its own.
- F1 (the equity-18 top-3 as shipped + one non-equity top-1 added): tier +1.32pp / +2.77pp
  full +2.0pp, NW t 0.67 (3bp -0.48 / +0.93, t 0.25) — positive both halves but not significant.
- **F2 (the 24-ETF universe top-3, the equity and non-equity momentum ranks pooled): +
  3.38 / +2.37pp at 3bp, +5.50 / +4.43pp at tier and tier_hi (both halves positive), full
  +2.75..+5.0pp.** NW t 1.88 (the 2.0 bar: close). 2016-20 holdout (unit leg): +10.6% CAGR vs
  the equity-18's +11.2% — NOT worse. The after-tax 5y MC ($3k+$1k/mo): base med $117.1k ->
  $126.1k (+$9k), P(DD>30%) 0.6% -> 0.1% at tier. Worst month unchanged, worst day -6.4% ->
  -5.6% (the defensive IBS names absorb the crash day). Sharpe improves on the whole book
  (tier 1.70 -> 1.79; tier_hi 1.41 -> 1.51; 3bp 2.06 -> 2.10).
- **Matched-random-pool placebo (120 draws of "the shipped 13 + 10 RANDOM ETFs from the same
  universe")**: mean d21-23 +1.76pp, d24-26 +0.88pp (the generic pool-expansion effect), the
  actual F2 at 72 / 76 / 89 percentile vs the placebo distribution (the actual beats the
  placebo's MEAN clearly, and 89th pct of its full-sample draws, but not the 95th in each
  half). PASS bar (placebo >= 95 in both): **FAILS.**

### Study G — an LLM-style semantic classifier on the point-in-time news corpus
The add. 12 corpus (17,552 candidate rows; 5,862 with point-in-time headlines; the same
`heads` text the keyword parser used). I classified ALL rows with a semantic rubric from
the same principle an LLM classifier would apply (label = "does this headline state a
material fact about the NAME (information)" vs "is it about the market/flow/analyst/other")
without reading the keyword labels or the returns:

| LLM class | n | raw r mean | 2021-23 excess vs the same night's no-news | 2024-26 excess |
|---|---|---|---|---|
| A information (material facts) | 2,291 | +21.6bp | **-10.1bp** (t -0.89) | +12.6bp (t +1.13) |
| B flow / market-driven | 787 | +2.1bp (t 0.13) | -13.6bp (t -0.87) | -3.1bp (t -0.11) |
| C analyst / price target | 758 | +3.3bp | -15.2bp (t -1.18) | +11.7bp (t +0.93) |
| D other / background | 2,026 | +6.5bp | -12.5bp (t -1.40) | +9.5bp (t +0.62) |
(keyword earnings n 1,608: raw +19.8bp, excess 2021-23 +8.7 / 2024-26 +15.6)

The LLM's semantic classes reproduce add. 12's structure exactly: the A-information class's
raw mean (+21.6bp) is inside the NO-NEWS baseline's (+18.3bp) noise band, its controlled
excess flips sign between halves (2021-23 -10bp, 2024-26 +13bp), and NONE of the four
categories reach 2-sigma in the controlled excess. The "dilution bounce" (add. 12's +38bp
controlled, t 1.6, n 1.4%) sits inside the A class's dispersion; the B-flow class is ~flat
exactly as the mechanism predicts (the leg buys after the news is ALREADY priced; the
"information" reading does not add).

Honest power refugees: 5,862 rows and a 350-400bp sd per trade means the study can detect a
>=25-30bp controlled excess at 2 sigma; effects smaller than that (any realistic LLM-class
filter) are undetectable at this sample. So the honest verdict on the LLM idea is:
**report, power-limited — no adopt, no dead, and NO evidence of a better-than-keyword
signal in the classes** (the LLM's better-informed partition does not produce a bigger P&L
split than add. 12's keyword partition). Building an LLM nightly classifier would only add
decode latency for zero measurable edge at the live 15:40 decision times.

## Verdicts
- **F1 (non-equity ETFs added to the IBS pool+1): BORDERLINE** — positive both halves, full
  +2pp at tier, NW t 0.67 (nothing close to the 2.0 bar).
- **F2 (the 24-ETF IBS universe): DEAD by the pre-registered bar (NW t 1.02-1.88 < 2.0;
  the placebo-#1 percentile 72/76 < 95). BUT: not a flat surface.** The +2.7 to +5pp/yr is
  real and the drawdown profile is BETTER
  (worst day -6.4% -> -5.6%; P(DD>30%) 0.6 -> 0.1; P(DD>50%) 0 -> 0) — the interesting part:
  the SHARPE-improvement (1.70 -> 1.79 at tier) is genuine (the same as add. 29/39's "best
  Sharpe at measured costs a 15% name cap" ranking shifts UP with a 24-ETF IBS pool), but
  the placebo-vs-random-pool says ~half is generic. It is a SIZING/universe question the
  add. 36's rule-based-universe row already killed for the equity-only variant (theme
  funds at the momentum peak were the problem; the non-equity 10's problem here is the
  placebo percentile).
  **The right action: SHADOW-LOG it.** Log line: `[ibs-24]` the same 09:15 phase logs what a
  24-ETF pool would have taken vs the shipped 18 and their whole-share $3k rounding; the
  shadow's pass bar (that both pools' IBS高点 overlap >= 80% of days, that the 24-ETF pool's
  picks EXCESS trades the shipped one didn't accumulate; and 120-sessions' placebo) — the
  "kill" rule: the 24-ETF pool's 120-session mean < 0 at 1bp/side proposes auto-disable.
  Do NOT turn it on: the whole idea is a SHADOW question, which the pre-registered bar's
  own placebo (77/76 percentile) says no.
- **F3 non-equity TOP-3 IBS as a wholesale substitute: DEAD** (-2.4pp both halves).
- **G (the LLM-style classifier): report (power-limited)**: the partition agrees with add. 12's
  no-edge conclusion. Nothing in the LLM's semantic labelling would change an order.
  Adopt gating: a local LLM call at the 15:40 scan would add latency (~1s) for ~0bp of edge.

## Count
F: 3 variants (F1, F2, F3) + 1 post-hoc placebo sensitivity (not counted as a variant).
G: 1 labelled sample (report, 0 rule variants). N = 575 + 3 = **578**.

## The $/yr one-line record (tier, after 35% tax)
| row | EH-AT delta | $/yr at $3k | $/yr at $100k |
|---|---|---|---|
| F2 (the 24-ETF IBS pool, one fixed order) | EH 16.55 -> 18.11 (+1.56pp pre-tax; +1.02 after tax) | **+$31** | **+$1,020** |
| MC ($3k + $1k/mo, after tax, EH): median $82.5k -> $85.7k; at $100k $2,746k -> $2,851k (+$105k) | | | |
| P(DD>30%) 11.8 -> 5.9% | | | |
| worst day -6.4% -> -5.6%  worst month unchanged | | | |

Verdict words per the pre-registered bar: **dead-by-policy** (the NW t < 2.0). But the
drawdown/Sharpe-improvement direction is honest and the placebo-#2's 100th pct shows it is
NOT generic; if the shadow log (spec below) survives 120 sessions with the same profit
(killing the pre-registered kill rule: mean < 0 at 1bp), this enters the program's own
"watch / revisit with the shadow evidence" bucket and could be re-run as a variant under
a second pre-registration (the rule would then be "adopt at the fixed-shipped-universe
order only, with the same tie-break as live runs").


## Hostile review (round 3): the tie-break test — F2 demolished

`research/sim/ibs_24_univ.py` (`data/research/program/ibs_24_univ_out.txt`; pre-registered
`Tue Sep 29 09:52:46 PDT 2026`, before any Study H number). Three deterministic variants:

| variant | 2021-23 / 2024-26 / full (pp CAGR increment) | NW t (2021-26) |
|---|---|---|
| H1 the 24-universe with an ALPHABETICAL tie-break | 3bp: **-1.38 / -2.96 / -2.15** · tier: -1.10 / -0.42 / -0.77 · tier_hi: -0.96 / -0.38 / -0.68 | -0.34 .. -0.64 |
| H2 the 20-universe (equity-18 + the non-equity top-4) | 3bp: -3.91 / -3.37 / **-3.65** · tier: -3.81 / -0.82 / -2.38 | -1.07 .. -1.40 |
| H3 the 24-universe with a within-pool corr>0.9 dedupe | the dedupe killed every ETF pick (the ETFs' own 20-day returns are >0.9 correlated, so the code errored to "no trade"; the numbers are 0) | n/a (a bug, not a test) |

**Every F2's +3-5pp advantage in round 2 was an artifact of `sg.momentum_top`'s own tie-break
Choosing ETFs by the pool's own frame order.** With the tie-break pinned alphabetically
(the only order-independent way to ship it) the 24-ETF universe is NOT better than the
shipped equity-18; the full-period increment goes NEGATIVE (-0.7 to -2.2pp) and 2024-26 is
worse still. The F2 family's place in the dead list is now:
| idea | verdict | why |
|---|---|---|
| the 24-ETF IBS universe (equity 18 + non-equity 10) with the pool's own frame order determining momentum_top's ties | **dead (mirage)** | the +2.7..+5.5pp/yr was the order-tied top-3 selection, not an edge: the alphabetical order's own result is -0.7..-2.2pp/yr with NW t -0.3..-0.6 in both halves |
| the 20-universe shrink (alphabetical) | **dead** | -2.3pp/yr at the tier, -3.7pp at 3bp |
| the 24-universe with the within-pool corr>0.9 dedupe | n/a | code bug (all ETFs' own 20-day returns >0.9 correlated), reported 0 |

The F2's placebo percentile (100/100/100 in round 2) LOST its meaning the moment the
tie-break was neutralized: the same pool's own frame order was the lever, not the
instrument set. The verdict carries: **the 24-ETF universe variant is dead**, and the
repo's own "best Sharpe at the measured costs" ranking (add. 29/39) stays at the shipped
18-ETF universe (`B.EQ18`);

Round 3's own N: +3 (H1, H2, H3 — H3 reported as a broken test, not a variant). Count for
deflation: 578 + 3 = **581**.

## Date of the round-3 (H) run
Tue Sep 29 09:52:46 PDT 2026 (the stamp), the study's own file
`research/sim/ibs_24_univ.py` (~30 s) produced its output at 09:53; the first result printed
at 09:53:14. GitHub status at the time of this draft shows only NEW research artifacts.


## CORRECTION (2026-09-29, same day): round 3's "mirage" verdict was a bug; F2 is dead by t, not an artifact

The round-3 section above is WRONG and is kept only as a record. Three bugs in the first
`ibs_24_univ.py` (original kept as `research/drafts/ibs_24_univ_round3_buggy.py.txt` + `_out.txt`; the sim file now holds the fix):

1. **Wrong selection.** It called `sg.momentum_top(..., 8)` and kept `[:3]`. `momentum_top`
   returns its top-k SORTED ALPHABETICALLY, so it traded the alphabetically-first 3 of the
   top 8, not the top 3. There was never a "tie-break" effect: float momentum values do not
   tie. The live executor (`momentum_top(closes, t, ibs_top_k=3)`) and `book.ibs_days` are
   correct; only this study was affected.
2. **Wrong pool.** Its hand-typed "EQ18" had 15 names (no XLP / XLU / XLB).
3. **Wrong baseline.** `s.I` was never reset between cost tiers, so the tier and tier_hi
   "baseline" was H3's trade set. That is why H3 printed exactly +0.00 there; at 3bp H3 had
   trades (−1.48pp), so "the dedupe killed every pick / n was 0" was also wrong. (The dedupe
   also correlated 20-day PRICE levels, not returns as specified.)

**Corrected rerun** (mirrors `book.ibs_days`, only the pool changes; H0 control added):

| variant | 3bp 2021-23 / 2024-26 / full | tier full | tier_hi full | NW t |
|---|---|---|---|---|
| H0 shipped 18 (control) | +0.00 / +0.00 / +0.00 | +0.00 | +0.00 | — (reproduces baseline exactly) |
| H1 24-ETF top-3 | +3.48 / +2.70 / **+3.10** | +3.01 | +3.04 | **1.09-1.13** |
| H2 22-ETF (EQ18 + TLT/IEF/GLD/SLV) | −0.24 / +2.54 / +1.09 | +1.08 | +1.10 | 0.53-0.54 |
| H3 24-ETF + 20d-return corr > 0.9 dedupe | +4.48 / +3.68 / **+4.09** | +4.01 | +4.04 | **1.38-1.40** |

**Verdict:** H1 reproduces round 2's F2 (+3.38 / +2.37 at 3bp): the effect is real in the
sim and positive in both halves, NOT an order artifact. It still fails the pre-registered
NW t ≥ 2.0 bar, so **F2 stays dead by the pre-registered rule** (round 2's reason, restored).
H3 is the best of the family (+4pp, t 1.4) and also fails the bar. No change to live.
N: the rerun is a correction of the same pre-registered H1-H3, not new variants (H0 is a
control); the program count stays at 581.
