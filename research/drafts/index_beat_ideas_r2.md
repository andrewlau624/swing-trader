# Index-beat hunt, round 2 (method: outside-literature sweep by a research subagent, 2019-26 sources), written before any outcome

25 candidates came back (links in the session log, summarized here). Mapped against the death map and the repo:

| r2 id | idea (source) | status before any run | track |
|---|---|---|---|
| R2-1 | Short-term legs in the Roth, long-hold sleeves in taxable (Vanguard / Morningstar asset location) | = C1/C2 (done: haircut-dependent) | C |
| R2-2 | Odd-lot priority self-tenders (Special Sits Digest, SEC Q&A) | live alert (Round 31) | A |
| R2-3 | Split-off exchange offers (mymoneyblog JNJ/CMI) | live alert (B2) | A |
| R2-4 | Reverse-split round-up (SIFMA white paper 2025, Computershare) | live (B1) + DL-IB1; note SIFMA wants it policed: adaptation risk | A |
| R2-5 | TLH with non-identical ETF pairs vs the book's ST gains (Chaudhuri-Burnham-Lo FAJ 2020) | C14 (only with an index core, C2) | C |
| R2-6 | Dividend payment-day SPY exposure (Hartzmark-Solomon NBER w30688) | A17 killed by bound (~+1pp gross on idle day cash, taxed) | A |
| **R2-7** | **Spin-offs bought after the index-fund selling (~20 sessions in), held > 1 year (LT tax)** (Cusatis-Miles-Woolridge; S&P spin-off index) | **NEW to test** (outside_box #23 killed as "well-known"; the dodge here is TAX: an LT hold in taxable, and a new window) | A |
| R2-8 | Split-off SpinCo flowback, buy ~40 days after (stockspinoffinvesting, n~10) | too rare (1-3/yr) -> killed | A |
| R2-9 | ETF creations at a premium -> next day (Xu 2022) | LOOKAHEAD risk (shares outstanding post T+1) + no free history -> killed | A |
| R2-10 | Monthly ETF flow reversal (Brown-Davies-Ringgenberg RoF 2021) | no free shares-outstanding history -> request only | A |
| R2-11 | Mutual-fund fire sales (Coval-Stafford; arXiv 2026) | N-PORT 60-day lag, heavy, TEXTBOOK -> killed | A |
| R2-12 | Month-end Treasury extension (Hartley-Schwarz) | calendar family dead (turn-of-month, IEF auctions) -> killed | A |
| R2-13 | Oct-31 fund tax-loss rebound (Gibson-Safieddine-Titman) | TOO RARE (2/yr) -> killed | A |
| R2-14 | 23/5 overnight-move reversal at the open (Eaton-Shkilko-Werner 2024) | forward-only; A20's pre-market prior says thin -> idea only | B FWD |
| R2-15 | Multi-day hold of margin-call losers (Bian et al.) | dead row (2/3/5-day losers) -> killed | A |
| R2-16 | Forward-split announcement drift | Jump hunt S5 owns it -> skip | — |
| R2-17 | Retail-attention veto on night picks (Barber et al. JF 2022) | Jump hunt's attention domain + night tilts dead -> skip | — |
| R2-18 | 1256 wrapper for the noise leg (XSP/XND) | = C11 (dead on COST; agent: XND spreads > 10% of premium) | C |
| R2-19 | XSP box spreads for idle cash (1256 interest) | bound: 9% tax saving x 4% yield x ~0.4 idle = ~0.15pp -> killed | C |
| R2-20 | Front-load the Roth | = C3 (dead) | C |
| R2-21 | Bond-ETF deep discounts in stress | TOO RARE -> killed | A |
| R2-22 | Reverse-split names as a night veto | = A19 (killed) | B |
| R2-23 | USO roll front-run | needs futures -> killed | A |
| R2-24 | Payday (16th) exposure (Ma-Pratt) | calendar family dead, weak -> killed | A |
| R2-25 | Morningstar-rating style flows | disputed, paywalled -> killed | A |
| R2-26 | DL-IB1b: the Alpaca live account (repo has an API client) as another round-up account | conditional on Alpaca passing round-ups; same as DL-IB1 -> fold into DL-IB1 | A DP |
| R2-27 | Tick-size / access-fee rules (agent: delayed to Nov 2027, SEC order 34-105656) | B4 killed: no 2026-27 effect | B |

R2-7 explore spec (written before any spin-off bar is fetched): SpinCos = Form 10-12B registrants 2016-2026 (EDGAR FTS
'"spin-off"' and '"spin off"' in forms 10-12B, 10-12B/A) whose FTS display name carries a ticker with Alpaca daily bars
starting after the first 10-12B filing; first regular-way session d0 = first Alpaca bar. Entry: the close of d0 + 20
sessions; exit: the close 260 sessions later (> 1 year: long-term in taxable). Return = split-adjusted close/close
minus SPY over the same dates; cost 2 x the ADV tier (jump_runner.cost_side). SELECT = entries 2021-01..2022-12 (exits
inside 2023); JUDGE = entries 2024-01..2025-09; HOLDOUT = entries 2016-2019. Select bar: >= 15 spin-offs, mean excess
>= +8% per spin-off (a ~1-year hold at ~1/3 of capital, enough for +2pp/yr after LT tax at EH), median > 0, ex-top-3
mean > 0. The one further variant (threshold now): entry at d0 + 5 sessions.
