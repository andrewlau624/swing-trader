# Round 16 summary: making the conviction trade better (prompt_conviction_research.md), N 619 -> 642

Studies AF-AK: 25 pre-registered variants, 2 pass (AJ1, AJ2: SHADOW), the rest dead. Money is tier_hi (stressed), mult 2,
2016-26 mean increment x equity, pre-tax, with 2024-26 where it differs. Details in study_af..study_ak.

| rank | idea | verdict | $2.3k | $25k | $100k | $500k | what live evidence would change it |
|---|---|---|---|---|---|---|---|
| 1 | **Turn the built conviction trade on** (TQQQ 0.5, `conviction_mode: auto`; value priced in AI) | built, shadow → switch on per add. 19's gate | +$78 | +$844 | +$3.4k | +$16.9k | ~5 clean intraday days (existing gate). Then the 60-round-trip kill rule: live EV/trade ≤ 0 at 60 trades turns it off |
| 2 | **Trade it in MNQ instead of TQQQ** (AJ1 w .5; AJ2 w .75 later) | **SHADOW**: passes all 5 bars, t 4.3 | keep TQQQ | ~$0 (under 1 contract; keep TQQQ) | +$2.7k (AJ2 +$5.6k) | +$15.9k (AJ2 +$31.5k) | Needs a futures-API broker (Schwab's API cannot trade futures). A 20-session `[conv-mnq]` shadow with slippage ≤ 2bp/side. ≥ 30 live TQQQ round trips first. Equity ≥ $30k |
| 3 | Second breakout after a failed first (AK1) | dead (t 0.9; + in every half) | +$17 | +$189 | +$757 | +$3.8k | A forward log of second-breakout days; revisit only if 2027 data keeps it positive, as a new pre-registration |
| 4 | Faster / streaming decisions (AK latency report) | report | ≤ +$10 | ≤ +$90 | ≤ +$870 | ≤ +$4.4k | Upper bound = recovering the full 1-minute delay cost (2.4bp/trade). Build the L1 recorder only for a tick-level idea |
| 5 | Size by predicted magnitude (AF) | **dead** | −$22 (AF1) | −$240 | −$959 | −$4.8k | None: EV peaks on ordinary days, not loud ones |
| 6 | More weight in TQQQ, 0.75-1.0 (AI1-3) | dead (t 0.5) | +$28 | +$300 | +$1.2k | +$6.0k | Only a lower TQQQ margin rate (it takes the noise leg's margin), i.e. see #2 |
| 7 | Stops / targets / half-off / pullback entry (AH) | dead | +$14 (AH1 stop, best) | +$148 | +$590 | +$2.9k (−$10.6k in 2024-26) | None for targets / pullback. The 1u stop only as tail control if the weight rises |
| 8 | Confirmations: strength, SMH/SPY/IWM agreement, volume, VIX, VIX9D, time (AG) | dead | −$55 | −$599 | −$2.4k | −$12.0k | Forward: join VIX to the `[conv]` log; at ~60 trades compare VIX(d−1) > 21 (the post-hoc middle-vol hump) |
| 9 | More setups: SMH / SPY / IWM on no-TQQQ days (AK2-5) | dead (IWM t −2.7) | −$118 (IWM) | −$1.3k | −$5.1k | −$25.7k | None |
| 10 | Weight 2.0 via MNQ (AI4) | dead: maxDD −36%, P(DD>50%) 38% | +$390 | +$4.2k | +$17.0k | +$84.8k | None at this drawdown |
| — | 0DTE options; NDX breadth; NQ leading QQQ | untested: no data | | | | | 0DTE: ThetaData $80/mo (tick NBBO). Breadth needs minute bars for NDX members; NQ lead needs futures minutes |

Capacity: TQQQ at w 0.5-1.0 is a median 0.8-1.6% (p95 2-4%) of the entry minute's $ volume at $500k (2024-26).
MNQ is 35 contracts at $500k, w 1.0. Neither binds below ~$1M.
Taxable after tax: TQQQ legs × 0.65; MNQ 60/40 (26% blended), e.g. AJ1 $100k +$2.3k AT, $500k +$13.6k AT.
Roth: the conviction trade stays off (add. 31: borderline). No futures in a limited-margin IRA.

## What failed, plainly
- **Magnitude sizing, confidence filters, exits, extra setups and extra TQQQ weight all failed.**
- The trade's EV per trade is highest on ordinary-vol days with ordinary-strength breakouts. Nothing measured at the
  open or at the breakout minute picks the winners better than the shipped rule.
- The shipped rule (first breakout, ≥ 0.341σ, band/VWAP exit, 0.5) is already the best version this data can find.
- The two things that add money do not touch the signal:
  - switching the built trade on;
  - moving it to a cheaper, margin-light, better-taxed wrapper (MNQ). That needs a second broker.
