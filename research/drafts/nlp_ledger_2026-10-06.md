# NLP candidate ledger — open financial NLP as a discovery tool (2026-10-06)

Session prompt: `prompt_finbert_discovery.md`. Program N 887 at start. Gate (CLAUDE.md research-priority gate):
`ceiling %/yr = events/yr x net edge/event x deployable share x capture`; kill before testing if < +8pp/yr at $10k,
unless the candidate is a FILTER on a live/promising edge (then judged by the lift it adds to that edge).

Common prior for every row: the program's two text tests (NEWS-DRIFT N 885, LLM-EARN/FINBERT N 886-887) found that
fast, widely-read text is priced at the open. The only open question is slow, rarely-read text.

| # | candidate | who is slow / forced | trade, hold | ceiling $2.3k / $10k / $25k | verdict |
|---|---|---|---|---|---|
| 1 | **CEF-RV x N-CSR shareholder-report tone** (filter) | CEF holders (retail, income) do not read the semi-annual report; the discount may widen on information (holdings, distribution cut coming) or on flow | existing CEF-RV trade, ~14 wk | filter: CEF-RV is capital-bound at $1k slots (~10 at $10k, 3.7 turns/yr); +100bp/trade lift on kept trades = **+3.7pp/yr** on the CEF sleeve; capacity-capped at the cross, so $ plateau as in CEF-RV | **RUN (CEF-TXT, N 888-889)** — filter on the strongest small-account candidate |
| 2 | Lazy prices (10-K/10-Q YoY text change; Cohen-Malloy-Nguyen 2020) | investors ignore boilerplate changes | long non-changers (Roth/long-only), monthly | published L/S ~30-60bp/mo 5-factor alpha (extreme sorts higher); long leg ~half; post-2018 publication decay ~50%; 50% capture: ~15bp/mo x 12 = **~1.8pp/yr** excess at 100% deployment, any size | **KILL at gate** (and needs ~60k 10-K/10-Q downloads; not worth it) |
| 3 | Forced-flow discovery recall (zero-shot / FinBERT tagging of EDGAR) | named forced counterparties (odd-lot tenders, guaranteed floors) | CPC events, days-weeks | CPC whole complex ~+8.4pp at $10k historically; NLP adds only events the regex misses. The clauses that matter (odd-lot priority, per-holder cap, guaranteed floor) are exact contractual phrases deep in long documents: regex on full text finds them; a 512-token classifier on the first window cannot. Binding limits are event rarity (~14 deals/10yr) and the MANUAL Schwab election, not recall | **KILL as a return study**; tooling note: a classifier is the wrong tool for clause detection. If recall is ever doubted, audit regex misses by hand on one year of SC TO-I |
| 4 | Preferred / baby-bond call & deferral text x PREF-EX (filter) | holders miss redemption / deferral notices | PREF-EX ex-night | PREF-EX hit rate is high (median +35bp, t 20, 22/22 yrs). A call notice ends the ex-date sequence (the final payment rides the redemption; no ex-night trade exists); a deferral removes the ex-date. Text can only remove trades that would not exist. Lift ~0 | **KILL at gate** |
| 5 | Form 4 footnote text x insider ID3/EV2 (filter) | discretionary vs plan/gift/exercise buys | open->close / days | insider family is an event sliver (~0.5%/yr at book level); 10b5-1 status is a checkbox since 2023 and a keyword (`10b5-1`) before — a regex control matches any classifier by construction | **KILL** (dumb control dominates; ceiling far below gate) |
| 6 | FOMC statement/minutes tone (FinBERT-FOMC) x Treasury month-end (TME) | none forced by text; TME flow is calendar index-extension | TLT T-3 -> T | TME = 12 x ~35bp x 100% = ~4%/yr; a tone filter cannot double it, and FOMC text is the most-read text in finance | **KILL at gate** |
| 7 | 10-K/10-Q distress text (going concern, ATM/shelf language) x night leg (filter) | night bounce is liquidity provision; information drops should not bounce | night pick, 1 night | night leg validated-small (~+3bp/night 2003-15, ~4pp/yr of book); the same mechanism with the faster, more specific text (news-sentiment filter on night picks) is already dead; filing text is staler and less specific | **KILL (dominated by the dead news filter)** |
| 8 | CEF proxy / activist text (DEF 14A, PREC14A: open-ending, tender, liquidation proposals) | boards forced to act on votes | CEF, weeks-months | G45 activist 13D on CEFs measured +2-3.6%/60d, ~+3.4%/yr at book level; announcement gap absorbs the vote outcome | **KILL at gate** (overlaps G45; too small) |
| 9 | CEF N-CSR tone CHANGE (within-fund lazy prices) | as #1 | as #1 | as #1 | **RUN as arm A2 of CEF-TXT (N 889)** |

Not candidates: anything on headlines, earnings releases, 8-K items, Reddit (dead list in the prompt). Time-series
foundation models (price-only) are the program's most-tested dead class.

## Results
**CEF-TXT (N 888-889): KILL both arms** (details round1_prose.md, `research/sim/cef_txt_out.txt`). 8,160 scored reports,
3,562 CEF-RV trades. A1 tone level spread -58bp (t -1.86, wrong sign; placebo 5th pct); A2 tone change -31bp (t -0.79).
No control filters either (size, distribution-cut keyword ~0; discount depth +121bp t 1.53). FinBERT tone is valid
(tracks the 2022 bear market) but uninformative about which discounts revert.

## Verdict
**No.** Open-source financial NLP does not give this account an edge that price data alone does not, at any place the
program can reach:
- fast text (headlines, earnings releases) is priced at the open (NEWS-DRIFT, LLM-EARN/FINBERT);
- slow text attached to the best small-account edge (CEF N-CSR letters x CEF-RV) carries nothing: the CEF discount
  reverts on flow, and the report is market commentary;
- every other slow-text idea fails the gate before a backtest (lazy prices ~1.8pp/yr; PREF-EX, Form 4, FOMC filters
  can at most trim trades that are already rare or dominated by a regex);
- for forced-flow discovery, regex on full text is the right tool, not a classifier.
Where NLP could still matter: tooling (reading documents faster for the manual CPC pipeline), not a signal. The one
new lead from this session is price-only (CEF-RV entries after a NAV fall do best), and it needs its own
pre-registration.
