# Round 32 (event and structural edges): two contractual passes with alerts (round-up, split-offs), four dead

Brief: `prompt_event_edges.md`. Candidates (36, before any test): `event_edge_candidates.md` (e67e794). Rules and
pre-registration: `round1_prose.md` Round 32 amendment (cf5d8cf). Pipeline: `research/sim/event_fetch.py` (cached EDGAR
full-text search, filing headers with acceptance times, documents, quarterly full index; Alpaca reverse splits and raw
daily bars). Family A ran through ID3's registered evaluation (`insider_day.run`, unchanged).

## Results

### B1 — reverse-split round-up (family B): PASS as a free option -> `roundup_watch.py` alert
Script `research/sim/roundup.py`, output `data/research/program/roundup_out.txt`, deals `roundup_deals.csv`.
- 5,335 Alpaca reverse splits 2016-26 (2 <= N < 1000). 812 had a full-text-search round-up hit in the 90 days before
  the ex-date. **Correction before reading the deal table (same rule, tighter text match):** the FTS phrase alone also
  matched REIT ownership limits, convertible notes and board-seat counts (5 of 5 of the largest "deals" were such text),
  so a document qualifies only with a sentence about the split's fractional shares that rounds them up and has no cash
  alternative in it. A random 12 of the survivors read by hand: 12 genuine split round-up clauses (one, LABT, describes
  an earlier split in the past tense: a small overstatement; the live alert requires "will/shall/would").
- Excluded: 170 participant-level rounding (a 1-share holder gets nothing), 135 no split round-up sentence, 126 no bars,
  32 filed after 15:30 ET on the last pre-split session, 5 failed the price check (P_E / P_S / N outside 1/3-3).

| | deals | if rounded up: mean / median / worst | at E+5 | if cash in lieu instead | capital per deal |
|---|---|---|---|---|---|
| 2016-26 | 344 | **+$4.36 / +$3.56 / +$0.21** (100% > 0) | +$4.09 (worst −$0.26) | −$0.02 (worst −$1.37) | median $0.25 |
| 2024-26 | 231 | +$4.25 / +$3.45 / +$0.54 | +$3.87 | −$0.03 | $0.26 |

Deals per year: 2016-22 1-18, then 2023 69, 2024 91, 2025 66, 2026 (to Sep) 74. **Break-even probability that the
round-up is paid: 0.6%.** The payoff is per account, so the taxable and the Roth each collect it.

- **Unknown from history: does Schwab pass the extra share to a 1-share holder?** The rounding happens at the transfer
  agent and DTC; the issuer's 8-K says holders, but the broker allocates. The first 2-3 live deals settle it at ~$0.25
  of risk each.
- Issuers are adapting: 8-Ks pairing "rounded up" with "participant level" were 0 in 2018 and 2022 and 22 in 2025 (FTS
  counts); the watch skips them.

### B2 — split-off exchange offers with odd-lot priority (family B): PASS -> `splitoff_watch.py` alert
Script `research/sim/splitoff.py`, terms `research/data/splitoff_terms.csv` (read from the filings by an agent), output
`splitoff_out.txt`. 14 completed offers 2016-25, **all oversubscribed and all with odd-lot priority**.

| parent -> received | gain | | parent -> received | gain |
|---|---|---|---|---|
| BAX -> BXLT 2016 | +9.2% | | DHR -> NVST 2019 | +7.3% (cap) |
| LMT -> LDOS 2016 | +21.3% (cap) | | MCK -> CHNG 2020 | **−5.4%** (cap; March 2020) |
| PG -> COTY 2016 | +3.1% (cap) | | ECL -> APY 2020 | +30.4% (cap) |
| CBS -> ETM 2017 | +10.4% | | DD -> IFF 2021 | +15.2% (cap) |
| FTV -> AIMC 2018 | +6.7% | | MMM -> NEOG 2022 | **−8.8%** (flowback after the merger) |
| LLY -> ELAN 2019 | +7.5% | | JNJ -> KVUE 2023 | +5.8% |
| CMI -> ATMU 2024 | +16.1% | | LEN -> MRP 2025 | +6.2% (cap) |

