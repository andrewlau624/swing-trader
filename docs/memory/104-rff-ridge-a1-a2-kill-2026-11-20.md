# Random-feature ridge A1/A2 (N 1212-1213): KILL, judged 2011-20, 2026-11-20
- 6,000 random Fourier features of random price/vol/drawdown/IBS windows over 8 ETFs; ridge; daily SPY timing (A1), top-2 rotation (A2).
- A1 -0.6bp/day t -0.4, 0/5 seeds; A2 +0.3 t 0.2; placebos 51st/68th pct; 2021-26 report negative.
- Lambda went to max shrinkage in the fit period: daily price windows carry no next-day signal for ETFs.
- Not tested: published monthly Welch-Goyal macro setup, stock cross-section, 5-20d horizons.
