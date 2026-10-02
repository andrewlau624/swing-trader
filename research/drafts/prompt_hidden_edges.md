# HIDDEN-EDGE HUNT: find the edges that are not retail ideas, and don't stop until one is FOUND

The user is away. Don't ask questions: decide, write down why, keep going. Work in
`~/Documents/Code/Projects/swing-trader` (research data lives here; `llm-trader` is the live checkout). Other sessions
share this tree: run `ListAgents`, tell every session here that you're running this file, and message them whenever you
register an N. **Lanes already owned:** the Jump hunt (`prompt_jump_hunt.md`) owns hype / attention / news -> jump ideas;
the Index-beat hunt (`prompt_index_beat.md`) owns regime robustness and after-tax / account structure. Don't take
those. Only `git add` files you name; never clean, stash, reset or checkout files you didn't write. Claims in your log
are prefixed `Hidden hunt`.

## 0. Why this hunt exists
Around 800 variants have been judged here (program N 767). Nearly everything a retail trader or a public quant blog
would think of is dead: price patterns, calendar effects, regime dials, sentiment, momentum and reversal variants, ML on
bars, index adds, earnings drift, insider clusters. A full sweep of r/algotrading, r/quant, r/Schwab and r/pennystocks
(2026-10-02, `study_reddit_round.md`) found nothing new. **Commonly known ideas are mined out. Stop generating them.**

What has SURVIVED here has one shape (read these first):
- **Own-money purchases:** ID3 / EV2: an officer buying their own stock after 2+ years of silence, especially >= $500k
  (`study_ev2_first_insider_buy.md`; the tail diagnostic in `study_reddit_round.md` R2).
- **Contract payoffs:** B1 reverse-split round-ups, B2 split-off exchange offers with odd-lot priority, odd-lot tenders,
  DL1 DRIP discounts (`study_round32_events.md`, DL rules in `round1_prose.md`).

The common thread is not a signal. **It is a counterparty who is forced, rule-bound, mandate-bound or indifferent, and a
payoff written into a document, too small or too fiddly for anyone with capacity to take.** That is the hunting ground.
A pattern in prices is never the starting point. A **mechanism** is.

## 1. The edge test: every idea must answer five questions BEFORE any data is touched
Write these into `hidden_ideas.md` for every idea. An idea that can't answer all five is not written down.
1. **Who pays?** Name the counterparty who loses money by trading against you: an index fund, a liquidating fund, an issuer
   following its own charter, a dealer hedging a note, a fund that can't hold OTC names, a transfer agent following a
   formula, a holder who doesn't read mail.
2. **Why do they accept it?** Mandate, rule, contract, law, tax, inattention, cost of doing it better. "They're dumb" is not an
   answer.
3. **Why hasn't anyone with capacity taken it?** Pick one: capacity < ~$1M/yr total; per-holder or odd-lot caps; it needs
   reading documents one at a time; it's operationally awkward (tendering, DRS, election forms); legal or mandate barrier;
   the events are too rare for a fund to staff. **If the answer is "nobody noticed", assume it's dead or wrong.**
4. **What document or rule makes it repeat?** A filing type, an exchange rule, an index methodology, a prospectus clause,
   a DTC notice type. If it can't be found mechanically, it can't be automated.
