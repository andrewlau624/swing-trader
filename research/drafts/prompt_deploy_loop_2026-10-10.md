/loop Swing-trader loop (repo /Users/andrewlau/Documents/Code/Projects/swing-trader). Two phases, in order. One item per wake-up, end to end.

READ FIRST each wake-up: CLAUDE.md (priorities, standing permissions, research gate), NEXT.md do-not-redo table, research/drafts/trend_loop_2026-10-10.md (summary: free frontier exhausted, N 930). Log to research/drafts/deploy_loop_<date>.md.

PHASE 1 — DEPLOY THE SMALL VALIDATED ITEMS (Roth-first, whole shares, log-only until the user says "go" on each):
1. PREF-EX + ETDX (Roth): read the live shadow on him (pref_ex_shadow log, 60 ex-nights gate): report fills-vs-cross cost, hit rate, bp/event vs the +38/+44 backtest. If the gate is met, write the live module (MOC/MOC "CC" form, 5% of ex-ante auction $, BIL kept, GFV-safe) behind a config switch defaulting OFF, add the REGISTRY entry and tests in the same commit, and present the switch-on diff. The first real order is user-run.
2. CEF-RV (Roth): read the forward shadow (60 closed trades, >= 10 entry weeks, excess vs EW CEF >= +60bp t >= 2). Refresh the NAV panel from the Mac (make cef-rv-panel) if stale. Report where it stands; if met, same procedure as item 1.
3. Night-leg size-ups within NX (S1 losing-night x2, S2 1.3x cap .15): confirm live auction cost is still ~0bp on all fills since 09-23 (ssh him, logs/), then present the config diff with the measured numbers. User decides.
4. ROTH-STACK ordering (PREF-first over night buys, +2pp) and ETF twins (+0.5-1.7pp): only if items 1-2 are on; present as one config diff with the wash-guard/noise-leg interaction checked.
Rules: never change live config, place orders or buy data without the user's explicit OK per item; read-only on him by default; every switch gets a REGISTRY entry in the same commit; report money at $2.3k / $10k / $25k.

PHASE 2 — RESEARCH (only after phase 1 items are each ON, WAITING or DECLINED):
No free-data variants: the trend/regime, dividend-calendar, loser-bounce, index, roll/basis, options and calendar classes are closed. Work only on: (a) forward-shadow readouts (CROWD-HOLD, BB, ID3, CPC ledger, SPLIT-T0, LETF-NIGHT) against their registered gates; (b) one user-decided data question at a time with the data-buy-rule math written first (deal-break database for BREAK-REV; OPRA signed gamma $180); (c) a new mechanism only if it has a named forced counterparty, a never-inspected history and small-account capacity, pre-registered in round1_prose.md with N bumped, judged once. Same gate as before (>= +10bp/night or stated %/event, clustered t >= 2.5 and above expected-max z, halves, median, ex-top-5, 2x cost, ex-crash, beats leverage).

STOP: phase 1 complete and no phase-2 item is runnable without a user decision -> summarise and stop. Report verdict first, numbers with t, what needs the user.
