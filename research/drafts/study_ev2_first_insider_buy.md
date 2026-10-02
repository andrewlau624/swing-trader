# Study EV2 — first insider purchase in 2+ years, next session open -> close: PASS
Pre-registration: round1_prose.md Round 33 (commits faa96e8, renumbered ec9909b to N 760 before the judge because
another session had looked at a variant first, d4a0401). Runner: research/sim/event_runner.py.
Events: an officer/director open-market purchase Form 4 (`insider_buys()`, `X[X.insider]`) at an issuer with no
open-market purchase filing by anyone in the previous 730 days (data start 2020-01, so events start 2022-01);
3,011 events, 1,317 trades at ADV >= $20M, 809 in the book window; ~159/yr on the select half. Track: FREQUENT.
Hold: 1 session (opening cross -> closing cross). Builder: research/sim/events_firstbuy_build.py.

Select half (2022-23): `net per trade +41.8bp  median +20.0bp  hit 53%  t +2.44` (2022 +61.7 / 2023 +15.0bp).
Judge half (2024-26): event net **+31.5bp**, daily-sleeve NW t **+2.54**. Full window: gross +40.5bp (median +28.8),
net +35.5bp at 2.5bp/side; by year 2022 +66.7 / 2023 +20.0 / 2024 +28.3 / 2025 +48.0 / 2026 +14.6bp.
$10k: NW t +3.57, sign-flip 100%, feature placebo 100% (placebo −0.59pp/yr), dDD +2.0pp, P(DD>50%) 0.0%,
**DSR 0.553 (N 760)**, corr with the noise leg +0.03. **Verdict as printed: PASS.**

$/yr if real (V7 + daytime sleeve increment, as printed by the runner):
| cost | $2.3k | $10k | $25k |
|---|---|---|---|
| 2.5bp/side | +6.3pp ($+144) | +7.2pp ($+717) | +7.5pp ($+1,867) |
| tier_hi/side | +3.4pp ($+77) | +3.7pp ($+369) | +3.9pp ($+966) |
Both halves positive at every size and cost. Capacity: one session in $20M+ ADV names, a few per week; fine to ~$250k,
then the cross impact matters (not tested).

Who pays / why it persists: opening-cross sellers and market makers; the later-session buyers are attention-limited
screeners reading "first insider buy in years". A buy that breaks a 2-year silence is a rare, costly signal and is
noticed slowly; one-day, small, manual, so funds can't size into it.

**Caveats (read before acting).**
- **It is a subset of ID3** (all officer/director buys, already in shadow). It is not a new, independent edge: it says
  the ID3 day trade is about 2x stronger (+35bp vs +17bp net) on the "first buy in 2 years" names. The useful form is
  a **weight inside the ID3 shadow**, not a separate book.
- The idea was looked at twice (d4a0401 FAILED t 1.66 with a left-censored rule that counted every 2020-21 buy as a
  "first"); counted as 2 variants in N. DSR 0.553 is the program's best but still < 0.95.
- Same open question as ID3: the live MOO/MOC cost in $20-100M names. At tier_hi costs it still adds +3.7pp at $10k.

## Spec for a shadow (for the next session; no live code built)
- **Event source:** the ID3 shadow's daily Form 4 pull (`swingtrader/daily/insider_shadow.py`), plus a per-issuer
  "last open-market purchase filing date" table built from the Form 345 sets (2020+) and kept up to date from the
  daily pull. Flag an ID3 event as EV2 when the issuer's previous purchase filing (any owner) is >= 730 days before.
- **Daily check time:** same as ID3, weekdays before 09:00 ET (the filing date is the previous calendar day or earlier).
- **Orders:** market-on-open buy at the 09:30 opening cross of the first regular session after the filing date;
  market-on-close sell at the 16:00 closing cross the same session. ADV (20d, $) >= $20M, prior close >= $5.
- **Size:** 10% of equity per name (whole shares), at most 2% of equity at risk per event; when EV2 and plain ID3
  events compete for the sleeve, EV2 names get 2x the plain weight.
- **Kill rule:** after >= 60 scored EV2 trades, a losing mean -> off (fold back into plain ID3).
- **Weekly digest line:** `EV2 first-buy-in-2y: n trades, mean net bp, hit %, t (vs ID3 rest: mean bp)`.

## Post-judge diagnostics (2026-10-02; NOT a new verdict, and the PASS stands as printed)
`research/sim/ev2_diagnostics.py`: every ID3 event 2022-01..2026-03 (ADV >= $20M) tagged with the days since the
issuer's previous open-market purchase by anyone. **These cuts saw the 2024-26 half, so nothing below can be judged on
2024-26 any more: a rule built from them is forward-only (shadow).**
- **EV2 vs the rest of ID3:** +41.8 vs +14.6bp (select), +31.5 vs +17.2bp (judge). Same sign in both halves, but the
  difference is Welch t 1.50 / 1.09 (all: +19.6bp, t 1.84). "About 2x ID3" is likely but **not proven**.
- **Dose-response is not clean:** <7d +14.5, 7-30d -8.7, 30-90d +24.7, 90-180d +5.3, **180-365d +46.4**, 1-2y +23.3,
  >=2y +35.0, none-since-2020 +36.0bp. Roughly "silence > 6 months beats recent", but 730 days is not a special
  threshold.
- **Robust to the market and trimming:** minus SPY open->close +32.3bp (day-t 3.35); trimmed 1/99% +31.8bp (t 3.86).
  **Fragile to the best days:** without the 10 best trades +20.7bp (t 2.37); without the 20 best days (of ~450)
  +13.8bp (day-t 0.81). It is positively skewed: part of the edge is occasional big up days.
- **Buy size is the strongest cut** (also inside the rest of ID3: <$100k +5, $100-500k +17, $500k-1M +23, >= $1M
  +35bp). In EV2: <$100k +19.8, $100-500k +0.7, **$500k-1M +71.9 (sel +119 / jdg +35), >= $1M +101.1 (sel +110 /
  jdg +96)**. EV2 with a buy >= $500k: ~260 trades (~60/yr), ~+90bp net, day-t > 3, both halves positive.
- **Cost:** EV2 gross +40.5bp -> break-even **20.3bp/side**, vs 10.5bp/side for the rest of ID3. That is the practical
  win: ID3's open question is live MOO/MOC cost, and EV2 survives about twice the cost.
- **Small accounts:** median price $66, median ADV $100M; at $2.3k (a $230 slot), 11% of EV2 trades can't buy one share
  (the buyable rest: +33.7bp). No constraint at $10k+. Median 1 EV2 trade a day (90th pct 3, max 10).
- Next step (forward only): log in the ID3 shadow, per trade, the silence days and $ bought, so EV2 and EV2 x big-buy
  get scored on new data. Pre-register "EV2 & buy >= $500k" as a forward-only shadow gate (>= 60 trades), never as a
  backtest.
