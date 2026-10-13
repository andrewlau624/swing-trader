# Deep loop ledger (started 2026-10-12, prompt `prompt_deep_loop_2026-10-12.md`)

Program N at start: 934. Ceiling = events/yr x net edge x deployable share x capture (<= 50%), at $10k unless noted.

| iter | track | idea | class tags (mechanism / data / asset / horizon / counterparty) | ceiling @ $10k | status | evidence |
|---|---|---|---|---|---|---|
| 1 | C | Crypto access check + perp funding carry (long spot / short perp) | carry / Binance UM funding dumps / crypto BTC,ETH / multi-week / levered perp longs | ~+1-3pp long-run, ~0 in 2025-26 | CEILING-KILL (no N) | `crypto_access_2026-10-12.md`, `data/research/crypto_funding/` |
| 2 | B | LUCK-B1: 1000 random price/volume/fundamental cross-sectional rules, Sharadar 2006-15 discovery, permutation null | random grammar / Sharadar SEP+DAILY / US stocks / overnight-20d / unknown | n/a | LUCK: 0/1000 pass, null 0, placebo 0; best t 2.27, median t -5.9 (cost-dominated) | `luck_b1_out.txt` |
| 3 | A | Box-spread financing to replace 12.5% Schwab margin and reopen leverage (Goal L redo) | financing / Schwab margin docs + forums / options boxes / 1d-1y / the broker | 0 at $2-25k: Reg-T requirement ~= box width, so boxes swap buying power for cash; Portfolio Margin needs $125k | ACCESS-KILL (no N) | Bogleheads box thread; schwab.com portfolio-margin page; alphaarchitect short-box primer |
| 4 | C | Crypto mechanism ceiling table (CME basis, weekend, unlocks, listings, depegs, DAT discount) | various / literature + access / crypto / 1d-1y / various | all < +8pp; DAT discount ~+2.5-5pp | CEILING-KILL x7, DAT discount OPEN (data check) | `crypto_access_2026-10-12.md` |
| 5 | A | WIKI-ATTN: Wikipedia pageview spikes -> overnight retail-attention pressure | retail attention / Wikimedia pageviews + Wikidata / US stocks / overnight + 5d / retail open buyers | needs >= +15bp/night | KILL: gross -1.0bp/night (t -0.28), net -16; 5d drift -2.2 gross | `wiki_attn_out.txt` |
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

