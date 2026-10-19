# Branch N — forced par redemption of CEF preferreds on asset-coverage breach (2026-10-18)
Status: descriptive only. No N consumed, no backtest, no pre-registration appended. Probes: `research/sim/branch_n_probe/`
(`crisis_desc.py`, `trigger_desc.py`, `edgar_fts.py`, `cov2020*.py`; outputs `*_out.txt`). Data touched: Sharadar SFP category
"CEF Preferred" (82 issues, first price 2012-12; 42 delisted), raw closes (`closeunadj`), 2015-16, 2018Q4, 2020-03, 2022, 2023-03. All crises are TOUCHED.

## Card N1 — "breach forces par redemption, so panic is floored": MECHANISM REAL, TRIGGER NEVER FIRED, VERDICT: CEILING-KILL
**Mechanism (verified in primary text).** Eagle Point Credit 424B3 (EDGAR 0001104659-23-070457), "Mandatory Redemption for Asset Coverage": if 1940 Act
asset coverage < 200% on the last business day of a calendar quarter and not cured by 30 days after that quarter's N-CSR/N-CSRS/N-PORT filing, the fund
must redeem within 90 more days enough preferred to restore 200% (or the max redeemable), at $25 + accrued. Oxford Lane N-CSR 3/2020 (0001615774-20-005611)
says the same (200% at each fiscal quarter end; may be "forced to sell... to redeem"). Frictions: (a) breach timing is quarter-end plus ~60-90 days to the
cure date plus up to 90 days to redeem = 5-7 months to cash; (b) the fund chooses WHICH preferred (any series, pro rata) and may cure by selling assets
or repaying debt instead; (c) only the shortfall amount is redeemed. So it is a slow, partial, discretionary put, not a par put.
**Counterparty/who pays:** the issuer's common holders (junior); the preferred holders are senior. Persistence: retail holds $25 paper by yield, not coverage.
**Evidence it never bound in a crisis (coverage was far above 200% when prices were -35..-50%).**
- OFS Credit N-CSRS 4/30/2020 (0001716951-20-000026): Series A coverage $60.30 per $25 unit = 241% (asset coverage per $1,000 = $2,412), vs OCCIP's trough
  $14.75 (-41%, 2020-03-19). `crisis_desc_out.txt`.
- Eagle Point N-CSRS 6/30/2020 (0001104659-20-095774): net assets $368.8M vs preferred $47.1M plus notes $28.9M (coverage roughly 5x); ECC prefs low only mild.
- Priority Income N-CSR FYE 6/2020 (0001554625-20-000089): $68 coverage per $25 unit = 272% at year end; its prefs fell to $14-16 on 3/16-3/18/2020.
- Oxford Lane (OXLC): ratio not parsed from the filing (tables not located) -> UNVERIFIED; OXLCM1 hit $11.72 (-53%).
- No 8-K/N-CSR hit found for an actual coverage-breach-triggered mandatory redemption of a listed CEF preferred in 2020, 2022-23 (EDGAR FTS queries in
  `edgar_fts.py`; hits were boilerplate charters). UNVERIFIED, but no breach is visible in the data: all 42 delisted CEF prefs end 23-26 (34), >26 (4), and
  the 4 under 23 are $10-par munis/MLP issues (NTX-PC, NXJ-PC, TYG-PB, TYG-PC), a par artifact, not losses. So principal loss in the sample = 0, but the
  cause is call/redemption by choice and rising coverage, not a forced-breach redemption.
**Conclusion:** the panic discount in 2020 was NOT a case of "price below a legally forced par"; coverage stayed 240-270+%. The floor logic (huge
overcollateralisation, senior, never lost principal) is real, but the market's discount was about portfolio-mark credibility, not breach.

