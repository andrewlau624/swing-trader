# Branch G: cumulative preferred dividend SUSPENSIONS (G1) and ARREARS catch-ups (G2), 2026-10-17

Verdict: **zero surviving cards.** G2 is a real, repeatable ex-date effect but ~1 issuer-event/yr with thin auctions: ceiling ~0.5-2pp at $10k.
G1 is a credit lottery (median negative, multi-year lock). Repo grep (arrears|suspension|cumulative) found nothing prior in NEXT/MISTAKES/drafts
beyond PREF-EX/ETDX/FXD/HYC (round1_prose.md ~4725-4960); the PREF-EX filter (y 0.2-4% per payment) EXCLUDES catch-ups, so this is untested ground, not a duplicate.
All numbers below are DESCRIPTIVE and TOUCHED (Sharadar 1998-2026, no untouched window consumed). Scanner: `research/sim/pref_arrears_scan.py`
(+ scratch in /tmp/x). Universe: Sharadar SEP "Domestic/ADR/Canadian Preferred Stock" + SFP ETD / CEF Preferred; raw `closeunadj`, raw open = open*closeunadj/close.

## Evidence (task 1-2)
Catch-up = dividend >= 3x median of the prior 4 payments, y = div/raw prior close in 5-60%, price $3-80: 38 series-events. After removing 2006-09 structured-trust
artifacts (Sharadar books an annual $2.00 as one payment on 2007-03-27; CORTS/SATURNS 2009/2013 rows) the genuine arrears payments are ~9 issuer-events, 2014-2026,
each cluster covering 1-7 series: Old Second OSBCP 2014-07-01; Chesapeake CHKLQ 2017-01; Gastar GST-PA 2018-04-19; TPG/MITT PA,PB 2020-11-27; Hersha HT-PC/D/E 2021-03-18;
Ashford AHT-PD/F/G/H/I 2021-11-30; PG&E PCG-PA..PH 2022-04-28 (y 21-23%); NGL NGL-PB/PC 2024-02/04 (two tranches); CareCloud CCLDO 2026-05-15 (y 8%).
Per year: 2014 1, 2017 1, 2018 1, 2020 1, 2021 2, 2022 1, 2024 1, 2026 1. Mean ~0.4 issuer-events/yr (~1/yr since 2020, COVID-suspension cohort).
Suspensions (regular payer, gap >= 2.2x median interval and >= 150d, 2005+): ~163 gaps / ~110 issuers in Sharadar, but many are data holes (e.g. PSA 2019 gap) or
non-cumulative bank paper (Hovnanian HOVNP 2007->2021, DB/HSBC contingent capital) that pays NO catch-up.

EDGAR 8-K verification (efts full-text, UA per brief), 5 of ~10 cases opened:
- Ashford 8-K 2021-11-19: board declared cash dividends on Series D/F/G/H/I **Cumulative** Preferred "reflecting accrued and unpaid dividends" for six quarters (6/2020-9/2021). Announcement Fri 11-19, ex 11-30 (Sharadar).
- Gastar 8-K 2018-04-09: "special cash dividend ... to pay in full all accumulated and unpaid cash dividends" on Series A and B (suspended earlier on oil-price decline). Announced 04-09, ex 04-19.
- Sotherly 8-K 2023-01-24: reinstates quarterly Series B/C/D (cumulative) dividends, declared at regular $0.50; arrears NOT in the ex-date payment (Sharadar shows ordinary amounts), so no catch-up event. Counter-example: reinstatement without catch-up is common.
- Old Second 8-K 2014-05-20 (Q1 deck): pro-forma "payment of ... unpaid dividends on Series B Preferred" funded by the April 2014 common offering; 25,669 shares repurchased at 94.75% with unpaid dividends waived.
- Hersha 8-K 2021-03-01: Series C/D/E "Cumulative Redeemable"; payment text not reached in the 300-char window.
Not opened/unverified: MITT, NGL (hit was an indenture exhibit), PG&E (full-text returned nothing; PG&E prefs are listed as cumulative in the 10-Q index but the arrears wording was not read), CareCloud.
Treat PG&E/NGL/MITT as Sharadar-only.

## Descriptive results (task 3)
G2 ex-date (T-1 raw close -> T raw open + dividend), genuine arrears events, series-level:
- drop/dividend median ~0.66 (IQR ~0.5-0.8; two NGL rows ~0 where the dividend was a second tranche), vs ~0.8 on regular PREF-EX nights. Under-adjustment scales with the payment.
- CO return per event mean ~+4.2% (series, n=38 raw rows; issuer-event mean ~+4.8%, all 9 issuer-events positive, range +1.9% to +8.4%; PG&E +4.5..+13.9%, Gastar +4.7%, AHT +0.6..+5.7%).
- **Announcement -> ex is flat; the whole effect is the ex-night.** Ashford: ann-day change -0.4..+0.6%, ann -> ex-1 close -1.2..+0.6%; Gastar ann-day +4.9% (arrears announcement priced then), ann -> ex-1 -0.4%. Price runs to par + accrued BEFORE the announcement (AHT already $26.5-27.7 vs $25 par pre-announcement; MITT $17 -> $22 in the month before ex). Nothing to buy at announcement.
G1 suspensions (t0 = first missed ex-date, P = price 10 days later, outcome = price at resumption or at data end, one row per issuer-event, hindsight list built from my gap + stopped-payer scans, so it over-samples cases that left a trace):
- Among suspensions whose price had fallen >30% within 10d of the first missed date (n=29, 28 issuers; 16 in 2020-22 COVID cluster): resumed 9; **median return P(t0+10d) -> resolution -13%, hit 41%, mean +45% carried by <=6 outliers (+120..+390%)**; resumed-cohort mean +105%, unresolved/ended -> bankrupt/delisted/still-suspended mean +18%, median negative. >50% drop (n=20): median -25%, hit 35%.
- Failures: ALIN -80%, OTRK -92%, FRC -90%, FATPQ -95%, Presidio, WPG, PREIT, QVC, CBL (CBL prefs $0.6 at end). Time to resolution 0.5-14 yr (median ~1.5; Hovnanian 14.3, Wheeler 5.9, NGL 3.1). 2026 live cases: AHT again suspended 2025-12 (prefs ~$4 vs $25), SQFTP, WHLRP.
- Selection note: this cohort is defined partly by hindsight (issuer still exists / trace in data), so true failure rate is higher than shown, not lower.

