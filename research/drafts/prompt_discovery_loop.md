# DISCOVERY LOOP: find mechanisms nobody has looked at (outside the box, then rigorous)

The user may be asleep. Work alone until a STOP condition (section 7). Don't ask questions: make the call, write down
why, and move on. You are in `~/Documents/Code/Projects/swing-trader`. Other sessions may share this working tree:
only `git add` files you name; never clean, stash, reset or checkout files you didn't write.

## 0. What 790+ tested variants have taught us (read this twice)
- **Statistical "news -> trade the next session" is dead.** Round 33 tried 13G, 13D/A, S-8, 25-NSE, ASR,
  strategic alternatives, special dividends, spin-offs, dividend initiations/reinstatements, first buybacks, FDA
  approvals, Breakthrough designations and topline 8-Ks. News moves in the gap; the session after is ~0, and biotech
  news is a lottery. **Banned this round: any "8-K phrase / form type -> next-session or N-day drift" idea**, unless
  the phrase sets a contract payoff or a forced trade with a known date (section 2A/2B).
- **Two families pay:**
  1. **Insiders putting in their own money:** ID3 (shadow) and EV2, "first buy in 2 years" (PASS, DSR 0.553).
  2. **Payoffs written into a document, where small holders get better terms:** odd-lot tenders (14/14 profitable)
     and split-off exchange offers with odd-lot priority (12/14 > 0, median +7.4%).

  Family 2 pays *more* the smaller the account and needs no statistics, only the terms and the dates. **That is
  where to dig.**
- Also read before proposing: NEXT.md (top + the do-not-redo table), `outside_box_ideas.md` (47 ideas, Round 30),
  `event_edge_candidates.md`, `deep_search_candidates.md`, `runbook_menu_extra.md`, `runbook_claims.md`, and
  `research/drafts/study_oddlot_tenders.md` / the split-off notes (they are the model of a good find).

## 1. Hard rules (unchanged; break one = the session doesn't count)
1. Research only: never edit `swingtrader/`, `scripts/`, `config.yaml`, `deploy/`, `.env`. No live code, no orders.
2. No 2024-26 outcome before a rule is pre-registered and pushed. Statistical ideas explore on <= 2023-12-31 only.
3. No money. Free data only (EDGAR, Alpaca, exchange/FINRA/Cboe public files, issuer documents, web pages).
4. Git: `git fetch && git merge origin/main` before every push; never rebase or force.
5. A command that fails twice: drop that idea, log the error, move on.
6. Verdicts copied exactly as printed. Never re-run a judge with new settings.
7. Small accounts are the target (CLAUDE.md): rank by %/yr at **$2.3k / $10k / $25k** (taxable) and in the Roth
   (+$7.5k/yr, long-only, no margin). Whole shares. A manual action is fine if it takes <= 30 min per deal.

## 2. Discovery methods. Use at least 4; tag every idea with its method letter
**A. Contract-payoff hunt (top priority).** Find corporate actions whose payoff is fixed by a document and that treat
small holders better, or let anyone buy below a guaranteed value. For each type: find the EDGAR form or phrase,
read 3 real filings in full, and write the payoff formula, the dates, the small-holder clause and the failure modes.
Seeds (verify each against the dead list; extend it):
- **Odd lots and rounding:** odd-lot cash-outs (B4, claimed by llm-trader-0e) and reverse-split round-ups (B1,
  claimed). Also forward/reverse-split "cash in lieu at a premium", odd-lot buyback programs, and odd-lot priority
  in exchange offers other than split-offs (preferred/debt-for-equity, holding-company reorganizations).
- **Depositor/member rights:** mutual-to-stock thrift and MHC second-step conversions (depositors get subscription
  priority at a fixed $10; S-1 / 424B3 / "Plan of Conversion"), insurer demutualizations, credit-union conversions.
- **Fixed-price offers:** rights offerings with oversubscription privileges priced below market (fixed vs.
  formula price), DRIP/optional cash purchase plans with a 1-5% discount (S-3D / 424B3 "discount" text), employee-
  style discounts open to all holders.
