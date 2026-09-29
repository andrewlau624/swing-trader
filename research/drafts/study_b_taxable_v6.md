# Draft addendum — Study B: taxable V6 (SPY/QQQ oversold overnight, idle money) on the RAW pool (2026-09-29)

    PYTHONPATH=. .venv/bin/python -m research.sim.taxable_v6_raw      # ~45 s
    output: data/research/program/taxable_v6_raw_out.txt

## Pre-registration
research/drafts/round1_prose.md (stamped `Tue Sep 29 01:33:38 PDT 2026`). This is a RAW-
pool restatement of addendum 27/31/39's taxable V6 (SPY/QQQ "either" trigger at 15:40,
close auction -> next open, idle money only, whole shares): A1t = the idle IBS half only
(the published form), A2t = + the night leg's unused cash (FOMC eves stay with the adopted
F3). Trigger nights 353 of 1,415 sessions; the 15:40 rule agrees with the close rule on
97.9% (the same as add. 27's published check).

## Results (book increment vs the shipped V7 raw pool, pp CAGR)

| row | cost | 2021-23 / 2024-26 | full | NW t (5 lags) |
|---|---|---|---|---|
| A1t idle-IBS only | tier | +0.63 / +3.07 | +1.79 | +2.12 |
| | tier_hi | +0.27 / +2.61 | +1.39 | +1.66 |
| A2t all idle overnight | tier | +0.62 / +5.11 | +2.76 | +2.21 |
| | tier_hi | +0.11 / +4.47 | +2.18 | +1.76 |

Gross overnight exposure in every variant <= 1.01x (the money was idle; no new margin).

Holdout 2016-20 (the returns book; the night leg = the raw 2020 rebuild at cap .10):
base 15.9/1.08; A1t 16.8/1.12 — dSharpe +0.04 (not worse). A2t has no holdout leg; A1t's
holds for the shared leg.

Placebo (same trigger count per symbol on random dates, 200 seeds, from the tier rows):
A1t realizes at the 53rd (2021-23) / 54th (2024-26) percentile of the placebo increments;
A2t at the 57th / 58th. The trigger's actual mean increment sits ABOVE the placebo MEAN
but far below the 95th percentile: the effect is largely "empty non-FOMC nights with idle
cash riding index overnight", not the oversold signal (add. 27 already called it post-hoc).

Record rows (the intent, not a gate): after-tax MC ($3k + $1k/mo, 35%): base median $117.1k,
A1t $122.2k, A2t $124.9k; P(DD>30%) 0.5-0.6%, P(DD>50%) 0% in every row (the taxable bound
<= 5% holds easily). Correlation of the leg's daily P&L with the night/IBS/noise legs:
0.21 / 0.03 / 0.04 (A2t 0.18/0.01/0.06) — no duplicate-leg problem. Deflated Sharpe at the
N=568 count: A1t 0.158, A2t 0.186 — both far below any adoption bar.

$/yr at tier: A1t +1.79pp after 35% tax = +$54 at $3k, +$1.79k at $100k; A2t +2.76pp =
+$54pp raw -> +$54 (per-year x35%) at $3k and ~$1.8k at $100k (tier_hi A2t +2.18pp: +$43/yr at $3k).

## Verdict: A1t / A2t = BORDERLINE. Nothing adopted.

What passes: the raw-pool A1t increment is positive in both halves at the tier (+0.63/+3.07)
AND at tier_hi (+0.27/+2.61), the holdout is not worse (dSharpe +0.04), and the tier row's
NW t is 2.12 (A2t 2.21) — at the tier.
What fails: the tier_hi NW t (1.66/1.76 < 2.0), and both fail the pre-registered placebo
>= 95th percentile in BOTH halves (53-58%). The increments cluster in 2024-25 (add. 27's
own diagnostic: the trigger's per-night edge lives in 2024-26 and not 2021-23), which is
the pattern the bar exists to reject. DSR(N=568) of the best row (0.16-0.19) rejects
adoption on its own.

This moves nothing: V6 (SPY/QQQ oversold overnight) remains in SHADOW (built log-only,
config `daily.oversold_mode: shadow`), and A2 funded from all idle overnight money is
what addendum 31/39 already scoped for the ROTH. What this study adds: the same shadow
should carry the TAXABLE variant's log line (SoA: taxable book explicit: the same 15:40
signal buys the idle IBS half instead of T-bills and logs `[oversold] tax` beside the Roth
line), plus a pre-registered kill rule: after 15 taxable shadow nights, mean net < 0 at 3bp
/side proposes auto-disable; the live gate is unchanged (the money would otherwise sit in
BIL).

Do NOT redo:
| idea | verdict | why |
|---|---|---|
| Taxable-book V6 (oversold SPY/QQQ overnight on idle money), raw pool tier/tier_hi | **borderline** | both halves positive but NW t 1.7-2.2 at tier and 1.7 at tier_hi, placebo 53-58th pct << 95, the gains concentrated in 2024-26; DSR 0.16-0.19 at N=568 (add. 27-31/39 unchanged, stays shadow) |

Variants: 2 (A1t, A2t). No survivors.
