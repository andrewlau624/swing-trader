# Study AW (Round 19) — the night leg on official auction prints: REPORT, restate the night leg by ~−3.8bp/trade

Pre-registration: `round1_prose.md` Round 19 (commit dc53fcb). Scripts: `research/sim/auction_fetch.py`
(data: Alpaca `/v2/stocks/auctions`, SIP, cached in `data/research/night/auctions/`),
`research/sim/auction_audit.py`. Output: `data/research/program/auction_audit_out.txt`. No variant; N unchanged.

## Why
Quantpedia (2025) found that a vendor's daily "open" is the first trade, not the opening cross. On GDX
that turned an 8.6%/yr overnight return into 30%/yr. The program checked the close in add. 6 (90% exact),
and live costs are measured against the auction prints (add. 29). The **backtest's next-open price was
never audited**, and it sets every night-leg number.

## Result (9,546 picks 2021-26, raw pool corr .7; crosses found for 100%, 1 corporate action excluded)

| | vendor ret | auction ret | diff mean (median) | t |
|---|---|---|---|---|
| 2021-23 (n 4,175) | +17.3bp | +14.0bp | −3.2bp (0.0) | −4.4 |
| 2024-26 (n 5,167) | +15.9bp | +11.9bp | −4.0bp (0.0) | −5.6 |
| all | +17.1bp | +13.3bp | **−3.8bp** (0.0) | −7.5 |

- The close the backtest pays equals the closing cross (median |diff| 0.0bp). **The bias is at the open.**
- The median is 0, but 20-24% of picks differ by > 10bp, and the vendor open sits above the cross on
  average. The bias is biggest in cheap names: < $10 −5.8bp, $10-20 −4.7bp, > $20 −2.1bp.
- This is not a live cost: live sells are already measured against the cross. It is a backtest level
  error. The pre-registered rule (> 3bp in either half) fired, so **every night-leg level is restated.**

## Restated books (fixed capital, %/yr, vendor → auction)

| book, night cost | $2.3k | $10k | $25k |
|---|---|---|---|
| V7, 2.5bp/side | 32.7 → 30.7 (−$46/yr) | 34.6 → 32.3 (−$227) | 35.1 → 32.8 (−$583) |
| Roth cash IBS+night, 2.5bp/side | 21.2 → 19.4 (−$42) | 23.0 → 20.9 (−$208) | 23.5 → 21.3 (−$532) |
| V7, tier_hi | 17.9 → 16.1 | 18.1 → 16.1 | 18.3 → 16.3 |
| Roth, tier_hi | 7.7 → 6.1 | 7.9 → 6.1 | 8.1 → 6.2 |

- **What it changes:** about −2pp/yr on every book with a night leg. Study AQ's crossover moves about
  2bp/side tighter, from ~6bp to ~4bp/side.
- **What it does not change:** no earlier verdict flips. Night-leg variant studies compare variants on
  the same returns, and AU3 re-judged on auction returns passes. The Roth cash book (IBS + night) still
  beats IBS-only at measured costs; re-check AQ's gate at ~4bp/side before switching it on.

## Follow-ups run (2026-10-01, reports, no N)
- **AQ's Roth gate on auction prints** (`research/sim/aq_auction.py`, `aq_auction_out.txt`; cash-IRA
  replay, $3k, whole shares + probe). IBS-only 18.6%/yr. IBS .5 + night .5: 22.8% at 0bp/side, 19.9% at
  2.5, 18.2% at 4, 17.0% at 5 (vendor: 25.0 / 22.0 / 20.2 / 19.0). **Crossover 3.7bp/side** (vendor 5.4;
  2021-23 1.9, 2024-26 5.1). At measured live costs (~0bp/side, add. 29) IBS+night still wins by +4pp, but
  the gate is now **≤ ~3bp/side**, not ~5. Updated in config comments (`roth_cash_ira`).
- **IBS leg on opening crosses** (`research/sim/ibs_auction_audit.py`; 18 ETFs' crosses 2016-26, 1,385 of
  1,386 legs): cross minus vendor per leg −0.27 / −0.34 / −0.74bp (2016-20 / 21-23 / 24-26), median ~0:
  **immaterial** (liquid ETFs). Books with both legs on crosses, 2.5bp/side: V7 $10k 34.6 → 32.1%, Roth cash
  23.0 → 20.7% (almost all of it the night leg).

- **Standing rule:** run new night-leg studies on `auction_audit_picks.pkl` returns (cached, free;
  `auction_audit.with_rets`).
