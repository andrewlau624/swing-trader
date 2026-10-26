# Research memory — deploy loop + autonomous run (2026-10-10)

- Live auction cost re-audited on 216 auction fills since 09-23: 213 printed exactly at the official SIP price (night close mean
  -0.04bp, night open +0.60, IBS/T-bill 0.00). S2 night size-up deployed as profile `nx_s2` (night 0.65, IBS 0.5, taxable only;
  user "go" 2026-10-10, armed via DAILY_LIVE_PROFILE on him). S1 losing-night x2 NOT built (~$20-230/yr, recommended against).
- Schwab order endpoint cannot resolve preferreds by symbol (BAC/PRP -> "Could not resolve instrument"); it needs symbol + CUSIP.
  `SchwabAdapter._cusip` attaches it for slash symbols (previewOrder validated). JRI CEF open-cross test: both legs 0.0bp vs the
  official open (AUTO route, pre-open market order). PREF-EX shadow 0/60 forward; Sept backfill CO on-backtest, CC weak (t 0.4).
- **BREAK-REV2 (N 930 -> 931): FAIL, wrong-signed.** CIK-mapped 85 new events: A2 -2.84% median -4.22 hit 32%; pooled 128 <= 0.
  Post-deal-break reversal class CLOSED; do not buy a deal database for it. Program N = 931.
- **CEF-PEER (N 932 -> 933, 2026-10-10): PASS.** CEF-RV excess vs SAME-CATEGORY EW CEF peers (name-regex, delisted included) is
  +114bp/trade t 5.8 (2016-26), median +78, every category positive, 91% of the EW-universe excess retained: fund-specific discount
  reversion, not category rotation. The open CEF-ALPHA question is closed. Deployment still waits on the CEF-RV-FWD forward gate.
- **Ceiling-killed / closed, 2026-10-10 (no N, no backtest):** VIX-inversion long mirror (~12-15 non-overlapping entries/yr x 59bp x
  50% honest capture ~ +4pp at $10k, regime class closed); 13F implied-shares dilution screen on the night leg (selection-conditioning
  on the night leg is a closed class per FUND-STATE; median px $7.7 sample barely overlaps the $5+/$10M leg).
- Digest fix (audit_execution_1002 item 2): the "Overnight 1.3x" re-arm line now shows night open-sell cost vs the OFFICIAL open
  (`sg.night_exit_cost`), not `slippage_bps` drift.
- **NOISE-GATE (N 933 -> 934, 2026-10-11): WEAK.** A realized-intraday-vol > 1y-median gate lifts the intraday leg to Sharpe 0.82 ON
  vs -0.41 OFF over 2016-26, but 2026 is ON 61% of sessions with ON Sharpe -1.78: the leg's 2026 loss is high-vol days that do not
  trend, not calm. Conditioning the noise leg is now a closed class (vol gate tested; do not run a trendiness variant). Leg decision
  for the user: `daytrade_mode: off`, re-arm on a positive 60-session replay.
- **Intraday (noise) leg OFF (user, 2026-10-11)** `daytrade_mode: "off"` (quoted: bare off is YAML False). NOISE-DIAG: 2026 QQQ variance
  ratio 1.02 (vs 1.2-1.5 in 2022-25), first-hour continuation ~0; losses are first-hour and last-90-min entries plus band/VWAP whipsaw;
  hold-to-close already tested (add. 22, fails 2016-23). The leg's fix space is closed: do not propose exit/entry/time-of-day/gate
  variants. Re-arm only on a positive 60-session replay (`research/sim/noise_recent.py`).
- **NOISE-REARM watch (2026-10-11, no N):** `noise_rearm_watch.py` (research-shadows, weekly) applies the accepted re-arm rule
  forward: PROD replay with `replay_instrument(..., lag=30)` on the last 60 sessions; POSITIVE = n >= 30, Sharpe >= 0.5, mean > 0 at
  2bp/fill -> re-arm CANDIDATE for the user, never automatic. First read 07-16..10-09: n 85, mean -12.1bp, Sharpe -4.2: off.
  `replay_instrument` gained `lag` (default 0, unchanged); it reproduces `noise_recent.trades_for(lag=30)` exactly.
- **TME scaling (3x via TMF, Roth), 2026-10-11: CEILING-KILL at honest capture, no N, no backtest.** 12 events/yr x (3 x 32bp)
  x 100% of account x 50% capture = +5.8pp/yr at every size (full capture +11.5pp): below the +8pp gate, and it would displace
  the night leg's cash for 3 sessions a month. The "only open Treasury question" is closed; reopen only with a measured forward
  capture rate for TME itself (none exists: TME was never shadowed).
