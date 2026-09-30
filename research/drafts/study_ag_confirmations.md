# Study AG — confidence and confirmation signals at the breakout minute: DEAD (N 623 -> 624)

Stamp: `round1_prose.md` Round 16 AG (commit 97245a1). Script: `research/sim/conviction_ag.py` (~2 s).
Output: `data/research/program/conviction_ag_out.txt`. Brief: `prompt_conviction_research.md` idea #1.

## Rule (pre-registered)
- Each confirmation is bucketed on the 2016-23 conviction trades.
- A confirmation earns a variant only if net EV per trade is monotone across its buckets in 2016-23. The variant
  drops the worst end bucket, and it is judged on 2024-26 and the full-period bars.
- **Untestable (no data):**
  - NDX-100 breadth: minute bars exist only for 11 ETFs.
  - NQ futures leading QQQ: the repo has no futures data.

## Net EV per trade by bucket (1.5bp/side), 2016-23 → 2024-26
| confirmation | low | mid | high | monotone 2016-23? |
|---|---|---|---|---|
| C1 strength (≥ 0.341; cuts 0.57 / 1.02σ) | +4.1 → +8.0bp | **+34.1** → +15.7 | +17.7 → +25.3 | no |
| C2 SMH/SPY/IWM also outside their band, same way (0 / 1 / 2-3) | +11.4 → +29.3 | **+30.3** → +23.7 | +14.6 → +13.5 | no |
| C3 QQQ volume in the breakout half hour vs 14 days (cuts 1.03 / 1.47) | +14.7 → −5.5 | **+40.6** → +3.9 | +0.6 → **+57.1** | no |
| C4 VIX(d−1) (cuts 14.4 / 20.9) | +2.4 → +22.7 | **+37.5** → +27.7 | +16.0 → **−62.5** | no |
| C5 VIX9D/VIX (cuts 0.90 / 0.98) | +11.4 → +38.5 | **+47.3** → −1.8 | −2.8 → +1.2 | no |
| C6 time (10:00 / 10:30-11:30 / 12:00+) | +17.8 → +3.1 | +19.4 → +47.0 | +20.8 → +26.9 | yes, barely (+1.5bp steps) |

- C1 across **all** first breakouts, including those below the 0.341 threshold (2016-23 quintiles):
  +25 / −7 / −9 / +23 / +21bp.
- The weakest quintile (strength < 0.10) earns as much as the strongest, so strength is not a confidence dial either.
- Only one variant ran, AG6: drop the 10:00 entries, which are 464 trades, 58% of all.
  - Increment: −2.2pp/yr in 2016-20, −4.9pp in 2021-23, −0.0pp in 2024-26.
  - NW t −1.3, placebo 81st pct, DSR 0.00.
  - **DEAD.** It throws away positive-EV trades.

## Reading
- **No confirmation raises EV monotonically.** "Only take the very confident ones" has no measurable handle in the
  data at the breakout minute. The obvious candidates fail: a stronger breakout, other ETFs agreeing, and heavy volume.
- One repeated shape: the middle tercile is best for strength, cross-ETF agreement, volume, VIX and VIX9D/VIX in
  2016-23. That is the same hump Study AF found for predicted magnitude.
- Most of those features are vol proxies (VIX, VIX9D/VIX, rvol, m̂), so this is roughly **one** observation, not five.
  It is post-hoc and it does not hold in 2024-26 for C3 or C5.
- It is logged as a hypothesis only: "the trade works in ordinary vol; skip VIX(d−1) > ~21". The only honest test is
  forward. The live `[conv]` shadow log records each trade's date, so VIX(d−1) can be joined from the Cboe file. After ~60 round trips, compare the top-VIX-tercile trades with
  the rest. No variant is counted for it now.
- Keep the shipped rule unchanged: first breakout, ≥ 0.341σ, 0.5 of equity.

## Money
- AG6 (the only run): −$55 / −$599 / −$2.4k / −$12.0k per yr at $2.3k / $25k / $100k / $500k (tier_hi, 2016-26).
- It is ~$0 in 2024-26.
