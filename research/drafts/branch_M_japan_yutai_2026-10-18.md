# Branch M: Japan shareholder-perk (yutai) ex-date over-adjustment (2026-10-18)

No N consumed, no judged backtest, no pre-registration (nothing repeatable enough to register). Probe is descriptive, touched ALL years 2005-2026.
Code: research/sim/branch_m_probe/{pull,an,an2}.py (cache in scratchpad m/). Data: WRDS tr_ds_equities ds2primqtprc (raw primary-quote open/close), ds2div
(FIN/INT/YR/HYR, JPY, estimated dates dropped), ds2ctryqtinfo (JP, EQ, primary quote, delisted included): 6,7k stocks, 102k ex-events.

## Literature (only items whose pages/abstracts I opened via search results; full texts NOT read)
- Huang, Rhee, Suzuki, Yasutake, "Shareholder Perks in Japan: Price Movement and Trading Volume Around Ex-Benefit Days", SSRN 2777549: perk stocks drop on ex-benefit day beyond cash dividend, excess volume (clientele valuing non-cash payout).
- "Do investors value shareholder perks? Evidence from Japan", J. Banking & Finance, ScienceDirect S0378426622001716: ex-day drop larger than estimated perk cost; higher ex-day volume.
- Univ. of Hawaii thesis (scholarspace.manoa.hawaii.edu ... c906452b-...): perk+dividend stocks drop more, higher volume than dividend-only.
- Sakai review (Ritsumeikan, file.jsp?id=645959): cites Aono et al. 2008 / Suzuki-Isagawa 2008 for significantly negative returns right after ex-rights. (Secondary citation; UNVERIFIED primary.)
- JSDA study-group report 2025-04 (jsda.or.jp .../250416_houkokusho.pdf): perk-for-dividend swaps give price falls beyond perk value (as summarised in search snippets).
- Practitioner, non-academic: note.com 135 Sept-perk obs 2021-25 mean ex-day -0.82% (excess -0.60%); systemtrade-kabu.com 450k events: March-end ex-day mean -1.53%, March-end at +5d -2.12%, all-events +10d fully unrecovered (+0.02%). Unreviewed, unverified.
- Cross trade (kurosu): no dividend-equivalent payment on loan stock for perks (unlike cash dividends), so the hedge is cheap; summarised from IR magazine/kabukiso snippets only. UNVERIFIED primary.
Literature agrees the over-drop exists. It does not show a recovery; practitioner data says March-end drops do NOT recover.

## Task 1: point-in-time perk list
None in hand. WRDS Datastream has no perk field; ds2sharehldgs (retail/free-float shares) is nearly empty for JP rows sampled. Public perk lists (broker pages, calendar blogs) are current snapshots, with survivor and look-ahead bias (perk programs are added/dropped, JSDA notes abolitions); JP EDINET/TDnet notices would be a manual PIT source (not collected).
Honest proxy used: record-date-end Mar/Sep ex-events (day>=24), SMALL traded-value tercile (20d yen turnover, per-year) x LOW dividend-yield tercile (perk issuers pay little cash). Bias: also catches thin low-payout firms with no perks; true perk names are a subset, so the proxy dilutes the effect. The ex-date drop itself was not used as a selector.

## Task 2: descriptive results
Market adjustment trap: on Mar/Sep month-end the cross-sectional median return is itself the ex-dividend drop (most firms have Mar FYE), so "excess vs median stock" shows a fake +70bp UNDER-drop in group A (all 22 years). Discarded; relative-to-same-date-ex-cohort used instead (median of that day's ex-events).
Group A = Mar/Sep ex-dates day>=24 (74k events). Median drop/dividend at close: 0.89 overall.
| bucket (A) | n | med yield | drop/div (close) | rel-to-cohort close excess | rel +5d | rel +10d |
|---|---|---|---|---|---|---|
| large / mid yield | 8.4k | 125bp | 0.88 | +1 | +22 | +50 |
| mid / low yield | 7.4k | 72bp | 1.07 | -20 | -5 | -28 |
| small / mid yield | 7.3k | 130bp | 0.86 | +3 | +8 | 0 |
| small / high yield | 11.6k | 219bp | 0.80 | +24 | -18 | -25 |
| **small / low yield (perk proxy)** | 5.0k | 75bp | **1.40** | **-49bp** | **+23bp** | **+19bp** |
Small/low-yield by year: close excess negative in 21/22 years (so the over-drop sign is stable, as literature says); +10d relative drift positive in 14/22 years, median +19bp, year values range -138..+275bp (noise, no pattern); recovery is <=40% of the excess drop and not significant. Open vs close: most of the over-drop is already at the open (-31bp open, -49bp close), so the intraday leg adds more drop, not bounce.
Not done: dividend-vs-perk value netting (perk values unknown), true perk-vs-nonperk matching, costs, tax.

## Task 3: access (all UNVERIFIED, nothing sourced this session)
IBKR is the assumed route to TSE (JPY, 100-share units, JPX ~9:00-15:30 JST with auctions); Schwab does not trade TSE directly. Costs, FX, and the 15.315% dividend withholding (not relevant to a no-dividend capture, relevant to holding through ex) not checked. Roth: foreign-market access and JPY FX through an IRA unverified. Cross-trade hedging needs Japanese margin/loan (not retail-accessible from US). Ex-date buy at JP close needs overnight exposure to JPY. Minimum lot ~100 x JPY 1-3k = USD 700-2,000 per name, so a $2.3-10k account holds 1-5 names.

## Card 1: perk-clientele ex-date over-drop recovery (Japan)
- Mechanism: perk-seekers buy cum, hedge via cross trade, dump at ex; counterparty is that clientele. Literature supports the over-drop (above).
- Evidence here: proxy bucket drops 1.4x dividend, rel excess -49bp, sign 21/22 years; recovery +19bp @10d median (14/22 yrs, noisy). The over-drop is real; the buyable bounce is not demonstrated, and practitioner data (March-end -2.12% at +5d) says it keeps falling.
- Ceiling at $10k: 2 clusters/yr x ~3 names x 19bp gross x 30% of account each (lot-limited) x 50% capture ~ 0.1pp/yr, before ~10-30bp costs/FX. Even full 49bp captured: ~0.4pp. At $2.3k and $25k: same order. Gate +8pp: KILL (ceiling).
- The opposite side (short cum / hold cross) needs Japanese loan market and gives the perk-cross arb to institutions: ACCESS-KILL.
- Verdict: CEILING-KILL (events cluster twice a year; deployable share per event small; recovery not shown). No pre-registration draft written because no repeatable excess-drop + recovery exists. Reopen only with a PIT perk list showing >=100bp recovery with t>=2 at +5d. Do not re-run the proxy buckets.

## Dropped
- Ex-day over-drop short side: no JP borrow access. Perk announcement/abolition drift: events/yr per name ~0, needs manual TDnet collection (not tested).
