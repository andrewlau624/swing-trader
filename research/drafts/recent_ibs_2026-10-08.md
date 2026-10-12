# Recent regime: IBS leg replayed through 2026-10-07 (2026-10-08)
Rule (live `signals.py` + `config.yaml`, mirrored by `research/sim/book.py:ibs_days`): universe = top-3 of EQ18 ETFs by 12-1 momentum (`sg.momentum_top`, ranked at prior month-end), IBS(d) < 0.2 on the last complete bar (`sg.ibs_targets`), buy open(d+1), sell open(d+2). Roth trades a look-alike (`WASH_SAFE_LOOKALIKE`, e.g. XLE->VDE) and skips same-index names. Runner `research/sim/recent_ibs.py {adj|raw}`, fetch `recent_ibs_fetch.py`; data `data/research/recent/etfd/` (Alpaca SIP daily, 2019-12..10-07; outputs `ibs_replay_{adj,raw}_out.txt`). Nothing tuned. Last scorable entry is 10-06 (10-07 entries need the 10-08 open).
Primary series = adjustment=all (total return): a holder selling at the ex-date open still receives the dividend, and live matches it (corr 0.99). Price-only raw is lower by ~10bp/trade in 2021-25 (+5.2 vs +15.8 at 0bp) and is shown only to explain the gap to older raw-looking numbers; the older `ibs_oos.py` 2021-25 figure (+16.6bp) is the adjusted panel.

## IBS trades (bp per trade, open->open, adjusted; day-clustered t)
| period | n | 0bp/side mean / med / hit / t | 2.5bp | 5bp |
|---|---|---|---|---|
| 2021-25 | 738 | +15.8 / +29.0 / 57% / 1.91 | +10.8 / 1.28 | +5.8 / 0.65 |
| 2026 YTD | 97 | +67.2 / +70.7 / 63% / 3.10 | +62.2 / 2.86 | +57.2 / 2.62 |
| 2026-06..10-06 | 47 | +77.2 / +51.2 / 66% / 2.73 | +72.2 / 2.53 | +67.2 / 2.34 |
By year (0bp): 2021 +33, 2022 +18, 2023 +15, 2024 -8, 2025 +20, 2026 +67. 2026 months: May -65 (n 5), Jun +132 (n 13), Jul +30, Aug +72, Sep +84 (n 7), Oct +30 (n 2).

## Control: unconditional EQ18 top-3 basket, same entry day
| period | IBS minus same-day basket (0bp): mean / med / hit / t | basket all-days mean |
|---|---|---|
| 2021-25 | +1.7 / -0.5 / 50% / 0.57 | +6.6 (IBS slots fire 20%) |
| 2026 YTD | +12.0 / +2.3 / 53% / 0.47 | +14.8 |
| 2026-06..10 | +31.0 / +14.9 / 55% / 1.21 | +4.2 |
Read: the 2026 strength is mostly the basket (tech/energy/biotech up-tape: unconditional top-3 +15bp/day YTD). Unpaired, IBS beats the basket by ~+9bp (2021-25), +52 (YTD), +73 (Jun-Oct), but the paired same-day excess is not significant in any window (t 0.5-1.2). Gross is positive and costs are small relative to the 2026 level, but 2024 was negative, so the leg is regime-dependent. Consistent with the cost-bound/beta-proportional memory; no new evidence either way on alpha.

## Live overlay (`ssh him` logs/daily-fills-{live,roth}.jsonl, leg ibs, buy fill -> next sell fill; 09-24..10-07)
7 live round trips (6 taxable, 1 Roth). 5 match a replay pick (4 base-symbol; Roth VDE vs base XLE): live mean +90.3bp vs replay +87.8, corr 0.991 (XBI 09-24 +147 vs +127; XLE 09-25 +137 vs +137; XLE 10-01 +118 vs +115; XBI 10-02 -54 vs -54; Roth VDE +104 vs VDE-own replay +104, XLE +115). Remaining 2 (10-07 SMH -96, XBI -23) are unscorable in the replay (exit = 10-08 open, not in panel). All 4 replay picks in the window were traded live; no live trade lacks a signal. Execution tracks replay; per-trade slippage_bps (-43..+129) is ref-price drift, not cost.

## Verdict
IBS leg in the recent regime: strong in absolute terms (2026 YTD +67bp/trade, t 3.1, survives 5bp/side) and live fills match the replay, but versus the same-day unconditional basket it adds no significant excess (paired t 0.5-1.2). Treat 2026 as up-tape beta plus a weak IBS conditional premium. No sizing change. Caveats: ETF-only, daily open prints from SIP daily-bar opens (not always the official cross); 2024 negative; small n in 2026 (97 trades, ~45 signal days).
