# Study AL — the idle Roth: what the limited-margin delay costs, and the best cash-IRA book (Round 17)

> **Correction (Study AQ, Round 17c):** the IBS-only recommendation below used the repo's `tier_hi`
> (15-50bp round trip), which is 5-10x the measured night cost, not the brief's "measured x2"
> (~5bp). At the brief's stress the cash-IRA book **IBS .5 + night .5** earns 19.0%/yr (22.0% at
> 2.5bp), t 3.06, and is the recommendation; IBS-only is the fallback if live costs exceed ~6bp.
> See `study_aq_night_cost.md`. The rest of this file stands as the tier_hi stress case.

`research/drafts/round1_prose.md` Round 17, Study AL (pre-registered before any number).
Code: `research/sim/roth_cash.py` (`PYTHONPATH=. .venv/bin/python -m research.sim.roth_cash`).
Output: `data/research/program/roth_cash_out.txt`. N = 642 -> 648 (6 variants).

## The question

The Roth has never traded: `executor.py:165` returns before any phase unless `.env` has
`ROTH_LIMITED_MARGIN=yes`. Two things: (a) what does waiting cost per month at $1-3k + $7.5k/yr,
and (b) is there a book that needs no limited margin, so the Roth can start now?

## The cash-IRA book (mechanism, checked before running)

A plain cash IRA cannot borrow, short, or use unsettled proceeds for a same-day round trip.
- IBS leg: buy open d+1 (settles d+2), sell open d+2 = the funding sale's T+1 settlement date -> safe.
- Night leg: buy close d (settles d+1), sell open d+1 = the settlement date -> safe.
- The **3x-ETF intraday leg** (buy ~10:01, sell ~15:57, funded by the morning's unsettled sale) is the
  **only** leg that needs limited margin. So the cash-IRA book is IBS + night, no intraday leg.

## Results (fixed capital, whole shares + $150 probe; 2021-23 / 2024-26 / full CAGR/Sharpe/maxDD)

| variant | 3bp full | tier_hi 21-23 | tier_hi 24-26 | tier_hi full | maxDD |
|---|---|---|---|---|---|
| M3 limited margin (live reference) | 45.3/2.25 | 28.1/1.80 | 34.9/1.61 | **31.3/1.67** | −12 |
| M2L limited margin | 45.7/2.40 | 33.1/2.14 | 33.4/1.64 | 33.2/1.84 | −12 |
| AL1 cash IBS .5 + night .5 | 21.4/1.54 | 3.4/0.35 | 12.1/0.86 | **7.5/0.62** | −14 |
| AL3 cash **IBS only 1.0** | 18.4/1.25 | 14.1/1.00 | 22.1/1.45 | **17.9/1.22** | −16 |
| AL4 cash night only 1.0 | 23.7/1.07 | −6.9 | +0.4 | **−3.4** | −35 |
| BIL (idle) | 3.2/12.1 | 2.1 | 4.4 | 3.2 | 0 |
| SPY | 15.3/0.94 | 10.6 | 20.5 | 15.3 | −24 |

IBS-only at lower weight (tier_hi): w 0.5 -> 6.9% (−12% DD), w 0.75 -> 11.1% (−14%), w 1.0 -> 17.9% (−16%).

**The night leg is the drag.** At stressed costs the night leg alone (AL4) is negative (−3.4%/yr),
so AL1 (IBS .5 + night .5) earns only 7.5%. Study T/30/39's restatement already showed the night
leg is thin at tier_hi; in a cash IRA there is no intraday leg to carry it. The IBS leg is nearly
cost-insensitive (1bp fixed): it earns 17.9% at tier_hi and 18.4% at 3bp.

Verdict table (tier_hi, vs BIL, 2021-26): AL3 t **+2.41**, placebo 99.3%, P(DD50) 0%, maxDD −16
(vs M3 −12); AL1 t +1.00, placebo 82.7% (fails). AL2 strict (0.25/0.25) 2.4%/yr, AL5 alternating
1.2%/yr — both dead.

**Verdict: AL3 (IBS-only, cash IRA) is the one that clears the bar** — both halves up at the
stressed cost, NW t 2.41, placebo 99.3%, P(DD>50%) 0%. It misses the generic "max DD not worse by
>2pp" clause vs M3 (−16 vs −12), because it is a different, intraday-less book; at w 0.5-0.75 the
DD is −12 to −14% at 6.9-11.1%. **SHADOW** (a live switch, default off, with the kill rule).

## A. Cost of the delay (tier_hi, $start + $7,500/yr = $625 every 21 sessions, tax-free)

| start | book | full CAGR | end $ | $/mo vs BIL | $/mo vs M3 |
|---|---|---|---|---|---|
| $1,000 | M3 limited margin | 31.9% | 107,952 | +889 | 0 |
| $1,000 | AL3 IBS only 1.0 | 15.2% | 71,768 | +352 | −537 |
| $1,000 | AL1 IBS+night | 5.3% | 54,222 | +91 | −797 |
| $1,000 | BIL | 3.2% | 48,057 | 0 | −889 |
| $3,000 | M3 limited margin | 32.5% | 118,584 | +1,011 | 0 |
| $3,000 | AL3 IBS only 1.0 | 17.9% | 84,378 | +504 | −508 |
| $3,000 | BIL | 3.2% | 50,446 | 0 | −1,011 |

- Waiting for limited margin costs **~$890-1,010/month** in forgone book profit (vs idle), on the
  growing balance. The cash-IRA IBS-only book recovers **~$350-500/month of that now**; the rest
  (~$500/mo) is what the intraday leg and the full overnight book are worth.
- Over the first 6 months at $3k the cash-IRA book is roughly flat vs BIL (tiny balance, weak 1H21);
  by 12 months it is ahead. The dollars are dominated by the **$7,500/yr deposits at this size**,
  not by the edge — which is exactly why starting now matters: the deposits compound in the book.
- The delay is **not about alpha on $2k; it is about turning the next few years of $7.5k/yr
  deposits loose.**

## What to do

1. **Spec a `cash_ira` Roth mode: IBS-only** (no night leg, no intraday leg), weight sized to the
   DD budget (0.75 = 11.1%/yr, −14%; 1.0 = 17.9%/yr, −16%). Whole shares; the $150 probe is inert
   for IBS (budget ~$383 at $2.3k/BIL-parked, see Study AO). Needs a kill rule and tests.
2. **Do not wait for limited margin to start the Roth.** When approval arrives, add the intraday leg
   and the night leg back (M3) — but note the night leg is negative at stressed costs, so even then
   IBS + intraday may beat IBS + night + intraday.
3. The cash-IRA IBS-only book still needs the cross-account wash guard (`roth_first`, add. 31/39 G4s)
   if the taxable book trades the same ETFs.

## What failed plainly

- IBS + night without the intraday leg (AL1): 7.5%/yr at tier_hi, fails the t/placebo bar — the
  night leg's stressed cost kills it.
- The strict-settlement and alternating-session books (AL2/AL5): 2.4% / 1.2%.
- Night-only (AL4): −3.4%/yr at tier_hi.
