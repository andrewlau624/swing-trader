# Plan changes

Every change to a plan in `daytrade/plans/`, dated, with why. A changed plan is a new variant: it gets its
own name (e.g. `gap_vwap_reclaim_v2`), its own pre-registration in `research/drafts/round1_prose.md`, and it
adds to the program N. Results of the old variant are never deleted.

| date | strategy | change | why | new variant / N |
|---|---|---|---|---|
| 2026-10-01 | gap_vwap_reclaim | created (Study AS) | first plug-in, the brief's popular pattern | N 669 -> 670 |
| 2026-10-01 | open_imbalance | created (Study AT) | first idea that needs the L1 recording | N 670 -> 671 |
| 2026-10-01 | gap_vwap_reclaim | clarification, written before any result: a signal skipped for R outside 0.2-5% does not end the day for that name; a later valid reclaim may still trade (still one entry per name per day). The ETF/fund name filter is the list in `daytrade/research/as_replay.py` (`NOT_COMMON`); it was narrowed once before the data was used (it had dropped real common stocks such as "Strategy Inc") | the plan's wording was ambiguous; code and plan must agree | not a new variant (nothing computed) |
