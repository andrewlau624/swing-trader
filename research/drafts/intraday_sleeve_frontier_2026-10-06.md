# Intraday sleeve frontier (loop started 2026-10-06)

Objective: a real, executable, high-$-per-trade INTRADAY edge for a ~$2.3k margin account (Schwab Intraday Margin
Buying Power up to ~4x since 2026-07-13; 3x ETFs 75% maintenance; Roth has none). Leverage only after an unlevered edge.

## Starting inventory (what is already dead — do not rerun)
Minute-level, 2022-26 (lab): gap>=4% VWAP reclaim (AS), 5-min ORB on stocks in play (AU, t -16.7), VWAP flip QQQ/TQQQ
(AW, cost-bound), +25% late movers (AX), inferred-halt reopen long (AY) and short (BA), opening L1 imbalance (AV),
Nasdaq closing imbalance (AZ/BB/BC/BD/BG: real +6bp gross, spread-bound), opening-cross imbalance (BE/BF).
Main book: ETF gap-fill / Gao last-half-hour / capitulation / opening-drive fade; stock gap-and-go / gap-down squeeze /
15:30 losers; QQQ 1-15min scalping; big-swing sign prediction (AE); single-stock noise legs; 0DTE straddle (T6).
Live: QQQ+SMH noise leg (fading). Full list with file:line: subagent inventory 2026-10-06 (NEXT.md:1342-1366, RS:603-745).

