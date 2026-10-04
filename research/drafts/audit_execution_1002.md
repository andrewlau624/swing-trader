# Execution audit: live fills 2026-10-02 (and all 130 live fills since 09-23) — no slippage; the field mislabels drift

Read-only reconstruction (server logs + Schwab executionLegs + Alpaca SIP auction prints / NBBO). Nothing changed.

**Verdict: true execution cost is ~0bp. The +65..+240bp in `slippage_bps` is market movement between a decision-time
reference and the auction, not cost.** All 17 fills on 10-02 printed exactly at the official SIP auction price
(primary/largest 'O' or '6'); the SIP mid ~1 s before each auction was within +/-25bp of the print.

How the field is built (`slippage_bps = (px/ref - 1) x 1e4 x side`, executor.py:564-565; sign correct):
| leg | order | ref_px | what the "slippage" really is |
|---|---|---|---|
| night sell | market DAY sent 09:17, fills in the open auction | Schwab position mark at ~09:17 (executor.py:627, 1642) = often the pre-market bid | pre-market mark offset (up to ~28bp) + pre-open drift |
| IBS / T-bill | market DAY sent 09:17, open auction | prior official close (executor.py:826/834/851) | the overnight gap (XLE +133, XBI +159 on 10-02) |
| night buy | MARKET_ON_CLOSE sent 15:40 | Schwab last trade at ~15:40 (executor.py:1070) | 15:40 -> close drift (10-02: the -8..-15% losers rallied into the close) |
| noise exit | intraday | the ENTRY price (executor.py:1531-1536) | the trade's P&L, not cost |

Corrected cost since 09-23 (130 fills; vs the auction print, or the SIP NBBO mid at the fill second intraday):
open auction n=59 **0.0bp** (58/59 = the 'O' print); close auction n=57 **-0.2bp** (logged mean +21.3, sd 118);
intraday noise n=14 **+0.4bp** vs mid. The config.yaml "~0bp" claim holds for every fill type. The night backtest buys at
the close-auction price (`research/sim/night_exit_gap.py:13`), so 15:40 -> close drift is not a gap vs the backtest either.

Causes ruled out: real slippage, sign error, timestamp mismatch, delayed orders, split/dividend adjustment, wrong-day
data, Roth 3x-ETF mapping. Not verified: raw Schwab order JSON (fill prices from executionLegs match the prints exactly);
the daytrade L1 recorder holds none of these symbols; the executor's own exit-cost check says +2.0bp vs 0.0 here (it
scores against the SIP daily-bar open rather than the 'O' print; not reconciled).

Fix list (describe only, not done; live code was out of scope):
1. Split decision price from cost: keep `ref_px` as the decision price, add a cost field scored vs the auction print / NBBO mid.
2. `digest.py:256/264` feeds raw night-sell `slippage_bps` (~+43bp, mostly drift) into the "Overnight 1.3x" re-arm text as
   "open-sell cost": it will mislead the re-arm decision; use `_check_exit_cost`'s auction-relative number.
3. Night-sell ref = a 09:17 broker mark: use the prior official close or the pre-open mid, and label it.
4. Noise-exit ref should not be the entry price if the field means cost.
