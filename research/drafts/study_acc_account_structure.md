# Study ACC — account structure for the IBS edge at small size: Roth-first + non-callable 3x-ETF (N 833 -> 834)

Status: run, one look. Pre-registered `round1_prose.md` "Amendment — Study ACC" before any
account-structure return was read. Runner `research/sim/account_struct.py`; out
`data/research/program/account_struct_out.txt`. Research only — NO DEPLOYMENT, NO LIVE SIZING,
NO MARGIN CHANGES. The leg is the LIVE IBS rule only (`book.ibs_days`), 3bp/side; night and
noise legs OFF (not OOS-validated).

## Question
With the OOS-validated IBS leg taken as given, what account structure maximizes after-tax %/yr and
$/yr at $2.3k / $10k / $25k — (a) asset location (IBS in Roth vs taxable), (b) Roth-first
contribution sequencing (+$7.5k/yr), (c) non-callable leverage via a partial 3x-ETF allocation vs
taxable margin — subject to a 25% maxDD budget and no liquidation? Windows: judge 2016-20, stress
ex-2020 (2017-19) and the 2022 bear, plus in-sample 2021-26. An arm passes only if its strategy
maxDD stays within −25% and it never liquidates in **every** window.

## Method (frozen)
- **Leg**: top-3 of the 18 EQ18 ETFs by 12-1 momentum (monthly), IBS(close d)<0.2, buy open(d+1),
  exit open(d+2); 3bp/side. Returns from the shipped simulator, whole shares.
- **Leverage**: partial 3x-ETF — f = min(L/3,1) of capital in the *actual* 3x proxy of each pick
  (UPRO, TQQQ, TNA, UDOW, SOXL, TECL, FAS, LABU, MIDU, EDC; no-proxy names express 1x), rest in
  T-bills; **non-callable** — vs a callable Reg-T margin twin (12.5%/yr on the debit, $2,000
  floor). L in {1, 1.25, 1.5, 2}.
