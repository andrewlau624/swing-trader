# Branch J: retail income paper ex-date under-adjustment outside US/Canada (2026-10-18)

No N consumed, no judged backtest. Probe = descriptive only, touched ALL years 2004-2026 in every market below.
Probe code: scratchpad `j/p4.py`, `p5.py`, `p6.py` (not in repo). Data: WRDS `tr_ds_equities.ds2ctryqtinfo` (typecode PREF + name regex
HYB|PERP|SUB RED|BBSW|NCPS|CAPS|RESET|PREF), `ds2primqtprc` (raw OHLC, primary quote), `ds2div` (effectivedate = ex-date, estimated dates dropped).
Same construction as `research/sim/intl_pref.py` (buy close E-1, sell open E, dividend added, same-currency only, |ret|<25%, y<8%).
Return numbers are GROSS descriptive medians in local currency unless stated; "net" lines use a placeholder 15bp round trip and a stated withholding rate.

## Verdict
No market clears the +8pp/yr stand-alone gate. Two are real additive candidates to the INTL-PREF/PREF-EX sleeve, both conditional on
an IBKR-type foreign-venue unlock and on foreign withholding that is not recoverable in a Roth:
South Africa (JSE bank/insurer prefs): strongest per event, thin and shrinking. Sweden (real-estate/holding prefs): most events, withholding-dependent.
ASX hybrids, UK, Germany/Austria/Italy (Vorzug), Japan, Singapore, Norway, NZ: dead or untestable (cards below).

## Descriptive probe (gross, CO = pc to open_E, dividend added; all years)
| market | n events | names | ev/yr 2015+ | y/event med | CO med bp | drop/div (open) | 2019+ CO med bp (n) | yrs CO-med>0 |
|---|---|---|---|---|---|---|---|---|
| ZA | 541 | 29 | 21 (12 now) | 4.4% | +169 | 0.61 | +185 (136) | 23/23 |
| SE | 900 | 42 | 66 (~45 now) | 1.7% | +62 | 0.63 | +49 (424) | 19/20 |
| AU | 2270 | 160 | 129 | 1.2% | +9 | 0.91 | +9 (1298) | 21/23 |
| DE (Vorzugsaktien) | 743 | 67 | 28 | 2.5% | +65 | 0.75 | +50 (198) | 23/23 |
| AT (Vz) | 132 | 26 | 8 | 2.3% | +61 | 0.73 | +50 (86) | 17/23 |
| IT (RSP/PRF) | 53 | 11 | 3 | 3.8% | +131 | 0.65 | +102 (22) | 21/21 |
| SG | 159 | 11 | 4 | 2.2% | +28 | 0.89 | +44 (10) | 14/21 |
| NO | 44 | 1 | 4 | 2.2% | +51 | 0.80 | +51 (31) | 10/12 |
| JP | 125 | 8 | 8 | 1.3% | -8 | 1.03 | +10 | 6/22 |
| GB | 285 | 19 | 11 | n/a | negative | 1.9+ | -41 | 3/23 |
| NZ, CH, BE, FR, HK | <10 events each | | | | n/a | | | untestable |

Controls: all-nights CO mean on ZA/SE pref quotes 2015+ = -3.7 / 0.0 bp (median 0); the ZA/SE ex-date effect is not a general open drift.
Caveat carried from INTL-PREF: Datastream opens may be back-filled, not first-print (open==close 19% of ZA/SE ex rows; CC median ZA +67, SE +37 is the open-free cross-check).
ZA by year CO median (bp/n): 2006 118/25, 2008 210/27, 2012 122/36, 2016 160/30, 2020 259/26, 2023 214/14, 2025 252/12: no decay, but n/yr is falling (30 -> 12) as the pref list shrinks.
SE by year: 2013 48, 2016 55, 2018 80, 2020 35, 2022 67, 2024 76, 2025 32, 2026 33 (n 36-110/yr, 13 names with events since 2024).

## Card 1: JSE preference shares (Standard Bank, Investec, Capitec, Discovery, Netcare, Grindrod; Absa/Nedbank history)
- Mechanism: cumulative/perpetual ZAR prefs held by retail and local funds; ex-date price falls only ~0.6 of the semiannual distribution (y 4.4%/event).
  Counterparty: local holders who do not value the dividend at full price on ex-date (tax-clientele/accrual pricing). Persists because the segment is small
  (about 7 live names, ZAR ~1.2M median ex-day turnover, roughly US$70k, from `ds2primqtprc` close*volume on ex rows).
- Evidence: table above (probe, all years touched). 23/23 years positive CO median. Not a judged result.
- Access: UNVERIFIED that IBKR trades JSE prefs, whether JSE has opening/closing auctions usable at the official print, and ZAR FX leg (a 1-night ZAR move has sd of order 100bp, comparable to the edge per trade; mean zero but adds noise). Schwab cannot.
- Withholding: UNVERIFIED. SA dividends tax 20% statutory; US treaty 15% shown as the scenario. Roth cannot reclaim.
- Net (descriptive, 15bp RT): WHT 15% mean +90 / median +86bp, hit 0.68; WHT 20% +68 / +66bp.
- Ceiling at $10k: events now ~12/yr x ~75bp net x deployable share. Turnover cap: 5% of ex-day turnover is ~US$3.5k per name, so about 35% of $10k per event; x 50% capture = 12 x 0.0075 x 0.35 x 0.5 = ~1.6pp/yr. At $2.3k deployable share rises to ~100%: ~2.2pp (and a $2.3k account cannot carry per-trade foreign commissions/FX spread, UNVERIFIED). At $25k ~0.7pp. Not stand-alone.
- Verdict: additive sleeve candidate ~+1-2pp, forward-shadow only; gated on access verification (user decision).

