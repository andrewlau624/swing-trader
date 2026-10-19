# Branch C: buying forced sellers near the bottom (2026-10-18)
Study CRASH-C (N 1026; pre-reg `research/drafts/round1_prose.md` "Study CRASH-C", runner `research/sim/crash_c.py`, out `data/research/program/crash_c_out.txt`). One run.

## Verdict
CEF discount blowout (question 1): the registered gate PASSES 2 of 3 episodes (2008-09, 2020), FAILS 2022. Read it as WEAK-PASS / forward-shadow candidate, not a
validated crash harvester: live-fund survivorship, 3 effective episodes, and the pattern is stated for $2-25k Roth-eligible long-only. No orders, no deployment.
Question 2 ($25-par IG < $18) was not re-run: INCOME-SHOCK (N 1021) already killed it (2008-07 screened -13% at +120d). Question 3 answered from existing outputs: no new N.

## Rule (frozen before reading outcomes)
- Trigger: SPY <= -20% from 252d high AND EW-median CEF discount >= 3.0 pts below its own 52w median; 52-week lockout.
- Select: bottom decile of (fund discount - own 52w median) at trigger; 3 tranches (trigger, +4w, +8w); exit when discount returns to the pre-trigger median, else 260d.
- Cost 1.0% round trip base, 2.0% at 2x. Primary excess = fund price TR minus the EW NAV TR of the same name-category (all panel funds), SPY and EW-universe as beta comparators.

## Results (selected decile, net of 1x / 2x cost)
| episode | n | price TR | own NAV TR | wedge | excess vs cat NAV net1x/net2x | median | ex-top5 | SPY same window | gate |
|---|---|---|---|---|---|---|---|---|---|
| 2008-09-26 | 23 | +18.1% | -8.0% | +26.0 | +17.3 / +16.3 | +13.1 | +9.8 | -0.5% | PASS |
| 2020-03-13 | 30 | +28.8% | +16.8% | +12.0 | +14.0 / +13.0 | +12.7 | +8.7 | +31.2% | PASS |
| 2022-06-17 | 32 | +2.6% | +1.4% | +1.3 | -0.6 / -1.6 | +1.4 | -1.4 | +4.4% | FAIL |
| 2001-09-21 (extra) | 12 | +5.4% | +1.5% | +3.9 | +3.5 / +2.5 | +3.9 | +1.6 | -0.8% | FAIL |
| 2002-12-20 (extra) | 12 | +11.2% | +11.1% | +0.1 | +6.0 / +5.0 | +5.4 | +3.2 | +11.9% | FAIL |
Lines: `crash_c_out.txt` per-episode blocks. Mean hold 145-195 days (2008 145d, 2020 188d, 2022 195d). The 2022 episode (a -23% SPY, 2.5% discount blowout, no solvency or
redemption panic) is the control: no forced-seller footprint, no edge. So the edge appears only where the blowout is a panic (2008-09, 2020), consistent with the mechanism.

## What the numbers say
- The profit is wedge compression, not beta: in 2008 the funds' own NAV fell 8% while price TR rose 18%; SPY was flat over the window. In 2020 the NAV rose 17% (beta
  rebound) and the wedge added +12pp; price TR (+28.8%) is almost the whole SPY move (+31%), so raw return there is mostly beta and only the wedge/excess is claimed.
- Timing is not a bottom call: 2008 tranche at the trigger (9/26) lost money (price TR -3.2%, NAV -28.7%) and the +8w tranche earned +39.9%. The staged entry is what makes the 2008
  excess positive in every tranche (+14.7/+13.3/+26.9 gross); the trigger fires roughly 2-6 weeks before the bottom.
- Levered proxy (muni/taxable_fi/pref_conv by name) is similar (+19.3% 2008 with only n=6, ex-top5 -1.4; +19.0% 2020, n=7): the deepest blowout is not specific to levered funds.
- Cost is irrelevant (1pp vs 10-18pp effect); capacity is not the issue at $2-25k (CEFs trade $0.5-20M/day).

## Why this is not yet a PASS (unverified / failure modes)
1. Survivorship (material): the panel is 355 funds alive in 2026. Non-panel CEFs (delisted/merged/not covered) earned 15.6% vs 27.9% in the 2020 window (-12pp) and
   +2.6pp more in 2008-09. The decisive 2020 excess (+14%) would shrink toward ~0-5% if dead funds are included at the same blowout rank; 2008 does not show the same gap.
   Dead-fund NAV does not exist, so history cannot settle it (same wall as CEF-SURV99).
2. Effective n: 3 crashes; two pass, one control fails; extra 2001/2002 fires are both positive but below the +10% gate. A gate of "2 of 3" with n=3 is weak.
3. The trigger is not a bottom signal: a >=30% drawdown that continues after the fire is the 2008-type path; staged entries survived here but 2000-02 and 2008 type slow bears
   leave tranches deep underwater for months (2008 tranche 0 NAV -28.7%). Max adverse excursion per fund is not computed.
4. Same-category comparator uses name regex on panel funds; the gate's excess is partly category-NAV dispersion (not a clean same-fund hedge). The own-NAV wedge row is the cleaner view.
5. Roth: long-only, no margin: executable. Schwab liquidity in the first panic weeks (wide spreads when discounts blow out) is not modelled beyond 50bp/side.

