# Branch R: how much can the US PREF-EX/ETDX sleeve hold at Schwab? (2026-10-18)

Execution-economics estimate on touched data (official crosses 2021-26). NOT a new edge test; no program N; nothing deployed, no orders.
Code: `research/sim/branch_r_probe/{taq_pull,taq_open,cross_stats,sleeve}.py`; outputs `cross_stats_out.txt`, `sleeve_out.txt`;
data `data/research/branch_r/`. Sleeve engine reused unchanged: `etdx_exec.rows` + `pref_exec.account` (equal split across a night's events,
cap = p x ex-ante auction $, whole shares, Roth, no leverage), PREF+ETDX, 7,264 events, 2021-01..2026-10, gross $/yr, fixed account.

## Verdict
- Capacity, not edge, is the binding constraint (net edge ~28bp/event at 10bp RT, t 14; median closing cross is only $6.7k, so 5% = ~$340 = ~14 shares).
- The 5% cap is conservative if impact is mild, and about right if it is severe. TAQ cannot tell which (see "What TAQ can and cannot say").
- Best participation: **~10% at $10k, ~20% at $25k** under the central and stress models. Past that the curve is flat or falls.

| Roth form, gross $/yr (5bp/side flat kept on top of impact) | 5% (today) | best p | note |
|---|---|---|---|
| CC (MOC in + MOC out, Schwab-safe) $10k | $676 (S1) / $574 (D) | 10-20%: $943 (S1) / $789 (D) | +15-40% |
| CC $25k | $762 / $623 | 20%: $1,794 (S1) / $1,528 (D) | ~2.4x |
| CO (MOC in, pre-open market sell out) $10k | $977 / $944 | 10%: $1,220 (S1) / $1,262 (D) | +30% |
| CO $25k | $1,265 / $1,221 | 20%: $1,958 (S1) / $2,580 (D) | +55-110% |

Reference with the same machinery and today's flat 10bp RT, no impact (`etdx_exec_out.txt`): CO $1,107 ($10k) / $1,442 ($25k); CC $737 / $844.
The brief's $789 / $919 is the older PREF-only figure. Severe case (S2: imbalance = 1/4 of the cross, price walks to the half spread): $10k CC
peaks at ~$490 at 5-10% and CO collapses beyond 10% (negative at 20%): there the 5% rule is already the optimum and nothing is gained.
Without the 5bp/side cushion the central models give $10k CC ~$1.7k at 10% (C) and CO ~$2.2k; treat those as upper bounds.

## Measurement (WRDS TAQ, `taqmsec.ctm_* / nbbom_*`)
- Symbol convention (verified): preferreds root=issuer, suffix=`PR`+series (`BAC.PRO` -> BAC/PRO); baby bonds/ETDs of >=5 letters root=ticker[:-1],
  suffix=last letter (TANNZ -> TANN/Z), <=4 letters root=ticker, NULL suffix. Closing cross = trade with `tr_scond` containing `6`
  (size x price reproduces the Alpaca `close_usd`; print equals `events.pc` to 0.00bp). Opening cross = `tr_scond` Q (also O).
- Sample: 988 E-1 crosses on 158 random ex-nights (2021-01..2025-11), 964 matching E opens. TAQ has no NYSE/Nasdaq imbalance feed, so
  imbalance is not observed.
- Closing cross: median $6.7k (p25 $2.8k, p75 $17k), 300 shares, 1.1% of that day's dollar volume. 15:59:50 NBBO half-spread median 18bp (mean 27),
  top of book ~1 lot. **The print is inside the 15:59:50 NBBO 80% of the time, mean +2.8bp / median +4bp from mid** (in half-spread units +0.12); at/above the ask 34%,
  at/below the bid 23%. Buying at the cross therefore beats lifting the ask by ~25bp on average, vs the 15:50 mid it is +3.3bp.
- Dispersion of the print around the pre-close mid is mostly quote noise: |dev| 17bp even in the smallest-cross quartile, 30bp in the largest
  (cross >= ~10% of the day's volume, mostly month-end/index days, signed dev -2.5..-3.9bp there, i.e. sell-heavy, no buy premium).
  OLS |dev| = 15.9 + 32.6 x sqrt(cross/day $vol), corr +0.23. Imbalance-linked excess is ~13bp at a 10% volume share.
- Opening cross: median $15k, post-open (09:30:30) half-spread median 60bp; print vs post-open mid |dev| median 32bp (0.67 half-spreads), signed +0.14 half-spread.
  Wide/stale quotes make this noisier than the close; the open leg is the more fragile one.

## Impact models used (per leg, bp, p = share of that leg's cross)
- C: sqrt-law on day volume, b=32.6 from the regression: ~0.3bp at 20%, ~0.8bp at 50% (our order adds p x 1% of day volume).
- D: PREF-PART's registered 0.8 x sqrt(100p): 1.8bp at 5%, 3.6bp at 20%.
- S1 (stress): excess dispersion 13.3bp scaled by p/cross, open leg x3.3 (spread ratio), capped at the half-spread.
- S2 (severe): as S1 with imbalance = 1/4 of the cross.

## What TAQ can and cannot say
- It identifies the *level* of the cross print vs the book and its natural dispersion; it cannot identify directional impact of an
  added buy MOC, because the sign and size of natural imbalance are unobserved. The models bracket that; the truth between S1 and S2 is unknown.
- The first-order risk is not smooth impact but an unfilled-opposite-side cliff when our order exceeds the net sell imbalance of a thin cross.
  The 100-300 share crosses (median 300 shares) make this a real risk above ~20%.
- Selection: sample is 14% of events (random ex-nights); month-end index days inflate the big-cross quartile.
- Execution realism: Schwab has no MOO (CO needs the pre-open market-sell route tested on JRI: 0.0bp on 1 share, uninformative for size).
- Touched data; the live 30-trip PREF-EX record (orders from 2026-10-21) is the real judge of cost at 5%.

## Recommendation for the pilot (user decision)
Do not raise above 5% on model evidence alone. After the 30-trip record at 5% confirms ~0bp cost, step to 10% and compare
fill-vs-official-print per trip; a rise to 20% is only justified at >= ~$20k and only if 10% showed no cost. Log cross size and our share per trip so g can be identified.
