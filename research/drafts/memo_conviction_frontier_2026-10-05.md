# Memo — Conviction / high-capacity frontier (2026-10-05)

Scope: the user's directive to find a *small number of extremely high-conviction, highly liquid*
opportunities that can absorb $100k–$1M, possibly with modest leverage. Research only; no
deployment. This is a **survey/synthesis** of already-run studies plus the Oct-4/5 uncommitted work,
not a new judged hypothesis. Program N stays 821.

## Verdict

**No conviction leg found.** No candidate clears *clear mechanism + no hindsight + substantial
capacity + untouched OOS + realistic execution*. The one structural flow with a genuine
untouched-window pass (TME) is real, unlimited-capacity, but small (~+4.2%/yr on deployed) and
already a shadow. Every other high-capacity mechanism is either REJECTED, or DATA-LIMITED with no
free evidence, or per-holder-capped (cannot take $1M).

Important reframing: the live book is **already not capital-constrained until ~$1M**
(`memo_next_frontier_2026-10-04.md:3-6`, Study Y). The binding constraint is capital/deposits, not
capacity. So "find a leg that can take $1M" has an existing answer (the book + IBS on liquid ETFs);
what is missing is a *new* edge large enough to matter, and the map is picked over.

## Candidate table (only non-REJECTED, or high-capacity, candidates)

| Candidate | Mechanism (who is forced) | Trigger | Net EV/trade | Capacity $10k→$1M | Holding | Turnover | Scalability | OOS | Mechanism evidence | Leverage | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **TME** month-end Treasury duration extension | benchmark-tracking bond funds extend duration at the index reset | last 3 sessions of month, close(T-3)→close(T) | +32.3bp/mo net, t 2.76 | unlimited (TLT/IEF ~$1B/day) | 3 sessions | 12 rt/yr | High | **PASS** (untouched 2002-15, 13/14 yrs, duration-monotonic) | Strong | see below | **VALIDATED but small → not a new conviction leg** |
| TME-L leveraged sleeve | same, 2x/3x via TLT margin / TMF | month-end | L2 +58.1bp, L3 +100.5bp/window | unlimited | 3 sessions | 12 rt/yr | High | report-only | Strong | **No efficiency gain** (mean/downside L1 0.51 → L2 0.39; DD −7.9%→−16.8%/−22.5%) | FORWARD SHADOW |
| Non-SPY SPDR ETF premium/discount | AP creation/redemption only at NAV; stale matrix NAV in stress | discount ≤ threshold | unknown | JNK/EMB millions/day → ~$100k–$1M | ~5 days | event | Medium/High | untested | Weak (SPY version rejected: create +9bp t1.5, discount ~0) | n/a | **DATA-LIMITED ($0 SSGA navhist scrape)** |
| Cross-market / futures–cash basis | index arb must converge futures/cash | roll/expiry | unknown | **maximal (ES/NQ)** | intraday | high | High | untested | Weak prior (roll already arbitraged since 2021) | n/a | **UNTESTED (Databento ~$0.02/root-yr)** |
| Dividend-month premium (Hartzmark-Solomon) | income retail/funds pay up before ex-date | month start | est. +1.5–3%/yr | high (large caps) | ~1 month | 12/yr | Medium | untested | Medium | n/a | **UNTESTED, small** |
| Signed dealer gamma → underlying | short-gamma dealers must hedge with the move | daily GEX sign | free proxy **−1.09bp, t −0.13** on untouched 2016-20 | bottomless (SPY/ES) | last 30 min | daily | High | **FAIL** (free proxy) | Strong in theory | n/a | **DATA-LIMITED / proxy falsified** |
| Fallen angels | IG trackers/insurers must sell on downgrade | rating cut / index exit | unknown | bonds not retail-executable (1-2% markup) | 1-3 mo | event | Medium | untested | Strong | n/a | **DATA-LIMITED (no free PIT ratings)** |
| Borrow / HTB lending revenue | short sellers must pay fee / be recalled | fee spike / recall | unknown | = lent position | days | event | Low/Med | untested | Strong | n/a | **DATA-LIMITED (no free fee/recall history)** |
| CEF discount vs own history | forced/retail flows; Dec tax-loss selling | wide discount | ~2–5%/yr lit. | thin funds | weeks | 12/yr | Low | survivorship unresolved | Medium | n/a | **DATA-LIMITED** |
| Russell Dec-2026 recon | Russell trackers must trade adds/deletes at the close | rank day → effective | unknown | thin microcaps (tiny at $100k+) | days | 1/yr | Low | forward-only | Strong | n/a | REGISTERED forward shadow |

