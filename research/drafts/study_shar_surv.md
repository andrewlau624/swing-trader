# Study SHAR-SURV — survivorship audit of the 2021-26 night-leg panel (diagnostic)

`date`: 2026-10-06. Registration: "Amendment — Study SHAR-SURV" at the end of
`research/drafts/round1_prose.md` (diagnostic, no judged rule, **N unchanged**).
Runner: `research/sim/shar_surv.py`; raw output: `research/sim/shar_surv_out.txt`.

## Question

The live night leg's published 2021-26 daily-bar numbers were computed on a
survivor-only panel (today's listing). How much of that result is survivorship?
Re-run the identical rule on a delisted-complete panel and on the survivor-only
analogue of the same panel, and report the difference.

## Design

- **Rule** (daily-bar form; the close is the proxy for the live 15:40 decision):
  live `loser_picks` at the close (`close(d)/close(d-1)-1 <= -8%`, `IBS(d) < 0.10`,
  raw price `$5..2000`, `ADV$ >= 1e7`, `vol20 >= 0.60`), `dedupe_correlated` at
  `.7`, `night_sizing(crowd_n=30, max_name_pct=0.10)`; buy `close(d)`, sell
  `open(d+1)`, equal weight per name. Implemented by `nx.build_panel` +
  `nx.collect_trades` (the frozen NX code; `nx.py` not edited).
- **Panels**, both over 2021-02-01..2026-09-18, primary common-stock universe
  (`nx.universe_mask(..., "primary")`):
  - **(a) delisted-complete** — Sharadar SEP common stocks, every eligible name
    regardless of today's delisting flag (`~/data/sharadar/stocks.parquet`,
    9.81M bars loaded Nov-2020..Sep-2026 for the 20-session warm-up).
  - **(b) survivor-only analogue** — the same panel restricted to names with
    `isdelisted == "N"` (master filtered before `collect_trades`).
- **Statistic**: per-trade net `= ret - 2*cost/1e4`; day-clustered t on the
  per-trade daily means; ex-top-5 = drop the 5 best trades; median; hit rate.
  Also the published-style portfolio leg (`sum(per*net)` per night). Costs:
  `tier` (assumed, per side) and `flat2.5` (2.5bp per side, 5bp round trip).
- Cross-check (reported only): the local Alpaca-cache survivor panel
  (`book.night_days`), unweighted per trade.

## Headline

| model | panel | n | mean/trade | clus t | median | hit | ex-top-5 | leg/night (t) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| tier | (a) delist-complete | 7706 | **+14.75bp** | 1.81 | +8.53 | 51.5% | +7.49 | +8.61bp (2.34) |
| tier | (b) survivor-only | 6563 | **+18.86bp** | 1.99 | +6.42 | 51.3% | +10.33 | +9.31bp (2.72) |
| flat2.5 | (a) delist-complete | 7706 | **+30.14bp** | 3.17 | +22.45 | 54.6% | +22.88 | +14.04bp (3.82) |
| flat2.5 | (b) survivor-only | 6563 | **+33.95bp** | 3.09 | +20.00 | 54.3% | +25.42 | +14.02bp (4.10) |

## Survivorship estimate

- **Per-trade mean**: survivor-only is **+4.11bp/trade too high at `tier`**
  (−21.8% of (b)) and **+3.81bp too high at `flat2.5`** (−11.2% of (b)). Restoring
  the names that were since removed lowers the night-leg per-trade mean by ~4bp.
- **Portfolio leg/night**: the gap is **~0** (`tier` −0.71bp, `flat2.5` +0.02bp):
  the now-delisted names carry small `per` weights, so at the portfolio level the
  survivor bias is negligible. The bias lives in the per-trade mean, not the leg.
- The 1143 extra trades in (a) are the removed names' pre-delisting bars; only
  **1** is an actual delisting-price outcome (`delist_nopx`), 7705 are ordinary
  `open` outcomes. So the bias is a **selection effect** (which names stay in the
  panel), not a small number of −100% delisting events.

By year (mean net/trade at `tier`): the bias is concentrated in 2022
((a) +23.9 vs (b) +36.6) and 2023 ((a) −11.3 vs (b) +7.5); 2021, 2025 and 2026
are ~flat and 2024 is −6bp. Both panels are positive in 4-5 of 6 years.

## Delisted-name decomposition

- Eligible primary names in window: **5239**, of which **1260 (24.1%) are now
  delisted**; 1256 of those have a last price inside the window (so they really
  left the tape in 2021-26).
- Share of (a) picks from now-delisted names: **16.0% by count / 16.1% by
  per-weight** — delisted names are under-picked relative to their 24% share of
  the eligible universe.

## Cross-check (reported only): local Alpaca-cache survivor panel

1414 nights, unweighted per trade: gross +17.64bp, `tier` **+0.30bp**,
`flat2.5` **+12.64bp**. This is **far below** the Sharadar survivor-only panel
(b) (+18.86 / +33.95), and below the delisted-complete panel (a). The local
panel produces ~2.3x more trades (14986 vs 6563): it is a **different, broader
candidate universe** (Alpaca cache), not a survivorship-flattered one. On this
evidence the local published panel is not optimistic *relative to the
delisted-complete truth*; the two data sources disagree for universe reasons
that this diagnostic does not resolve.

## Caveats

- Daily-bar form, not the exact live 15:40 rule (the exact rule is optimistic
  ~2x per the NX work); the close proxy is the registered design.
- `tier` costs are assumed, not measured; `flat2.5` is 2.5bp/side. No cost shock
  beyond these two.
- The now-delisted flag is keyed by ticker string in the Sharadar master; ticker
  reuse (a new security under an old string) could misclassify a few names. The
  master is the same one NX (2003-15) validated, and 1256/1260 have an in-window
  last price.
- `nobar_halt` (ret −1 for a name that vanishes without a recognised delisting
  action) does not occur here (0 trades); the only end-of-series outcome is 1
  `delist_nopx`.
- The local Alpaca panel's universe differs from Sharadar's `primary`; the
  cross-check is indicative only.

## Verdict

Survivorship flatters the **per-trade** night-leg mean by ~4bp/trade
(11-22% depending on cost model) but **not** the portfolio leg/night (~0bp).
The published survivor-only per-trade number is modestly optimistic; the
leg-level result is essentially unaffected. No pass/fail, no tuning, N unchanged.
