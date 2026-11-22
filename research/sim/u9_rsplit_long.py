"""Study U9 RSPLIT-LONG (N 1258): reverse-split ex-date night, long side, Sharadar SEP. Pre-registration in round1_prose.md.

Convention (hand-checked C 2011-05-09 v .10, AIG 2009-07-01 v .05, ETFC 2010-06-02 v .10, XRX 2017-06-15 v .25):
actions.value = new/old shares (< 1 for reverse); SEP open/close are split-adjusted, closeunadj raw; f = closeunadj/close
equals value on E-1 and 1 on E, so f(E-1)/f(E) == value confirms the ex-date. One pre-split share at the E open is worth
open_raw(E) * value = adjusted open(E) * f(E-1)... i.e. adjusted open(E)/close(E-1) - 1. ADV = adjusted close * adjusted volume.
"""
import pathlib, numpy as np, pandas as pd
from research.sim import book

S = pathlib.Path.home() / "data" / "sharadar"
OUT = []
def P(s=""):
    print(s); OUT.append(s)

tk = pd.read_parquet(S / "tickers.parquet", columns=["table", "ticker", "category"])
tk = tk[tk.table == "SEP"]
cats = tk.category.fillna("")
common = set(tk[cats.str.startswith("Domestic Common") | cats.str.startswith("Canadian Common")].ticker)
st = pd.read_parquet(S / "stocks.parquet", columns=["ticker", "date", "open", "close", "volume", "closeunadj"])
st = st[st.ticker.isin(common)].copy()
st["date"] = pd.to_datetime(st["date"])
st = st.sort_values(["ticker", "date"]).reset_index(drop=True)
st["f"] = st.closeunadj / st.close
g = st.groupby("ticker", sort=False)
st["pclose"] = g.close.shift(1); st["pcloseu"] = g.closeunadj.shift(1); st["pf"] = g.f.shift(1); st["pdate"] = g.date.shift(1)
dv = (st.close * st.volume).fillna(0)
cs = dv.groupby(st.ticker, sort=False).cumsum()
n = g.cumcount()
adv = (cs - cs.groupby(st.ticker, sort=False).shift(20).fillna(0)) / np.minimum(n + 1, 20)
st["padv"] = adv.groupby(st.ticker, sort=False).shift(1).where(n >= 5)        # ADV20 ending E-1, adjusted close x volume
st["night"] = st.open / st.pclose - 1
st["cc"] = st.close / st.pclose - 1
ok = (st.pcloseu >= 1) & (st.padv >= 2.5e5) & st.night.between(-0.9, 2) & ((st.date - st.pdate).dt.days <= 5)
bench = st[ok].groupby("date")[["night", "cc"]].mean().rename(columns={"night": "ew_n", "cc": "ew_cc"})

a = pd.read_parquet(S / "actions.parquet")
a["date"] = pd.to_datetime(a["date"])
rv = a[(a.action == "split") & (a.value < 1) & (a.value > 0) & a.ticker.isin(common)][["ticker", "date", "value"]].drop_duplicates()
P(f"reverse-split rows (common, SEP-listed): {len(rv)}")
d = rv.merge(st, on=["ticker", "date"], how="inner")
P(f" with an E bar: {len(d)}")
d["conf"] = (d.pf / d.f / d.value - 1).abs() < 0.05
P(f" factor-confirmed: {d.conf.sum()}  (unconfirmed dropped: {(~d.conf).sum()})")
d = d[d.conf]
gap = (d.date - d.pdate).dt.days <= 5
d = d[gap & d.pcloseu.notna()]
# DATA FIX (post-registration, before judging; found on the first run's worst rows: KSU/TEN/ITT/TYC/T/MSI/EXPE/HSH):
# a reverse split paired with a spin-off on the same ex-date makes close(E-1) include the child, so the parent's
# night shows the child's value as a loss. Drop rows with any spinoff action for the ticker within +-3 days.
so = a[a.action.isin(["spinoff", "spinoffdividend"])][["ticker", "date"]].rename(columns={"date": "sd"})
m = d[["ticker", "date"]].reset_index().merge(so, on="ticker")
bad = set(m[(m.sd - m.date).dt.days.abs() <= 3]["index"])
P(f" spin-off + reverse split combos dropped: {len(bad)}")
d = d.drop(index=list(bad))
d["t0_raw"] = d.open * (d.closeunadj / d.close) * d.value / d.pcloseu - 1       # raw-price form
P(f" raw-form vs adjusted-form T0: median |diff| {np.median(np.abs(d.t0_raw - d.night))*1e4:.1f}bp, share within 50bp {np.mean(np.abs(d.t0_raw - d.night) < 5e-3):.3f} (closeunadj is rounded to cents)")
big = d.night.abs() > 1.0
P(f" |T0|>100% dropped: {big.sum()}")
d = d[~big]
filt = (d.pcloseu >= 1) & (d.padv >= 2.5e5)
P(f" after price>=$1 & ADV20>=$250k: {filt.sum()} (of {len(d)}; sub-$1 {(d.pcloseu<1).sum()}, ADV<250k {(d.padv<2.5e5).sum()})")
d = d[filt].merge(bench, left_on="date", right_index=True, how="left").dropna(subset=["ew_n"])
d["ex"] = d.date; d["yr"] = d.date.dt.year; d["px"] = d.pcloseu
d["x_n"] = d.night - d.ew_n
d["x_cc"] = d.cc - d.ew_cc
c1 = 2 * book.cost_bps("tier+tick", d.px.to_numpy(), d.padv.to_numpy()) / 1e4
c2 = 2 * 2 * book.cost_bps("tier_hi+tick", d.px.to_numpy(), d.padv.to_numpy()) / 1e4
for k in ("n", "cc"):
    d[f"net_{k}"] = d[f"x_{k}"] - c1; d[f"shk_{k}"] = d[f"x_{k}"] - c2
