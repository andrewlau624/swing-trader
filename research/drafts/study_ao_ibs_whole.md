# Study AO — whole-share drag at $2.3k, and the cheaper-look-alike / fewer-picks levers (Round 17)

`research/drafts/round1_prose.md` Round 17, Study AO (pre-registered before any number).
Code: `research/sim/ibs_whole.py`. Output: `data/research/program/ibs_whole_out.txt`.
N = 642 -> 664 (5 variants). Study R's method: fixed capital per day, whole vs fractional, by size.
Book = night 0.5 + IBS 0.5, no intraday leg, live tilt, weekend x0.5, corr 0.7, name cap 0.10,
whole shares + $150 night probe. Look-alike prices from `panel.pkl` (2020-10+), same-index return
for sizing. **SPLG has no research data**; the SPY->SPLG gain uses SPY/8.5 and is labelled a
sensitivity (included in the `look-alike` row below).

## The drag (fixed capital, CAGR full; gap = variant − fractional, pp/yr)

| size | whole+probe | fractional | gap (tier) | gap (tier_hi) |
|---|---|---|---|---|
| $2,300 | 12.6% | 14.6% | **−2.05** | **−1.52** |
| $10,000 | 14.0% | 14.6% | −0.64 | −0.41 |
| $25,000 | 14.4% | 14.6% | −0.26 | −0.16 |

Confirms Study R ($2k −2.53 at tier). The drag is a $2.3k problem; by $25k it is ~0.2pp.

## Levers (d-vs-base = pp/yr over whole+probe, same size)

| variant | 21-23 / 24-26 CAGR | d-vs-base $2.3k (tier) | d $2.3k (th) | d $25k (tier) |
|---|---|---|---|---|
| IBS top2 (fewer, larger picks) | 8.5 / 18.5 | **+0.63** | +0.59 | +0.55 |
| cheaper look-alike | 7.7 / 19.1 | **+0.48** | +0.46 | +0.01 |
| IBS 1-share probe | 7.5 / 18.3 | +0.00 | +0.00 | +0.00 |
| look-alike + probe | 7.7 / 19.1 | +0.48 | +0.46 | +0.01 |
| **top2 + look-alike (POST-HOC)** | 8.4 / 19.4 | **+1.01** | +0.96 | +0.55 |
| IBS top1 | 5.0 / 16.0 | −2.45 | −2.32 | −2.76 |

## Verdict: REPORT — nothing clears the 2.0pp adopt bar

- The $2.3k drag is ~2.0pp/yr (tier). The registered levers recover at most ~0.6pp each; the
  post-hoc **top2 + look-alike** combination recovers **~1.0pp** at $2.3k — about half the drag —
  and still fails the ≥2.0pp adopt bar. Surfaced as a report, not a switch.
- **IBS top1 is worse** (−2.45pp): the top-3 IBS diversification is worth more than the rounding.
  "Fewer, larger" helps only from 3 -> 2, not to 1.
- **The IBS 1-share probe is inert**: at $2.3k the per-ETF budget is ~$383, so any ETF cheap enough
  for a $150 probe already buys ≥1 share, and the expensive ones (SPY/QQQ ~$600) are above the
  probe cap. (The night leg's probe is the one that fires.)
- The look-alike gain is small at $25k because the drag is already ~0 there.
- $/yr: top2+look +$23 at $2.3k, +$100 at $10k, +$250 at $25k (tier). The honest read: the
  whole-share drag is real but its fix is worth ~$25/yr at today's size; the bigger $ lever is
  growing the account (deposits) and switching on the built conviction trade.

## What would change it

Real QQQM/SPLG trade data and a Schwab fractional-share path for these ETFs. A `daily` option to
run the IBS leg at top_k 2 is cheap to build if the user wants the ~+0.6pp; it is below the bar.
