# Hypothesis space (built 2026-10-25, Tier A measured same day: N 1061-1064 all KILL; from NEXT.md do-not-redo, docs/memory, round1_prose, branch_loop)

Purpose: the next study must come from a cell that is `untested`, not from a killed cell under a new indicator name or
parameter set. Program N = 1060 (2026-10-19). Sources: `NEXT.md` "Things already tested" table (lines 1220-1521) and
the dated session sections above it; `docs/memory/06..54`; `research/drafts/round1_prose.md` RESULT sections 7700-8973
and the open-loop close-out at 8974; `research/drafts/branch_loop_2026-10-19.md`.

Standing constraints encoded here (all user rulings):
- **Schwab only, US-listed only** (2026-10-18): IBKR, TSX/JSE/SE prefs, Coinbase perps, international lines are ACCESS-KILLED.
- **Odd-lot tenders ABANDONED** (2026-10-24; `docs/memory/54`): never listed as open. CPC class keeps split-offs and
  reverse-split round-ups only; **no new CPC families** (CLAUDE.md, CPC 2026-10-04).
- **No options strategies** (premium buying/selling closed, part 4-5); options reopen only for options-INDUCED underlying flows.
- **LLM/NLP/text signals CLOSED by the user** (2026-10-19). Reddit/forum pattern ideas closed (GOLD-IFVG, CHART-YOLO).
- **Ceiling gate before any backtest**: `%/yr = events/yr x net edge x share of account deployable x honest capture (<= 50%)`;
  kill if < +8pp/yr at $10k. A cell whose paper ceiling is below the gate is **ceiling-killed, not untested**.
- Status words: `killed` (judged, cite id/date/why) | `passed/live` | `ceiling-killed (number)` | `blocked (what data)` |
  `access-killed (why)` | `untested`. "Both halves 2021-26" is within-regime; Sharadar 1998-2026 is TOUCHED for the
  night/IBS/ex-date/CEF rules; CRSP 1992-97 touched for night + OVN-MOM; 2003-15 touched for night (NX) and IBS (SHAR-IBS).

## Matrix

Columns = mechanism. Rows = instrument family. Cell text: status (study id, date, one-clause why). Where a row/column
pair has several studies, the class verdict is given first.