d["pb"] = np.where(d.px < 5, "$1-5", "$5+")

def stat(x, col):
    v = x[col].dropna()
    if len(v) < 3: return f"n {len(v)}"
    day = x.groupby("ex")[col].mean()
    t = day.mean() / (day.std(ddof=1) / np.sqrt(len(day))) if len(day) > 2 else np.nan
    top5 = v.sort_values().iloc[:-5].mean() if len(v) > 8 else np.nan
    trim = v.sort_values().iloc[5:-5].mean() if len(v) > 12 else np.nan
    return f"n {len(v):4d} mean {v.mean()*1e4:+7.1f}bp med {v.median()*1e4:+7.1f} hit {(v>0).mean():.2f} t {t:5.2f} ex-top5 {top5*1e4:+7.1f} trim5/5 {trim*1e4:+6.1f}"

def block(name, x, k):
    P(f"== {name} [{'close E-1 -> open E' if k=='n' else 'close E-1 -> close E'}]")
    P(" raw          " + stat(x, "night" if k == "n" else "cc"))
    P(" excess EW    " + stat(x, f"x_{k}"))
    P(" net tier+tk  " + stat(x, f"net_{k}"))
    P(" 2x hi+tk     " + stat(x, f"shk_{k}"))
    for b, gb in x.groupby("pb"):
        P(f"   {b:5s} excess " + stat(gb, f"x_{k}") + f" | net mean {gb[f'net_{k}'].mean()*1e4:+.1f} med {gb[f'net_{k}'].median()*1e4:+.1f}")

J = d[(d.yr >= 1998) & (d.yr <= 2012)]
for k in ("n", "cc"):
    block("JUDGED 1998-2012", J, k)
    P(" halves excess: 1998-2005 " + stat(J[J.yr <= 2005], f"x_{k}") + " | 2006-12 " + stat(J[J.yr > 2005], f"x_{k}"))
    block("report-only 2013-26 (2016-26 touched)", d[d.yr >= 2013], k)
P("== cost per round trip (tier+tick) judged: mean %.1fbp median %.1fbp" % (np.mean(c1[d.yr.between(1998, 2012).to_numpy()]) * 1e4, np.median(c1[d.yr.between(1998, 2012).to_numpy()]) * 1e4))
P("== by year (night excess median bp, n): " + "  ".join(f"{y}:{gy.x_n.median()*1e4:+.0f}({len(gy)})" for y, gy in d.groupby("yr")))
epy = len(J) / 15
for k in ("n", "cc"):
    ceil = epy * J[f"net_{k}"].mean() * 0.25 * 0.5 * 100
    P(f"== ceiling [{k}] judged: {epy:.1f} events/yr x net {J[f'net_{k}'].mean()*1e4:+.1f}bp x 0.25 x 0.5 = {ceil:+.2f}pp/yr (same % at $2.3k/$10k/$25k)")
for acct in (2300, 10000, 25000, 100000):
    P(f"   ${acct:>6}: position {0.25*acct:,.0f} <= 5% ADV20 in {np.mean(0.25*acct <= 0.05*J.padv):.2f} of judged events")
pathlib.Path("research/sim/u9_rsplit_long_out.txt").write_text("\n".join(OUT) + "\n")
