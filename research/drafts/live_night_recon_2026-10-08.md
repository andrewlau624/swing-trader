# Live night leg reconciliation (2026-10-08)

Read-only. Fills: server logs/daily-fills-{live,roth}.jsonl; decisions logs/daily-decisions-{live,roth}.jsonl; shadow state/size-shadow.jsonl;
official crosses via `pick_cost_watch.score` on `marketdata.sip_daily` (pick_cost_watch.py:60-67), run on all trips incl. 10-08 sells.

## 1. Shadow +132bp vs realized +8bp: not a bug, three accounting differences
- Shadow = dollar-weighted gross over 8 sessions (09-24..10-06) at $30k: 557.8 / 42,108 = +132.5bp (size_shadow.py:1-20; picks = live decisions, official close -> next open).
- Excluded from the shadow: 09-23 (19 trades, -190bp, -$5.6; no decisions row, shadow began 09-24) and 10-07 (1 trade, -415bp, not yet scored); 09-29 had no taxable picks.
- Same live account, shadow window only (30 trades, 8 sessions): trade-mean +138.6bp, dollar-weighted +43bp; all 50 trades: +8.2bp mean, -12.7bp dollar-weighted. Shadow's own "live" column (the $1k account, same picks) is +63bp.
- Weighting: whole-share rounding at $1k deploys $32 on 09-25 but $2,218 at $30k; at $30k the big winning sessions (09-24, 09-28: ~+290-325bp) carry 31% of dollars; 10-06 (-367bp) is 17%. Session-simple mean is +155bp.
- Shadow counts picks that never filled live: VNET 09-28 and ARCT 10-06 (orders "ended rejected unfilled", MOC; logs daily-live-2026-09-28/10-06). Minor overstatement.
- "net" = gross minus sqrt impact only (0 at these sizes); it is not net of spread.
- Statistically both are one noisy number: trade sd 421bp, SE 59bp (taxable); n=50 over 10 sessions. Backtest expectation ~+22-25bp/trade (config night_impact_edge_bps 22) is inside 1 SE of +8.

## 2. Roth cost check (digest.py:265; gate is only a count, no computed value exists in code)
Fill vs official close (buys) / official open (sells), all 35 Roth trips (2026-09-29..10-08):
- buy: mean 0.0bp, median 0.0 (35/35 within rounding of the close).
- sell: mean -0.13bp (SE 2.8), median 0.0; mean |dev| 6.9bp (noise, symmetric; SIP daily-bar open is not always the 'O' print).
- per side ~ -0.06bp vs 3bp rule: PASS. Keep Roth night on. Taxable same: buy -0.24, sell -1.99 (SE 4.4).
- Roth loss is the bounce, not cost: official close->open mean -107.6bp, median ~-78; net -107.7bp. Executor's own check (executor.py:858-905) said +1.3bp/side, 88% at print.

## 3. Roth vs taxable: different picks, not different fills
- Only 5 overlapping buy dates; 32 Roth vs 12 taxable trades, and almost no common names (SECZ 10-05, 10-07 differ in who held it).
- Cause: roth_first wash-sale blocking (taxable skips names Roth holds, Roth skips taxable loss-sold names; "[wash] roth_first" log lines), the 20d-corr dedup keeps whichever name is most beaten within the allowed set (10-06: Roth kept AEHG/DNA/GRML/TEM; taxable kept TWST/SKHX/SDGR/GRAL), and the Roth has more cash-permitting size (10 picks on 10-06 vs 5; 3x ETFs / SPACs in the Roth set on 10-02).
- Roth skipped 10-05 SECZ and SPCG: "only $470 free for the bot (< $500)" (daily-roth-2026-10-05.log).
- Per-session mean net bp, Roth (n): 09-29 -93 (3), 09-30 +143 (4), 10-01 +64 (2), 10-02 -10 (7), 10-06 -338 (10), 10-07 -81 (9). Taxable: 09-23 -175 (19), 09-24 +326, 09-25 -38, 09-28 +302, 09-30 +182, 10-01 +535, 10-02 +232, 10-05 +73, 10-06 -391, 10-07 -415.
- On shared dates both lose 10-06/10-07; Roth's result is dominated by 10-06 (10 names, -338bp, one correlated selloff day). Effective sample = 6 sessions. Roth trade SD 249, SE 42; dollar-weighted -125bp. Not distinguishable from taxable or from backtest on this n; sizing/whole-share differences are minor.

## 4. Integrity
- Every night buy has a matching sell; qty equal; no unmatched sells, no open night positions, no partials (50 taxable, 35 Roth).
- Two decisions without fill: VNET, ARCT (rejected unfilled MOC). Roth SECZ/SPCG (cash floor).
- Cosmetic issue (known, audit_execution_1002.md): `slippage_bps` is drift vs decision ref, not cost.
