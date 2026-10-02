# Index-beat hunt, round 4 (method: small-holder contractual-payoff sweep, research subagent), written before any outcome

| r4 id | idea (source the subagent found) | status before any run | track |
|---|---|---|---|
| **R4-1** | **Reverse splits with a round-lot top-up** (AREB 8-K Feb 2026: holders of 100+ never drop below 100) | **deal rule DL-IB2 registered (0f32a57); EDGAR count running** | A DP SMALL |
| R4-2 | Stock dividends whose fractions round up (NXDT Oct 2025 NYSE; PVBK OTC 2024) | reopens C16 (c5 found 0 listed 2016-26; NXDT is a counterexample): test with DL-IB2's scanner | A DP |
| R4-3 | Merger fractional round-ups at the beneficial level (ETRN/EQM 2020) | parked A3; rare (1-3/yr) | A DP |
| R4-4 | Bank checking bonuses ($100-900, 6-12/yr per person) | not investing; manual 15+ min; report to the user only | C (report) |
| R4-5 | Saver's Match from 2027 ($1,000/yr at AGI <= ~$20.5k) | **excludes full-time students and dependents** -> likely $0 for this user; report as a question | C (report) |
| R4-6 | Small-deposit broker sign-up bonuses ($30-150 each, recycle the $2.3k) | manual, one per broker; report | C (report) |
| R4-7 | IRA contribution match (Webull 3.5% ~ $223 net/yr) | = C10 (the bot can't run there; killed) | C |
| R4-8 | Mutual-bank depositor priority (conversion pops +10-25%) | manual, 1-3 yr lag, > 5 min/event -> killed as a deal (report) | A |
| R4-9 | CEF tenders at 97.5-99% NAV / CEF->ETF | = A4 / DL5 family (killed by bound) | A |
| R4-10 | Class-action / Fair Fund claims | ~$0-50, manual -> killed | C |
| R4-11 | Promo cash APY (Moomoo 8.1% 60d) | ~$30 -> killed | C |
| R4-12 | Shareholder perks (Carnival) | no cash value -> killed | — |
| R4-13 | Referrals | needs real people -> killed | — |
| R4-14 | ACATS transfer match (Moomoo 3%) | moves the bot off Schwab -> killed | C |
| R4-15..20 | ADR ratio changes, Australian SPPs, Irish odd-lot buybacks, ASX sale facilities, baby-bond consents, reverse/forward cash-outs | dead per sources (cash in lieu / US excluded / tiny / market price) | — |
| R4-21 | Extinguishing reverse splits (VISM 1-for-1,500 wiped lots < 750 with no cash) | a RISK for DL-IB1/2 scanners: add a "no cash / extinguished" check | — |
