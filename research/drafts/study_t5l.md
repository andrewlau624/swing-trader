# Study T5L: the earnings iron fly on liquid large caps, executable prices, untouched 2016-22 — DEAD

Pre-registered `round1_prose.md` (f667b2f, N 805 -> 806), one look. Runner `research/sim/contest_t5l.py`. Events: Nasdaq
calendar 2016-02..2022-12 (91k rows, never inspected), ex-ante liquidity: 20-session $ ADV >= $1B and price >= $20 (the
calendar's market cap is as-of today and was NOT used). T5 structure, every leg at the far side both ends, entry gate:
entry half-spread <= 10% of max loss. 1,762 liquid events, 1,620 priced, 1,304 pass the gate.
(Bug caught before the verdict: the first run imported the T1 split date 2025-01-01, so "judge" included 2023-24; fixed
to the registered 2023-01-01 split and re-run. Verdict is the same either way.)

| | n | far-side return on risk: mean / median | win | P(mean<=0) | ex-best-5 | 2x exit spread | mid-to-mid |
|---|---|---|---|---|---|---|---|
| **judge 2016-22** | 716 | **-3.4% / +3.0%** | 54% | 0.94 | -4.0% | -6.5% | +3.3% |
| selection 2023-26 (seen) | 588 | -4.3% / +3.6% | 53% | 0.95 | -5.1% | -9.1% | +4.5% |
| judge, no entry gate | 800 | -8.0% / +0.8% | 51% | 1.00 | -8.6% | -13.2% | +2.6% |
Judge by year: 2016 -14.8%, 2017 +5.6%, 2018 +0.9%, 2019 +3.9%, 2020 +1.1%, 2021 -3.5%, 2022 -13.3% (4/7 > 0).
Gates failed: mean, bootstrap, ex-best-5, years, cost shock. 3-month at 5% risk/trade: median 0 / -0.7% / -0.9% at
$2.3k / $10k / $25k (most trades do not fit at $2.3k).

**Mechanism (the answer to "does it survive"):** no. T5's +20% of risk mid-to-mid (2023-26, >= $2B) was a liquidity
mirage: it lived in names whose quoted mid is not a price anyone trades at. In liquid large caps the earnings event
premium is close to fairly priced: **mid-to-mid only +3.3% of risk**, against a round trip of ~3.7% of risk in
half-spreads (1.8% in, 1.9% out). What is left is a classic short-vol profile: a positive median (+3%) and a fat left tail
(worst -124% of risk; 2016 and 2022 lose double digits), so the mean is negative. Kill it; options are closed for this account.
