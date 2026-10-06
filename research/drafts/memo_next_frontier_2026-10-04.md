# Research memo — next frontier (2026-10-04)

Context: Treasury-concession and SPY ETF-flow are REJECTED. The live book (IBS + noise + capped
night) scales to ~$100k/yr taxable, ~$250k/y ROI; its own leg-level capacity shows IBS and noise
decay only past ~$1M. So **execution improvements to the current book cannot plausibly 2x total
P&L at $2-25k** — the book is not capital-constrained until ~$1M. That kills the "capacity audit"
as the primary path to 2x and pushes the search back to new alpha. One caveat: the after-tax
crossover at ~$250k means *tax/capital location*, not execution, is the real ceiling — a separate,
known lever (Roth first), not new alpha.

Each candidate below is scored on mechanism → forced participant → survival → magnitude →
capacity → data → fastest falsification → failure mode → independence.

---

## Ranked directions

### 1. Signed dealer gamma → underlying (the one untested options-INDUCED flow)
- **Mechanism.** Market makers net short gamma must buy as spot rises / sell as it falls
  (positive feedback near big strikes); net long gamma dampens. Signed GEX (OI x gamma by strike,
  by expiry) predicts intraday continuation/reversal of the UNDERLYING.
- **Forced party.** Option dealers hedging inventory; they cannot not-hedge.
- **Survival.** Dealer inventory/risk limits; the effect is inventory-dependent and regime-switching.
- **Magnitude.** Literature: +0-2pp/yr as a *gate* on an intraday rule; strongest in the last 30 min.
- **Capacity.** SPY/QQQ underlying = bottomless.
- **Data.** Databento OPRA `statistics` (OI) + `definition` (strike/expiry) + option prices/IV for
  gamma; ~$180/yr SPY+QQQ (paid). **DATA-TARGET.**
- **Fast falsification.** One index, 2013-2016 (untouched): does negative-GEX → last-30-min
  continuation exceed 3bp net, t>2, placebo (GEX sign shuffled) 0?
- **Failure mode.** GEX sign assumed, not observed (need dealer long/short classification);
  OI-based pinning already failed (Study A-OPEX), so gamma ≠ pinning must be shown.
- **Independence.** Orthogonal to IBS/night; a possible *gate* on the existing noise leg.
- **Upside if real.** Modest; improves the intraday leg or adds a gated sleeve.
- **Recommendation: DATA-TARGET** (lowest-cost paid test left; must beat the killed OI-pinning).

### 2. **Futures roll / calendar / basis** (the genuinely new universe)
- **Mechanism.** Index futures (ES/NQ/RTY, and commodity/rate futures) are held by roll-driven
  passive/beta capital. At the roll, longs sell the front and buy the back → the front-back basis
  and the last-days roll pressure are *scheduled and mechanical*. Same in commodity rolls
  (roll yield), and in the MOC of futures-roll ETFs.
- **Forced party.** Beta/passive futures holders whose mandate is to stay long a rolling contract;
  they must transact the calendar on the roll schedule.
- **Survival.** Roll windows are crowded but the *cash-settled, continuous* nature and SOQ
  (Special Opening Quotation) settlement leave auction/print distortions.
- **Magnitude.** Roll-yield/calendar effects in commodities are documented and can be multi-%/yr;
  equity-index roll basis is smaller but capacity is enormous.
- **Capacity.** Deepest market there is — hundreds of millions.
- **Data.** Free: CME settlement/volume (CME site), CFTC COT (200 OK verified), exchange
  settlement files; paid: continuous contract history (Databento/Norgate) where needed.
  **Mix of NOT SEARCHED + DATA-LIMITED.**
- **Fast falsification.** Free: build the nearest two contracts' settlement series from CME/Fiscal
  data for ES/NQ (or a commodity), test whether the calendar spread has a scheduled, sign-stable
  move in the last 5 sessions before first-notice/roll; net of 1 tick.
- **Failure mode.** Roll mechanics already arbitraged in ES/NQ; the tradeable effect lives in the
  spread, not the outright, with thin liquidity.
- **Independence.** Entirely different market — the point.
- **Upside if real.** High capacity; a modest bp edge on notional is large dollars.
- **Recommendation: SEARCH** (this is the "have we been in the wrong universe" test).

### 3. Borrow / hard-to-borrow / recall (the cleanest named counterparty)
- **Mechanism.** Short sellers must pay the borrow fee and can be recalled; fee spikes / recalls
  force covering (a forced BUY). Also fully-paid lending lets a long *collect* the fee.
