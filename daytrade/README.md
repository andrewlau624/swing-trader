# Day-trading lab

A separate package (`daytrade/`), a separate brokerage account, and its own state (`state/daytrade/`),
recordings (`data/daytrade/`) and logs. It never imports anything that places orders for the live book
(`swingtrader/daily`). It reuses the live code's helpers by import only: `signals.regular_clock`,
`marketdata.trade_date`, `brokers.regular_sessions` and the Schwab login. Brief:
`research/drafts/prompt_daytrade_lab.md`.

## 1. Honest starting point (read this before any strategy)

**Most day traders lose money.** Two large full-population studies:
- **Taiwan.** Barber, Lee, Liu & Odean, "The cross-section of speculator skill: Evidence from day trading",
  *Journal of Financial Markets* 18 (2014), 1-24. They use every day trade on the Taiwan Stock Exchange,
  1992-2006. Fewer than 1% of day traders are predictably profitable net of fees. See also Barber, Lee, Liu,
  Odean & Zhang, "Learning, fast or slow", *Review of Asset Pricing Studies* 10(1) (2020), 61-93: most people
  keep trading after losing, and quitting is the profitable choice for almost all of them.
- **Brazil.** Chague, De-Losso & Giovannetti, "Day Trading for a Living?", SSRN working paper 3423101 (2019).
  They study every individual who day-traded mini-index futures, 2013-2015. Of those who kept going for
  300+ days, 97% lost money. About 1% earned more than the Brazilian minimum wage, and 0.5% more than a bank
  teller's starting salary.

**Daily profit = account size x net profit per trade x trades per day.** At $2-25k, $1,000 a day means
making 4% (at $25k) to 43% (at $2.3k) of the account **every day**. No edge measured in this repo comes
within two orders of magnitude of that. The repo's best intraday edges make cents to tens of dollars a day
at these sizes (table below).

### What each strategy earns per day

`make daytrade-table` (source: `daytrade/table.py`; keep it current, and every strategy adds a row once it
has replay numbers). The model:
- $/day = notional per trade x measured net bp x trades/day.
- Notional is at the full intraday buying power: 4x equity on margin at $2k+ (add. 40). This is an
  **upper bound**; the live legs run at about 0.5-1x.
- A cash account (any account under $2k) uses settled cash only, and a sale settles T+1, so the money turns
  over at most once a day.
- The last column is the account size needed for $1,000/day at that edge, on margin.

| strategy | net bp/trade | trades/day | $2.3k cash | $2.3k margin | $10k | $25k | size for $1k/day | source |
|---|---|---|---|---|---|---|---|---|
| noise leg, QQQ (live book) | +2.0 | 1.00 | $0.46 | $1.84 | $8.00 | $20.00 | $1,250,000 | RESULTS add. 35: plan on ~+2bp/day per unit of equity, 2016-26 (0DTE era +2.2) |
| conviction trade, TQQQ (live book, shadow) | +15.3 | 0.29 | $1.02 | $4.08 | $17.75 | $44.37 | $563,444 | Study AK: +15.3bp/trade at 3bp/side 2016-26 (0s delay; 1-min delay +12.9); ~73 trades/yr |
| gap_vwap_reclaim (lab, Study Lab-AS: DEAD) | -18.9 | 2.78 | -$1.68 | -$1.68 | -$7.30 | -$18.26 | never (edge <= 0) | Study Lab-AS 2022-26 replay at 1x (10bp/side), 1s; lev 0.14 = the risk layer's measured average (0.5% risk per trade). Gross -1.7bp: no edge. At 2x costs -36.1bp |
| orb_in_play (lab, Study Lab-AU1: DEAD) | -23.5 | 2.37 | -$1.92 | -$1.92 | -$8.35 | -$20.89 | never (edge <= 0) | Study Lab-AU 2022-26 at 5bp/side: 19,016 trades; even the optimistic fill bound is ~0 at 5bp and -9bp at 10bp/side. 2.4 trades/day and lev 0.15 as measured under the lab limits (3 slots, 0.5% risk) |
| vwap_trend QQQ (lab, Study Lab-AW1: DEAD) | -9.3 | 1.00 | -$2.14 | -$2.14 | -$9.30 | -$23.25 | never (edge <= 0) | Study Lab-AW 2022-26, per DAY at 0.5bp/side, whole equity: gross +6.7bp/day eaten by 16 switches |
| *illustration only: 10bp x 5 trades* | +10.0 | 5.00 | $2.30 | $46.00 | $200.00 | $500.00 | $50,000 | the brief's illustration, NOT a measured edge |

