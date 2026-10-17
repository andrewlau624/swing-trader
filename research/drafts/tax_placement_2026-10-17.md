# Tax placement memo (2026-10-17) - lever 4, no backtest, no N

Verdict: the current placement is already close to right on tax; the only material gain (+1.4 to +2.5pp/yr after tax on combined money) is making the Roth actually run IBS, not moving legs between accounts. Moving high-turnover legs "to the Roth first" is already what happens: the Roth is full at every size, so there is no spare Roth room to move into.

## 1. After-tax %/yr on combined capital (model, assumptions below)
Sizes (taxable T / Roth R, $k): now 2.3/2.0 = 4.3; ~10k 3.0/7.0; ~25k 4.0/21.0 (Roth +$7.5k/yr, taxable compounds only).

| Placement | now | ~$10k | ~$25k |
|---|---|---|---|
| P0 today: taxable IBS .5 + night .65 (nx_s2); Roth night .5, IBS half in SGOV, + PREF-EX/ETDX | 11.7 | 11.7 | 10.4 |
| P1 Roth also runs IBS (full 1.0x book + stack); taxable as P0 | 13.1 | 13.8 | 13.0 |
| P2 as P1, taxable holds SPY/QQQ buy-and-hold (8% pre, ~10% tax drag) | 12.9 | 13.7 | 12.9 |
| P3 as P1, taxable only night 1.15x (IBS entirely to Roth) | 11.8 | 13.1 | 12.6 |
| **Gain P1 vs P0, pp/yr** | **+1.4** | **+2.1** | **+2.5** |

Per-account after-tax: taxable P0 7.5%/yr (11.5% pre x 0.65); Roth P0 16.5 / 13.5 / 11.0 (night 5 + SGOV 2 + stack 9.5 / 6.5 / 4.0); Roth P1 19.5 / 16.5 / 14.0.

## 2. Facts (file:line)
- Both accounts run the night leg: server fills (logs/daily-fills-{live,roth}.jsonl, read 2026-10-17): taxable night 95 buys / 69 sells, Roth 96 / 70; same names most days.
- IBS: taxable 9 round trips since 09-23 (XBI, XLE, SMH); Roth 1 (VDE on 10-01/02, not in `ibs_symbols`). Roth IBS is mostly suppressed: `wash_guard: roth_first` (config.yaml:170) and idle IBS half parked in SGOV (`ibs_cash_symbol`, config.yaml:100). Cause not verified from logs; could also be the cash-account GFV rule. Roth tbill fills 5 buys / 4 sells.
- Profile nx_s2 (night .65, cap .15, 1.15x gross) is taxable-only; "profiles never reach the Roth" (config.yaml:217-223).
- `roth_cash_ira: false` (config.yaml:103); Roth books GFV-safe IBS+night with no intraday (config.yaml:103-108). Noise leg is off (CLAUDE.md, 2026-10-11).
- `pref_ex_mode: "live"` (config.yaml:178), Roth only, CC form, idle settled cash, <= 50% of Roth equity, BIL/SGOV never sold. CEF-RV is Roth, OO form, still gated by CEF-RV-FWD (60 closed trades), not live.
- Repo numbers used: NX 3.9%/yr of book at w .5 on 2003-15 (CLAUDE.md "Study NX RESULT"), live book realistic 8-15%/yr pre-tax (research-priority gate), IBS cost-bound and weak 2003-15 (SHAR-IBS), ROTH-STACK +10.5 / +8.4 / +5.4 / +3.6pp at $1k/$3k/$10k/$25k of Roth equity, 3x cost leaves +1.6 / +0.9 at $3k / $10k. RESULTS.md:2759: tax at 35% makes after-tax ~0.66x pre-tax, matching the 0.65 used here.

## 3. Tax character and constraints (date-versioned, 2026-10)
| Item | Character | Taxable | Roth |
|---|---|---|---|
| IBS, night | short-term gains, ~daily/weekly turnover | 35%, losses deductible (wash-sale exposure, hence wash guard) | tax-free, losses worthless |
| PREF-EX / ETDX | dividends on preferreds/baby bonds: non-qualified or interest = ordinary | ~35% on the ~0.8 x dividend captured, kills the edge | tax-free; Roth-only by design |
| CEF-RV | gains ST (hold weeks) plus ordinary distributions | taxed heavily | Roth upgrade over beta |
| SGOV/BIL | ordinary (state-exempt) | 35% federal | tax-free |
| Buy-and-hold index | qualified dividends, deferred LTCG | ~10-15% effective | wasted shelter |
- Taxable: margin account >= $2,000 (intraday margin from 2026-07-13 per secondary sources), 1.15x overnight max in nx_s2, shorting possible (unused). Old PDT rule is gone (effective 2026-06-04); not applied.
- Roth: no shorting, no margin, settled cash only (T+1; GFV risk on back-to-back nights, which `roth_night_priority` and the PREF-EX reservation file manage), no loss deduction.
- Cannot move: the 1.15x night extra (needs margin) and any short-side idea (SSR-LIFT, BORROW) stay taxable; PREF-EX/ETDX/CEF-RV stay Roth.
- Roth capacity: cash Roth runs <= 1.0x of its own equity, so it can never absorb the taxable book. Roth night capacity peaks ~$250k (digest.py:52); PREF-EX plateaus at ~$5k of Roth in dollars (capacity binds, stack pp fall 9.5 -> 4.0). At $25k the Roth is 84% of money, so taxable placement barely moves the total.

## 4. Why the alternatives are not better
- Move all overnight to Roth, taxable holds the index (P2): ties P1 within 0.1pp because the book (~11% pre, 7.2% after tax) is close to index beta (8% pre, 7.2% after). It only wins if book alpha over beta is zero (unresolved, book_decomp: night alpha t 1.5), and loses the margin extra. No reason to switch.
- Taxable on night only (P3): worse than P1 by 1.0-1.3pp at $10k+ because taxable IBS earns 10%/unit pre-tax, still 6.5% after tax, above T-bills.
- Rank by after-tax return per Roth dollar: PREF-EX/ETDX (taxable value ~0) > CEF-RV > night > IBS > SGOV. Roth should fund in that order; today's SGOV in the Roth is the lowest-value use of shelter.

## 5. Unverified assumptions (all change the pp, not the ranking)
- Per-unit pre-tax: IBS 10%/yr and night 10%/yr per unit weight (5% each at w .5; NX conservative 7.8% per unit). At NX 3.9% the P1 gain shrinks to ~+1.0 / +1.5 / +1.8.
- 35% rate applies to all gains; real federal+state could be 24-32% (smaller gap), and the $3k loss-offset limit and wash sales are ignored (taxable P0 overstated if losers are not offset).
- Why Roth IBS is suppressed was inferred, not read from the executor; if it is GFV/wash-driven, P1 needs a rule change (user decision) and may not reach full IBS.
- Roth stack pp interpolated from ROTH-STACK points; assumes ~0bp cross cost (3x cost cuts $10k Roth stack to ~1pp, shrinking P1/P0 gap by little because stack is in both).
- Taxable growth only by compounding (no new deposits); Roth balance ($2k/$7k/$21k) is an assumed path. Cash yield on parked half and 1.15x financing cost ignored in taxable.
- Server fills are a 3-week window (since 2026-09-23/29), so "who trades what" is recent behaviour only.
