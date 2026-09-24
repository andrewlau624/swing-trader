from grow import *
rng = np.random.default_rng(42)
D = list(days); nD = len(D); BLK = 21; YRS = [1, 2, 3, 5, 10]; H = 252 * YRS[-1]; N = 400
SCEN = {
    "A  backtest costs (auction-quality fills)":      dict(night_cost=7.5,  nz=noise_series(0.5, 1.5)),
    "B  moderate (+5bp night, 1bp intraday)":         dict(night_cost=12.5, nz=noise_series(1.0, 1.5)),
    "C  poor Schwab opens (+10bp, 1.5bp intraday)":   dict(night_cost=17.5, nz=noise_series(1.5, 1.5)),
    "D  backtest costs, intraday OFF (<$2k bot cap)": dict(night_cost=7.5,  nz=None, intraday_on=False),
}
paths = []
for _ in range(N):
    seq = []
    while len(seq) < H:
        i = rng.integers(0, nD - BLK); seq += D[i:i + BLK]
    paths.append(seq[:H])
out = {}
for name, kw in SCEN.items():
    res = np.zeros((N, len(YRS))); spyv = np.zeros((N, len(YRS))); dep = np.zeros(len(YRS))
    for p, seq in enumerate(paths):
        E, sp, dp, j = 3000.0, 3000.0, 3000.0, 0
        for t, d in enumerate(seq):
            if t and t % 21 == 0: E += 1000; sp += 1000; dp += 1000
            E += day_pnl(E, d, whole=True, resplit=False, **kw)
            s = spy.get(d, 0.0); sp *= 1 + (s if np.isfinite(s) else 0.0)
            if t + 1 == 252 * YRS[j]:
                res[p, j] = E; spyv[p, j] = sp; dep[j] = dp; j += 1
    out[name] = (res, spyv, dep)
    print(name, flush=True)
    print(f"   {'yr':>3} {'deposited':>10} | {'strategy p10':>12} {'median':>11} {'p90':>11} | {'SPY median':>11} | P(<deposits) P(<SPY)")
    for j, y in enumerate(YRS):
        r, s = res[:, j], spyv[:, j]
        print(f"   {y:>3} {dep[j]:>10,.0f} | {np.percentile(r,10):>12,.0f} {np.median(r):>11,.0f} {np.percentile(r,90):>11,.0f} | "
              f"{np.median(s):>11,.0f} | {100*(r<dep[j]).mean():>10.0f}% {100*(r<s).mean():>6.0f}%")
pickle.dump(out, open('grow_mc.pkl', 'wb'))
