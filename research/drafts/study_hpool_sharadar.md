# Study H-POOL on Sharadar — pooled insider-buy next-session open -> close

**Pre-registration:** the "Study H-POOL" amendment in `research/drafts/round1_prose.md` (~:2759)
and the "Clarification — Study H-POOL, Sharadar data substitution and the SF2 2008 start" (~:3961).
**Status:** the registered one look. Program **N 796, unchanged**. Runner
`research/sim/hpool_sharadar.py`; output `research/sim/hpool_sharadar_out.txt`.

## Verdict

**PASS at `tier`, NOT ROBUST (fails the `tier_hi` stress).** Judged 2008-01-01..2015-12-31 on
delisted-complete Sharadar bars, n = 29,285 trades over 1,988 sessions.

| pass-bar check (tier) | value | result |
|---|---|---|
| (1) mean net > 0, t (day-clustered) >= 2.0 | +21.1bp, t +2.71 | pass |
| (2) mean net > 0 in 2008-10 AND 2011-15 | +37.2bp / +10.6bp | pass |
| (3) n >= 500 | 29,285 | pass |
| robust: (1)+(2) also at `tier_hi` | +11.4bp, t +1.46; halves +27.0 / +1.2bp | **fail** |

The stress cost (`tier_hi`) leaves the effect positive but not distinguishable from zero, so the
result is a PASS, not a robust PASS.

## What was run

- **Events (SF2 `insiders`).** Officer/director (`isdirector=="Y"` or `isofficer=="Y"`)
  Form 4 / RESTATED-4 (`formtype` "4" or "RESTATED - 4") non-derivative code-P acquisitions
  (`transactioncode=="P"`, `securityadcode=="NA"`), summed per (ticker, filing date `fd`). 363,335
  Form-4 code-P rows -> 352,098 non-derivative -> 347,903 usable -> 91,412 officer/director
  (ticker, fd) groups (6,782 issuers). Eligible if ANY of ID1 (>= $10k and 20-session
  ADV$ >= $1M), EV1 (ADV$ >= $20M and another officer/director filing in [fd-5d, fd)), or EV2
  (ADV$ >= $20M and no code-P filing by anyone in the 730d before fd; evaluable only fd >= 2010-01).
- **Ticker-reuse guard.** Dollar-weighted Form 4 price (SF2 `transactionvalue`/shares, else
  shares x price) within 0.67-1.5x the raw close of the session before d. 2,304 groups lost here
  (2,099 had no Sharadar series at all; 2,327 had no bar on d/d-1 or < 20 sessions).
- **Trade.** Buy the raw opening cross of d, sell the raw closing cross of d; d = the first regular
  session strictly after `fd` (<= 7d). One trade per (ticker, d). Raw OHLC from Sharadar
  (`x * closeunadj / close`); ADV$ = 20-session mean of split-invariant close x volume to the
  session before d. Costs `book.cost_bps("tier")`, `"tier_hi"`, and flat 2.5bp/side.
- **Causality.** Every input is dated <= fd (filings) or <= the session before d (prior close, ADV,
  guard, cluster and silence look-backs). The only same-session inputs are volume > 0 on d (2
  dropped) and the inherited |open->close| >= 50% drop (0 dropped).

## Results (2008-01-01..2015-12-31, n 29,285, 1,988 trade dates)

| cost | mean | t (date-cl) | median | hit | ex-top-1% |
|---|---|---|---|---|---|
| gross | +40.2bp | +5.16 | +19.7bp | 53.8% | +24.3bp |
| 2.5bp/side | +35.2bp | +4.52 | +14.7bp | 53.3% | +19.3bp |
| **tier (judged)** | **+21.1bp** | **+2.71** | +2.0bp | 50.4% | +5.4bp |
| tier_hi (stress) | +11.4bp | +1.46 | -6.7bp | 48.5% | -4.4bp |

- **By year (net, tier):** 2008 +38.9, 2009 +33.8, 2010 +37.0, 2011 +17.4, 2012 +21.5, 2013 +8.3,
  2014 +12.0, 2015 -1.8. Halves: 2008-10 +37.2bp (t +2.30), 2011-15 +10.6bp (t +1.45). The effect is
  strong in the crisis years and decays to roughly zero by 2013-15.
- **Subsets (context, no new N):** ID1-only n 29,111 +20.9bp (t +2.72); EV1-only n 2,410 +14.0bp
  (t +1.02); EV2-only n 840 +30.1bp (t +2.89); added by EV1/EV2 only (not ID1) n 174 +51.2bp
  (t +1.33).
- **Placebo** (each trade re-drawn on a random non-event session of its own symbol, 200 draws,
  tier): mean -17.7bp (sd 5.3), the real +21.1bp at the 100th percentile of the draws.
- **DSR at N 796:** per-trade-date daily SR 0.094 vs E[SR] 0.072 -> **DSR 0.842** (T 1,988 dates).
- **Cash sleeve** (0.63 x equity split equally over the session's trades, <= 10% equity and
  <= 1% ADV$ per name, whole shares at the raw open), %/yr and $/yr:

| equity | tier | tier_hi |
|---|---|---|
| $2,300 | +20.2%/yr ($466) | +8.0%/yr ($184) |
| $10,000 | +22.7%/yr ($2,275) | +9.4%/yr ($940) |
| $25,000 | +23.2%/yr ($5,800) | +9.6%/yr ($2,412) |
| $100,000 | +23.4%/yr ($23,350) | +9.7%/yr ($9,694) |

## Mechanism and who pays

The registered mechanism is a short-horizon (one-session, open->close) reaction to clustered,
legally-required disclosure of open-market insider buying by officers/directors. The counterparty is
the early-session liquidity provider/attention-limited buyer: the filing is public before the open,
so the first session's open-to-close captures the immediate order-flow and attention response, and
the liquidity provider on the other side of that response is paid the spread/impact. This is a
disclosure event, not a prediction, and it is concentrated in small/less-liquid names where the
ADV$ thresholds still admit a market impact. Because the trade is intraday and the account is small,
the capacity limit (<= 1% ADV$ per name) is not binding at $2.3-25k.

## Caveats

1. **SF2 starts 2008-01-02**, not 2006q1, so the registered 2006-15 window is truncated to
   2008-2015 and EV2 is evaluable only for fd >= 2010-01 (two years after the data start). The
   pre-registered window is therefore shorter than first written; the clarification anticipated this.
2. **Restated filings.** `formtype` "RESTATED - 4" rows are included; where a filing and its
   restatement share a (ticker, fd) the summed P transactions are combined, so a restatement can
   inflate a group's $ or add a duplicate event (mitigated by the one-trade-per-(ticker, d) rule).
3. **Ticker reuse.** The guard (Form 4 price within 0.67-1.5x the prior raw close) drops 2,304
   groups; residual mismatches from reused ticker strings at the issuer level remain possible but
   are bounded by that guard.
4. **The effect decays and is not `tier_hi`-robust.** Half the tier edge is the 2008-10 crisis
   period; 2013-15 are flat-to-negative. The one look therefore does not support deployable size
   even though the registered bar is met. This mirrors the repo's pattern (TME, night leg): a real
   early-period effect, crowding out toward the end.
5. **One look, no variants.** This is the registered judgment only; no tuning, no size-up, no
   filters were searched after reading. Program N stays 796.
