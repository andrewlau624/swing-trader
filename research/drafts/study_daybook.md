# Daybook: reconciliation vs the live noise rule, and the forward shadow (2026-10-04)

BOT #2 candidate: **Systematic Intraday Day Book** — the intraday noise-area breakout run
standalone, vol-targeted, flat nightly. Code: `swingtrader/daybook/` (signal/engine/metrics/shadow).
This file records Phase 1 (reconciliation) and Phase 2 (forward shadow registration).

## Phase 1 — reconciliation

Reference: `research/daily-strategies/noise.py` (its `m1/` data dir was moved, so it was ported
verbatim into `research/sim/daybook_reconcile.py` and run on the same QQQ panel).
Result: per-day corr **0.996**, mean ratio **1.05** (engine +6.23bp vs ref +5.94bp), 16-20/21-26/full.

Attribution of the difference (QQQ, cost 0.5bp/side, max_lev 3.5, target_vol 0.02):

| variant | full CAGR | Sharpe | mean bp | t |
|---|---|---|---|---|
| REF verbatim (`noise.py` defaults: cost **2.0**, maxlev **4.0**) | −1.4% | −0.02 | −0.10 | −0.05 |
| REF live-config (cost **0.5**, maxlev **3.5**) | 14.9% | 1.03 | +5.94 | 3.36 |
| REF + VWAP = (H+L+C)/3 | 15.0% | 1.03 | +5.95 | 3.36 |
| REF + close at the **16:00** bar | 11.7% | 0.84 | +4.81 | 2.75 |
| REF + drop half-days | 14.9% | 1.03 | +5.94 | 3.36 |
| **daybook engine** (was: close 16:00) | 11.2% | 0.80 | +4.65 | 2.59 |
| **daybook engine** (fixed: close 15:59) | 15.8% | 1.08 | +6.23 | 3.51 |

**Findings.** (1) The apparent 2x gap in the first prototype was *not* a rule difference: it was
(a) comparing the engine at cost 1.0bp to a documented number at cost 0.5bp, and (b) the engine
flattening at the **16:00 auction** instead of the live 15:57/15:59 print (−1.1bp/day). Fixed.
(2) VWAP basis (close- vs typical-price) is immaterial (0.01bp). (3) Half-day handling is immaterial.
(4) `noise.py`'s own defaults (cost 2.0, maxlev 4) are **not** the live rule; `config.yaml` /
`executor.py` use cost 0.5 (shadow) and maxlev 3.5. The verbatim defaults make the leg look dead —
this is the single most misleading thing in the reference file.

**Ambiguities (documented, not silently resolved).**
- `noise.py` default `cost_bps=2.0` vs live `NOISE_COST_BPS=0.5`: the live value is used.
- Flatten timing: reference backtest closes at the 15:59 minute; the live executor's `flatten`
  phase is 15:57; the 16:00 auction is **not** used. The engine now defaults to `close_min=389`.
- `noise.py` default `maxlev=4` vs live 3.5: live used.
- `intra.py` drops half-days by "volume after minute 300 > 0"; the engine keeps days with ≥300 bars.

## Phase 2 — forward shadow (no orders)

Module `swingtrader/daybook/shadow.py`, ledger `state/daybook-shadow.jsonl`, scheduled via
`research-shadows.service` (`ExecStart=-... -m swingtrader.daybook.shadow forward`) and
`make daybook-shadow [DATE]` / `make daybook-report`. Registered in `testing.py` REGISTRY
(3 entries, 60-session gate each). Data source = `marketdata.minute_history` (SIP), the same
source the live executor uses.

Three configs shadowed, all no-order:
- **PROD** — production-equivalent noise leg: QQQ 0.5 + SMH 0.5, lookback 14, step 30, vm 1.0,
  target_vol 0.02, max_lev 3.5, close-weighted VWAP, flat 15:59.
- **B** — moderate day book: QQQ/SMH 0.4 each + conviction TQQQ/SOXL 0.25 each (2x on a strong
  first breakout ≥ 0.341σ), same vol/lev/cost. PRIMARY REFERENCE.
- **C** — high risk (research-only): as B, target_vol 0.04, max_lev 7.0. **Not approved for capital.**

Each hypothetical trade records: timestamps, instrument, direction, signal + strength, intended/
observed/assumed-fill entry and exit, gross/net bp, slip, leverage, vol state, exit reason, and an
**unfillable** flag with the next-minute price and the P&L if filled there (`alt_net_bp`). One daily
record per config carries the leveraged net return.

Seeded with the genuinely out-of-sample sessions 2026-09-22..2026-10-02 (design data ended 09-21).

## Historical (post-reconciliation) — `data/research/program/daybook_out.txt`

| config | full CAGR | Sharpe | maxDD | 16-20 | 21-23 | 24-26 |
|---|---|---|---|---|---|---|
| QQQ only (sanity) | 11.0% | 0.78 | −28% | 10.4% | 17.3% | 5.4% |
| A QQQ+SMH | 9.9% | 0.82 | −16% | 7.5% | 17.5% | 6.5% |
| **B moderate** | **26.6%** | **1.24** | **−25%** | 26.6% | 36.4% | 16.4% |
| B at live cost 0.5bp | 30.3% | 1.38 | −24% | 30.3% | 40.5% | 19.8% |
| C high risk | 53.8% | 1.24 | −45% | 54.6% | 79.1% | 29.2% |

## The one question this shadow answers
Not "does the backtest look good" but **does the edge still exist in the current market**, with
attention to the 2024-26 decay. No thresholds changed after seeing forward data; no new signals.