- **Forced party.** Shorts facing a fee spike or recall; they must buy back.
- **Survival.** Lenders are captive (index funds can't recall at will / lend income is free money).
- **Magnitude.** Fee spikes on HTB names are large (10-100%+); recalls cause sharp spikes.
- **Capacity.** Micro/illiquid names — capacity-limited but high per-dollar.
- **Data.** **BLOCKED:** no free borrow-fee/recall history. Proxies: FINRA bi-monthly short interest
  (2020+, free), FTD (cached 2015+), short volume. **DATA-LIMITED.**
- **Fast falsification.** Proxied: SI/ADV spike + a scheduled catalyst → next-session cover pop.
  (DS4 short-interest tilt already DEAD; the *change* + catalyst interaction is untested.)
- **Failure mode.** Proxies are weak; effect is really about *recalls*, which no free feed shows.
- **Recommendation: DATA-LIMITED** (do not proxy-test again without new data).

### 4. Fallen angels / forced credit flows
- **Mechanism.** IG mandates and index funds MUST sell a bond on downgrade to HY (index exit,
  month-end), forcing price pressure that partly reverts.
- **Forced party.** IG index trackers and rating-mandate insurers (NAIC RBC).
- **Survival.** Slow HY capital, thin dealer balance sheets.
- **Magnitude.** 3-6% pressure; partly reverts.
- **Capacity.** Bonds at $1k lots, 1-2% markups → **not retail-executable**; equity leg is a weak link.
- **Data.** No free PIT ratings. **DATA-LIMITED.**
- **Fast falsification.** Requires PIT ratings — a paid vendor. Equity proxy weak.
- **Recommendation: DATA-LIMITED / DEPRIORITIZE** (execution-blocked at $2-25k).

### 5. Margin / forced-deleveraging cascades
- **Mechanism.** Margin calls and vol-target/CTA/risk-parity deleveraging force selling at a
  schedule (e.g. vol-target de-levers after vol spikes).
- **Forced party.** Levered funds, vol-target funds, CTAs.
- **Survival.** Rules are public but timing is noisy.
- **Data.** Triggers (CME margin notices 403; FINRA margin monthly, lagged). Price-proxy versions
  overlap IBS. **DATA-LIMITED.**
- **Fast falsification.** Vol-target deleveraging proxy already TESTED-REJECTED; true triggers need
  notice feeds.
- **Recommendation: DEPRIORITIZE.**

### 6. Benchmark / index rebalances (beyond S&P add/delete)
- **Mechanism.** Passive funds must trade at reconstitution (Russell June, MSCI, S&P); the close
  flow is mechanical.
- **Forced party.** Index trackers.
- **Survival.** Crowded; the effect is in the announcement gap (already dead for S&P) and the
  recon-day auction.
- **Data.** No membership/PIT history free. **DATA-LIMITED.**
- **Recommendation: DEPRIORITIZE** (membership data is the blocker; S&P leg already in-gap).

### 7. Auction / settlement mechanics beyond TAC
- **Mechanism.** SOQ settlement, MOC/MOO imbalance, closing-auction auction-on-close.
- **Status.** Closing-auction imbalance TESTED-REJECTED (paid data); TAC just rejected.
- **Recommendation: DEPRIORITIZE** (thin).

### 8. Per-fund ETF creation/redemption (non-SPY)
- **Mechanism.** The AP arbitrage is cleanest in SPY (dead). A stressed/intl/bond fund with a stale
  NAV matrix may leave a premium/discount.
- **Data.** Needs the per-fund raw-NAV + shares scrape (SSGA xlsx per fund). **DATA-LIMITED.**
- **Magnitude.** small/episodic. **Recommendation: DEPRIORITIZE.**

### 9. Volatility / risk-premium structures (not retail-viable)
- Put-write, iron condors, VIX roll — all TESTED-REJECTED or leverage/insurance, not alpha.
- **Recommendation: KILL** for retail breadth.

---

## The one chosen direction: **FUTURES ROLL / CALENDAR / BASIS**

Why it beats the alternatives on `P(new large scalable alpha) x impact / cost`:
- It is the one candidate that answers the *strategic* question — "have we been searching the
  wrong universe?" — rather than extending the ETF/equity neighbourhood where 800 variants already
  live. Callbacks: #1 signed gamma is a *small* intraday gate; #3/#4/#5 are data-blocked; #6-#9 are
  thin or already dead.
- Capacity is maximal (futures notional), the forced participant is identifiable (beta/passive
  roll), the flow is **scheduled** (roll calendar), and execution is cleaner/lower-friction.
- It can be **falsified cheaply with free data** (CME settlement/volume + CFTC COT) before any
  purchase, satisfying the data-buy rule.
- It is structurally independent of IBS/night/noise.

**Fastest falsification (first experiment next cycle):** build the front/back settlement series for
one liquid complex (start ES/NQ; add a commodity with a known roll premium, e.g. CL or NG) and test
whether the calendar spread has a sign-stable, scheduled move in the roll window, net of 1 tick and
a realistic spread. If ES/NQ are clean (arbitraged), move to commodity/rate rolls where the
"roll return" is a documented risk premium and capacity is still large. If the roll window shows
nothing anywhere after costs, the futures hypothesis is downgraded to DATA-LIMITED (needs
continuous-contract history) — but not before the free CME test.

**Artifact to hunt hardest:** the calendar spread's liquidity (the tradeable instrument is the
spread, not the outright) and the fact that settlement prices are not directly tradable — measure
with spread/bid-ask, not settlement-to-settlement only.
