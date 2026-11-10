# FF-P2 (2026-11-10, no N): CLAUDE.md search priority 2 branch list, all five ceiling-killed

Task: strongest untested structural / forced-flow event edge where small size helps. Excluded up front: odd-lot tenders,
CPC split-offs/round-ups, IPO quiet period/lockup, SSR-LIFT, index-LETF rebalance (memory 97), LLM/text.
Formula: events/yr x net edge x share deployed x capture (50%). Gate: +8pp at $10k. Program N stays 1209.

| branch | input / fill / counterparty | $2.3k | $10k | $25k | ledger before today |
|---|---|---|---|---|---|
| SPAC discount-to-trust at extension votes / liquidation | trust/share from 10-Q, vote dates; buy in session, redeem (manual, 1-3 wk lock) or hold to liquidation; exiting holders | 1.5pp | 1.5pp | 1.5pp | SPAC trust yield ceiling-killed (prose 8984, L16) |
| SPAC public-warrant redemption calls | 8-K call notice, warrant + common; buy warrant / short common, exercise; holders who must exercise or get $0.01 | 2pp | 2pp | ~1.5pp (thin warrants) | new form; DL2 (SC TO-I exchange offers) dead |
| small-deal cash merger arb + break model | DEFM14A/8-K deal price; buy in session, cash-out at close; target holders who sell on announcement | 2.3pp | 2.3pp | 2.3pp | MERG-CASH N 841, B3, B4 dead; prose 10533 dedupe |
| small-name index deletions (S&P 400/600, Russell June, dividend-index cut deletions) | index notices; buy effective-date close cross, sell T+1..5; index funds | 4.5pp | 4.5pp | 4.5pp | S&P/MSCI rebound 1.5pp, Russell killed at gate |
| non-CEF transferable rights (BDC/REIT/opco) | prospectus terms; rights vs stock arb / oversubscription; non-participants | 0.6pp | 0.6pp | 0.6pp | rights DEAD by prior; CEF-RIGHTS N 1084 wrong sign |

Inputs: SPAC 17 rotations x 0.3% excess over T-bill; warrants 20 calls/yr (2025 wave) x 2% net of HTB borrow; merger arb uses
MERG-CASH's own completed-deals-only figure (8.7%/yr total, i.e. perfect break foresight) minus BIL ~4% = 4.7pp before capture;
deletions 4 S&P rebalance days x 1.5% + Russell 1-1.5pp; rights 20/yr x 2% x 30%. ETF/ETN closures (DL6, ETN acceleration),
mandatory converts and Dutch (memory 66), pref calls (memory 85), 2a-7/fallen angels (0.4pp) are already in ledgers.

Verdict: no survivor, so nothing was pre-registered or run. This agrees with memory 37: the free-data forced-flow space is
exhausted for shape B/C; the merger-arb ceiling is capped by its own perfect-foresight number, not by an estimate.
Not tested: any branch with data (no event tables built); warrant price vs exercise value on thin warrants (Sharadar has
no warrant category; would need Alpaca/SIP warrant symbols + EDGAR call notices); SPAC discounts in the 2025-26 revival;
S&P 400/600 membership (not on disk). A reopen needs a per-event edge >= ~8% (warrants) or a new data source.