## Question 3: is the existing book a crash harvester? (existing outputs, no new run)
- SHAR-CRASH (`research/sim/shar_crash_out.txt`): 0.5 IBS + 0.5 night daily-bar replay, gross: 2000-02 +278% (maxDD -24.1%), 2008-09 +51% (maxDD -9.9%), 2011 +17%. The night
  leg earned the bulk (2000-02 +1287%, 2008-09 +60.6%) but that panel is daily-close optimistic (~1.7x per NX).
- NX (`data/research/program/nx_out.txt:10,27-28`): night leg 2008-09 +4.99bp/night vs 2010-15 +3.81bp at tier; 2008 +1.37bp, 2009 +8.63bp; at 2x tier_hi 2008-09 is -5.32bp (cost-bound).
  Exact 15:40 replay 2020 +76bp (part 3 ledger) vs ~0 outside 2019-20: the night leg is vol-proportional, not crash-proof.
- IBS leg: pre-2016 is weak and cost-bound (SHAR-IBS +5bp net, t 1.0); no crash premium shown beyond beta.
- PREF-EX: no crash data (Sharadar pref panel thin pre-2014); its edge is a calendar mechanism, not a crash one.
- Conclusion: the book earns more in high-vol (2009, 2020) but not by an amount that supports a crash-triggered size-up (NX size-ups are already a separate user decision and 2x tier_hi is negative).

## Next (only if the user wants)
Forward shadow, log-only, no orders: a weekly check of the trigger (SPY dd, EW discount widening) plus the decile list from the CEFConnect panel (`make cef-rv-panel` from the Mac;
CEFConnect blocks the server). Must be registered in `swingtrader/daily/testing.py` REGISTRY if built. Dead-fund NAV (CRSP MF has no CEFs; WRDS check) is the survivorship test.

## EXTENSION: Great-Crash scale (CRSP via WRDS; N 1027; `research/sim/crash_c_great.py`, out `data/research/program/crash_c_great_out.txt`)
Question: in a 1929-scale crash, does early bottom-buying ruin the account? YES. Rules frozen first (round1_prose.md "CRASH-C extension"). Long-only, cash 0%, 0.25%/tranche.
Account = fraction of starting cash; window = peak to peak+6y. Worst dd is peak-to-trough of the account after the first purchase.
| window (index maxDD) | R1 staged 1/3 at -30/-50/-70 | R2 all-in at -30% | R3 trend-confirmed (>=40% DD, then >210d SMA; exit 5% below SMA) | R4 hold from peak |
|---|---|---|---|---|
| 1929-32 (-84.0%) | dd -65.2%, final +12.8%, BE 1,086 sess | dd -80.2%, final -25.5%, NEVER BE | dd -36.8%, final +83.2%, BE 901 | dd -84.0%, final -52.3% |
| 1937-38 (-50.8%) | -22.8%, +34.1%, 148 | -30.9%, +27.5%, 217 | -34.7%, +24.5%, 1,291 | -50.8%, -12.9% |
| 1973-74 (-48.1%) | -8.6%, +18.5%, 164 | -25.8%, +55.4%, 164 | -14.3%, +51.0%, 4 | -48.1%, +8.7% |
| 2000-02 (-49.4%) | -14.2%, +13.9%, 614 | -38.4%, +41.7%, 614 | -8.6%, +67.3%, 20 | -49.4%, -1.3% |
| 2007-09 (-55.5%) | -18.4%, +76.7%, 129 | -35.0%, +76.5%, 212 | -18.8%, +73.2%, 33 | -55.5%, +20.8% |
Dollars, 1929-32 (final value): $2.3k -> R1 2,595 / R2 1,714 / R3 4,214 / R4 1,097; $10k -> 11,283 / 7,453 / 18,322 / 4,771; $25k -> 28,208 / 18,632 / 45,805 / 11,927.
Other windows $10k: R1 11.3-17.7k, R2 12.7-17.7k, R3 12.5-17.3k (all in the output file at $2.3k/$10k/$25k).
Findings: (1) All-in at -30% (the Nov-1929 buyer) loses 75% at the low and is still down at year 6. (2) Staging -30/-50/-70 cuts worst dd to -65% and breaks even in about 4 years
but is a long, painful hold; it is 1/3 cash at the -30 tranche so deployment is small early. (3) Trend-confirmed survives every window with the smallest drawdowns outside 1937-38.
Warnings: R3's 1929 gain relies on a 4-week stop-out after buying the 1930 false bottom (lost -21%) then re-entering Aug 1932; the stop is the active ingredient, a rule with no stop
would have been ruined by the April 1930 rally (user's point). R3 in 1937-38 took 1,291 sessions to break even (whipsaw). It gives up the first 30-40% of any rebound (e.g. 2009 entry after +).
(4) R5 cheapest decile (price/52w-high, month-end after -30%): 1929 -0.5%, dd -80.8% (no protection); 1937 +60%, 1973 +207%, 2000 +49% (EW all stocks +110%), 2007 +228% vs index +98%.
It beats the index in 1937, 1973, 2007 only; a valuation tilt, not a drawdown shield. Survivorship: CRSP includes delistings (msedelist), so no panel survivorship here.
Caveats: index-level, not tradable ETF (1929 no ETFs; SPY-like proxy VTI/SPY from 1993 only; the pre-1993 series is a vwretd index), no margin, Roth friendly long-only, cost 0.25% only, 5 windows = 5 events, one of which (1929) defines the answer.