**Per-holder-capped (real but cannot take $1M):** split-off exchange offers (+$934/yr at $10k, ~0
above), odd-lot tenders (~$150–200/yr, manual Schwab election), reverse-split round-ups
(~$130/yr/account), thrift conversions (~$200–400/deal, manual), UMH DRIP hold-only.

**Clearly REJECTED (do not re-open):** index add/delete (in the gap), cash-tender/merger arb
(~0.4% gross, −20–42% failures), going-private cash-outs, Reg SHO threshold forced buy (long side
−959bp, short side unborrowable), FTD spikes, S&P/Russell historical, LETF flow, vol-target proxies,
OPEX/OI pinning, TAC auction concession, SPY create/redeem, futures roll, FND physical delivery,
RB6040 month-end, insider Form 4 (ID1/ID2/IN1/IN2), RGTI level bounce (N 820–821).

## Leverage answer (TME-L, report-only; `data/research/program/tme_l_hist_out.txt`)

The one validated high-capacity leg was already lever-modelled: L1 +35.9bp/window (maxDD −7.9%),
L2 TLT-margin +58.1bp (−16.8%), L3 TMF +100.5bp (−22.5%). L2 is 1.62x L1 (theory 2 less financing);
**mean/downside falls from 0.51 to 0.39**, so leverage scales dollars and risk roughly together and
does *not* materially improve capital efficiency. Ruin/liquidation risk is historically contained
(min maintenance headroom 22.5%; no window lost >15%; worst TMF overnight −5.64%): the risk is a
−16% to −22% drawdown, not ruin. Conclusion: modest leverage is *permissible* on TME but not
transformative; it does not create a conviction leg.

## Genuinely open, next-step candidates

1. **Non-SPY SPDR premium/discount reversion** — cheapest real test ($0 SSGA navhist + raw closes).
   Testable in one study; SPY analog rejected, so prior is low. If pursued, pre-register the trigger
   and judge on pre-2021 untouched SPDR NAV (stress regimes 2008/2020).
2. **Cross-market futures–cash basis** — maximum capacity, cheap paid data (Databento, key in .env).
   Roll pressure already arbitraged; the arb itself is untested but prior low.
3. Neither has a mechanism as clean as TME; neither promises >+8pp/yr at $10k.

## Next step if pursued

Only #1 or #2 is worth a pre-registered study. Do NOT force a result; do not lower the gate to
produce a "conviction leg". If the user wants capital deployed now, the honest lever remains
deposits + the existing book (already absorbs ~$1M at ~16%/yr per Study Y), not a new leg.

## Addendum (same day, after the objective changed to small-account efficiency)

The user reframed: capacity does not matter; find a leg where moderate leverage materially raises
$/yr at $3k-$25k. That re-opened the leverage question on the ONE validated short-hold edge, IBS.

Study CLE (`study_cle.md`, N 821 -> 822, `cle_out.txt`): Goal L charged retail margin (12.5%) on all
leverage; a 3x ETF instead finances at ~5.5% (embedded swap) and is **non-callable**. Result:

| exposure (partial 3x-ETF allocation, rest in T-bills) | 2016-20 CAGR | maxDD | 2021-26 maxDD | P(DD>50%) | edge vs 1x |
|---|---|---|---|---|---|
| 1x IBS (base) | 9.6% | -16% | -21% | 0% | — |
| **1.5x** | **16.1%** | **-22%** | **-25%** | **0%** | **+6.5pp** |
| 2x | 21.3% | -29% | -33% | 0.5% | +11.7pp |
| 2.5x | 26.5% | -36% | -41% | 3.2% | +16.9pp |
| 3x all-in | 31.6% | -42% | -49% | 9.0% | +22.0pp |

