# LOOP_LOG

Decisions and state for the research loop, newest first. One entry per decision; link the evidence.

## 2026-10-04 — Next cycle: NX still blocked; OPEX OI-pinning FALSIFIED; frontier probes

**Closed branches (do not reopen):** stable pre-2021 night edge; daily-close proxy; generic intraday-noise variants;
generic options strategies; midpoint options results; night-rule parameter tuning.

**NX: still DATA-LIMITED, not run.** Frozen registration (commit `5be14c74`, N 806->809); the $69 Sharadar purchase
is user-approved but there is **no `SHARADAR_API_KEY` in `.env` and no vendor data on disk** (re-checked this cycle).
No progress fabricated. Day-1 checks run the moment the key exists; then NX runs once on 2003-2015, no tuning. 2016-20
stays exploratory.

**Options-induced underlying flow — cheapest variant TESTED and FALSIFIED.** Pre-reg
`research/drafts/study_A_opex_pin.md`; runner `research/sim/opex_pin.py` (Databento OPRA `statistics`, OI = `stat_type 9`;
prior-close OI is lookahead-free). SPY monthly OPEX 2023-2024 (24 events), max-OI strike within +/-3% of prior close,
trade open->close toward it: **K1 (max-OI) hit 43%, net -8.4bp, t -0.51; K2 (2nd-OI placebo) hit 55%, +19.5bp**.
No attraction, and K1 does not beat the placebo. **OI-concentration / pin variant REJECTED for this window**
(underpowered at 24 events; the 2013-2024 extension ~$110 is not justified by a wrong-sign first look).
**Signed dealer gamma (OI x gamma from IV) remains DATA-TARGET and untested.** Observed OPRA `statistics` cost:
SPY ~$0.37/day, QQQ ~$0.36/day — the reset doc's "credit left ~$4" is stale (pulls to ~$17 succeeded this cycle).

**Other frontier probes:** ETF creation/redemption DATA-LIMITED (no free bulk shares/NAV; iShares page 200 scrapeable,
SSGA `navhist` URL 404). Fallen angels DATA-LIMITED (FRED ICE BofA is aggregate only; no free PIT issuer ratings).
Borrow/HTB BLOCKED. Futures-roll / benchmark-change / auction mechanics NOT SEARCHED.

**Ledger delta:** options OI-pinning TARGET -> REJECTED (the OI variant only); signed gamma still TARGET. Highest-value
next experiment: NX once the key is added; otherwise the free PROMISING threshold-list forced-buy test (daily Nasdaq lists
2007+) ahead of any paid signed-gamma pull.

## 2026-10-04 — Options line closed; execution audit; FRONTIER RESET (contest-hunt session)

**Options: CLOSED.** 12 judged variants dead at executable OPRA NBBO (T1-T7; `research/drafts/study_contest_t*.md`).
**T5L (permanent verdict): DEAD** on untouched 2016-22, liquid names, far-side fills: -3.4% of risk/trade, 5/6 gates
failed; T5's +20% mid-to-mid was a midpoint/liquidity illusion (mid +3.3% vs ~3.7% round-trip spread; residue = short
vol). `research/drafts/study_t5l.md`, registration f667b2f. No T5 variations; options reopen only for induced flows.
**Execution audit:** true live cost ~0bp (130 fills = auction prints); the +65..+240bp was ref->auction drift.
Cleanup item (separate): digest 1.3x re-arm text uses that drift as cost. `research/drafts/audit_execution_1002.md`.
**Frontier reset:** `research/drafts/frontier_reset_2026-10-04.md` (fallen angels, ETF create/redeem, borrow/HTB,
margin cascades, settlement/buy-ins, dealer gamma, other forced flows; every data source queried). Nothing VALIDATED;
PROMISING: threshold-list forced buy (daily lists free 2007+), Treasury auction concession (small). CEF discounts
recorded as a secondary track (CEFConnect weekly NAV 1996+, survivorship unhandled). N = 809. No deployment, no sizing.

## 2026-10-04 — Exact night-rule reconstruction (touched window) + noise audit + OPRA status

Cycle order: exact night OOS, noise-residual audit, execution realism, OPRA frontier. No deployment.

