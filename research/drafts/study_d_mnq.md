# Draft addendum — Study D: MNQ/micro-futures as the second bot (2026-09-29)

    PYTHONPATH=. .venv/bin/python -m research.sim.mnq_swap
    output: data/research/program/mnq_swap_out.txt

## Pre-registration
research/drafts/round1_prose.md, "Amendment - Study D" (stamped `Tue Sep 29 02:04:34 PDT 2026`,
before any number below was computed). The add. 25 PROXY stands (QQQ minute bars in place of
NQ; MNQ = $2 x NQ ~ 82 x QQQ; the Globex session, roll and basis are NOT modelled). The
raw-price book (load_sim(raw_price=True), corr 0.7) supplies the rest of the legs exactly
against the last rounds' baselines (47.2/2.06 at 3bp; 29.4/1.41 at tier_hi, reproduced). The
1256 tax model: ST 35% on the non-1256 net, LT 20%, so the 1256 blended = 0.6*0.20 + 0.4*0.35
= 0.26; the ETF legs keep T3's wash-sale model; MNQ is not a security (no wash-sale issue).

## The size gate (the machine, at TODAY's MNQ notional $60,794; 7% margin $4,256)

| E0 | forced 1-contract leverage (MNQ notional / E0) | fits the 2x Reg-T / no-margin-call bound? |
|---|---|---|
| $3k | 20.3x | no |
| $7.8k (Roth) | 7.8x | no |
| $15k | 4.05x | no |
| **$30k** | **2.03x** | at the bound: exercises the "about $30k per contract" rule (add. 25) |
| $50k | 1.22x | 1 contract = 3.3x the leg's 0.375x vol target (still an over-suspension) |
| $100k | 0.61x | 1 contract ≈ 1.6x the leg's vol target |
| ~$160k | ~0.38x | the 1 contract matches the leg's vol target (0.375x equity per the 0.5 share cap 0.75) |

## Results (the noise leg swapped QQQ -> MNQ; the book's after-tax 5y Monte-Carlo, 21-day blocks, $3k+$1k/21-sessions scaled; the costs per row on the row's own notional)

Costs at the TODAY's notional: MNQ 0.247bp/side (tier) / 0.411bp (tier_hi) vs the ETF leg's
1bp/2bp; per-side historical rows use their own px (the same live rule, so the GROSS is the
same; the delta is all costs and tax).

| book/cost | 2021-23 / 2024-26 / 2016-20 (the increment's Sharpe) | NW t (2021-26) | at $3k waivers | at $50k |
|---|---|---|---|---|
| D2 MNQ swap, 3bp night | +0.1 / +0.2pp | +3.57 | med $138.6k -> $140.2k (+$1.6k) | $2,309.6k -> $2,335.8k (+$26.2k) |
| D2, tier | same | +3.57 | $117.1k -> $118.3k | $1,950.3k -> $1,971.3k (+$21k) |
| D2, tier_hi | -0.7 / -0.1pp (t -15.5) | negative tier | - | - |
| D3 Kelly 0.03 | the same sign, ~flat vs D2 | +2.20 | med $138.6k -> $140.3k | $2,309.6k -> $2,336.7k (+$27.1k) |
| tax-rate sensitivity (the swap's 5y median delta, tier) | ST 25%/LT 15% (blended 0.19): +$16.2k at $50k, +$32.5k at $100k | — | — | — |

(after-tax MC P(DD>30% / 50%): all rows 0.3-2.8% / 0.0% at the FRACTIONAL model; the
whole-contract machine's forced leverage is the risk item at the small sizes.)

## Verdict: the MNQ swap is a candidate ABOVE ~$160k of taxable equity and OUT below ~$50k

- The gross-carry (a) passes: the MNQ leg's gross is not worse than QQQ's at every cost model
  (2021-23 9.84 vs 10.09, 2024-26 4.92 vs 4.44, the 16-20 proxy row 5.03 vs 7.35 — the proxy loses
  the Globex session, which is the part where the futures edge is qualitatively different).
- The after-tax edge (b): +0.9-1.1pp/yr at the FRACTIONAL model at $50k/$100k — driven by the
  60/40 blended rate (26% vs 35%) worth ~+7-9% of the leg's net gains a year, plus ~0.5bp/side
  cheaper execution; the swap's cost delta at the OWNER size is fully explained by these.
- The size gate (d) fails at every size below $50k the add. 25 rule names (the forced
  1-contract leverage 2.03x at $30k, 20.3x at $3k): the account's drawdown-bounded intraday
  book cannot hold a whole-contract margin tree at these equity levels (the vol-target
  0.375x-vs-forced 1.22x/2.03x mis-sizing alone).
- The Kelly no-v2 (D3) rows add nothing beyond the add. 40's own shadow verdict.

So: the "second bot" on micros is a **tax-structure upgrade** (35% -> 26% blended on the
intraday leg + a quarter of the per-side at the current notional) whose size gate is ~$160k
of taxable equity (or ~$85k if the SMH half is retired and the noise leg gets the full
0.75x budget). Below that it is over-sizing — the contract's notional pegs the book higher
than its own drawdown bound, and the Monte-Carlo P(DD) model's own machinery (the account_mc
lev1 rows) refuses it.

Do NOT redo:
| idea | verdict | why |
|---|---|---|
| MNQ (micro futures) as the day book's second rail at $3k-$30k tax and margin | **dead at these sizes** | the forced 1-contract leverage 2.03x-20.3x vs the leg's 0.375x vol target; the 60/40 tax saving (+~1pp/yr) only pays at ~$160k+ (add. 25's $30k/contract rule matches it) |
| The same swap in the Roth | **n/a** | a limited-margin IRA cannot run futures/shorts |

Variants: 4 (D1-D4). No adoption at the user's sizes.
