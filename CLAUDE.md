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

## Research memory — session "contest hunt + T5L + execution audit" (2026-10-04, part 4)

### Options hunt: CLOSED for this account (N 791 -> 806)
- 12 judged option variants, every one dead at executable (far-side) NBBO from Databento OPRA cbbo-1m:
  QQQ 0DTE on the noise signal (T1a-c, T2a: -5..-15% of risk/trade, the underlying signal is only +2.6bp/trade in
  2025-26), overnight 1DTE condor/fly (T4: mid-to-mid ~0), intraday 0DTE straddle (T6: -9%), pre-earnings straddle
  (T3: mid +1.5% vs ~20% spread), insider-buy calls (T7: 23% spread at 09:35), short earnings fly (T5, T5L).
  Studies `research/drafts/study_contest_t*.md`, `study_t5l.md`; log `contest_hunt_log.md`.
- **T5 status: DEAD.** Its +20% of risk mid-to-mid (2023-26, >= $2B) was a liquidity mirage. On liquid names
  (20d $ADV >= $1B) judged on untouched 2016-22 with far-side fills (T5L): **-3.4% of risk/trade** (median +3.0%, fat left
  tail; 2016 -15%, 2022 -13%; 4/7 years > 0). In liquid names the earnings premium is ~fairly priced (mid +3.3% of risk)
  and the round trip costs ~3.7% of risk. Do not re-test with filters (news, sector, size): no filter changes the spread.
- Rule for any future options idea: compute mid-to-mid AND far-side on the most liquid names first; a mid-only effect
  in thin chains is a quote artifact, not an edge. Retail cannot capture an option premium smaller than ~2x its spread.
- Data gotchas: the SIP minute matrices (`intra.load`, data/research/night/m1) are DIVIDEND-ADJUSTED (~2% low in 2023):
  option strikes need raw prices. The Nasdaq earnings calendar's marketCap is as-of today (look-ahead): never filter on it.
  Databento credit: ~$4 of $125 left after this session (signal-driven windowed pulls cost cents; month-wide pulls dollars).
- `swingtrader/daily/zero_dte.py` is an uncommitted, untested DRAFT (T1a live mirror); the permission classifier
  blocked editing it further. Not deployed. T1a is a measured loser: do not finish it.

### Execution audit (10-02 and all 130 live fills since 09-23): true cost ~0bp
- Every fill printed exactly at the official SIP auction price. True cost: open auction 0.0bp (n 59), close auction
  -0.2bp (n 57), intraday noise +0.4bp vs mid (n 14). The "~0bp" claim holds.
- `slippage_bps` is NOT cost: it is fill vs a decision-time ref (09:17 broker mark for night sells, prior close for IBS,
  15:40 last trade for MOC buys, the ENTRY price for noise exits), i.e. ref -> auction market drift. `digest.py:256/264`
  feeds that drift (~+43bp) into the "Overnight 1.3x" re-arm text as cost: misleading. Fix list (not done):
  `research/drafts/audit_execution_1002.md`.

### Next unexplored frontier (from `research/drafts/alpha_frontier_2026-10-04.md`)
- No candidate on the forced-flow map promises a LARGE edge at $2-25k; most of the map is already dead or done here.
- Best untested: **closed-end fund discount vs its own history** (Pontiff 1995; Patro-Piccotti-Wu 2017; ~2-5%/yr over
  PCEF after haircut, long-only, Roth-friendly), with arms for CEF December tax-loss selling and CEF rights offerings;
  then the **dividend-month premium** (Hartzmark-Solomon 2013, Roth). Blocker for CEFs: free daily NAV history 2016+.
- Conflicts with the part-3 ledger above, not resolved: that ledger lists fallen angels and ETF creation/redemption as
  TARGETS; the part-4 survey dropped both (dealer markups 1-2% on $1k bonds; no free consolidated ETF NAV history).
  Dealer gamma/OI (part 3, paid OPRA statistics) is a different question from T1-T7 (it predicts the UNDERLYING) and
  remains open.