5. **Which death does it dodge?** Name the row in the death map (`prompt_index_beat.md` section 1 and NEXT.md "Things
   already tested") and say how this idea avoids it. Same mechanism as a dead idea = don't write it.

## 2. Where to dig (seeds, not answers: check every seed against NEXT.md's dead list first)
Read primary documents, not commentary: EDGAR full text (efts.sec.gov), exchange rule filings (SR-NASDAQ / SR-NYSE /
SR-CboeBZX on sec.gov/rules/sro), index methodology PDFs and their announcement archives, ETF / CEF / BDC prospectuses and
424B2 pricing supplements, DTC Important Notices, Nasdaq / NYSE trader updates and corporate-action alerts, FINRA daily
list (UPC / symbol / delete notices), OCC info memos (contract adjustments), Federal Register, state unclaimed-property and
escheat rules. LLMs are fine for EXTRACTING terms from these documents; never for judging outcomes (Round 25: the model
remembers 2025 prices).

**A. Contract payoffs (the family that pays here; generalise it)**
- Any per-holder rule with a discontinuity: rounding (up / to round lots / to 100-share lots), odd-lot priority, minimum
  holder thresholds, "holders of fewer than N shares receive cash at a premium", odd-lot buy-back or round-up PROGRAMS
  (issuer offers to buy or sell to round up odd lots, sometimes commission-free at a premium).
- Mandatory exchanges and conversions with a fixed ratio but a market price: share-class collapses, dual-class
  unifications, ADR ratio changes, ADR terminations (depositary sells the shares and pays cash later: the ADR's last
  trading price vs the cash eventually paid), REIT / MLP conversions, mutual-fund -> ETF conversions, CEF -> open-end
  conversions, interval-fund and BDC tenders at NAV.
- Redemptions with a known price and date: preferreds / baby bonds called at par (the notice is filed, the last price
  isn't there yet), ETN issuer calls and accelerations (the call price is formula-set), warrant mandatory redemptions,
  mandatory convertible settlements.
- Distributions where vendors and markets mis-handle mechanics: due-bill periods for large special dividends (ex-date after
  the pay date), non-transferable vs transferable rights, spin-off "when-issued" vs "regular-way" vs "ex-distribution"
  trading (three prices for one claim).

**B. Rule-bound flow you can see coming (not the flagship S&P / Russell events: those are dead and crowded)**
- Small or second-tier index events: S&P SmallCap 600 / MidCap 400, Russell Microcap, sector and thematic ETF rebalances
  with published schedules, equal-weight ETF quarterly rebalances, dividend-index reconstitutions, ESG exclusion lists.
  Practitioners (r/quant 1ppnw7t) say "still some juice in smaller indices": rank by expected flow / ADV.
- **Structured-note hedging:** bank 424B2 pricing supplements on EDGAR list the underlying, barrier, knock-in and observation
  dates for thousands of autocallables. Dealers hedge around those levels and dates. This is rule-bound flow on single
  names that almost no retail tool parses.
- Forced holders and sellers: moves to OTC or from Nasdaq to NYSE American, loss of margin eligibility, ADR level
  downgrades, fund liquidations of illiquid holdings, bankruptcy-emergence equity distributions (check the Jump hunt's
  Ch. 11 idea first), ESPP purchase dates (employees sell the discounted shares), convertible issuance (arbs short the
  stock on pricing day; the stock recovers as the hedge is set).

**C. Plumbing (how the auction, settlement and corporate-action machinery behaves at the edges)**
- Exchange rule changes that alter the closing or opening cross (SR filings): what changes on the effective date?
- CUSIP changes, ticker changes and symbol reuse, where vendor data and index providers lag the event.
- Settlement mechanics (T+1, ex-date rules, due bills) that make the first ex-day print mechanically wrong.

**D. Small-account superpowers (use them, they're the moat)**
- Per-person caps (DRIP OCP, odd-lot priority, round-ups): a fund can't scale, you can repeat across two accounts.
- No market impact at $2-25k in thin names and in the crosses; holder-level treatment where institutions get
  participant-level treatment.
- The Roth: short-term gains tax-free, so high-turnover contract payoffs keep 100%.

## 3. Pipeline per idea (cheapest kill first)
1. **Count before outcomes:** from documents alone, count events per year 2016-26 and the max $ per event per person. Kill
   if < ~5/yr or < $20 per event at $2.3k, unless one event pays a lot (state it).
2. **Mechanism check:** from the terms alone (no prices yet), compute the CONTRACTUAL payoff (what the rule pays if you
   hold through it). If the contract pays nothing, there's no hidden edge, only a price pattern: kill it.
3. **Register** (before any outcome): a deal rule (DL convention in `round1_prose.md`, no N) for contract payoffs, or a
   pre-registered study (N++) for flow ideas. Name the entry, exit, size, costs, failure cases (deal broken, terms
   changed, cash in lieu) and the pass bar. Commit and push.
4. **Run on history:** raw prices (`research/sim/event_fetch.raw_bars`, `filing_day`), real costs (tier / tier_hi, odd-lot
   spreads at the touch for thin names), whole shares, both halves, worst case named.
5. **Automation check:** can the server do it through the Schwab API (as `roundup_orders.py` does), or is the manual step
   under 5 minutes per event? Write down which broker mechanics it depends on and whether `reddit_broker_facts.md` says
   Schwab supports them.

## 4. FOUND (don't loosen, don't redefine)
Exactly one of:
1. **Deal payoff:** a deal rule pushed before any outcome; PAYS on its own history (median > 0, hit >= 60%, worst case
   survivable); **>= +$150/yr at $2.3k (>= 6%)** after costs and whole shares; automatable or < 5 minutes per event.
2. **Flow / book idea:** pre-registered; select 2021-23, judge 2024-26, holdout 2016-20 not negative; raw-price pool;
   **>= +2pp/yr at $10k and at $2.3k after whole-share rounding** (after tax in the brokerage, or in the Roth book);
   NW t >= 2 on the judge half; placebo >= 95th percentile; DSR at the current N reported.
Report k (ideas judged) next to any FOUND.

## 5. Quotas (so the hunt doesn't drift back to price patterns)
Write at least **40 ideas before any outcome**, with at least 10 contract payoffs (A), 8 rule-bound flows (B), 5 plumbing
(C), 5 that only work because the account is small (D), and 5 wildcards from a primary-document type nobody here has
read yet (check `research/sim/*.py` and `data/research/events/` for what's been parsed). **Zero** ideas may start from a
chart, an indicator, a calendar or a sentiment score.

## 6. Logging and stop rules
- `hidden_ideas.md` (ideas with the five answers), `hidden_log.md` (STATE line at the top: round, k, N, what's running,
  next). A NEXT.md section and do-not-redo rows in the commit that ends each idea.
- Any shadow, alert or log-only switch gets a `swingtrader/daily/testing.py` REGISTRY entry in the same commit
  (CLAUDE.md rule).
- **Don't stop until FOUND.** When a round of 40 is exhausted, write the next 40 from the document types that came
  closest. After every 10 ideas judged, write one paragraph: which mechanism came closest and why it failed. Use that to
  aim the next round.
- If FOUND: build the alert or the automatic order path behind an `.env` switch that defaults OFF, add the registry
  entry, email-style summary in NEXT.md with $ at $2.3k / $10k / $25k and a one-line capacity note for $100k / $500k.
  The user switches it on.
