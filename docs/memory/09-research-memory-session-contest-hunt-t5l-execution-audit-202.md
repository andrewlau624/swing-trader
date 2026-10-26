# Research memory — session "contest hunt + T5L + execution audit" (2026-10-04, part 4)

### Options hunt: CLOSED for this account (N 791 -> 806)
- 12 judged option variants, every one dead at executable (far-side) NBBO from Databento OPRA cbbo-1m:
  QQQ 0DTE on the noise signal (T1a-c, T2a: -5..-15% of risk/trade, the underlying signal is only +2.6bp/trade in
  2025-26), overnight 1DTE condor/fly (T4: mid-to-mid ~0), intraday 0DTE straddle (T6: -9%), pre-earnings straddle
  (T3: mid +1.5% vs ~20% spread), insider-buy calls (T7: 23% spread at 09:35), short earnings fly (T5, T5L).
  Studies `research/drafts/study_contest_t*.md`, `study_t5l.md`; log `contest_hunt_log.md`.
- **T5 status: DEAD.** Its +20% of risk mid-to-mid (2023-26, >= $2B) was a liquidity mirage. On liquid names
  (20d $ADV >= $1B) judged on untouched 2016-22 with far-side fills (T5L): **-3.4% of risk/trade** (median +3.0%, fat left
  tail; 2016 -15%, 2022 -13%; 4/7 years > 0). In liquid names the earnings premium is ~fairly priced (mid +3.3% of risk)
  and the round trip costs ~3.7% of risk. Do not re-test with filters (news, sector, size): no filter changes the spread.
- Rule for any future options idea: compute mid-to-mid AND far-side on the most liquid names first; a mid-only effect
  in thin chains is a quote artifact, not an edge. Retail cannot capture an option premium smaller than ~2x its spread.
- Data gotchas: the SIP minute matrices (`intra.load`, data/research/night/m1) are DIVIDEND-ADJUSTED (~2% low in 2023):
  option strikes need raw prices. The Nasdaq earnings calendar's marketCap is as-of today (look-ahead): never filter on it.
  Databento credit: ~$4 of $125 left after this session (signal-driven windowed pulls cost cents; month-wide pulls dollars).
- `swingtrader/daily/zero_dte.py` is an uncommitted, untested DRAFT (T1a live mirror); the permission classifier
  blocked editing it further. Not deployed. T1a is a measured loser: do not finish it.

### Execution audit (10-02 and all 130 live fills since 09-23): true cost ~0bp
- Every fill printed exactly at the official SIP auction price. True cost: open auction 0.0bp (n 59), close auction
  -0.2bp (n 57), intraday noise +0.4bp vs mid (n 14). The "~0bp" claim holds.
- `slippage_bps` is NOT cost: it is fill vs a decision-time ref (09:17 broker mark for night sells, prior close for IBS,
  15:40 last trade for MOC buys, the ENTRY price for noise exits), i.e. ref -> auction market drift. `digest.py:256/264`
  feeds that drift (~+43bp) into the "Overnight 1.3x" re-arm text as cost: misleading. Fix list (not done):
  `research/drafts/audit_execution_1002.md`.

### Next unexplored frontier (from `research/drafts/alpha_frontier_2026-10-04.md`)
- No candidate on the forced-flow map promises a LARGE edge at $2-25k; most of the map is already dead or done here.
- Best untested: **closed-end fund discount vs its own history** (Pontiff 1995; Patro-Piccotti-Wu 2017; ~2-5%/yr over
  PCEF after haircut, long-only, Roth-friendly), with arms for CEF December tax-loss selling and CEF rights offerings;
  then the **dividend-month premium** (Hartzmark-Solomon 2013, Roth). Blocker for CEFs: free daily NAV history 2016+.
- Conflicts with the part-3 ledger above, not resolved: that ledger lists fallen angels and ETF creation/redemption as
  TARGETS; the part-4 survey dropped both (dealer markups 1-2% on $1k bonds; no free consolidated ETF NAV history).
  Dealer gamma/OI (part 3, paid OPRA statistics) is a different question from T1-T7 (it predicts the UNDERLYING) and
  remains open.
