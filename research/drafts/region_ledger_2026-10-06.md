# Research-region ledger (golden-egg loop, 2026-10-06)

| family | hypotheses tried | status | strongest attack | unexplored | why next |
|---|---|---|---|---|---|
| Corporate-action ex-date open (splits, spins) | ~12 (SPLIT-T0, SPIN-T0, EXDIV, ATTN, acquirer, rev split...) | STRONG CANDIDATE, forward shadow live on him; **locally explored, closed** | vendor-vs-tape stitching; recent-year decay | — | left on purpose (domain-jump rule) |
| Event drifts (uplisting, emergence, spin child) | 3 | REJECTED / short-side | long-only | short-side with borrow data | DATA-LIMITED |
| Dealer balance-sheet constraints (bond ETFs at quarter/year-end) | 1 (region B) | REJECTED | quarter-ends look like other month-ends (TME) | intraday/NAV-gap version needs NAV | — |
| **Product-induced forced flow (single-stock LETF rebalancing)** | 1 (LETF-NIGHT) | **STRONG CANDIDATE (in-sample)**: official crosses n 2009 +44bp t 2.17 med +32 | retail-attention confound (failed to explain: asymmetric, flat days negative); pre-2021 analog uninformative | intraday last-hour pressure; options/covered-call ETF (YieldMax) flows | new region; forward test needs OK |
| Insider sale supply (scheduled sellers) | 1 (D) | REJECTED | sales >= 15% of day $vol: -14bp intraday, no next-night reversal (-2..-4bp); small sales sit on up days (selection) | predictability step skipped (no reversal to harvest) | — |
| Tax-lot timing (IPO 1-year LT threshold) | 1 (A) | REJECTED (short side) | winners +160bp pre-anniversary -> -64bp post (LT selling); losers = momentum | short side needs borrow | — |
| Round-number order clustering | 1 (C) | REJECTED | crossings vs non-crossings at equal return: 1-8bp next day | intraday version needs minute data | — |
| Corporate treasury: buyback blackout windows | 1 (T) | REJECTED | open-minus-blackout median rises with buyback yield (+4 -> +35bp) but mean t 0.59, sign flips by year; <= ~3%/yr | daily buyback execution data (none free) | — |
| 24/7 asset vs session-bound stock (weekend BTC -> Monday crypto stocks) | 1 (X) | REJECTED | ETFs price the weekend at the open (gap beta 1.04); Monday continuation after >= +2% weekends +70bp/weekend, t 1.81, 58 weekends, 2024-carried; no mirror on down weekends | — | — |
| Financing: margin-call liquidation at the next open | 1 (M) | REJECTED | market <= -3% days: T+1 session -12bp (t -0.9), no open-liquidation rebound; idiosyncratic <= -10%: T+1 session -44bp t -4.3 (continuation, short side); the overnight bounce is the night leg | broker margin data (none) | — |
| Forced institutional selling via 13F filer disappearance | 1 (F) | REJECTED / DATA-LIMITED | only 54 stock-events with >= 0.2% of shares held by vanished >= $500M filers (2013-26); they keep falling (-25..-40% abn 6m), no recovery | true fund-flow fire sales need N-PORT (SEC UA) | — |
| Exchange auction mechanics: NYSE<->Nasdaq listing transfer | 1 (U) | PROMISING-small (sub-gate) | first night on the new venue +30bp t 2.54, median +23, 2013+ +31/+20; ~17/yr -> ~4%/yr | official-cross check not run (low ceiling) | — |
| Mechanically linked prices: dual share classes (24 pairs) | 1 (S) | PROMISING-small (cost-bound, needs a short leg) | |z| >= 2 spread -> 5-day reversion +30bp/pair, t 9-11, stable 2000/2013/2020+; 4 fills per round trip, ~5%/yr net on margin | long-only version only for holders of the company | — |
