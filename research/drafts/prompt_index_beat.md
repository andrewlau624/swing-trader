# INDEX-BEAT HUNT: widen the margin over an index fund at $2-25k, automated, and don't stop until one is FOUND

The user is asleep. Don't ask questions: decide, write down why, keep going. Work in
`~/Documents/Code/Projects/swing-trader` (the research data lives here; `llm-trader` is the live checkout).
Other sessions share this tree and repo: run `ListAgents`, tell every session working here that you're running
this file, and message them whenever you register an N. **The Jump hunt (`prompt_jump_hunt.md`, claims prefixed
`Jump hunt`) owns hype/attention/news -> +20% jump ideas: don't take those.** Only `git add` files you name; never
clean, stash, reset or checkout files you didn't write.

## 0. The goal, made precise
Where the book stands (from the 2026-10-02 projections, `swingtrader/daily/digest.py` PLAN / BACKTEST):
- **Brokerage:** the base plan (17.8%/yr pre-tax, edge-halves) **ties an index fund after the 32% short-term
  tax**. It beats the index hard only if every gated lever works.
- **Roth** (+$7.5k/yr, no tax, no shorting, no intraday margin): the bot already beats the index by ~17% of the
  ending balance at the 5-year median.

The user wants the bot to **beat the index by a wide margin at $2.3k / $10k / $25k**, ideally **with no manual
steps**. Three tracks; each idea belongs to exactly one:

- **A. NEW EDGE (automated).** A new leg, overlay, filter or deal payoff the server can run without the user.
- **B. ROBUST TO THE MARKET.** Change the CURRENT book so it keeps (or grows) its edge as markets change, and uses
  what is unusual about 2026-27 (23/5 trading from 2026-12-06, the 2026-07 intraday-margin rule for small
  accounts, today's volatility and retail-flow regime). **Read section 1's REGIME rows first: every simple
  "adapt to the regime" rule tried here has died.** Track B ideas must be structural (a mechanism that is
  regime-proof by construction) or forward-only (new market structure no history covers), not a dial fitted to the
  past.
- **C. AFTER-TAX / ACCOUNT STRUCTURE.** In the brokerage, tax is the biggest drag (~1/3 of every gain). Raise
  AFTER-TAX growth across the two accounts with the same edges: which leg runs in which account (asset location
  under the wash guard), holding-period and lot rules, 60/40 instruments small enough for $2-25k, loss timing
  around December, where idle cash and deposits go. These are allowed to be "report" findings with exact dollars
  if they need no N.

**FOUND** means exactly one of these:
1. **Book idea (tracks A/B):** pre-registered in `research/drafts/round1_prose.md` before any 2024+ outcome;
   select 2021-23, judge 2024-26, holdout 2016-20; on the raw-price pool (`research/sim/validate.py load_sim(raw_price=True)`, addendum 39);
   the increment over the shipped book, **edge-halves AFTER tax** (`research/sim/taxable_frontier.py`
   `after_tax` / `mc_tax`, 35% ST) at **tier costs**, is **>= +2.0pp/yr at $10k** and **>= +2.0pp at $2.3k after
   whole-share rounding**, with NW t >= 2 on the judge half, a placebo >= 95th percentile, the holdout not
   negative, and DSR at the current program N **reported** (not gated; say it plainly). Roth-only ideas use the
   Roth book (`research/sim/roth*.py`), no tax, same bars.
2. **Deal payoff (track A):** a deal rule written and pushed before any outcome (the DL1-DL7 convention in
   `round1_prose.md`, no N), **PAYS** on its own history, **>= +$150/yr at $2.3k (>= 6%)**, and **automatable**:
   the server can buy and exit it through the Schwab API (as `roundup_orders.py` does), or the only manual step
   takes under 5 minutes per event.
3. **Structure finding (track C):** a change that needs no new edge, worth **>= +2pp/yr after tax** on the
   combined plan ($2.3k brokerage + Roth $8.5k now, $1-2k/month taxable, $7.5k/yr Roth), computed exactly with the
   repo's tax code, both halves.

**Do not stop until FOUND** (section 8). Never redefine FOUND, never loosen a bar, never re-run a judge with new
settings. Count every judged idea (k) and report it next to any FOUND.

## 1. Why ideas have died here: the death map (read this, then design around it)
About 800 variants have died for a short list of reasons. **Every idea you write must name the death it is built
to dodge, and how.** If you can't name one, it's the same dead idea again. Read `NEXT.md` "Things already tested
— do NOT redo these" in full before writing anything.

| death | what it looked like here | how to dodge it |
|---|---|---|
| **REGIME DIAL** | SPY/VIXY regime gates, cross-leg regime tilts, SKEW sizing, vol-targeted gross, Moreira-Muir: every leg earns MORE on stressed days, so de-risking in bad regimes cuts the edge | don't size the existing legs by a market-regime signal; if you must, show the leg's own edge (not the market) moves with the signal |
| **REFIT** | walk-forward annual refits lose 0-8pp/yr; trailing-Sharpe softmax across legs ~0..−1.5pp | adaptivity must come from a mechanism (who is forced to trade), not from re-estimating parameters on recent returns |
| **FALSE ALARM** | CUSUM / rolling-t de-risking costs 1.3-14pp/yr with nothing decayed | no switch-off rules from short live windows |
| **HALF-FLIP** | most tilts and filters flip sign between 2021-23 and 2024-26 | ask "why would this work in 2017 AND 2025?" before running |
| **TAX** | aggressive/1.5x profiles add +0.7pp after tax for +12-17pp P(DD>30%) | judge after tax; prefer ideas that are tax-efficient by construction or live in the Roth |
| **WHOLE SHARES** | $2.3k books miss 15 of 49 backtest names | model whole shares at $2.3k; an edge that needs fractional shares is a $25k+ edge |
| **COST** | intraday lab ideas: real +6bp signals eaten by the spread | the edge must be >= 2x a round trip at tier costs |
| **GAP** | 8-K, FDA, index adds, 13D: the move is in the announcement gap | be earlier than the news, or trade a contract, not a reaction |
| **LOTTERY / TOO RARE** | a few huge winners; contract payoffs at ~1 a year | ex-top-5 test; >= 6 events a year or a family of them |
| **LOOKAHEAD** | split-adjusted bars let sub-$5 winners in (addendum 36); LETF close cross; LLM memory | raw prices only; timestamp every input; LLM judgment only after its cutoff + 2 months |
| **TEXTBOOK** | 12-1 momentum, PEAD, put-write, pairs: published and decayed | data or rules no paper uses; mechanisms specific to small accounts or 2026 structure |
| **STACKING** | the program's survivors stacked: no increment clears DSR 0.95 | one clean mechanism beats five weak tilts |

Also read before writing ideas: `CLAUDE.md`; the top of `NEXT.md`; `RESULTS.md` addenda 26, 29, 31, 32, 37, 38, 39,
40 (grep); `study_everything_on.md`; `prompt_small_account_profit.md`; `prompt_max_edge.md`; `outside_box_ideas.md`;
`discovery_log_c5.md`; `research/drafts/runbook_claims.md`; and `index_beat_log.md` if it exists (resume from its STATE).

## 2. Hard rules
1. Research only. Never edit `scripts/`, `config.yaml`, `deploy/`, `.env`, or any order path in either checkout.
   One exception, a FOUND idea: add a **shadow/alert module** (logs and emails, never orders) under
   `swingtrader/daily/`, with tests, registered in `swingtrader/daily/testing.py` (CLAUDE.md rule).
2. Select data only while exploring (2021-23, plus anything before 2016 you like). **No 2024+ outcome before the
   pre-registration is committed and pushed.** 2016-20 is the holdout: look at it once, at judging.
3. No money. Free data only. The OpenCode Go subscription (`swingtrader/daily/news_judge.py
   make_client("opencode-go")`) is allowed for EXTRACTION of facts (any window) and judgment (post-cutoff only), at
   most 3,000 calls per idea, counted in the log. If an idea needs paid data, write the request and move on.
4. Git: `git fetch && git merge origin/main` before every push; never rebase or force. Claim ideas in
   `research/drafts/runbook_claims.md` before any data work (prefix `Index beat`); skip ideas others claimed.
5. A command that fails twice: drop the idea, log the error, move on. Respect rate limits and terms (SEC needs
   `sec_headers()`).
6. Verdicts copied exactly as printed. Small accounts (CLAUDE.md): report $/yr and %/yr at **$2.3k / $10k /
   $25k** first, $100k / $500k as one capacity line.
7. The Roth: long only, no intraday margin, limited margin only (no borrowing), wash guard `roth_first`.

## 3. Raw material
- **This repo's sims:** `research/sim/book.py` (`Sim`, `Params`, `replay`), `everything_on.py`,
  `taxable_frontier.py`, `roth*.py`, `program_books.py`, `growth.py`, `rawprice.py`; event tools
  (`event_fetch.py`, `event_runner.py`, `jump_runner.py`); deal sims (`roundup.py`, `splitoff.py`,
  `tender_report.py`, `drip_ocp.py`). Reuse them; don't write a new simulator.
- **Live evidence** (forward only, on the server `him`, read-only over ssh): `logs/daily-fills-*.jsonl`,
  `logs/daily-decisions*.jsonl`, `state/book-daily-*.json`. Live open sells cost ~0bp vs the auction; paper fills
  are the Alpaca simulator's and are NOT evidence (fixed 2026-10-02).
- **New 2026 structure:** 23/5 trading from 2026-12-06 (NEXT.md "23/5 trading"); Schwab Intraday Margin Buying
  Power for accounts >= $2,000 since 2026-07-13 (addendum 40); odd-lot quote dissemination; Schwab API order types.
- Free data: EDGAR (full text, XBRL companyfacts), FINRA, Cboe/Nasdaq daily files, French library, FRED, Treasury,
  Alpaca bars/news/corporate actions with the repo's keys, the Wayback Machine.

## 4. Creativity engine (mandatory: the idea list must show these)
Write `research/drafts/index_beat_ideas.md` with **>= 50 ideas** before computing any outcome. Each idea: track
(A/B/C), method tag, the cause sentence ("<who> is forced to <trade> at <time/price> because <rule>; we take the
other side at $2-25k because <why a small account can>"), **who is on the other side and why they keep paying**,
the **death it dodges**, the closest do-not-redo row and what is different, data source (verified?), events/yr,
rough %/yr at $2.3k / $10k / $25k, novelty 1-5 with what you searched. Quotas:
- **>= 15 track A** new automated edges, of which **>= 5 contract/deal payoffs** the Schwab API can run end to end
  (like the round-up buyer).
- **>= 10 track B** ideas, of which **>= 4 forward-only** (23/5 overnight session, the intraday-margin rule, other
  2026 structure): write their shadow spec and measurement plan, since history can't judge them.
- **>= 10 track C** after-tax / account-structure ideas.
- **>= 8 death-dodges:** take a specific DEAD row, name its death, change exactly that.
- **>= 5 small-account-only** ideas: things that break above ~$50k (odd lots, thin auctions, per-account caps,
  whole-share rounding used as a feature).
- **>= 5 wildcards** that feel silly.
- **>= 5 from outside the repo:** papers (SSRN/arXiv q-fin/NBER), Quantpedia, Alpha Architect, practitioner
  writing; each with a link and its decayed edge (published edges shrink ~1/4-1/2 after publication).
Banned as-is (dead; allowed only as a named death-dodge): market-regime sizing of existing legs, parameter
refits, CUSUM switch-offs, more leverage profiles, price-pattern momentum/breakouts, technical indicators,
sentiment scores on pre-cutoff news, earnings drift, index adds, and anything the Jump hunt owns.

## 5. Process
1. **Setup:** merge; `PYTHONPATH=. .venv/bin/python -m pytest tests/ -q` must pass; read the current N (last
   `## Amendment` in `round1_prose.md` that registers one). Create/resume `research/drafts/index_beat_log.md` with
   a **STATE** block at the top: N, k, current idea, next 5 ideas, data sources verified/broken, the running "why
   things die" line. **Update STATE after every idea** so a resumed session knows exactly where it is.
2. **Diverge:** the idea list (section 4). Commit + push before any outcome.
3. **Rank:** (P it dodges its death) x (%/yr at $2.3k-$10k after tax) x (automatable) x (novelty) x (P the data
   works). One reachability request each for the top 15. Work down the list; alternate tracks so no track starves.
4. **Per idea:**
   1. Claim it.
   2. Explore on select data ONCE with the variant written down before the run (one further variant allowed, its
      threshold written down first, logged as a second look). Log every number.
   3. If it meets the bar on select: write who pays and why it persists; pre-register (`## Amendment — Index beat,
      Study IB<k>: <idea> (pre-register; track <A|B|C>, <looks> looks, program N a -> a+1)`, or a deal rule with no
      N). Commit + push. Renumber if another session took that N.
   4. Judge ONCE (2024-26), then the 2016-20 holdout ONCE, same code and arguments. Book ideas: increment after tax,
      edge-halves, tier costs, at $2.3k (whole shares) and $10k; NW t; placebo; DSR at N.
   5. Write `research/drafts/study_ib_<name>.md` (all numbers, verdicts as printed), a NEXT line, and a do-not-redo
      row if dead. Update claims + STATE, commit, push.
5. **Refill** when < 5 untested ideas remain: 20 new ones from a method or source you haven't used. Re-read the
   death map first and add the new deaths you've seen.
6. **Every 5 ideas:** tests pass, your files clean in git, re-read sections 0-2, update the "why things die" line.
   If the last 10 ideas died the same way, the next 10 must be built to dodge THAT death.
7. **Forward-only ideas** (track B 23/5 etc.) that pass a sanity check: write the shadow spec, register it in
   `testing.py` as a spec-only row if the module isn't built, and keep hunting. They are not FOUND.

## 6. Using LLMs without fooling yourself
- **Extraction (any window):** facts printed in a document (terms, dates, ratios, "rounded up" clauses), with only
  that text in the prompt and the output checked verbatim against it.
- **Judgment (post-cutoff only):** the model knows events through at least 2025-10 (Round 25 BC). Opinions as
  signals only on events after cutoff + 2 months.
- **Brainstorm partner:** for mechanisms and sources; its ideas go through the death map like any other.

## 7. FOUND protocol
1. Writeup: select / judge / holdout lines as printed; k and N; DSR; the cause sentence; who pays; the death it
   dodged; what would kill it; **after-tax %/yr and $/yr at $2.3k / $10k / $25k** next to the index fund; the
   5-year median for the user's plan ($1k and $2k/month taxable, Roth $8.5k + $7.5k/yr) with and without it;
   events a year; manual steps (ideally none).
2. Shadow/alert (or, for a deal payoff, an alert-first module mirroring `roundup_watch.py`; the user switches on
   automatic orders, not you): `swingtrader/daily/<name>.py`, logs to `state/<name>.jsonl`, emails, **never
   orders**; tests; a Makefile target; a `testing.py` REGISTRY entry with its forward gate; a NEXT line. Full test
   suite passes.
3. Commit, merge, push. Append the summary to `index_beat_log.md`. Message the other sessions. STOP and reply to
   the user in plain words: what it is, why it might be real, the verdict lines, k, the money at three sizes vs the
   index, what they need to switch on.

## 8. Stop rules (the only ones)
- FOUND (section 7).
- Tests fail and can't be fixed without touching live code: stop, write why.
- **At least 6 rounds of idea generation AND >= 120 ideas explored across all three tracks**, and no source left:
  stop with the honest summary (what came closest, the death that got it, and the best track C report in dollars).
  "Nothing found" after an honest search is a result; a fluke dressed up as FOUND is a disaster.
- Running low on context is NOT a stop: update STATE, commit, push, and continue (or let the loop restart you
  from STATE).

Before any stop: update STATE and append to `index_beat_log.md` the table
`idea | track | method | death dodged | events/yr | select | judged? | verdict | holdout | after-tax $ at $2.3k/$10k`,
plus the near misses. Commit, merge, push.