## Candidate cards
### G2 catch-up ex-night: CEILING-KILL as a standalone, keep only as a log-only extension of PREF-EX
- Mechanism: arrears paid as one cash dividend; marginal holder is retail/income (taxable ordinary income, no Roth), thin dealer inventory; ex-night drop ~0.66 x payment so a 10-40% payment leaves several percent. Named counterparty: sellers who view the lump as a return of principal/taxable; dividend capturer = Roth.
- Resolves at the ex open; invalidated if drop/div -> 1.0 (the PREF-EX effect decaying; FXD showed this in funds <10bp since 2020) or if price is clean (not cum-arrears) before ex.
- Frequency: ~0.4/yr issuer-events (2014-26), ~1/yr since 2020, 1-7 series each; payoff ~+4-5% per event (descriptive, touched); downside: one-night hold, ex-date risk is a price-gap vs the cum price (worst row ~ -4.9% on a mispriced trust), capital lock 1 night (2 with MOO miss).
- Capacity: pre-ex volume is tiny: AHT series 2.4-6k shares (~$65-160k/day), PG&E PE $0.5k/day median, MITT ~$120-220k/day, NGL-PB $2.3M/day, CareCloud $150k/day. At 5% of auction $ (PREF-EX rule) ~ $250-800 per series; a 5-series cluster ~ $2.5k; NGL up to ~$5k.
- Ceiling = events/yr x edge x deployable x 50% capture: $2.3k: 1 x 4.5% x $0.8k x 0.5 = $18/yr (0.8pp); $10k: 1 x 4.5% x $2.5k x 0.5 = ~$56/yr (**0.6pp**); $25k: 1 x 4.5% x $4k x 0.5 = $90/yr (0.4pp). Even at 100% capital and full capture: 1 x 4.5% = 4.5pp, still < +8pp gate. Fails the gate by 10x+.
- Data path: in hand (Sharadar actions, flag mult >= 3). The universe overlaps `etd_symbols.txt`; PREF-EX shadow `pref_ex_shadow.py` already logs ex-nights but filters y 0.2-4%, so catch-ups are excluded. Zero-cost option: relax the y cap to 30% for events with div >= 3x trailing and log them. Registry-entry rule applies if built (not done here; no live code touched).
- Pre-registrable spec (if the user wants it logged): G2-FWD. Event = pref/ETD/CEF-pref with ex-dividend >= 3x median of last 4 payments, y 4-30%, raw price $10-60, $vol(20d median) >= $50k, EDGAR 8-K text containing "accrued and unpaid|accumulated and unpaid|arrears". Trade (log only): T-1 closing cross -> T opening cross. Gate: n >= 8 issuer-events, median net (10bp RT) > +100bp, 7/8 positive. Window: forward from 2026-10 only; at ~1/yr this needs ~8 years: **unpowerable**, so the log is only informative as a PREF-EX sub-slice, not as a test. All 2014-26 history above is touched. Untouched pre-2014 window is too thin (3 genuine events 2005-13: trust artifacts only).

### G1 suspension/dump long: KILL before test (mechanism-reliability and lock)
- Premise (income funds/yield buyers dump at suspension; cumulative paper of survivors trades below par + arrears; resolution = resumption) is partly true: survivors AHT/HT/NGL/MITT/GST returned +60% to +235% from t0+10d to resumption. But the entry is indistinguishable ex ante from failures (ALIN/OTRK/FRC/QVC -80..-95%); median -13..-25%, hit 35-41%, mean carried by outliers (fails the "median not mean" rule); lock median ~1.5y, up to 14y (Hovnanian, tied to a non-cumulative case); concentrated in one 2020 regime. Cumulative status is also not sufficient: Sotherly reinstated with no catch-up in the ex-payment. An edge requires issuer credit selection (no systematic counterparty rule), i.e. the "single-name lottery" shape the repo has repeatedly killed.
- Ceiling: 5-10 liquid-enough suspensions/yr x median negative = no positive expected honest-capture ceiling. Capital lock multi-year violates the user's lock ruling in spirit (tender capital lock ruling 2026-10-17).
- Only salvageable thought: a **screen to avoid** PREF-EX/ETDX positions in issuers with a missed dividend (AHT, SQFTP, etc.), already implied by PREF-EX needing a regular dividend. No work needed.

## Dropped
- Announcement -> ex window long: flat (Ashford -1.2..+0.6%, Gastar -0.4%); priced before announcement.
- Non-cumulative reinstatements (Hovnanian, DB/HSBC CoCo, Flagstar): no catch-up by contract.
- Sotherly-style reinstatement (cumulative, no lump at ex): no event.
- Structured-trust (CORTS/SATURNS/PPLUS) "catch-ups": Sharadar annual-vs-quarterly booking artifacts, not arrears.
- Bank TARP-style deferrals (Old Second): one-off, paid via a capital raise and partly waived at 94.75%.
- Capital-lock/forced-sale variants of G1 (buy at suspension, hold to resolution): median negative, lock-years.
