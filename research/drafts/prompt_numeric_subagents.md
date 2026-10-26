# Delegable research prompts: numeric models and the CEF-RV beta question (2026-10-06)

Six self-contained prompts. Each one can go to a separate subagent or session, and they can run in parallel. Paste the
**shared preamble** plus ONE task block. Program N is 891 when these are written. Each task has its own reserved N
block so parallel sessions do not collide (past sessions collided on 857-861). If a task needs fewer numbers, leave the
rest unused; never take another task's numbers.

---

## Shared preamble (paste first, every time)

You are a research agent in the swing-trader repo (`~/Documents/Code/Projects/swing-trader`). Before anything else read
CLAUDE.md and docs/memory/INDEX.md (then the memory files the task touches): the research philosophy, the research-priority gate, the validation protocol, and the session
memories, in particular "FinBERT / open NLP discovery" and "CEF-OOS / NAVFALL" (2026-10-06). Also read the NEXT.md
do-not-redo table (grep it for your topic first) and the end of `research/drafts/round1_prose.md` from
"Study CEF-TXT" onward.

Facts you must not re-derive:
- CEF-RV (`research/sim/cef_rv.py`, trade builder `build_trades`) passed on untouched 1999-2014: +333bp/trade net,
  t 5.3, alpha +237bp after 0.53*SPY. In 2016-26 it earns +448bp raw, but **only +46bp alpha (t 0.74) after 0.76*SPY
  over the hold**: the recent edge is mostly equity beta bought after selloffs. Diagnostic: `research/sim/cef_beta_diag.py`.
- NAV-fall filter (CEF-RV entries in the bottom within-year tercile of distribution-inclusive 26-week NAV return):
  +376bp spread OOS, about half of it SPY rebound.
- Free open NLP (FinBERT on news, earnings and N-CSR letters) is dead as a signal source. Price-only forecasting of
  returns is the program's most-tested dead class.
- The CEFConnect panel (`data/research/cefconnect/cef_panel.parquet`, weekly NAV/price 1996+) is LIVE FUNDS ONLY;
  704 of 1,074 CEF permatickers are delisted and have no NAV there.

Rules (non-negotiable):
- The user's objective is %/yr after costs on $2.3k / $10k / $25k accounts (Roth: long-only, no margin; taxable: margin
  >= $2k). Report money at those three sizes first.
- Pre-register in `research/drafts/round1_prose.md` (append only: name, rule, data, window, gate, kill rule) and use
  your reserved N **before** reading any outcome. Judge on a window or asset never used to choose the rule. Report
  halves, a 2-3x cost shock, ex-top-5, median, hit rate, a clustered t, a placebo, and a dumb non-model control. If the
  dumb control matches the model, the model adds nothing.
- Quote alpha (beta-adjusted over the actual holding window), not raw returns, for anything held more than a day.
- Treat spectacular results as bugs until checked: use `closeadj` for total return (raw closes break across splits);
  for any filing, use the SEC acceptance time, not the period date; check survivorship.
- Python: the project `.venv` for pandas work. Models needing torch/transformers run on system `python3`, with
  `sys.modules["torchvision"] = None` before importing transformers (the installed torchvision is mismatched). Do not
  change either environment; install new packages into a fresh venv in your scratchpad.
- Do not edit CLAUDE.md, NEXT.md or any live code under `swingtrader/` (the orchestrating session merges memory).
  No paid data, no orders, no deployment, no server changes. `ssh him` is read-only.
- Deliverable: one file `research/drafts/<task-slug>_2026-10.md` with the pre-registration text, the results table,
  the verdict (PASS / KILL / DATA-LIMITED), and every claim backed by a `path:line` or an output file. Runners go in
  `research/sim/`, outputs in `research/sim/*_out.txt`. End with a 5-line summary the orchestrator can paste.

---

## Task 1: Is CEF-RV alpha or timed beta? (reserved N 892-894) — HIGHEST PRIORITY

Question: does CEF-RV beat the cheapest beta-equivalent a Roth could hold instead?
- Build three comparators for each CEF-RV trade (same entry/exit dates): (a) beta x SPY over the hold; (b) the
  equal-weight CEF universe over the hold (Sharadar SFP closeadj of every CEF trading that day, **including delisted**
  funds); (c) "buy SPY after a drawdown": hold SPY whenever SPY's own 26-week return is in its bottom tercile, with the
  same hold length. If (c) earns what CEF-RV earns, CEF-RV is a SPY-dip rule in disguise.
- Judge windows: 1999-2014 (already touched once by N 890; report it, do not tune on it) and 2016-2026 (touched). The
  only untouched evidence is forward, so also write the spec for a forward log-only shadow that records CEF-RV
  entries next to their comparators (spec only, no code under `swingtrader/`).
- Long-only (Roth) economics: what does CEF-RV add over simply holding SPY or a CEF index at $2.3k / $10k / $25k?
  Taxable: is a SPY-hedged CEF-RV executable (borrow is not needed to short SPY; margin is)?
- Kill rule to pre-register: CEF-RV minus comparator (b) has clustered t < 2 in 2016-26 -> CEF-RV is beta-dominant and
  is not a small-account alpha candidate.