| 16 | A | CRSP-EARLY: live night leg + OVN-MOM on untouched 1992-97 (first WRDS study) | liquidity-provision bounce / overnight clientele / CRSP via WRDS / US stocks pre-decimal / overnight / small-cap sellers, retail open buyers | robustness (no %): confirms or breaks the live leg + the only lead | N1 NOT CONFIRMED (bid-ask bounce: mid gross t 1.33); N2 MECHANISM CONFIRMED (+16bp t 8, mid-robust, stale-score persistent), net economics not judgeable pre-decimal | `crsp_early_out.txt`, `crsp_early_adv_out.txt` |
| 17 | B | LUCK-B4: 1000 random long-only rules on OptionMetrics IV/skew/PC volume + Compustat short interest (grammar 4) | random / OptionMetrics + Compustat SI via WRDS / US stocks / overnight-5d-21d / none named | gate inside the batch: >= 16%/yr at 100% | LUCK: 0 passes, null 0/10, placebo 0; best = high-IV overnight premium (known) | `luck_b4_out.txt` |
| 18 | A | LATE-FLOW: late-day (15:00-15:45) Lee-Ready signed trade flow -> overnight, top-1000 stocks, judge 2010-15 | order-flow liquidity premium / WRDS TAQ ms / US stocks / overnight / late-day liquidity demanders | needs >= +6.5bp/night net | RUNNING (TAQ aggregation ~6.9h; 166-day preview -2.1bp t -2.3 read by the runner agent before completion, disclosed) | `late_flow_out.txt` (pending) |
| 19 | B | LUCK-B5: 1000 random long-only rules on IBES consensus/dispersion/revision/LTG features (grammar 5) | random / IBES statsumu via WRDS / US stocks / overnight-5d-21d / none named | gate inside the batch: >= 16%/yr at 100% | LUCK: 0 passes, null 0/10, placebo 0; best t 2.00 (revision x dispersion, reversal x EY: known families) | `luck_b5_out.txt` |
| 20 | A | WRDS ceiling sweep 2: daily bond->equity lead (TRACE), mutual-fund fire-sale pressure (CRSP MF holdings), closing-volume-share overnight reversal (TAQ), SPY signed dealer gamma as a leg gate (OptionMetrics) | informed bond trading / redemption-forced funds / closing-cross pressure / dealer hedging; TRACE, CRSP MF, TAQ, OptionMetrics; US stocks + SPY; daily-quarterly | BOND-LEAD clears on paper (night shape, needs >= +6.5bp/night) but prior low (Hotchkiss-Ronen: no lead post-dissemination); MF fire-sale ~2-4pp (quarterly lag, Wardlaw mechanical critique); close-volume reversal = LATE-FLOW's family; GEX gate needs a second look at touched IBS windows | BOND-LEAD = next Track A candidate; MF fire-sale CEILING-KILL; close-volume DEFERRED to LATE-FLOW verdict (dies with it); GEX gate KILL (touched windows) | this row |
| 21 | A | BOND-LEAD: issuer's top-decile TRACE bond return on d -> stock close d -> close d+1, judge 2006-15 | cross-market information / TRACE enhanced / US stocks with bonds / 1d / informed bond traders | needs >= +6.5bp/day | KILL: gross -0.5bp/day, net -4.5 t -3.95, within-tercile +0.03 t 0.03, every year but 2009 negative | `bond_lead_out.txt` |
| 22 | B | LUCK-B6: 800 random long-only rules on all US ETFs/ETNs (CRSP shrcd 73, delisted incl.) with flow / premium-to-NAV / age / size features (grammar 6) | random / CRSP + CRSP MF NAV / ETFs / overnight-5d-21d / none named | gate inside the batch: >= 16%/yr at 100% | LUCK: 0 passes, null 0/10, placebo 0; best t 2.06 (premium x reversal, outlier-carried) | `luck_b6_out.txt` |
| 23 | A | Ceiling notes: (a) TAQ auction-cost history for OVN-MOM names 2010-15; (b) earnings-announcement premium (IBES anndats, buy ~5d before, hold through) | (a) execution cost / TAQ / US stocks / overnight / none; (b) attention-risk premium / IBES actuals / US stocks / ~1wk / pre-announcement sellers | (a) no %: OVN-MOM was already scored at official crosses 2021-26 (+7.2bp gross) and MOC/MOO fills at the cross, so a spread history cannot move the +4..+9pp range, only forward capture can; (b) literature ~5-7%/yr L/S at 100%, long-only half capture ~+3pp | (a) DROPPED (uninformative), (b) CEILING-KILL; no N | this row |
| 24 | A | MODERN-XS (user request): monthly top-decile stock sorts on 14 untested traits (value, quality, size, investment, issuance, leverage, turnover, $vol trend), discover 2021-23, judge 2024-26 | characteristic premia / Sharadar SEP+DAILY+SF1 / US stocks / 1 month / none named | needs >= +16%/yr vs QQQ at 100% | KILL: kept sales-yield+ and low-issuance (disc t 2.2/2.1); judge -13%/yr vs QQQ, vs EW t -0.4/-0.6; 1998-2015 same sign, noise-sized | `modern_xs_out.txt` |
## Crypto access (date-versioned, checked 2026-10-12)
- Schwab Crypto spot BTC/ETH (rollout from 2026-05-12, SOL/AVAX/LINK added ~2026-08): via Charles Schwab Premier Bank,
  ~75bp per trade (secondary sources), not in NY/LA. Not an IRA product as far as the sources say: assume NOT Roth.
- Coinbase Derivatives US perp-style futures (nano BTC 0.01, nano ETH 0.10; since 2025-07-21): hourly funding, 0% maker /
  0.03% taker promo (third-party), 60/40 tax. Needs a Coinbase account (not Schwab).
- Roth crypto exposure = spot ETFs (IBIT/ETHA etc.) during US hours only.

## Waiting on user
- (2026-10-13) Items 1+2 DEPLOYED by the user; WRDS login done. SEC_USER_AGENT set local+server 2026-10-13 (EDGAR 200). Nothing waiting on the user.
- **2026-10-12 evening: user said YES to items 1+2.** The push/pull + unit re-render on him was blocked by the auto-mode
  classifier (persistence on the server); user is away and will grant later. To run by hand: `git push origin main`, then on him
  `git pull --ff-only` and re-render research-shadows.service from `deploy/research-shadows.service.in` (sed __APP_DIR__), daemon-reload.
  The 33 pushed commits touch only research/, NEXT/CLAUDE.md, ovn_mom_shadow.py + test, testing.py REGISTRY, Makefile, the unit file.
  Funding logger (item 2) BUILT + committed (6c45622: `cb_funding_log.py`, cb-funding hourly timer, install-schedule lines,
  REGISTRY CB-FUNDING, 2 tests); live dry run parsed 29 CDE perps. Same deploy step, plus `scripts/sysd.sh enable --now cb-funding.timer`.
- **WRDS (Wharton) access: user has it (2026-10-12).** Not usable yet: no `wrds` package, no ~/.pgpass. Needs the user to log in once
  (Duo MFA) and say which libraries the subscription covers. Triage below.
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

## Checkpoint 3 (after iter 15, 2026-10-12 ~15:30)
- Since checkpoint 2: WIKI-ATTN KILL (no raw overnight attention effect); LUCK-B3 LUCK; alt-event and Track A sweeps ceiling-killed.
- Totals for the session: 15 iterations, N 934 -> 941. Tests run: LUCK-B1/B2/B3 (luck x3), WIKI-ATTN (kill), LEG-HEALTH (kill),
  OVN-MOM (historical PASS, small now). Ceiling/access/data kills: ~20 ideas. New infrastructure: Binance delisted-complete alt
  panel, Wikipedia pageview cache, Coinbase perp access notes, OVN-MOM forward shadow (not deployed).