**Exact night leg at 15:40, 2016-2020 (EXPLORATORY — this window is the "touched" one; not the NX judge).**
Script `research/sim/night_exact_pre2021.py` (SIP minute bars, signal-driven candidate fetch; adjusted daily
for the outcome). Exact live signal at 15:40 (day_ret <= -8%, IBS(15:40) < 0.10, $5-2000, vol20>=60%,
ADV>=$10M; buy close, sell next open). Per year (bp/trade): 2016 -2.1, 2017 -23.1, 2018 +15.5, 2019 +91.9,
2020 +76.5. 2016-18 +3.0 (t 0.25, ex-top-5 -6); 2016-19 ex-2020 +26.3 (t 2.57); **after 7.5bp/side 2016-18
-12.0, ex-2020 +11.3 (t 1.10)**. The earlier daily-CLOSE reconstruction (+108bp) was flattering: selecting on
the close is a stronger signal than the 15:40 entry. **Read: consistent with "night edge is a high-vol regime
effect (2019-2020), not a stable edge"; reinforces do-not-size-up. It does NOT settle NX — the decisive judge
remains 2003-2015, delisted-complete (vendor purchase still awaiting OK).**

**Noise residual audit.** `research/sim/noise_audit.py`. The ~13% intraday residual is not a leverage or
omitted-factor artifact (unlevered alpha 10.2%, t 4.29; QQQ beta ~0; long-vol UVXY beta t 7-8), but it is
fragile (near-zero 2016-17, 2019, 2025-26) and cost-dominated: 1.65 fills/day, Sharpe 1.07 at 0.5bp/fill,
0.19 at 2bp, -0.94 at 4bp. **Promoted with a caveat: the book's only factor-independent residual, but viable
only below ~1.5-2bp/fill, so execution is the open question.**

**Execution realism.** Night: close-auction in / open-auction out, 7.5bp/side research, live ~0bp on 34 fills.
Noise: 30-min bar-close fills; edge fits inside ~2bp/fill; no midpoint assumptions.

**OPRA frontier.** Databento OPRA.PILLAR `statistics` (daily open interest, 2013+) + `definition` + `cbbo-1m`.
Cost ~$1.75-1.90/symbol-week for OI (~$180/yr SPY+QQQ); key present. **Status: DATA TARGET.** Next test is a
structural constraint on the UNDERLYING from options positioning (dealer gamma / OI concentration / expiration
flows), not a calls/puts/condor hunt.

**Ledger:** night durability WEAKENED; intraday noise GENUINE-BUT-FRAGILE; dealer positioning TARGET; borrow/HTB
BLOCKED; fallen angels TARGET; ETF creation/redemption TARGET; margin cascades NO DATA.

## 2026-10-04 — Night-leg OOS is the primary question (Study NX)

**Decision (user).** Stop the broad strategy hunt. Resolve whether the exact live night leg survives on untouched,
survivorship-free pre-2016 data before any night-leg size-up or new search direction. Do not deploy or size up the
night leg until NX is complete. Keep the 2006-15 insider study (H-POOL) registered but secondary.

**Why this question.** Three rounds of exploration (methodology meta-analysis, structural/forced-flow scouting,
information-before-price, edge conditioning, Study IN, options T3-T7) found no new large bot-tradable edge.
The night leg contributes materially to the book, both proposed size-ups depend on it, and it has never been judged
on data it was not chosen on (2021-23 and 2024-26 are one regime). Its answer changes the research direction.

**Pre-registration.** `research/drafts/round1_prose.md`, "Study NX" (N 806 -> 809): exact live rule from
config.yaml 2026-10-04, judge 2003-01..2015-12 with subperiods 2003-07 / 2008-09 / 2010-15, tier costs (tier_hi and
2x stress reported), beta-adjusted, ex-best-5-nights, median. Secondary rules NX-S1 (losing-night x2) and NX-S2
(moderate 1.3x + cap .15) judged only if the primary passes. 2016-20 is touched (survivor-only Alpaca run
`research/sim/night_oos_pre2021.py` and the D3 proxy): reported, never judged.

**Data requirements (all needed; plain OHLC is not enough).**
1. Unadjusted daily OHLCV + split/dividend factors (the rule reads raw close >= $5 and raw $ volume).
2. Delisted securities through their last trading day, with a delisting price or return.
3. Permanent security id across ticker changes and ticker reuse.
4. Security type (common / ADR / ETF / ETN / CEF / unit / warrant / preferred): the live universe includes ETFs.
5. Exchange trading calendar.
6. Coverage gate before any outcome: eligible-name counts per year within +/-15% of an independent count.
Known limit: no daily vendor has the official auction prints before ~2016; consolidated open/close stand in, which
is why the judge uses tier costs, not the live ~0bp.

