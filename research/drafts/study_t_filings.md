# Study T — SEC offering filings on the night picks: E3 DROP passes (barely) -> SHADOW

Pre-registration: `round1_prose.md` Round 6 (commit ff5e7b9). Script:
`research/sim/night_filings.py` (`fetch` pulls EDGAR into `data/research/night/edgar/`).
Output: `data/research/program/night_filings_out.txt` (run 2),
`night_filings_out_run1_etn_bug.txt` (run 1), `night_filings_diag.txt`.

## What was tested
V7 night picks 2021-26 (9,346). Event = an offering-type filing by the issuer accepted
between 16:00 ET on d-1 and 15:40 ET on d (point-in-time; EDGAR `acceptanceDateTime`
verified to be true UTC: read as UTC, 9.6% of filings after 18:00 keep the same
filingDate, vs 66% read as ET). E1 = 424B*, E2 = original S-1/S-3/F-1/F-3, E3 = either.
Symbol -> CIK mapping: 88% of symbols; after the operating-company and periodic-filing
filters, 68% of picks are "mapped".

## Bug found after run 1, fixed, both runs reported
FNGD / BULZ / BNKU are MicroSectors ETNs issued by Bank of Montreal, an "operating"
entity that files ~2,566 424Bs a year: they matched on almost every night (16 events).
KOLD (SIC 6221 commodity pool) likewise. The pre-registration intended ETPs excluded;
fix = drop SIC 6221 and issuers with > 100 424B/yr (8 CIKs).

| run | variant | excess 21-23 / 24-26 (bp, tier) | t | perm pct | book pp/yr 21-23 / 24-26 (tier) | verdict |
|---|---|---|---|---|---|---|
| 1 (bug) | E1 DROP | −59 / −114 | −2.04 | 1.5 | +0.25 / +1.13 | pass |
| 1 (bug) | E3 DROP | −38 / −150 | −2.38 | 0.7 | +0.21 / +1.77 | pass |
| **2 (fixed)** | E1 DROP | −45 / −118 | −1.76 | 3.4 | +0.38 / +0.86 | fail (t) |
| **2 (fixed)** | **E3 DROP** | **−24 / −158** | **−2.13** | **1.7** | **+0.34 / +1.50** | **PASS** (tier_hi: t −2.15, +0.48 / +1.64) |
| 2 | E2 DROP | +81 / −355 (n 14 / 13) | −1.25 | 7.5 | −0.04 / +0.64 | fail |
| 2 | all DOUBLE | — | — | — | ≤ +0.07 / −0.30 | fail |

n(E3) = 84 / 78. DOUBLE is structurally near-inert: the median pick already sits at the
0.10 name cap (a pre-registration flaw, noted, not rescued).

## Why this is SHADOW, not ADOPT (reading, not new variants)
- **Barely over the bar, after a bug fix.** t −2.13 vs a 2.0 bar, one of 6 variants, at
  program N = 607: a deflated Sharpe would not clear. E3 nests E1, so the two run-1
  passes were never independent.
- **Mostly 2024-26.** Excess by year (run 1 E3): 2021 **+61**, 2022 −91, 2023 −241,
  2024 −66, 2025 −79, 2026 −348. Median −80bp, 60% of event picks negative; dropping
  the 5 worst leaves −34bp.
- **It contradicts addendum 12** (headline "dilution/offering" bounced MOST, +38bp
  excess, t 1.6). Headlines tag the story days late and flag old deals; the filing
  window is the same session. Plausible, but unproven.
- **Mechanism is sensible:** a 424B3 resale prospectus (53 events, −96bp) or a fresh
  shelf (S/F-only, 27, −129bp) means registered supply that sells into the bounce.

## Dollars (the rule drops ~2.7% of picks; +0.34..+1.6 pp/yr on the book)
| equity | $/yr at +0.34pp | at +1.5pp | event order, % of 20d ADV (median / p95) |
|---|---|---|---|
| $2,300 | $8 | $35 | 0.000% / 0.001% |
| $25,000 | $85 | $375 | 0.002% / 0.010% |
| $100,000 | $340 | $1,500 | 0.009% / 0.042% |
| $500,000 | $1,700 | $7,500 | 0.047% / 0.209% |
Capacity is not the constraint (pick ADV floor $10M, median $43M). A drop rule costs
nothing to run and only removes trades.

## Shadow plan: no live code needed
EDGAR acceptance times are permanent, so the out-of-sample check is a rerun: pick up
live/paper night picks after 2026-09-29 and score E3 with this script. ~2.7% of
~1,600 picks/yr ≈ 45 events/yr → **~100 out-of-sample events by late 2028**. Adopt if
the OOS excess is negative with the same bar. A live pre-trade EDGAR check at 15:40 is
~1 request per pick (well within SEC's 10/s): easy to build if/when adopted.

## Side observation (NOT pre-registered; its own study if pursued)
Mapped picks (operating companies filing today) net −10.6bp/trade at tier; unmapped
(delisted, ETPs, foreign unmapped) +14.6bp. The leg's edge may sit disproportionately in
names that later delisted or in ETPs. Could be survivorship in the mapping, or real.
Worth a pre-registered look before anyone reads the leg's edge as "small caps in general".