Entry: the parent's close 5 sessions before expiry; exit: final ratio x the received stock's first close after expiry.
**Mean +9.1%, median +7.4%, 12 of 14 > 0, worst −8.8%, held 8-10 days.** The losses are the received stock falling
after delivery (Neogen's flowback; the COVID crash), not the contract. Value check at the last pre-expiry close:
median 1.076 x the parent (the 7% discount).

| | $2.3k | $10k | $25k | $100k / $500k |
|---|---|---|---|---|
| shares (<= 99, whole) | ~15-50 | 99 of most | 99 | 99: capped |
| $/deal mean (worst) | $201 (−$198) | $797 (−$867) | $1,461 (−$1,226) | ~$1,500 |
| $/yr (~1.4 deals) | **~$280 (+12%)** | **~$1,100 (+11%)** | **~$2,000 (+8%)** | ~$2,100 (+2% / +0.4%) |

**Live now:** Medtronic -> MiniMed (MDT -> MMED), $107.53 per $100, upper limit 4.5939, expires 2026-10-09 (midnight).
At the 10-01 closes the upper limit binds: 4.5939 x $19.60 / $86.44 = **+4.2%** (not 7%), ~$360 on 99 shares
($8.6k). Odd-lot priority confirmed in the offer. MMED has fallen ~13% since the launch (expected flowback).

### B3 — cash tender offers by acquirers (SC TO-T, merger arbitrage): DEAD
Script `research/sim/cash_tenders.py`, output `cash_tenders_out.txt`. 301 deals 2016-01..2026-03 with a parsed cash
price; Alpaca has bars for only 48 (acquired targets often vanish from the feed; 25 more failed the price check, mostly
the acquirer's ticker parsed by mistake). **The spread is gone by the first close after the offer: median +0.44%
(small targets, ADV < $5M: +0.47%)** for a ~30-day hold, about a T-bill. Failures cost −20..−42% (TherapeuticsMD,
Juno, Southwest Gas, Dawson). Mean −1.3%, median +0.3%, 60% > 0; small deals mean +0.6%. No small-size advantage:
arbitrage funds price even tiny deals. Coverage is the caveat (48 of 301), but the entry spread does not depend on it.

### B4 — going-private odd-lot cash-outs (family B): DEAD
Script `research/sim/cashout.py`, terms `research/data/b4_deals.csv` (agent-read; 49 deals: 37 odd-lot cash-outs, of
which 11 exchange-listed, 20 OTC, 6 no market). Listed deals: 9 of 11 paid +2..+49% over ~3-4 months (median +3.9%),
but Vestin traded above its cash price (−9%) and Anebulo abandoned the split for a tender and delisted (−89% under the
registered 365-day exit). ~1 listed deal a year, a 100-day hold, and a deal can turn into something else.
**Fails "worst loss small".** OTC deals (20) are outside Alpaca's data; not tested.

### A1 — Schedule 13D originals, next session open -> close: DEAD
4,402 13D originals (2020-07..2026-09) -> 1,321 trades (ADV >= $1M, price >= $5). **−45.8bp gross per trade** (median
−30.9), every year but 2024 negative; book −15.9pp at $10k, NW t −3.03, sign-flip 0%, placebo 0%; judge half −31.4bp.
The 13D jump is in the announcement gap; holders sell into the next session. DSR 0.000 (N 757; N 760 after EV2).

### A2 — 10%-owner purchases (no director/officer), next session open -> close: DEAD
10,078 filings -> 2,529 trades. +15.9bp gross (2021 +50, 2022 +28) but **2024-26 −6.3bp net** (t −0.37); full-window
NW t 1.14, sign-flip 85%. Fails (a), (b), (c), (g). DSR 0.02.

## Closing table

| event | fam | who pays | verdict | events/yr | $/yr at $2.3k / $10k / $25k | capacity | what live evidence would change it |
|---|---|---|---|---|---|---|---|
| Reverse-split round-up (1 share per account) | B | the issuer (a few extra shares) | **PASS -> alert** (`make roundup-watch`) | ~75 | ~$320 per account, ~$640 for 2 accounts: **+28% / +6% / +2.6%** if Schwab rounds up; ~$0 if not | fixed per account: same $ at any size | Schwab's treatment on the first 2-3 deals (1 post-split share vs cash in lieu) |
| Split-off exchange offers, <= 99 shares | B | the parent (a 6-10% discount to shrink its share count) | **PASS -> alert** (`make splitoff-watch`) | ~1.4 | ~$280 / ~$1,100 / ~$2,000 (+12% / +11% / +8%) | 99 parent shares: ~$2.1k/yr flat above ~$15k | a deal where the received stock falls > 10% after delivery |
| Cash tender offers (SC TO-T) | B | (nobody: spreads already ~0.4%) | DEAD (median +0.3%, worst −42%) | ~30 | ~−$30 to −$160 per deal | — | — |
| Going-private odd-lot cash-outs | B | the issuer | DEAD (worst −89%, ~1/yr listed) | ~1 listed | ~−$90 / −$470 / −$390 | holders below the ratio | — |
| 13D originals, next session | A | (none: holders sell) | DEAD (−46bp, t −3.0) | ~250 trades | −$352 / −$1,589 / −$4,003 | — | — |
| 10%-owner buys, next session | A | — | DEAD (judge half −6bp) | ~470 trades | — | — | — |
