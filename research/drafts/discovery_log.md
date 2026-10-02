# Discovery log (prompt_discovery_loop.md), session llm-trader-mid-01, 2026-10-02

Every look, one line. K = number of form types scanned in an enrichment scan.

- Setup: git merge clean; tests 327 passed; N 760.
- Wrote `discovery_ideas.md` (40 ideas, 8 killed; method letters A-F) BEFORE any outcome on them.
- Census: `F.full_index` form counts 2022Q1..2026Q1 (see ideas file); K (form types scanned) = 180.
- **I14 Reg SHO threshold-list close-out (method B): LOOK.** Nasdaq `dynamic/symdir/regsho/nasdaqthYYYYMMDD.txt` works
  by date (28/40 calendar days in early 2023; non-trading days 404 to an HTML error page). Daily list is only 16-39
  names with ~3 new additions/day, almost all sub-$2 thin names. -> far too few events for power and the wrong name
  profile (low-ADV, hard to borrow on both sides, often exiting the list before T+13). **Quick-kill**: not worth a
  registered test. No outcome looked at.
- **I29 CEF manager buys (method E): quick-kill.** Form 345 buys among N-2 filer tickers: only 58 in the whole
  cached window (2020-26). Too rare for power and likely a subset of ID3. No outcome looked at.
- **I26 insider exercise-and-hold (Form 4 code M, no same-day S) (method E): explored-dead.** 43,643 events
  2020-01..2026-03; select half ADV >= $20M: 9610 trades (2402/yr), net **-0.3bp**, median -1.8bp, hit 49%, t -0.11;
  by year +15.2 / +0.1 / -0.1 / -4.2bp. FREQUENT FAILS. (The exercise itself, unlike an open-market P purchase, puts
  shares in the insider's hands for free/at a strike, so it carries no purchase information.) Explored-dead.
- **I1/I2/I15 reverse-split round-up, pre-announcement/proxy window (method A/B): covered by B1, no new edge.** The
  proxy documents (DEF 14C 194 / PRE 14C 192 with split + round-up, 2020-26) do announce the round-up clause weeks
  before the ex-date, but the payoff formula is exactly B1's (1 share at the last pre-split close -> 1 post-split
  share); entering earlier is a split-announcement *drift* bet, which this round bans. The live `roundup_watch` already
  fires on the terms. No new test.
- **I37 odd-lot in same-issuer exchange offers (method A): quick-kill (too few).** The tender corpus has 18 exchange
  offers, of which only ~5 are same-issuer debt/preferred-for-equity (ELAB 2024, HFRO 2025, NXDT 2020, SQFT 2026,
  CDRPB 2025) — a handful over 10 years, and B2 already covers the paying split-off shape. Not enough events for a
  statistical test. (Method D also flagged SC TO-I, ratio 2.53, but over broad tender text.)
