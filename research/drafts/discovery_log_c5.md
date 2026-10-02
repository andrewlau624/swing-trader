# Discovery log, session llm-trader-c5 (prompt_discovery_loop.md), 2026-10-02

Every look, one line. Peer session llm-trader-mid-01 logs in `discovery_log.md`.

- 10:40 setup: merge clean; tests 327 passed; N 760 (round1_prose.md, EV2).
- 10:42 FTS count probes (30 phrases x 2018/2022/2025, counts only) and form census 2020-26 (full_index, form counts only): see `discovery_ideas_c5.md` header.
- 10:48 found peer's `discovery_ideas.md` (I1-I40) + 6 claims; wrote `discovery_ideas_c5.md` (unclaimed rows + C1-C14), ranking, claims. No outcomes looked at.
- 10:55 I7 (A): FTS 4 OCP-discount phrases in S-3D/S-3/424B 2016-26 (~90 issuers); read discount sentences of each issuer's latest/earliest plan; read UMH (2019 S-3D, 2021 424B3, FY2025 10-K), YORW (2025 424B3), TDS, OKE, HASI, QNBC: fixed OCP discount only UMH, MNR. No prices.
- 11:05 registered DL1 (2f57a54). 11:07 ran `research/sim/drip_ocp.py` once: 203 months, mean +$47.40/$1,000, hit 93%, 11/11 years > 0 -> PAYS. UMH only ~$540/yr.
- 11:12 C1 (A): FTS 4 phrases SC TO-I 2019-26 -> 57 offers; read Vivid Seats, Payoneer, AvePoint in full; hand-read the ratio/cash sentence of every offer (12 excluded as not warrant offers). Probe: Alpaca has warrant bars (OPENW, SOFIW, CLOVW 2021) — availability only.
- 11:15 registered DL2 (6d89505). 11:25 ran `warrant_offers.run` once: 38 deals, mean -2.2%, median +0.5%, hit 53% -> DEAD.
- 11:30 C3 (A, C): FTS DEFM14C "per share in cash"+"written consent"+"merger" 2016-26 -> 57 issuers; read Datto, Ocean Bio-Chem, Sterling Check. Registered DL3 (f47fa76).
- 11:38 ran `consent_mergers` once: 12 cash deals, median +0.17%, hit 58% -> DEAD. Price parse errors (DWA, FOGO, TWKS) found after; corrected line (data fix, same rule) median +0.17%, hit 67% -> still DEAD.
- 11:45 I8 (A): FTS DEF 14A plan of dissolution + estimate 2016-26 -> 76 issuers; read Actua, Merrimack, Third Harmonic; Alpaca CA probe (liquidating payouts recorded as cash_mergers / special dividends, incomplete). Registered DL4 (aa91261).
- 11:52 ran `liquidations.entries` (+ a ticker lookup for 10 old names): 1 of 16 below the low estimate (OTIC); read OTIC 8-Ks: $0.11 paid -> +43%. Rule PAYS on n=1, 0.1/yr -> too rare.
- 12:00 C16 (A): FTS 8-K 5 round-up/forward-split/stock-dividend phrases 2016-26; strict sentence filter -> 8 issuers, 6 OTC shells (no bars), MIGI false hit, TRT 2-for-1 (integer, no fraction). Fast kill: no listed non-integer split/stock dividend rounds up at the holder level. No prices.
- 12:05 DL1 extension (forward-only, web): Chatham's 0-5% discount applies only to approved waivers > $10k/month; NNN 1% on reinvested dividends; no published monthly OCP discounts. UMH remains the only fixed small-holder OCP discount found.
- 12:08 I10 (A): FTS SC TO-T/A "subsequent offering period"+"accepted for payment"+"commenced" 2016-26: 45 issuers, 5 with a commenced-SOP sentence (Alcatel, LoJack, AVG, Talend, Calliditas) -> fast kill (< 1/yr). I6 fast kill by reasoning (no data). Claimed C15.
