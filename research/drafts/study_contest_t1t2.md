# Contest hunt T1 / T2: QQQ 0DTE options on the noise-leg signal — DEAD (all four)

Pre-registered `round1_prose.md` (0dc72d6, N 791 -> 795). Runner `research/sim/contest_options.py`
(`PYTHONPATH=. .venv/bin/python -m research.sim.contest_options run`). Data: Databento OPRA.PILLAR cbbo-1m, only the
contracts the rules trade ($2.01 of the shared credit), strikes from raw prices (the SIP minute matrix is dividend-adjusted,
~2% low in 2023: first fetch had $5-wrong strikes, caught and redone). Fill = NBBO 1 minute after the decision, ask to buy,
bid to sell, $0.65/contract/leg; exit by 15:50. Max loss per trade 5% of equity, whole contracts.

| variant | n sel / judge | return on risk per trade sel / judge | P(mean<=0) judge | judge ex-best-5 ($/sh) | win judge | 3-mo median / p10 / p90 @ $2.3k | P(-30% in 3 mo) @ $2.3k / $10k | judge CAGR @ $2.3k / $10k / $25k | maxDD @ $10k | worst day @ $10k |
|---|---|---|---|---|---|---|---|---|---|---|
| T1a long ATM | 455 / 408 | +5.1% / **-4.9%** | 0.79 | -63 | 24% | -20% / -35% / +18% | 24% / 53% | -41 / -66 / -63% | -91% | -9.6% |
| T1b $2 debit vertical | 450 / 407 | -1.8% / **-15.5%** | 1.00 | -42 | 27% | -29% / -45% / -9% | 56% / 72% | -51 / -76 / -82% | -91% | -11.0% |
| T1c long 0.5% OTM | 454 / 408 | -3.9% / **-11.4%** | 0.88 | -50 | 16% | -42% / -64% / +20% | 79% / 80% | -76 / -88 / -91% | -98% | -18.7% |
| T2a short condor inside the band | 367 / 313 | -11.9% / **-9.5%** | 1.00 | -28 | 47% | -15% / -24% / -7% | 1% / 9% | -26 / -51 / -56% | -71% | -6.9% |
Skipped at $2.3k (one contract > 5% of equity): 73% / 67% / 55% / 71%. No variant passes any gate except T2a's ruin bar.

Why: the underlying signal is too small for 0DTE. The same 865 noise trades on QQQ shares (entry/exit 1 minute after the
decision, gross) earn **+4.5bp/trade, t 2.16 in 2023-24 and +2.6bp, t 0.77 in 2025-26**. A 0DTE ATM option pays ~1-3% of
premium in spread at each crossing and decays all day; a 3-5bp edge on the underlying cannot cover that at any strike.
The condor (the other side of the friend's trade) loses on four spread crossings at 1-wide wings, and on trend days.
This also prices the friend's likely strategy: long 0DTE premium on a tested breakout trigger loses ~5-15% of the risked
premium per trade after real spreads. His 2x lead is far more likely variance than an edge.
