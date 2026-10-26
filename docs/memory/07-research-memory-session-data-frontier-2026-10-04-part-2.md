# Research memory — session "data frontier" (2026-10-04, part 2)

The binding constraint is data access, not idea generation. This session finished the two
cheapest high-value tests and mapped what each remaining mechanism actually needs.

### Correction to prior memory
- "Pre-2021 stock data blocked: the repo has no pre-2021 stock bars anywhere" was a **cache**
  limit, not a source limit. **Alpaca serves pre-2021 stock bars (2016+), including
  inactive/delisted symbols** (verified with AAPL/TWTR/ATVI/GE; fetched into
  `data/cache/bars_pre2021/`). The night-leg OOS is therefore TESTABLE; stop calling it
  blocked. (The default `data/cache/bars` stays 2021-2026 — always fetch the old range into a
  separate cache or it evicts the current one.)

### PHASE 1 results
1. **Night-leg OOS 2016-2020** (`research/sim/night_oos_pre2021.py`; picks
   `data/research/program/night_pre2021_picks.parquet`). Daily-bar reconstruction of the live
   rule (close/prev_close <= -8%, IBS<0.10, $5-2000, vol20>=60%, ADV>=$10M; buy close, sell
   next open); universe = the swing cache incl. ~14% inactive names. **Positive every year:**
   2016 +16.5 / 2017 +31.5 / 2018 +16.2 / 2019 +84.9 / 2020 +139.3 bp/trade; pooled +108bp
   (t 14.4), **ex-2020 +36bp (t 3.5, ex-top-5 +26.5)**. Liquid names earn MORE (+138bp) than
   illiquid (+91bp) -> not a microcap premium. The same daily-bar rule on 2021-26 = +47bp
   (t 10.2). **Conclusion: the loser-bounce is not a 2024+ artifact; it was positive
   pre-2021, and its strength tracks volatility.** Caveats: daily-bar, not the 15:40 live rule
   (optimistic ~2x); survivorship-limited (inactive included, fully-removed dead tickers not);
   no costs. **SUPERSEDED by the exact 15:40 test (part 3 below): the daily-close selection
   is optimistic; the exact rule is weak and regime-concentrated, not a stable pre-2021 edge.**
2. **Book beta/factor decomposition** (`research/sim/book_decomp.py`; out
   `data/research/program/book_decomp_out.txt`). Factors must be WINDOW-MATCHED (close-to-close
   SPY is off by a day and wipes the correlation). Night leg: alpha 7.1% (t 1.5) after TECH
   +35.7 (t 3.5) and SIZE +17.8 (t 3.1) -> weak alpha, much of it is a levered small-cap/tech
   overnight bet. IBS: alpha t 1.8, MKT beta +15.9 (t 3.3). **Noise (intraday): alpha 13.0%,
   t 3.0 — the one significant residual.** Total book: overnight SPY beta +0.31 (t 3.5).
   **The book is not pure alpha; the overnight legs are partly style/beta and the clearest
   residual alpha sits in the intraday leg.**

### PHASE 5 result (settlement / forced buy-in)
- **Reg SHO threshold close-out** (`research/sim/threshold_probe.py`). Threshold episodes
  (5+ consecutive settlement days with fails >= 0.5% of shares) 2021+: n=2241. The mandated
  close-out deadline is 13 settlement days after the first threshold day, but the SEC FTD file
  is public only ~20 days later — **the forced-buy window had already passed when the data was
  public in 2234 of 2241 episodes**. Post-publication the names keep falling (abn -2.8% at +5d,
  t -7.5), but they are by definition the unborrowable names (short side inaccessible) and the
  drift is a distress premium. **Verdict: the forced flow is real but NOT harvestable from SEC
  FTD; the timely source would be the daily exchange/OTC threshold lists, and the payoff is on
  the untradable side.** Do not re-run FTD-spike tests (jump R3-2/R3-16 dead).

### Data map — what each frontier mechanism needs
`AVAILABLE` = testable now; `TARGET` = acquire; `NO` = do not pretend we tested it.

| mechanism | required fields | depth / PIT | access / cost | status |
|---|---|---|---|---|
| Night-rule OOS incl. delisted | daily OHLCV, PIT listing | 2016+ (could go to 2016 Alpaca limit) | Alpaca SIP, keys in `.env` | **AVAILABLE** (fetched) |
| Borrow / HTB / recalls | daily borrow fee, utilization, recall notices | PIT 2015+ | IBKR API needs funded acct; Ortex/Fintel paid | **NO free history**; proxies below |
| \_ borrow proxies | bi-monthly short interest, FTD, short volume | FINRA SI free 2020+; FTD cached 2015+ | FINRA API (free), SEC FTD (cached) | **AVAILABLE**, but no fee/recall info |
| Fallen-angel forced selling | PIT issuer ratings (and/or bond spreads) | 2000s+ | ratings paid (WRDS/Compustat); TRACE bond prices partial | **TARGET**; free ratings do not exist |
| Settlement / buy-ins | daily threshold lists + FTD + shares outstanding | FTD/shares cached; threshold lists not | Nasdaq/NYSE daily lists need scraping | **TARGET** (lists); FTD+shares AVAILABLE |
| Margin-call cascades | daily + margin/borrow stats | — | none free | **NO**; price proxy only |
| Vol surface / dealer positioning | historical option chains + OI | 2013+ | Databento OPRA cbbo-1m, key in `.env`, ~$0.001/sym-day | **TARGET** (paid, cheap for targeted pulls) |
| ETF creation/redemption flows | daily shares outstanding + NAV | 2016+ | issuer sites / ETF.com, no free bulk API | **TARGET** (scrape) |

- SEC EDGAR / FTD index gives **403 without `SEC_USER_AGENT`** (absent from `.env`). Setting it
  (with the user's contact) is a one-line, user-approved change that unblocks EDGAR pulls.
- Databento was used for the options contest; historical OPRA is obtainable at low cost, so the
  vol-surface and dealer-positioning mechanisms are acquisition-feasible, not impossible.

### Remaining frontier (ranked by information gain x accessibility)
1. **Delisted-complete pre-2021 night test** (`asset_meta.json` + Alpaca 2016 bars for the
   inactive universe) — turns PHASE 1's supportive result into a decisive one.
2. **Historical option chains via Databento** (vol surface, dealer positioning) — paid but
   accessible; unlocks two mechanisms plus better options-cost modelling.
3. **Borrow-fee / HTB history** — the one named counterparty (short sellers) with no data;
   without it borrow stays a proxy game (FINRA SI / FTD / short volume).
4. **Point-in-time ratings** (fallen angels) — no free source; needs a paid vendor or a
   bond-spread/TRACE proxy.
5. **Daily threshold lists** (settlement) — scraping task; the payoff side is unborrowable.
6. **Daily ETF shares-outstanding / NAV** — scraping task; unlocks creation/redemption flows.
