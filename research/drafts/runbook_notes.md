# Event-runbook session notes (Round 33; runbook research/drafts/prompt_event_runbook.md)

Session start 2026-10-02. Program N at start: 757 (Round 32, round1_prose.md). Select data only until pre-registration.
Tested in order from the runbook menu; at most 6 ideas.

---

## 1. Cluster insider buys (menu row 1) — Study EV1, track FREQUENT
Event: `insider_buys()` (SEC Form 345 sets), `X[X.insider]`. Rule: per symbol, chain filings whose consecutive
filing dates are <= 5 days apart (distinct accessions); each chain of 2+ filings emits one event at the
**completion date** (the last filing in the chain), so it is known only once the cluster is visible. File
`data/research/program/events_cluster.parquet` (snippet C). Trade: buy the opening cross / sell the closing cross
of the first session after the completion date; ADV >= $20M (runner default).

Select-half (<= 2023-12-31), ADV >= $20M:
```
events 9787 -> trades 780  (195 per year)
net per trade +27.7bp  median +12.3bp  hit rate 53%  t +2.42
by year: 2020: -42.0bp (n 29)  2021: +21.2bp (n 198)  2022: +22.7bp (n 284)  2023: +45.2bp (n 269)
TRACK FREQUENT (>= 100/yr): net >= +10bp, hit >= 50%, t >= 2: MEETS -> may pre-register
```

Why it should work (before registering):
- **Who is on the other side:** at the opening cross, liquidity providers (market makers) and early sellers; the
  premium is paid later in the session by attention-limited buyers — screeners, alert apps and newsletters that
  surface "multiple insiders bought" Form 4 lists after the open.
- **Why they keep paying:** a cluster of two or more distinct officer/director open-market purchases is a stronger,
  costlier-to-fake signal of private information than a single buy, and attention diffuses slowly, so the
  open-to-close drift repeats. Same mechanism as ID3, concentrated on the strongest filings.
- **Why big funds don't take it:** capacity is small and manual (one session, modest-ADV names, whole-share lots);
  the per-event edge is tens of bp, and parsing Form 4s daily across thousands of issuers is operational overhead
  a large book cannot size into. The event is also short-horizon and cannot absorb size without moving the cross.

(If judged DEAD, this section still stands as the pre-registered reasoning.)

**Judge (2024-01..2026-03), pre-registered commit f4d19c5, N 758: DEAD.**
```
== EV1 cluster insider buys: 1415 trades; per trade gross +32.5bp (median +15.9); net 2.5bp/side +27.5; by year 2020:-37.0 2021:+26.2 2022:+27.7 2023:+50.2 2024:+35.3 2025:+19.9 2026:+63.4
  $10k 2.5bp: NW t +2.61  sign-flip 99%  feature placebo 100%  dDD +0.3pp  P(DD>50) 0.0%  DSR 0.218 (N 758)  corr(inc, noise) -0.04
  judge half alone: event net +27.3bp, daily-sleeve NW t +1.85
  -> DEAD
```
Died **only** on the pre-registered judge-half bar (g): the judge-half daily-sleeve NW t is +1.85 < 2 even though the
event-level net is +27.3bp (the mean holds; the t fails). Everything else passes (halves positive at all three sizes,
sign-flip 99%, feature placebo 100%, DSR 0.218). Verdict copied as printed: DEAD.

Writeup: research/drafts/study_ev1_cluster_insider.md.

---

## 2. First insider purchase in 2+ years (menu row 2) — explored-dead
Event: `insider_buys()`, `X[X.insider]`, real tickers only (`^[A-Z][A-Z0-9.]*$`). Rule: per symbol, an officer/
director open-market purchase whose filing date is >= 730 days after the previous such filing (or the first ever).
File `data/research/program/events_firstbuy.parquet`. ADV >= $20M, 1-session hold (runner default).

Select-half (<= 2023-12-31), ADV >= $20M:
```
events 2973 -> trades 562  (140 per year)
net per trade +23.9bp  median +11.4bp  hit rate 52%  t +1.66
by year: 2020: +86.7bp (n 33)  2021: -22.4bp (n 203)  2022: +66.4bp (n 187)  2023: +19.3bp (n 139)
TRACK FREQUENT (>= 100/yr): net >= +10bp, hit >= 50%, t >= 2: FAILS -> stop, record as explored-dead
```
No pre-registration (explore FAILS). 2024-26 never read. One line: t 1.66 < 2 on the select half; not tested.

