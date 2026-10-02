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
