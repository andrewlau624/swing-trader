# Index-beat DL-IB2: reverse splits with a round-lot top-up (no N) — DOES NOT PAY (too rare: one issuer)

Rule registered 0f32a57 before any event was counted. Script `research/sim/ib_dl2.py`, output
`data/research/program/ib/dl_ib2_out.txt`. EDGAR FTS ("round lot" / "reduced to less than 100" + "reverse stock split",
2016-26: 7,848 hits, mostly fund prospectuses) -> operating filers' split documents -> a protection-sentence regex -> 16
reverse splits with such a filing in the 90 days before ex.

Read by hand, 12 of the 16 sentences are the standard RISK FACTOR ("the split may result in a lesser number of round lot
holders"), not a promise. Genuine commitments: **American Rebel (AREB) only** — 2022-02-07, 2025-03-31, 2025-10-03,
2026-02-02 ("Stockholders holding at least 100 shares prior to the reverse stock split will retain a minimum of 100 shares
post-split"); AREB 2026-03-23 and Singlepoint (2021, 2023) were discretionary ("the Board may").

| AREB event | N | pre-split price | 100 shares cost | if topped up (E+2) | if not |
|---|---|---|---|---|---|
| 2025-03-31 | 25 | $0.068 | $7 | +$622 | +$18 |
| 2025-10-03 | 20 | $0.930 | $93 | +$478 | −$64 |
| 2026-02-02 | 20 | $0.277 | $28 | +$102 | −$21 |

Rule test: >= 3 events/yr in 2024-26 -> **fails** (~1/yr, one issuer); mean if topped >= $100 (passes, +$400); break-even
P(top-up) <= 25% (passes, ~3%). **Verdict: DOES NOT PAY (too rare).** Cheap to watch, though: a detector for the AREB-style
sentence ("will retain a minimum of 100 shares" / "will not own less than 100 shares") inside roundup_watch would cost
~$7-93 per hit with a +$100-600 payoff if the broker passes the top-up to beneficial accounts. NEXT line: "DL-IB2 (index
beat): round-lot top-up reverse splits = AREB only (4 since 2022, +$102-622 each if topped up); too rare as a rule;
optional: add the sentence to roundup_watch's alert text check (live code, user's call)."
