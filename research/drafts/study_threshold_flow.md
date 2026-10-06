# Study THR: Reg SHO threshold-list forced-buy window (pre-registered 2026-10-04)

Before reading any outcome. Free data. Mechanism probe, not a strategy variant (no N bump).

## Mechanism (who is forced, when)
A security is a **threshold security** when aggregate fails-to-deliver are >= 0.5% of shares
outstanding (and >= 10,000 shares) for **5 consecutive settlement days**. From the day it appears
on the SRO list, **Reg SHO Rule 203(b)(3) forces the clearing member carrying the fail to close it
out within 13 consecutive settlement days** (buy-in). That is a mandated, deadline-bound **buy**.
- Forced party: the clearing member/broker with the persistent fail.
- Window: published at list_start (5th consecutive qualifying day, known after the close); the
  buy-in must complete ~13 settlement days later.
- Question: is there predictable abnormal **buying** (price/volume) in that window, and is it
  tradable long-only (the names are hard-to-borrow, so the short side is inaccessible)?

## Data
- Threshold status: SEC fails-to-deliver (`data/research/jump/ftd/`, 2015-12+), `frac = qty/shares`
  (shares from XBRL). Same definition as the SRO list; all exchanges. Nasdaq daily lists
  (`nasdaqthYYYYMMDD.txt`, 2008+) are equivalent and used to spot-check.
- Bars: `panel.pkl` (SIP daily, 2020-10..2026-09, ~14k symbols). **Survivorship-limited**; episodes
  2016-2020 are fetchable from Alpaca later.

## Rule (frozen)
1. Episode: a run of >= 5 consecutive settlement days with frac >= 0.005 and qty >= 10,000.
   `list_start` = the 5th day. `deadline` = list_start + 13 settlement days.
2. Entry = open of the first trading session after `list_start` (the list is public that evening).
3. Long-only (short side is unborrowable). Measure CAR to the deadline and to +4/+8 sessions;
   abnormal vs the equal-weight panel return over the same window.
4. Volume: mean daily volume in the window / 20d ADV at entry (forced-execution footprint).
5. Overnight (open/prevclose) vs intraday (close/open) split.
6. Placebo: same symbol, a random non-threshold window of the same length.

## Kill rule
KILL if long CAR <= 0 after a 50bp round-trip cost, or no abnormal volume spike, or < 100 events.
A null means the forced flow is real but not harvestable long-only (short side inaccessible).
