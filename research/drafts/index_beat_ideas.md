# Index-beat hunt, round 1: idea list (written before any outcome)

Session llm-trader-ee, 2026-10-02, `prompt_index_beat.md`. Program N at the start: **760**. k (ideas judged) = 0.
Nothing below has been computed. Every idea names the death it is built to dodge (section 1 of the prompt).

Tags: track **A** new automated edge (**DP** = contract/deal payoff the Schwab API can run), **B** robust-to-market
(**FWD** = forward-only, 2026 structure), **C** after-tax / account structure. Extra tags (overlap allowed):
**DD** death-dodge of a named dead row, **SMALL** small-account-only, **WILD** wildcard, **OUT** from outside the repo.
Rough %/yr = gross guess at $2.3k / $10k / $25k before any data, so ranking can start; they are priors, not results.
Novelty 1-5 (5 = nothing like it in the repo or the literature I searched: NEXT.md dead table, RESULTS.md addenda,
outside_box_ideas.md, discovery_ideas.md, jump_ideas.md, event_edge_candidates.md, max_edge_candidates.md).

The base case all track C ideas are measured against ("the plan"): taxable $2.3k + $1k or $2k a month running the
live book (V7 as built, wash guard roth_first/G4s), Roth $8.5k + $7.5k/yr running the proposed Roth book; 35% ST /
20% LT, April payment, wash sales, edge-halves, tier costs (`taxable_frontier.after_tax`, `program_books.joint`).

---

## Track C: after-tax / account structure (16)

