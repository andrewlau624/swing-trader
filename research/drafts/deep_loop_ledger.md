# Deep loop ledger (started 2026-10-12, prompt `prompt_deep_loop_2026-10-12.md`)

Program N at start: 934. Ceiling = events/yr x net edge x deployable share x capture (<= 50%), at $10k unless noted.

| iter | track | idea | class tags (mechanism / data / asset / horizon / counterparty) | ceiling @ $10k | status | evidence |
|---|---|---|---|---|---|---|
| 1 | C | Crypto access check + perp funding carry (long spot / short perp) | carry / Binance UM funding dumps / crypto BTC,ETH / multi-week / levered perp longs | ~+1-3pp long-run, ~0 in 2025-26 | CEILING-KILL (no N) | `crypto_access_2026-10-12.md`, `data/research/crypto_funding/` |
| 2 | B | LUCK-B1: 1000 random price/volume/fundamental cross-sectional rules, Sharadar 2006-15 discovery, permutation null | random grammar / Sharadar SEP+DAILY / US stocks / overnight-20d / unknown | n/a | LUCK: 0/1000 pass, null 0, placebo 0; best t 2.27, median t -5.9 (cost-dominated) | `luck_b1_out.txt` |
| 3 | A | Box-spread financing to replace 12.5% Schwab margin and reopen leverage (Goal L redo) | financing / Schwab margin docs + forums / options boxes / 1d-1y / the broker | 0 at $2-25k: Reg-T requirement ~= box width, so boxes swap buying power for cash; Portfolio Margin needs $125k | ACCESS-KILL (no N) | Bogleheads box thread; schwab.com portfolio-margin page; alphaarchitect short-box primer |
| 4 | C | Crypto mechanism ceiling table (CME basis, weekend, unlocks, listings, depegs, DAT discount) | various / literature + access / crypto / 1d-1y / various | all < +8pp; DAT discount ~+2.5-5pp | CEILING-KILL x7, DAT discount OPEN (data check) | `crypto_access_2026-10-12.md` |
| 5 | A | WIKI-ATTN: Wikipedia pageview spikes -> overnight retail-attention pressure | retail attention / Wikimedia pageviews + Wikidata / US stocks / overnight + 5d / retail open buyers | needs >= +15bp/night (night shape ~+4.7pp at 15bp; +8pp needs ~25bp) | RUNNING (N 936-937) | round1_prose WIKI-ATTN |
| 6 | C | DAT (crypto-treasury co.) discount to coin NAV: data check | discount reversion / CoinGecko treasury API + EDGAR / crypto-equity / months / issuers, activists | ~+2.5-5pp (iter 4) | DATA-LIMITED (free history 365d; EDGAR needs UA; anecdotes = persistent discounts) | `crypto_access_2026-10-12.md` |
| 7 | A | LEG-HEALTH: own trailing-63-session P&L kill switch on night + IBS legs | leg P&L persistence / internal replays / US stocks+ETFs / 63d / none (robustness) | robustness bar: <= 1pp cost, maxDD x0.75 | KILL: costs 2-14pp/yr, maxDD below placebo, no P&L persistence | `leg_health_out.txt` |
| 8 | C | Coinbase US500 / BTC perp funding as carry or cheap leverage | funding carry, financing / Coinbase public API / equity-index + crypto perps / hourly-1y / levered retail longs | unknown: funding swung -5%..+13%/yr across 2 snapshots | DATA-LIMITED (no public funding history; forward logger needs server OK) | `crypto_access_2026-10-12.md` |
| 9 | A | OVN-MOM: Lou-Polk-Skouras overnight momentum held overnight only, reopened because auction cost is now measured ~0bp | overnight clientele / Sharadar SEP 1998-2015 judge / US stocks / overnight / opening-cross buyers | needs >= +6.5bp/night net excess (250 x 6.5 x 100% x 50% = +8.1pp) | RUNNING (N 939) | round1_prose OVN-MOM |
| 10 | B | LUCK-B2: 600 random event x price-state rules (8-K codes, actions, dividend changes), 20/60d, discovery 2005-15, confirm 2016-20 | random grammar 2 / Sharadar EVENTS+ACTIONS / US stocks / 20-60d / unknown | n/a until survivors | RUNNING (N 940) | round1_prose LUCK-B2 |

## Crypto access (date-versioned, checked 2026-10-12)
- Schwab Crypto spot BTC/ETH (rollout from 2026-05-12, SOL/AVAX/LINK added ~2026-08): via Charles Schwab Premier Bank,
  ~75bp per trade (secondary sources), not in NY/LA. Not an IRA product as far as the sources say: assume NOT Roth.
- Coinbase Derivatives US perp-style futures (nano BTC 0.01, nano ETH 0.10; since 2025-07-21): hourly funding, 0% maker /
  0.03% taker promo (third-party), 60/40 tax. Needs a Coinbase account (not Schwab).
- Roth crypto exposure = spot ETFs (IBIT/ETHA etc.) during US hours only.

## Waiting on user
- OK to add a read-only hourly Coinbase perp funding logger (US5/BIP/ETP public GET) to the server's cron + REGISTRY? Builds the funding history no one publishes; decides iter 8.
- SEC_USER_AGENT in .env (your name + contact) would unblock EDGAR pulls (DAT holdings rebuild, forced-flow scanner). Low priority: nothing currently gated on it clears +8pp.

## Checkpoint 1 (after iter 8, 2026-10-12)
- Tried: crypto access + 9 crypto mechanisms (ceiling/access/data kills), box financing (access kill), LEG-HEALTH (KILL, N 938).
- Running: LUCK-B1 (random batch, N 935), WIKI-ATTN (pageview attention, N 936-937).
- Survivors: none. Best addition vs index at $2.3k / $10k / $25k: unchanged (book ~10-12%/yr; index 8-10%).
- Read: crypto for a US retail account is cost/access-bound (Schwab 75bp, no alt shorts); the only open crypto items need data
  (DAT holdings via EDGAR, perp funding history via a forward logger). Track C should now move to data acquisition, not more ideas.