- **Value floors:** liquidations and dissolutions trading below the estimated distribution (8-K "plan of
  dissolution", DEF 14A, liquidating trusts); CEFs announcing a conversion to open-end, liquidation or a NAV
  tender for all holders (not odd-lot; the discount closes); CVR deals; SPACs below trust where the deadline is
  near (only if > 8% of equity can sit there; see Round 30 #13).
- **Merger mechanics:** cash/stock election deals where the oversubscribed side is prorated but small holders aren't
  (read the election clause); "short-form" mergers after a tender where the squeeze-out price is fixed.
- **Already-approved actions:** `DEF 14C` information statements. The majority has already approved the action
  (reverse split, going private, sale), and it becomes effective a known >= 20 days later. What is priced in?

**B. Rulebook mining.** Read the actual rules (free on the web) for thresholds, deadlines and mandated actions:
IRS (wash sale, qualified dividends' 61-day holding, Roth rules), Reg SHO, Rule 10b-18 (buyback timing limits),
FINRA odd-lot and round-lot rules, Nasdaq/NYSE listing rules (bid-price cures, delisting timelines), index
methodology PDFs for small indexes (S&P 600 / sector / dividend / equal-weight: who is *forced* on which date),
ETF rule 6c-11, 40-Act diversification tests at quarter-end, Fed/insurer capital rules. Output: a table of "rule ->
who must trade -> when -> can a small long-only account stand on the other side?".

**C. Form-type census.** `F.full_index(y, q).form.value_counts()` over 2020-26. List every form with ~10-3,000
filings a year that no study has used (grep the drafts). For the ~20 most promising, open 3 filings each and write
one line: what event, who must act, is there a dated payoff? Candidates worth a look include SC 14F1, SC TO-C,
DEF 14C, 15-12B/15-12G, N-23C3A, 8-K12B, 425, 40-APP, 1-U, CORRESP (SEC comment letters released later). This is
reading, not backtesting.

**D. Enrichment scan (data-driven, with a guard).** Take the biggest 5-day moves in $1-100M ADV names on 2020-10 ..
2022-06 only. Count which EDGAR form types and Form 4 codes appear in the 10 days before, against a random base of
the same names and dates. Report the enrichment ratio with a binomial CI. Form types that are over-represented by
> 2x with > 30 cases become candidates only if they **confirm on 2022-07 .. 2023-12** (same rule, one look). Log K =
the number of types scanned; the registration must state K, so a reader can recompute DSR at N + K.

**E. Who else puts their own money in?** Extend the family that works, with new signals rather than ID3 re-cuts:
- insiders who exercise options and **hold** (Form 4 code M with no same-day S);
- insiders whose 10b5-1 sales stop early;
- directors buying at a *second* company they serve;
- a CEO buying in the first 90 days of tenure;
- buys by a fund's portfolio managers in their own closed-end fund (Form 4 on CEFs);
- issuer purchases disclosed in 10-Q repurchase tables (stale, but sized).

State why each is not just a subset of ID3/EV2; if it is a subset, it is a *weight* inside ID3 (like EV2), not a
new book.

**F. Steal from another field.** Auction theory (fixed-price vs. Dutch, winner's curse in rights offerings), insurance
(being paid to hold a known tail), queueing (who stands first in line at a deadline), law (appraisal, squeeze-outs,
tax elections), sports betting (closing-line value on deal spreads). Each analogy must end in a dated, tradable rule.

## 3. Process for each idea
1. **Claim** it (`runbook_claims.md`, commit + push) before any data work. Re-check after merging.
2. **Kill fast** (write the reason in one line): on the dead list; a renamed common strategy; needs shorting, paid
   data or > 30 min/deal; < 1 deal/yr; can't be held in whole shares at $2.3k.
3. **Read before you count.** For contract payoffs, read >= 3 filings and write the payoff formula *first*.
4. **Two judging tracks** (pick by what the idea is, not by what looks better):
   - **Deal rule (contract payoffs, no N):** write the deal-selection rule and payoff formula as an amendment in
     `round1_prose.md` (like Round 32 family B), commit + push, THEN list every deal 2016-26 with its P&L at the
     odd-lot size and at 10% of equity. Report count/yr, hit rate, median, worst, $/yr at $2.3k/$10k/$25k. No
     tuning after the list. Use `event_runner deals` when an events file fits; otherwise a small script in
     `research/sim/`.
   - **Statistical (everything else):** the runbook path exactly (`prompt_event_runbook.md` Steps 2-7: explore on
     select data -> who pays -> pre-register with the next free N -> judge once -> write up).
5. **Write it up** (`research/drafts/study_<name>.md`), add a NEXT line (and a do-not-redo row if dead), update the
   claims line, commit, push. If it passes or a deal rule pays, add "Spec for a shadow/alert" (event source, check
   time, the manual or MOO/MOC steps, size, kill rule, digest line). Don't build it.

## 4. Discovery log (honesty)
Keep `research/drafts/discovery_log.md`: every look, one line each (time, idea, method, data window, what was
computed, result). A look you don't log is a look you're hiding. Enrichment scans log their K.

## 5. Order of work
1. Setup: merge, run the tests (`PYTHONPATH=. .venv/bin/python -m pytest tests/ -q`), note the current N (last
   amendment in `round1_prose.md`).
2. **Diverge first (no data on outcomes):** write `research/drafts/discovery_ideas.md` with **>= 30 ideas**, each
   with: method letter, the forced-trader or contract sentence ("<who> must <do what, when> because <rule>; a small
   long-only account gets <payoff> by <how>"), the form/phrase/data source, est. deals/yr, the small-size
   advantage, and a 1-5 novelty score with what you searched to check it. Add a kill column. Commit + push.
3. Rank the survivors by (expected %/yr at $2.3k-$25k) x (P it is real) x (novelty) x (hours of manual work, lower
   is better). Commit the ranking, then work down it.
4. Every 3 ideas: tests pass, `git status` clean for your files, re-read section 1.

## 6. Coordination
`ListAgents` once at start. Tell any session working in this repo that you're running this file, and message it
whenever you register an N. Don't take ideas claimed by others (llm-trader-0e holds B1/B3/B4, A1/A2).

## 7. STOP when any is true
- 8 ideas taken to a verdict (deal list reported, or judged, or explored-dead), not counting fast kills;
- the ranked list is used up;
- tests fail, or the same command fails 3 times across ideas.

A pass doesn't stop the loop: write its spec, then continue.

## 8. Before you stop
Append a morning summary to `research/drafts/discovery_log.md`:
- the table `idea | method | track (deal rule / statistical) | deals or trades per yr | verdict | $/yr at $2.3k / $10k / $25k | manual min/deal`;
- plain words: what is new and real, what died and the pattern behind the deaths, and what the user should do
  first (e.g. "open a savings account at X before the record date").

Commit, merge, push, then reply with that summary, short.