## Task 2: CEF-RV survivorship on 1999-2014 (reserved N 895-896)

The 1999-2014 pass uses 276 funds that survived to 2026. CEF-RV's own attack (`cef_rv_surv.py`) estimated a ~2pp/yr
survivorship gap for 2016+, but survivorship is far heavier for older eras.
- Use Sharadar SFP prices of the 704 delisted CEFs, with no NAV, to bound the bias. One option: a price-only proxy
  entry (a 26-week price drawdown in the fund's bottom decile, or a large discount where an N-CSR / N-Q / N-PORT NAV is
  available on EDGAR at semiannual or quarterly frequency) to compare live vs delisted funds' forward returns after
  equivalent entries.
- Answer: could adding back the delisted funds plausibly erase the +237bp OOS alpha? Give a number, not a word.
- Also measure how delisted CEFs end (liquidation near NAV, merger, conversion, open-ending) by era, from
  `actions` and EDGAR (N-8F deregistration) — the "dies benignly" claim was measured only for recent eras.

## Task 3: Time-series foundation models for VOLATILITY, not returns (reserved N 897-898)

Models: Amazon Chronos-Bolt (small/base), Google TimesFM, Salesforce Moirai, IBM TinyTimeMixer (Hugging Face, CPU).
- First, a leakage audit: for each model, list its pre-training corpora from the model card or paper and whether they
  contain financial series (and which dates). Only a model whose corpus excludes your judge window can be backtested
  honestly; state the usable window per model.
- Task: forecast next-5-day realized volatility for SPY, QQQ and the IBS ETF universe. Baselines: trailing 20-day vol,
  EWMA (lambda 0.94), HAR-RV on daily |returns|. Metric: QLIKE and MSE of log-variance, out of sample.
- Then the money test (the only one that counts): use the best forecast to size the live IBS leg (inverse-vol, same
  gross exposure cap as live) and the night leg (daily-close proxy) vs sizing on trailing-20d vol. Pre-register the
  %/yr and max-drawdown gate; an improvement under +1pp/yr at the book level is a KILL even if QLIKE improves.
- Do not forecast returns or direction with these models.

## Task 4: Tabular challenger on CEF-RV entries (reserved N 899-900)

Can a tabular model (TabPFN v2 and LightGBM, both free) choose CEF-RV entries better than one-line rules?
- Features, fixed before any fit: entry discount, discount minus own 52-week median, 26-week distribution-inclusive
  NAV return, 26-week price return, distribution rate, fund age, $ADV, leverage if obtainable from N-CSR / N-PORT
  free data, the CEF's sector/asset class (from the CEFConnect fund list), SPY 26-week return, VIX level.
- Train on 1999-2014 entries (`data/research/cefconnect/cef_rv_trades_1999_2014.csv`), test once on 2016-2026
  (`cef_rv_trades.csv`). Target: **beta-adjusted** trade return (Task 1 method), not raw return, so the model cannot
  win by learning "buy after selloffs".
- Controls the model must beat by >= +50bp/trade on the kept set: NAV-fall tercile alone, discount depth alone, a
  2-feature logistic regression. Report feature importances and whether the model mostly re-learns SPY timing.

## Task 5: Night-leg pick conditioning with a tabular model (reserved N 901-902) — run only if Tasks 1-4 leave capacity

The night leg (buy -8% losers at the close, sell at the next open) is VALIDATED-SMALL (NX: +3.07bp/night on 2003-15).
- Can a tabular model on point-in-time Sharadar features (SF1 fundamentals as of the pick date with the publication
  date respected, size, prior 20-day path, short interest from FINRA 2020+ if used, sector, dilution flag: implied
  shares down >= 5% in a quarter) separate night picks that bounce from those that don't?
- Windows: 2003-2015 is TOUCHED for the night leg (NX single look): do not judge there. Fit on 2003-15, judge once on
  2016-2026 delisted-complete Sharadar picks (`research/sim/shar_surv.py` shows how to build them), daily-close proxy
  clearly labelled.
- Gate: kept-picks lift >= +10bp/night after tier costs, beats a single-feature rule (best of size, dilution flag,
  20-day drawdown) by >= +5bp, both halves positive. The dead "news-sentiment filter on night picks" is the prior.

## Task 6: Survey — what numeric/ML tools could still matter at $2-25k? (no N; read-only)

A literature and model survey, not a backtest. For each of: time-series foundation models, tabular foundation models
(TabPFN), graph models over fund holdings (13F / N-PORT holdings overlap -> forced selling contagion), anomaly
detection on NAV/price (CEF and ETF premium spikes), and option-implied numerics (free sources only), answer:
- What decision in THIS book could it change (sizing, entry filter, risk gate, discovery)?
- What would the honest ceiling be under the research-priority gate at $10k?
- What free data exists, and what is the cheapest falsification test?
- Has the repo already killed the underlying mechanism (grep NEXT.md / round1_prose.md and cite the row)?
Output a ranked table with a one-line recommendation each, and name at most two worth a pre-registered study.
