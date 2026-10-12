# Binance spot daily panel (survivorship-complete)

Source: data.binance.vision bulk dumps, `data/spot/monthly/klines/{SYM}/1d/{SYM}-1d-{YYYY}-{MM}.zip`, listed via the S3 index. Pulled 2026-10-12. Raw zips in `raw/` (28,245 files, 111 MB). Monthly zips only (2017-08 through 2026-09); the current month (Oct 2026) is not included.

Files: `panel.parquet` (long: date, symbol, open, high, low, close, volume, quote_volume, trades, plus per-symbol base, first_date, last_date, delisted, is_stable_fiat, is_leveraged, on_coinbase_us), `symbols.csv` (one row per symbol).

## Counts
- Spot symbols in the dump: 3,745 total; 757 USDT-quoted (756 have rows in the panel; 1 has no data), 489 BTC-quoted (BTC-quoted not downloaded).
- Panel: 844,541 rows, 2017-08-17 to 2026-09-30.
- delisted (last_date < 2026-09-01): 249 of 756; 202 have last_date before 2026-01-01.
- Flagged is_stable_fiat: 22 (USDC, BUSD, TUSD, FDUSD, DAI, USDP, EUR, GBP, AUD, AEUR, EURI, USD1, USDE, RLUSD, USDS, USDSB, SUSD, UST, USTC, PAX, XUSD, BFUSD). is_leveraged: 50 (*UP/*DOWN/*BULL/*BEAR tokens; SYRUP is not leveraged and is unflagged). Flags are name-based. Rows are kept; filter them out for a clean universe (683 symbols, 190 delisted).
- Symbols with data per calendar year (any row that year): 2017 6, 2018 24, 2019 90, 2020 245, 2021 353, 2022 374, 2023 394, 2024 433, 2025 489, 2026 554.

## Timestamps
Each bar is the UTC 00:00 to 23:59:59 day, labelled by the UTC open date (`date`). This is not a US-session day. Spot dumps switched open_time from milliseconds to microseconds in 2025; the build detects it per row (value >= 1e14 means us). Header rows in some files are skipped.

## Known gaps and caveats
- Data starts 2017-08-17 (Binance launch); USDT pairs only began appearing in late 2017, so 2017 has 6 symbols.
- 24 symbols have internal gaps (3,605 missing days in total): exchange halts, maintenance, monitored/suspended pairs. Gaps are not filled.
- Renames/migrations appear as separate symbols: BCCUSDT (to 2018-11-20) -> BCHABCUSDT (2018-11-16 to 2019-11-28) -> BCHUSDT (from 2019-11-28; BCHUSDT ticker was reused for the new BCH). LUNAUSDT (2020-08) is the original Terra token and its series continues to 2026-09 across the 2022 collapse; the data includes the post-collapse relaunch (LUNA 2.0) under the same ticker, so there is a price break in May 2022. LUNCUSDT starts 2022-09. MATICUSDT ends 2024-09-10 -> POLUSDT starts 2024-09-13 (rename, flagged delisted for MATIC). Stitch these by hand if needed; the panel does not.
- "delisted" means no data after the cutoff; it includes ticker renames/swaps, not only removals. Pre-delisting prices are often distressed and Binance seldom reports delisting prices (the final bar is the last traded bar).
- Volume/quote_volume are Binance-only; trades is the trade count.
- Binance.com is not available to US residents; prices are a proxy for liquid-venue prices.

## Coinbase US column
`on_coinbase_us` = base currency has a USD-quoted product with status "online" on https://api.exchange.coinbase.com/products as of 2026-10-12 (403 bases). It is a current listing, NOT point-in-time: it ignores when a coin was listed or delisted on Coinbase. 237 of the 683 non-stable, non-leveraged symbols are flagged True. Matching is on base ticker, so reused tickers can be wrong.

## Sanity check
BTCUSDT close vs Yahoo BTC-USD close (2019-2026-09, 2,830 days): median absolute difference 0.07%, 95th percentile 0.74%, 91.5% of days within 0.5%. Spot checks: 2021-05-03 57,169 vs 57,200; 2025-01-10 94,726 vs 94,701. Larger deviations occur on volatile days (2019-06-03 +1.1%; 2020-03-12 4,800 vs 4,971), consistent with venue and cutoff-time differences.
