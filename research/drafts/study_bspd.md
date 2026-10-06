# Study BSPD: bond-SPDR premium/discount and creation-flow reversion (pre-registration)

Registered 2026-10-05. Program **N 834 -> 835**. One look, no tuning. This file is written
BEFORE the runner is executed on any outcome.

## Motivation / mechanism
In illiquid bond ETFs the authorized-participant creation/redemption arbitrage is slow, so the
fund price can deviate from NAV (premium/discount) and creation/redemption flow may predict
short-horizon reversion. SPY's version was rejected (`research/sim/etc_etf_flow.py`,
`data/research/program/etc_etf_flow_out.txt`); the bond SPDRs were downloaded but NEVER judged
(`research/drafts/study_ef.md:43`). This is the one untested branch of Study EF.

## Data (on disk, free; no purchase)
`data/research/etf_flow/nav_{T}.csv` (NAV, shares outstanding `so`, tna) and `px_{T}.csv`
(open/high/low/close/adjclose/volume), loaded via `research/sim/etf_flow_data.py::load_nav` /
`load_px`. **Premium uses RAW `px.close` / nav; NEVER `adjclose`** (adjusted-close bug documented
at `research/sim/etf_flow.py`/`etc_etf_flow.py:45-68`).

Universe = the 5 bond SPDRs: **JNK, SJNK, SPSB, SPIB, SPLB**. If a fund lacks a NAV file it is
dropped and named in the output. (All 5 NAV+px files are present on disk; per-fund date ranges are
reported, not assumed.)

NAV alignment: on trading day t, `nav_eff(t)` = the latest NAV row with date <= t (forward-fill
over the price calendar). `p_t = px.close_t / nav_eff(t) - 1`. Signal known after close t; entry at
open(t+1). No lookahead.

## Exact rules (fixed)
**H1 — discount reversion.** p_t as above. Each trading day rank the available funds
cross-sectionally by p_t. Bottom quintile = the single most-discounted fund (floor(n/5), n=5 -> 1).
Long that fund at open(t+1), exit at open(t+1+h), h in {1, 5} trading days. Non-overlapping trades
(see below). Report:
- `H1a` market-adjusted: R_fund - R_universe_EW (universe = equal-weight all available funds over
  the same window).
- `H1b` vs top quintile: R_bottom - R_top (top quintile = single most-premium fund).

**H2 — creation flow.** r_t = so_t/so_{t-1} - 1, excluding splits (drop when |r|>0.4 AND
|r * nav_t/nav_{t-1} - 1| < 0.25). Top quintile = single largest creation fund. Long at open(t+1),
exit at open(t+2) (hold 1 trading day). Non-overlapping. Report `H2` market-adjusted
(R_fund - R_universe_EW).

Non-overlap: process candidate signal days chronologically; accept a trade only if its entry index
is strictly after the previous accepted trade's exit index (global, across funds). This makes the
t-stat's observations non-overlapping. t-stat is day-clustered on entry date (`clus_t`); the
Newey-West `nw_t` is reported alongside.

## Costs
Per-side cost c. Scenarios: c = 2bp and c = 5bp. A spread trade (long selected + short
equal-weight universe) has two legs, each with a round trip, so **total round-trip = 4c**. Report:
- `net_1x` (c=2 -> spread cost 8bp), `net_2x` (c=4 -> 16bp), `net_3x` (c=6 -> 24bp).
- Long-only net (one leg, round trip 2c) reported for reference.

## Judge window
Full overlap of NAV+px per fund; pooled window is the union of fund availability (no fund has ever
been judged). Report each fund's range. Also report sub-periods **2008-2015 / 2016-2020 /
2021-2026**, and **both halves** (split at the pooled median entry date).

## Gates / kill rule (fixed before running)
PASS (H1 or H2) only if ALL hold on `net_1x` market-adjusted spread:
1. net_1x >= 2 x round-trip cost, i.e. net >= 2 x (single-fund round trip 2c) = 8bp at c=2bp;
2. day-clustered t >= 2;
3. median > 0;
4. same sign in BOTH halves.
KILL if net_1x <= 0, or t < 2, or events < 30, or sign flips between halves.
Report ex-top-5 always. Gross numbers reported for every rule.

## Verdict definition
A PASS needs the gate above; anything else is KILL. No shadow, no live code either way (research
only). N is not re-used for anything else in this study.

## Program bookkeeping (do not edit here; recorded for the next agent)
Program N 834 -> 835. `round1_prose.md`, `NEXT.md`, `LOOP_LOG.md`, `testing.py` are deliberately
not touched by this study.

---

# RESULT (one look, 2026-10-05). VERDICT: KILL (both H1 and H2).

Command: `PYTHONPATH=. .venv/bin/python -m research.sim.bond_spdr_flow`.
Raw output: `data/research/program/bond_spdr_out.txt`. All 5 NAV+px files present; no fund dropped.
Fund ranges: JNK 2007-12..2026-10, SJNK 2012-04..2026-10, SPSB 2010-01..2026-10,
SPIB 2009-02..2026-10, SPLB 2009-03..2026-10. Pooled 2007-12-04..2026-10-02 (4737 rows).
Two-leg spread cost = 4c (c = per-side bp): net_1x = gross - 8bp, net_2x - 16bp, net_3x - 24bp.

| rule | n | gross spread | net_1x | median | hit | clus_t | ex-top5 | net_2x | net_3x |
|---|---|---|---|---|---|---|---|---|---|
| H1 h=1 mkt-adj (long most-disc, -EW) | 2209 | +0.32bp | **-7.68** | -7.63 | 38.1% | -8.55 | -8.24 | -15.68 | -23.68 |
| H1 h=5 mkt-adj | 736 | -1.54bp | **-9.54** | -7.07 | 45.1% | -2.88 | -12.22 | -17.54 | -25.54 |
| H1 h=1 vs-top | 2209 | +1.39bp | **-6.61** | -7.64 | 44.2% | -4.23 | -7.61 | -14.61 | -22.61 |
| H2 creation-top -EW (1d) | 2197 | -1.25bp | **-9.25** | -8.74 | 34.3% | -11.60 | -9.77 | -17.25 | -25.25 |

Sub-periods (net_1x mean bp, n), H1 h=1 mkt-adj: 2008-15 -8.9 (858) / 2016-20 -7.3 (629) /
2021-26 -6.6 (722). H2: -9.7 / -7.3 / -10.4. Both halves same sign (negative) for every rule.

**The gross market-adjusted spreads are ~0 (+0.32bp, -1.54bp, -1.25bp): the premium/discount and
flow signals carry no reversion at all.** Net is decisively negative and the direction is the
*opposite* of the hypothesis (the most-discounted and highest-creation funds slightly
*underperform* the universe). This fails every prong of the gate: net_1x < 8bp (indeed < 0),
day-clustered t < 2 (strongly negative), median < 0. Not a cost problem — even at zero cost the
gross spread is far below the 8bp bar. Consistent with the SPY result (`etc_etf_flow.py`) and the
EF study: no tradable premium/discount or creation-flow reversion in liquid bond SPDRs. This was
the last untested branch of Study EF; the ETF-flow/premium family is now closed.

Executable %/yr: none (negative before size). No shadow, no code, nothing built.