## Never tested at minute level (the open ground at loop start)
- Rule 201 trigger-day path after the -10% cross (SSR-LIFT was T+2 only).
- Single-stock leveraged-ETF rebalance flow into the close (only index-LETF / Gao-style tests exist; single-stock 2x
  funds on MSTR/COIN/TSLA/NVDA etc. have AUM that is a non-trivial share of the underlying's closing volume).
- Earnings-day post-open drift with an official calendar (ORB-in-play covered it only loosely).
- Official halt codes / reopening-auction prints (halts were inferred from minute silence).
- NYSE/Arca imbalance; post-closing-print drift.

## Checked and left dead (old test DID cover the mechanism)
- S&P 500 add/delete effective-date close flow incl. deletion overnight reversal (RESULTS Q1 S3-S5: dead, outliers).
- Earnings-day intraday continuation: the gap>=4% VWAP (AS) and ORB-in-play (AU) universes are dominated by earnings
  gappers; both dead at minute level. An official calendar would not change the trade.

- PREF/ETDX ex-day intraday leg (descriptive, no N): open->close on the ex-date is -9.7bp (pref) / -6.2bp (etdx), day t
  -4.4/-4.0: the CO exit at the open is right; the short mirror is far inside the 38-88bp quoted spread. No intraday add-on.

## Frontier
### ACTIVE
(none — free-data ground exhausted; see verdict below)
- **SPREAD-PREF (queued, ceiling check first)** — passive two-sided liquidity provision in thin $25-par preferreds / baby
  bonds (quoted spreads 38-88bp, retail-dominated, PXB showed passive bids fill ~25% with mild adverse selection).
  Who pays: impatient retail crossing the spread. Needs Alpaca historical NBBO + trades (free, 2018+). Small-capacity
  by nature = small-account advantage.
### PROMISING
### OOS
### EXECUTION
### CAPITAL-EFFICIENCY
### DATA-BLOCKED
### KILLED (this loop)
- **SSR-TD (N 876)** — long after the intraday -10% cross: +3.4bp/EW-day t 0.43, H2 negative, discontinuity at -10% is
  the WRONG sign (-10.9bp t -9.7). Rule 201 creates no bounce. Generic +20-27bp gross at +30/60m after any -8..-12% cross
  ~= one round trip. Side finding -> GAP-SHORT (gap-downs >= 10% keep falling all day, -89bp/EW-day long, 2021-26).
- **GAP-SHORT (N 878)** — short >=10% gap-downs 09:31 -> close. Sealed 2016-20 liquid: +61bp/EW-day t 2.45 (< 2.5 bar);
  2021-26 liquid -8bp t -0.37; squeeze tail (worst -58%/-212%). Regime pattern, not an edge.
- **BTC-FIX (N 879)** — spot-BTC ETF NAV window 15-16 ET: no added window volatility post-launch; fade +0.2bp; flow-proxy
  wrong sign; |edge| < round trip. Absorbed.
- **SS-LETF (N 877)** — mechanism CONFIRMED (I x r_pre t 3.11; placebo diff +5.9bp t 2.82) but only +3-5bp gross from
  15:45; trade -6.6bp net. Real forced flow, priced in before a retail entry can act.
- **SQZ (N 881)** — long gap-ups in HIGH days-to-cover names: -19bp/EW-day; covering is real (HIGH-LOW +83bp t 3.4)
  but not enough to make the long pay. Branch -> GUF-LOW.
- **GUF-LOW (N 882)** — short low-DTC gap-ups: discovery 2021-26 short ~+63bp/EW-day; untouched 2018-20 -18bp t -0.43,
  liquid -65bp, LOW-HIGH flat. Retail-era pattern. (FINRA key-less SI starts 2018.)
- **PREF-DIP (N 880)** — 1% dip bids in thin preferreds, exit close: -7.5bp/fill, halves negative; a real PFF hedge does
  not help (corr 0.28). Idiosyncratic dips revert only vs a close-to-close benchmark that is not executable.
- **LIQ-CASC (N 883)** — fade BTC/ETH perp liquidation cascades (OI -3% & px -1.5% in 15m): -14 / -20bp at 60m, worse
  than plain drops. Cascades continue.
- Pre-FOMC day-session drift: already dead (add. 33) — not re-run.
- **ETF-THIN (N 884)** — bids 0.5% below hedged fair value in 433 thin benchmark-tracking ETFs: -22bp/fill hedged,
  every year negative. Thin ETFs are quoted tight to FV; the fills that do happen are informed.
- **NEWS-DRIFT (N 885)** — continuation after in-session single-symbol headlines (>= 1% first-5-min move): -12.6bp
  net at +60m, gross ~+7bp; news absorbed within ~5 minutes.
- **Capital-efficiency check, SSR-LIFT (existing forward shadow):** cannot be levered — squeeze tail maxDD -41% already
  at 0.5x (region ledger); 4x intraday buying power would turn it into a ruin bet.

## Mid-loop synthesis (after 10 studies, 2026-10-06)
Every intraday mechanism tested so far ended in one of three ways:
1. **Absent / wrong sign** — SSR trigger bounce (D -10.9bp t -9.7), liquidation-cascade fade, BTC fixing window.
2. **Regime-bound to 2021-26** — gap-down short (2016-20 t 2.45 but 2021-26 liquid -8bp), low-DTC gap-up short (2021-26
   short ~+63bp/day, untouched 2018-20 -18bp). The retail/meme era manufactures strong-looking stock patterns that do not
   exist before it; every stock-level finding must be judged on pre-2021 minute data.
3. **Real but smaller than one round trip** — single-stock LETF close flow (t 3.1, +3-5bp), short covering (+83bp
   HIGH-LOW but long still negative), preferred dip reversion (idiosyncratic only, unhedgeable).
No candidate has produced >= +15bp net per trade with stability. The binding constraint is consistent with the program's
history: US equity intraday at minute tier is efficiently arbitraged at retail cost; forced flows that are visible in free
data are priced before a retail entry can act. Remaining free-data ground is thin (official halt codes, NYSE imbalance not
free); paid ground (signed gamma, borrow) is a user decision.

## Loop verdict (2026-10-06, after 11 pre-registered studies, N 876-885 + descriptive checks)
**No high-conviction, high-dollar intraday sleeve exists in the data this program can reach for free.** Every free-data
mechanism class on the brief's list now has a minute-tier test (this loop or the prior lab/main-book work): auctions,
imbalance, SSR, halts, gaps, short covering, LETF/ETF flows, ETF fixing, thin-instrument liquidity provision, crypto
liquidation, news, FOMC, index events. Best real effect found: single-stock LETF close flow (+3-5bp, t 3.1) — real, but
an order of magnitude below the +15bp/trade a $2.3k sleeve needs. Leverage cannot help: the only intraday edges with a
positive mean (SSR-LIFT) carry squeeze tails that make 2-4x a ruin bet.

Remaining ground needs user decisions, not more loops:
1. **Signed dealer gamma** (OPRA OI ~$180/yr) — options-induced underlying flow; prior lowered by OI-pin and COTX/VTS kills.
2. **NYSE/Arca closing-imbalance feed** (paid) — Nasdaq imbalance was real (+6bp) but spread-bound; NYSE unlikely larger.
3. **Borrow-fee / HTB history** (paid) — would make the shortable side of gap/squeeze patterns testable.
4. **New market access** — a futures account (MES/MNQ intraday margin ~$50-$500) is the only route to cheap intraday
   leverage on index moves; the edge question is unchanged (QQQ noise leg already harvests the index-momentum residual).
