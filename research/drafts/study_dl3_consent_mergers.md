# Discovery DL3: written-consent all-cash mergers (DEFM14C) (deal rule, no N) — DEAD

Session llm-trader-c5, 2026-10-02. Registered in `round1_prose.md` ("deal rule DL3", f47fa76) before any price.
Script `research/sim/consent_mergers.py`; deals `data/research/events/consent_merger_deals.csv`.

**Contract.** A controlling holder signs a written consent; the DEFM14C mails; the merger can close 20 calendar days
later (Rule 14c-2) once HSR / regulators clear. Read Datto 2022, Ocean Bio-Chem 2022, Sterling Check 2024. 57 issuers
2016-26; 17 have a stock leg (excluded), 12 more lack a parsable symbol/price or bars; **12 cash deals** priced.

| | deals | mean | median | hit | worst |
|---|---|---|---|---|---|
| **registered parse (most frequent "$X per share in cash")** | 12 (1.1/yr) | −4.7% | +0.17% | 58% | −41% |
| corrected price ("right to receive $X": DWA $41 not $35, Fogo $15.75, Thoughtworks $4.40) | 12 | −2.3% | +0.17% | 67% | −41% |

$/yr at $2.3k / $10k / $25k: −$12 / −$52 / −$132 (registered), −$6 / −$26 / −$65 (corrected).
**Verdict (median > +1%, mean > 0, hit >= 80%): DEAD** on both lines. Typical spread the session after the
information statement: +0.0-1.5% for ~1 month (Datto +1.5%, Ocean Bio-Chem +1.3%, Convey 0.0%). The −41% (Sears
Hometown) and the open Blue Buffalo row look like symbol reuse or bar problems in raw data. They don't change the
median. Once the vote is locked, the market prices these deals at roughly T-bill rates. There's no small-holder term.