## Descriptive evidence by crisis (Sharadar CEF prefs, raw close vs $25)
| window | issues | median low vs par | issues >=10% below par | >=20% below | notes |
|---|---|---|---|---|---|
| 2015-16 (energy) | 22 | +1.8% | 5 | 2 | 2 of 5 are $10-par TYG; real: OXLC prefs -12..-14%, rebound +12..14% by +20d |
| 2018Q4 | 30 | -1.3% | 4 | 0 | max -15%; +5..9% by +60d |
| 2020-03 | 35 | -12.4% | 22 | 11 | worst: OXLCM1 -53%, OXLCP -50%, PRIF-PC -44%, OCCIP -41% |
| 2022 | 43 | -13.2% | 31 | 7 | rate-driven, grinds Jan-Dec; trough rebound only +5-7% at +20/60d |
| 2023-03 | 43 | -11.8% | 27 | 6 | still the 2022 rate discount, little bounce (+3-5% at +60d) |
Trough-low-to-+60d medians (look-ahead upper bound, NOT tradable): 2020 +17%, 2022 +7%, 2023 +5%, 2018Q4 +4%.
Non-peeking trigger (first close <=80% of $25 inside the window; `trigger_desc_out.txt`; raw closes, no costs):
- 2020-03: n=11 issues (PRIF x5, OXLC x3, OCCIP, HFRO-PA, RMPL-P), entry 3/16-3/23: median +16% at +20d, **+29% at +60d, +30% at +120d**, 11/11 positive
  at +60d (min +17%); median max-adverse -11% in the next 120d (OXLCP -33%, OCCIP -26%). 5-day dollar volume per issue $40k-$670k (median $250k).
  At <=85%: n=13, median +22% at +60d, 13/13 positive.
- 2022: n=7 (<=80%) median +3.7% at +60d; 2023-03: n=6, +2.4%; 2018Q4: no issue reached the trigger.
- Context: SPY +33%, HYG +19%, JNK +22% over the same 3/18/2020 +60-session window (Sharadar SFP). The preferred rebound is the same size as the market rebound
  (not separated); concentrated in 2 sponsors (PRIF, OXLC), i.e. ~2-3 independent events, not 11.
- 2008-09 not tested: Sharadar SFP starts 2012-12 and listed CEF term preferreds were scarce (auction-rate preferreds dominated and froze in 2/2008) ->
  UNVERIFIED; a CRSP check is possible but INCOME-SHOCK already killed the broad $25-par panic rule on 2008-07.

## Access
NYSE/Nasdaq $25 paper, Roth-eligible, long-only, cash. Auction/close liquidity at the trough is thin ($40-670k/day per issue, widest spreads exactly at the
trigger); a $10k account needs 1-4 issues, one fill each, 2-5% of daily dollar volume: fillable. Schwab symbol+CUSIP routing quirk for slash tickers is
already handled (`SchwabAdapter._cusip`). Whole shares at $15-19 are no problem.

## Ceiling (research-priority gate)
Shape: **rare-event, ~1 crisis-class trigger in 2012-26 (2020 only; 2022-23 is a slow rate repricing paying +2-4%)**, i.e. ~0.07-0.12 events/yr.
ceiling at $10k = 0.1 events/yr x +29% median (descriptive, same period that defines the event, = the market rebound) x 100% of Roth cash deployable x 50% capture
= **+1.5pp/yr** averaged (full capture +2.9pp). Per event at $10k: ~$1.4-2.9k when it fires; at $2.3k ~$330-670; at $25k capped by $250k/day volume to maybe $5-7k.
Far below +8pp/yr, and the 29% is the market bounce. The 2022-23 analogue (the only repeated cases) has a ceiling of < 0.5pp. VERDICT: **CEILING-KILL**; the
"legal floor" does not add a distinct edge beyond INCOME-SHOCK/crash-beta. Nothing registered; no draft pre-reg warranted by the gate.

## If the user wants a free option on the next crash (not a research claim)
Pre-register DRAFT only, forward/next-crisis judged (2020 is touched, 2008 untested): trigger fixed ex-ante and not outcome-peeking: SPY closes >=25% below its
trailing 252-session high AND the SFP "CEF Preferred" basket median close <=80% of $25; buy 1/N of each issue with coverage >=250% on the latest N-CSR/N-PORT
and a term/maturity <=2030 (so call/term path to par exists), at the next official close cross, no leverage, hold to par-called or +120 sessions; kill: any
principal loss from a coverage-breach redemption below par, or median +60d < SPY. Zero capital otherwise. This is a dormant standing order, not a program edge.

## Dropped
- "Wait for an actual breach and buy before the forced redemption": no listed-pref breach observed in 2012-26; cycle is 5-7 months with issuer discretion.
- BDC prefs (150% test post-SBCAA): same structure, no breach seen in samples; folded into this card, not separately tested.
- Broad $25-par panic buying: INCOME-SHOCK (N 1021) KILL.