- **Accounts**: taxable (30% on each year's net gain, loss carried forward, year-end) vs Roth
  (tax-free, cash IRA — no borrowing). **Contributions**: $7.5k/yr ($625/21 sessions) into the Roth.
- **Metrics**: money-weighted IRR, time-weighted %, $/yr edge (final − cumulative contributions),
  account maxDD (deposit path) and **strategy maxDD** (constant-capital time-weighted path),
  realized exposure (notional/equity), liquidation count.

## Judge 2016-20, deposited (IRR %/yr | $/yr | strategy maxDD | realized exposure)

| structure | $2.3k | $10k | $25k |
|---|---|---|---|
| A all-taxable base 1x | 12.9 \| +3,077 \| −15.8 \| 1.00 | 11.4 \| +3,770 | 10.1 \| +5,107 |
| B all-taxable letf 1.25x | 17.0 \| +4,270 \| −17.1 \| 1.22 | 15.3 \| +5,348 | 13.6 \| +7,289 |
| C all-Roth base 1x | 17.6 \| +4,476 \| −15.8 \| 1.00 | 15.6 \| +5,481 | 13.8 \| +7,427 |
| D all-Roth letf 1.25x | 23.2 \| +6,292 \| −17.1 \| 1.21 | 20.8 \| +7,900 | 18.4 \| +10,685 |
| **E all-Roth letf 1.50x** | **27.5 \| +7,875 \| −20.8 \| 1.47** | **24.4 \| +9,756 \| −21.1** | **21.8 \| +13,393 \| −21.3** |
| F all-Roth letf 2.00x | 36.0 \| +11,455 \| **−27.9** | 32.0 \| +14,288 \| **−27.2** | 28.5 \| +19,540 |
| G seq(initial all-taxable) letf 1.25x | 23.0 \| +6,242 \| −15.0 | 19.5 \| +7,275 | 16.5 \| +9,302 |
| H seq(initial all-taxable) letf 1.50x | 27.2 \| +7,788 \| −18.5 | 23.0 \| +9,011 | 19.3 \| +11,388 |
| J all-taxable margin 1.25x | 15.5 \| +3,822 \| −20.4 \| 1.25 | 13.6 \| +4,654 | 12.0 \| +6,268 |
| K all-taxable margin 1.50x | 18.0 \| +4,598 \| −24.8 \| 1.49 | 15.8 \| +5,575 | 13.9 \| +7,480 |

E ends $77,874 / $94,820 / $127,695 from $2.3k / $10k / $25k plus $36,875 of contributions.

## Drawdown gate — worst strategy maxDD across ALL four windows (reject if < −25%)

| structure | $2.3k | $10k | $25k | realized x | verdict |
|---|---|---|---|---|---|
| A/C base 1x | −18.6 | −18.6 | −18.7 | 1.00 | PASS |
| B/D 1.25x letf | −19.9 | −20.0 | −20.0 | 1.22 | PASS |
| **E 1.50x letf** | **−24.1** | **−24.1** | **−24.2** | **1.47** | **PASS (narrow)** |
| F 2.00x letf | −31.9 | −32.0 | −32.0 | 1.97 | REJECT |
| H seq 1.50x letf | −23.9 | −24.0 | −24.1 | 1.43 | PASS |
| J margin 1.25x | −23.5 | −23.5 | −23.5 | 1.25 | PASS (marginal) |
| K margin 1.50x | −28.1 | −28.2 | −28.2 | 1.50 | REJECT |

The 2022 bear alone, strategy maxDD (deposited): base 1x −18.5%; partial-3x 1.25x −9.5%, 1.5x
−11.8%, 2.0x −15.4%; **margin 1.25x −23.1%, margin 1.5x −27.8% (reject)**. A synthetic
fully-invested 1.5x of the base sleeve (financed, i.e. the margin shape) is −29.0% in 2022 — the
partial-3x arm is genuinely shallower because the unallocated half of the capital sits in T-bills
and cannot be lost, and the 3x leg is not borrowed against.

Ex-2020 (2017-19), same structures: all-Roth 1x IRR 5.1 / 4.0 / 3.2%; 1.25x 7.9 / 6.6 / 5.9%;
1.5x 8.8 / 7.4 / 6.9%, maxDD −14 to −21%. Per-year TW, all-Roth: base 1x 2017 −3.1 / 2018 +1.7 /
2019 +8.1 / 2020 +52.9 / 2021 +24.2 / 2022 −1.0 / 2023 +15.4 / 2024 −5.2 / 2025 +17.6 / 2026 +66.9;
1.5x +2.3 / +8.2 / +10.0 / +87.0 / +34.4 / +1.8 / +19.0 / −14.8 / +11.5 / +155.5.

## Readings
1. **Winner: E — all-Roth (or Roth-first), partial 3x-ETF allocation 1.5x.** Best IRR in every
   window at every size, realized exposure 1.47x, worst strategy maxDD −24.1% (2021-26) — inside
   the budget in all four windows, zero liquidation. 2.0x (F, −32%) is rejected on the judge window
   alone. **The 1.5x pass is narrow (−24.1% vs a −25% cap); with the CLE-attack whole-share path
   showing −27.7% for the same definition, 1.25x is the prudent deployment cap.**
2. **Non-callable partial-3x dominates margin at equal nominal L, on both return and risk.** At
   1.25x taxable: 17.0% / −17.1% (letf) vs 15.5% / −20.4% (margin); margin 1.5x is rejected
   (−28%) while partial-3x 1.5x passes. The edge is mechanical: the T-bill half cannot be called
   and pays no borrow, whereas margin risks the whole debit. The advantage is largest exactly in
   the 2022 bear (−11.8% vs −27.8%).
3. **Asset location (a): IBS belongs in the Roth.** Tax-free vs taxable at 1x = **+4.7 / +4.2 /
   +3.7 pp** at $2.3k / $10k / $25k (C vs A). IBS is high-turnover short-term, so the Roth is the
   right sleeve; only capital that cannot fit keeps running taxable.
4. **Sequencing (b): every $7.5k/yr to the Roth.** Roth-first with the starting capital stuck in
   taxable (H) is within 0.3–2.5 pp of the all-Roth bound (E) — the realistic answer, since
   starting capital cannot be moved into a Roth retroactively.
5. **(c) The deposits, not the alpha, carry the dollars.** $36,875 of forced Roth contributions
   over the window dominates the small-account outcome; the structure (Roth + leverage +
   contributions) is the lever at $2–25k, not a new signal. The high IRRs are money-weighted and
   flattered by deposits arriving into the 2019–20 run-up — ex-2020 the same arms are 5–9%.

## Verdict: PROMISING (structure only; no deployment)
The structure that maximizes after-tax %/yr and $/yr within the 25% budget and no liquidation:
- **Roth-first**: contribute the full $7.5k/yr to the Roth up front; run the IBS leg *inside* the
  Roth. Existing taxable capital runs the same leg (Roth-first wash guard) until sheltered; never
  margin.
- **Non-callable leverage**: hold each IBS pick via its 3x proxy at **1.25x** for a robust cap
  (IRR 23.2 / 20.8 / 18.4%; worst DD −20.0%) or **1.5x** as the judged-window max (27.5 / 24.4 /
  21.8%; worst DD −24.1%, narrow). Never margin at 1.5x (rejected), never above 1.5x.

No live 3x-ETF IBS mode exists; it would be a new switch needing its own registry entry, shadow
period and kill rule.

## What failed plainly
- **Margin 1.5x: REJECTED** (−28.1% worst, and −27.8% in the 2022 bear). Margin 1.25x passes only
  marginally (−23.5%) and for far less return than the same-risk partial-3x.
- **2.0x+ leverage: REJECTED** (−32%).
- **Taxable-only: −3.7 to −4.7 pp/yr** vs Roth at the same leverage.
- **Synthetic/full 1.5x leverage** (the margin shape) is −27 to −29% DD — the reason the
  non-callable partial allocation, not "more leverage", is the finding.

## Decision (user, 2026-10-05) — accepted, structure only
Accepted as **PROMISING, structure only, no deployment**; **do not ship a live 3x-ETF IBS mode.**
- (a) Move the IBS leg into the Roth and (b) sequence all $7.5k/yr Roth-first — **manual account
  actions, not bot changes**.
- (c) Non-callable partial-3x is the right leverage form, but **cap at 1.25x** (1.5x is a narrow
  in-sample pass: worst-window DD −24.1% vs the −25% cap, and CLE-attack's whole-share path is
  −27.7%). Never margin (1.5x rejected), never above 1.25x.
- Carry the caveat: the judge-window dollars are the **$36,875 of forced Roth contributions plus a
  2020-vol regime** — ex-2020 the arms are 5–9%/yr. This is a **structure/deposit result, not new
  alpha**; do not re-open it as a signal search.