| id | idea / cause sentence | other side, why they keep paying | death dodged (how) | closest dead / done row, what differs | data (verified?) | ev/yr | rough %/yr | nov |
|---|---|---|---|---|---|---|---|---|
| C1 | **Bot only in the Roth, taxable = buy-and-hold index.** The taxable book's ST gains pay 35% every April, an index fund pays ~0.2%/yr dividend drag and defers 20% LT to the sale; with no taxable trades the Roth needs no wash guard at all (G0 inside the Roth = every night name, every IBS ETF). | the IRS: deferral is an interest-free loan; nobody "pays", the plan just stops paying | TAX (dodged by construction: no ST realization in taxable) | add. 31 G0-G4 (both accounts trade), add. 13 AD (SPY + noise overlay, switch at $100k): never "taxable holds only the index while the Roth gets G0" | sims in repo (`program_books.joint`, `after_tax`); SPY bars (verified) | n/a | combined plan Δ: guess −1..+3pp | 2 |
| C2 | **Taxable = index core + only the legs the Roth cannot run** (intraday margin noise leg at 4x, overnight leverage); IBS + night only in the Roth. | same as C1 | TAX, STACKING (no new edge, just placement) | add. 31 (d) said "no leg is better located on tax grounds" because all are ST; this splits on what each account CAN do, not on tax character | repo sims (verified) | n/a | Δ −1..+2pp | 3 |
| C3 | **Front-load the Roth**: contribute each year's $7.5k on the first trading day of January (and catch up the prior year's unused limit before April 15) instead of $625 every 21 sessions. | nobody; time in the tax-free account | TAX (more dollar-days at 0% tax) | Roth sims all use monthly deposits (roth.py, roth_opt); never tested | `roth_opt` / `program_books` (verified) | 1 | +$150-500/yr on the plan | 2 |
| C4 | **Section 475(f) mark-to-market election** for the taxable book: wash sales stop applying (incl. the permanent cross-account Rev. Rul. 2008-5 disallowance), losses become ordinary with no $3k cap. Lets both accounts run G0 (same legs, same names). | n/a (tax election) | TAX + the add. 31 G0 death (82% of losses disallowed) dodged by removing §1091 | add. 31 / 32 mention 475(f) only as a NOTE; never computed | repo tax code (needs a 475 mode: wash=False, no $3k cap) | n/a | Δ 0..+3pp | 3 |
| C5 | **The user's real marginal rate.** The program taxes every ST $ at 32-35%. A full-time student born 2007 with little wage income: either low brackets (fed 10-12%, CA 1-4%) or the kiddie tax (unearned income > ~$2.7k taxed at the parents' rate). Report the plan's after-tax %/yr vs the index at 0 / 12 / 22 / 32 / 35%. | n/a | TAX (if the real rate is ~12%, the brokerage book beats the index after tax by a lot) | digest uses 32% flat; add. 32 sensitivity 25/45% only | `after_tax(rate=...)` (verified) | n/a | report | 3 |
| C6 | **Tax-gain harvesting at the 0% LT bracket** (if C5 says the user is in it): an index core held > 1 year, sold and re-bought each December to step up basis at 0%. | n/a | TAX | none in repo | IRS brackets, after_tax | 1 | small, report | 3 |
| C7 | **December loss timing**: the taxable book's realized losses cluster in some Decembers; defer the January re-buy of Dec loss names (wash window) so losses land in the year they help most. | n/a | TAX (timing only) | add. 32 mech. 3 expected a small negative wash effect across Dec->Jan; never optimized | trade lists from taxable_frontier (verified) | 1 | <0.3pp | 2 |
| C8 | **Treasury-only idle cash for state tax**: taxable idle cash in SGOV/BIL (>50% Treasury, CA-exempt) vs a sweep/money fund; Roth idle cash in the highest-yield (state tax irrelevant). | n/a | TAX | add. "Parking idle cash in BIL/SGOV" ADOPTED; the state angle is new | yields (FRED) | n/a | <0.1pp | 2 |
| C9 | **Roth solo 401(k) if the user has any 1099/self-employment income**: Roth employee deferrals up to $24.5k (2026) on top of the IRA, run with the same cash-IRA book (Schwab Individual 401(k), no margin). Moves taxable money into tax-free. | n/a | TAX | none | IRS limits; Schwab account types | n/a | depends on SE income | 4 |
| C10 | **Robinhood-style IRA contribution match** (Gold 3% on new contributions) for the Roth deposits vs keeping the Roth at Schwab where the bot runs. | broker marketing budget | TAX/structure | none | public terms | 1 | +3% of $7.5k = $225/yr minus fees, but the bot can't run there | 3 |
| C11 | **1256 index options (XSP / XND) for the QQQ noise leg** via the Schwab API (it trades options, not futures): 60/40 tax, no wash sales. | n/a | TAX (26% blend vs 35%) | add. 32 M1-M3 were MNQ futures (API can't trade them, ~$61k notional) | contract specs (XND = NDX/100, ~$21k notional) | 250 | ~+0.8pp if costs allowed | 3 |
| C12 | **Wash guard by account size**: let the account with the larger *after-tax* marginal value own each shared name daily (Roth-first is fixed today); as the taxable outgrows the Roth the priority could flip. | n/a | REFIT (rule is mechanical: compare balances x (1 − rate)) | G1/G4s fixed priorities | joint() (verified) | daily | small | 3 |
| C13 | **Donate/gift-free: hold the taxable book's winners?** All legs close in a day: nothing to hold. Variant: route the *deposit day's* buy to the index and the bot only trades the account's first $X. | n/a | TAX | C1/C2 family | — | — | dup of C2, kept for count | 1 |
| C14 | **Index in taxable + tax-loss harvesting** with different-index pairs (VOO -> SCHX/VV): harvested LT-deferred losses offset nothing else if the bot is out of taxable; with C2 they offset the noise leg's ST gains at 35% now vs 20% later. | n/a | TAX (rate arbitrage 35% -> 20%) | none | SPY/VV bars | 1-3 | +0.2-1pp in bad years | 3 |
| C15 | **Kiddie-tax-aware split**: if unearned income above ~$2.7k is taxed at the parents' rate, cap the taxable *realized* ST gain near the threshold (rest in an index that defers), since the first $2.7k is taxed at 0-10%. | n/a | TAX | none | IRS thresholds | 1 | report | 4 |
| C16 | **Deposit routing**: the $1-2k/month goes to the account where the next dollar earns the most after tax (Roth until its limit, then taxable bot vs taxable index by C5's rate). | n/a | TAX | none | — | 12 | covered by C1/C3/C5 | 2 |

## Track A: new automated edges (19; DP = deal payoffs: 7)

| id | idea / cause sentence | other side | death dodged | closest dead row, what differs | data | ev/yr | rough %/yr | nov |
|---|---|---|---|---|---|---|---|---|
| A1 DP SMALL WILD | **Round-up in more accounts.** B1 pays per *account* (a 1-share holder becomes a 1-post-split-share holder). Schwab lets one person hold several brokerage accounts; `roundup_orders.py` already buys 1 share per account. N accounts = N x the payoff, capital ~$1-25 each. | issuers' other holders (dilution ~0) | LOTTERY (75 deals/yr, ~$4 each, not a few big ones); TOO RARE | B1 (PASS, live, 2 accounts): only the account count differs; depends on Schwab rounding per account (VIVK settles ~10-07) | roundup history (verified, `roundup.py`) | 75 | +$320/yr per extra account (+14% each at $2.3k) IF rounded | 5 |
| A2 DP | **Spin-offs / distributions that round fractional shares UP** (B1's mechanism on a spin-off ratio: 1 parent share -> 1 whole spinco share when the ratio is 1:20). | other parent holders | TOO RARE (search all EDGAR Form 10 / 8-K distribution text) | C16 forward splits / stock dividends round-up (0 listed); spin-offs never searched | EDGAR FTS (verify) | 1-5? | lottery-ish | 4 |
| A3 DP | **Mergers paid in acquirer stock whose fractional shares are rounded up** (1 target share -> 1 acquirer share when ratio < 1). | acquirer | TOO RARE | B1/C16 family; mergers not searched | EDGAR FTS (verify) | ? | ? | 4 |
| A4 DP | **CEF -> ETF / open-end conversions**: after the announcement the remaining discount closes to NAV on a dated conversion (contractual), bought with idle cash. | CEF holders who sell before the date (income funds, tax sellers) | GAP (enter after the announcement, take only the dated remainder); LOTTERY (no failure mode except a cancelled conversion) | DL5 term CEFs (discount had closed by the final year), DL6 ETF closures | EDGAR N-14 / 497 (verify), bars | 5-15 | +1-2% per event on idle cash | 3 |
| A5 DP | **Mandatory odd-lot "round-up" offers** (issuers selling odd-lot holders shares to reach 100 at a discount) — inverse of odd-lot buybacks. | issuer | TOO RARE | I3 premium programs (1 in 10y) | EDGAR FTS | ~0 | — | 3 |
| A6 DP | **SPAC redemption below trust** within 10 sessions of the vote/extension, redeem for trust $ (redemption = a 2-minute online reorg). | SPAC arbs who sell to recycle capital | GAP (contractual trust value) | L16 SPAC commons as BIL (closed: little idle money); the redemption-deadline window is the new part | SPAC lists (verify), EDGAR 8-K | 30-100 | +1%/event on ~$2k ~ +$20 | 2 |
| A7 DP | **Broker cash-transfer promotions** (ACATS bonuses 1-3% of assets, IRA match): small accounts can move the cheap part (index core) and back. | broker marketing | n/a | none | public terms | 1-2 | $50-300 one-off | 2 |
| A8 DD | **ID3 insider-buy day trade in the Roth's idle daytime cash** (it is a long-only, no-margin, same-day trade: legal in a limited-margin IRA, tax-free there). | opening-cross sellers (ID3) | TAX (the edge lives where tax is 0) + WHOLE SHARES ($20M+ ADV names are cheap enough) | ID3 shadow is taxable; Roth never tested | events_*.parquet (verified) | 150 | +2-5pp Roth | 3 |
| A9 DD | **IBS leg in closed-end funds** (no creation/redemption, retail-held, thin: the close-to-close reversal should be larger than in ETFs; small size has no impact). | retail CEF sellers at the close, no arbitrageur | TEXTBOOK (CEF IBS not published), COST (choose CEFs with ADV >= $5M) | add. 36 rule-based ETF universe (theme funds at momentum peaks) — CEFs are not ETFs; #34 parked | Alpaca bars of CEFs (verify) | 100+ | +1-3pp | 3 |
| A10 | **Night leg on preferred stocks / baby bonds** that drop >= 3% on no news (income holders dump at the close). | income retail | REGIME | night leg = common stocks only | Alpaca bars (verify) | ? | small | 3 |
| A11 DD | **Bogousslavsky end-of-day margin selling**: high-idio-vol stocks sold in the last 30 min by intraday-levered traders (who must be flat or within overnight margin at 16:00) rebound overnight; tilt the night leg toward names whose *last-30-min* drop is a large share of the day's drop. | intraday-levered retail forced to cut at the close | TEXTBOOK (published 2021, but our pool is different), HALF-FLIP (mechanism is rule-driven) | add. 23 "late selling" tilt dead (late-selling share not monotone) — same feature, so likely dead: kept only for the post-2026-07 forward version B7 | night panel (verified) | 250 | ? | 2 OUT |
| A12 DD | **Insider purchases in the Roth as a 20-session hold** — L19 20d drift dead in taxable; in the Roth no tax, but the drift was ~0: dead by construction, kept for count. | — | — | L19 | — | — | 0 | 1 |
| A13 | **Quarterly 13F "new position" by small specialist funds** (not Jump's hype): crowd copies a known small-cap fund's first buy 45 days later. | copycats arriving late | GAP (13F is 45 days stale: the move, if any, is slow) | none (W6 ARK is Jump's) | EDGAR 13F (verify) | 100s | ? | 3 |
| A14 | **Tender-offer odd-lot automation**: send the tender instruction through Schwab's API/online in < 5 min and buy automatically (removes the manual step of the live odd-lot tender alert). | prorated large holders | n/a (engineering) | odd-lot tender alert (live, manual) | Schwab API docs (verify: likely no corporate-action endpoint) | 1.3 | +$150-200/yr already counted | 2 |
| A15 OUT | **Overnight drift window (Boyarchenko-Larsen-Whelan, NY Fed SR 917)**: US equity overnight returns accrue around 02:00-03:00 ET (European open) as dealers lay off the prior close's order imbalance. With 23/5, hold SPY/QQQ from the close only to ~03:30 and sell in the overnight session. | dealers' inventory | REGIME (direction-free: the drift follows the close imbalance) | V6 / F3 / IBS index legs (close -> open) | E-mini history needed (not free) -> forward only, see B5 | 250 | ? | 4 OUT |
| A16 OUT | **Muravyev-Ni: options gain overnight, lose intraday** (JFE 2020): sell QQQ 0DTE/1DTE premium at the open, buy back before the close in the Roth (defined risk)? Needs option NBBO history (paid). | hedgers buying intraday vol | COST | Round 13 Z put-write dead; this is intraday-only | ThetaData $80/mo (paid) -> request only | 250 | ? | 3 OUT |
| A17 OUT | **Hartzmark-Solomon dividend reinvestment days** (RFS 2022): market +3-6bp on the heaviest dividend payment days; Roth idle cash only. | dividend-reinvesting funds | REGIME (direction from a calendar of cash flows) | outside_box #15 (not run: no shares outstanding) | Alpaca corporate actions + XBRL shares (verify) | 10-20 | ~0.1pp | 2 OUT |
| A18 DD SMALL | **Night leg names priced $50-500 at $2.3k use odd lots of high-priced picks first** — whole-share rounding today drops 15 of 49 names; re-rank the cash so the leftovers buy the next pick rather than sit (outside_box #41). | the bot's own idle cash | WHOLE SHARES (turn the rounding into redeployment) | #41 "engineering" never quantified | night panel (verified) | 250 | +0.5-2pp at $2.3k | 3 |
| A19 WILD | **The roundup deal list as a night pick blacklist / whitelist**: names announcing a reverse split within 14 days are excluded from the night leg (holders dump pre-split). | pre-split dumpers | GAP | none | roundup history (verified) | ~75 | tiny | 3 |

## Track B: robust to the market (14; FWD = forward-only: 7)

| id | idea / cause sentence | other side | death dodged | closest dead row, what differs | data | ev/yr | rough | nov |
|---|---|---|---|---|---|---|---|---|
| B1 FWD | **23/5 exit for night picks**: log the night picks' overnight-venue quotes at 20:00 / 00:00 / 04:00 / 08:00 ET from 2026-12-06; test whether a resting limit at +X% in the overnight session captures the bounce before the open (when the bounce comes from overnight retail buying). | overnight retail buyers | REGIME, REFIT (a fixed rule, measured forward) | "night exit later than the open" dead (add. 7); earlier exits never possible | Schwab/Alpaca overnight quotes (forward) | 250 | ? | 4 |
| B2 FWD | **23/5 Sunday-evening session for weekend night picks** (Friday close buys can exit Sunday 20:00 on weekend news). | weekend retail | REGIME | weekend x0.5 rule | forward | 50 | ? | 4 |
| B3 FWD | **Intraday-margin rule (2026-07-13) changes the 15:30-16:00 selling**: small accounts levered 4x intraday must cut to overnight margin by the close: the night leg's late drop and bounce should grow in retail-heavy names. Measure pre/post on Jul-Sep 2026 data already in hand + forward. | newly levered small retail | REGIME (a rule change, not a dial) | add. 40 is the bot's own BP, not others' | night panel to 2026-09 (verify) | 250 | ? | 4 OUT(A11) |
| B4 FWD | **Half-penny ticks / lower access-fee caps (Reg NMS 612 amendments)**: if tick-constrained names get $0.005 ticks, the noise leg's per-name costs fall and single-stock noise legs (add. 41 dead at 1.65bp) may clear; log spreads in the top-20 names forward. | spread earners | COST | add. 41 dead at the measured spread | compliance date (verify), forward quotes | daily | ? | 3 |
| B5 FWD | **Overnight drift (A15) in the 23/5 session**: log SPY/QQQ overnight-venue prices at 03:00-04:00 ET vs the close and the open. | dealers | REGIME | V6 | forward | 250 | ? | 4 OUT |
| B6 FWD | **Odd-lot quotes in the SIP (MDI rule)**: when odd-lot quotes inside the NBBO become visible, the night leg's close buys and open sells in high-priced names can be routed as odd-lot limits; log the improvement. | market makers | COST | #32 killed as research (engineering, forward) | forward fills | 250 | +0.2-1bp/side | 2 |
| B7 FWD | **Live fills as the cost regime**: the book's value collapses at tier_hi; a forward cost tracker that moves the night leg's capital between the 2.5bp and tier_hi books only on *measured* live cost (not returns). | n/a | REFIT (estimates cost, not edge), FALSE ALARM (cost is measured per fill, no small-sample edge test) | add. 38 live cost model (shadow), AQ cost gate | live fills (server) | daily | protects 5-15pp in bad cost regimes | 2 |
| B8 DD | **Regime dial that is the leg's OWN edge**: size the night leg by the trailing 60-day *auction-to-auction bounce of the whole night pool* (not the book's P&L, not the market) — the prompt's allowed dodge. | n/a | REGIME DIAL dodged as the prompt allows (the leg's own edge moves with the signal), REFIT risk | AU1/AU2 (20d mean overnight return per name: dead) — this is pool-level | night panel (verified) | daily | ? | 2 |
| B9 DD | **Edge diversification by mechanism**: give the IBS leg's idle half to ID3 (insider) day trades instead of BIL: a second, unrelated forced-trader edge so the book does not depend on one bounce. | opening-cross sellers | STACKING (one clean mechanism in idle money only, no shared capital) | ID3 shadow (taxable, 0.45x sleeve) | events parquet (verified) | 150 | +1-3pp | 2 |
| B10 | **Structural: night leg capacity by name ADV in $ (Study V)** — irrelevant at $2-25k; kept as the capacity line. | — | — | Study V | — | — | 0 | 1 |
| B11 DD | **De-correlate the noise leg from QQQ crashes by trading it in SMH/QQQ/IWM by liquidity rank each month** — IWM noise dead (AK); kept only as count, will not run. | — | — | AK | — | — | — | 1 |
| B12 WILD | **"Bot vacation" rule-free: none.** Run nothing on the 10 sessions a year with the widest overnight spreads (holiday half-days, Russell recon day) — a cost-calendar, not a regime dial. | n/a | REGIME (cost-driven) | pre-holiday "watch"; DS5 dead | night panel + calendar (verified) | 10 | <0.5pp | 2 |
| B13 FWD | **0DTE-era shift of retail flow to the open**: log the opening-cross share of retail-heavy names forward; if the open auction gets thinner, the night leg's open sell cost rises (a cost early-warning). | n/a | FALSE ALARM (cost only) | AX2 dead as a tilt | forward | daily | 0 (protective) | 2 |
| B14 | **Leg weights fixed by mechanism, not fit**: equal risk to each leg's *structural* counterparty (closing auction / reversal / trend) — a one-time, non-refit weighting. | n/a | REFIT dodged (no re-estimation) | AS softmax/inverse vol (dead) — same family, so likely dead | sims | — | 0..1pp | 1 |

## Wildcards and small-account extras (6)

| id | track | idea | death dodged | data | nov |
|---|---|---|---|---|---|
| W1 WILD SMALL | A DP | **Round-up in the Roth's look-alike tickers**: buy 1 share of both share classes when a dual-class issuer reverse-splits both (each class rounds). | LOTTERY | roundup history | 4 |
| W2 WILD | C | **Pay the April tax from the Roth?** Not allowed (distribution of earnings = taxed + 10%); contributions (basis) can come out tax-free: in a year the taxable needs cash for its April bill, withdraw Roth *basis* instead of selling... then re-contribute is not allowed. Dead by construction — written down. | TAX | IRS rules | 2 |
| W3 WILD SMALL | A | **$1 limit buys on 2-for-1 forward splits for the ex-date due-bill mismatch** (brokers mis-mark odd lots) | LOOKAHEAD | — | 2 |
| W4 WILD | B | **Run the night leg backward on up days** (buy the top gainers' last-minute pullback)? Price-pattern: banned. Written only to be killed. | — | — | 1 |
| W5 WILD SMALL | A DP | **Fractional-share programs as round-up buyers**: buy 0.01 share at Schwab (Stock Slices) before a round-up reverse split — does the round-up apply to a fractional holding? (Probably cash in lieu, but costs $0.01 to learn.) | LOTTERY | live test | 5 |
| W6 WILD | A | **Treasury auction reopenings in the Roth's idle cash** — dead family (#14), written for count. | — | — | 1 |

---

Counts: track A 19 (DP: A1-A7, W1, W5 = 9), track B 14 (FWD: B1-B6, B13 = 7), track C 16, wildcards 6 (W1-W6; A1 also
WILD), death-dodges (DD) 9 (A8, A9, A11, A12, A18, B8, B9, B11, + C4 dodges the G0 death), small-account-only 5 (A1,
A18, W1, W3, W5), outside sources 5 (A11 Bogousslavsky JFE 2021 https://doi.org/10.1016/j.jfineco.2021.03.009;
A15 Boyarchenko-Larsen-Whelan NY Fed SR 917 https://www.newyorkfed.org/research/staff_reports/sr917; A16 Muravyev-Ni
JFE 2020 https://doi.org/10.1016/j.jfineco.2020.04.004 ; A17 Hartzmark-Solomon RFS 2022 "Predictable price pressure"
https://www.nber.org/papers/w27993 ; C14 Chaudhuri-Burnham-Lo 2020 "An empirical evaluation of tax-loss harvesting
alpha" https://doi.org/10.1080/0015198X.2020.1760064). Decayed edges: published effects shrink 1/4-1/2 after
publication; A11 (late-day reversal ~ +10-20bp/night in the paper's high-IVOL decile) -> ~5-15bp here before cost;
A17 +3-6bp on ~10 days/yr -> ~0.1pp/yr, already below any bar (kept for count).
Total: 55 ideas.

## Rank (P dodge x %/yr at $2.3-10k after tax x automatable x novelty x P data works) — top 15

1. **C1** bot only in the Roth / taxable index (exact, cheap, the user's core question)
2. **C5** the user's real tax rate (exact, decision-changing)
3. **C3** front-load the Roth (exact, cheap)
4. **A1** round-up in more accounts (contract; conditional on VIVK)
5. **C4** 475(f) (exact with a 475 mode)
6. **A8** ID3 in the Roth's idle daytime cash
7. **C2** taxable = index + margin-only legs
8. **A18** whole-share leftover redeployment at $2.3k
9. **A9** IBS in closed-end funds
10. **B3** intraday-margin-rule close selling (pre/post on 2026-07..09 + forward)
11. **A4** CEF conversions
12. **B8** night pool's own-bounce dial
13. **B9** ID3 in the IBS idle half (taxable) — overlaps A8, run after it
14. **B1/B2/B5** 23/5 forward logs (spec-only rows)
15. **A2** spin-off round-ups (EDGAR search)

Alternation: C1 -> A1 -> B3 -> C5 -> A8 -> B8 -> C3 -> A9 -> ... (no track starves).