---

## 3. SC 13G originals: a new passive 5% holder (menu row 3) — explored-dead
Event: EDGAR quarterly full index (`full_index`), form exactly `SC 13G` (snippet A), filer CIK with <= 50 such
filings a quarter (drops banks/funds), CIK -> current ticker via `company_tickers()`. File
`data/research/program/events_13g.parquet`. ADV >= $20M, 1-session hold.

Select-half (<= 2023-12-31), ADV >= $20M:
```
events 21545 -> trades 4082  (1020 per year)
net per trade +9.6bp  median +8.1bp  hit rate 51%  t +1.82
by year: 2020: -67.3bp (n 92)  2021: -7.5bp (n 1626)  2022: +5.6bp (n 1322)  2023: +48.1bp (n 1042)
TRACK FREQUENT (>= 100/yr): net >= +10bp, hit >= 50%, t >= 2: FAILS -> stop, record as explored-dead
```
No pre-registration. 2024-26 never read. One line: net +9.6bp (< 10) and t 1.82 (< 2); not tested.

---

## 4. SC 13D/A amendments: an activist adding shares (menu row 4) — explored-dead
Event: EDGAR quarterly full index, form exactly `SC 13D/A` (snippet A), <= 50 filings/quarter per CIK, CIK ->
current ticker. File `data/research/program/events_13da.parquet`. ADV >= $20M, 1-session hold.

Select-half (<= 2023-12-31), ADV >= $20M:
```
events 14825 -> trades 2077  (519 per year)
net per trade -21.1bp  median -21.8bp  hit rate 45%  t -2.82
by year: 2020: +49.7bp (n 137)  2021: -33.4bp (n 729)  2022: -22.1bp (n 605)  2023: -21.2bp (n 606)
TRACK FREQUENT (>= 100/yr): net >= +10bp, hit >= 50%, t >= 2: FAILS -> stop, record as explored-dead
```
No pre-registration. 2024-26 never read. One line: net −21.1bp, t −2.82 (sign wrong); not tested.

---

## 5. 8-K text "strategic alternatives" (menu row 5) — explored-dead
Event: EDGAR full-text search (`fts_years`) for the exact phrase "strategic alternatives" in form 8-K, 2020-2026;
ticker from the hit display name (`ticker_of`, first ticker). File `data/research/program/events_stratalt.parquet`.
ADV >= $20M, 1-session hold. (Expected track was rare/big, but it selected > 100/yr names, so the tool applied the
FREQUENT gate; the rare-deal gate is not used when the event flow is this high.)

Select-half (<= 2023-12-31), ADV >= $20M:
```
events 2233 -> trades 424  (106 per year)
net per trade +11.2bp  median +12.9bp  hit rate 52%  t +0.71
by year: 2020: +25.4bp (n 26)  2021: -20.9bp (n 149)  2022: +50.6bp (n 124)  2023: +7.4bp (n 125)
TRACK FREQUENT (>= 100/yr): net >= +10bp, hit >= 50%, t >= 2: FAILS -> stop, record as explored-dead
```
No pre-registration. 2024-26 never read. One line: t 0.71 (< 2), unstable by year; not tested.

---

## 6. 8-K text "special dividend" (menu row 6) — explored-dead
Event: EDGAR full-text search for the exact phrase "special dividend" in form 8-K, 2020-2026; ticker from the hit
display name (first). File `data/research/program/events_specdiv.parquet`. ADV >= $20M, 1-session hold.

Select-half (<= 2023-12-31), ADV >= $20M:
```
events 1491 -> trades 348  (87 per year)
net per trade -10.6bp  median -3.4bp  hit rate 49%  t -0.60
by year: 2020: +6.6bp (n 18)  2021: -34.7bp (n 104)  2022: -18.8bp (n 107)  2023: +15.2bp (n 119)
TRACK SEMI-RARE (24-100/yr): net >= +50bp, hit >= 55%, t >= 2: FAILS -> stop, record as explored-dead
```
No pre-registration. 2024-26 never read. One line: net −10.6bp, t −0.60; not tested.

---

# End of session — closing table (Step 9)

6 ideas run (the session maximum). None pre-registered beyond EV1; EV1 judged DEAD. 2024-26 was read only for EV1,
after its pre-registration commit f4d19c5.

