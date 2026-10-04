# Contest hunt T6: QQQ 0DTE long straddle 09:45 -> 15:50 (Muravyev-Ni intraday side) — DEAD

Pre-registered `round1_prose.md` (8a3935e). Runner `research/sim/contest_options.py` (`fetch6` / `run6`), 930 sessions
2023-01..2026-09, ATM strike nearest the raw 09:45 price, ask at the 09:46 NBBO, bid at the 15:51 NBBO, $0.65/leg.

| | n | return on premium | win | P(mean<=0) | ex-best-5 |
|---|---|---|---|---|---|
| select 2023-24 | 500 | **-8.7%** | | | |
| judge 2025-26 | 430 | **-9.2%** | 30% | 0.99 | -$253/sh total |
Median straddle $3.13/sh ($313/contract): never fits 5% of $2.3k (100% skipped). Judge at $10k: CAGR -25%, maxDD -55%,
P(-30% in 3 months) 13%; at $25k CAGR -50%. The intraday option premium (if any) is far below 0DTE theta + spread.
