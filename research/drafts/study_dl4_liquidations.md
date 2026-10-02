# Discovery DL4: liquidations below the proxy's low estimate (deal rule, no N) — rule met once in 10 years (too rare)

Session llm-trader-c5, 2026-10-02. Registered in `round1_prose.md` ("deal rule DL4", aa91261) before any price.
Script `research/sim/liquidations.py`; entries `data/research/events/liquidation_entries.csv`.

**Contract.** A plan of dissolution proxy states a range of total distributions per share. Read Actua 2018,
Merrimack 2024, Third Harmonic 2025 (and Otonomy's 2023 8-Ks). 76 DEF 14As 2016-26; after dropping SPACs, 18
operating companies print a range; 16 have bars on the entry date.

**Result.** Only **1 of 16** closed below the low estimate the session after the proxy: **Otonomy (OTIC)**, entry
$0.077 vs. a $0.11-0.13 range; it paid **$0.11** on 2023-03-24 (record) → **+43% in ~6 weeks**. The others traded
**above** the low end, often far above (Vyant $0.68 vs $0.17-0.24, Histogen $0.66 vs $0.30-0.41, Marin $1.30 vs $0-0.10,
NovaBay $0.62 vs $0.13-0.97). Merrimack ($14.79 vs $14.68-15.30) and Third Harmonic ($5.15 vs $5.13-5.33) were
priced right at the bottom of the range, i.e. at the floor.

| | traded deals | per yr | median / mean | hit | $/yr at $2.3k / $10k / $25k |
|---|---|---|---|---|---|
| registered rule | **1** (OTIC) | 0.1 | +43% | 1/1 | ~$9 / ~$40 / ~$100 (one deal over 10.7 years) |

**Verdict as printed by the rule (median > 3%, mean > 0, hit >= 70%): PAYS, on n = 1.** It fails the loop's
kill-fast floor (< 1 deal/yr), so it isn't actionable as a deal list. **Practical verdict: too rare; DEAD as a
book.** The finding that carries over: the market prices dissolutions at or above the board's low estimate. The
discount sits in the odd case (a sub-$0.10 shell nobody watches). An alert would cost little to run (DEF 14A
"plan of dissolution" + price < low estimate), but it would fire about once a decade.
