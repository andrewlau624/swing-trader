# Discovery C6 (method D): form types before the biggest 5-day up moves — explored-dead (no candidate)

Session llm-trader-c5, 2026-10-02. Script `research/sim/enrich_scan.py`; tables `data/research/events/enrich_disc.csv`,
`enrich_conf.csv`. Exploration only (2020-10 .. 2023-12); nothing from 2024-26 was read.

**Design (fixed before the run).** Panel: SIP daily, split-adjusted, names with 20-session median $ADV $1-100M. Event:
close d → close d+5 >= +30% (one per name per 10 sessions). Controls: 5 random in-universe dates of the same name per
event (controls for each issuer's filing rate). A form "precedes" an event if the issuer (EDGAR CIK via
company_tickers, current tickers, so survivors only) filed it in the ~10 sessions up to d. Discover on 2020-10 ..
2022-06; a candidate needs ratio > 2 with > 30 event cases, then one confirmation on 2022-07 .. 2023-12 (ratio > 2,
p < 0.05).

**Result.** Discovery: 2,646 events, 12,506 controls, **K = 96 form types** (>= 5 cases). **No form type passes**:
every form with > 30 event cases has ratio <= 1.44 (S-1 1.44, FWP 1.32, SC 13D 1.31, 424B2 1.25, 424B5 1.24,
SC 13G/A 1.18, EFFECT 1.14, 6-K 1.12). Forms above 2x have 2-6 cases (SC TO-I/A 5, DEF 14C 3, F-4/A 6, F-N 3). Nothing
reached the confirmation window. **Verdict: explored-dead.** No form type flags a coming big move. At most, offering
paperwork (S-1/FWP/424B) is a bit more common before them, consistent with issuers raising into strength. A DSR
reader should count K = 96 looks against this scan; no N was spent because nothing was registered.
