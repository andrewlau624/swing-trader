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
