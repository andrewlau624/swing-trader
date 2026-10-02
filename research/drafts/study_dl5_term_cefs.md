# Discovery DL5: dated-term closed-end funds in their final year (deal rule, no N) — DEAD

Session llm-trader-c5, 2026-10-02. Registered in `round1_prose.md` ("deal rule DL5", 80cbcc8) before any price.
Script `research/sim/term_cefs.py` (`funds_by_cik`, `DEALS`, `run`); deals `data/research/events/term_cef_deals.csv`.

**Contract.** A term / target-term CEF's charter makes it liquidate at NAV on a set date (unless a vote or the board
extends or converts it). Dates come from each fund's own N-CSR/N-2 sentence (FTS restricted to its CIK); a first pass
over shared family reports mis-attributed dates and was discarded before any price. Where no sentence was found the
registered fallback (the name's year) was used. CBH's parsed date (2031) came from a shared report, so CBH also uses its
name year (a data fix, logged). **23 funds scheduled to end 2019-2024.**

| | funds | excess vs matched ETF: mean | median | > 0 | worst |
|---|---|---|---|---|---|
| **all (registered)** | 23 | **−1.6%** | **−0.77%** | **35%** | −20.8% (IHIT; possibly missing distributions) |
| liquidated on schedule | 18 | | −0.77% | 33% | |
| extended / converted (BGB, BSL, JPT, NIQ, JPI) | 5 | | −3.7% | 40% | |

Fund total return over the final year: median +1.9%. $/yr at $2.3k / $10k / $25k: −$9 / −$40 / −$101.
**Verdict (median excess > +2%, mean > 0, > 0 in >= 70%): DEAD.** By the final year the discount has mostly closed
(term funds trade near NAV once the date is close), and what's left is the fund's leverage and credit mix against a
plain ETF. Winners (DCF, IHTA, JPI +8%) were 2023-24 high-yield rallies, not convergence. The two 2020 "terms" (BGB,
BSL) had already been extended, and a real trader reading the latest filing wouldn't have bought them. Dropping them
doesn't change the verdict (median ~−0.5%).
