# Study J2 (jump hunt idea R2-5): officer/director buy after a 30% fall — DEAD (judge half)

Session llm-trader-51, 2026-10-02, `prompt_jump_hunt.md`. Pre-registered in `round1_prose.md` (Amendment — Jump hunt,
Study J2; program N 761 -> 762). k = 2.

**Rule:** Form 4 open-market purchase by an officer/director (>= $1k; first per stock in 30 days) filed while the stock
is >= 30% below its close 60 sessions earlier. Buy the next open; +20% limit within 5 sessions else the 5th close
(`tp20`, hold 5). Builder `research/sim/jump_insider.py r2_5`.

| window | line (as printed) | verdict |
|---|---|---|
| select 2016-23 | `tp205 n 2379 (297/yr) jump 15.1% vs base 5.8% (x2.6) mean net +0.5% ex-top3 +0.5% median +0.3% vs stock's usual +1.2% hit 51% worst -74% best +38% P(mean<=0) 0.02` | jump MEETS (also RIDE hold20 +3.5%, hold60 +8.7%) |
| judge 2024-01..2025-06 | `tp205 n 378 (189/yr) jump 9.5% vs base 7.2% (x1.3) mean net +0.5% ex-top3 +0.3% median -0.2% vs stock's usual +1.4% hit 49% worst -38% best +20% P(mean<=0) 0.18` | **JUMP VERDICT: DEAD** |
| confirm | not run | — |

**Why it died:** PRICE PROXY + REGIME. A select-only control stated before the judge (same stocks, >= 30% falls with no
insider buy) did as well (tp205 +0.93%, hold20 +4.8%): the insider added nothing over the fall itself, and the fall's
bounce is a market-bottom effect (2020). In 2024-25 the jump lift fell to x1.3 and the mean's P to 0.18.

**Do not redo:** insider-buy-after-a-fall at other drawdowns, holds or exits; "buy small caps down 30% in 60 days" is
the price-first rebound this reduces to (banned as-is for RIDE; the night leg already owns the 1-day loser bounce).
