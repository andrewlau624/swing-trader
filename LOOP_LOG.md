# LOOP_LOG

Decisions and state for the research loop, newest first. One entry per decision; link the evidence.

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
