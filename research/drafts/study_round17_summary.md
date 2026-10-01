# Round 17 summary: more %/yr at $2-25k (prompt_small_account_profit.md), N 642 -> 664

Studies AL-AO, 22 pre-registered variants + 1 post-hoc. One SHADOW (the cash-IRA Roth), one report
(the whole-share drag), the rest dead. All on `load_sim(raw_price=True)`; pass bar (SHADOW) in the
brief. Money is tier_hi (stressed), pre-tax, with 3bp (measured) where it differs. Code:
`research/sim/roth_cash.py` (AL), `night_limit.py` (AM), `night_quality.py` (AN), `ibs_whole.py` (AO).

## Ranked table (the brief's deliverable)

| rank | idea | verdict | %/yr and $/yr at $2.3k / $10k / $25k | capacity ($100k / $500k) | what live evidence would change it |
|---|---|---|---|---|---|
| 1 | **Start the Roth now: a cash-IRA IBS .5 + night .5 book** (no limited margin; no intraday leg) | **SHADOW** — clears the bar at the brief's stressed cost (t 3.06, placebo 99%, P(DD>50%) 0%) | 19.0%/yr at 5bp (22.0% at 2.5bp) -> **+$364 / +$1,582 / +$3,956** vs idle (tax-free) | IBS low single-digit $M; night ~$250k | Build the `cash_ira` mode; the gate is live night round-trip cost <= ~5bp (crossover ~6bp). Night kill rule (>=100 rt, losing, t<-1); if cost > 6bp -> IBS-only |
| 2 | Whole-share drag at $2.3k: IBS top2 + cheaper look-alikes | **REPORT** (below the 2.0pp bar) | +1.01pp at $2.3k, +0.55 by $25k -> +$23 / +$100 / +$250 | ~0 (drag is gone by $100k) | Schwab fractional shares for these ETFs; real QQQM/SPLG bars |
| 3 | Night-leg limit buys/sells at the bid/ask | **DEAD** | +$12 / +$50 / +$125 (AM3; ~0 in 2024-26) | thin names fine; needs quote data | An L1/ThetaData quote recorder; if the true 15:40 spread > ~10bp the limit is worth more |
| 4 | Night-leg pick tilt (drop US operating / 2x FOREIGN ADR) | **DEAD** | +$19 / +$84 / +$210 (AN1; t 1.86) | median ADV $40-57M, not binding | Forward picks: FOREIGN ahead of US_OPER by > 5bp with n > 400 -> new pre-registration |
| 5 | IBS selection: cross-sectional rank-1 / always-deployed / `ibs_max` 0.1 | **DEAD** | -0.3 to -7.6pp at every size | not the limit (IBS is low single-digit $M) | None: the shipped top-3/IBS<0.2 breadth is the edge |

For context, the pre-existing built-but-gated switches (not studied here) still dominate the DOLLARS
from live evidence already in hand: turning on the conviction trade (`DAILY_LIVE_PROFILE=moderate10c`,
+3.3pp = +$76 at $2.3k, +$844 at $25k — gate: ~5 clean intraday days), and `DAILY_INTRADAY_MULT`
(built, +~5pp with conviction at 4x). Ranked #1 above on **%/yr at today's money**, the cash-IRA Roth
is the only new thing that pays a five-figure sum over the next few years, because its $7,500/yr of
deposits compound in a 17-18%/yr book instead of sitting in T-bills.

## The studies

- **AL — the idle Roth (SHADOW).** A plain cash IRA is good-faith-violation-safe on the IBS leg
  (buy open d+1, sell open d+2 = the funding sale's T+1 date) and the night leg (buy close d, sell
  open d+1); only the 3x-ETF intraday leg needs limited margin. IBS-only 1.0 = 17.9%/yr tier_hi
  (14.1/22.1 halves), t 2.41, placebo 99.3%, P(DD>50%) 0%. Delay cost ~$890-1,010/mo vs idle; the
  $7.5k/yr deposits are the real prize of starting early.
- **AQ — the night-leg cost crossover (report).** `tier_hi` is 5-10x measured, not the brief's 2x.
  The cash-IRA **IBS .5 + night .5** book earns **19.0%/yr at 5bp** (22.0% at 2.5bp; crossover
  ~6bp; 7.5% at tier_hi). This is the recommendation; IBS-only is the fallback above ~6bp. The
  taxable V7 book: 32.0%/yr at 5bp, 18.6% at tier_hi.
- **AP — IBS selection (DEAD).** Cross-sectional rank-1 (with/without threshold), all-18 rank-1,
  rank-2 and `ibs_max` 0.1 all *lose* to the shipped top-3/IBS<0.2 leg (-0.3 to -7.6pp). The
  overnight-reversal edge needs the shipped breadth; concentration and always-deployment dilute it.
- **AM — limit orders (DEAD).** Best realistic close-buy (20bp below the 15:50 price): +0.96pp in
  2021-23, **+0.15pp 2024-26**, NW t 1.74. Sell limits -1.6..-2.6pp. "Adverse selection" is
  favourable (+33..41bp: filled names bounced more) but the fill loss eats it. The buy-at-the-low
  bound (+7.6/+8.7pp) is look-ahead. add. 13's +2pp was optimistic for implementable limits.
- **AN — pick quality (DEAD).** A point-in-time EDGAR classifier (fixes Study U's mislabels) shows
  FOREIGN ADR picks +5bp, US operating ~0, LETF not an edge (confirms Study W). Tilts are <=1.3pp/yr
  and fail t>=2 at planning cost; FOREIGN is 1.7% of picks.
- **AO — whole-share drag (REPORT).** ~2.0pp/yr at $2.3k (tier), ~0.2pp at $25k. IBS top2 +0.63pp,
  look-alikes +0.48pp, top2+look (post-hoc) +1.0pp — half the drag, below the adopt bar. IBS top1 is
  worse (-2.45pp); the IBS probe is inert.

## What failed, plainly

- **Night-leg limit orders did not clear the bar**, on either side, in either half robustly.
- **A proper pick-quality classifier did not produce a tradeable tilt** — the class spread is real
  but the actionably-large bucket (FOREIGN) is 1.7% of picks.
- **Whole-share drag cannot be fixed to the 2.0pp bar** with fewer picks or look-alikes at $2.3k.
- **The strict/alternating cash-IRA books (AL2/AL5) failed** (2.4% / 1.2%). [Correction: IBS+night
  is *not* dead — Study AQ shows it wins at the brief's stressed cost; only `tier_hi` kills it.]
- **IBS selection changes all failed (AP)** — cross-sectional rank-1, all-18 rank-1, rank-2 and a
  stricter gate lose 0.3-7.6pp; the shipped top-3 breadth is the edge.

## Open thread (not studied this session)

The brief's #5-#7 (multiple formation horizons / cross-sectional ranking; 0DTE options on the
conviction trade; tax location across accounts) were out of time. #7 is largely settled structurally
(every leg is <=1 session, 100% short-term; the cross-account part is the G4s guard).
