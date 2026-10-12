# Crypto access + funding-carry ceiling (deep loop iter 1, 2026-10-12, no N)

## Access (sources, checked 2026-10-12)
- Schwab spot crypto: Schwab press release 2026-04-16 (Schwab Crypto, phased rollout, via Charles Schwab Premier Bank);
  CoinDesk 2026-05-13 (rollout began, BTC/ETH); fee 75bp/trade per coinalertnews/reelfinancial (secondary, unconfirmed).
  No source says IRA-eligible -> treat as taxable-only. 75bp/trade kills any frequent crypto trading at Schwab.
- Coinbase US perp-style futures: coinbase.com blog "Coming July 21: US Perpetual-Style Futures", help.coinbase.com
  funding-rate page (hourly premium-based funding, no interest component stated). Fees 0/0.03% are a third-party figure.
- Roth: only spot-crypto ETFs in US hours.

## Funding carry ceiling (Binance UM BTCUSDT/ETHUSDT 8h funding, data.binance.vision, 2020-01..2026-09)
Sum of funding per year (gross, % of notional): BTC 17 / 31 / 4 / 8 / 12 / 5 / 2 (2020..2026 YTD); ETH 27 / 38 / 1 / 8 / 13 / 5 / 1.
Excess over T-bills (~4-5% since 2023): 2022-26 ~ -3..+8pp gross, 2025-26 negative; only 2020-21 (+13..+34pp) clears.
Capital efficiency ~0.75 (spot leg + perp margin), fees ~10-20bp per rebalance, honest capture 50%:
- $2.3k / $10k / $25k: ~+1-3pp/yr long-run average, ~0 or negative in the current (2025-26) regime. $100k: same %, capacity unlimited.
- Coinbase US funding (premium-only) snapshot 2026-09 was 0.0019%/h (~17%/yr annualized), which conflicts with
  Binance's ~3%/yr 2026; one snapshot, no history pulled: not evidence.
Verdict: CEILING-KILL. Carry only pays in euphoric bull regimes (2021), when it is a disguised short on crash risk.
Funding-as-positioning-signal for BTC/ETH direction = crowded-positioning class (COTX dead) in a new costume: not run.

## Iter 4: crypto mechanism ceiling table (pre-test estimates, no data read, no N)
Costs for a US retail account: Schwab Crypto ~75bp/trade (taxable only); Coinbase Advanced spot ~40-60bp taker at
small volume; Coinbase US perps 0-3bp; IBIT/ETHA ~1-3bp (Roth-eligible, US hours only). Short alt exposure: not
available to US retail (Coinbase US perps cover a handful of majors). Ceiling at $10k, honest capture 50%.

| mechanism | who pays / constraint | ceiling @ $10k | verdict |
|---|---|---|---|
| Perp funding carry (iter 1) | levered perp longs | +1-3pp long-run, ~0 2025-26 | CEILING-KILL |
| CME spot-futures basis (long IBIT / short MBT micro) | levered futures longs | basis ~5-7% now minus 4% bills ~= +1-2pp; one MBT ~$8.6k notional + margin: impossible at $2.3k | CEILING-KILL |
| Weekend / Monday-open (24/7 vs ETF hours) | none named | calendar effect, no forced flow; ETF-window flow already dead (BTC-FIX) | KILL (no mechanism) |
| Spot-ETF create/redeem flow vs spot | APs | BTC-FIX dead, ETF-flow family closed | DEAD |
| Token unlocks / vesting cliffs | unlocked insiders sell | payoff on the short side; no alt shorting for US retail | ACCESS-KILL |
| Exchange listings / delistings | announcement buyers | move is in the announcement gap; post-listing drift is short-side | KILL (gap + short) |
| Stablecoin depegs (fiat-backed, redeemable at par) | panic redeemers | ~0.7 events/yr x ~6% x 100% x 50% ~= +2pp; tail = reserve loss | CEILING-KILL |
| Liquidation cascades | liquidated longs | LIQ-CASC dead (cascades continue) | DEAD |
| **Crypto-treasury company (DAT) discount to BTC NAV (mNAV < 1), long DAT / short BTC hedge** | discount closes via buybacks, mergers, liquidations, activists (CEF-like) | 30% discount x ~1/3 closing per year x 50% deployable x 50% capture ~= +2.5-5pp; fatter if events (mergers at NAV) cluster | **OPEN, needs data check** (sample 2025-26 only, in-sample; forward shadow at most) |

Only the DAT discount is not dead on paper, and its ceiling is still near or below the gate. Next Track C step: check
whether free daily BTC holdings per company exist (bitcointreasuries / 8-K counts) and how many DATs had mNAV < 0.8 for
more than 20 sessions. If fewer than ~15 names, it is DATA-LIMITED; log it and leave it.

## Iter 6: DAT discount data check -> DATA-LIMITED (no N)
- CoinGecko `/public_treasury/{entity}/{coin}/holding_chart` (docs.coingecko.com/reference/public-treasury-entity-chart):
  holdings back to 2020-08, but the free Demo tier is capped at 365 days (Basic $35/mo 2y, Analyst $129/mo max); step series
  (~weekly / per transaction), not daily. EDGAR 8-K rebuild is feasible but needs SEC_USER_AGENT (absent from .env).
- Episodes: ~40% of BTC treasuries < 1.0x mNAV in Jan 2026 (Bloomberg/bitcointreasuries via an Empery proxy); Sep 2026 Twenty
  One 0.73, Nakamoto 0.90; Strategy < 1 around 2026-06-27. Resolutions are anecdotal: Strive/Semler stock merger at ~0.8x
  (2025-09), ETHZilla sold ETH + buybacks, Empery activist liquidation demand (its own proxy: buybacks narrowed then the
  discount persisted). No systematic convergence study. MSCI did NOT exclude DATCOs (2026-01-06).
- Verdict: DATA-LIMITED, and the anecdotes lean to persistent discounts. Ceiling was already ~+2.5-5pp at $10k. Leave it.
  Reopen only if SEC_USER_AGENT is set and an EDGAR holdings rebuild is wanted for other reasons.

## Iter 8: Coinbase US perp-style futures as a carry / financing venue (no N)
- US500 perp (US5-19DEC30-CDE; launched 2026-08-17): tracks the MarketVector MVUS5P index (NOT the S&P 500, though press says
  "S&P"), contract = 1 index (~$3,150), Sun 20:00 - Fri 17:00 ET, hourly funding = hourly premium/24, 60/40 tax.
  Public API (api.coinbase.com/api/v3/brokerage/market/products/...) 2026-10-12 16:00Z: US500 funding -0.0006%/h
  (~-5%/yr, shorts pay), OI 1,204 contracts (~$3.8M), ~$9.6M/day; BTC nano perp +0.0011%/h (~+9.6%/yr). Earlier
  snapshots (Sep 2026 product pages): US500 +0.0015%/h (~+13%/yr), BTC +0.0019%/h (~+17%/yr).
- Two ideas checked: (a) cheap leverage for the book via a long perp instead of 12.5% margin: funding swings between about
  -5% and +13%/yr, so it is not reliably cheaper, and it is index beta, not edge (Goal L / UPRO sleeve = user decision).
  (b) Harvest rich funding (long VOO / short US500 perp): tracking error MVUS5P vs S&P plus an unknown funding mean.
- No public funding history ("available on request"); the index level history is not free intraday. Verdict: DATA-LIMITED.
  Cheapest test = a forward hourly funding logger (one public GET/hour) for US5/BIP/ETP; it needs a server cron = user OK.