## Card 2: Nasdaq Stockholm preference shares (Corem, Sagax, Tingsvalvet, ALM Equity, Volati, Heimstaden, NP3, Emilshus, ...)
- Mechanism: same family as TSX/US $25-par income paper: quarterly fixed distribution, retail holders. Drop/div 0.63 median, 0.65 in 2019+. Counterparty: thin retail holders/non-institutional. 66 events/yr (2015+), ~45/yr now.
- Evidence: probe table. CO med +49bp 2019+, 19/20 years positive. Open-free CC median +37bp.
- Withholding is decisive: net of 15bp RT, WHT 15% mean +32 / median +21bp, hit 0.58; WHT 30% (default non-treaty) mean +3 / median -2. UNVERIFIED which rate IBKR applies at source to a US individual/IRA and whether relief-at-source works for Swedish nominee holdings.
- Ceiling at $10k: ~45 events/yr x ~20bp net (WHT 15%) x deployable ~35% (ex-day turnover SEK 0.8M median, ~US$75k) x 50% = ~1.6pp/yr; at WHT 30% ~0. Not stand-alone.
- Credit note: issuers are leveraged property holdcos; one-night hold has small credit risk, a gap on a distress day is possible (not measured).
- Verdict: marginal additive ~+1.5pp only if relief at source works. Lower priority than Card 1; combined J1+J2 ceiling ~3pp, still below gate.

## Dropped / dead (one line each)
- ASX hybrids (CBA PERLS, ANZ CAPS, Perpetual Credit Income, Multiplex SITES, ...): descriptive CO median +9bp, drop/div 0.91, net of 15bp RT ~-6bp median, hit 0.46.
  Franking direction: a one-night holder fails the 45-day rule, so franking credits (30/70 of the cash) are NOT captured; to the extent the
  ex-date drop includes franking value (drop/div > 1 would show it), the marginal holder prices it in. Observed 0.91 < 1 means cash is largely under-priced vs a cash-only holder, but the gap is 9% of a 1.2% dividend (about 10bp) before spreads. Unfranked distributions face 30% non-resident WHT (treaty 15% on interest-like): net -38bp. DEAD on size, not on mechanism. Note ASX hybrids can have wide quotes (UNVERIFIED).
- UK: CO median negative, drop/div >1.9 (sample is investment-trust/legacy split-capital prefs and old Vorzug listings, not retail income paper; retail bonds/ORBs not typed PREF in Datastream, UNVERIFIED coverage). Dead on probe; no reopen without a proper ORB universe.
- Germany/Austria/Italy Vorzugsaktien (Porsche, VW, Henkel, Fuchs, Draegerwerk, Sixt, Hornbach, Jungheinrich): these are non-voting ORDINARY-equity shares, not fixed income paper. CO median +50-65bp but drop/div 0.75 may be Datastream ex-date/convention noise; German WHT 26.375% (15% only after reclaim) makes net ~-16bp median at 26% (DE), -17 AT. Dead after WHT. Italy n=22 since 2019, too few.
- Japan: A-share/P-1 prefs (SoftBank, ANA, JAL, Infroneer) trade almost never; Global X US preferred listing is a US-pref ETF, not local paper. CO median -8bp, 6/22 years positive. Dead.
- Singapore (OCBC/DBS/City Dev NCPS): 4 events/yr since 2015, mostly delisted; 14/21 years. Dead (scale).
- Norway (Pioneer Property), NZ, Switzerland, Belgium, France, HK: single name or <10 events; untestable; ceiling-killed.
- Swiss/Euro AT1/hybrid bonds: OTC/large denominations, not exchange income paper (UNVERIFIED listing detail); excluded by the account's no-OTC-bonds constraint.

## Pre-registration DRAFT (not registered): INTL-PREF-J, JSE + Stockholm
Do NOT judge on 2004-2026 Datastream: this probe read every year of both series descriptively, so the sample is touched. Options:
1. Forward-shadow only (preferred): log-only, `intl_pref_shadow.py` pattern, symbols from the 2024+ live list (ZA: Standard Bank pref, Investec, Capitec, Discovery, Netcare, Grindrod; SE: the 13 names with events since 2024), rule CO identical to INTL-PREF: buy last trade/close E-1, sell at the official opening print on ex-date E, dividend credited at the stated WHT (15% scenario and statutory scenario both logged), cost 15bp RT placeholder (2x shock = 30bp), same-currency raw prices only.
2. Gate: >= 40 forward ex-night trades per market (ZA will take roughly 3 years at 12/yr: therefore pool ZA+SE, ~57/yr), net mean >= +15bp at WHT 15% AND at the actual measured WHT, median > 0, day-clustered t >= 2 on the pooled set, drop/div <= 0.9 median, ex-top-5 > +10bp, open price verified against the exchange's official opening print (not Datastream) on every logged fill, 2x cost shock still > 0.
3. Kill rule: pooled net <= 0 after 40 trades, or measured WHT at source > 20% (SE) / > 20% (ZA), or the official open misses > 20% of ex-days, or IBKR cannot route to the venue.
4. Untouched data for a retrospective check if wanted: none inside Datastream; a second source (exchange official open file) for ex-dates 2024-2026 only would be cleaner but is also touched descriptively. State this before running.
5. Prior to any build: user verifies (a) IBKR JSE/Stockholm availability and minimum commissions at $2-10k, (b) Roth/taxable withholding actually applied, (c) opening-auction participation by order type. All UNVERIFIED here.

## Priority note
Gate result: stand-alone dead (max ~2pp each at $10k). Additive value to the sleeve ~1-3pp combined, below the cost of a build plus foreign-account/FX/withholding friction until INTL-PREF access (TSX) is itself verified. Recommend: no build now; revisit as a log-only add-on only after the TSX IBKR path is decided.
