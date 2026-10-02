# Research prompt: find real improvements the program has NOT looked for (deep search, Round 29+)

You are working in the `swing-trader` repo (research data is on the Mac at `data/research/night/`, gitignored;
the live bot runs on the server). The user's stance, and yours for this session: **anything can be made better.**
Seven hundred tested variants do not mean the bot is optimal. They mean the *obvious* places have been searched.
Your job is to search the non-obvious places, rigorously, and to build what survives.

## Read first (do not skip; most "new" ideas are already dead)
- `CLAUDE.md`: rank by %/yr at $2.3k / $10k / $25k after costs; regular-hours sessions only.
- `NEXT.md`: the top section, and the **whole** "Things already tested — do NOT redo these" table.
- `RESULTS.md`: grep it for any idea before proposing it. NEXT's table has missed dead ideas before (night exit
  time add. 7, gap share / rvol / late selling add. 23, news days add. 12, IBS at the MOC add. 6).
- `research/drafts/overnight_2026-10-01.md`, `study_everything_on.md`, `study_aw_auction_audit.md`,
  `study_round19_summary.md`.
- `research/drafts/round1_prose.md`: the LAST amendment gives the current program trial count N (shared with the
  day-trading lab session; check for a later one before you register).

## Non-negotiable rules (each one exists because the program got it wrong once)
1. **Pre-register before computing**: append a dated amendment to `round1_prose.md` (source, mechanism, who
   pays, variants ≤ 3 per idea, pass bars), commit and push it BEFORE any number. Report DSR at the new N.
2. **Night returns from the official crosses** (`auction_audit.with_rets`, `auction_audit_picks.pkl`), never
   the vendor daily open (Study AW: it overstated the leg by 3.8bp per trade).
3. **Raw prices** for any price filter (`load_sim(raw_price=True)`; add. 30's lookahead bug).
4. **Costs**: judge at 2.5bp/side (the measured costs stressed 2x; live night is ~0bp); report `tier_hi`. Say
   which levers only work at low cost. The night-leg levers do.
5. **Pass bar (SHADOW)**: increment > 0 in both halves (2021-23 / 2024-26; 2016-20 holdout where the leg
   exists); Newey-West t ≥ 2; sign-flip placebo ≥ 95th pct AND a placebo that shuffles *the feature* within the
   day/night (several of this program's "edges" were exposure changes, not selection: BD2, AS2, AU2);
   book maxDD not worse by > 2pp; 5y P(DD>50%) ≤ 5%.
6. **Use the live sizing map** (`growth.cfg`) and judge on the V7 book *and* the Roth cash book at
   $2.3k / $10k / $25k. Apply the size curve (Study Y) when you project dollars.
7. **Anything an LLM judges is tested FORWARD only.** Models remember post-event outcomes before their cutoff
   (Study BC: deepseek-v4-flash knew events through 2025-10 and invented a fabricated one).
8. **Nothing goes live**: a pass becomes a default-off switch with shadow logging, a kill rule, tests and a gate
   in `make review` / the weekly digest. The user flips it.
9. **Money**: the shared Databento credit has ~$9 left. Price any paid data with `metadata.get_cost` first,
   and tell the user, and the lab session (SendMessage), before spending.

## Where to search (areas this program has NOT really examined)
Spend the first part of the session building a ranked list of at least 20 candidates across these areas. Each
needs a source or mechanism, who pays, the dead-list check (RESULTS.md and NEXT), and the data it needs. Then
test the best 3-5.

### A. Execution and timing of what already works (no new signal needed)
- **Decision time vs research time.** Live scans the night leg at 15:40; the research pool uses 15:50 prices. How
  much edge is lost or gained between 15:40 and 15:50? Could a later decision (NYSE accepts offsetting MOC after
  15:50; Nasdaq takes MOC to 15:55) add names that qualify late, or drop ones that recover?
- **The IBS leg's entry/exit plumbing**: the open auction vs the first minute; the cash-IRA settlement
  constraints that cost exposure; whole-share rounding at $2.3k (AO left ~1pp on the table).
- **The noise leg's decision grid** (30-minute slots): finer slots on the same rule; skipping known
  low-information slots. Lab studies showed the latency cost; check whether the slot choice is optimal.
- **Order routing / auction participation** for the Roth and the brokerage (Schwab routes; directed opens).

### B. Capital efficiency (money that sits idle)
- ~60% of overnight equity-nights are idle in the Roth (add. 31). What else can safely use idle cash *without*
  conflicting with IBS/night and inside cash-IRA rules? (V6 is shadow; test what else, not V6 again.)
- The intraday buying power that the noise leg leaves unused on calm days.
- **Multiple formation horizons / cross-sectional ranking**: still on NEXT's untested list.

### C. New, uncorrelated legs that fit $2-25k (whole shares, no shorting in the Roth)
- Look outside equities-overnight: e.g. other assets' auctions or session effects that our data can reach
  (crypto sleeve is on the untested list; ETFs of other asset classes; treasury/commodity ETF reversal at the
  close). Judge each by its correlation with the existing legs (same-bet rule ≥ 0.7) and %/yr at small size.

### D. Sizing and risk (the program has a frontier study; look for what it lacks)
- Cost-aware sizing: size the night leg by its *measured* live cost per name/price bucket (live costs are
  ~0bp now; the leg was sized for 7.5-15bp).
- Per-name sizing by expected edge, combining the tilts that exist (v1 depth/vol, tug-of-war) without
  overfitting (one pre-registered combined weight, not a search).
- Drawdown-aware leverage that does NOT de-risk on noise (add. 37 killed CUSUM/rolling-t; find a rule that
  beats its false-alarm rate).

### E. Data the program has never had (cheap first)
- Free: FINRA short interest (bi-monthly), SEC 13F/Form 4 insider filings (EDGAR), Nasdaq/NYSE halt and IPO
  calendars, earnings calendars (from 8-K item 2.02 timestamps), Cboe indices.
- Paid (ask first): options flow / implied vol (ThetaData ~$80/mo), for the conviction trade's direction.
- The lab's L1 recordings (data/daytrade/...) after they accumulate: book imbalance for the noise leg.

### F. Verification work that can raise real returns
- Replay the live fills from `make review` against the research model day by day (not just costs): are the live
  picks the research picks? (review §1 does this per day; extend it to a running scorecard.)
- Check the size curve (Study Y) with today's auction-corrected returns; it drives every projection.

## Deliverables
- `research/drafts/deep_search_candidates.md`: ≥ 20 candidates with source/mechanism, payer, dead-list check,
  data, expected %/yr at $2.3k / $10k / $25k, and a rank. Commit before any test.
- One pre-registered study per tested idea, with a writeup in `research/drafts/` and a NEXT.md entry (dead
  ideas go in the do-not-redo table).
- For anything that passes: a default-off switch, shadow logging, a kill rule, tests (`make test`), and a gate
  line in the weekly digest (`swingtrader/daily/digest.py` gates()).
- **A final table**: idea | verdict | %/yr and $/yr at $2.3k / $10k / $25k | capacity line | what live evidence
  would change it. Say plainly what failed.
- Commit and push after each study. Merge (never rebase) `origin/main` before pushing: the lab session pushes
  to the same branch.