**Vendor evaluation (2026-10-04, vendor pages only; no data pulled, nothing bought).** Notes:
session scratchpad `data/vendors.md`.
- Recommended first: **Sharadar full-history bundle, $69 for 1 month** (sharadar.com personal plan). Delisted from
  Dec 1998 (~15k names), permaticker, security category, ACTIONS with delisting dates/reasons, Mac-native API.
  Gaps: only `closeunadj` is raw (raw O/H/L = field x closeunadj/close, raw volume = volume x close/closeunadj; valid
  only if the ratio is split-only, verify), delisted ETFs (SFP table) unverified, no delisting return.
- Fallback: **Norgate US Stocks Platinum, $346.50 / 6 months** (no monthly). Raw OHLCV, delisted from 1990, typed
  ETFs/ETNs/CEFs incl. delisted. Gaps: Windows-only updater (needs a VM; ARM unconfirmed), no permaticker (delisted
  symbols get a suffix), no delisting return.
- Rejected: CRSP (no individual access), Databento (2018+), Tiingo (delisted EOD ~2015+), EODHD (no permanent id,
  split-adjusted volume, no pre-2018 delisted splits), Massive ($199/mo, delisting events missing),
  QuantConnect (cloud-only unless paid org tier).
- Day-1 checks (any failure -> NX INCONCLUSIVE on that vendor, try the fallback): raw ratio math reproduces known
  raw prices across splits; LEH / WM / BSC / ENE / WCOM / Circuit City present through their last week; per-year
  counts near 5-8k; no phantom holiday bars; type field separates common from ETF/ADR/CEF; delisting price available
  (else score at last close with the NX rule's -100% if no next open).
- Purchase: awaiting the user's OK.

**State of related work (2026-10-04).**
- Methodology: select-half strength predicts the judge half (rank corr ~0.6, shrink ~0.63); the t>=2-in-both-halves
  gate rejects many real small edges; live cost vs auction prints -0.66bp/side (78 fills). Forward test M1 staged,
  uncommitted (`swingtrader/daily/insider_shadow.py`, `events.py`, `testing.py`).
- Study IN (insider gap from the filing): DEAD. The gap is real but happens before a public trader can enter.
- D3 losing-night x2 and M1 "moderate": positive on 2021-26 at live cost, but they depend on the unverified night
  leg. Shadow / NX-secondary only.
- H-POOL (2006-15 insider): registered, blocked on the same delisted-inclusive data (free Yahoo covers 37% < 40% gate).

**NX registration stamp.** Commit `5be14c74df68be34bf2d04a185a0d9ed5a23da41`, 2026-10-04T14:46:25-07:00, before
any Sharadar purchase or 2003-15 data. The NX methodology in `round1_prose.md` is frozen from this commit.
User approved the Sharadar $69/1-month purchase (2026-10-04); the user makes the purchase and adds the key.

## 2026-10-04 — NX not funded (user decision)

**Decision (user).** Do not buy Sharadar ($69): the upside if NX passed (~+4-10pp/yr on size-ups, ~$90-230/yr at
$2.3k) does not justify it, given P(pass) ~0.2-0.3 after the exact 15:40 rule came out ~0 on 2016-18 (touched,
survivor-only). Alpha Vantage was probed as a free substitute and fails (full history is premium; its delisted list
has ~47 names for 2006-09 and none of LEH/WM/BSC/Circuit City).

**Consequences (binding until NX runs on qualifying data).**
- NX stays registered (commit 5be14c7) and UNRUN. Code staged: `research/sim/nx.py` (fetch/validate/run, 13 synthetic
  tests in `tests/test_nx.py`). If qualifying data appears later (university WRDS/CRSP, a vendor), run it as registered.
  Open wording issues to settle in a dated clarification BEFORE any fetch: the delisting gate (per name-year cannot
  reach 20%; per-name reading proposed) and halted-then-resumed names (registered text scores -100%).
- The night leg is **unproven**, not failed. No size-ups (losing-night x2, "moderate"), no parameter changes.
  Evidence on file: exact rule 2016-18 ~0 net, edge concentrated in 2019-20; factor decomposition alpha t 1.5 after
  tech and size exposure (`book_decomp.py`). Whether to keep it at its current weight is the user's call.
- H-POOL (2006-15 insider) stays blocked on the same data.
- The validated components: IBS (OOS 2016-20 on ETF data). Research direction: data-obtainable mechanisms in the
  CLAUDE.md frontier ledger, not more night-leg variants.

## 2026-10-04 Study EF (ETF creation/redemption flow, N 810 -> 813) - REJECTED x3
- Registered `round1_prose.md` (30251ec) before any flow-conditioned return; run once, 2008-26, entry t+1 and t+2 stress.
  Write-up `research/drafts/study_ef.md`; code `research/sim/etf_flow.py`, `etf_flow_data.py`.
- SSGA navhist (27 SPDR funds) matches Alpaca prices. SO date convention (internal evidence): row t = orders at the t-1 close;
  publication lag unknown, t+1 open assumed (unproven).
- H1 BDR weekly LS: -21.9bp/wk net (t -2.9), gross +5bp. H2 JNK/SJNK discount: 15 episodes, -16bp (t -0.1). H3 redemption
  reversal: -31.7bp (t -15), gross -5bp. Decile effects are 4-6bp/day, before the flow is knowable, below cost. No shadow, no sizing.

## 2026-10-04 — Treasury frontier settled: auction concession KILLED, month-end VALIDATED (Study TME)

- **Auction concession (Study TAC, third session, 2016-26): KILLED.** Pre-auction dip real (-29bp/3d, t -4.3) but no
  bounce (-16.5bp, t -2.6); tradable +2.4bp (t 0.9). Do not rerun or vary. Code-quality flag (not fixed, not a reason
  to rerun): bare `except Exception: pass` in `research/sim/tac_treasury.py` around the bid-to-cover tercile split.
- **Month-end duration extension (Study TME, pre-reg 003e176, N 813 -> 814, one look 15:24): VALIDATED (registered
  label).** TLT close(T-3) -> close(T), 2002-08..2015-12, 161 months: net AR +32.3bp/month (median +35.9, t 2.76),
  ex-best-5 +20.8 (t 1.91), 2x cost +28.3, subperiods +23.5 (t 1.58) / +40.4 (t 2.26), 13/14 years positive.
  Identification: TLT > IEF > SHY in proportion to duration; the move sits on T-1 and T with a partial reversal after.
  Refunding months not stronger (against the mechanism). 2016-26 probe same sign. `research/drafts/study_tme.md`.
- **Economics:** +4.2%/yr on deployed capital, capital used ~14% of sessions; $2.3k +$58-96/yr, $10k +$250-417,
  $25k +$625-1,042, $100k +$2.5-4.2k. Capacity effectively unlimited for this account. Small per trade, scalable,
  capital-light; it does not by itself move the book toward 2x at today's balances. No deployment; next step if chosen
  = log-only forward shadow (testing.py entry) and, separately, a pre-registered scaling study (margin over 3 sessions
  in taxable; 2x/3x Treasury ETFs in the Roth).
- **Forward-shadow specs registered, NOT run:** Russell Dec-2026 reconstitution (`shadow_russell_recon.md`; a rule must
  be registered before the ~13 Nov preliminary lists) and signed dealer gamma (`shadow_dealer_gamma.md`, DATA-TARGET,
  free SqueezeMetrics GEX first; distinct from the killed OI-pin study). No paid data bought. REGISTRY entries are
  added when their logging code exists.
- Threshold-list (TL) is the other session's study; status per that session.

## 2026-10-04 — TME-L forward shadow registered; futures frontier memo

- **TME-L** (pre-reg e68391a, N 814 -> 816; runner/registry 774d67d): L2 = TLT 2x on Reg T margin (taxable), L3 = TMF
  (Roth/taxable), L1 = TLT reference; official closing prints; kill/success gates at 24 forward windows (Oct-2028),
  interim at 12. No orders; `make tme-shadow` must be added to the server schedule by the user to log forward.
  Report-only instrument history 2009-26: TMF keeps 2.8x of the TLT window (tracking -9bp, worst window -8.7%,
  maxDD -22.5%); TLT 2x margin keeps only 1.62x (financing ~15bp/window); UBT poor (15bp/side + tracking).
  TME rule stays FROZEN; TME is now an implementation question, not a discovery target.
- **Futures frontier** (`research/drafts/frontier_futures_2026-10-04.md`, web + repo reading, nothing run). Verified
  access facts: Schwab futures need margin approval ($1,500 min); IRA futures need $25k NLV and 125% of initial
  margin; the Schwab Trader API cannot place futures orders; one MES/MNQ is ~$30k/$61k notional (13-26x on $2.3k).
  Futures at this account size are a leverage/tax wrapper, not a new alpha source. Roll, commodity-index roll,
  USO roll, CTA crowding, pre-FOMC, VIX SOQ: dead or decayed (evidence in the memo).
  Ranked next cycle: (1) month-end 60/40 rebalancing spread SPY vs TLT/IEF (Harvey-Mazzoleni-Melone 2025), standalone,
  one look on untouched 2002-15 via ETFs, + the Agg 3pm->4pm (2021-01-14) timing diagnostic; (2) month-end index
  extension in LQD/HYG/TIP/MBB; (3) CFTC hedging pressure; (4) micro /10Y as a TME vehicle (implementation);
  (5) equity-index implied financing (signal only).
