# Sharadar Phase 0 triage — 2026-10-05

Purpose: run every pre-registered, decision-relevant study that the Sharadar full bundle (delisted-complete,
1998-2026, permaticker ids, SFP ETFs, SF2 insiders, actions/sp500) newly makes possible, before the subscription
is cancelled. Daily bars only: no 15:40/intraday rule is exactly testable; every daily-close proxy is labelled.

Binding rules honoured: CLAUDE.md (validation protocol, failure-mode order, research-priority gate, NX result —
2003-15 is TOUCHED for the night leg, so no night variants/tuning on it); NEXT.md do-not-redo table; the NX
amendment + clarification in `round1_prose.md`.

## Ceiling gate (CLAUDE.md): `events/yr x net edge x deployable share x capture`, at $2.3k / $10k / $25k.
Kill before testing if the $10k ceiling < +8pp/yr under <=50% capture. Diagnosis-only work is exempt.

| # | study | events/yr | net edge | deployable | capture | $10k ceiling | who pays / why it persists | cheapest kill | gate |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **SHAR-IBS** — live IBS leg on untouched 2003-15 SFP ETFs | ~1/day (leg days) | OOS 2016-20 +29.8bp, 2021-26 +21.6bp per trade | 0.5 book (ibs_w) | ~100% | the leg itself (~4-8pp/yr) | sellers into oversold closes; small capacity limit in the user's favour | mean<=0 or day-clustered t<1 on 2003-15 | **RUN** (validation of the durable leg on a never-seen regime) |
| 2 | **SHAR-CRASH** — whole-book crash replay 2000-02 / 2008-09 / 2011 / 2015-16 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | **RUN** (diagnostic; no pass/fail, no tuning, no N) |
| 3 | **H-POOL on Sharadar** — pooled insider-buy open->close, judged 2008-15 (registered N 796; 2006-15 recast on the SF2 2008 start) | ~195/yr select, ~1,400 judged trades | ID1 +18bp / ID3 +16.6bp / EV1 +27.7bp / EV2 ~+2x (select) | 0.45x equity sleeve | <=50% | ID3 +10.5pp, ID1 +14.4pp (select half) | market makers at the open; attention-limited later buyers | mean net<=0 or t<2 on 2008-15 at tier | **RUN** (the window forward shadowing cannot reach) |
| 4 | **SHAR-SURV** — survivorship audit of 2021-26 stock-panel results | n/a | n/a | n/a | n/a | n/a | n/a | n/a | **RUN** (diagnostic; no N) |
| 5 | **SHAR-EVENT** — spin-offs / reverse splits / S&P 500 add-delete | spin-offs ~1.4/yr; rev-split ~? ; SP add/del ~25/yr | spin-offs +?%, rev-split ~$370/yr, SP in the GAP | small | small | fails +8pp | n/a | gap-vs-trade check first | **CONDITIONAL** (only if 1-4 finish and the gap check does not kill it; likely DROP) |

Dropped without a backtest (do-not-redo rows, or fails the gate): generic fundamentals factor mining (not
pre-registered, no mechanism); S&P add/delete (effect in the untradable gap — CLAUDE.md); reverse-split
round-ups and odd-lot tenders (manual/small, already characterised); anything in NEXT.md marked dead.

## Exception to the "already done" list
Kills made only for want of pre-2021 or delisted data are exactly what is new and are eligible: H-POOL
(registered 2006-15, never run — INCONCLUSIVE(data) on Yahoo), the survivorship-limited night tests, and the
IBS pre-2016 window. Everything else in NEXT.md stays dead.

## New data facts that shape the registrations
- `funds` (SFP) daily 1997-12-31..2026-10-05, 15.7M rows; `stocks` (SEP) same span, 45.4M rows; both carry
  `closeunadj` (raw) and split-adjusted `close`. No `closeadj` in the local store.
- ETF first price dates (EQ18): SPY/MDY 1997-12-31, DIA 1998-01-20, XL* 1998-12-22, QQQ 1999-03-10,
  IWM 2000-05-26, SMH 2000-06-05, EFA 2001-08-27, EEM 2003-04-14, XBI 2006-02-06. Effective universe per year
  must be stated; absent ETFs are not candidates.
- `insiders` (SF2) = **2008-01-02 .. 2026-10-05**, 11.6M rows; columns include `formtype` (3/4/5 + RESTATED),
  `transactioncode` (`P` = open-market purchase), `transactionvalue`, `transactiondate`, `date` (filing date),
  `isdirector`, `isofficer`. **No 2006-07 data** -> H-POOL's window must be recast.
- `sp500` has add/delete rows; `actions` has split/delisted/spinoff etc.
- Program N is currently **838** (VT-IBS 836->838). SHAR-IBS is the only new judged rule here -> N 838->839.

## Protocol
Each judged study: pre-register in `round1_prose.md` (done, serially, before any subagent), one look, report both
halves + judge window, 2-3x cost shock, ex-top-5, median/hit rate, day-clustered t, placebo, DSR at program N.
A PASS with no mechanism or carried by <5 events is a NO. Gate on executable raw P&L.

## Orchestration
At most 6 subagents; studies 1-4 in parallel, one each, distinct new files. Each verdict adversarially checked
(data bug, lookahead at the close, survivorship, selection, multiple testing) before acceptance. Sharadar-derived
caches only under `data/research/sharadar_derived/`; never commit/upload/share the vendor data.
