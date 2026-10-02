# Discovery DL2: issuer offers for its own listed warrants (deal rule, no N) — DEAD

Session llm-trader-c5, 2026-10-02. Rule registered in `round1_prose.md` (amendment "deal rule DL2", 6d89505) before
any price. Script `research/sim/warrant_offers.py` (terms + `run`); deals `data/research/events/warrant_offer_deals.csv`.

**Contract.** After a de-SPAC, issuers clean up warrants with an SC TO-I: r shares (0.075-0.62) or $c cash per public
warrant, with a consent that lets them force the rest at ~0.9r. Read in full: Vivid Seats 2022 (0.240), Payoneer 2024
($0.78; warrant last $0.40), AvePoint 2024 ($2.50; last $1.87). 57 SC TO-Is found 2019-26; 12 were not warrant offers
(notes, preferred, fund, share tenders, unlisted warrants); 45 warrant offers; 38 have warrant bars at entry.

**Rule.** Buy the warrant at the close 5 sessions before the last SC TO-I/A; if the warrants stop trading (retired),
value = c + r x stock 2 sessions after; else the warrant's close 2 sessions after.

| | deals | mean | median | hit | worst |
|---|---|---|---|---|---|
| **all (registered)** | 38 (~4.9/yr) | **−2.2%** | **+0.5%** | **53%** | −69% (DRCT: $1.20 cash offer failed, warrant $0.36) |
| retired (completed) | 18 | +2.5% | +1.6% | | |
| still trading | 20 | −6.4% | −4.0% | | |
| share consideration | 29 | +0.6% | +0.6% | 55% | |
| cash consideration | 9 | −11.1% | −3.0% | 44% | |

$/yr at $2.3k / $10k / $25k (stake min(10% equity, 5% of warrant ADV)): **−$28 / −$94 / −$196**.
**Verdict (median > +1%, mean > 0, hit >= 70%): DEAD.**

Why: the warrant reprices to the offer the day it is announced; 5 sessions before expiry the remaining spread is the
failure risk (consents fail, offers get amended) plus the stock's move over the settlement days. No small-holder
clause: everyone tenders at the same ratio. Unlike odd-lot tenders and split-offs there is nobody prorated, so
nobody leaves money on the table.