- Best addition vs index at $2.3k / $10k / $25k: none confirmed. Candidate: OVN-MOM, ~+4pp at 2bp/side, ~+9pp if ~0bp auction
  cost holds on its names (half capture); $100k fine (median pick closing print $5.5M).
- The loop is now gated on user decisions and forward data, not ideas. Until one of the "Waiting on user" items moves, ticks only
  read forward shadows (daily) and take a new idea only if it brings a new data family and clears the ceiling first.

## WRDS triage (2026-10-12, before any data is read; no N)
Which mechanisms move from DATA-LIMITED to testable, ranked by gate odds at $10k:
1. **Borrow fees / utilization (Markit Securities Finance, if subscribed).** The one named counterparty (short sellers) with no data
   so far. Only shapes that can clear +8pp: a daily-frequency long leg that is paid by constrained shorts (e.g. recall/fee-spike
   squeeze as an event leg). Selection-conditioning the night leg on fees is a CLOSED class (FUND-STATE): do not run it.
2. **CRSP 1926-1997 = untouched windows** for rules already validated (OVN-MOM 1992-97 once opens exist; PREF-EX/ETDX pre-1998 if
   preferreds are in CRSP). Robustness, not new %: confirmation only, one look each.
3. **OptionMetrics -> signed dealer gamma.** Prior lowered (OI-pin killed, VTS/COTX/CBAS killed); index-level daily state ~<4pp ceiling.
   Test only if a single-stock gamma-flip event shape clears the gate on paper first.
4. **Mergent FISD / ratings -> fallen angels.** Equity move likely in the announcement gap; bonds not retail-executable. Low.
5. **TAQ (millisecond).** Closing/opening imbalance history: closing imbalance already dead (paid data, 2026-10); exact 15:40 night
   rule is moot (NX done on daily). Low, unless used to price auction cost for OVN-MOM's names historically (that one IS useful:
   it decides whether OVN-MOM is +4pp or +9pp at $10k).
Next step once access works: list subscribed libraries (`db.list_libraries()`), then run #5-for-OVN-MOM cost or #1, whichever exists.

## WRDS access verified (2026-10-13)
Connected (pgpass). Subscribed and useful: CRSP daily (delisted, OPENPRC from 1992), Compustat (incl. sec_shortint 1973+),
OptionMetrics opprcd 1996-2025, TAQ millisecond taqm_2003..2026 (+ ISSM 1983-92), TRACE + FISD, IBES, TR 13F/insiders,
CBOE, Datastream futures/equities. **NOT subscribed: Markit/IHS securities lending -> borrow fees stay DATA-LIMITED.**
Re-rank of the triage: TAQ auction cost for OVN-MOM is low value (live fills already print at the official cross, ~0bp; the
open question is forward return, not cost). First WRDS study = CRSP-EARLY (N 942-943): night leg + OVN-MOM on untouched 1992-97.
Deploys done by user 2026-10-12 night: OVN-MOM shadow in research-shadows (first run 10-13 08:20 ET), cb-funding hourly timer.

## Checkpoint 4 (after iter 20, 2026-10-13 ~03:00 ET)
- Since checkpoint 3: CRSP-EARLY (night leg NOT confirmed on 1992-97: bid-ask bounce; OVN-MOM mechanism CONFIRMED, net untestable
  pre-decimal), LUCK-B4 (options/SI: luck), LUCK-B5 (IBES: luck), WRDS ceiling sweep 2 (row 20). LATE-FLOW (TAQ, row 18) still
  aggregating (~6.9h; 2010 preview -2.1bp/night, far below the +6.5bp gate, not a verdict).
- Totals: 20 iterations, N 934 -> 947. Luck track 0 signal in 5 batches across 5 data families (price, events, crypto alts, options/SI,
  analysts): the random-rule search keeps reproducing known families (reversal, high-vol overnight premium, value) and nothing else.
- Best addition vs index at $2.3k / $10k / $25k: still none confirmed. OVN-MOM (forward shadow live since 10-13) is the only
  candidate; ~+4pp at 2bp/side, ~+9pp if ~0bp auction cost holds (half capture); $100k fine.
- **Pivot (last ~10 iterations nothing above the gate):** Track C is PAUSED. Every crypto mechanism reachable from this user's
  access is dead or ceiling-killed (funding carry, CME basis, unlocks, listings, depegs, cascades, trend, IBS, alt luck); DAT discount
  is DATA-LIMITED; the only open item is the Coinbase CDE funding log (90 days -> 2027-01-11). Its 30% goes to Track A on the
  WRDS-unlocked data families (TAQ, TRACE, FISD, CRSP MF, OptionMetrics). Track B: next grammar must leave stock cross-sections
  (5 batches there were all luck): e.g. bond/fund panels, or stop B until a new asset panel exists.
- Waiting on user: nothing. Forward shadows: OVN-MOM (first 08:20 ET 10-13), CB-FUNDING (hourly), PREF-EX, CEF-RV, LETF-NIGHT, ARETE-DIP.
