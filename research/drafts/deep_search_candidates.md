# Deep search (Round 29+): ranked candidates, built BEFORE any test

Brief: `prompt_deep_search.md`. Program N at the start: **745** (round1_prose.md, Lab Round 51).
Dead-list check = grep of RESULTS.md + NEXT.md's do-not-redo table + `max_edge_candidates.md` (Round 19's 44).
%/yr figures are **priors** (from the mechanism's published size or the nearest tested relative, at 2.5bp/side,
V7 taxable or the Roth cash book), not results. "—" = no defensible prior.

Data probes done for this list (2026-10-02, no returns looked at):
- Nasdaq earnings calendar (`api.nasdaq.com/api/calendar/earnings?date=`): free, historical dates and EPS surprise,
  **but `time` is "time-not-supplied" in history** (no before-open / after-close flag). A test must hold across
  both candidate nights (close d−1 -> open d+1).
- FINRA consolidated short interest (`api.finra.org/.../consolidatedShortInterest`): free, no key, bi-monthly,
  with days-to-cover. Published ~7-8 business days after the settlement date (the lag must be modelled).
- EDGAR cache (`data/research/night/edgar/`): 1,992 issuers of past night picks; form + acceptance time only (no
  8-K item, no Form 4 transaction code). Not a universe for a new leg. New EDGAR pulls need an SEC User-Agent
  contact (the Mac's .env has none: user decision, NEXT.md).
- Live executor already skips half days (`executor.py` "early close today - night leg skipped"); no gap there.

## Ranked list

| rank | id | idea | area | source / mechanism | who pays | dead-list check | data | prior %/yr $2.3k / $10k / $25k | test? |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **DS1** | **Earnings-announcement premium, overnight: buy at the close before the announcement date, sell at the open after it (close d−1 -> open d+1)**, a sleeve on idle overnight cash (the Roth's ~60% idle nights) | C, E | Frazzini-Lamont 2007; Barber-De George-Lehavy-Trueman 2013 (premium in the announcement window, worldwide); Savor-Wilson 2016 (systematic announcement risk); Lou-Polk-Skouras 2019 (it accrues overnight) | a risk premium for announcement risk + attention-driven buyers at the post-news open (Barber-Odean 2008) | not tested: add. 12 only split *night picks* by an earnings headline (a different question: does news change a drop's bounce) | Nasdaq calendar (free), panel.pkl daily bars; confirm on Alpaca crosses | unknown sign at retail costs; if the published ~+20-40bp per window survives, ~+2-5pp on idle Roth cash | **yes** |
| 2 | **DS2** | **Noise leg decision grid: 15-minute slots instead of 30** (same rule, same bands) | A | Zarattini-Aziz-Barbon 2024 used 30 min untested against finer grids here; earlier entry into trend days | same as the noise leg (hedging / LETF rebalancing flows trending late) | not in RESULTS (grep "15-min", "decision grid", NOISE_STEP: 0 hits); lab latency studies only | m1 QQQ/SMH minute bars 2016-26 (cached) | ±1pp (more trades at 0.5bp/side vs earlier entries) | **yes** |
| 3 | **DS3** | **Noise leg: no new entries at the midday slots (12:00-13:30)** | A | intraday U-shape: midday breakouts are noise (Gao-Han-Li-Zhou 2018: momentum lives in the first/last half hour) | — (saves costs on low-information slots) | not tested (same grep) | as DS2 | ±0.5pp | **yes (2nd variant of DS2's study)** |
| 4 | **DS4** | **Night picks tilted by FINRA days-to-cover** (short interest / ADV, lagged to publication) | E | crowded shorts in a stock that fell 8% cover into the next open (Boehmer-Huszar-Jordan 2010: high-SI stocks reverse; Diether-Lee-Werner 2009 short-term) | short sellers covering at the open | AY tested the **daily off-exchange short VOLUME ratio** (dead); short INTEREST (stock of positions) is untested (grep "short interest": 0) | FINRA API (free) | +0..+2pp if like AU3; ~0 if a vol proxy | **yes** |
| 5 | **DS5** | **Night leg sized up in December's last 10 sessions (tax-loss selling) and the last 3 sessions of each quarter (window dressing)** | D | Grinblatt-Moskowitz 2004 (tax-loss), Ng-Wang 2004 (quarter-end selling of small losers) | tax-motivated and window-dressing sellers who dump losers into the close regardless of value | turn-of-month dead for SPY (add. 27 scan) and month-end pension rebalancing is IBS sizing (watch); a loser-specific seasonal tilt on the night leg is untested | existing night pool | +0..+1pp (≈ 26 nights/yr) | **yes (low power: reported as such)** |
| 6 | DS6 | Roth IBS leg held in 2x ETFs (SSO/QLD/ROM/USD...), the Roth's only leverage | B, D | add. 31: the Roth is below its Kelly peak; an IRA has no margin | — (leverage; financing inside the ETF ~RF+0.5% + 0.9% fee, not 12% margin) | SOXL IBS (add. 22) = same bet concentrated, maxDD −54%; Roth 3x on daytime cash borderline; UPRO sleeve = user risk decision | etf_daily + 2x ETF bars (Alpaca) | +4..+8pp Roth, with DD to match | not now: a leverage/risk decision of the UPRO kind, not an edge; listed for the user |
| 7 | DS7 | Post-earnings drift on the calendar's EPS surprise (long top surprise, 20-60 days) | C | Bernard-Thomas 1989 | slow-to-update investors | not tested; literature says it is gone in large caps since ~2006 (Martineau 2022) | Nasdaq calendar | ~0 | no (published decay; multi-day legs lag the index here, Lab-BH/BR) |
| 8 | DS8 | Weekend night scale 1.0 instead of 0.5, judged on auction prints | D | add. 18 set 0.5 as risk parity (weekend mean = weekday, t 0.04) | — | add. 18 (a choice, not a test) | existing | +1pp at the cost of the COVID weekend tail | no: an exposure change (the BD2/AS2 lesson), not selection |
| 9 | DS9 | Night decision at 15:50-15:55 instead of 15:40 | A | NYSE/Nasdaq MOC cutoffs | — | **dead**: RESULTS "decision time" 15:35 37.8 / 15:40 34.8 / 15:45 26.1 / 15:49 28.4%, no monotone relation | — | ±5pp of noise | no |
| 10 | DS10 | Fill idle Roth night capital with −6..−8% losers | B | — | — | **dead** (RESULTS: band has no gross edge, t −2.3) | — | — | no |
| 11 | DS11 | Noise leg on TLT/GLD/USO/IWM (uncorrelated intraday) | C | Gao et al. intraday momentum across assets | — | **dead** (RESULTS: "diversify the intraday leg ... no gross edge on non-equity-index instruments") | — | — | no |
| 12 | DS12 | Cheaper look-alike ETFs (QQQM, SPLG) for whole-share rounding | A | — | — | **report** (Study AO: +0.5pp, top2+look-alike +1.0pp post-hoc) | — | +0.5..1pp at $2.3k only | no (done) |
| 13 | DS13 | IBS entry with a limit at the bid instead of the open auction | A | NEXT "ideas not yet tested" | — | bounded by add. 13 (~+2pp if free); Lab-BG: passive fills adversely selected | needs ETF quotes at the open (none) | ≤ +2pp, likely ~0 after adverse selection | no (no quote data; adverse-selection prior) |
| 14 | DS14 | Insider open-market purchases (Form 4), multi-day | E | Lakonishok-Lee 2001; Cohen-Malloy-Pomorski 2012 | uninformed sellers | NEXT: waiting on the user (SEC User-Agent) | SEC quarterly Form 3/4/5 sets | — | blocked (user decision) |
| 15 | DS15 | Night picks: drop names with an after-close earnings report tonight | E | — | — | add. 12: earnings-headline picks ≈ the night (+0.6bp, t ~0) | Nasdaq calendar | ~0 | no |
| 16 | DS16 | Treasury/commodity ETF IBS (TLT, GLD) | C | Connors-style IBS outside equities | — | rule-based IBS universe (equity ETFs) dead add. 36; non-equity untested but intraday non-equity had no edge | etf_daily | ~0 prior | no (weak prior) |
| 17 | DS17 | Cost-aware night sizing on measured live cost per price bucket | D | live costs ~0bp vs 7.5-15bp assumed | — | the cost-gated levers (15% cap, 1.3x) already encode it (study_everything_on) | needs ≥ 300 live fills (34 now) | the 15% cap + 1.3x: +8.7 / +11.7pp at 2.5bp | no: a gate, not a study; already in the digest's order |
| 18 | DS18 | Combined per-name weight (tilt v2 × tug-of-war) | D | — | — | done: AU3 R2 (+2.7pp on top of v2) | — | — | no |
| 19 | DS19 | Drawdown-aware leverage with a lower false-alarm rate than CUSUM | D | — | — | add. 37 dead (CUSUM / rolling-t); no new mechanism | — | — | no |
| 20 | DS20 | Cross-sectional ranking / multiple formation horizons | B | NEXT untested list | — | applies to the quarantined swing book's z-score, not the live legs | — | — | no |
| 21 | DS21 | Broker margin rate (12% Schwab small-balance) as a lever on the 1.3x overnight step | D | — | the broker | report-level: the 1.3x step pays ~12%/yr on the debit | — | a few pp at 1.3x, only after the cost gate | no: a business choice, listed |
| 22 | DS22 | Live-vs-research pick scorecard (are the live 15:40 picks the research picks?) | F | — | — | `make review` §1 does it per day; no running score | live decisions jsonl | protects every number | build later (engineering, no N) |
| 23 | DS23 | Study Y size curve re-run on auction-corrected returns | F | — | — | Study Y used vendor opens | existing | ~−2pp restatement at size | report later (no N) |

## What gets tested (one pre-registration, Round 29)
DS1 (earnings premium, 3 variants), DS2+DS3 (noise grid, 2 variants), DS4 (days-to-cover tilt, 1 variant),
DS5 (seasonal night size, 1 variant): **7 variants, N 745 -> 752**. Registered in round1_prose.md before any number.
