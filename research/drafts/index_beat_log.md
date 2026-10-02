# Index-beat hunt log (session llm-trader-ee, prompt_index_beat.md)

## STATE (update after every idea)
- program N: 760 (no registration by this hunt yet)
- k (ideas judged): 0 · ideas explored: 4 (C1, C3, C5: reports; A1 = DL-IB1 deal rule PAYS conditional) · idea rounds: 1 (55 ideas, index_beat_ideas.md)
- current idea: B3 (intraday-margin close selling, pre/post 2026-07)
- WAITING: DL-IB1 is FOUND only after 2 live rounded deals (VIVK ex 10-05, check ~10-07: read state/roundup-orders.json on him)
- next 5: A8 (ID3 in the Roth's idle daytime cash), C4 (475(f)), B8 (night pool own-bounce dial), A18 (whole-share leftovers at $2.3k)
- data sources verified: repo sims (program_books.joint/run_pair, taxable_frontier.after_tax, roth_opt), etf_daily (dividend-adjusted), night panel, roundup history, events_*.parquet
- data sources broken/unverified: E-mini overnight history (not free), option NBBO (paid), 23/5 quotes (forward only)
- why things die (running): HAIRCUT (new, C1/C5): at edge-halves the taxable book ~= SPY pre-tax, so tax/placement ideas are bounded near 0; plus REGIME / REFIT / FALSE ALARM / HALF-FLIP (C3) / TAX / WHOLE SHARES / COST / GAP / LOTTERY / LOOKAHEAD / TEXTBOOK / STACKING

## Log
- 2026-10-02 13:20 setup: merged, 356 tests pass, N 760 (last registered: EV2). Messaged llm-trader-51 (Jump hunt), 198-da.
- 2026-10-02 13:40 round 1: 55 ideas written before any outcome (16 C, 19 A incl. 9 deal payoffs, 14 B incl. 7 forward-only, 6 wildcards).
- C1 bot only in Roth + taxable SPY: C1-P -0.1..+0.2pp (2021-23), +3.6..+4.3pp (2024-26), +3.6..+4.8pp full -> NOT FOUND (one half). study_ib_c1_location.md
- C5 rate grid: at EH the taxable book loses to SPY held even at 0% (full $95.9k vs $111.9k); rate matters only without the haircut -> report
- C3 Jan Roth lump: +$296 / -$329 / +$60 per yr (2021-23 / 2024-26 / full) -> dead (half-flip, tiny)
- A1 / DL-IB1 (rule 7da5578): round-up in K accounts PAYS on history, $371/yr per account 2024-26 (ex-top5 $336), qualifying deals not falling; CONDITIONAL on Schwab rounding a 1-share holder -> not FOUND until 2 live rounded deals. study_ib_dl_ib1_roundup_accounts.md
