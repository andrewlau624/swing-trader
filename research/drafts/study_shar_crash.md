# Study SHAR-CRASH — whole-book crash/stress replay, daily-bar form

**Pre-registration:** the "Study SHAR-CRASH" amendment in `research/drafts/round1_prose.md`.
**Status:** diagnostic. No pass/fail, no judged rule, **N unchanged (839)**, one ref, no variants,
no tuning. The noise leg is excluded (no pre-2021 minute data).

## What was run

Delisted-complete Sharadar bars (`~/data/sharadar`, SEP + SFP) let the two daily-bar legs be
replayed through the four stress windows. The combined book is `0.5*IBS + 0.5*NIGHT`, rebalanced
daily, **no leverage, no margin, gross of costs**. Runner: `research/sim/shar_crash.py`; output:
`research/sim/shar_crash_out.txt`.

- **IBS leg** — exactly the live rule (`book.ibs_days`): EQ18 ETFs, top-3 12-1 momentum chosen at
  the last month-end before d, `IBS(close d) < 0.2`, buy open(d+1), sell open(d+2). Return dated by
  the signal day d. ETF bars from Sharadar `funds` (split-adjusted).
- **NIGHT leg** — the daily-bar form of the live night leg, built through `nx.collect_trades`
  (`which="primary"`, delisted-complete common stocks, primary exchanges): `loser_picks` at the close
  (`close(d)/close(d-1)-1 <= -8%`, `IBS(d) < 0.10`, raw price 5..2000, ADV$ >= 1e7,
  `vol20 >= .60`, corr dedupe 0.7, `night_sizing(crowd_n=30, max_name_pct=0.10)`), buy close(d),
  sell open(d+1). `collect_trades` additionally applies the live `night_tilt(0.25)`, the weekend
  `gap_scale(0.5)`, back dividends and delisting prices, so the replay is the delisted-complete,
  tradable-outcome form of the live rule. **The daily close stands in for the live 15:40 decision.**

The combined daily return on session d is `0.5*ibs_ret(d) + 0.5*night_ret(d)`; a leg with no signal
that day contributes 0 (cash). Both legs are fully causal (signals use only data known at the decision).

## Results (gross, no costs)

| window | cum | maxDD | worst 5d | worst 20d | recover | halt .25 | lever .10 | IBS cum | night cum | n | IBS days | night days | picks |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2000-01..2002-12 | +278.4% | -24.07% | -11.02% | -20.74% | never | no | **YES** | -6.2% | +1286.6% | 752 | 329 | 639 | 7455 |
| 2008-01..2009-12 | +51.3% | -9.86% | -8.44% | -9.25% | 54 | no | no | +38.1% | +60.6% | 505 | 190 | 318 | 2075 |
| 2011-01..2011-12 | +17.3% | -8.35% | -5.10% | -6.31% | 28 | no | no | +12.0% | +21.5% | 252 | 82 | 123 | 337 |
| 2015-08..2016-02 | +2.1% | -8.25% | -6.65% | -3.45% | 10 | no | no | -4.3% | +8.0% | 145 | 52 | 112 | 425 |

Night outcome kinds per window (all kept; `delist_nopx` / `nobar_halt` score -100%):

- 2000-01..2002-12: `open:7452`, `delist_nopx:3` (GNET1 2000-10-12, SEG1 2000-11-21, IMNX 2002-07-15)
- 2008-01..2009-12: `open:2075`
- 2011-01..2011-12: `open:337`
- 2015-08..2016-02: `open:425`

- `maxDD` = peak-to-trough of the compounded curve; `worst 5d/20d` = worst compounded
  5- and 20-session return; `recover` = sessions from the trough back to the prior peak.
- `halt` = maxDD would breach `signals.HALT_DRAWDOWN` (0.25); `lever` = would breach
  `signals.LEVER_MAX_DD` (0.10). Only **2000-02** trips the leverage gate (-20.1%).
- No leverage was used: `sum(per) <= 1.0` on every session (max exactly 1.0), so the
  equal-weight replay never borrows.

## Reading

- **The daily-bar book survives all four windows gross.** The dot-com bust is dominated by the
  **night** leg (`ibs_cum -6.2%`, `night_cum +1286.6%`): 7455 trades over 639 nights (7452 open,
  3 full losses on names delisted with no usable price), mean 43bp per session, median 20bp, and
  still +851% after dropping the best 5 sessions. The IBS leg bought dips into a downtrend and went
  nowhere; the loser-bounce paid.
- 2008-09 is broad (IBS +38%, night +61%). 2011 and 2015-16 are small positive.
- The only stress that would have tripped a live gate is the 2000-02 leverage gate
  (`LEVER_MAX_DD` 0.10); the 0.25 halt was never approached in any window.

**Data-bug fix (this revision).** The first run filtered the night leg to `kind in {open,
delist_price}`, silently dropping `delist_nopx` and `nobar_halt` — outcomes the registered engine
scores **-100%** (`nx.py:623/625`), and which `nx.leg_series` keeps (`nx.py:670-675`). The fix keeps
every kind. It moves 2000-02 only (3 `delist_nopx`, no `nobar_halt`): combined +310.3% -> **+278.4%**,
night +1537.1% -> **+1286.6%**, maxDD -20.07% -> **-24.07%**, worst 20d -16.57% -> -20.74%. The other
three windows have no dropped outcomes and are unchanged. Halt/lever conclusions are unchanged:
-24.07% is still shallower than the 0.25 halt, and still trips the 0.10 leverage gate.

## Caveats (do not over-read)

1. **Daily-close proxy.** The night leg selects on the close and buys the same close; live decides at
   15:40 and buys the 16:00 auction. NX found the daily-close proxy ran ~1.7x the exact 15:40 rule on
   2016-20, and the exact 2003-15 edge was only ~+3bp/side at tier (regime-concentrated). Treat the
   numbers above, and especially the 2000-02 night blow-off, as an **optimistic upper bound**, not a
   forecast. The entry timing is nearly identical; the **selection** on the close is the optimistic part.
2. **EQ18 universe growth.** In 2000-02 only ~13-15 ETFs existed (IWM 2000-05, SMH 2000-06, EFA
   2001-08, EEM 2003-04, XBI 2006-02), so early IBS months rank momentum over fewer names.
3. **Delisting handling.** Inactive names are retained with delisting prices and back dividends;
   `delist_nopx` and `nobar_halt` outcomes are kept and scored at -100% (matching `nx.collect_trades`
   and `nx.leg_series`). The 2000-02 and 2008-09 night legs are the most exposed to any residual gap.
4. **Gross of costs.** Live auction cost is measured ~0bp, but per-side tier costs would reduce the
   night leg; the 7.5bp/side research assumption would roughly halve a 76bp mean pick.
5. **No leverage/margin/deposits** were modelled; the combined curve is the pure leg-weight return.
6. This is a **diagnostic**, not evidence for a new rule. It changes no live parameter and adds no
   forward test.
