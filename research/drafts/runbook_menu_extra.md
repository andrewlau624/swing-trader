# Runbook menu, extra rows (overnight loop, session llm-trader-e4, 2026-10-02)

Written after menu rows 1-10 were used up, BEFORE any number on these rows. Same four-part shape as the runbook
menu: a public, timestamped event; who pays; why small size helps; long-only whole shares. Dead-list check done
(NEXT do-not-redo table, RESULTS, event_edge_candidates.md, outside_box_ideas.md, deep_search_candidates.md):
uplisting (killed Round 30 #30), spin-offs, index adds, special dividends, ASR, strategic alternatives, 13D/13G,
S-8, 25-NSE, offerings, NT filers, Form 144 and insider-buy variants are excluded. All are tested as the runbook's
next-session trade (open cross -> close cross; deal report for RARE), built with
`research/sim/events_fts_build.py NAME '"phrase"'` (8-K full text, 2020-26). One phrase per row, fixed here; no
second phrase after a look.

| # | event (8-K full-text phrase) | who pays | small-size advantage | expected track | status |
|---|---|---|---|---|---|
| X1 | `"initiation of a quarterly"` (dividend initiations; Michaely-Thaler-Womack under-reaction) | holders who under-react to a costly payout signal; income funds whose screens add the name only after a payment history | small/mid caps, a few a month, one session | semi-rare | new |
| X2 | `"reinstatement of the quarterly"` (dividend reinstated after a suspension) | the same under-reaction, plus dividend-screen funds that excluded the name | rare, manual | rare/semi | new |
| X3 | `"first share repurchase program"` (first-ever buyback authorization) | sellers into a new, price-insensitive buyer; slow attention in small caps | thin small caps, rare | rare | new |
| X4 | `"has approved"` + FDA, via phrase `"Food and Drug Administration (FDA) has approved"` | short sellers and option writers caught by a binary outcome; slow re-rating of small biotechs | thin biotech names, odd lots fine | semi-rare | new |
| X5 | `"Breakthrough Therapy Designation"` | attention-limited investors re-rating a pipeline signal | small biotechs, one session | semi-rare | new |
| X6 | `"met its primary endpoint"` (positive topline data) | shorts covering through the session; slow institutional re-rating | small biotechs | semi-rare | new |
| X7 | `"regained compliance"` (exchange listing rule, usually minimum bid) | holders who sold on the deficiency notice; mandate funds barred from deficient names | sub-$100M names | frequent/semi | new |
| X8 | `"strategic investment"` (a larger company buys a stake) | sellers who under-weight a validation signal | small caps, rare | semi-rare | new |
| X9 | `"raises full-year"` (guidance raise in an 8-K) | under-reaction to guidance (PEAD-like, untested here: DS7 was not run) | the session trade only; small caps cheap to enter at the cross | frequent | new |
| X10 | `"awarded a contract"` (government/commercial contract award 8-K) | attention-limited small-cap investors | thin names, one session | frequent | new |
