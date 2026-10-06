"""Track M1: pooled posterior + predicted forward mean + forward n, from published select/judge numbers only."""
from math import sqrt
from scipy.stats import norm
m, tau, s, delta, SHR = 0.36, 1.91, 1.46, 1.10, 0.63      # meta_report A1 (t-only, n 51, k 23)
LIVE, LIVE_HI = 0.0, 0.09                                 # bp/side: live mean -0.66 floored at 0; 95% UB
# name: (sel mean, sel t, sel n, judge mean, judge t, judge n, judged cost bp/side (round trip x2), trades/yr fwd, unit)
I = {
 "ID1 all ADV>=$1M":  (20.2, 3.40, 8934, 17.2, 1.18, 6076, 2.5, 2700, "bp/trade net"),
 "ID2 ADV $1-20M":    (27.6, 2.60, 4699, 14.4, 0.86, 2982, 2.5, 1325, "bp/trade net"),
 "EV1 cluster >=$20M":(27.7, 2.42, 780, 27.3, 1.85, 635, 2.5, 282, "bp/trade net"),
 "N2 night x1.5 CPI/NFP": (18.7, 2.44, 70, 9.0, 0.74, 64, 0.0, 24, "bp equity/event night, vs other nights"),
}
pooled_pub = {"ID1 all ADV>=$1M": 18.2, "ID2 ADV $1-20M": 19.8, "N2 night x1.5 CPI/NFP": 14.0}  # published full-sample
for k, (ms, ts, ns, mj, tj, nj, c, rate, unit) in I.items():
    r = sqrt(nj / ns)
    prec = 1 / tau**2 + 1 / s**2 + (delta * r)**2 / s**2
    mu = (m / tau**2 + ts / s**2 + delta * r * tj / s**2) / prec
    sd = prec ** -0.5
    p = norm.cdf(mu / sd)
    pool = pooled_pub.get(k, (ms * ns + mj * nj) / (ns + nj))
    gross = pool + 2 * c
    net_live, net_hi = gross - 2 * LIVE, gross - 2 * LIVE_HI
    pred = SHR * net_live
    se_j = mj / tj                       # bp, judge-half SE on nj units
    sig = se_j * sqrt(nj)                # per-unit effective sd
    n80 = (2.487 * sig / pred) ** 2      # one-sided 5%, 80% power
    n90s = (1.2816 * sig / pred) ** 2    # P(forward mean > 0 | real) = 0.9
    print(f"{k:24s} r {r:.2f} post mu {mu:+.2f} sd {sd:.2f} P(mu>0) {p:.3f} | pooled net {pool:+.1f} gross {gross:+.1f} "
          f"live {net_live:+.1f} live_hi {net_hi:+.1f} | PRED {pred:+.1f} {unit} | sd/unit {sig:.0f} | "
          f"n80 {n80:,.0f} ({n80/rate:.1f} yr) | n_sign90 {n90s:,.0f} ({n90s/rate*12:.1f} mo) | "
          f"P(fwd>0|real) at n80 {norm.cdf(pred/(sig/sqrt(n80))):.3f}")
