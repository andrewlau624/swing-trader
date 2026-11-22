"""Study U7 ARK-COPY (N 1259): ARK daily-disclosed trades -> next-day open->close in the traded names. Pre-registration in round1_prose.md.

Data: arkfunds.io v2 trades API (github.com/frefrik/ark-invest-api), funds ARKK/ARKW/ARKG/ARKQ/ARKF/ARKX, 2020-09-09 onward, saved as
trades_<FUND>.json ({"trades": [{fund, date, ticker, direction, shares, ...}]}). Fetch:
  https://arkfunds.io/api/v2/etf/trades?symbol=ARKK&date_from=2019-01-01&date_to=2026-11-21
Usage: python research/sim/u7_ark_copy.py <dir with trades_*.json>.  Prices: Sharadar SEP (adjusted, split-consistent).
"""
import sys, glob, json, pathlib, numpy as np, pandas as pd
import pyarrow.dataset as ds
from research.sim import book

S = pathlib.Path.home() / "data" / "sharadar"
OUT = []
def P(s=""):
    print(s); OUT.append(s)

tr = pd.DataFrame([r for f in sorted(glob.glob(str(pathlib.Path(sys.argv[1]) / "trades_*.json"))) for r in json.load(open(f))["trades"]])
tr["date"] = pd.to_datetime(tr.date)
tr["sgn"] = np.where(tr.direction.str.lower() == "buy", 1, -1)
tr["ns"] = tr.sgn * tr.shares
ev = tr.groupby(["ticker", "date"]).agg(ns=("ns", "sum"), funds=("fund", "nunique")).reset_index()
P(f"ARK trade rows {len(tr)} ({tr.date.min().date()}..{tr.date.max().date()}), ticker-days {len(ev)}, net buys {(ev.ns>0).sum()}, net sells {(ev.ns<0).sum()}")

tk = pd.read_parquet(S / "tickers.parquet", columns=["table", "ticker", "category"])
tk = tk[tk.table == "SEP"]; cats = tk.category.fillna("")
common = set(tk[cats.str.startswith("Domestic Common") | cats.str.startswith("Canadian Common")].ticker)
st = ds.dataset(S / "stocks.parquet").to_table(filter=ds.field("date") >= pd.Timestamp("2020-06-01").date(),
        columns=["ticker", "date", "open", "close", "volume", "closeunadj"]).to_pandas()
st["date"] = pd.to_datetime(st.date)
st = st.sort_values(["ticker", "date"]).reset_index(drop=True)
g = st.groupby("ticker", sort=False)
st["adv"] = (st.close * st.volume).groupby(st.ticker, sort=False).transform(lambda s: s.rolling(20, min_periods=5).mean())  # ADV20 ending D
st["oc1"] = g.close.shift(-1) / g.open.shift(-1) - 1          # open D+1 -> close D+1
st["oc2"] = g.close.shift(-2) / g.open.shift(-1) - 1          # open D+1 -> close D+2
st["gap"] = g.open.shift(-1) / st.close - 1                    # close D -> open D+1 (untradable: email after close)
st["d1"] = g.date.shift(-1); st["px1"] = g.closeunadj.shift(0)
P(f"SEP last date {st.date.max().date()}")
u = st[st.ticker.isin(common) & (st.closeunadj >= 1) & (st.adv >= 2.5e5)]
bench = u.groupby("date")[["oc1", "oc2", "gap"]].mean().add_prefix("ew_")

d = ev.merge(st, on=["ticker", "date"], how="inner").merge(bench, left_on="date", right_index=True, how="left")
P(f"ticker-days matched to SEP: {len(d)} of {len(ev)}")
d["tdol"] = d.ns.abs() * d.close
d["pct_adv"] = d.tdol / d.adv
d = d.dropna(subset=["oc1", "ew_oc1", "adv"])
d = d[(d.px1 >= 1)]
cost1 = 2 * book.cost_bps("tier+tick", d.px1.to_numpy(), d.adv.to_numpy()) / 1e4
cost2 = 4 * book.cost_bps("tier_hi+tick", d.px1.to_numpy(), d.adv.to_numpy()) / 1e4
d["c1"], d["c2"] = cost1, cost2
d["ex"] = d.d1; d["yr"] = d.date.dt.year

