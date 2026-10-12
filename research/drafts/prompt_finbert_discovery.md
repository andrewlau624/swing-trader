# Prompt: FinBERT / open NLP models as a discovery tool (new session)

Run a research session in this repo (swing-trader) on one question:

> **Where can free open-source financial NLP models (FinBERT and relatives on Hugging Face) turn TEXT that the market
> reads slowly into a tradable, small-account edge — beyond news headlines?**

Read CLAUDE.md first (the research philosophy, the research-priority gate, the validation protocol, the do-not-redo
tables in NEXT.md). Program N is 887 at the start of this session; pre-register every judged variant in
`research/drafts/round1_prose.md` and bump N before any outcome is read.

## Why this is worth a session (and what is already dead)

- **Dead — do not redo:** headline/news continuation intraday (NEWS-DRIFT, N 885), LLM + FinBERT reading the pre-open
  earnings release (LLM-EARN, N 886-887: 09:35->close -14 / -10bp), news sentiment filter on night picks, 8-K bad-news
  items, Reddit sweep (6 variants), earnings straddles/drift/gaps. Lesson: **fast, widely-read text (headlines, earnings
  releases) is priced at the open.** Do not test another headline/earnings variant.
- **The opening:** FinBERT (ProsusAI/finbert) was trained on 2010s financial text, so — unlike an LLM — it carries no
  memory of 2016-2026 outcomes. **Backtests on 2016+ are honest** (an LLM is only valid after its cutoff). That makes
  long, slow, rarely-read documents testable for the first time in this program.
- **Where text plausibly carries information not yet in price:** long documents few people read, changes buried in
  boilerplate, and documents attached to the program's few LIVE/PROMISING edges.

## Candidate mechanisms (rank them with the research-priority gate before coding any)

1. **"Lazy prices" (Cohen-Malloy-Nguyen 2020):** year-over-year CHANGES in 10-K/10-Q text (esp. Risk Factors, MD&A)
   predict returns over months; firms that change their filing language underperform. FinBERT tone of the changed
   sentences + plain similarity (TF-IDF or a sentence-embedding model). Monthly/quarterly holding — capital-efficient?
2. **CEF shareholder letters (N-CSR) and distribution notices x CEF-RV.** CEF-RV (discount reversion) is the program's
   strongest small-account candidate (+409..+486bp/trade at real auction prints, PROMISING-SURV-LIMITED). Does manager
   tone / a distribution-cut warning in N-CSR / 19a-1 notices separate the discount entries that recover from those that
   keep widening? Filter on an existing edge = the highest-value use of a classifier here.
3. **Forced-flow discovery (P01 scanner, `swingtrader/daily/forced_flow_discovery.py`):** zero-shot classification
   (e.g. facebook/bart-large-mnli) or FinBERT-based tagging of EDGAR filings to find odd-lot tenders, guaranteed-floor
   offers, rights offerings, mandatory redemptions of preferreds/baby bonds, CEF tender/liquidation announcements —
   events with a named forced counterparty that keyword search misses. Measure recall vs the current regex scanner.
4. **Preferred / baby-bond documents x PREF-EX:** redemption/call notices, deferral language (non-cumulative skip risk)
   as a risk filter on the PREF-EX ex-night trade.
5. **Insider Form 4 footnotes x ID3/EV2:** 10b5-1 / gift / option-exercise boilerplate vs discretionary buys —
   a cleaner "informed buy" filter for the insider family (forward-only shadow; footnote text is in SF2/EDGAR).
6. **Fed/Treasury text (FOMC statements/minutes; FinBERT-FOMC exists) x Treasury month-end (TME, validated small).**
   Only if it can clear the +8pp gate — likely not; rank it honestly.

Add your own, but every candidate must name: who is slow or forced, why the text is not already in price, the trade,
holding period, and the ceiling `events/yr x net edge x deployable share x capture` at $2.3k / $10k / $25k.

## Data and tooling (verify before relying on it)

- Prices: Sharadar bundle `~/data/sharadar` (SEP stocks + SFP funds, 1998+, delisted-complete; loader in CLAUDE.md).
  Use `closeadj` for total returns — raw closes break across splits (CEF-RV audit 2026-10-06).
- EDGAR full text: needs a `SEC_USER_AGENT` header (403 without it; check `.env` by variable name only, never print it;
  the news judge uses `NOTIFY_EMAIL`). Respect SEC rate limits (10 req/s). Cache raw filings under `data/research/`.
- Models: run torch + transformers in a SEPARATE venv (do not change the project `.venv`); a working pattern is in
  `research/sim/llm_earn_finbert.py`. CPU is fine for FinBERT at ~6k docs/minute in batches of 32 (512-token windows;
  for long filings score sentence-level and aggregate — say how).
- Existing text infra: `research/sim/llm_earn.py` (Alpaca/Benzinga news + leakage placebo pattern),
  `swingtrader/daily/news_judge.py` (SEC headers, filings fetch), `forced_flow_discovery.py` (EDGAR forms scanner).

## Protocol (non-negotiable, from CLAUDE.md)

- Research-priority gate BEFORE any backtest: kill a candidate if its honest ceiling at $10k is < +8pp/yr, unless it is a
  FILTER on an existing live/promising edge (then judge by the lift it adds to that edge).
- Pre-register (rule, data, window, gate, kill rule) before reading outcomes. Judge on a window/asset never used to choose
  the rule; report halves, cost shock (2-3x), ex-top-5, median and hit rate, clustered t, a placebo (shuffled text or
  shuffled dates), and a non-NLP control (does plain word count / filing length / a keyword rule do as well?). If a
  dumb control matches the model, the model adds nothing.
- Assume spectacular results are bugs (split-adjustment, timestamp/lookahead: use the SEC ACCEPTANCE time, not the
  period date; survivorship: include delisted names).
- Record every verdict in round1_prose.md and every dead end in the NEXT.md do-not-redo table. No live orders, no paid
  data, no deployment; anything with orders goes to a forward shadow registered in `swingtrader/daily/testing.py`.

## Deliverable

A ranked ledger of NLP candidates (gate math for each), 1-3 pre-registered and judged studies, and a plain verdict:
does open-source financial NLP give this account an edge that price data alone does not — and where exactly?
