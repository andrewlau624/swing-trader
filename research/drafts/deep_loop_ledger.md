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
| 9 | A | OVN-MOM: Lou-Polk-Skouras overnight momentum held overnight only, reopened because auction cost is now measured ~0bp | overnight clientele / Sharadar SEP 1998-2015 judge / US stocks / overnight / opening-cross buyers | judge +15.4bp/night (2bp/side); now +3.2bp net official prints -> ~+4pp ($10k), ~+9pp if ~0bp cost holds | PASS (historical) / SMALL now -> forward shadow | `ovn_mom_out.txt`, `ovn_mom_adv_out.txt` |
| 10 | B | LUCK-B2: 600 random event x price-state rules (8-K codes, actions, dividend changes), 20/60d, discovery 2005-15, confirm 2016-20 | random grammar 2 / Sharadar EVENTS+ACTIONS / US stocks / 20-60d / unknown | n/a | LUCK: 5 real passes (2 distinct) vs date placebo 34 -> firm-type (issuer dilution drag, short-only), not event timing | `luck_b2_out.txt` |
| 11 | C | Delisted-complete Binance spot daily panel (all USDT pairs 2017+) + Coinbase-US tradable flag | infrastructure / Binance bulk dumps / crypto alts / daily / n/a | n/a (data) | DONE: 756 USDT pairs 2017-08..2026-09, 249 delisted (190 in the clean 683), BTC vs Yahoo median 0.07%; on_coinbase_us not PIT | `data/research/crypto_spot/`, `research/sim/crypto_spot_build/` |
| 12 | A | Earnings-announcement DELAY short (8-K 2.02 later than last year's same quarter; Johnson-So) | disclosure timing / Sharadar EVENTS 2.02 / US $5+ stocks / ~2wk / bad-news delayers | ~1,000 delays/yr x ~1% net x ~1% of account each x 50% ~= +5pp, short-only (taxable), small-cap borrow; FN-LAG sibling: $5+ late filers negative (consistent) but the class is short-side | CEILING-KILL (no N) | this row; NEXT FN-LAG |
| 13 | B | LUCK-B3: 800 random long-only rules on crypto alts (delisted-complete Binance), 7/30d, discovery 2019-22, confirm 2023-26 | random grammar 3 / Binance spot panel / crypto alts / 7-30d / unknown | n/a | LUCK: 0/800, nulls 0, placebo 0, best t 1.69 | `luck_b3_out.txt` |
| 14 | A | Ceiling sweep of remaining event/flow ideas: Nasdaq-100 Dec recon adds, IPO quiet-period expiry (Bradley-Jordan-Ritter), lockup-expiry SHORT, covered-call ETF (QYLD/JEPQ) roll flow, index close->open sleeve for idle cash | index/event/dealer flows / various free / US stocks+ETFs / 1-10d / index funds, analysts, insiders, dealers | NDX recon ~10 events/yr, effect in announcement gap (S&P lesson) ~0; IPO quiet period ~200 x 1.5% x 10% x 50% ~= +1.5pp; lockup short ~150 x 1% x 30% x 50% ~= +2pp, HTB borrow; CC-ETF roll = gamma/OI class (OI-pin dead, signed gamma DATA-TARGET); index overnight sleeve = add. 16 dead (one half only) | CEILING-KILL x5 (no N) | NEXT add. 16, event_edge_candidates #26 |
| 15 | C | Alt-panel event ideas: Binance delisting -> rebound on Coinbase after the last Binance day; Binance new-listing first-30-day long; LULD-halt reopen (equity cross-check) | forced exchange exit / Binance panel last_date / crypto alts / 7-30d / Binance holders forced to withdraw | delisting rebound: ~5-8 Coinbase-listed Binance delistings/yr x ~8% x 30% x 50% ~= +0.8pp; new-listing long = known negative post-listing drift; halts = Lab-AY/BA dead family | CEILING-KILL / DEAD (no N) | NEXT Lab-AY/BA |

## Crypto access (date-versioned, checked 2026-10-12)
- Schwab Crypto spot BTC/ETH (rollout from 2026-05-12, SOL/AVAX/LINK added ~2026-08): via Charles Schwab Premier Bank,
  ~75bp per trade (secondary sources), not in NY/LA. Not an IRA product as far as the sources say: assume NOT Roth.
- Coinbase Derivatives US perp-style futures (nano BTC 0.01, nano ETH 0.10; since 2025-07-21): hourly funding, 0% maker /
  0.03% taker promo (third-party), 60/40 tax. Needs a Coinbase account (not Schwab).
- Roth crypto exposure = spot ETFs (IBIT/ETHA etc.) during US hours only.

## Waiting on user
- Deploy the OVN-MOM-FWD shadow (log-only, committed locally: `swingtrader/daily/ovn_mom_shadow.py`, research-shadows unit line) to him? Untested against live sip_daily/crosses; first run pulls ~400 days of daily bars for the night universe.
- OK to add a read-only hourly Coinbase perp funding logger (US5/BIP/ETP public GET) to the server's cron + REGISTRY? Builds the funding history no one publishes; decides iter 8.
- SEC_USER_AGENT in .env (your name + contact) would unblock EDGAR pulls (DAT holdings rebuild, forced-flow scanner). Low priority: nothing currently gated on it clears +8pp.

## Checkpoint 1 (after iter 8, 2026-10-12)
- Tried: crypto access + 9 crypto mechanisms (ceiling/access/data kills), box financing (access kill), LEG-HEALTH (KILL, N 938).
- Running: LUCK-B1 (random batch, N 935), WIKI-ATTN (pageview attention, N 936-937).
- Survivors: none. Best addition vs index at $2.3k / $10k / $25k: unchanged (book ~10-12%/yr; index 8-10%).
- Read: crypto for a US retail account is cost/access-bound (Schwab 75bp, no alt shorts); the only open crypto items need data
  (DAT holdings via EDGAR, perp funding history via a forward logger). Track C should now move to data acquisition, not more ideas.

## Checkpoint 2 (after iter 14, 2026-10-12)
- New this block: LUCK-B1/B2/B3 all LUCK (stocks price grammar, 8-K/actions grammar, crypto alts; nulls and placebos never beaten
  except B2's permutation null, which its date placebo overturned). OVN-MOM: registered PASS on 1998-2015, adversarially confirmed
  as an overnight clientele effect (not bounce), but decayed to ~+3bp net now -> forward shadow built (not deployed). LEG-HEALTH
  KILL. Earnings-delay short, 5 event/flow ideas, crypto alt delisting ideas: ceiling-killed. Crypto alt panel (delisted-complete)
  built for future use.
- Survivors: OVN-MOM (forward only). Best addition vs index at $2.3k / $10k / $25k: unchanged until OVN-MOM-FWD reads; if the
  measured ~0bp auction cost holds, ~+9pp at $10k (half capture), ~+4pp at 2bp/side; $100k: picks' median closing print is
  $5.5M, so capacity is fine to ~$1M.
- Structural read: the +8pp gate admits only (a) every-night shapes with >= 15bp, (b) monthly >= 2% on most capital, (c) rare
  capped contract payoffs. Event strategies at 50-1000 events/yr die on deployable share; random search dies on cost + nulls.
  The free-data frontier is close to empty; the remaining value is forward evidence (OVN-MOM, PREF-EX, CEF-RV shadows) and the
  user decisions below.
- Pivot for the next block: Track B paused (3 grammars, 3 LUCKs; reopen only with a new data family). Track A/C only on new
  data sources (Wikipedia result pending) or forward-evidence reads; ceiling first, test only what clears.

## Forward-evidence read (2026-10-12 ~14:45, him read-only)
PREF-EX 1/60 forward nights (2 events, CO -84bp: noise at n 1); CEF-RV 0 closed forward (backfill 5 closed +295bp vs EW CEF);
LETF-NIGHT 3/120 days (-80.6bp/day, t -0.75); GAMMA-FREE 0/120; Ex-date open n 1 forward; PREF-EX / CEF-RV live Roth tests 0/30.
Nothing decidable yet; earliest reads in weeks (PREF-EX ex-nights cluster mid/late month).