- **I4/I39 rights offerings with oversubscription at a fixed discount (method A): quick-kill (unidentifiable).** The
  phrase "over-subscription privilege" is dominated by shelf/ATM prospectus boilerplate (S-3 928, 424B5 2794 hit
  docs); genuine completed rights offers cannot be separated from the text without hand-reading, and the payoff
  (subscription price vs market) is ~0 (event_edge_candidates #9). Parked.
- **Method D enrichment scan (big 5-day moves, $1-100M ADV, 2020-10..2022-06): K=168 form types.** Script
  `research/sim/discovery_enrich.py`, output `data/research/program/discovery_enrich_out.txt`. 162,848 big-move
  events over 4,086 names; 89,256 issuer-days with a form in the prior 10 days. Top ratios (with tiny CIs at these
  counts): 8-K12B 5.62 (n 34), S-11/A 2.85 (17), 15-12B 2.69 (16), 144/A 2.53 (15), **SC TO-I 2.53 (46, CI [1.26,14.6])**,
  **25/25-NSE ~2.4-1.6 (135/360)**, S-3MEF 2.04, S-3 1.75, 424B5 1.72, 424B3 1.70, SC 13D 1.46. Most are either known
  dead (25-NSE), the banned drift family (the S-/424B- shelf forms), or contract families already covered (SC TO-I).
  The only un-tested candidate with a tight-enough CI was 8-K12B -> tested below and dead.
- **8-K12B (successor-issuer/shell registration), next session open->close (method D confirm): explored-dead.**
  134 events 2020-01..2026-09 (74 in the select window) -> RARE (~6/yr); ADV>=$20M: RARE gate FAILS. Deal report
  (select, ADV>=$1M, hold 1): 37 deals, hit 38%, mean -2.19%, median -0.91%, worst **-36.2%**. The successor usually
  trades down hard. Explored-dead.
- **I22 deregistration 15-12B/15-12G (method C): quick-kill.** Deregistering issuers move to OTC/unsupported; no
  Alpaca bars to hold or exit on, and the long side is a forced-seller *buyer's* trade we cannot take. No outcome.

---

## STOP: ranked list used up. Verdicts taken this session: I26 (explored-dead), 8-K12B (explored-dead). Quick-kills with
a written reason: I14, I29, I37, I4/I39, I1/I2/I15 (covered by B1), I22. The surviving families after 168-form
enrichment + contract probes are the ones already known: own-money (ID3/EV2) and odd-lot/round-up contract payoffs
(B1/B2, live alerts). No new independent book.

---

# Morning summary (discovery loop, session llm-trader-mid-01, 2026-10-02)

| idea | method | track | deals or trades/yr | verdict | $/yr at $2.3k / $10k / $25k | manual min/deal |
|---|---|---|---|---|---|---|
| I26 insider exercise-and-hold (Form 4 M, no same-day S) | E | statistical | ~2400 | explored-dead (net -0.3bp, t -0.11) | — | — |
| 8-K12B successor/shell registration | D | statistical (rare) | ~6 | explored-dead (rare gate; hit 38%, worst -36%) | — | — |
| I14 Reg SHO threshold-list close-out | B | — | ~3 new/day, sub-$2 names | quick-kill (no power, wrong names) | — | — |
| I29 CEF manager buys (Form 4 on funds) | E | — | ~10 total | quick-kill (58 in 6 yr; subset of ID3) | — | — |
| I37 odd-lot same-issuer exchange offers | A | deal rule | ~0.5 | quick-kill (too few; B2 covers split-offs) | — | — |
| I4/I39 rights offerings at a fixed discount | A | — | few | quick-kill (text unidentifiable; payoff ~0) | — | — |
| I1/I2/I15 round-up pre-announcement window | A/B | — | covered | no new edge (B1's exact payoff; live alert exists) | — | — |
| I22 deregistration 15-12B/G | C | — | ~120 | quick-kill (OTC, no bars; wrong side) | — | — |

**In plain words.**
- **Nothing new and real.** The 168-form enrichment scan over 162,848 big 5-day moves found no form type that both
  beat a matched base and survived the known dead/banned lists: the high ratios were shelf-registration paperwork
  (S-/424B, the banned drift family), delisting (25-NSE, dead), or tenders (SC TO-I, already covered). The one
  tight-CI candidate, 8-K12B, traded down hard (-2.2% mean, -36% worst).
- **What died and the pattern.** Own-money *purchases* (ID3, EV2) pay; own-money *exercises* do not (I26 = -0.3bp:
  an option exercise hands the insider shares at a strike, so it carries no purchase signal). Filing-form events do not
  drift in the session after (one more confirmation of the Round 33 pattern). Contract payoffs that pay are all
  already found: odd-lot tenders and the round-up/split-off clauses (live alerts).
- **What the user should do first.** Nothing new to build. Keep the two live research alerts running (`make
  tender-watch`, `make roundup-watch`, `make splitoff-watch`) and the ID3/EV2 shadow. The one open live question is
  still whether Schwab passes a reverse-split round-up to a 1-share holder (2-3 real deals settle it at ~$0.25 of
  risk each). No new N was registered; program N stays **760**.





- (session llm-trader-c5, second runner of this prompt) Looks, verdicts and the morning summary are in `discovery_log_c5.md`; ideas in `discovery_ideas_c5.md`. 8 verdicts: DL1 UMH DRIP 5% OCP **PAYS** (~$540/yr per person); DL2-DL7 and C6 dead or too rare. No N spent (760).
