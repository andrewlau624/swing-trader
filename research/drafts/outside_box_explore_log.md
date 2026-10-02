# Round 30 exploration log (SELECT data only; does not count toward N, counts toward honesty)

Every look taken before the pre-registration. All panel data were cut at 2023-12-31 when loaded
(`outside_box.SEL_END`); night picks are 2021-23. Outputs: `data/research/program/outside_box_explore_out.txt`,
`outside_box_explore2_out.txt`. Script: `research/sim/outside_box.py explore | explore2`.

| # | look | what it showed (select data) | decision |
|---|---|---|---|
| L1 | #5 night picks by 20d $/trade tercile (within-night demeaned auction return) | 2021-22 lo +11 / mid +2 / hi −11bp; 2023 lo +20 / mid −28 / hi +13 | — |
| L2 | #5 same, today's $/trade | 2021-22 +14 / +9 / −19; 2023 +42 / −42 / +12 | — |
| L3 | #5 $/trade vs price; shares/trade terciles; price terciles as control | $/trade is a price proxy (Spearman +0.83); shares/trade not monotone (2023 lo +19 / mid −74 / hi +53); price alone gives the same lo > hi | **dead**: price tilt is already dead (add. 23) |
| L4 | #10 night picks by listing exchange | Nasdaq +5.6 / NYSE −11.2bp (2021-22) flips to Nasdaq −17.3 / NYSE +49.6 (2023) | **dead** (flips) |
| L5 | #7 picks within IPO+173..190 days | 23 picks, −122bp within-night (the wrong sign; supply-driven drops continued) | **dead** (sign and n) |
| L6 | #4 crashed names (≤ −15% on ≥ 3x $vol, ADV ≥ $5M), excess vs SPY around the first session ≥ day 31 | day 0 −19.5bp (n 1,585), Oct-Dec events −47bp; no positive bump anywhere in −6..+3 | **dead** (no rebuy pressure visible; sign wrong) |
| L7 | #6 raw close crossing below $5 (after 20 sessions ≥ $5), night-pool names | overnight +6.7bp, 1d −52, 5d −109, 10d −167bp vs SPY; placebo $4 −31 (5d), $7 +2 | **dead for us**: the forced selling is real but it *continues*; the long side loses and sub-$5 shorts are hard to borrow |
| L8 | #6 crossing above $5 | 5d −108, 10d −258bp: no institutional buying bump | dead |
| L9 | #1-3 twins, all pairs (both classes either way; clones; LETF vs L×anchor), z of the close residual | class z ≤ −2 next close rel +21bp; clone +5.5; LETF +15; per-pair: the gross is in the thinnest pairs (MOG, HVT, KELY, BH, CRD: +150..+260bp) = stale prints | thin pairs are print artifacts |
| L10 | #1-3 liquid only (both legs 20d ADV ≥ $10M), vs each pair's own baseline | class z ≤ −2: overnight +2.2, next close +6.8bp (t 5.9, every year +); clone: +5.4 / +5.6 (t 13.8); **LETF: overnight +12.4, next close +11.7 (t 10.1), every year +8.7..+15.7**; z ≤ −3 LETF +16.5 overnight | LETF survives the liquidity filter; class/clone below a 5bp round trip |
| L11 | #9 SIC peers of a ≤ −15% crash, themselves down 3-8% | next overnight −7.9bp vs non-peers −2.8 (2020-22); 2023 +1.6 vs +3.0 | **dead** (contagion carries information; peers bounce *less*) |
| L12 | #14 IEF/TLT vs BIL around 308 note/bond auctions 2016-23 | IEF days +1..+3 +2.7bp/day (t 2.0), pre-auction −1.1; TLT +3.7 (t 1.25) | **dead at the bar**: ~38 switches/yr × 5bp round trip ≈ the gross; published (Lou-Yan-Zhang) |
| L13 | LETF twins with the residual measured **before** the cross (SIP minute bars at 15:45 / 15:50 / 15:55 / 15:59), bought in the cross, sold at the next open | z ≤ −2: cross → open vs pair baseline **−0.0 / −0.1 / −0.0 / +0.1bp** (t −0.4..+0.6); z ≤ −3 −0.3..−0.4bp (t −1.9..−0.5); the pre-cross gap closes *in* the cross (+21-23bp decision → cross) | **dead**: L10 was lookahead (the dislocation is made by the cross itself) |
| L14 | L13's 15:45 events on Alpaca official crosses | prints cover 100%; raw long −3.7bp on crosses vs +3.5 on the panel; vs baseline −1.1 (z ≤ −2) / −2.0bp (z ≤ −3) | confirms L13 |
| L15 | Implementable version: limit-on-close buy at 10/20/30/50bp below the 15:50 fair value (prev close × (1 + L × underlying move to 15:50)), sold at the next open | fills 42-15%; vs L × underlying only **+0.8..+1.5bp**; 76-84% of fills come from the underlying's own last-10-minute drop; raw-vs-pair flips by year (2020 +93..+131, 2022 −25..−32); the LETF's *own* cross gap (not observable live) is +13..+17bp rel, t ≈ 0 | **dead**: the LOC fill selects late market selloffs (leveraged beta; IBS/"LETF-flow last half hour" territory, add. 34) |

**Lookahead caught before registration (L10 → L13):** the twin z used the official close of both legs, which is not
known when a closing-auction order must be entered. Re-measured before the cross, the effect is zero.

**Converge: nothing survived exploration.** No study is pre-registered; program N stays 752; 2024-26 was never read
for any Round 30 idea (no judge-half minute bars or auction prints were fetched).

## Round 31 looks (EDGAR unblocked; select data only)

| # | look | what it showed | decision |
|---|---|---|---|
| L16 | #13 SPAC trust: does the book have money idle long enough? (V7/Roth sim, $10k) | overnight use 36% on average, but only **7.9%** of equity is idle for a whole 20-session window; the panel lacks the liquidated 2021-22 SPACs (survivorship) | **closed without a test**: +1-2pp of yield on ~8% of equity ≈ +0.1%/yr |
| L17 | #44 / #8 / #45 flags on 2021-23 night picks (EDGAR cache, acceptance time <= 15:40 ET on d): NT 10-K/Q in 60d, EFFECT in 7d, Form 144 in 7d | NT +41 / −71bp (flips); 144 −19 (n 5) / +18; **EFFECT +32 (median +50) / +236bp (median +118), n 53 / 14** | NT, 144 dead |
| L18 | EFFECT robustness | ex-top-3 +17.7bp, **ex-top-5 −0.0bp**; 60% positive; offering-overlap picks −28 vs pure EFFECT +99 | **not registered**: outlier-driven like DS5 |
| L19 | DS14 insider buys (officer/director P >= $10k, SEC Form 345 sets): night tilt 30/90d; 1/5/20-day drift from the next open | tilt 30d +11 / +18 (medians −1 / −28); 90d +17 / +2; 20-day excess ≈ 0 except 2020 (+596bp; 2021 −58, 2023 −59) | tilt and 20-day drift dead |
| L20 | same events, next session open -> close | **+20.2bp (median +4.1), every year + (2020 +49, 2021 +25, 2022 +26, 2023 +5), t 3.4**; ADV $1-20M +27.6 (median +10.9, t 2.6); ADV >= $20M +15.8 (t 2.2) | **registered as Study ID** (adjusted-price filter in this look; the registration uses raw prices) |
