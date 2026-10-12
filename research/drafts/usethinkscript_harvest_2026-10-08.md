# useThinkScript strategy harvest (2026-10-08)

Two read-only crawls of usethinkscript.com: strategy boards (~28 threads read, ~25 snippets) and scans/indicators
(~68 read, ~30 snippets). Everything on the forum is self-reported; the forum itself calls the ToS backtester
unreliable (look-ahead `open[-1]`, impossible fills, repaints, no fees). Only two threads give any P&L (Stoch-IFT 21EMA,
1-min Donchian), both self-reported. Thread ids below are usethinkscript.com/threads/<slug>.<id>/.

## Triage against this repo

### Already judged here (do not re-run as stated)
| forum setup | repo test | verdict |
|---|---|---|
| TTM squeeze fire / Squeeze Pro "fired" (2751, 4021) | F1, W1, C1 | dead / underpowered |
| TMO, MTF TMO cross (1128, 91) | F2, C2, W2 | dead; W2 wrong sign |
| MACD crosses, zero-cross scans, MACD+200EMA (7745, 7944) | F3, F11 | dead |
| Stochastic cross-up < 20, Stoch+DMI (17033) | F4 | dead |
| BB lower re-entry scans, PriceSwing (762) | F5, C3 | dead |
| RSI divergence | F6, W5 | dead |
| ADX trend pullback, PSAR+ADX | F7 | dead |
| NR4/NR7 inside day breakout (94) | F8 | dead (breakouts fade) |
| Explosive BB-bandwidth squeeze, contraction breakout (3840) | F10 | dead |
| Heikin Ashi reversal / first green after reds (22297, 7501) | H5 | dead |
| TD-sequential-style count, selling climax, pocket pivot, island | H1-H4 | dead |
| IBS < 0.2 (13310) | live IBS leg | durable on ETFs; weak 2003-15 |
| Connors RSI(2)+200SMA on SPY (10016, 411) | IBS-family ETF rules (G1, H6, M1-M2, W4) | no indicator variant beats IBS |
| Pullback in uptrend (Connors / 1-ATR / 8-21 buy zone) (22566, 2751) | W4 | dead vs EW ETFs |
| Gap fade / gap fill (14001) | I1-I2 | dead |
| Wheel, PMCC, credit spreads, 0DTE flies (10711, 5026, 19033) | T1-T7 | options search CLOSED |

### Untested, daily-OHLCV, window-shaped (candidates for the combo/window harness)
| # | setup (thread) | rule as stated | natural exit | note |
|---|---|---|---|---|
| U1 | Radge RSI(2) LIMIT entry (791) | close > SMA100, RSI(2) < 10; next day limit buy at close - ATR(10) | next open after first higher close | new = resting limit below market; fill if low <= limit (forum code peeks ahead) |
| U2 | Squeeze depth/duration dose-response (Mobius 8414, Carter 4021) | squeeze index <= -20 ("deep"); claim: ~5 bars beats 2-3, > 20 bars worse; 3-width dot level | histogram fade (light->dark blue) | a falsifiable dose-response claim on the squeeze itself, not tested by F1/W1 |
| U3 | Triple Exhaustion (9001) | SlowK(10,10,3) < 20 AND MACD z(1000) < -1 AND DI+ < 15; buy when the exhaustion state ENDS | opposite exhaustion | state-end trigger (window), 230 replies / 212k views |
| U4 | Stochastic-IFT + 21 EMA pullback (5586) | > SMA200, ADR >= 5%, pulls to EMA21, IFT_Stoch(3,1) 0 -> 100 | IFT rolls back | only self-reported stats: +13.8% / -2.4%, 59% win |
| U5 | Relative-strength pullback (20950) | beat SPY over 30d, then -1% over 10d (v1: beat SPY 5/31/64d, 3 up days) | 3-14 day hold | RS x pullback combo |
| U6 | Wide Ranging Days (9767, Schwager) | TR/ATR10 > 1.6 (book 2); break of the high/low range from WRD-1..WRD+2 | stop-and-reverse | user's daily run: "a sea of red" |
| U7 | Stockbee 4% momentum burst (7478) | +4% close to a new 20d high after range contraction, market uptrend | (none stated; Stockbee uses 3-5 days) | breakout family is dead here (F8/F10); low prior |
| U8 | Market Pulse stage transitions (2668) | VWMA 8>21>34 stack = acceleration, transitions between 4 stages | next stage change | state machine |
| U9 | Elder Impulse colour runs (33) | EMA13 and MACD-hist both rising = green | colour change | single-indicator colour sequence |
| U10 | Ichimoku TK cross above cloud (895, 18291) | Tenkan x Kijun up AND low > max(SpanA, SpanB) | none stated | fully daily-computable |
| U11 | Radge BB breakout weekly (451), Turtle 20/10, SPX 200EMA 57-bar (3321) | trend-following on stocks / one index | band / channel / EMA | trend-state; low prior (breakouts fade; one-index tuned) |

### Intraday-only (no minute stock data in Sharadar; noise leg / book rule apply)
ORB variants (16, 164), VWAP setups (110, 9278), HA All-in-One, 20-EMA 2-bar, DMI+TTM 1m/3m, EMA/TSI/premarket-high
(10866), SuperTrend QQQ intraday (22031), Volume Pressure EA, 3x LETF 5-min, SPX Hypoluxa 10-min (5087).

### Futures / options (closed or off-book at $2-25k)
/ES HalfTrend (9911), /ES Mobius scalp (3330), 1-min Donchian (1447), ASAP SMI, NQ scalps (11000, 1958), value-area
pullback (22491), AGAIG option series (18436...; repaints, no stops), 0DTE / spreads.

## Schwab odd-lot tender fee check (2026-10-08)
Bogleheads t=370780 (Cerner tender, ~2021-22): Schwab charged $39 "voluntary reorganization". Schwab pricing guides:
$39 in Feb-2017 and Oct-2020 retirement guides; **$0 voluntary reorganization from Jan-2023** and in every 2026 guide
found (independent-advisor Jul-2026, retirement/PCRA Apr-2026, Hong Kong Jan-2026). The individual-investor guide was
not in the results: confirm once in the account. Read: the $39 fee does not apply to current CPC tender economics.
