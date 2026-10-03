# Pick-quality hunt log (session llm-trader-ee, prompt_pick_quality.md)

## STATE
- program N: 778 (PQ1 took 777-778)
- ideas tried: 5 (PQ1 dead (judged); PQ2, PQ6, PQ7, PQ7b explored-dead; PQ5 thresholds = already swept, plateau) · current: PQ3 same-story clusters
- facts so far (counts only, no 2024+ outcome by idea): leveraged/inverse ETF share of night picks 2021 3% / 2022 7% /
  2023 6% / 2024 10% / 2025 17% / 2026 24%; 2021-23 bounce LETF +20.6bp vs stocks +17.5bp (n 208 / 3,857).

## Log
- PQ1 (registered 36af33b, N 778) JUDGED once: PQ1a exclude LETFs (1,363 picks): select -0.29pp; judge -7.19pp at tier (NW t
  -1.67, placebo pct 4 — worse than dropping random picks), -5.95pp tier_hi, -7.6pp at $2.3k -> DEAD (LETF picks were GOOD in
  2024-26). PQ1b dedupe: 1 pick removed (the 0.7 corr cap already dedupes) -> DEAD (no effect). pq1_out.txt.
  Lesson: the 2026 weakness is not the LETF influx. Do not exclude, do not up-weight (Study W).
- PQ2 explore spec (written before any look): for each raw-pool night pick 2021-01..2023-12, the Alpaca/Benzinga headlines naming
  it published from the prior session's 16:00 ET to 15:50 ET on the pick day (decision time; nothing later). Category by keyword
  (first match wins, order fixed): OFFERING (offering|priced|pricing|dilut|registered direct|ATM|private placement),
  EARNINGS (earnings|results|quarter|Q[1-4]|EPS|revenue|guidance|outlook|forecast), DOWNGRADE (downgrade|cut to|lowers price
  target|price target cut), BIOTECH (FDA|trial|CRL|phase|endpoint|PDUFA), LEGAL (lawsuit|investigation|SEC |subpoena|class
  action|fraud|short seller|short report), OTHER (any other headline), NONE (no headline). Measure the mean close->open bounce
  net of tier cost per category, t by night-clustered SE, by year. Explore bar to register a rule: a category with >= 150
  picks whose net bounce is <= -15bp below the pool mean in EACH of 2021, 2022, 2023 (or above, for an up-weight), |t| >= 2.
  Mechanism priors: OFFERING / EARNINGS = new information (no overreaction) -> weaker; NONE / DOWNGRADE / OTHER = flow -> stronger.
- PQ2 explore (2021-23, 4,177 picks, 75% with no headline before 15:50): DOWNGRADE n 139, -31bp vs pool (every year < 0 but t -1.0);
  OTHER n 386, -40bp (t -1.7, 2023 +20); EARNINGS n 430 ~0; OFFERING n 55; BIOTECH n 31; LEGAL n 10; NONE n 3,126 +7bp
  -> no category meets the bar -> explored-dead, not registered (matches the dead news filters). pq2.py, pq2_explore.txt
- PQ6 fails-to-deliver as a hard-to-borrow proxy (spec before any look): for each night pick, the latest SEC FTD half-month file whose
  period ended >= 30 days before the pick date (publication lag); FTD$ = max daily (qty x the pick's price) in that file / the pick's
  20d ADV$. Buckets: NONE (no FTD row), LOW (FTD$/ADV < 1%), HIGH (>= 1%). Sign is open (short constraint could mean a
  forced-long-seller drop that bounces, or overpricing that keeps falling): explore bar = HIGH vs the rest differs by >= 15bp
  in each of 2021/2022/2023, same sign, |t| >= 2, n HIGH >= 150. Not a short-interest/DTC/SVR redo: FTDs are settlement failures.
- PQ6 FTD explore (2021-23): HIGH (46%) vs rest +4.5bp t 0.32, years -22/+17/+44; LOW -17.6bp t -1.3; NONE n 514 years
  +72/+24/-136 -> no bucket meets the bar -> explored-dead. pq6.py
- PQ7 RAW-price tilt (death-dodge of add. 23's dead "price" tilt, which ran on split-ADJUSTED prices, the add. 30/36 bug; hint:
  A18 found whole shares at $2.3k earn MORE because rounding drops high-priced picks). Spec before any look: buckets of the RAW
  decision price $5-10 / $10-20 / $20-50 / $50+; net bounce at tier per bucket and year, 2021-23. Bar to register: a monotone
  price gradient with the cheapest bucket >= +15bp over the rest in each of 2021/2022/2023, |t| >= 2.
  PQ7 result at tier: gross gradient $5-10 +39.7 / $10-20 +20.0 / $20-50 +7.1 / $50+ -0.3bp, but tier cost (15 / 10 / 6.4 / 5.8bp
  per side) flattens it: net vs rest +14.8 (t 0.84, years -22/+2/+116) -> fails at tier.
  PQ7b (the one further variant, written before running it): same buckets and bar, net at a flat 2.5bp/side (the program's
  measured-live-auction stress cost, add. 29), since the night leg trades only in the auctions.
  PQ7b result (2.5bp/side): $5-10 +29.8bp vs rest (t 1.69; 2021 -7, 2022 +17, 2023 +131) -> fails; $50+ -21.6bp vs rest, EVERY
  year negative (-33 / -9 / -15, t -1.47) -> misses only on 2022 (-9 > -15). Not registered (two looks used). WATCH: high-priced
  picks are consistently the weakest; at $2.3k whole shares already skip most of them (A18: whole shares earn +3.2 vs +1.4%/yr),
  at $10k+ the book buys them. A fresh registration needs a mechanism beyond this data (e.g. live fills by price bucket).
