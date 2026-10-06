# Study DM — dividend-month clientele premium (Hartzmark-Solomon 2013) (N 834 -> 835)

Status: PRE-REGISTERED 2026-10-05, before any long-minus-benchmark, event-window or sub-period
outcome was read. Runner `research/sim/dividend_month.py` -> `data/research/program/dividend_month_out.txt`;
**one look, no tuning**. Research only — NO DEPLOYMENT.

## N counter note
Highest registered study at registration is Study ACC (N 833 -> 834, commit `85778ca`,
`research/drafts/round1_prose.md:3795`). This study claims **834 -> 835**. No "BSPD"
registration exists anywhere in the tree (grep for BSPD is empty). If a concurrent BSPD study
also claims 834 -> 835, the correct number for this study is **835 -> 836** per the task
instruction, and this note is the flag.

## Question
Hartzmark-Solomon (2013, JF "The Dividend Month Premium") report that stocks predicted to go
ex-dividend in a month earn abnormal returns over that month, attributed to dividend clientele
demand timed to the ex-date, not to payout changes. Does that premium exist in this panel at the
size the program's gate requires?

## Data (free, on disk — verify coverage in-run)
- **Ex-dates**: `data/research/night/dividends.json` — 14,543 rows, fields
  `ex_date, payable_date, record_date, rate, special, foreign, symbol`; `ex_date` range
  2020-04-28 .. 2026-09-23. Regular = `not special and not foreign` (12,099 rows before
  price joins).
- **Price panel**: `data/research/night/panel.pkl` — keys
  `open, high, low, close, volume, vwap, trade_count`; close matrix **1499 sessions x 13,933
  symbols**, 2020-10-01 .. 2026-09-21. These are SIP daily bars fetched with `adjustment="all"`,
  so the close series is **dividend+split adjusted (total-return-like)**. Verified in-run: the
  mean ex-date close-to-close return (11881 matched events) is 13.16bp vs a panel all-day mean of
  12.94bp — i.e. the ex-date dividend drop is already adjusted out, so a close-to-close return is
  the correct total-return measure and does not mechanically penalise payers by the dividend.
- **Coverage caveat (flag)**: the price panel is **2021+ only** (starts 2020-10-01). This is a
  SINGLE REGIME (post-2020 retail/0DTE, tech-led, dip-friendly). No pre-2021, so no
  cross-regime OOS is possible here; the result is within-regime.

## Exact rule (frozen, no tuning)
Monthly cross-section over the panel's session calendar:
1. **Month M** = calendar month; universe decided on data through the last session of M-1.
2. **Liquidity universe U(M)**: symbol present on the last session of M-1 with close >= $5
   AND its trailing 20-session mean dollar volume (`close*volume`, sessions ending at the last
   session of M-1) >= $5,000,000. No lookahead.
3. **Payers P(M)** = symbols with >= 1 regular (non-special, non-foreign) ex-date in month M.
4. **Forward return** `r_i(M) = close[last session of M] / close[last session of M-1] - 1`.
   Requires both endpoints present; missing either endpoint -> symbol excluded.
5. **Long** = P(M) ∩ U(M), equal-weight. **Benchmark** = U(M) \ P(M), equal-weight.
6. **Statistic** `DM(M) = mean(r over Long) - mean(r over Benchmark)` in bp.

## Secondary event-time test
For each regular ex-date event `(sym, T)`:
- `stock_ret = close[T+5]/close[T-5]-1` (position-based +/-5 sessions), requires a full window.
- `market_ret = SPY close[T+5]/close[T-5]-1` (SPY from the panel).
- `abn = stock_ret - market_ret`. Report mean/median/hit and t clustered by ex-date.

## Sub-periods
Chronological halves of the DM months, plus per calendar year. Sign must hold in both halves.

## Costs
Trading the payer basket monthly is one round trip per month = **2 sides**. Report:
- gross;
- net@5bp/side = gross - 10bp;
- net@15bp/side = gross - 30bp;
- 3x cost shock (45bp/side) = gross - 90bp.

## Gates / kill rule (written BEFORE running)
PASS only if ALL hold:
1. Long-minus-benchmark month return **>= 15bp/month net @5bp/side** (headline);
2. **t >= 2** on the monthly DM series (month-clustered);
3. **median > 0** across months;
4. **sign holds in both chronological halves**;
5. **sign holds in the event-time test** (mean abnormal event-window return > 0).

Also report the 15bp/side and 3x nets, hit rate, and ex-top-5-months. **KILL otherwise.** A
pass that is carried by < 5 months or that dies under the 3x cost shock is reported as such and
is not a deployment candidate in any case.

## Falsification
The H-S mechanism predicts a positive payer-minus-nonpayer month return. A negative or
zero net result, a sign flip between halves, or an event-window sign opposite the monthly sign
falsifies it in this panel.

## RESULT (one look, 2026-10-05)

Command: `PYTHONPATH=. .venv/bin/python -m research.sim.dividend_month` ->
`data/research/program/dividend_month_out.txt`. Coverage: panel 1499 sessions x 13,933 symbols
2020-10-01..2026-09-21; 12,002 in-window regular ex-dates; 71 DM months 2020-11..2026-09
(avg 164 longs / 3081 benchmark names).

Monthly long-minus-benchmark, bp/month: **mean +66.8, median +20.1, hit 52%, month-clustered
t +2.51, ex-top-5 +31.2.** Costs: gross +66.8, net@5bp +56.8, net@15bp +36.8, **net@3x(45bp)
-23.2**. Halves: half1 2020-11..2023-09 mean +97.3 (median +82.7, hit 60%); half2
2023-10..2026-09 mean +37.2 (**median -10.4**, hit 44%). Years: 2021 +162.3, 2022 +166.0,
2023 +4.1, 2024 +66.5, 2025 +29.5 (median -19.2), 2026 +17.7 (median -24.8).

Event-time (close T-5 -> close T+5 minus SPY, n=11,797): **mean -6.9bp, median -19.7bp, hit
48%, date-clustered t -0.04, ex-top-5 -9.0.**

Gate: (1) net@5bp >= 15 PASS (+56.8); (2) t >= 2 PASS (+2.51); (3) median > 0 PASS (+20.1);
(4) sign both halves PASS (+97.3 / +37.2); (5) **event-time mean > 0 FAIL (-6.9bp, t -0.04)**.

**VERDICT: KILL.** The only gate that tests the actual H-S mechanism (ex-date-timed clientele
demand) fails: the payer's abnormal return over T-5..T+5 is -6.9bp (t -0.04), the wrong sign and
zero. The monthly spread passes gates 1-4 but is a **size/value tilt, not the ex-date premium**:
the benchmark is 3081 small, just-above-threshold names vs 164 established dividend payers, the
mean (+66.8bp) is carried by 2021-2022 (+162/+166bp) and is ~0 from 2023 on (medians negative in
half2, 2025 and 2026), and it dies at the 3x cost shock (-23.2bp). Within a single regime
(2021+ panel only); no deployment.