| idea | track | events/yr | select result | judged? | verdict | $/yr at $2.3k / $10k / $25k |
|---|---|---|---|---|---|---|
| 1 cluster insider buys | FREQUENT | ~195 (ADV>=20M) | net +27.7bp, hit 53%, t 2.42 | yes (EV1) | **DEAD** (judge-half t 1.85 < 2) | +168 / +879 / +2,262 if real (not real) |
| 2 first insider buy in 2+ yr | FREQUENT | ~140 | net +23.9bp, hit 52%, t 1.66 | no | explored-dead | — |
| 3 SC 13G originals | FREQUENT | ~1,020 | net +9.6bp, hit 51%, t 1.82 | no | explored-dead | — |
| 4 SC 13D/A amendments | FREQUENT | ~519 | net −21.1bp, hit 45%, t −2.82 | no | explored-dead | — |
| 5 8-K "strategic alternatives" | (FREQUENT by count) | ~106 | net +11.2bp, hit 52%, t 0.71 | no | explored-dead | — |
| 6 8-K "special dividend" | SEMI-RARE by count | ~87 | net −10.6bp, hit 49%, t −0.60 | no | explored-dead | — |

Not reached this session (menu rows 7-10): ASR buybacks ("share repurchase" + "accelerated"), 25-NSE delistings,
spin-off completion, S-8 filings. Program N: 758 (EV1 registered, one variant). Nothing to switch on.


---

# Overnight loop (prompt_overnight_loop.md), session llm-trader-e4, started 2026-10-02 ~06:32 PT

## 2. First insider purchase in 2+ years (menu row 2) — Study EV2, track FREQUENT
Event: `insider_buys()`; an officer/director purchase filing (`X[X.insider]`) at an issuer whose previous Form 4
open-market purchase by ANYONE was >= 730 days earlier (the Form 345 sets start 2020-01, so an issuer with no
purchase in the data counts as "none since 2020-01-01"; events therefore start 2022-01). Built by
`research/sim/events_firstbuy_build.py` -> `data/research/program/events_firstbuy.parquet` (3,011 events
2022-01..2026-03). NOTE: this is a subset of ID3's events (ID3 = all officer/director buys), so it is not independent
of the ID3 pass. Trade: next session open cross -> close cross, ADV >= $20M (runner default).

Select-half (<= 2023-12-31), ADV >= $20M:
```
events 1449 -> trades 318  (159 per year)
net per trade +41.8bp  median +20.0bp  hit rate 53%  t +2.44
by year: 2022: +61.7bp (n 182)  2023: +15.0bp (n 136)
TRACK FREQUENT (>= 100/yr): net >= +10bp, hit >= 50%, t >= 2: MEETS -> may pre-register
```
No other ADV floor tried.

Why it should work (before registering):
- **Who is on the other side:** sellers at the opening cross and market makers; the buyers who pay later in the session
  are screeners and alert readers ("first insider buy in years" is a headline phrase).
- **Why they keep paying:** a purchase that breaks a 2-year silence is a rare, costly signal (insiders who never buy
  suddenly buying), and it gets noticed slowly through the session; the same attention lag as ID3, on its rarer and
  more surprising subset.
- **Why big funds don't take it:** one session, a few names a week, mostly $20-100M ADV stocks; needs daily Form 4
  parsing and a 2-year history per issuer; a single-day hold cannot absorb size.

**Duplicate-look note:** d4a0401 (another session, pushed 06:32 without a claim) explored a variant of row 2 that
counted 2020-21 first buys (left-censored) and FAILED (t 1.66). EV2 above excludes those (events start 2022-01).
Because the idea was looked at twice, EV2 is registered as 2 variants: N 758 -> 760 (amendment note in round1_prose.md).

**Judge (N 760): PASS.** Judge half event net +31.5bp, daily-sleeve NW t +2.54; full net +35.5bp, NW t +3.57,
sign-flip 100%, placebo 100%, DSR 0.553. Writeup + shadow spec: research/drafts/study_ev2_first_insider_buy.md.

