# Live-vs-backtest reconciliation, first run (2026-11-10, recon.py, fb4e88d; weekly timer Sat 07:20 ET)
Gap = backtest - live (+ = live worse); total = pick + fill + residual(sizing + timing), asserted exact. Fills vs official SIP crosses.
- Night (pooled 25 days / 232 trades): pick match 52% (taxable 29%, Roth 62%); fill gap per side ~0 (buy -0.2bp t -0.4, sell
  -0.6 t -0.7): auction fills = the print. Total +4.7bp/night t 0.16, median -1.6, ex-top-5 -47: unresolved, needs ~6+ months.
  Timing term is ONE event (below). Pick mismatch: 43-name universe bug 10-23..11-05, cash exhausted, 0-share rounding,
  dedupe added late Sept, Schwab vs SIP quotes 0.3-1.5pp apart near the -8% / IBS .10 cutoffs.
- IBS: pick match 86/81%, fill gap 0.0bp on 26 fills. Roth +60bp t 2.1 = roth_first wash guard skipping XBI (by design).
- PREF-EX: fill +7.9bp buy / +6.3 sell (two early buys, OPP sells); timing +78bp = the known 10-21..10-28 rejected-sell episode.
- CEF-RV: 2 of 28 rule entries bought; the other 26 were budget/slot skips on the entry session (CORRECTED 2026-11-10, memory 93:
  the "24 missed" was recon reading the next day's re-logged "missed" row over the session's buy-skip; no late NAV, no lookahead).
## Bugs found
- 2026-10-13: the PAPER book ran first, hung ~15 min on a network call, systemd killed the run at TimeoutStartSec=900 -> live
  and Roth never ran the open phase; 11 night positions held a second night (CUE 24.40 open -> sold 20.01). Fixed bb1c8ae:
  real books run first; reconcile/intraday/close sell any prior-day night position with no working order (exit-stranded).
- Cost gate / kill check / review.py compare open sells to sip_daily bar opens with adjustment="all", not the official cross:
  Roth last 50 open sells +7.92bp/side vs bars but -3.93 vs the cross (lever gate 10bp, kill 25bp); dividend adjustment
  misprices ex-div days (~110bp CNXC). NOT changed: it moves a live sizing gate -> user decision.
- marketdata._per_symbol fallback ignored `adjustment` (always "all"); fixed in fb4e88d (batch path already honoured it).
- sel_night.py:244 logs adv from the wrong pick (research SEL-NIGHT adv numbers noisy). review.py replay skips dedupe/prev-close.
Not reconciled: intraday leg (off), T-bills, CEF-RV returns (no closed trip), non-trading days, rule changes since a trade day.
## Follow-ups done 2026-11-10 (user "yes yes")
- Exit-cost gate, kill check, digest and review.py now score against md.official_crosses (SIP auction prints); fills with no
  published cross are left out, never scored against a bar. Last 50 open sells: taxable 0.00bp (bars -0.12), Roth -3.93bp
  UCB +2.55 (bars +7.92 UCB +16.6). No action changes today: taxable already passed the 10bp lever gate, and the Roth is a cash
  account (no leverage); the Roth kill check (25bp) is now far from firing for the right reason.
- CEF-RV SLOT_MIN 500 -> 250 (5 slots in a $2.5k sleeve, same dollars); amendment in round1_prose.md.