Measured through the risk layer, Study Lab-AS lost −$1.46/day at $2.3k cash and −$18.23/day at $25k
($2.3k -> $568 over 2022-26). The formula row above reproduces it within ~2%.

The brief's illustration said "$12/day at $2.3k with no margin". That figure turns the cash over 5 times a
day. T+1 settlement allows once, so the honest number is ~$2.30/day.

## 2. Recording market data (running from day one)

`daytrade/recorder.py`, systemd unit `daytrade-recorder` (`make daytrade-persist` on the server).
- Starts 09:20 ET on weekdays and exits on holidays. Sessions come from the exchange's regular-hours
  calendar via `signals.regular_clock`, never a broker clock.
- **09:25 gapper sweep.** Candidates are the live book's cached daily universe (read only) plus Schwab's
  movers lists. A gapper has a premarket gap of >= 3% either way and price >= $5. They are ranked by
  premarket volume, and the **cap is 10** gappers, added to QQQ, SPY, TQQQ, IWM, SMH.
- **What is saved.** Every level-one update from 09:30 to 16:00, plus each symbol's last pre-open row (the
  volume baseline). The format is Parquet, partitioned `data/daytrade/l1/trade_date=YYYY-MM-DD/`, labelled
  by `marketdata.trade_date`. Gaps and reconnects go to `data/daytrade/meta/<date>.json`.
- **Gap rule.** A reconnect, or more than 30s with no message during the session, is logged. A day with a
  gap over 5s or any in-session reconnect is **flagged** and excluded from studies, never patched.
- **Isolation.**
  - It uses its own copy of the Schwab token (`state/daytrade/schwab-token.json`), so it never writes the
    live bot's token file.
  - It places no orders and reads no account.
  - It is capped at 350 MB of RAM and 50% CPU, because the server has 1 GB and the live bot must always win.
- `make daytrade-status` lists the recorded days, clean or flagged. `make daytrade-smoke` is a 20-second
  connectivity check that writes to /tmp.

### What the feeds give (checked 2026-10-01; do not assume more)