| family \ mechanism | liquidity provision / reversal | continuation / momentum | forced flow (named counterparty) | information asymmetry | calendar-structural | cost / carry capture | conditioning / regime gate |
|---|---|---|---|---|---|---|---|
| **US single stocks, daily, auction-executed** | **passed/live**: night leg (-8% & IBS<0.10 at 15:40, close cross -> open cross), NX PASS 2003-15 +3.1bp/night t 3.1 (2026-10-06), delisted-complete 2021-26 +14.8bp tier (SHAR-SURV); profile nx_s2 live. killed: 2/3/5-day losers, multi-day holds M2-M5, NIGHT-BAND -4..-8% (N 1040, +4bp gross = inside cost; forward shadow), every exit later than the open (NEXIT N 901-907, OPENSIG N 907-911, 9:35/10:00/10:30), NIGHT-TAU (N 1037, timing closed), confirmed-bounce tree (HL-BOUNCE/BNC-IBS/DEEP-PULL/BRK-RETEST N 1055-58, all <= 0 both periods), swing-book z-score reversal + 40 indicators + C1-C8/W1-W6/U2-U11 (LUCK), PANIC-IDX (N 1018), CLOSE-DISLOC LOC fills, Radge limit entries (fill artifact), 1-month reversal Lab-BQ, long-term reversal Lab-BV. **untested: open-to-open IBS<0.2 on liquid stocks without the -8% drop (U3); the short mirror (U2)** | killed as a class: 12-1 momentum top-20 (Lab-BR, dead by t), MODERN-XS (N 977: QQQ is the modern winner trait), 52w-high / low-vol / theme-explosion / residual momentum / breakouts, OVN-MOM (N 939: PASS 1998-2015, ~+3bp net 2016-26, forward shadow only), GAP-NIGHT (N 1050: PASS-SMALL 2016-21, +5.4bp t 1.6 since 2022, shadow), CUST-MOM (N 1005), announcement-gap drift Lab-BH/BI, PEAD (in the gap), industry lead-lag at minutes (SECT-LAG). Daily-horizon industry lead-lag untested but ceiling-killed (~1.5pp, long-only half of a decayed 1%/mo LS). | killed: Reg SHO threshold buy-in (THR, long side -959bp), SSR-LIFT (N 860: mechanism CONFIRMED, short-only ~4-5%/yr honest, forward shadow, below gate), SSR-NIGHT/SSR-TD, 13F trim/freed (F13C N 854-857), fund fire sales (F-SALE N 1054 proxy; F-SALE2 N 1060: -273bp in the event quarter, +15bp next: information, not snap-back), LETF single-stock rebalance (SS-LETF N 877: mechanism real, trade dead), LATE-FLOW (N 945, +0.9bp gross), DRIP-PAY (N 927-930 wrong sign), buyback/ATM/follow-on/convert hedges (G8/G13/G31/J5), merger-arb break (BREAK-REV/REV2), index flows (see index row). **untested: dividend/proxy record-date lending recalls in HTB names (U1); Coval-Stafford 2-4q holds (U5, below gate); inflow-bought short side (ceiling-killed ~0.8pp)**. blocked: margin-call cascades (no data; MFLW aggregate killed), daily ETF creation pressure on constituents (no daily shares outstanding). | **shadow**: insider Form 4 ID3/EV2 (H-POOL PASS-not-robust 2008-15, tier +21bp t 2.7, decays to ~0 by 2013-15). killed: ID1/ID2/EV1/G12/G36/G42-43/L19 (judge half), 13D originals (A1), 10%-owner (A2), 10b5-1 (I33), Form 144/NT 10-K (L17), BORROW-XS/XS2 (N 1006-7: real LS signal, payoff is the unshortable side; long-only = size/vol beta), LUCK-B4 (option state), LUCK-B5 (IBES), UPG-DAY0/POCKET (N 985/987), BOND-LEAD (N 948), WIKI-ATTN (N 936-7), REV-TONE (N 1008), LLM-EARN/NEWS-DRIFT (N 885-7), FN-LAG (sub-$2 artifact). Congress PTR copying: R8 "no data" then; data exists free now but the 45-day lag puts the effect in the gap -> ceiling-killed (< 2pp). ARK-class daily-disclosed active-ETF trades: untested, ceiling ~2-5pp and decaying (U7). | killed: TL-JAN (N 853-4, 28 yrs delisted-complete), DM dividend-month (N 835-6, size tilt), Lab-BJ month seasonality, day-of-week/TOM/Friday/pre-holiday(watch)/witching, DS5 quarter-end, OPEX calendar sizing, FOMC/CPI/NFP night sizing (F3 QQQ eve adopted small), EXDIV-OPEN common ex-nights (vendor open = cross; "+9bp" was the normal overnight premium), THN thin commons ~0 since 2021, SPECIAL-EX (N 1052: drop 0.95; the "PASS" was a vendor-date artifact), earnings night DS1. untested: due-bill (>= 25%) specials as a trade (count/bound killed in Goal hunt; ~10-20/yr, ceiling < 1pp). | adopted: BIL/SGOV idle cash. killed: PCP-HTB conversion carry (N 1019, far-side -78%/yr), box-spread financing (access: PM needs $125k), wash-sale day-31 rebuy, tax-loss harvest timing. **untested: Schwab fully-paid lending income on HTB holdings (U4) -- paper ceiling <= 0 on BORROW-XS numbers unless utilization ~100% and rebate share > ~80%; one free account test decides.** | class closed: TREND-NIGHT (N 916-9 wrong sign), REGIME-10M (N 919-22, 1999-2015), BREADTH-GATE (N 1041), NDISC vol/VIX buckets, PROVOL size-up (ceiling 1.2pp), LEG-HEALTH own-P&L switch (N 938), CROWD-NIGHT (N 1043), VENM venue-mix (N 867, beaten by its placebo), FUND-STATE pe sign (N 901 wrong sign), THEME-NIGHT/CAT-MOM/HC-BAN/sector (N 1034), PATTERN-NIGHT snapshots (N 1036), SEQ-NIGHT sequences (N 1038), MINPATH minute path (N 1042), QI-HIST (N 898), SSR flag, listing age, LETF picks (W/PQ1), 8-K bad news, earnings/8-K/dow/index-IBS/short-interest conditioners (idea scan 2026-10-08: every conditioner acts on a ~4%/yr leg, ceiling < 1pp). Not run and ceiling-killed: breadth as a sizing dial, option-implied borrow fee as a night filter (same short-constraint class), S&P membership / dividend-payer / ma200 state (< 0.5pp each). |
| **US single stocks, intraday / minute (tape)** | killed as a class (scalp loop checkpoint 2, 2026-10-13): LEVEL-BOUNCE (N 984), STOP-RUN (N 983), SCALP-CLF/OFI (N 980/982, path features forecast vol not direction), VOLDAY x5 (N 989-93), INPLAY x3 (N 994-6), Lab-AS/AU/AW, HF QQQ scalping, noise-leg variants (DS2/DS3, 15-min decisions, hold-to-close add. 22). Intraday noise leg OFF (2026-10-11, re-arm only on a positive 60-session replay). | killed: ISO-BURST (N 979), RETAIL-HERD (N 981), SECT-LAG (N 978), last-half-hour momentum (Gao), +25% movers 15:00->15:55 (Lab-AX), first-hour continuation ~0 (NOISE-DIAG), INTRA-ANY learned any-time triggers (N 1044-5, corr(pred,y) ~0.02), PREMKT-CROSS (N 1047-8). Not tested after INTRA-ANY: non-tape inputs (imbalance feeds, L2), < $200M ADV, passive limit entries -- all same class, ceiling-killed by the zero-gross-drift finding. | killed: closing-auction imbalance (Round 13 AC / 26 BD, Lab-AZ/BB/BC/BG: real, spread-bound), opening-cross imbalance (Lab-BE/BF, Round 27 BE), CLOSE-IMB-FREE (lookahead by construction), GAP-SHORT (N 878), SQZ/GUF-LOW (N 881-2), LETF-flow last half hour, 15:50 MOC decision for IBS. blocked: intraday iNAV. | killed: NEWS-DRIFT Benzinga (N 885), EDGAR acceptance-time buys (G12), LLM intraday (closed by user). | killed: SOQ third-Friday open dislocation (ceiling-killed 2.4pp, prose 8974+), pre-FOMC day session (add. 33), OPEX-day noise. | killed: resting dip bids / passive fills in thin names (PREF-DIP N 880, ETF-THIN N 884, U1/S7 fill artifacts, PXB: positive only as an add-on tranche). The "limit at the bid instead of MOO" bound (NEXT Ideas-not-yet-tested) is +2pp for the quarantined swing book: obsolete. | killed: NOISE-GATE vol gate (N 934: 2026 losses are high-vol days that do not trend), cross-leg regime tilt, time-of-day gates; class closed 2026-10-11. |
| **Broad / sector / factor equity ETFs** | **passed/live**: IBS leg (18 ETFs, top-3 12-1 momentum, IBS<0.2, open d+1 -> open d+2), OOS 2016-20 +29.8bp (ibs_oos), SHAR-IBS 2003-15 WEAK (net +5bp t 1.0, cost-bound). killed: BNC-IBS confirmation (N 1056), AV hold-until-IBS>0.5, AT1-3 vol/trend gates, VT-IBS vol weights (N 836-8), rule-based IBS universe (all liquid ETFs, dead), multi-day oversold index (V6 shadow, dead), sector-loser reversal, ETF pairs / clones (Round 30 #1-2), IBS>0.8 control (~0bp). untested: nothing at the daily tier that is not a universe variant; crypto ETFs see the crypto row (U6). | killed: sector/industry-ETF momentum (Lab-BS/BX, trend loop idea 4), cross-asset TSMOM (11 ETFs), category momentum, ETF-CLF minute classifier (N 986), new-ETF basket. Lab-BW/BY/BZ PASS on French 1963-2015 but recent era poor (shadow only). | class closed: ETF premium/discount + creation flow (ETC SPY, EF broad SPDRs, BSPD bond SPDRs N 835, ETF-PD N 1059 delisted-complete 2,737 ETFs: deepest-discount decile +0.9bp gross, NAV moves to price = information). LUCK-B6 (N 949) null on flow/premium/age/size. Not tested after ETF-PD: premium SHORT side (symmetric by the same mechanism decomposition -> ceiling-killed), creation-flow conditioning (blocked: no daily shares outstanding), FX-hedged intl funds (same stale-NAV structure). Thematic/equal-weight reconstitution flows in thin constituents: RSP/SCHD killed (count/bound); ceiling < 1pp. | killed: LUCK-B6; ARK-class disclosed trades untested (see single-stock info cell, U7). | killed: month-end 60/40 (RB6040 artifact), window dressing, pension rebalance (watch, dead), Lab-BJ, TOM; FXD fund ex-nights (< 10bp since 2020); high-yield-ETF ex-night +17.5bp drop 0.86 (support only, FXD KILL as capacity). | killed: SVXY contango (Lab-BN), put-write overlays (Round 13 Z), Lab-BK short both legs of 3x pairs. | killed: Moreira-Muir vol-managed (Lab-CD), Faber 10m on the book (REGIME-10M), VIX regime gates, VTS term structure (N 864: contango = drift, inversion wrong sign; long mirror ceiling-killed ~4pp 2026-10-10), Cboe SKEW (Lab-CC PASS predictive, declined as sizing), equity put/call (Lab-CB), PLUM repo stress (N 865), MFLW margin debt (N 866). |
| **Leveraged / inverse ETFs** | IBS on LETFs = leverage only (xasset scan: SOXL/TQQQ/UPRO premium 3x base). CLE 1.25x cap / ACC structure accepted (not alpha). killed: Round 30 #3 LETF-vs-underlying close (lookahead), Study W LETF night picks, PQ1. | killed: TQQQ conviction trade (Round 16 AF-AK, shadow), Lab-CA 3x with 200d exit (risk bars), CRASH-A/D inverse sleeves (N 1024/1028: negative-EV insurance). | killed: LETF rebalance flow (last half hour, night size-up after big down days), SS-LETF (N 877), LETF-NIGHT forward registration (N 851, log-only; no PASS). | -- (no information mechanism specific to the wrapper) | -- | killed: Lab-BK (short both legs, decay capture), Roth 3x "up to 3.0x" borderline (structure). | killed: PROVOL, vol-targeted overnight gross. |
| **International / single-country ETFs, ADRs** | xasset scan: intl equity IBS +3.8bp (weak, rejected). | killed: intl close->open (Round-era, dead), intl ETF overnight (frontier reset TESTED-AND-REJECTED). | ETF-PD intl +1.0bp (closed). MSCI add/delete flows on US-listed ADRs: untested, ceiling-killed (~4 effective days/yr x ~1.5% x 50% x 50% ~ 1.5pp). | ADR vs home close (ADR-HOME): deferred, then closed by reasoning (same stale-price structure as ETF-PD; cross-venue inaccessible at Schwab). G4 ADR terminations killed (count). INTL-PREF PASS but ACCESS-KILLED (TSX/IBKR). | foreign-holiday stale NAV: dead by the ETF-PD mechanism (NAV moves to price). | -- | -- |
| **Bonds / Treasuries (ETFs; cash bonds not retail-executable)** | xasset: bonds +1.7bp (rejected). TAC Treasury-auction concession KILL (2016-26, +2.4bp t 0.9). IEF after auctions (Round 30 #14) dead. | -- | killed: BSPD (N 835), fallen-angel issuer equity ceiling-killed (~0.4pp, FISD PIT ratings do exist at issue level), HY-ETF (HYG/JNK) rebalance-day arm not tested but TME-class ceiling 1-2pp. BOND-LEAD (N 948) dead. Corporate bonds: dealer markups 1-2% -> access-killed. | -- | **validated small**: TME month-end duration extension (TLT close T-3 -> T, +32bp/mo net, 2002-15 untouched, 13/14 yrs; ~4%/yr deployed). TME-L2 overlay promising; TMF 3x ceiling-killed (+5.8pp honest, 2026-10-11); TME via futures access-killed (Schwab IRA futures $25k). XB IBSxTME allocation dead. RB6040 artifact. | BIL/SGOV adopted; non-competitive T-bill auctions vs SGOV ~5-10bp/yr (trivial, not run). | -- |
| **Preferreds / baby bonds ($25-par)** | killed: PREF-DIP (N 880), INCOME-SHOCK panic rule (N 1021, loses 2008-07), PXB (add-on tranche only). untested: auction-executed overnight dip in $25-par paper -- ceiling-killed (thin crosses cap deployment to ~20%, ~1pp). | -- | killed/ceiling-killed: PREF-INDEX inclusion/deletion (0.2-0.4pp, no PIT holdings), K delisted $25 paper (2 events/11y), L special-event calls, N CEF-pref 200% coverage floor, downgrade-to-HY forced selling by IG-only pref ETFs (same class, thin paper, < 0.5pp). | arrears catch-up ex-nights (G2): 9/9 positive, +4.8%/event, ~1/yr, log-only (ceiling < 0.5pp). New-issue first close +0.28% median: allocations unavailable, killed. | **passed/live**: PREF-EX (N 861, official crosses 2021-26 +38bp/event t 20, Sharadar 22/22 yrs; Roth live from 10-21, 30-trip cost gate) + ETDX (N 869, baby bonds + CEF prefs +44bp CO). Capacity binds ~$5k/book; ROTH-STACK +5.4pp at $10k; TAX-STACK pass-small but TAX-NOWASH (N 1029) forbids running it in taxable while the Roth runs it. The $25-par neighbourhood is **saturated** (memory 49). | PREF-EX IS the carry capture (dividend-proportional under-adjustment). FXD/CEFX5 (N 1023, CC KILL; CO forward arm in the shadow) cover fund paper. | SEL-PREF yield-desc stands (N 1033); conditioning a ~5pp leg is ceiling-killed. |
| **Closed-end funds** | **passed/live (Roth, dry->live 10-19)**: CEF-RV weekly discount reversion (N 859-60), OOS 1999-2014 PASS but survivorship MATERIAL (CEF-SURV99: alpha bound ~0..+105bp), 2016-26 +125bp/trade vs EW CEF (CEF-ALPHA N 892-3), +114bp vs same-category peers (CEF-PEER N 933); ~+4.8pp/yr deployed; CEF-RV-FWD gate 60 trades. CRASH-C discount-blowout staged buy WEAK-PASS (N 1026-7, 2008/2020 only). A daily-cadence discount-shock night = cadence variant of a live leg (not untested). | -- | killed: term/target-term CEFs (DL5), CEF NAV tenders as odd-lot (Round 31), activist 13D G45 (+2-3.6%/60d, +3.4pp book: forward watcher), G50/G51/G53/G54 (select), CEF-TL/CEF-TL2 (N 824, N 864: Jan gross +2.7% t 3.3, net +0.13), SEL-CEF slot rules (N 1032). Rights offerings: capital-proportional, no per-deal table, payoff ~0 (NEXT 299, prose 3337). | killed: CEF-TXT N-CSR tone (N 888-9), NAV nowcast from holdings (blocked N-PORT; and ETF-PD says NAV moves to price). NAVFALL lead (N 891) PASS but ~half SPY rebound. | killed: CEF December tax-loss (above), FXD CEF ex-nights (+13bp, < 10bp since 2020), CEFX5 large-distribution ex-night (N 1023 CC KILL; CO +52bp t 2.85 unregistered -> CEFX5-FWD shadow, 30 events). | CEF DRIP-at-discount: reinvested dividend only, trivial. | SEL-CEF depth rank-1 stands; CRASH-C is the only regime arm (weak-pass). |
| **Open-end mutual funds (Schwab OneSource, NAV at 16:00)** | closed by reasoning: a fund order fills at the closing NAV = buying the closing print of a diversified basket; index-IBS / multi-day oversold index entries are dead (V6, "IBS timing"). | -- | killed: F-SALE/F-SALE2 as the counterparty (above). Fund liquidations -> holdings: ceiling-killed (prose 8974+, stakes tiny vs ADV). | stale-price (time-zone) timing: structurally dead since the 2003 fair-value rules + Schwab 30-day round-trip fee. | -- | money-market vs SGOV: trivial. | -- |
| **Options (instrument) / options-induced underlying flow** | class closed (2026-10-04 part 4-5): T1-T7, T5/T5L (-3.4% of risk far-side), 0DTE, 1DTE condor/fly, straddles, put-write, iron condor, CRASH-B rolled puts (N 1025: one SPY put needs ~$170k). | -- | killed: OPEX OI-pinning SPY (opex_pin 2023-24), GAMMA-MKT index dealer gamma (N 1008: positive = vol proxy), GAMMA-FREE forward (N 932 shadow), SKEW-MKT (N 1009), LUCK-B4 per-stock option state. ceiling-killed on paper: single-stock OPEX pin (1.8-4pp), per-stock signed gamma continuation (<= 10bp/day lit), buffer-ETF reset-day collar hedging (deep market). | BORROW-XS (option-implied fee) = unshortable side. | OPEX-week calendar sizing dead. | killed: PCP-HTB (N 1019), box spread (access), covered-call ETF roll flows (deep market, not run). | killed: Lab-CB put/call, Lab-CC SKEW (declined), VIX9D/VIX conviction confirmations. |
| **Futures (ES/NQ/MES/MNQ, CL/NG, ZN)** | killed: CBAS cash-futures basis (N 863: no persistent dislocation regime 2011-25; label-shift fix in cbas.py). | killed: cross-asset TSMOM (ETF proxy), COTX positioning (N 862). | killed: FUT-ROLL (ES +1.3bp 2021-25, arbitraged), FND physical delivery (CL/NG, branch closed by user 2026-10-04), FCC commodity curve carry (N 825; generic carry excluded until a named constrained participant is written down), SOQ (ceiling-killed). blocked: CME margin-hike deleveraging (no margin-rate history; probed 4 ways). | COTX (N 862) dead. | TME via Treasury futures: access-killed (commissions; Roth futures need $25k). | MNQ vs QQQ noise (Study D), micro futures (add. 25): nothing to run; conviction in MNQ AJ1/AJ2 shadow. Access: Schwab futures in taxable only, $2-25k is one MES. | -- |
| **Crypto (Schwab spot BTC/ETH ~75bp/trade, taxable; spot ETFs in Roth)** | xasset: crypto majors no premium (spot, 24/7). LIQ-CASC perp cascades (N 883) dead (and perps are not at Schwab). **untested: IBS on auction-traded crypto ETFs (IBIT/ETHA/FBTC) -- a different wrapper (closing/opening cross, equity clientele) from the spot test; standalone ceiling ~3-7pp (U6, below gate; universe extension only).** | killed: CRYPTO-TA MACD/RSI daily (N 998) and 12h-4h (N 999-1002), crypto trend (RESULTS.md: = B&H Sharpe), LUCK-B3 alts (N 941). | killed: BTC-FIX ETF NAV window (N 879), GBTC conversion (over). ceiling/access-killed: funding carry, CME basis, unlocks, listings, depegs (memory 43); DAT mNAV discount data-limited. | -- | weekend gap into the Monday open cross: in the gap (closed by reasoning). | funding carry: access-killed (Coinbase). | MACD>0 & >SMA200 trend filter: risk choice, not alpha (CRYPTO-TA). |
| **Corporate actions (splits, spin-offs, split-offs, round-ups, offerings, tenders)** | **shadow**: forward-split ex-date night (EXDATE-OOS 1998-2012 +82bp raw, median +43; SPLIT-CROSS 2016-20 net +129 but t 1.73 FAIL; exdate-open shadow 1/40). SPIN-T0 parent into E open (+83bp t 2.0, n 78, ~13/yr, registered PASS, shadow family). killed: split nights T+1..T+4, Lab-BM 60d drift, reverse-split nights (short side), ticker-change first night (artifact), de-SPAC first night, spin-off child first nights (short side). untested: reverse-split ex-date night LONG (data convention; junk universe, prior negative, ceiling < 2pp). | killed: SPIN-CHILD drift (N 840), parent post-spin drift (-3.1%, killed at gate), J5-J8 (buyback/split/upgrades), DELIST-31, uplisting (short side only), BK-EMERGE-GV Ch.11 equity (N 1020 lottery). | **CPC forward validation (live, personal-scale)**: split-off exchange offers (12/14, +7.4%; odd-lot priority) and reverse-split round-ups (alert; ~$370/yr). **Odd-lot tenders ABANDONED (2026-10-24)**; UMH DRIP hold-only (DL1 pays, manual); thrift conversions DL-G27 (+2.6pp, needs a depositor account 1-2 yrs before the record date, manual). killed: DL2 warrant offers, DL3 DEFM14C, DL4 liquidations (too rare), DL6 closing ETFs, DL7 IPO access, B3 cash tenders, B4 going-private cash-outs, MERG-CASH (not tradeable), SPAC commons L16 / SPAC trust yield (manual election = the tender objection), lockups (#7), G4 ADR terminations, rights offerings (~0). The free-data shape-B/C space was declared exhausted 2026-10-08 (memory 37) and no new CPC family is allowed. | Study T SEC offering filings on night picks (shadow), Study U issuer classes (dead, mislabeled), EFFECT notices (L18 not registered), I25 short interest x announced buyback: untested conjunction, event-sliver shape -> ceiling-killed (< 2pp unless > 5%/event). | -- | -- | -- |
| **Index events (S&P, Russell, sector/pref indices)** | S&P 500 deletion rebound at the effective-date close cross: not separately run; most deletes are M&A; ~10 discretionary/yr x 2% x 20% -> ceiling-killed (~0.4pp). | -- | killed: S&P add/delete after announcement (in the gap, tradable window flips sign), SPX-ELIG (N 843), S&P 400/600 replacement prediction, RSP/SCHD rebalance front-run (count/bound), PREF-INDEX (0.2-0.4pp), Russell recon reversal (untestable: no membership; proxyable from PIT cap but 1 event/yr x 2-3% x 50% ~ 1-1.5pp, killed at gate 2026-10-06), MSCI ADR adds (ceiling ~1.5pp). | -- | witching-day night (dead, weak watch), quarterly share updates (in witching). | -- | -- |
| **Halts / news** | closed in every form 2019-26: HALT-REOPEN (N 1046), RE-HALT (N 1053), NEWS-HALT (N 1051: bad news keeps falling; up-news fade +112bp short-only, ~35/yr, ceiling ~0.5pp), Lab-AY/BA, BF (night picks that halted, too rare). Not tested and ceiling-killed: halts reopening at the 09:30 cross (short side), < $10M ADV, 4th+ halts. | NEWS-DRIFT dead. | THR threshold lists dead; SEC 10-day suspensions untradable at Schwab. | news sentiment / LLM judge / FinBERT: closed by the user. | -- | -- | 8-K bad-news drop filter (R1a/b) dead. |
| **Insider / filings (Form 4, 13D/G, 13F, 8-K, S-1/424B)** | -- | -- | 13F (F13C) dead; dilution-drag screen (implied shares -5%/q) = defensive observation, ceiling-killed as a night filter (2026-10-10). | see single-stock info cell: ID3/EV2 shadow (the only live event edge), everything else dead at judge half. RSU vest selling (G36) dead; 10b5-1 unusable long-only. | 10b-18 buyback blackout flow: ceiling-killed (1-2%/yr). | -- | -- |
| **Tape / auction microstructure (official crosses only)** | execution cost ~0bp established (216 fills at the official print); night auction cost by price bucket (REGISTRY). CLOSE-DISLOC dead. | -- | Nasdaq imbalance feeds: dead (spread-bound; paid). Closing-cross size as a free proxy: lookahead. | 15:40 quote imbalance (BB forward, QI-HIST N 898 dead as registered). | -- | fill-cost ledger live. | NIGHT-TAU closed; AX1/AX2 auction-share tilts dead. |
| **Alternative data / text** | -- | -- | -- | closed: Wikipedia (N 936-7), Amazon reviews (N 1008), Reddit sweeps (Round 18/Reddit round), Benzinga, LLM news judge (shadow, backtest invalid), FinBERT; Google-Trends attention = WIKI class (not run). Tor: null permanently. | -- | -- | -- |

Rows/cells marked `--` have no study because no mechanism of that column is plausible for that wrapper; they are not
"untested" cells (a bars-and-signals test there would be a costume of the single-stock/ETF row).

## Untested cells and named siblings (ranked)

Ranking key: paper ceiling at $10k (formula in each row) and distance from the nearest killed neighbour. Honest
read first: after N 1060, **only three cells clear the +8pp gate on paper, and each carries a low prior from a
neighbouring result**. Tier B cells are untested but below the gate (run only as a zero-cost extension of a live leg,
or as a class-kill that closes several `not tested:` siblings in one run). Tier C is blocked. Everything else that
earlier rows called "not tested" resolves to ceiling-killed (listed at the end so it is not re-proposed).

### Tier A: MEASURED 2026-10-25, all KILL (kept for the record; none of these is untested now)
- U1 -> REC-RECALL (N 1061): KILL, WEAK by bars (+29/+21bp net, t 3.0/2.8) but the E-10..E-6 placebo earns the same; the D10 fee at E-6
  is a put-call-parity dividend spike (data rule). Cell "US single stocks x forced flow (record-date recall)" = killed 10-25.
- U2 -> NIGHT-SHORT (N 1062): KILL, 2003-15 excess -12.8bp/night t -3.0; the >20% bin (NIGHT-SHORT-20, N 1064) fails OOS 2016-26
  (-27.6, squeeze profile). Cell "US single stocks x liquidity provision, short side, overnight" = killed 10-25.
- U3 -> STK-IBS-OPEN (N 1063): KILL, 2003-15 net -4.1bp t -1.8, 2016-26 -1.6. Cell "US single stocks x liquidity provision at the
  opening cross (no drop gate)" = killed 10-25.
Next study must come from Tier B (below gate: U6 crypto-ETF IBS replay is the one zero-cost extension) or from unblocking Tier C data.

### (was) Tier A: untested, paper ceiling >= +8pp at $10k, runnable today on data on disk

**U1. Record-date lending recalls in hard-to-borrow names (the deferred RECORD-RECALL leaf, branch_loop 2026-10-19).**
- Cell: US single stocks x forced flow (named counterparty = short sellers who must cover / lenders who recall before the
  holder-of-record date). Form: fixed rule, standalone long, auction-executed: buy the closing cross at E-5 (E = ex-date,
  = record date - 1 under T+1), sell the E-1 closing cross (before the ex drop), only in option-implied borrow-fee D9-D10
  names (`optionm.borrate`, nearest-30d tenor, sentinel -99.99 dropped). Arm B: proxy record dates (DEF 14A cover page,
  EDGAR full-text search, needs `SEC_USER_AGENT`), same window into the record date.
- Why it is not a costume: EXDIV-OPEN / THN measured the ex-NIGHT on all commons (tax-clientele under-adjustment); the
  "dividend-fail pre-ex front-run" ceiling-kill (memory 27) was the FTD form. The pre-ex covering window conditioned on
  borrow fee has never been read. BORROW-XS says D10 names underperform ~106bp/mo unconditionally, so the test must be
  excess vs the same-decile unconditional window.
- Data: WRDS `crsp.dsedist` (exdt, rcrddt, 2001-2024) x `optionm.borrate` x `crsp.dsf`; official crosses 2021-26 for
  the executable check. Period never used to choose a rule: all of it (no record-date rule exists in the program).
- Ceiling: ~1,500 HTB dividend events/yr (~6/day), 4-session holds, 100% of the account deployable in rotation ->
  ~60 full-capital holds/yr x net edge x 50%: +40bp/event -> **+12pp**; +20bp -> +6pp (below gate). Clears only if the
  pre-ex run-up is >= +40bp net in D10 and monotone in fee.
- Cheapest kill test (~1 h): D10 minus D1 close(E-5)->close(E-1) excess vs same-decile unconditional 4-day windows,
  2001-24, day-clustered t, halves, ex-top-5, median; kill if < +20bp or not monotone in fee decile. Taxable or Roth (long).

**U2. Night-leg short mirror: liquid up-day names at the close cross, covered at the open cross (taxable margin only).**
- Cell: US single stocks x liquidity provision, short side. Form: day_ret >= +8% and IBS >= 0.90 at the close (daily-bar
  proxy; exact 15:40 on SIP minutes 2016-26), $5+, ADV >= $10M, ETB only, short the closing cross, cover the opening
  cross; net 5bp/side + 2bp borrow; excess vs the EW-universe overnight.
- Why it is not a costume: every short study so far was intraday (Study S after the open, GAP-SHORT 09:31->close,
  Lab-BA halt reopens, NEWS-HALT up-fade, SSR-LIFT T+2 session) or a tilt. The overnight short of a close-at-high
  crash-up has never been run; it is the explicit "short side: not tested" sibling on INTRA-ANY, PREMKT-CROSS,
  BRK-RETEST, HL-BOUNCE, ETF-PD, F-SALE2.
- Prior: **negative** (OVN-MOM N 939 and GAP-NIGHT N 1050 show attention/up-gap names earn the overnight premium, +13bp
  for up-gaps). Value is a class kill: one run closes the "short side" sibling on six rows at once, or finds the one
  asymmetry the long-only program could not see.
- Data: Sharadar SEP 2003-26 (delisted-complete) for the daily proxy; `data/research/night/sipd` minutes + official
  crosses 2021-26 for the exact form. Judge 2003-15 first (never used for a short rule), report 2016-26.
- Ceiling: night-leg shape at 0.5x gross: ~250 nights/yr x +15bp net x 50% x 50% = **+9pp** if the overnight premium is
  negative for these names; Roth excluded (no shorting); squeeze tail (SSR-LIFT maxDD -41% at 0.5x) applies.
- Cheapest kill test (~1 h): daily-bar proxy on Sharadar, pooled and per-year, ex-top-5, median; kill if mean <= 0 or
  median <= 0 in 2003-15. No tuning of the +8% / 0.90 cutoffs (the mirror of the live rule, by construction).

**U3. Open-to-open IBS on liquid single stocks without the -8% drop (the ETF leg's form on stocks).**
- Cell: US single stocks x liquidity provision at the OPENING cross. Form: top-500 by 20d $ADV, IBS < 0.2 on d with
  day_ret > -4% (so it is disjoint from the night leg and NIGHT-BAND), buy the d+1 opening cross, sell the d+2 opening
  cross, equal weight across signals, excess vs the EW liquid universe open-to-open; tier 5bp/side.
- Why it is not a costume: the IBS leg was only ever run on 18 ETFs (and "rule-based IBS universe" = all liquid ETFs,
  dead); the night leg is close-cross entry with a -8% drop; NIGHT-BAND covered -4..-8% close->open; the swing-book
  "IBS / close-at-low entry gate" was a multi-day z-score book. The one-session open-to-open stock form has no row.
- Prior: low. The IBS premium scales with vol (xasset scan) and single stocks are more volatile than ETFs, but
  NIGHT-BAND's gradient (-4..-8% ~ +4bp gross) says the shallow-dip premium in stocks is small, and the ETF leg's own
  2003-15 net was +5bp t 1.0.
- Data: Sharadar SEP 2003-26 (daily open = official open cross 2016-20 verified, SPLIT-CROSS); official crosses 2021-26.
  Judge 2003-15 (touched for the ETF rule, never for a stock rule; report it as such), report 2016-26 and 2021-26 crosses.
- Ceiling: daily, 100% of capital: 250 x +15bp net x 100% x 50% = **+19pp** on paper; at the NIGHT-BAND-like +4bp gross
  it is ~0 net. Clears only at >= +10bp net.
- Cheapest kill test (~1 h): one look, net mean/median/ex-top-5/halves/day-clustered t vs the universe; kill if net
  < +8bp or t < 2 in 2003-15. No IBS-cutoff or universe tuning.

### Market scan 2026-10-26 (added after the Tier A measurement)
- LETF-REV (N 1065): "US single stocks x forced flow (single-stock LETF close rebalance), reversal at the next open" = killed standalone
  10-26; **open candidate: night-leg tilt by LETF pressure** (+99.6bp/night on the live picks with I >= 0.05, 88 nights, paired t 1.66),
  status = untested forward (shadow not yet built; night size-up is a user decision).
- Round-up pipeline: supply flat; lead time is the constraint (EDGAR discovery would add days). Not an edge question.
- Overnight-session passive quoting: UNBLOCKED (Alpaca feed=boats, Blue Ocean bars from 2024-09-16) and measured: NIGHT-BOATS (N 1066)
  KILL for the night leg's +1% exit offer (tail stop only). Untested: dynamic overnight exit, entry side, exchange sessions after 2026-12-06.
- Blocked until data exists: half-penny-tick spread capture (from 2026-11).

### Tier B: untested, below the gate on paper (extensions, class kills, or forward shadows only)

**U4. Schwab fully-paid securities lending income on HTB holdings** (single stocks x cost/carry). Named counterparty =
short sellers; capacity-limited in the user's favour only if small lots get lent. Paper ceiling: D10 fee ~15-30%/yr x
Schwab's share (~50%) = +7-15pp on lent capital, **minus** the D10 underperformance BORROW-XS measured (~-8..-13%/yr vs
low-fee names), unhedged -> ~0 or negative; hedged needs a short (taxable). Verdict on paper: <= 0 unless rebate share
> ~80% and utilization ~100%. Not a backtest: the one free test is an account action (enrol SLFP, hold one known HTB
name 30 days, read the lending-income line; user decision). Data: `optionm.borrate` for the fee universe; Schwab's
actual rebate is the blocked "custodial borrow fee" row.

**U5. Coval-Stafford 2-4 quarter holds on the fire-sold decile** (single stocks x forced flow, the `not tested:` field
of F-SALE2 N 1060). Pressure panel `data/research/fsale2/` is on disk (30 min). Literature long-leg reversal ~+6-8%/yr
gross over 12-18 months, 100% of capital, quarterly: x 50% capture = **+3-4pp**: a Roth sleeve over beta, not a 2x.
Kill: next-4-quarter excess vs EW <= 0 or carried by < 5 names.

**U6. IBS on auction-traded crypto ETFs (IBIT / ETHA / FBTC, Roth)** (crypto x liquidity provision). Different wrapper
from the spot Binance test (closing/opening cross, equity clientele; the mechanism is the equity-vol liquidity premium,
and BTC vol is ~3x SPY). History 2024-01 on (Alpaca daily + official crosses), ~450 bars: a replay, then forward. Ceiling
standalone: ~50 trades/yr x 30-60bp x 50% x 50% = **+4-7pp**; as a universe extension of the live IBS leg it costs
nothing. Kill: 2024-26 excess vs the leg's same-day picks <= 0; else forward shadow (no live size without 60 trades).

**U7. Daily-disclosed active-ETF trades (ARK-class) -> next-day in thin holdings** (information asymmetry x ETFs).
Named counterparty publishes its own trades after the close; copycat and continuation flow in names where the trade
is > 1% of ADV. Data: historical daily holdings CSVs (not on disk; github archives 2020+, a scrape). Ceiling: ~5-10
trades/day in thin names, +20bp next day, 20% of capital, 50% -> **+2-5pp**, and ARK AUM is ~1/5 of 2021. Below gate;
run only if a larger disclosed-trade universe (all fully transparent active ETFs) lifts the event count 10x.

**U8. Single-stock close-at-low in the shallow band as a night (close-cross) entry** (-4%..0%, IBS < 0.10): the last
leaf of the NIGHT-BAND tree. Ceiling-marginal: the -4..-8% band is +4bp gross (inside cost); the shallower band is
expected lower. Run only if NIGHT-BAND-FWD passes its 60 nights. Otherwise ceiling-killed.

**U9. Reverse-split ex-date night, long side** (corporate actions x liquidity provision; EXDATE-OOS left it "data
convention untested"). ~300/yr, mostly sub-$5 junk; post-reverse-split drift is negative in the literature; ceiling < 2pp.
Run only as a 20-minute Sharadar look if a reverse-split-adjustment convention is needed for another study anyway.

**U10. Short interest x announced buyback (discovery I25, memory 06)** (single stocks x forced flow, named counterparty =
issuer under 10b-18). Compustat `sec_shortint` on WRDS + buyback authorizations (8-K text, needs EDGAR). Event-sliver
shape: ~100 events/yr x effect x 10% position x 50% -> < 2pp unless > 5%/event (J5 big buybacks dead at judge half).
Ceiling-killed as a leg; only a > 5%/event median would reopen it.

### Tier C: untested and blocked (do not write code; record the data unlock first)

- ETF creation/redemption pressure at daily horizon on constituents / "ETF fire sales" (needs daily shares outstanding
  per fund; CRSP MF has monthly TNA only; at the quarterly horizon it is a costume of F-SALE2). Intraday iNAV entries for
  ETF-PD / CEFs (blocked). N-PORT monthly holdings (blocked). Margin-call cascades (no data). CME margin-hike
  deleveraging (no margin-rate history). Custodial borrow/recall fees (U4's rebate). Russell membership (paid). PIT issuer
  ratings beyond FISD issue level (sample only). DAT mNAV discount (data-limited).
- Proxy record dates (U1 arm B) are a 3-4 h EDGAR build, not blocked; listed with U1.

### "Not tested" fields from earlier rows that resolve to ceiling-killed (do not re-propose as untested)

| sibling named on a row | ceiling at $10k (formula) | source |
|---|---|---|
| ETF-PD premium short side | symmetric to the long side by the NAV-moves-to-price decomposition: ~1-3bp -> ~0pp | ETF-PD N 1059 |
| HY-ETF (HYG/JNK) rebalance-day arm | 12 x <= 30bp x 100% x 50% = 1.8pp | prose 8974+ |
| single-stock OPEX pinning | 12-52 x <= 30bp x 50% x 50% = 1.8-4pp | prose 8974+ |
| per-stock signed dealer gamma continuation | <= 10bp/day lit, index form dead (GAMMA-MKT) | prose 8974+ |
| SOQ third-Friday open dislocation | 12 x <= 20bp x 100% = 2.4pp | prose 8974+ |
| fallen-angel issuer equity (FISD PIT) | ~40/yr x small x sliver ~ 0.4pp | ETF-PD tick |
| mutual-fund liquidations -> holdings | stakes tiny vs ADV | prose 8974+ |
| ADR vs home close | ETF-PD structure; cross-venue not at Schwab | prose 8974+ |
| SPAC trust-value yield | manual election, weeks of lock = the tender objection | prose 8974+; memory 54 |
| earnings-announcement night (IBES timing) | DS1 dead at +0..6bp gross | prose 8974+ |
| VIX-inversion long mirror | 12-15/yr x 59bp x 50% ~ 4pp | memory 42 |
| TME via TMF 3x | 12 x 96bp x 100% x 50% = 5.8pp | memory 42 |
| breadth as a sizing dial; PROVOL high-vol size-up; dilution screen; borrow-fee night filter | each acts on a ~4%/yr leg: < 1.2pp | N 1041, memory 48, 42 |
| weekly-bar bounce forms; holds > 10d; trailing stops; k != 3; 20d/252d levels; intraday retests | ~6 events/yr/name, < 1pp; neighbours all <= 0 | N 1055-58 |
| F-SALE2 inflow-bought short side | quarterly x 80bp x 50% x 50% ~ 0.8pp | N 1060 / F-SALE correction |
| NEWS-HALT up-fade short; 09:30-cross halt reopens; 4th+ halts | ~35/yr x 1% x 10-20% x 50% ~ 0.4-0.7pp | N 1051, 1053 |
| GAP-NIGHT siblings (RVOL attention, < $50M ADV, up-gap-only) | decaying family, +3-5pp at 2022-26 strength | N 1050 (shadow) |
| due-bill (>= 25%) specials | ~10-20/yr, count/bound | Goal hunt G-rows; N 1052 |
| Congress PTR copying | 45-day lag -> effect in the gap; post-2012 lit ~0 | R8 (data now free) |
| MSCI / S&P deletion rebounds on US-listed names | ~4 days/yr x 1.5% x 50% x 50% ~ 1.5pp | index row |
| industry lead-lag at daily/weekly | long-only half of a decayed 1%/mo LS ~ 1.5pp | SECT-LAG sibling |
| $25-par overnight dip at the cross | thin crosses cap deployment ~20%: ~1pp | PREF-DIP / INCOME-SHOCK neighbours |
| THEME-NIGHT themes from text/news or ETF flows | text closed by user; flows = ETF-PD class | N 1034 |
| SEL-* dedupe-before-vol20 | <= +0.6pp, shipped as a code fix 2026-10-19 | N 1030-33 |

## Data sources

On disk / licensed (what each cell above runs on):
- **Sharadar full bundle** `~/data/sharadar` (SEP stocks + SFP funds 1997-12..2026-10, delisted-complete, permaticker;
  actions, sp500, SF1 fundamentals, SF2 insiders 2008+, holdings). Daily bars only; daily open == official open cross
  2016-20 (SPLIT-CROSS). Rules: confirm `actions` dividend rows by the closeadj/close jump (40% of pre-2013 specials
  mis-dated); SFP dividends can be split-adjusted vs raw prices; night/IBS/ex-date/CEF rules have touched every year.
- **Alpaca SIP** minute bars 2016+ (`data/research/night/sipd`, `data/cache/bars_pre2021`), daily 2021+; inactive symbols served.
- **Official auction crosses 2021-26** (SIP open/close prints; live cost ~0bp on 216 fills). `data/research/cefx5/auctions.json`, exdate-open and PREF-EX shadows.
- **WRDS** (user account; standby read-only, pass explicit `sym_root IN (...)`): CRSP daily/dist (`dsf`, `dsedist` with
  rcrddt/exdt; prices end 2024-12-31), `crsp.dsenames`; Compustat incl. `sec_shortint` 1973+; OptionMetrics `opprcd`
  (OI, greeks, EOD not raw NBBO; SPY/QQQ from 2005), `borrate` (option-implied fee, -99.99 sentinel, pick nearest-30d
  tenor), `vsurfd`; TAQ ms 2003-26 (~40s/day-scan without a symbol list); CRSP mutual funds (`daily_nav`, `monthly_tna`,
  `fund_hdr_hist`, et_flag; NO CEFs) -> `data/research/etf_pd/nav.parquet`; `tfn.s12` (flow proxies from `assets` are
  noise; no MFLinks); TRACE/FISD (`fisd_ratings` = PIT issue-level ratings; `cmsn_trd` NULL from 2012-02); IBES;
  Datastream (international; access-killed for trading).
- **Binance** daily/4h spot panel 2017-08..2026-09 incl. 249 delisted (`data/research/crypto_spot/`).
- **FINRA** weekly ATS venue mix (`data/research/finra/ats_etf.parquet`, key-less `otcMarket/weeklySummary`; regData key
  401s), margin debt monthly (`finra/margin.xlsx`), short interest 2020+.
- **LULD / NYSE halt history** 2019-07+ (`data/research/halts/`); Nasdaq Reg SHO threshold lists 2008+ (URL in memory 12).
- **CFTC COT** (Socrata, cached `data/research/cot/`); **Databento** GLBX daily contracts 2011-25 (session-start stamped:
  remap trade_date per `cbas.py::trade_dates`), OPRA cbbo-1m (credit ~$4 left); SSGA navhist; CEFConnect (blocks the
  server IP; Nasdaq Fund Network NAV symbols instead); FRED (SOFR/IORB/DTB3); Wikipedia pageviews `data/research/wiki/`;
  Amazon reviews `data/research/reviews/`.
- **Pressure panels reusable**: `data/research/fsale2/` (fund-flow pressure by stock-quarter), `data/research/f13f/agg.parquet`
  (13F state), `data/research/program/night_exact_pre2021.parquet`, `premkt_rows.parquet`.
- Free but not yet pulled: EDGAR full-text search (needs `SEC_USER_AGENT` in `.env`; DEF 14A record dates for U1-B);
  House/Senate PTR disclosures (ceiling-killed); ARK-class daily holdings archives (U7).

Blocked (verified against entitlements 2026-10-16, memory 46): margin-rate history (CME/FINRA house), custodial
borrow/recall fees (borrate is option-implied), intraday iNAV, N-PORT monthly holdings, `cboe.*` (permission denied),
PIT issuer ratings beyond the FISD issue level and the 1,322-row `ciqsamp_ratings` sample, Russell membership, MFLinks.
Access-killed by user ruling: IBKR and every non-US listing (2026-10-18); Coinbase perps; Schwab IRA futures (< $25k).