def stat(x, col):
    v = x[col].dropna()
    if len(v) < 3: return f"n {len(v)}"
    day = x.groupby("ex")[col].mean()
    t = day.mean() / (day.std(ddof=1) / np.sqrt(len(day))) if len(day) > 2 else np.nan
    top5 = v.sort_values().iloc[:-5].mean() if len(v) > 8 else np.nan
    return f"n {len(v):5d} mean {v.mean()*1e4:+7.1f}bp med {v.median()*1e4:+6.1f} hit {(v>0).mean():.2f} t {t:5.2f} ex-top5 {top5*1e4:+7.1f}"

def run(name, x, sign, h="oc1"):
    x = x.copy()
    x["xr"] = sign * (x[h] - x["ew_" + h]); x["net"] = x.xr - x.c1; x["shk"] = x.xr - x.c2
    x["xg"] = sign * (x.gap - x.ew_gap)
    P(f"== {name} [{h}]")
    P(" excess EW    " + stat(x, "xr"))
    P(" net tier+tk  " + stat(x, "net"))
    P(" 2x hi+tk     " + stat(x, "shk"))
    P(" gap D->D+1 (untradable) excess " + stat(x, "xg"))
    mid = x.date.median()
    P(f" halves (split {mid.date()}): " + stat(x[x.date <= mid], "xr") + " | " + stat(x[x.date > mid], "xr"))
    P(" by year excess median/mean bp (n): " + "  ".join(f"{y}:{gy.xr.median()*1e4:+.0f}/{gy.xr.mean()*1e4:+.0f}({len(gy)})" for y, gy in x.groupby("yr")))
    return x

yrs = (d.date.max() - d.date.min()).days / 365.25
prim = run("PRIMARY net BUY, trade >= 1% ADV20, long open D+1 -> close D+1", d[(d.ns > 0) & (d.pct_adv >= 0.01)], +1)
k = prim.groupby("ex").ex.transform("size")
share = np.minimum(0.2, 1.0 / k)
ceil = (share * prim.net).sum() / yrs * 0.5 * 100
P(f"== ceiling primary: {len(prim)/yrs:.1f} events/yr, sum(share x net)/yr x 0.5 = {ceil:+.2f}pp/yr (same % at $2.3k/$10k/$25k)")
for acct in (2300, 10000, 25000, 100000):
    P(f"   ${acct:>6}: 0.2 x acct <= 5% ADV20 in {np.mean(0.2*acct <= 0.05*prim.adv):.2f} of events")
P("-- secondary (reported, not judged)")
run("net BUY >= 1% ADV, hold open D+1 -> close D+2", d[(d.ns > 0) & (d.pct_adv >= 0.01)], +1, "oc2")
run("net SELL >= 1% ADV, SHORT open D+1 -> close D+1", d[(d.ns < 0) & (d.pct_adv >= 0.01)], -1)
run("ALL net buys (any size), long", d[d.ns > 0], +1)
run("ALL net sells (any size), short", d[d.ns < 0], -1)
run("net BUY >= 5% ADV, long", d[(d.ns > 0) & (d.pct_adv >= 0.05)], +1)
run("net BUY, first ARK buy of the name (new position proxy: no ARK trade in prior 60d)", d[(d.ns > 0) & d.apply(lambda r: True, axis=1)].pipe(
    lambda x: x[~x.set_index(["ticker", "date"]).index.isin(
        [(t, dt) for t, dt in zip(x.ticker, x.date) if ((ev.ticker == t) & (ev.date < dt) & (ev.date >= dt - pd.Timedelta(days=60))).any()])]), +1)
pathlib.Path("research/sim/u7_ark_copy_out.txt").write_text("\n".join(OUT) + "\n")
