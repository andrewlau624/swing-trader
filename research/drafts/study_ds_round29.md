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

## DS1: earnings-announcement premium as an overnight sleeve — all three DEAD

Data: the Nasdaq earnings calendar (free), 111,505 rows for 2019-10 .. 2026-09 and 4,944 symbols, plus the SIP daily panel.
108,808 events have clean windows. The unit is the event's return minus SPY's over the same window, net of 2.5bp/side.

| variant | n | mean net excess (median) | 21-23 / 24-26 | gross | NW t | sign-flip | moved-date placebo |
|---|---|---|---|---|---|---|---|
| E1 liquid, close d−1 -> open d+1 | 40,798 | −4.7bp (−3.4) | −9.7 / −8.7 | +0.3bp | −1.95 | 3% | 7% |
| E2 thin ($2-20M ADV), same | 32,792 | −0.9bp (−3.1) | −8.0 / −17.8 | +4.1bp | −1.32 | 10% | 84% |
| E3 liquid, two overnights only | 40,798 | −4.1bp (+3.6) | −5.4 / −12.0 | +5.9bp | −0.33 | 36% | 70% |

- **There is no announcement premium left to harvest at retail costs.** The window grosses +0 to +6bp over SPY in
  2021-26, below one round trip. Only 2020 was positive (+25 to +83bp), which was the post-COVID rebound in exactly
  these names. The published premium (1970s-2000s samples) is not there in the window this book can use.
- The crosses (e) and the book (f) were not run: nothing passed (a)-(d).

## DS4: night picks tilted by FINRA days-to-cover — DEAD

Data: FINRA consolidated short interest (free), 151 settlement dates 2020-06 .. 2026-09, lagged to publication
(settlement + 10 business days). It covers 94% of the 9,546 picks.

| | $2.3k | $10k | $25k |
|---|---|---|---|
| inc, 2.5bp/side | +0.1pp (+$2/yr) | +0.2pp (+$22) | +0.2pp (+$44) |
| halves 21-23 / 24-26 | +0.1 / −0.1 | +0.4 / −0.2 | +0.3 / −0.2 |

NW t 0.14, sign-flip 55%, feature shuffle within the night 42%.
- **The tercile order flips between halves.** By DTC tercile, low / mid / high: 2021-23 earns +0.0 / +15.1 / +18.0bp,
  2024-26 earns +18.7 / +12.2 / +5.0bp.
- DTC is mostly an inverse-volatility proxy (Spearman −0.45 with vol20), so the tilt only moves exposure toward the
  calmer picks.
- This matches AY (the daily short-volume ratio): **short-selling data carries no night-leg information here.**

## Final table

| idea | verdict | %/yr and $/yr at $2.3k / $10k / $25k (V7, 2.5bp/side) | capacity ($100k / $500k) | what live evidence would change it |
|---|---|---|---|---|
| DS5 night ×1.5 on tax-loss / quarter-end nights | **DEAD**: passes the registered 2021-26 bar (t 2.28, matched placebo 99%) but rests on 5 nights (without them −5.5bp) and reverses in 2019-20 (−32bp vs +13bp) | +1.8pp +$42 / +2.2pp +$215 / +2.2pp +$539 (in-sample only) | as the night leg (breaks ~$250k) | the live night log's December nights: at ~10 a year it would take 5+ Decembers. Not worth waiting for |
| DS3 noise leg: no midday entries | **DEAD** (t 0.12; 2024-26 and 2016-20 negative) | +0.4pp +$9 / +$38 / +$95 | QQQ/SMH: none | none |
| DS4 night tilt by days-to-cover | **DEAD** (terciles flip halves, t 0.14) | +0.1pp +$2 / +0.2pp +$22 / +0.2pp +$44 | — | none |
| DS1 E2 earnings premium, thin names | **DEAD** (−0.9bp net, both halves negative) | ~0 to negative | thin names: none at this size | none |
| DS1 E3 earnings premium, overnights only | **DEAD** (−4.1bp net) | negative | — | none |
| DS1 E1 earnings premium, liquid | **DEAD** (−4.7bp net, t −1.95) | negative | — | none |
| DS2 noise leg every 15 minutes | **DEAD** (−4.8pp, t −2.29) | −4.7pp −$109 / −4.8pp −$480 / −4.8pp −$1,203 | — | none: confirms the 30-minute grid |

**What failed, plainly:** all four studies (7 variants) failed. Two were clean nulls (DS1, DS4). One confirmed the
live setting is the better one (DS2). One was a fat-tailed in-sample pass that the only older data reverses (DS5).
Program N is now 752. Two things carry over:
1. The noise leg's 30-minute grid is now tested in both directions (finer, and with midday slots removed).
2. Two more free data sources produce nothing for this book: the earnings calendar and FINRA short interest. With
   the short-volume ratio (AY), the closing imbalance (BD) and the news headlines (add. 12), the night leg has now
   been conditioned on every cheap public event and positioning feed tried, and none adds selection.

**What is left from the 23** (`deep_search_candidates.md`):
- **DS6, the Roth's IBS leg in 2x ETFs.** It is a leverage choice, like the UPRO sleeve, not an edge. It is listed
  for the user.
- **DS14, insider purchases.** Blocked on an SEC User-Agent contact in `.env` (the user's choice).
- **Two engineering items, no N:** DS22, a running live-vs-research pick scorecard, and DS23, Study Y re-run on cross
  returns.
- The rest were dead on the dead-list check before any test.
