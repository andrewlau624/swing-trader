"""Study PANIC-IDX: rare index washout buy (SPY). See round1_prose.md."""
import pathlib, numpy as np, pandas as pd

S = pathlib.Path.home() / "data" / "sharadar"
OUTF = pathlib.Path("data/research/program/panic_idx_out.txt")
OUT = []
def P(s=""):
    print(s); OUT.append(s)

f = pd.read_parquet(S / "funds.parquet", columns=["ticker", "date", "closeadj"], filters=[("ticker", "==", "SPY")])
f["date"] = pd.to_datetime(f["date"]); f = f.sort_values("date").reset_index(drop=True)
px = f.closeadj.values; dates = f.date.values
r1 = np.r_[np.nan, px[1:] / px[:-1] - 1]
dd = px / pd.Series(px).rolling(252, min_periods=60).max().values - 1
r5 = px / np.r_[np.full(5, np.nan), px[:-5]] - 1
COST = 2e-4

def trades(ddk, r5k, hold):
    out, i, n = [], 0, len(px)
    while i < n - hold:
        if dd[i] <= -ddk and r5[i] <= -r5k:
            raw = px[i + hold] / px[i] - 1 - 2 * COST
            lev = np.prod(1 + 3 * r1[i + 1:i + hold + 1]) - 1 - 2 * COST
            out.append((pd.Timestamp(dates[i]), raw, lev, dd[i], r5[i])); i += hold
        else:
            i += 1
    return pd.DataFrame(out, columns=["date", "raw", "lev3", "dd", "r5"])

def uncond(hold):
    return np.nanmean(px[hold:] / px[:-hold] - 1)

yrs = (dates[-1] - dates[251]).astype("timedelta64[D]").astype(int) / 365.25
t = trades(0.15, 0.07, 10); u = uncond(10); t["ex"] = t.raw - u
P(f"PANIC-IDX primary: dd>=15%, 5d<=-7%, hold 10, SPY {pd.Timestamp(dates[0]).date()}..{pd.Timestamp(dates[-1]).date()}")
P(f"n {len(t)} ({len(t)/yrs:.2f}/yr), uncond 10d {u*1e2:+.2f}%")
P(f"raw mean {t.raw.mean()*1e2:+.2f}% median {t.raw.median()*1e2:+.2f}% hit {(t.raw>0).mean():.0%} worst {t.raw.min()*1e2:+.2f}% best {t.raw.max()*1e2:+.2f}%")
P(f"excess mean {t.ex.mean()*1e2:+.2f}%  t {t.ex.mean()/t.ex.std(ddof=1)*np.sqrt(len(t)):.2f}")
h1 = t[t.date < "2012-01-01"]; h2 = t[t.date >= "2012-01-01"]
P(f"halves excess: 1998-2011 {h1.ex.mean()*1e2:+.2f}% (n {len(h1)}) / 2012-26 {h2.ex.mean()*1e2:+.2f}% (n {len(h2)})")
ex5 = t.sort_values("ex").iloc[:-5] if len(t) > 5 else t.iloc[:0]
P(f"ex-top-5 excess {ex5.ex.mean()*1e2:+.2f}%")
P(f"3x synthetic: mean {t.lev3.mean()*1e2:+.2f}% median {t.lev3.median()*1e2:+.2f}% worst {t.lev3.min()*1e2:+.2f}%")
g = dict(mean=t.ex.mean() >= 0.02, median=t.raw.median() > 0, hit=(t.raw > 0).mean() >= 0.6,
         halves=(h1.ex.mean() > 0) and (h2.ex.mean() > 0), ex5=ex5.ex.mean() > 0)
P("gate: " + " ".join(f"{k}={'Y' if v else 'n'}" for k, v in g.items()) + f" -> {'PASS' if all(g.values()) else 'KILL'}")
P(f"ceiling (1x, 100% acct, 50% capture): {len(t)/yrs*t.ex.mean()*0.5*1e2:+.2f}pp/yr; 3x: {len(t)/yrs*(t.lev3.mean()-3*u)*0.5*1e2:+.2f}pp/yr")
P("\nevents:")
for r in t.itertuples():
    P(f"  {r.date.date()} dd {r.dd*1e2:5.1f}% 5d {r.r5*1e2:5.1f}%  raw {r.raw*1e2:+6.2f}%  3x {r.lev3*1e2:+6.2f}%")
P("\nsensitivity (descriptive): dd 5d hold -> n, excess mean, median raw, hit")
for ddk in (0.10, 0.15, 0.20):
    for r5k in (0.05, 0.07, 0.10):
        for hold in (5, 10, 20):
            s = trades(ddk, r5k, hold)
            if len(s):
                e = s.raw - uncond(hold)
                P(f"  {ddk:.0%} -{r5k:.0%} {hold:2d}: n {len(s):3d} ex {e.mean()*1e2:+5.2f}% med {s.raw.median()*1e2:+5.2f}% hit {(s.raw>0).mean():.0%}")
OUTF.write_text("\n".join(OUT) + "\n")
