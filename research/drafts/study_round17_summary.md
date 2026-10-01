# Round 17 summary: more %/yr at $2-25k (prompt_small_account_profit.md), N 642 -> 664

Studies AL-AO, 22 pre-registered variants + 1 post-hoc. One SHADOW (the cash-IRA Roth), one report
(the whole-share drag), the rest dead. All on `load_sim(raw_price=True)`; pass bar (SHADOW) in the
brief. Money is tier_hi (stressed), pre-tax, with 3bp (measured) where it differs. Code:
`research/sim/roth_cash.py` (AL), `night_limit.py` (AM), `night_quality.py` (AN), `ibs_whole.py` (AO).

## Ranked table (the brief's deliverable)

| rank | idea | verdict | %/yr and $/yr at $2.3k / $10k / $25k | capacity ($100k / $500k) | what live evidence would change it |
|---|---|---|---|---|---|
| 1 | **Start the Roth now: a cash-IRA IBS-only book** (no limited margin; no night leg) | **SHADOW** — clears the bar (t 2.41, placebo 99.3%, P(DD>50%) 0%) | 17.1% / 18.3% / 18.5% -> +$320 / +$1,510 / +$3,825 vs idle (tax-free) | IBS low single-digit $M / same | Build the `cash_ira` mode; a 60-round-trip kill rule (mean <= 0, t < -1). Then the live IBS fills vs the backtest |
| 2 | Whole-share drag at $2.3k: IBS top2 + cheaper look-alikes | **REPORT** (below the 2.0pp bar) | +1.01pp at $2.3k, +0.55 by $25k -> +$23 / +$100 / +$250 | ~0 (drag is gone by $100k) | Schwab fractional shares for these ETFs; real QQQM/SPLG bars |
| 3 | Night-leg limit buys/sells at the bid/ask | **DEAD** | +$12 / +$50 / +$125 (AM3; ~0 in 2024-26) | thin names fine; needs quote data | An L1/ThetaData quote recorder; if the true 15:40 spread > ~10bp the limit is worth more |
| 4 | Night-leg pick tilt (drop US operating / 2x FOREIGN ADR) | **DEAD** | +$19 / +$84 / +$210 (AN1; t 1.86) | median ADV $40-57M, not binding | Forward picks: FOREIGN ahead of US_OPER by > 5bp with n > 400 -> new pre-registration |

For context, the pre-existing built-but-gated switches (not studied here) still dominate the DOLLARS
from live evidence already in hand: turning on the conviction trade (`DAILY_LIVE_PROFILE=moderate10c`,
+3.3pp = +$76 at $2.3k, +$844 at $25k — gate: ~5 clean intraday days), and `DAILY_INTRADAY_MULT`
(built, +~5pp with conviction at 4x). Ranked #1 above on **%/yr at today's money**, the cash-IRA Roth
is the only new thing that pays a five-figure sum over the next few years, because its $7,500/yr of
deposits compound in a 17-18%/yr book instead of sitting in T-bills.

## The four studies

- **AL — the idle Roth (SHADOW).** A plain cash IRA is good-faith-violation-safe on the IBS leg
  (buy open d+1, sell open d+2 = the funding sale's T+1 date) and the night leg (buy close d, sell
  open d+1); only the 3x-ETF intraday leg needs limited margin. IBS-only 1.0 = 17.9%/yr tier_hi
  (14.1/22.1 halves), t 2.41, placebo 99.3%, P(DD>50%) 0%; w 0.75 = 11.1% / -14%, w 0.5 = 6.9% /
  -12%. IBS .5 + night .5 = only 7.5%/yr — **the night leg is negative at stressed costs**
  (night-only = -3.4%/yr). Delay cost ~$890-1,010/mo vs idle; the cash book recovers ~$350-500/mo
  now, and the $7.5k/yr deposits are the real prize of starting early.
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
- **The cash-IRA Roth with the night leg (AL1) failed** — the night leg's stressed cost makes it
  worse than IBS-only; and the strict/alternating books were far worse still.

## Open thread (not studied this session)

The brief's #5-#7 (multiple formation horizons / cross-sectional ranking; 0DTE options on the
conviction trade; tax location across accounts) were out of time. #7 is largely settled structurally
(every leg is <=1 session, 100% short-term; the cross-account part is the G4s guard).
