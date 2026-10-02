# Discovery DL6: closing ETFs bought in their last week (deal rule, no N) — DEAD

Session llm-trader-c5, 2026-10-02. Registered in `round1_prose.md` ("deal rule DL6", 6c872de) before any price.
Script `research/sim/etf_closures.py`; deals `data/research/events/etf_closure_deals.csv`.

**Contract.** A closing ETF announces its last trading day; remaining holders get the liquidation cash a few days
later. Alpaca records the proceeds as `cash_mergers` for some closures (1,993 cash-merger records 2016-26, 57 on
symbols whose *current* Alpaca name says "ETF"). A data-validity guard was added after the first look at the record
list (before any return): the symbol must stop trading within 10 days of the record's effective date, which drops
reused tickers (BITA, KEM, CCSB ... were stocks). **9 ETF liquidations remain (2022-26).**

| | deals | mean | median | hit | worst / best |
|---|---|---|---|---|---|
| **entry 5 sessions before the last day (registered)** | 9 | −0.07% | **−0.24%** | **33%** | −12% (PLTI, an option-income ETF that paid its last distribution off the books) / +13% (LMNX, a 2x ETF) |
| entry at the last close (info) | 9 | +2.3% | 0.00% | 44% | |

$/yr: ~$0 at every size. **Verdict (median > +0.5%, mean > 0, hit >= 70%): DEAD.** Market makers keep a closing ETF
at NAV to the last day: the median ETF paid out within 0.3% of its price a week earlier. The two outliers are
leveraged/option products whose NAV moved during the week. Alpaca covers only a fraction of closures (most ETF
liquidations have no proceeds record), so the sample is small, but the sign and size match how ETFs trade, with
creation/redemption arbitrage working right up to the last day.
