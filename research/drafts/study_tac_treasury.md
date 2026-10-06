# Study TAC: Treasury-auction concession and reversal (pre-registered 2026-10-04)

Free data. Mechanism probe. Before reading any outcome.

## Mechanism
Primary dealers must bid at Treasury auctions and warehouse the new supply. To make room, they
sell or hedge existing duration into the auction -> a pre-auction **yield concession** (price dip).
After the auction clears (supply absorbed), the concession unwinds. Counterparty: dealers whose
balance-sheet cost forces them to cheapen the security to the marginal buyer.
- Observable: auction calendar (FiscalData, 1979+), the auction result (`high_yield`, `bid_to_cover`,
  dealer/indirect/direct takedown), and the pre-auction price path.
- Tradable proxy: TLT (20y+), IEF (7-10y), SHY (1-3y) ETFs (free bars 2016+). Best case: a
  buy-the-concession / sell-the-unwind trade on the matching ETF.

## Data
- Auctions: `api.fiscaldata.treasury.gov/.../auctions_query` (free, no key, 1979+). Filter
  security_type in {Note, Bond}, non-callable, offering_amt populated.
- ETF bars: `data/research/night/etf_daily.parquet` TLT/IEF/SHY (2016-2026, raw).

## Rule (frozen)
1. Event = a Note (2/3/5/7/10y) or Bond (20/30y) auction with a populated `high_yield`.
2. Matching ETF: 10y/20y/30y -> TLT; 2/3/5/7y -> IEF; (SHY sensitivity).
3. Windows: AUCTION-3 -> AUCTION (the concession), AUCTION -> AUCTION+3 (the reversal),
   AUCTION+1 open -> AUCTION+3 close (the executable version), close(A-1)->close(A) split.
4. Abnormal = ETF window return minus a duration-matched control (TLT vs SPY, IEF vs SPY).
5. Split by: tail/stop-through (`high_yield` vs the pre-auction 2nd-market yield is unavailable
   free; use bid_to_cover terciles and auction size terciles), 10y vs 30y.
6. Report ex-best-5, by year, and both sub-periods (2016-20 / 2021-26).

## Kill / economics
Kill if no window shows abnormal return > ~spread (TLT ~2-3bp), or the effect is <100bp/yr on the
ETF, or it is carried by <5 auctions. This is meant to be a *capacity* candidate (TLT/IEF are
liquid), so the bar is: an effect big enough to matter after costs across many auctions.
