# Study X — impact-optimal night cap: no variant adopted; the measurement loop is BUILT

Pre-registration: `round1_prose.md` Round 10 (commit 8f3e04a). Script: `research/sim/night_cap.py`.
Output: `data/research/program/night_cap_out.txt`. N = 614.

Rule: q_i <= q*_i = ADV_i (g / (3 Y sigma_i))^2, `signals.night_impact_cap`, g = 22bp.

## Registered verdict: none adopted
- "Inert at $2.3k" fails for every Y_rule: for ~300%-vol names q* is ~$10-150, so the cap
  binds on 1-18% of today's orders (pre-registration error: the claim was never checked).
- "Never below uncapped" fails for every Y_rule: under a low-impact truth any cap costs
  (A/Y 0.5 at $250k: uncapped $11.1k/yr vs Y_rule 4 $1.6k).

## What the table shows (night-leg $/yr; see output for all four truths)
| equity | truth A/Y 0.5: uncapped / Y_rule 4 | truth B/Y 0.5: uncapped / Y_rule 4 |
|---|---|---|
| $100k | $7,757 / $1,145 | −$23,887 / $146 |
| $1M | −$45,667 / $2,769 | −$1,046,323 / $1,004 |
| $5M | −$1.34M / $2,443 | −$12.5M / $473 |
Y_rule 4 is the robust choice (≥ 0 under 3 of 4 truths at every size; −$1k at worst), and it
shows the leg's ceiling: **a few $k a year at ANY size once impact is respected.** The right Y
is an empirical number, so the deliverable is the loop that measures it:

## Built (live code, off by default, 199 tests pass)
- `daily.night_impact_y` (null = off) / `night_impact_edge_bps` (22): the cap in the 15:40
  sizing loop, logged per capped name.
- `daily-decisions*.jsonl` now records `adv20` and `pct_adv` for every night order.
- `make review` section 8: fits Y = cost_bps / (sigma sqrt(fill$/ADV)), day-clustered SE,
  says when Y is identified. First run (paper, n 28): Y +1.6, 95% UB +6.3, not identified
  (orders 0.0001% of ADV). Expected to identify from ~$25k.
- Switch-on rule: when section 8 says identified, set `night_impact_y` to max(1, the fitted
  UB rounded up); until then set it to 4 by hand once the account passes ~$25k.
