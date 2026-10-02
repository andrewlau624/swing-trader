# Goal G1 (T5): the shipped contract-payoff stack on a SPY core, a bound (no N): NEAR at $10k, conditional on B1

Goal hunt, session llm-trader-ec, idea G1 (`goal_ideas.md`). No new rule and no new N: every part is an already-registered deal rule
(B1 round-ups, B2 split-offs, odd-lot tenders). This is a bound built from their own per-deal tables:
- `data/research/program/roundup_deals.csv` (B1, status ok = "rounded up" text and never "participant level")
- `data/research/program/splitoff_deals.csv` (B2, $ at each size with the 99-share cap)
- `study_oddlot_tenders.md` (~1.3 deals/yr x $120-150, the same dollars at every size)

The capital not in a deal sits in SPY, so the excess over SPY is the deal dollars after tax (deal holds are 1-10 days,
so the SPY given up while capital is in a deal is ignored; at most ~0.2pp). Tax: 35% short-term on the taxable deal
gains. The Roth keeps 100%.

| $/yr from deals | judge 2024-01..2026-09 (2.72 yr) | holdout 2016-20 |
|---|---|---|
| B1 per account (rounded deals: 235 judge / 25 holdout) | $1,008 / 2.72 = **$370** | $123 / 5 = $25 |
| B2 at $2.3k / $10k (judge: CMI, LEN; holdout: 9 deals incl. MCK −$122 / −$538) | $180 / $811 | $408 / $1,804 |
| Odd-lot tenders (any size) | ~$175 | ~$175 |
| **Taxable total at $2.3k** | $725 = +31.5% pre-tax → **+20.5pp after tax** | $608 → +17pp |
| **Taxable total at $10k** | $1,356 = +13.6% → **+8.8pp after tax** | $2,004 → +13pp |
| Roth $8.5k (B1 only: B2 and tenders count 99 shares across ALL accounts) | +$370 = +4.4pp | ~0 |

- **Lottery test:** without the 5 best deals in the judge half (CMI, LEN and the top 3 B1 deals) the taxable total at $2.3k is still
  > 0, since B1 alone pays. At $10k, B2 is most of the dollars, and dropping CMI + LEN leaves ~$545 = +3.5pp after tax.
- **Worst events:** MMM split-off 2022 (−$198 at $2.3k, −$867 at $10k); MCK 2020 (−$122 / −$538). The worst B1 outcome is cash in
  lieu (~−$0.3 a deal).

## Verdict: NEAR at $10k, conditional FOUND-level at $2.3k, nothing to build
- **At $2.3k** the stack clears SPY+10pp after tax in both the judge half (+20.5pp) and the holdout (+17pp), with 235 listed B1 events.
  But **B1 depends on Schwab rounding a 1-share holder**, which is unknown until VIVK settles (~2026-10-07; the first 2-3 live deals
  settle it). Without B1, $2.3k is ~+10pp (judge), right on the bar.
- **At $10k it misses:** judge +8.8pp (< +10pp), holdout +13pp. The per-holder caps that make it huge at $2.3k shrink it as the account grows.
- **Nothing to build:** all three parts already run (ROUNDUP_AUTO on, `make splitoff-watch`, `make tender-watch`). The only action is
  the one already true: keep the idle taxable cash in SPY, not BIL (index-beat C1 / R6-5 territory, not this hunt's to decide).
- **Combined with G2 (if G2-F passes forward):** at $10k it would be +8.8 + ~11 = ~+20pp after tax. That is the strongest $10k path
  in sight, and it waits on two live facts: the Schwab round-up (days) and 60 forward EV2-big trades (1-1.5 years).
