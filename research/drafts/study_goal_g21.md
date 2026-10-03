# Goal G21 (T5): everything we have, in one number, after tax, at today's balances (report, no N)

Goal hunt, session llm-trader-ec, ideas G21 + G22 + G28 (`goal_ideas.md`). This combines verdicts that already exist and
adds no new edge; every input is cited. Accounts today: taxable ~$2.3k, Roth ~$8.5k (combined ~$10.8k), +$1-2k/month
taxable, +$7.5k/yr Roth.

## The parts (judge half 2024-26 unless stated; after tax)
| part | where | status | combined pp/yr over SPY at ~$10.8k |
|---|---|---|---|
| A. Index-beat stack: taxable SPY 1.0x + legs on margin; Roth 1/3 UPRO + 2/3 book (`study_ib_found_stack.md`) | both | FOUND (index-beat bar 3), shadow `stack_shadow.py` | **+6.6pp** (2021-23 +5.3) at edge-halves; break-even at 25% of the backtested edge |
| B1. Reverse-split round-ups, 1 share per account (`study_round32_events.md`, G1) | both | live (ROUNDUP_AUTO); **Schwab rounding unverified** | $370/account/yr: taxable $370 x 0.65 + Roth $370 = $610 -> **+5.6pp** |
| B2 + odd-lot tenders, placed in the **Roth** (G22) | Roth | live alerts, manual | 99 parent shares fit in the Roth's ~$8.5k for most parents: ~$811 (B2 at the $10k size) + ~$175 (tenders), untaxed -> **+9.1pp** |
| G2 / `id3_big` overlay on the taxable SPY core (G2 study) | taxable | NEAR, forward gates (60 trades) | +11pp on the taxable $2.3k -> **+2.3pp combined** if it passes |

**Sum at today's balances:** A + B1 + B2/tenders = **~+21pp/yr over SPY after tax** (2024-26), or ~+23pp if G2 passes forward.
Holdout 2016-20 for the contract parts: B1 ~+0.5pp (round-ups were rare before 2022), B2 +17pp (9 deals), tenders as above.
A's 2016-20 isn't in the index-beat study; its 2020 alone was +51% vs SPY +13% in taxable.

**Why B2 goes in the Roth (G22):** the 99-share cap counts across accounts, so the account is a free choice. The Roth has
the cash (~$8.5k vs $2.3k), keeps 100% of a short-term gain, and the Roth book only loses ~8-10 sessions of its cash a year
(~1.4 deals x ~8 days; at the book's ~+15%/yr that is ~0.5% of the Roth, ~$40), against ~$280-400/yr of tax saved and 4x
the shares. **G28 (margin on B2 in taxable) is dominated** by this and is dropped.

## Lottery test (judge half)
Without the 5 best contract events (CMI and LEN split-offs + the 3 best round-ups), B2 contributes ~0. The remainder (B1
~$600 + tenders ~$175 + A) is still ~+7pp (contract) + 6.6pp (A) = **~+13pp**. Passes.

## As the balances grow (contract dollars are capped per holder; A scales)
| combined | A | contracts (~$1,600/yr after tax) | G2 if it passes (taxable share) | total |
|---|---|---|---|---|
| ~$10.8k (today) | +6.6 | +14.8 | +2.3 | **~+21 to +23pp** |
| $25k | +6.6 | +6.4 | +3-4 | ~+13 to +17pp |
| $50k | +6.6 | +3.2 | +4-5 | ~+10 to +15pp |
| $100k (capacity line) | ~+6 (night leg caps ~$250k, Study V) | +1.6 | +5 | ~+8 to +13pp |

## Verdict: a conditional FOUND-level combination, not FOUND yet
The combination clears SPY+10pp after tax at today's balances, both on the judge half and without its best 5 events. But
two facts are still outstanding:
1. **B1:** does Schwab pass a holder-level round-up to a 1-share holder? VIVK settles ~2026-10-07. If not, B1 is ~0 and
   the total falls to ~+16pp (A + B2/tenders in the Roth). That still clears +10pp at ~$10.8k, but at $25k it falls to ~+10pp.
2. **A** is FOUND on its own bar at edge-halves. Below 25% of the backtested edge it stops beating SPY; its own forward
   shadow decides that.

**Nothing to build.** A is shadowed by index-beat, B1 is live and the alerts exist. G22's recommendation is **already the
default:** `swingtrader/daily/splitoff_buy.py` and `tender_buy.py` try the Roth's cash first (`for acct in ("roth",
"live")`) and fall back to taxable. The only thing left is to wait for the two live facts above.
