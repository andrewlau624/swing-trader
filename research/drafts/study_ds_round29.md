# Round 29 (deep search): DS1-DS5 results

Pre-registration: `round1_prose.md` Round 29 (commit d4df5d1), before any number. Candidates (23, ranked, dead-list
checked): `deep_search_candidates.md`. Script: `research/sim/deep_search.py` (`noise | season | dtc | earn`);
outputs `data/research/program/deep_search_<part>_out.txt`. Program N 745 -> 752. Base book = V7 live today
(`growth.cfg(1.0, 0, 2.48)`, official-cross night returns, raw prices); it reproduces study_everything_on's S0
(37.6% / 39.4% / 39.9% at $2.3k / $10k / $25k, 2.5bp/side).

## DS2 / DS3: the noise leg's decision grid — both DEAD

| variant | $2.3k / $10k / $25k inc (2.5bp) | halves 21-23 / 24-26 | 2016-20 unit inc | NW t | sign-flip | slot placebo |
|---|---|---|---|---|---|---|
| G1 every 15 min | −4.7pp −$109 / −4.8pp −$480 / −4.8pp −$1,203 | −5.5 / −1.3 | −0.75pp | −2.29 | 1% | — |
| G2 no midday entries | +0.4pp +$9 / +$38 / +$95 | +1.3 / **−1.0** | **−0.50pp** | 0.12 | 56% | 92% |

- **The finer grid is clearly worse.** It trades 2.16 times a day vs 1.65 on QQQ, and the earlier entries are
  mostly false breakouts, which reverse before the next slot. It is negative in 8 of 11 years. The live 30-minute grid stands.
- **Skipping midday entries is noise.** It is positive in 2021-22 and negative in 2023-26 and in the 2016-20 holdout.
- Same verdicts at 1.0bp/side noise cost.

## DS5: night leg ×1.5 on tax-loss / window-dressing nights — DEAD (fails the 2019-20 holdout)

The registered 2021-26 bar was met:

| | $2.3k | $10k | $25k |
|---|---|---|---|
| inc, 2.5bp/side | +1.8pp (+$42/yr) | +2.2pp (+$215) | +2.2pp (+$539) |
| inc, tier_hi | +1.1pp (+$24) | +1.3pp (+$131) | +1.3pp (+$329) |
| halves 21-23 / 24-26 (2.5bp) | +0.7 / +2.1 | +0.8 / +2.5 | +0.8 / +2.6 |

NW t +2.28, sign-flip 99%, matched placebo (×1.5 on the same number of random nights per year) 99%, dDD 0,
P(DD>50%) 0%. DSR at N 752: 0.13.

The post-hoc checks (no new variant) say it is not an edge:
- **It rests on five nights.** Seasonal picks average +68.5bp vs +19.5bp on other nights. The five best seasonal
  nights are 2025-12-23 +18%, 2025-12-31 +17%, 2025-06-26 +15%, 2025-12-29 +9% and 2026-09-16 +9% (equal-weight
  picks, 3-5 names). Without them the seasonal mean is **−5.5bp**.
- **The quarter-end part is outliers only.** Median +26.5bp vs +25.8bp on other nights. The December part's median
  is +76bp, so it is the more plausible half, but December 2025 also holds a −44% night.
- **The 2019-20 reconstruction (`night_recon_2020.pkl`, the leg's only pre-2021 history) has the opposite sign.**
  Seasonal nights average −32bp vs +13bp on other nights. All six December 2019 nights are ≤ +2bp. Rule 5 includes
  the holdout where the leg exists, so this fails.
- Verdict: **DEAD**. Do not retest by changing the window (December only, last 5 sessions, ...): that would be the
  search the matched placebo cannot protect against.