| feed | has | lacks |
|---|---|---|
| Schwab streamer `LEVELONE_EQUITIES` (what the recorder uses) | real-time consolidated bid/ask, bid/ask size, last price and size, day volume, quote and trade times, per-field MIC ids | **conflated**: changes only, batched; not every quote or print. Sizes' units are as Schwab sends them (verify on the first recording) |
| Schwab streamer, other services | `CHART_EQUITY` (1-minute bars), `NASDAQ_BOOK` / `NYSE_BOOK` (level 2), screeners | **no time-and-sales service** (TD's `TIMESALE_EQUITY` is not in the Schwab API: schwab-py 1.5.1 has no `timesale` subscription). "Trades" in the recording are last-trade updates; one row can stand for several prints |
| Schwab REST | quote snapshots (incl. premarket last and volume), movers (top 10 per index), price history | no ticks; the movers list is 10 names per index |
| Alpaca free plan, real time | IEX trades and quotes only | IEX is a few % of volume and its quote is not the NBBO (on 2026-09-29 09:30 the IEX "spread" was $44 wide on QQQ). Real-time SIP needs the paid plan |
| Alpaca free plan, history | **SIP minute and daily bars, and SIP tick-level NBBO quotes and trades** (ms timestamps, exchange, conditions), latest 15 minutes withheld. Verified: QQQ 09:30:00-09:30:20 had 13,315 quotes and 5,090 trades on 2026-09-29, and 3,655 / 554 on 2018-03-01 | no imbalance/auction feed (Study AC still needs Databento or Nasdaq) |

**The last row changes the brief's premise.** Minute bars cannot see quote imbalance or trade flow, but
Alpaca's free historical SIP ticks can, back to at least 2018. Study Lab-AT (opening imbalance) was registered to
wait for 40 recorded sessions. It could instead be tested on ~8 years of history now, as a new
pre-registration (a new variant, +1 N). That is the user's call; see NEXT.md.

## 3. Strategies are plug-ins, each with a written plan first

- One file per strategy in `daytrade/strategies/`, one interface (`strategies/base.py`: `on_bar`,
  `on_quote`, `on_trade`, `on_fill`, `on_clock` -> orders).
- A strategy never sizes, never sees the mode, broker or account, and never touches a broker. A test parses
  every strategy file and fails if it does.
- Each strategy has `daytrade/plans/<name>.md`, committed before anything was computed: the idea, why it
  could work, the exact rules, the size and the drop condition.
- Historical runs are studies, pre-registered in `research/drafts/round1_prose.md` (Round 18) and counted in
  the program N: Lab-AS and Lab-AT take N 669 -> 671.
- Every plan change goes in `PLAN_CHANGES.md` as a new variant. Every mistake goes in `MISTAKES.md`.

| strategy | plan | status |
|---|---|---|
| `gap_vwap_reclaim` | plans/gap_vwap_reclaim.md (Study Lab-AS) | **DEAD** (Study Lab-AS, `research/drafts/study_as_gap_vwap.md`): −18.9bp/trade at 1x, t −3.2, gross −1.7bp, placebo 59th pct; never traded on paper |
| `orb_in_play` | plans/orb_in_play.md (Study Lab-AU) | **DEAD**: −23.5bp/trade at 5bp/side (19k trades); the optimistic fill bound grosses only ~+10bp, so −9bp at 10bp/side. Already dead in RESULTS.md |
| `vwap_trend` | plans/vwap_trend.md (Study Lab-AW) | **DEAD**: VWAP side is informative (+6.7bp/day gross, placebo 97th) but 16 switches/day cost 16bp |
| `late_mover` | plans/late_mover.md (Study Lab-AX) | **DEAD**: −33.7bp/trade at 20bp/side; gross +6bp, the move is over by 15:00 |
| `halt_resume` | plans/halt_resume.md (Study Lab-AY) | **DEAD** long: ~−130bp gross per 30 min after a halt either way (a first "pass" was a fill bug); the short side is Lab-BA |
| `open_imbalance` | plans/open_imbalance.md (Study Lab-AT; Lab-AV = the same on historical SIP ticks) | waiting: first look after 40 unflagged recorded sessions (or a new historical pre-registration, above) |

## 4. One engine, three modes

`daytrade/engine.py`. The same strategy objects run in:
- **replay**: recorded seconds (`make daytrade-replay DAY=...`) or SIP minute history (`daytrade/research/`);
- **paper**: the lab's own Alpaca paper account;
- **live**: Schwab, the lab account.

Only `daytrade/runner.py` knows the mode.

**Replay fills** (`daytrade/fills.py`):
- Market orders wait out the latency setting. On quotes they fill at the ask/bid. On minute bars they fill
  at the next minute's open (the closest minute data gets to 1s); 0s and 60s are reported too.
- Limits fill only when the price trades through them, or once the displayed size queued ahead at placement
  has traded.
- Stops fill at the stop, or at the open when a bar gaps through. In the same bar, the stop comes before the
  target.

**Drift report.** In paper and live, every order also goes to a shadow replay broker on the same quotes. The
journal stores both fills, and `make daytrade-review` reports the gap in bp by strategy each week. A
strategy whose real fills drift worse than its edge is dead, whatever replay says.

## 5. Hard risk limits (enforced in the engine, `daytrade/risk.py`)

| limit | default | what happens |
|---|---|---|
| daily loss | 2% of start-of-day lab equity (realised + open) | cancel, flatten, no more entries that day |
| risk per trade | 0.5% of equity, sized from the stop | an entry without a stop, or with the stop on the wrong side, is refused |
| position notional | 1.0x equity per position, 3 positions max, and never above buying power | refused if it rounds to 0 shares |
| adding | never to a losing position; no averaging down | refused |
| entry cutoff | close - 15 min (**15:45**; 12:45 on half days) | refused |
| flat by | close - 5 min (**15:55**; 12:55 on half days), from `regular_clock` | everything is flattened; nothing is held overnight |
| HALT | `state/daytrade/HALT` (`make daytrade-halt`), checked on every event | cancel all at the broker, flatten, stop |
| account | `SCHWAB_DAYTRADE_ACCOUNT_NUMBER`, required for paper and live | refuses to start if unset, or if it matches (even by last 4 digits) the live, Roth or leap account; checked again against the resolved account numbers |
| cash account | any account under $2k, or `DAYTRADE_ACCOUNT_KIND=cash` | settled cash only, sale proceeds settle T+1, no shorts. A good-faith violation cannot happen; modelled the same way in replay |

The tests (`tests/test_daytrade.py`) cover the account guard, every limit, flat-by-close (including half
days), HALT, mode-independence and the fill model.

## 6. Built to learn
- **Journal.** `state/daytrade/journal-<mode>.jsonl` holds every round trip: entry and exit reasons, the
  replay fill beside the real one, the plan, R and a free-text note. `events-<mode>.jsonl` holds every rule
  event.
- **Weekly review.** `make daytrade-review` writes `daytrade/reviews/<date>.md`. Per strategy it gives
  trades, net bp, t, drift, rule events and breaks, and a **drop / continue / change course** decision with
  the reason. The decision is proposed from the plan's drop condition; overrule it in writing.
- `MISTAKES.md` and `PLAN_CHANGES.md`: running logs, dated.

## 7. First experiments
See section 3 and the two plans.

## 8. Paper first, then at most $500

Paper only for now. **No live order is possible** unless all of these hold:
- `DAYTRADE_LIVE=on`;
- a written approval file at `state/daytrade/LIVE_APPROVED`;
- lab capital <= $500 (`DAYTRADE_LIVE_CAPITAL`);
- the account guard passes.

Live is also long-only until a short plan passes paper.

**What would justify a first $500 real-money test** (written 2026-10-01, before any paper results):
1. **Replay.** Net per trade > 0 at **2x costs in both halves**, day-clustered t >= 2.0 at 1x, and the
   placebo beaten at the 95th percentile. This is the plan's pass bar.
2. **Paper.** At least **N = 40 paper round trips**. Why 40: a fill's drift has an SD of roughly 10-20bp on
   these names, so 40 trades pin the mean drift to about +-3-6bp (95%). That is fine enough to tell a drift
   from a 15-30bp edge, and both plans' drop checks run at 40. At ~1 trade a day it also spans 8+ weeks
   of different tape.
3. **Drift.** Mean paper-minus-replay drift < half the replay net edge, and its upper 95% bound < the edge.
4. **Rules.** Zero rule BREAKS in paper: nothing held past 15:55, no order after HALT or flat, no late fill
   left open, no position held at end of data. A limit firing (the daily loss limit, HALT) is the design
   working, not a break.
5. **HALT tested live-safe.** On the lab account with $0 at risk: start the live loop, set HALT, and confirm
   the engine cancels, flattens and refuses new orders. Then one 1-share order, cancelled by HALT before it
   fills.
6. **Account guard proven on the server.** It refuses to start with each other account's number, and
   `make daytrade-status` shows the lab account's last 4 digits.
7. The user approves in writing.

**At $500 the money is tuition, not income.**
- $500 is a cash account: one turn a day.
- Even a 20bp net edge makes $500 x 0.0020 = **$1.00/day**, about $250/yr.
- One bad day at the 2% limit costs $10.
- The test's purpose is to measure real fills and drift, not to earn.

## What does not work yet (plainly)
- **The recorder has not run against Schwab yet.** I could not start it on the server from this session:
  remote writes were blocked. The stream logic is tested against fake messages only. The first real
  morning will show whether Schwab's L1 fields and units match what the code expects.
- **Paper mode has never run.** It needs a second Alpaca paper account (`ALPACA_DAYTRADE_API_KEY` /
  `_SECRET_KEY`) and `SCHWAB_DAYTRADE_ACCOUNT_NUMBER`. Neither exists yet, and the lab account is not
  opened.
- **The live loop polls Schwab REST quotes once a second.** It does not use the stream: Schwab may allow
  only one streamer per login, and the recorder holds it. Bars built from 1s polls are coarser than the
  recording's.
- **Stops and targets in paper and live** are real broker orders (Alpaca stop/limit; Schwab stop/limit).
  The cancel of the other leg after a fill is done by the engine, so there is a race of up to one poll
  (2s) where both legs could fill. A double fill would surface as a rule event and a position the engine
  flattens.
- Study Lab-AT cannot be looked at until 40 clean sessions are recorded (about early December 2026), unless
  it is re-registered on Alpaca's historical SIP ticks.
