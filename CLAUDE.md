# Standing context for Claude (read before any sizing, ROI or "is it worth it" call)

## Priority: % return on the money that exists now (user, 2026-09-30)
- The user cares most about **more return on lower money**: today's balances (Schwab taxable
  ~$2.3k as of 2026-09; Roth $1-3k) and the next few years of growth (to ~$25k). Rank ideas
  by **%/yr at $2-25k** after costs, whole shares and margin rules. An edge that only pays
  at $100k+ (MNQ needs ~$29k for one contract; capacity fixes) ranks below anything that
  pays now, however large it gets later.
- Report money at **$2.3k, $10k and $25k** first. Add $100k / $500k as one line for
  capacity: say where the edge breaks (Study V: the night leg peaks by ~$250k), but do not
  let large-size scalability decide a ranking.
- Small size is an advantage to use: thin names, auctions and odd lots have no capacity
  limit at $2-25k. Whole-share rounding and the $2,000 margin / intraday minimums are the
  real small-account constraints; model them.
- Roth IRA: **$7,500/yr of new contributions is guaranteed, every year**. Model the
  Roth as a growing account (+$7.5k/yr, compounding tax-free), not a static
  $1-3k. Roth rules still apply: no shorting, limited margin, no intraday margin
  buying power.
- "Deposits beat alpha at $2k" is true in dollars and is not an argument against
  research: %/yr compounds on every deposit.

## Sessions (23/5 trading from 2026-12-06)
- The book trades only the official 09:30 / 16:00 auctions and the regular session. Take session
  times from the exchange's regular-hours calendar (`signals.regular_clock`), never from a broker
  clock or a vendor "day" (which may start at 21:00 the evening before). Label bars/fills by trade
  date (`marketdata.trade_date`). Anything new that reads a daily bar or quote open/high/low must say
  why it is regular-hours, or use regular-hours minutes (`marketdata.rth_minutes`).

## Everything being tested goes on the weekly digest (user, 2026-10-02)
- Any new shadow, watch, alert, log-only switch or forward-only weight gets an entry in
  `swingtrader/daily/testing.py` REGISTRY **in the same commit** (name, what it tests, start date, gate count,
  a one-line reader). The weekly digest's "Being tested" section and `make testing` list every entry with its
  count, what's new this week and where it stands. `tests/test_testing_registry.py` fails if a module with a
  `LOG_NAME` or a `shadow` key under `daily:` in config.yaml is not covered. When a test ends (passed and
  switched on, or killed), remove its entry in the commit that ends it.
