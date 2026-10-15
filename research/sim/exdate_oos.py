"""Study EXDATE-OOS: ex-date night (buy close E-1, sell open E) on Sharadar SEP raw prices. See round1_prose.md."""
import pathlib, numpy as np, pandas as pd
from research.sim import book

S = pathlib.Path.home() / "data" / "sharadar"
OUT = []
def P(s=""):
    print(s); OUT.append(s)

st = pd.read_parquet(S / "stocks.parquet", columns=["ticker", "date", "open", "close", "volume", "closeunadj"])
st["date"] = pd.to_datetime(st["date"])
tk = pd.read_parquet(S / "tickers.parquet", columns=["table", "ticker", "category"])
common = set(tk[(tk.table == "SEP") & tk.category.str.contains("Common", na=False)].ticker)
st = st.sort_values(["ticker", "date"])
st["f"] = st.closeunadj / st.close                      # split factor (raw/adjusted)
st["ropen"] = st.open * st.f
g = st.groupby("ticker")
st["pclose"] = g.closeunadj.shift(1)
st["pdate"] = g.date.shift(1)
st["pvol"] = g.volume.shift(1)
st["padv"] = g.apply(lambda d: (d.closeunadj * d.volume).rolling(20, min_periods=5).mean().shift(1), include_groups=False).reset_index(level=0, drop=True)
key = st.set_index(["ticker", "date"])
fu = pd.read_parquet(S / "funds.parquet", columns=["ticker", "date", "open", "close", "closeunadj"])
fu = fu[fu.ticker == "SPY"].copy(); fu["date"] = pd.to_datetime(fu["date"]); fu = fu.sort_values("date")
fu["ropen"] = fu.open * fu.closeunadj / fu.close; fu["pclose"] = fu.closeunadj.shift(1)
spy = fu.set_index("date")
spy_r = (spy.ropen / spy.pclose - 1)

a = pd.read_parquet(S / "actions.parquet")
a["date"] = pd.to_datetime(a["date"])
ev = []
for r in a[a.action == "split"].itertuples():
    ev.append(dict(kind="fwd" if r.value > 1 else "rev", sym=r.ticker, ex=r.date, ratio=r.value, child=None))
sp = a[a.action == "spunofffrom"]
for r in sp.itertuples():   # ticker = child, contraticker = parent
    ev.append(dict(kind="spin", sym=r.contraticker, ex=r.date, ratio=r.value, child=r.ticker))
ev = pd.DataFrame(ev)
rows = []
for e in ev.itertuples():
    k = (e.sym, e.ex)
    if k not in key.index or e.sym not in common: continue
    x = key.loc[k]
    if not np.isfinite(x.pclose) or x.pclose < 5 or x.pclose * x.pvol < 1e6: continue
    if (e.ex - x.pdate).days > 5: continue
    num = x.ropen
    if e.kind == "fwd": num = x.ropen            # raw open is already post-split per-share; compare to raw close times nothing
    if e.kind == "spin":
        kc = (e.child, e.ex)
        if kc not in key.index: continue
        c = key.loc[kc]
        if not np.isfinite(c.ropen): continue
        num = x.ropen + e.ratio * c.ropen
    if e.kind in ("fwd", "rev"):
        num = x.ropen * e.ratio                  # value of the pre-split share at the ex open
    t0 = num / x.pclose - 1
    if abs(t0) > 1.0 or not np.isfinite(t0): continue
    rows.append(dict(kind=e.kind, sym=e.sym, ex=e.ex, ratio=e.ratio, t0=t0, px=x.pclose, adv=x.padv,
                     spy=spy_r.get(e.ex, np.nan)))
d = pd.DataFrame(rows).dropna(subset=["spy"])
d["ex_ret"] = d.t0 - d.spy
d["yr"] = d.ex.dt.year
for m in ("tier", "tier_hi"):
    d["c_" + m] = 2 * book.cost_bps(m, d.px.to_numpy(), d.adv.to_numpy()) / 1e4
d["net_tier"] = d.ex_ret - d.c_tier
d["net_hi"] = d.ex_ret - d.c_tier_hi
d["net_2hi"] = d.ex_ret - 2 * d.c_tier_hi
d["net_5"] = d.ex_ret - 0.001
d["liq"] = pd.cut(d.adv, [0, 5e6, 5e7, 1e12], labels=["<5M", "5-50M", ">50M"])
d["rb"] = pd.cut(d.ratio, [0, .1, .34, .99, 1.6, 2.01, 3.01, 1e9], labels=["<=1:10", "1:3-1:10", "<1", "1.5:1", "2:1", "3:1", ">3:1"])

def stat(x, col="ex_ret"):
    v = x[col].dropna()
    if len(v) < 3: return f"n {len(v)}"
    day = x.groupby("ex")[col].mean()          # day-clustered
    t = day.mean() / (day.std(ddof=1) / np.sqrt(len(day))) if len(day) > 2 else np.nan
    top5 = v.sort_values().iloc[:-5].mean() if len(v) > 8 else np.nan
    return f"n {len(v):4d} mean {v.mean()*1e4:+7.1f}bp med {v.median()*1e4:+6.1f} hit {(v>0).mean():.2f} t {t:5.2f} ex-top5 {top5*1e4:+7.1f}"

def block(name, x):
    P(f"== {name}")
    P(" raw-SPY       " + stat(x))
    P(" raw (no SPY)  " + stat(x, "t0"))
    for c, l in (("net_5", "10bp rt"), ("net_tier", "tier"), ("net_hi", "tier_hi"), ("net_2hi", "2x tier_hi")):
        P(f" {l:13s} " + stat(x, c))

for kind in ("fwd", "spin", "rev"):
    for lo, hi, tag in ((1998, 2012, "JUDGED 1998-2012"), (2013, 2026, "secondary 2013-26")):
        x = d[(d.kind == kind) & (d.yr >= lo) & (d.yr <= hi)]
        block(f"{kind} {tag}", x)
j = d[(d.kind == "fwd") & (d.yr <= 2012)]
P("== fwd judged halves 1998-2005 / 2006-12")
P(" " + stat(j[j.yr <= 2005])); P(" " + stat(j[j.yr > 2005]))
P("== fwd judged by split ratio");  [P(f" {k}: " + stat(g_)) for k, g_ in j.groupby("rb", observed=True)]
P("== fwd judged by liquidity ($ADV20)"); [P(f" {k}: " + stat(g_) + f" | tier net {g_.net_tier.mean()*1e4:+.1f}") for k, g_ in j.groupby("liq", observed=True)]
P("== fwd by year (median bp, n)"); P(" " + "  ".join(f"{y}:{g_.ex_ret.median()*1e4:+.0f}({len(g_)})" for y, g_ in d[d.kind=='fwd'].groupby("yr")))
P("== events per year fwd judged: %.1f ; all fwd 2013-26: %.1f" % (len(j)/15, len(d[(d.kind=='fwd')&(d.yr>=2013)])/14))
pathlib.Path("data/research/program").mkdir(parents=True, exist_ok=True)
pathlib.Path("data/research/program/exdate_oos_out.txt").write_text("\n".join(OUT))
