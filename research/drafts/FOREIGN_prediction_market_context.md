# FOREIGN RESEARCH — prediction-market / Kalshi material (NOT Trader evidence)

> **Classification: cross-project contamination. Do not treat as Trader research.**
>
> Prediction-market / Kalshi research was introduced into this repository during a
> cross-project contamination event. It is **not** part of the Trader's validated research
> universe, must **not** be counted as a Trader edge, must **not** set Trader priorities, and
> must **not** be used to argue that the Trader has found alpha. The relevant work belongs to
> the separate **Polymarket project** (a different repository). The Trader must never import a
> conclusion from that project unless the user explicitly asks to investigate that idea here.
>
> This file exists only so the material is preserved and clearly marked, not silently deleted.

Preserved: the Kalshi / Polymarket summary that a previous session mistakenly wrote into
`CLAUDE.md` (2026-10-04). Source of the summary: a read-only exploration of the separate
Polymarket project; all numbers below are **foreign**, quoted for context only.

## Foreign summary (prediction markets)

- **Kalshi LIP (liquidity incentive program).** Measured ~$213,225/day across 5,340 active
  markets (public API, read-only); median ~$14.29/day/market; a full-target two-sided quote
  modelled at a median ~0.42%/day on collateral at snapshot competition (~0.17%/day at 3x);
  ~7% of markets had an empty side. Blocker: no funded Kalshi account, and the reward scales
  with size (median collateral ~$495). Make-or-break unknown: adverse selection / fill markout
  of resting orders (planned test "K2" in the Polymarket project).
- **Polymarket US liquidity rewards.** Median market ~$0.007/day; under the $1 payout floor
  for a small account. Spread-ladder monotonicity pairs proven but ~$107/yr at $100 capital.
- **Polymarket/Kalshi taker effects** (locked pairs, cross-venue lead, calibration,
  copy-trade, combos): failed to replicate — see the Polymarket project's graveyard.
- **Rare structural / settlement / forced-flow events** in prediction markets: deprioritized
  there by an n>=20 bar; a contractual-payoff / mechanism bar would be more appropriate.

## Where this belongs

`/Users/andrewlau/Documents/Code/Projects/trading-lab` (the Polymarket project). Do not
re-import it here. If the user asks to investigate a prediction-market idea *inside the
Trader*, that is an explicit, separate instruction.
