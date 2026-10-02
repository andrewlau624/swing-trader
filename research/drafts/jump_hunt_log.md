# Jump & ride hunt log (prompt_jump_hunt.md), session llm-trader-51

## STATE (update after every idea)
- program N: 760 (no registration yet). k (ideas judged): 0. Ideas explored (runner explore run): 0. Rounds of idea generation: 1.
- current idea: none (idea list being written; no outcome computed)
- next 5 ideas: (after ranking)
- data sources verified: Alpaca/Benzinga news REST (2016+, ~900 items/day, downloading to data/research/jump/news), Arctic Shift
  Reddit posts (pennystocks, smallstreetbets, shortsqueeze, RobinHoodPennyStocks, SPACs, biotechplays, weedstocks, stocks,
  Daytrading, wallstreetbets; downloading), Wikipedia pageviews (3,524 tickers via Wikidata; downloading), EDGAR (sec_headers,
  submissions formerNames, XBRL frames dei shares), openFDA 510(k), USAspending. Cached: night panel 2020-10..2026-09
  (13,933 symbols, trade_count), EDGAR form.idx 2019Q1-2026Q3, Form 345 zips 2020+, FINRA short interest.
- data sources broken: none yet.
- why things die (running): GAP, LOTTERY, COST, REGIME, PRICE PROXY, TEXTBOOK, TOO RARE, LOOKAHEAD (death map); nothing new yet.

## Log
- 12:45 setup: the prompt names `swing-trader`; the session started in the `llm-trader` checkout (no data caches); work in
  `~/Documents/Code/Projects/swing-trader` (same GitHub repo, 13 GB of caches). Fetched 079aa21; tests 356 passed. N 760 (EV2).
  Peers told (llm-trader-9b, 198-eb). Memory note: a prior session ran `jump_runner explore` on FDA approvals (fdaapp)
  while building the runner (all fail); that was a runner smoke test, not part of this hunt, and counts toward nothing here.
- 12:50 probes, one request each: Alpaca news REST 427/975/1357 items on 3 sample days; Arctic Shift posts OK (100/page);
  Wikimedia pageviews OK; openFDA OK; USAspending OK; EDGAR submissions + XBRL frames OK. Started background downloads
  (`research/sim/jump_data.py`): news 2016-01..2026-09 (3 threads), Reddit subs in sequence, Wikipedia pageviews (6 threads).
