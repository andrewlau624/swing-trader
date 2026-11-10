# ANALOG (N 1180-1188, 2026-11-09): raw price-path analogs ("charts that look like RGTI") — KILL x9

User idea: find stocks whose chart has the same shape as RGTI and trade them. Form tested: z-normalized 20/40-session log-closeadj
path, PCA-8 (keeps ~0.88-0.90 of variance), walk-forward faiss HNSW kNN, K=50 analogs from strictly earlier years (same ticker
within 60 sessions excluded), forecast = mean analog cross-sectional excess open->open return, H 1/5/10. Universe: Sharadar
common + ETFs, closeunadj >= $3, ADV20 >= $5M, delisted-complete, 17.65M rows 1999-2026. Judge 2013-26.

- V1 top decile (~300 names/day): gross excess vs same-date vol-decile x price-band cell +0.1..+2.2bp/trade; after 5/10bp/side
  costs -10..-12bp, t -7..-38, both halves and median negative, alpha vs QQQ negative (beta 0.75-0.8). Shape-shuffled placebo
  (same total return/vol, permuted day order) does as well (diff t <= 1.7): the "shape" carries no information beyond return/vol.
- V2 template matching to 50 in-sample "swingers" (channel strategy 2008-12): H5 +8.6bp gross excess, placebo diff t 2.29, but
  2013-19 negative, ex-top-5 negative, median -11.8, 2020 -40bp. KILL.
- RGTI's latest 40d path's nearest 50 analogs: next 10d median -0.1% (library +0.3%). No usable forecast.
- Pitfall: when mapping a session index to a calendar built from a filtered frame, reindex to position == session (first run
  misaligned QQQ -> beta ~0).
Closed with Study CC / PATTERN-NIGHT / SEQ-NIGHT / SEQ-ENTRY / theme sleeve: chart-shape prediction is dead in snapshot, indicator-
sequence and raw-path forms. Not tested: DTW, OHLC/volume channels, intraday paths, full-dim distance, other K/L, H > 10.
Runner `research/sim/analog.py`; out `data/research/program/analog_out.txt`; cache `data/research/analog/` (~5GB, rebuildable).
