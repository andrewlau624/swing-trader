# Index-beat hunt log (session llm-trader-ee, prompt_index_beat.md)

## STATE (update after every idea)
- program N: 760 (no registration by this hunt yet)
- k (ideas judged): 0 · ideas explored: 0 · idea rounds: 1 (55 ideas, index_beat_ideas.md)
- current idea: C1 (bot only in the Roth, taxable = index)
- next 5: A1 (round-up in more accounts), B3 (intraday-margin close selling), C5 (real tax rate), A8 (ID3 in the Roth), B8
- data sources verified: repo sims (program_books.joint, taxable_frontier.after_tax/mc_tax, roth_opt), night panel, roundup history, events_*.parquet
- data sources broken/unverified: E-mini overnight history (not free), option NBBO (paid), 23/5 quotes (forward only)
- why things die (running): (start) REGIME / REFIT / FALSE ALARM / HALF-FLIP / TAX / WHOLE SHARES / COST / GAP / LOTTERY / LOOKAHEAD / TEXTBOOK / STACKING

## Log
- 2026-10-02 13:20 setup: merged, 356 tests pass, N 760 (last registered: EV2). Messaged llm-trader-51 (Jump hunt), 198-da.
- 2026-10-02 13:40 round 1: 55 ideas written before any outcome (16 C, 19 A incl. 9 deal payoffs, 14 B incl. 7 forward-only, 6 wildcards).
