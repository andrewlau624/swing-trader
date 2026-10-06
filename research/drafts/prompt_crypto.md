# Prompt: a crypto strategy that beats the people on the other side of the trade

Paste everything below the line into a fresh session (a new repo, `crypto-lab/`, kept apart from the
swing-trader live book; reuse its patterns, not its accounts).

---

You are building and testing a crypto trading strategy for a US retail account. Capital: **$2-3k
to start, adding over time toward $25k.** Rank every idea by **%/yr after all costs and taxes at
$2.3k, $10k and $25k**, against two benchmarks: **holding BTC** (same risk) and **T-bills**.
Size where the edge stops working gets one line; it doesn't decide the ranking.

## The core idea
Most retail crypto traders lose money. Fees, funding and leverage are the drains; liquidations
are the visible tail. A small account can't win by predicting direction better than funds with
better data. It wins by **being the side that gets paid**: collecting a structural premium,
supplying liquidity people pay for, or trading flows that are forced and predictable. For each idea,
write one sentence naming **who loses money to this trade and why they keep doing it**. If you can't
name them, the idea is probably noise-fitting. Drop it before testing.

## Where to look (mechanisms, not indicators)
Test only ideas with a named counterparty. Starting list; verify each still exists before testing:
1. **Funding and basis carry.** Long spot, short perp or dated future when funding/basis is high
   (leveraged longs pay it). Check what a US resident can actually trade: Coinbase Derivatives / CME
   micro BTC and ETH futures, contract sizes, margin, and whether one contract fits in $2-25k. The
   shape that fails: funding goes negative or the exchange fails at the worst moment.
2. **Funding extremes as a crowding signal.** Very high funding or open interest, then a liquidation
   flush, then reversion. Who loses: overleveraged longs and shorts getting force-closed.
3. **The spot-ETF bridge.** IBIT/FBTC/ETHA trade only in US regular hours, but BTC trades 24/7. The
   ETF's 09:30 open prices in the weekend and overnight move. Test the same open/close auction
   mechanics the swing-trader night leg uses, ETFs can go in the **Roth** (crypto spot can't at
   most brokers), and wash-sale rules apply to ETFs. This is the closest link to code that already works.
4. **Time-of-day / day-of-week seasonality.** Returns clustered around the US open, the 00:00 UTC
   funding/settlement times, and weekends with thin liquidity. Pre-register the hours **before** looking.
5. **Forced flows.** Token unlocks, index/ETF rebalances, exchange listings and delistings,
   stablecoin depegs and their reversion, big options expiries (Deribit monthly/quarterly).
6. **Time-series momentum on BTC/ETH** (documented in the literature, e.g. Liu & Tsyvinski 2021) as a
   **risk filter** (in or out of BTC), not a stock-picker over 500 alts.

Skip unless something new turns up: TA indicator soups, ML on price alone, altcoin pickers over
current listings, high leverage, copy-trading, memecoin sniping (you are the exit liquidity), and
anything needing sub-second speed against market makers.

## Methodology (non-negotiable; this is what keeps the equities program honest)
- **Pre-register** every variant (rule, universe, hold, cost model, pass bar) in a log **before**
  running it. Keep a running count N of every variant tried and use it in a deflated Sharpe.
- Split data **select / judge / holdout** by time. Touch the holdout once. Crypto regimes differ
  sharply (2017, 2018-19 winter, 2020-21, 2022 collapse, 2023-26), so a pass must hold in **more than
  one regime**. Report every year separately.
- **Survivorship kills crypto backtests.** Include delisted and dead tokens. Exchange-reported volume
  is often wash-traded; use trusted venues only (Coinbase, Kraken, CME, Binance for price discovery).
- **Costs at real tiers for a $2-25k account**: maker/taker fees at the lowest volume tier, spread,
  slippage, funding paid/received, withdrawal fees, and the spot/ETF expense ratio. Most crypto
  "edges" fit inside one round trip of taker fees at retail tiers. Compute the break-even cost for
  every rule.
- Define the daily bar explicitly (00:00 UTC, or US regular hours for ETF legs) and never mix vendor "days."
- Taxes: model US short-term gains on taxable trades. Check the current law on crypto wash sales and
  on broker reporting; don't assume.
- A pass means: beats the benchmark after costs and tax in the judge **and** holdout, t > 2 on
  independent periods, no single-month or single-trade dependence (ex-best-5% check), and a sane
  max drawdown at today's balance.
- Then run **forward shadow only**: log-only for a pre-set count of trades with a written kill rule.
  Money goes in only after it passes, starting small.

## Safety
- API keys trade-only, **withdrawals disabled**, IP-allowlisted. Keep no more on an exchange than the
  strategy needs; exchange failure is a real tail (FTX).
- No leverage above 1x until a strategy has passed forward. Hard daily loss stop in code.

## Deliverables
1. A ranked idea table: mechanism, named counterparty, data source, US-tradable instrument,
   break-even cost, and an expected %/yr range at $2.3k / $10k / $25k.
2. Pre-registrations for the top 3, then results with the full stats above, including the dead ones.
3. For any pass: a forward-shadow spec (gate count, kill rule) and the smallest live version.
Be blunt. "Nothing beats holding BTC after fees at $2k" is an acceptable and useful answer.
