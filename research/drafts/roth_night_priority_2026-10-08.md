# Roth night-leg priority (2026-10-08)

## Cause (10-08, executor.py `_phase_close_night`, ~l.1063)
Night sizing uses virtual `book.cash` at 15:40. Roth book equity $1,000 = cash $157 + 3x noise longs $441 (SQQQ/SOXS, bought 14:01, flattened 15:57) + SGOV $402. Night loop skips a name when `cash - qty*px < floor`; Roth floor = 0. No code sells SGOV at 15:40 (SGOV is sold only by the IBS leg at the open when it has targets), and noise cash is not counted. So APUS 13 sh + AXTX 2 sh used $126, rest "book cash exhausted". Broker account had $7k, so this is book accounting, not real buying power.
M2L is NOT the alternative: `_roth_cash_log` is a log-only line (`k = cash/requested`); it never sizes anything.

## Frequency (8 Roth sessions 09-29..10-08; taxable 11 sessions)
- Roth cash-limited: 10-08 (7 names skipped, funded $126 of $500, shortfall $374), 10-05 (ACMR skipped + SPCG warn "only $470.77 free"; funded $35 of $71, shortfall ~$36). 2/8 sessions. SGOV was held on 10-05, 10-06, 10-08 (not on 09-30 after buying).
- Noise held at 15:40 only on 10-01 ($154) and 10-08 ($441).
- Taxable: 1 skip (10-01 SKDD), not noise/SGOV related.
- Total shortfall ~$410 requested of ~$2,050 over 8 sessions (~20%).

## Rule implemented (branch `roth-night-priority`, commit e958dd3, config `daily.roth_night_priority: "on"`)
`_roth_night_priority`: Roth only. Effective night cash = book cash + marked noise longs (they flatten at 15:57, before 16:00 close); if still < requested night notional, sell all SGOV (day order) and add its value. Raw cash still feeds the `[roth-cash]` shadow. On 10-08 this gives 157+441 = $598 >= $500, no SGOV sale needed, all 10 names (SIMO still 0 sh).
Not done: capping noise sizing, or flattening noise at 15:40 (unneeded when noise value is counted; noise only holds night money by design: `mult = 1 + (1-w_ibs)*(roth_etf_lev-1)`).

## Interactions / risks
- Settlement: the funding comes from unsettled 15:57 noise proceeds / 15:40 SGOV sale. Night shares are sold at T+1 open, when T proceeds have settled (T+1) -> no GFV per roth_cash_2026-10-08 audit (timeline not re-verified against Schwab's cash-account rule; confirm in account).
- If the 15:57 flatten fails, the night buy rides on the broker's other cash ($7k account) - book would go negative, floor guard not hit. Low risk, but watch `[roth-night]` line.
- SGOV sold at 15:40 is rebought by the IBS leg at next open only if it has no targets; for a day, idle ~$400 earns ~0.01%/day lost. 3x noise unaffected (still limited-margin-free, cash-funded).
- Existing test `test_roth_cash_log_and_a2_place_no_orders` pinned old starved sizing; it now sets priority "off". 20 other failures in these test files pre-exist (no `alpaca` module locally); my 3 new tests pass.

## Value (honest)
Night leg +98bp/trade net Jun-Oct 2026 (recent_regime) but that is a hot 4-month window; long-run validated ~+3bp/night tier (NX), haircut to ~+20bp/trade. Recovered notional ~ $410 / 8 sessions ~= $51/session; ~250 sessions -> ~$12.8k notional/yr on a $1k-capital book at 2/8 frequency. Marginal edge ~20-50bp.
- $1k Roth: ~+$13k x 0.2-0.5% = $26-64/yr = +2.6-6%/yr, but only if the shortfall frequency (2/8, tiny sample) holds; with 0.5x for frequency uncertainty ~ +1.3-3%/yr.
- $3k: shortfall scales with book; the issue is proportionally the same: ~ +1.5-3%/yr (limited by whole shares, fewer signals deployable).
- $10k: noise/night shares both bigger; one-share rounding matters less; ~ +1-3%/yr, falls if SGOV parking is a smaller share.
Treat as small, not a new edge; mainly removes a bug that cut 7 of 10 signals on the best day.
