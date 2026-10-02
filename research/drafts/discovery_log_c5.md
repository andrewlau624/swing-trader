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
- 12:20 I11 (A): FTS 424B3/S-4/DEFM14A "election"+"proration"+"fewer than 100 shares"/"holders of fewer than" (4 sample years): hits are split-off exchange offers (B2); Tesoro/Western 2017 read: no small-holder exemption. Fast kill.
- 12:25 C4 (A, B): Alpaca CA probe (IZRL, CTRU, BEDZ: BEDZ proceeds as cash_mergers). Registered DL6 (6c872de). Pulled all Alpaca cash_mergers 2016-26 (1,993) + asset names; 57 on "ETF" names; added the symbol-reuse guard (last bar within 10 days of the effective date) after seeing BITA/KEM/CCSB in the record list, before any return.
- 12:32 ran `etf_closures` once: 9 deals, median -0.24%, hit 33% -> DEAD.
- 12:36 I3 (A): FTS 8-K/SC TO-I/DEF 14A odd-lot program + "fewer than 100 shares" + premium 2016-26: 18 issuers, only SunLink 2017 (odd-lot tender $1.50 + $100/holder) pays a premium; the rest are Dutch tenders (Round 31). Fast kill (tender_watch already covers odd-lot SC TO-Is).
- 12:30 DL5 first pass (shared-report N-CSR sentences) mis-attributed dates (5 funds, BKT has no term): no prices were pulled. Second pass: FTS restricted to each term fund's own CIK (44 named funds), running.
- 12:45 C6 (D): enrichment scan, discover 2020-10..2022-06 (2,646 events / 12,506 same-name controls), **K = 96** form types; no type with ratio > 2 and > 30 cases (max 1.44, S-1) -> nothing to confirm; explored-dead. Confirmation window computed by the script but no candidate to look up.
- 12:55 DL5: per-CIK FTS dates for 21 of 44 named funds; final 23-deal table (`DEALS`, fallback name-year dates, CBH data fix); ran `term_cefs.run` once: median excess -0.77%, hit 35% -> DEAD.
- 13:00-14:10 DL7 (F): FTS 424B4 IPOs 2019-26 (doc prefetch in 6 threads, bars batched); ran `ipo_access` once: 502 IPOs; pessimistic (cold-only) 30-session median -7.4%, hit 40% -> DEAD; optimistic +14.6% (unattainable).

## Morning summary (session llm-trader-c5, 2026-10-02)

Stop condition: 8 ideas taken to a verdict (not counting fast kills). No N spent (all deal rules, plus one guarded
exploration); program N stays 760. Every deal rule was pushed to `round1_prose.md` before its list was computed.

| idea | method | track | deals or trades per yr | verdict | $/yr at $2.3k / $10k / $25k | manual min/deal |
|---|---|---|---|---|---|---|
| **DL1 UMH DRIP optional cash purchases at 95%** | A | deal rule | 12 (monthly, $1,000 cap) | **PAYS** (203 months, mean +$47, hit 93%, 11/11 yrs) | **~$540 / $540 / $540 (+23% / +5% / +2%)** | ~15 |
| DL2 issuer warrant exchange / cash offers | A | deal rule | 4.9 | DEAD (median +0.5%, hit 53%) | −$28 / −$94 / −$196 | 10 |
| DL3 written-consent cash mergers (DEFM14C) | A, C | deal rule | 1.1 | DEAD (median +0.17%) | −$12 / −$52 / −$132 | 5 |
| DL4 liquidations below the proxy's low estimate | A | deal rule | 0.1 | PAYS on n = 1 (OTIC +43%): too rare | ~$9 / $40 / $100 | 10 |
| DL5 term / target-term CEFs, final year | A, B | deal rule | ~4 | DEAD (median excess −0.8%, 35% > 0) | −$9 / −$40 / −$101 | 5 |
| DL6 closing ETFs, last week | A, B | deal rule | ~2 (with recorded proceeds) | DEAD (median −0.24%, hit 33%) | ~$0 | 5 |
| C6 enrichment scan (forms before +30% 5-day moves) | D | statistical, explore only | — | explored-dead (K 96; max 1.44x) | — | — |
| DL7 retail IPO-access allocations (a bound) | F | deal rule | 67 IPOs (28 cold) | DEAD (cold-only 30-session median −7.4%, hit 40%) | −$573/yr at $500/deal (optimistic all-filled +$8.9k is unattainable) | 5 |
Fast kills (no verdict): C16 forward-split/stock-dividend round-ups (no listed non-integer case in 10 years), I10
subsequent offering periods (5 in 10 years), I11 merger elections (no small-holder exemption), I3 odd-lot buyback
programs (one premium program, SunLink 2017), I6 CEF rights, I12 CVRs, C7-C14 (data or shape).

**What is new and real.** The UMH DRIP is a small-holder contract of the same kind as odd-lot tenders and split-offs.
The issuer sells new shares at 95% of a 4-day (H+L)/2 average to anyone, but caps optional purchases at $1,000 a month,
so only small holders can use it. It repeats every month, and 2016-26 lost money in only 7% of months. It's the
largest dollar item found so far at $2.3k. Monmouth ran the same plan until 2022; ~90 other plans only discount
waivers above $10k at their discretion.

**What died, and the pattern.** Every payoff with no per-holder cap or priority was already priced by the first
session the document was public: warrant offers, consent mergers, ETF closures, term CEFs, liquidations (15 of 16
traded at or above the low estimate). The edge only exists where the contract *limits who can take it* (odd lots,
monthly caps, round-ups). Contracts open to everyone at any size are arbitraged to roughly T-bill rates.

**What to do first.** Open a UMH DRIP account at Equiniti (UMH plan, "optional cash payments"): either certify the
Schwab shares (plan Q4) or enroll with the $500 minimum. Then send $1,000 before each 15th, and after it posts,
DRS-transfer the shares to Schwab and sell (study_dl1_drip_ocp.md has the alert spec). Taxable account only.
