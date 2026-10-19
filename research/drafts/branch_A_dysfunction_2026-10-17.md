# Branch A: historical market-dysfunction archaeology (2026-10-17)

Descriptive only. No rule backtested, no N consumed, no live code touched. All return figures below are descriptive
reads of the TOUCHED Sharadar $25-par panel (`winsig.load_panel(kind="pref")`: SEP "Domestic Preferred Stock" + SFP ETD,
2002-06..2026-10, raw prices = closeunadj, liquidity = volume x raw >= $1-2e5/day). Scratch scripts are in the
session scratchpad (a1..a9.py), not in the repo. Repo dedupe: PANIC-IDX (NEXT.md:1513, index-level, dead), PREF-DIP (N 880, normal-day dips, dead),
PREF-CRASH (issuer-common crash -> pref, winsig_prefcrash.py), idea_scan_events #5/#7 (ETN accel, SPAC floor: ceiling-kill).
Nothing in the repo tests a *cross-sectional dysfunction trigger on the $25-par income-paper complex*, and nothing
measures its quote spreads on a crisis day.

## Episode table (what I actually looked at)

| episode | observable trigger | anchor | gap at trigger / trough | closure | accessible at $10k? | verdict |
|---|---|---|---|---|---|---|
| Mar-2020 $25-par prefs + baby bonds (ETD) | EW 10d return of liquid $25-par paper (n~600) -8.6% on 3/11, -17.9% on 3/12 | par $25, pre-shock price (2/14), same-issuer senior debt | trough-day (3/18) median px/par 0.67; ETD median drawdown -41% from 2/14; G-SIB prefs -9..-36% | G-SIB prefs: median ~17 days to regain 95% of 2/14 price (fixed-rate long-duration GS/MS/MET: 100-150d); ETD median 64d, 8% never | YES: quoted spreads (SIP, 14:00-14:30 ET) JPM.PRD 18bp (3/18), WFC.PRQ 64bp, BAC.PRN 39bp, Qwest CTBB 164bp; 3/23 CTBB 96bp. Trough dollar volume $1-18M/day per G-SIB pref | **candidate** |
| Mar-2023 regional-bank panic | bank-issuer pref 60d drawdown >= 10% (3/13); EW 10d -9% | par; pre-shock price | bank prefs px/par 0.76-0.82 (3/13-3/23); failed banks (SIVB, SBNY, FRC) went to ~0 | surviving-bank prefs: fwd60 +2..+11%, fwd250 +14..+28% (n 67-69, 3/13-3/23 entries) | yes, but trigger does not separate failed from survivors in real time | small second episode of the same rule; **not** standalone |
| 2008 (trust-preferreds, bank/GSE prefs) | EW 10d <= -12% on 2008-07-14 and 2008-09-15 | par, but issuer solvency was the question | px/par 0.41 median 2008-10-10 | NOT a bounce at the trigger: fwd60 -27%/-25%, fwd120 -12%/-46%; liquid panel only n 26-42 names | n/a | **the failure case of the same rule**: prefs of insolvent issuers (GSE, WaMu, Lehman) are not mispriced |
| Aug-2011 downgrade/Euro | EW 10d -12.9% (2011-08-08, n 55) | par | -13% | fwd60 +12.9%, fwd120 +22.9% | thin sample | consistent with rule, tiny n |
| Feb-2018 XIV | n/a | indicative value | XIV closed 2/6 at 7.35; traded 5.10-6.23 on 2/7-2/15; acceleration paid ~$5.99 on 2/20 (web memory, not verified here) | the "anchor" is a live inverse-VIX position, not a fixed contract value: buyer on 2/8 was long the VIX path | | DROP (below) |
| Aug-2015 open, May-2010 flash | opening prints 20-40% off | ETF NAV | huge but intraday | minutes; trades beyond the clearly-erroneous band were busted; retail MOO/limits not filled at those prices | no | DROP |
| 2022 UK LDI | gilt yields | n/a | none in US-listed instruments | n/a | n/a | DROP |
| 2021 Archegos block unwinds | VIAC -27%, DISCA -27% on 3/26 | none (no contractual value) | n/a | VIAC never regained its pre-block price in months | | DROP |
| 2022 SPAC trust collapse | units/shares < trust | trust $/share + redemption right | 0-5% | weeks-months | | DROP (CEILING-KILL already: idea_scan_events #7) |
| 2020 oil ETNs / ETN accelerations | issuer notice | indicative value | one-off (OIL delisted 2023-06) | | | DROP (idea_scan_events #5, ceiling <0.3pp) |

## Candidate card 1: INCOME-PAPER-SHOCK (dormant crisis rule on $25-par prefs and baby bonds)

**Mechanism.** In a fast liquidity shock the holders of $25-par income paper are retail income funds, levered CEFs/BDCs,
mutual funds with redemptions, and mortgage-REIT/bank balance sheets. They sell what is liquid, indiscriminately, in days,
while the market makers that normally intermediate this thin paper widen out. Each security is a contract with a stated
par ($25), coupon and (for baby bonds) maturity, issued by an entity whose senior obligations are still being paid. The
anchor is par / the pre-shock price / the same issuer's senior bond yield; the gap closes when funding pressure ends, not
when the issuer's credit changes.

**Who must act.** Forced sellers: levered fund deleveraging (CEF/BDC/mREIT repo calls), ETF redemptions (PFF/PGX net
sellers of the underlying), open-end fund outflows. They sell at any price in days.

**Why it persists.** It needs an accessible, patient, unlevered buyer in the 3-10 days when the complex gaps. Funds
that could buy are in the same redemption; retail Roth cash is exactly that buyer. It pays nothing in normal times, so no
fund runs it as a standing strategy. Because the wide-spread days are brief, only small size clears the offered prices.

**Evidence in hand (descriptive, touched panel; panel is survivorship-limited).**
- Mar-2020, entry on the first trigger date 2020-03-12 (10d EW -17.9%): all liquid names (n 557) fwd60 median +12.3%,
  fwd250 +22.0%; names with px <= $20 (n 138): fwd60 +31.2%, fwd250 +51.3%, p10 of fwd250 +31.3%, 2% below -30%.
  Entry on 3/18 (the near-trough close, not knowable): px <= $20 (n 393) fwd60 +57.7%, fwd250 +80.6%. NaN fwd250 12-15% (called/delisted; delisted-at-par outcomes are the
  likely cause but the panel does not carry the final cash, so this can bias either way).
- G-SIB prefs 3/18 (JPM, BAC, WFC, C, GS, MS, USB, PNC, SCHW, MET): troughs -9% to -45% vs 2/14, median days to regain 95% of the 2/14 price: low tens for fixed-rate
  JPM/BAC/WFC/C/SCHW series, 100-156 days for GS-PA/PC/PD, MS-PA, USB-PH, WFC-PQ/PZ (floating or long-duration).
- Executable: Alpaca SIP quotes (14:00-14:30 ET) 3/18/2020: JPM.PRD mid 22.16 spread 18bp; WFC.PRQ 18.73 / 64bp;
  BAC.PRN 19.20 / 39bp; Qwest CTBB (6.5% 2056 baby bond) mid 11.79 / 164bp, and 16.61 / 96bp on 3/23 (+41% in 3 sessions).
- Failure evidence (same trigger): 2008-07-14 and 2008-09-15 EW 10d <= -12% -> fwd60 -27%/-25%, fwd120 -12%/-46%. 2022
  (rate-driven, slow): px/par 0.83-0.90 median, fwd250 +4..+5%; a speed trigger (10d, not 60d) excludes it (no 10d <= -8% date in 2022).
- Trigger count, 10d EW return <= -8% (clustered by 60d), 2004-2025: 2004-05, 2007-08, 2008-03, 2008-07, 2011-08, 2020-03, 2023-03
  (7 in 22 yrs); <= -12%: 2008-07, 2008-09, 2011-08, 2020-03 (4). Liquid panel before 2020 is only 23-55 names.

**What invalidates it.** An issuer-solvency crisis (2008): the sellers are right. A rule without an issuer-quality
screen loses 25-45% in that class. Evidence the screen can be real-time: restrict to G-SIB/TLAC-regulated bank prefs, regulated
utilities and investment-grade operating-company baby bonds (senior bond YTM from TRACE/FISD, or the issuer's own common not in a drawdown beyond X); 2008 prefs of GSEs/WaMu/Lehman would be excluded,
but BAC/C/WFC prefs themselves fell 50-60% in 2008-09 and took 12-24 months, so the G-SIB screen alone does NOT fix 2008.

**Frequency.** Full-scale shock ~1 per 6-10 years (2008, 2020), small shock (2011, 2023) ~1 per 5 years. Assume 0.15 tradable events/yr.

**Payoff / event, downside, lock.** Honest entry (first trigger day, staged: 1/3 at trigger, 1/3 at -10% more, 1/3 at -20%): +15..+35% over 60-120
trading days in 2020-type and 2011/2023-type events, -25..-45% in a 2008-type event. Sleeve is long-only, unlevered, Roth-eligible (qualified dividends accrue). No contractual
capital lock; the paper is exchange-traded, but the payoff clock is 60-250 days.

**Ceiling.** events/yr x payoff x share x capture. At $10k: 0.15 x 25% x 100% x 50% = **+1.9pp/yr** if every event is a 2020-type win; with 1-in-3
events a 2008-type loser (-30%): EV/event +6.7% -> **~+0.5pp/yr**. Dollar scale per event at +25% before capture: $575 at $2.3k, $2.5k at $10k, $6.3k at $25k
(capacity not binding: trough-day dollar volume per name $1-18M). Fails the +8pp/yr stand-alone gate by 4x-16x. Its value is shape
(zero cost 85-90% of years, 25%+ in the year it fires), not annualized yield; I would not build it for the annualized number.

**Data path.** In hand: Sharadar $25-par panel (2002+), Alpaca SIP quotes (2016+), WRDS TRACE/FISD for the issuer-bond anchor (2002+).

**Cheapest falsification test (pre-registration spec).**
1. Universe: Sharadar SEP "Domestic Preferred Stock" + SFP ETD, raw price 5-60 and |median price - 25| <= 3 in the prior 60 days, 20d $volume >= $200k, >= 40 names with data on the date.
2. Trigger T: first date (cooldown 120 trading days) with EW 10-trading-day return of the universe <= -10% AND universe median px/par <= 0.90.
3. Screen S (fixed before looking): issuer is a US G-SIB/large bank, regulated utility, or an issuer with a TRACE senior bond whose 20d-prior yield was < 8% (IG/BB+).
4. Entry: close of T and +5, +10 trading days, 1/3 each (staged); exit close at +60 and +120; metric = net of 2x quoted half-spread proxy (use daily (high-low)/close x 0.5 as cost) EW return of S-names vs holding BIL.
5. Judge: each event separately (event-clustered, n will be ~4); pass = >= 3 of 4 events positive at +60 AND the 2008 events excluded only by S (not by hindsight); report ex-top-1 name and the 2008 result unconditionally. Do NOT call it a PASS with n=4: the only possible outcomes are "consistent with a one-episode mechanism" or "killed by 2008".
6. Period: 2002-2026 is touched by the descriptive reads above; the genuinely untouched evidence is (a) TRACE issuer-bond series 2008-09 and 2020 (unread), (b) the next shock, forward. A forward log-only trigger monitor (zero cost: compute T daily from the existing preferred ingestion) is the honest next step; it fires in ~1 of 7 years.

## Candidate card 2: BABY-BOND vs SAME-ISSUER SENIOR BOND (the anchor version of card 1)

Narrower and more documentable than card 1: only baby bonds (SFP ETD, debt not preferred equity) of issuers that also have a TRACE-quoted senior
bond. Anchor = senior bond price (or YTM) ; gap measure = baby bond YTM minus senior YTM at the same maturity, which should be ~50-150bp but blew out to 600+bp for solvent issuers
on 3/18/2020 (Qwest CTBB mid $11.79 on 2020-03-18 vs par $25, SIP quote above; I did NOT open the matching Qwest senior bond price, so the senior-bond anchor is unverified).
It excludes issuers where the senior bond collapsed too (DHC, TravelCenters -60..-75% troughs in the same table look like real credit fear; ETD median drawdown -41%, 8% never regained 95% of 2/14 within 2020, with ~half of the deep names (DHC, RCB/RCA/RCP, NSS) still down at year end).
Mechanically the same events as card 1, so it shares frequency and ceiling; the point is that it is the version with a *documentable* per-security anchor rather than a basket
bet. Test: card 1 steps 1-6 with S = "TRACE senior-bond-to-baby-bond YTM gap > 400bp AND senior bond price within 8% of its 20d-prior level". Needs WRDS TRACE + FISD issuer link (in hand), no new spend; ~1 day of work. Ceiling = card 1's.

## Dropped (one line each)
- XIV/SVXY Feb-2018: payoff is a leveraged VIX path, not a fixed contract value; single episode; vol-ETP rebalancing family already REJECTED (region_ledger_2026-10-06.md:34), SVXY-in-contango dead (NEXT.md:1411).
- Aug-2015 / May-2010 open and flash prints: trades busted under clearly-erroneous rules, minute-scale, ETF premium family excluded (BSPD/ETC).
- Mar-2020 muni/bond CEF and ETF discounts, BDC discounts to NAV: excluded (CEF discount variants, ETF premium/discount).
- Levered ETNs / ETN accelerations / 2020 oil ETNs: ceiling-kill <0.3pp (idea_scan_events #5).
- 2022 UK LDI: no US-listed instrument with a contractual anchor; the gilt move was in instruments the account cannot hold.
- Archegos blocks (VIAC/DISCA): no contractual anchor; "bounce" never closed.
- 2022 SPAC trust collapse: floor is trust yield only (idea_scan_events #7, Round 31 L16).
- 2023 regional-bank seconds as a standalone: failed names went to zero; survivors' bounce is the weaker repeat of card 1 (fwd60 +2..+11%).
- 2008 auction-rate/trust-preferred as a rule: ARS not exchange-listed; listed trust-preferreds are card 1's failure case (fwd60/120 -25..-46% from the 2008 triggers).
- Generic "buy when index/EW basket is down X%" with no anchor: PANIC-IDX, dead.

## Honest verdict
One credible but thin card: it is effectively a single-episode result (Mar-2020) with a positive 2011/2023 echo and a negative 2008. Ceiling +0.5 to +1.9pp/yr at $10k, well under the +8pp gate; payoff per event is large (25%+, $2.5k at $10k). Worth only as a zero-cost dormant forward monitor, not as a funded study.
Open question that decides it: whether an issuer-quality screen available in real time (TRACE senior-bond spread) separates the 2008 prefs from 2020's. Files: this file; panel `research/sim/winsig.py` (kind="pref"); quotes via `research/sim/auction_fetch._env` pattern.