Verdict **PROMISING (1.5x), reject 2x+**: Sharpe is ~flat (this is leverage, not alpha), but the
financing route is a genuine small-account advantage (retail margin cannot compete), and 1.5x keeps
drawdown ~-22/-25% with no callability. Caveats: the base is an idealised 100%-deployed fractional
book (whole-share granularity at $2.3k is unmodelled and worse); 3x-ETF daily-reset and expense are
inside the actual LETF returns but the realised multiple (2.93x) may not persist; tax is simplified.

Bigger point: the current book gives IBS only 0.5 weight and pairs it with the fragile, unproven
night leg (Goal L B0 ~3.9%/6.1%). Running the validated IBS leg at full weight is worth more than
any leverage. Not deployed; this is research.

## Attack on CLE (`cle_attack.py`, `cle_attack_out.txt`) — 2026-10-05

Attacked before any deployment. Frozen trigger unchanged. Findings:

1. **Decompose 1x->1.5x:** pure exposure adds +4.6pp (OOS) / +6.3pp (IS); cheap financing
   (5.5%) costs only 0.4-0.6pp (retail 12.5% would cost ~2.8-3pp). The gain is exposure; the
   LETF-specific advantage is the *financing*, not alpha. Sharpe ~flat.
2. **LETF vs synthetic daily-reset 3x:** actual 3x ETFs underperform the ideal path by
   **-7.6bp/trade (t -2.54)**, negative in 9/10 years (~-2.8%/yr on a 1.5x blend): fee +
   tracking + the intraday/overnight split. Decay is second-order for 1-session holds.
3. **Whole-share at real sizes:** $1k/$3k/$10k/$25k CAGR base 7.5/8.2/8.3/8.3%, "1.5x"
   12.9/12.8/12.7/12.6%, "2x" 17.3/17.6/16.7/16.9%. Realised effective exposure is only
   **1.33x ($1k) to 1.49x ($25k)** — ~30% of names have no 3x fund and whole-share rounds down.
   "1.5x" is really ~1.35-1.5x. maxDD: 1.5x -27/-28%, 2x -35/-36%.
4. **Robustness:** 1.5x full +16.6% pre-tax, but ex-best-5 +11.8%, ex-best-10 **+8.4%** —
   outlier-sensitive; 4 of 11 years negative (2017 -6.1, 2018 -0.3, 2022 -4.1, 2024 -13.6).
5. **Allocation vs leverage:** current book 5.4% -> 100% IBS 1x 10.4% (**+5.0pp, allocation**) ->
   1.5x 14.3% (**+3.9pp more, leverage**). Allocation is the bigger single move.
6. **Tails (1.5x):** bootstrap 3yr P(DD>25%) **32%**, P(DD>33%) **11%**, P(DD>50%) 0.2%;
   max recovery 70 sessions; worst rolling 5d -16%, 20d -19.5%; 2022 maxDD -27.9%.
7. **Structural threshold?** No. 1.5x maxDD -27.9% **breaches a 25% DD budget**; only **1.25x
   (-23.5%)** fits. The leverage cap is the risk constraint, not a fitted optimum.
8. **$/yr per $1,000 after tax:** 1x $71-95; 1.5x $104-137; 2x $135-177; 3x $190-247;
   SPY $107-115. So 2x IBS ~= 1.5x SPY dollars at similar DD; 1x is below SPY.

**Verdict: PROMISING as a FRAMEWORK, not a conviction strategy.** The valuable, surviving
idea is "cash-purchased leveraged instruments are cheaper and non-callable vs retail margin";
the leverage that fits a 25% DD budget is **1.25x**, and the single largest gain is allocation
to the validated IBS leg. Not deployed.

## TME-L2 (`tme_leverage.py`, `tme_leverage_out.txt`) — 2026-10-05

Applied the same capital-efficiency framework to the second validated edge (TME month-end Treasury
duration extension; frozen signal). After tax, whole-share 2009-2026:

| arm | CAGR | maxDD | $/yr per $1k |
|---|---|---|---|
| TLT 1x | 4.3% | -5.9% | $43 |
| UBT 2x | 4.0% | -17% | $40 (dominated; 15bp/side cost) |
| 0.5 TLT + 0.5 TMF (~2x) | 6.9% | -14.2% | $69 |
| TMF 3x | 9.5% | -21.9% | $95 |

ETF drag TMF-3xTLT -9.2bp/window (~-1.1%/yr). Risk-budget cap (TME-only): 2.5x at 25% DD, 3.0x at
33%. **PROMISING as a stacking overlay, not a standalone leg:** TMF 3x earns $95/k at ~-22% DD vs
IBS 1.25x $105/k at the same DD, and TME uses capital only ~14% of sessions so it ADDS on
month-end-idle cash. Right answer = more IBS allocation + modest TME (TMF or 0.5/0.5 blend), not a
single leveraged trade. Caveat: 2009-2026 flatters 3x Treasuries (bond bull); window tail bounded
(-8.7% worst) but forward rate-shock risk is not bounded by this sample.

## Edge #3 search (2026-10-05)

Frontier filtered to mechanisms with a NAMED forced counterparty and a different risk source from
IBS/TME. Top untested: (1) CEF discount vs own history (constrained arbitrage; needs daily-NAV
build), (2) dividend-month premium (clientele, not forced; testable free), (3) CEF year-end
tax-loss -> January.

Tested #3 decisively (`cef_taxloss.py`, N 823->824): **REJECTED.** 142 CEFs, distribution-adjusted
total returns 2016-26; bottom-YTD quintile shows NO December underperformance (+0.27% vs universe,
t 0.63) and NO January reversion (+0.01%); Jan Q1-Q5 -0.93%; the raw January rebound is market beta
(2018/2022 down-year recovery). No forced-flow signature.

Remaining open: the CEF discount-vs-own-history complex (the one sizable untested area; blocked on
daily NAV) and the dividend-month premium (free but non-forced). No new edge validated.

## CEF NAV data-value assessment (2026-10-05) — DO NOT BUILD

Checked: CEFConnect `/api/v3/pricinghistory/{T}/All` is live and returns weekly NAV + price +
discount to 1996-10 for LIVE funds (free, unofficial). N-PORT (SEC, monthly, 2019+) needs
`SEC_USER_AGENT`, absent from `.env` -> 403. On-disk: 142 CEF price series 2016-26 (distribution-
adjusted `all/` + raw), median ADV $2.0M (111 funds >= $1M, 27 >= $5M). No NAV on disk.

5-condition data-buy rule: (1) mechanism structurally compelling? partial (constrained arbitrage,
but well-known). (2) free evidence doesn't weaken it? no — free weekly NAV exists and the price-
based tax-loss version already failed. (3) falsifiable? yes. (4) payoff > existing edges? **no**
(literature 2-5%/yr vs IBS 8-13%). (5) cheaper dataset answers it? **no — CEFConnect weekly is $0**.
Two conditions fail (4,5) -> **do not build/acquire the CEF NAV panel.** A full delisted-complete
daily NAV build is not justified; even the "$0" weekly test is below the payoff bar. Recorded dead.

Open frontier (higher level): options-induced underlying flow (strike-level signed gamma) is the one
untested mechanism with a named forced counterparty (dealers must hedge) + high capacity; its only
real source is historical OPRA (Databento, key in .env, cheap targeted pulls), and the free GEX proxy
already failed, so prior is low. Borrow/recall and PIT ratings remain data-blocked.

## FCC commodity curve carry (fcc.py, N 824->825) — REJECTED; frontier reset ends here

Ran the frozen FCC experiment. Data bug fixed first (Databento single-digit-year symbol collisions split into
contract instances). Result: physical (CL/NG) OOS L/S +87.7bp/period but equity destroyed (cum -120%); CL -86.6bp
vs NG +344bp => kill #2 (one commodity); RY quintiles non-monotonic; NG OOS is a 2021-22 gas-crisis outlier; ES/NQ
~0. REJECTED. **Conclusion: NO SUFFICIENTLY PROMISING NEW FRONTIER FOUND.** The research question moves from "find
another alpha" to "maximize profit and capital efficiency from IBS + TME without unacceptable drawdown."
