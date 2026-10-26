# Research memory — hypothesis-map session (2026-10-25), N 1061-1064, all KILL

- **Map built:** `docs/research/hypothesis-space.md` (18 families x 7 mechanisms, every cell cited to a study id). After N 1060 only
  three cells cleared the +8pp-at-$10k paper gate on data on disk; all three measured this session, all KILL. No Tier A cell remains.
- **REC-RECALL (N 1061): KILL (WEAK by bars, placebo-equal).** Buy close E-5 / sell close E-1 in top-decile option-implied-fee dividend
  payers (CRSP 12xx x optionm.borrate 2001-24, 5,033 D10 events): +29/+21bp net excess (t 3.0/2.8) but the E-10..E-6 placebo earns the
  same; paired difference negative. **Data rule: `optionm.borrate` is a put-call-parity implied fee, so an under-projected dividend prints
  as "borrow fee" in the weeks before ex (D10 fee at E-6 is +22pp above E-36 in 92% of events).** Any fee read near an ex-date is
  contaminated; use a read >= 30 sessions before ex or a custodial fee. Side read: low-fee payers underperform their own baseline 12-20bp
  in E-5..E-1 (one look). Not tested: DEF 14A proxy record dates, post-record short side, E-36 fee read, 2025-26.
- **NIGHT-SHORT (N 1062): KILL.** Mirror of the night rule (day_ret >= +8%, IBS >= 0.90, short close cross -> cover open cross, 12bp):
  2003-15 excess -12.8bp/night t -3.0; gross excess ~-1bp. The short side of the night-leg family is closed at daily tier; it is
  short-beta + short-momentum, winning only in 2008/2022. **NIGHT-SHORT-20 (N 1064)** (the >20% bin, +53bp t 3.3 in-sample on 2003-15)
  judged on 2016-26: -27.6bp/night t -1.0, median +23 hit .56, ex-top-5 -44.5: squeeze profile, median wins, broad continuation tail
  (2018 -213, 2021 -266/night). Not tested: 15:40 form, ETB filter, holding past the open, 12-20% band.
- **STK-IBS-OPEN (N 1063): KILL.** The ETF IBS leg's open-to-open form on top-500 stocks (IBS<0.2, day_ret > -4%): 2003-15 net -4.1bp
  t -1.8 (gross +5.9 < 10bp RT), 2016-26 -1.6; by the d+1 open the bounce has happened; SPY/QQQ anchors +8bp on the same days. Not tested:
  other cutoffs/universes, multi-day holds, official 2021-26 open crosses.
- Remaining below-gate candidates (Tier B in the map): IBS on auction-traded crypto ETFs in the Roth (U6, +4-7pp, zero-cost extension of
  the live leg), Coval-Stafford 2-4q holds (U5, +3-4pp), Schwab fully-paid lending (U4, account action). Runners: `research/sim/rec_recall.py`,
  `night_short_mirror.py` (`--min-dr`), `stk_ibs_open.py`; outputs in `data/research/program/`.

## Market scan follow-up (2026-10-26), N 1065
- **LETF-REV (N 1065): KILL standalone** (day_ret <= -3% & single-stock-LETF pressure I >= 0.05, close -> open: +12.4bp t 0.8, excess vs
  the LETF-underlying universe -1.5, decaying). **Tilt read, edge unproven:** live night picks (<= -8%, IBS < 0.10) with I >= 0.05 earn
  +99.6bp/night net (t 3.3, median +153, hit .69, 88 nights / 30 names, 2024-26) vs +21.6 for I = 0; paired +58 (t 1.66). Named
  counterparty inside the live leg (the LETF must sell at the close). Next: log-only shadow NIGHT-LETF-TILT; a night size-up = user decision.
- **Round-up pipeline:** reverse-split supply is flat 2023-26 (~270 Jan-Sep); the 2026 delisting rule compressed time-to-split, not count.
  Live scanner is lead-time-bound (Alpaca announces 0-1 days before ex); EDGAR full-text discovery would add days. VIVK Roth round-up PAID.
- Market structure 2026: round lots by price (2025-11), half-penny ticks (2026-11), overnight sessions (2026-12-06), trade-through
  rescission proposed. Nothing tradeable now; the overnight session needs a data-capture plan before launch.
- **NIGHT-BOATS (N 1066): KILL.** Alpaca `feed=DataFeed.BOATS` serves Blue Ocean overnight minute/daily bars from 2024-09-16 (verified on
  this account; `feed=overnight` is invalid). A +1% resting overnight offer on the night picks: +22.6bp/night t 1.1, median 0, two
  catastrophe nights carry it. Overnight prints run ~+30bp above the open on printed picks (t 1.6), 61% print, median $76k, 20:00 ET
  front-loaded. Not tested: dynamic/VWAP overnight exit, entry side, exchange sessions from 2026-12-06.
- **Built (uncommitted):** NIGHT-LETF-TILT shadow (gate 40 tilt nights, paired >= +30bp, t >= 2, median > 0); round-up scanner rebuild
  (EDGAR discovery, outcome logging, regex fixes, `daily.roundup_order_mode`). Dry run found PARA 1-for-10 effective 2026-10-27 four days
  before Alpaca listed it.
