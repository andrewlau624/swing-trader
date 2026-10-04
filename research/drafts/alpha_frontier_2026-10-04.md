# Alpha frontier map (2026-10-04): forced / structural mechanisms not yet tested here

Literature + repo grep (do-not-redo table NEXT.md:1013, outside_box_ideas, discovery_ideas, max_edge_candidates,
RESULTS add. 34/35). Nothing below is measured yet; every published number needs a ~40-60% post-publication haircut
(McLean-Pontiff). Honest headline: **the forced-flow map is mostly used up for this account; no candidate promises a
large edge.** The one sizable, untested area is closed-end funds (CEFs): retail-held, unshortable for most, constrained
arbitrage. Already dead/done here (not re-proposed): Treasury month-end, pension rebalancing (watch), VIX-ETP rolls,
fund fire sales, Reg SHO threshold, FTDs, OPEX pinning, spin-off orphan day, small-index/sector recons, buffer/YieldMax
resets, ADR-home, SPAC floors, merger arb, lockups, ETF closures/term CEFs, buyback blackouts, dividend pay days, Roth
ex-div capture, CEF activists (G45, NEAR), CEF insiders (G54, dead), S&P add/delete, auction imbalance, LETF flow.

| # | candidate | forced / incentivized party | why they lose | why it persists | executable at $2-25k | est. net | untouched OOS data | status |
|---|---|---|---|---|---|---|---|---|
| 1 | CEF discount vs its own history (Pontiff 1995; Patro-Piccotti-Wu JFR 2017) | retail holders selling at panic discounts | sell below NAV | noise-trader risk, no shorting, small funds | yes, long-only, Roth | 2-5%/yr over PCEF on a full sleeve | prices 2016+ (Alpaca); **daily NAV history is the blocker** (CEFConnect scrape, N-PORT monthly 2019+) | test first if NAV data can be built |
| 2 | Dividend-month premium (Hartzmark-Solomon JFE 2013) | dividend-seeking retail / income funds | pay up before ex-date, then -72bp reversal | preference, not information | yes, Roth only | +1.5-3%/yr over SPY | Alpaca + repo dividend calendar, 2016+ unseen for this rule | test |
| 3 | CEF December tax-loss selling -> January (Starks-Yong-Zheng JF 2006; Carrion JFR 2024) | taxable retail must realize losses by Dec 31 | sell into thin December books | the tax code | yes, 4 weeks/yr | +0.2-1%/yr on the account | 10 Decembers (low power) | arm of #1 |
| 4 | CEF rights offerings, price path after expiry (Khorana-Wahal-Zenner JFQA 2002) | rights arbs short until delivery; non-subscribers sell | dilution + supply | manager fee incentive | yes | +1-3%/event x 10-25/yr | EDGAR full text 2016+ | cheap test (count first) |
| 5 | Spin-offs after the forced-selling window (Greenwood-Sammon: index effects shrinking) | index / mandate holders dump small spincos | mechanical selling | mandates | yes | 0-4%/yr, weak prior | EDGAR Form 10 + Alpaca 2016+ | low prior |
| 6-9 | small-cap tax-loss Jan rebound; IPO quiet-period expiry; non-traded BDC/REIT listings; first December Russell recon (2026-12-11) | | | | | ~0-2%/yr or unknown | | fold / one-shot kill / forward watch |
| x | dropped: GSCI roll, thin-ETF NAV premium (no NAV history), fallen-angel bonds (markups), HTB overpricing (long-only can't harvest), heartbeat trades, MSCI reviews, stock-for-stock merger arb | | | | | | | |

Options are closed: T1-T7 (`study_contest_t*.md`) and T5L (`study_t5l.md`: the earnings fly's mid-to-mid +20% was a
liquidity mirage; in liquid names it is +3.3% of risk vs ~3.7% round-trip spread, judge 2016-22 -3.4%/trade). Execution is not a hidden cost (audit_execution_1002.md).
First pre-registerable tests, in order: (1) CEF discount z-score, 5 most-discounted vs own 52-week history, monthly,
2016-20 judge, kill < +3%/yr over PCEF or placebo equal; (2) dividend-month premium, 2016-20 judge, kill < 15bp/month
net or no post-ex reversal; (3) CEF rights post-expiry, count events first, stop if < 40.
