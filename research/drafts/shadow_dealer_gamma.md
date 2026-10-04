# DATA-TARGET / forward shadow spec (NOT run): signed dealer gamma

Status: DATA-TARGET. No paid data. Not the killed OI-pinning study.
- Why it differs from OI pinning (killed: OPEX pin, A-study): pinning is about price being attracted to large-OI
  strikes near expiry. Signed dealer gamma is about the SIGN of dealers' aggregate gamma: when dealers are short gamma
  they must buy rallies and sell declines to stay hedged (amplifying moves, especially into the close); when long gamma
  they lean against moves. The prediction is about direction/continuation and volatility of the market, every day,
  not about strike attraction at expiry.
- Observable required: daily signed net dealer gamma for SPX/SPY (strike x OI x gamma, signed by who is long), known
  before the decision time. Free proxy: SqueezeMetrics GEX in DIX.csv (2011-05..2026-10, daily, model-signed).
- Trade: SPY last-30-minute continuation on short-gamma days (enter 15:30 in the direction of the 09:30-15:30 move,
  exit at the closing auction); long-only half for the Roth.
- Why scalable: SPY/ES are the deepest markets; the hedging flow is index-wide and size-insensitive at $2-250k.
- Minimum to justify buying OPRA (~$180/yr): a forward or untouched-window effect of >= +5bp net per trade at t >= 2 on
  short-gamma days, account >= $10k (payback needs 1.8%/yr at $10k), and a need for strike-level data the free GEX
  file cannot supply.
- Free falsification first: register the rule on the free GEX file and log it forward (the 2016-26 minute window is
  already touched by the market-map probe: +8.3bp, t 1.9). Kill if forward net <= 0 after ~120 short-gamma days.