## 3. SC 13G originals (menu row 3) — explored-dead
Event: full-index form "SC 13G" or "SCHEDULE 13G" (EDGAR renamed it Dec 2024), filer CIKs with <= 50 of these a quarter
dropped, CIK -> ticker via company_tickers (`research/sim/events_form_build.py 13g`); 50,499 events 2020-01..2026-09.
Select half, ADV >= $20M: events 21545 -> trades 4082 (1020/yr); net +9.6bp, median +8.1bp, hit 51%, **t +1.82**;
2020 -67.3 / 2021 -7.5 / 2022 +5.6 / 2023 +48.1bp. FREQUENT: FAILS.
One other floor (ADV >= $1M): 8357 trades, net +6.1bp, hit 51%, t +1.59: FAILS. Explored-dead; 2024-26 never read.
(One year, 2023, carries it all.)

## 10. S-8 filings (menu row 10, low prior) — explored-dead (overnight session; rows taken 10->7 to avoid the unclaimed in-order session)
Event: full-index form "S-8", busy filers (> 50/quarter) dropped, CIK -> ticker (`events_form_build.py s8`); 16,468 events.
Select half, ADV >= $20M: events 8533 -> trades 1855 (464/yr); net **-12.7bp**, median -10.2bp, hit 48%, t -1.43;
2020 -22.8 / 2021 -25.9 / 2022 +1.9 / 2023 -10.6bp. FREQUENT: FAILS. No other floor tried. Explored-dead.

## 9. Spin-off completion (menu row 9) — explored-dead
Event: 8-K full-text `"completed the spin-off"` 2020-26 (`research/sim/events_fts_build.py spinoff`), filer tickers
(parent and/or spinco); 213 hits -> 237 events (~35/yr raw). Explore at ADV >= $20M: 64 trades (16/yr) -> RARE;
net -38.8bp, hit 42%. Deal report (select half, ADV >= $1M, 72 deals, 18/yr):
hold 1: hit 39%, mean -0.53%, worst -7.0% | hold 5: hit 42%, mean +0.60%, worst -12.4% | hold 20: hit 57%, mean +2.08%,
worst -23.9%. RARE gate FAILS at every hold. Explored-dead. The second phrase ("distribution of all of the
outstanding") was not tried (same idea; trying it after this look would be a second variant).

## 8. 25-NSE delisting notices (menu row 8) — explored-dead
Event: full-index form "25-NSE" (filed by the exchange under the issuer's CIK), busy CIKs dropped, CIK -> ticker
(`events_form_build.py 25nse`); 4,008 events. Most are a security class being removed (notes, preferreds, warrants,
merger completions), not the common, so the common usually keeps trading. Select half, ADV >= $20M: 2573 -> 412
trades (103/yr); net **-26.2bp**, median -9.0bp, hit 47%, t -1.54; by year +3.3 / -54.5 / +16.6 / -23.5bp. FREQUENT:
FAILS. No other floor tried. Explored-dead.

## 7. ASR buybacks (menu row 7) — explored-dead
Event: 8-K full-text `"accelerated share repurchase"` 2020-26 (`events_fts_build.py asr`); 2,682 hits -> 2,595 events
(includes earnings-release exhibits that mention an ASR, not just new ASR agreements). Select half, ADV >= $20M:
1432 -> 670 trades (168/yr); net **+3.5bp**, median -5.0bp, hit 50%, t +0.27; by year -108.9 / -3.1 / +37.2 / -20.0bp.
FREQUENT: FAILS. No other floor tried. Explored-dead.

## X1. Dividend initiations, 8-K `"first quarterly dividend"` (extra row X1) — explored-dead
618 hits -> 469 events (noisy phrase, see runbook_menu_extra.md). Explore at ADV >= $20M: 40 trades (10/yr) -> RARE.
Deal report, select half, ADV >= $1M, 80 deals (20/yr): hold 1 hit 48% mean +0.23% worst -25.0% | hold 5 hit 54%
mean +1.68% worst -20.6% | hold 20 hit 52% mean +2.45% worst -46.8%. RARE gate FAILS at every hold. Explored-dead.

## X2. Dividend reinstatements, 8-K `"reinstates quarterly"` (extra row X2) — explored-dead
26 hits -> 26 events (2020-25; only 1 after 2023, so untestable on the judge half anyway). Explore ADV >= $20M: 10
trades -> RARE. Deal report, select, ADV >= $1M, 16 deals (4/yr): hold 1 hit 69% mean +0.21% worst -4.9% | hold 5
hit 69% mean +2.26% worst -7.9% (closest; mean < +3%) | hold 20 hit 50% mean +0.73% worst -17.3%. RARE gate FAILS.
Explored-dead.
