# RH-FADE (2026-11-07, no N; brief called it RETAIL-HERD, distinct from the N 981 RETAIL-HERD scalp): short-fade of Robinhood herding buys — CEILING-KILL

- Paper (Barber-Huang-Odean-Schwarz 2022 JF; SSRN draft Table 11, 2018-05..2020-08, in-sample): 5d AR all -2.94%, **price > $5 -0.85%**,
  mcap < $1B -4.25%, > $1B ~0; ~9 events/day; median event price $8.95. The effect is a sub-$5 / microcap effect.
- Borrow (proxy attention events = top 0.5%/day vol/avg20, CRSP 2018-24 x optionm.borrate): $5+ & < $1B mean 26.6%/yr, median 8.9;
  sub-$5 mean 59, median 23; optionable universe median 1-3%. Fees rose after 2020 (median 5% -> 11-17%). Coverage only 14-23%.
- Ceiling at 0.5x short, 5d holds, 50% capture: $5+ cell -2.0pp (mean fee) / +6.8pp (median) -> below +8pp. Sub-$5 -1.4 / +16.5;
  only a sub-$5 fee <= 25% leaf reaches ~+23pp on paper, and only if the edge survives in low-fee names (Miller says it shrinks).
- No live input: Robinhood popularity API died 2020-08. A live version needs WSB mention counts (YoloStocks free daily 2021+) = new hypothesis.
- **Data-unit rule:** `optionm.borrate.borrowrate` is a DECIMAL fraction/yr (GME 2021-01-22 = 0.94; GC ~0.002-0.006). Repo code that
  treats it as percent (`borrow_xs.py` /100, `pcp_htb.py` >= 10, `wrds_borrate_profile.py` text) needs a unit check.
- Not tested: any return backtest, fee-split leaf, mention-count proxy, puts, sales-herding long, real Schwab locates.
- Files: `research/sim/rh_fade.py`, `data/research/program/rh_fade_out.txt`, round1_prose RETAIL-HERD section.
