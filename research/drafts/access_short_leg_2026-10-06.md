# Access audit — short leg / margin (third-robot session, 2026-10-06; data VERSIONED per the
# standing rule: no pre-June-2026 PDT assumptions; account facts marked CONFIRM-IN-ACCOUNT)

## What the system already expresses (code, verified)
- `swingtrader/daily/brokers.py:312-345`: the Schwab submit path splits a sell into
  `SELL + SELL_SHORT` and a buy into `BUY_TO_COVER + BUY`. **Short orders are expressible with
  the existing client.** What does not exist: any live routine that opens/holds shorts (the books
  are long-only by construction), and no user OK has been given for real short orders.
- Order routing: MOC/close working, directed open-sell destinations (proxied `open_destination`),
  whole shares only (no fractional orders via API — `submit` floors notional to shares).

## Regulatory facts (date-versioned)
- FINRA Rule 4210 amendments approved 2026-04-14, effective 2026-06-04, firm phase-in 2027-10-20:
  PDT trade-count retired; real-time intraday margin buying power for margin accounts >= $2,000.
- Reg T $2,000 minimum equity for a margin account — the binding floor at the current $2.3k taxable
  size (the current account is JUST above it: a short book + long book both draw from $2.3k equity).
- Roth: no shorting, no intraday margin — all short-leg work is taxable-margin-only, i.e. is
  limited to ~$2.3k equity until further deposits.

## Schwab house facts (CONFIRM IN ACCOUNT before any live use)
- Stock shorts require margin eligibility per name; names below ~$5 and OTC/bulletin-board
  names are typically not marginable — the operable universe is mostly listed $5+ names (matches
  the night leg's existing $5-2000 filter, whose ADV >= $10M gate keeps borrow-balanced names).
- Maintenance margin: SEC floor 25% (15c3-1); Schwab house generally ~30%, higher specials on
  concentrated/volatile names. Shorts on HTB names incur borrow fees and are subject to recall —
  the recall right is a Schwab-announced event with minutes' notice and is the tail that kills
  naive squeeze-shorts.
- Borrow fee/rate per name is visible only at order entry (the API does not expose a rate table);
  availability is only observable by attempting.
- Unverified: exact Schwab short-maintenance schedule for the account's current tier; whether the
  account has Margin enabled at all (config only proves the API path works). CONFIRM.

## What a short leg actually unlocks, ranked by $-value at $2-25k
1. **NAV/liability-side pairs** — short the rich leg of premium/discount structures (CEFs vs
   pectus, closed twins vs ETF/NAV) IF the NAV data track below yields anything. Highest
   mechanism-quality: a real anchor, not prediction.
2. **Hold-to-resolution hedges** — the CPC exclusion said the UMH-style hold-only position cannot
   capture its hedge without shorts; a short leg restores the hedge/flip inside CPC accounting
   (user decision; standing rule: no positions opened for data).
3. **Forced-flow shorts where the buyer is underground**: fallen angels, margin-call-cascade names
   — remain DATA-BLOCKED (PIT ratings, margin-rate series), so shorting alone unlocks nothing here.
4. **Borrow-rate dataset creation** — the one dataset the frontier named BLOCKED becomes
   FORWARD-COLLECTIBLE: log every SELL_SHORT rejection/expiry/locate event + Schwab's
   shortability fields, on the server, from day 1 forward (spec `BOROW-SNAP` below; needs user OK
   for any live-editing of the daily job).
5. **Pair-CLASS-style dislocations** — killed-by-scale (6 fills/yr on GOOG/GOOGL); short access
   does NOT change the fill-frequency: do-not-reopen stands.

## Spec BOROW-SNAP (forward-only collector; NOT implemented; needs user OK for server edits)
- Each live decision session, after orders: log `{date, symbol, side, instructions[], reject?
  reason}` for every order and any SELL_SHORT rejection — this is the only borrow-observable
  Schwab exposes. Append to `state/borrow_snap.jsonl`.
- Weekly: the full positions' borrowable flags from the account API. Merges into the same line.
- No trading behavior change; a pure log. Registry entry required per the standing "everything
  being tested" rule when the job goes live.
