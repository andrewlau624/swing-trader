# Study A-OPEX: does open-interest concentration pin the underlying at expiration?

Pre-registered 2026-10-04 (this cycle), before any OI for these dates is read. Mechanism probe,
not a strategy: no N bump.

## Mechanism / counterparty
Index-option market makers who are net short gamma at a concentrated strike must hedge
mechanically: buy as spot falls toward the strike, sell as it rises. The prediction is that on
expiration day the underlying is *attracted* to the strike with the largest open interest near
spot — a predictable underlying flow caused by dealer hedging.

## Data
- **OI:** Databento OPRA.PILLAR `statistics` (daily open interest = `stat_type == 9`), pulled for
  each monthly OPEX day only (single-day ranges, ~$0.4/day). Expiry parsed from the OSI symbol.
- **Underlying:** SPY regular-session open/close from `etf_daily`.
- **Events:** monthly OPEX (3rd Friday), 2023-01..2024-12 (24 events).

## Rule (frozen)
1. K* = strike with the largest total OI (calls + puts) among contracts expiring that OPEX day,
   within +/-3% of the prior close.
2. Signal at the open: d = K* - open(OPEX day). Trade the underlying in sign(d) from open to close.
3. Placebo: same rule using the SECOND-largest-OI strike (K2) in the band.
4. Costs: SPY open/close auctions ~0.5bp round trip.

## Prediction / kill
- If pinning is real and tradable, the K* rule beats the K2 placebo in hit rate and net return,
  and the effect is larger when |d| is larger.
- **KILL if** K* does not beat K2 in hit rate, or net return <= 0 after costs, or the effect is
  carried by <5 events. A null closes the "index-OPEX OI pinning" mechanism as a standalone edge
  (underpowered at 24 events; extension to 2013-2024 is ~$110 if the first look is positive).
