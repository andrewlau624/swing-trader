# Plan: open_cross_reversal (Study Lab-BE)

Written 2026-10-01. Only the opening NOII's field availability was inspected (4 days, 09:27:50-09:28:05, 3 symbols).
No return computed. Pre-registration: `research/drafts/round1_prose.md`, Lab Round 29 (2 variants, program N 712 -> 714).
Data: Databento XNAS.ITCH `imbalance`, opening-cross messages 09:27:00-09:28:00 ET, Lab-AZ's universe (~$6).

## The idea
Auction price pressure mostly reverts (Bogousslavsky & Muravyev, JFM 2023, for the close). At the open, a large SELL
imbalance pushes the opening cross below where the stock will trade once the continuous market takes over. Buy IN the
opening cross: a market order sent before 09:30 and directed to Nasdaq joins the cross, as the live book's open sells
already do (`brokers.OPEN_ROUTE`). This pays no spread. Sell at 10:00. Mirror: short in the cross after a large BUY imbalance.

## Exact rules (fixed a priori)
- Universe: Lab-AZ's fixed list (top 100 Nasdaq-listed by Nov-Dec 2021 dollar volume + QQQ, TQQQ).
- At 09:28:00: each name's latest opening-cross message (auction_type O) at or before 09:28:00.
  d = near indicative price / ref price - 1 (0 if near is 0).
- Long: the 5 most negative d among names with side A (sell imbalance) and d < 0.
  Short: the 5 most positive d among names with side B and d > 0.
- Entry: the official opening cross price (SIP regular daily open). Exit: 10:00:00 at the SIP NBBO (sell at the bid /
  cover at the ask).
- Shorts: Rule 201 status carried from the previous day is not modelled (disclosed).
- Variants: Lab-BE1 long + short; Lab-BE2 long only.

## Costs
- 1x: 0.5bp at the cross; the 10:00 NBBO touch + 0.5bp.
- 2x: 1bp at the cross; the touch + half-spread again + 1bp.

## Pass bar, per variant
Mean net per trade > 0 at 2x in BOTH halves (split 2024-06-01), AND day-clustered t >= 2.0 at 1x, AND >= 95th pct of a
random-side placebo (gross open -> 10:00 mid, sign-flipped, same costs), AND the mean without the 20 best trades > 0.

## Lab-BF (2026-10-01; round1_prose.md Lab Round 30)
Lab-BE was untestable: the near price is 0 before 09:28:00. Lab-BF uses the same rule with the decision at 09:28:30,
on the top 28 names + QQQ + TQQQ (the budget), taking the 2 most extreme names per side.
