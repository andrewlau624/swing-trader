"""BTC-ETF-FLOW (pre-registered 2026-10-16, N 1010->1011): daily US spot-BTC ETF net flow
state -> next-day IBIT open->open return. Data: Farside full history via wayback capture
2026-10-10 (+ canadiancode mirror cross-check); IBIT bars Sharadar SFP. One look."""
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import os

BASE = os.path.expanduser("~/data/sharadar")
RT = 10.0  # bp round-trip stress


def load_flows():
    f = pq.read_table("data/research/crypto_etf/flows_farside.parquet").to_pandas()
    f["d"] = pd.to_datetime(f["d"])
    return f.set_index("d").sort_index()


def load_bars(ticker):
    df = pq.read_table(os.path.join(BASE, "funds.parquet")).to_pandas()
    b = df[df["ticker"] == ticker].copy()
    b["d"] = pd.to_datetime(b["date"])
    return b.set_index("d").sort_index()[["open", "close", "closeadj"]]


def cluster_t(ser, n_lag=None):
    x = np.asarray(ser, dtype=float)
    n = len(x)
    m = x.mean()
    xc = x - m
    if n_lag is None:
        g = max(int((n / 10.0) ** 0.5) - 5, 1)
    else:
        g = n_lag
    s1 = float((xc * xc).sum()) / n
    core = s1
    for l in range(1, g + 1):
        w = 1.0 - l / (g + 1.0)
        core += 2.0 * w * float((xc[l:] * xc[:-l]).sum()) / n
    var = core / n
    if var <= 0:
        return np.nan
    return m / np.sqrt(var), g


def run_leg(bars, flows, name, judge_from="2024-01-11"):
    f = flows["Total"].copy()
    f.index = f.index.tz_localize(None)
    prev = f.shift(1)
    med = prev.rolling(60, min_periods=30).apply(lambda s: np.median(np.abs(s - np.median(s))), raw=True)
    z = prev / med.replace(0, np.nan)
    strong = np.abs(z) >= 1.0
    infl = strong & (z > 0)
    outf = strong & (z < 0)
    r_open = bars["open"].copy()
    r_oo = (r_open.shift(-1) / r_open - 1) * 1e4
    df = pd.DataFrame({"z": z, "inflow": infl, "outflow": outf, "ret": r_oo}).dropna(subset=["ret"])
    df = df[df.index >= judge_from]
    ev = df[df["inflow"] | df["outflow"]].copy()
    ev["arm"] = np.where(ev["inflow"], "IN", "OUT")
    if len(ev["inflow"]) == 0:
        return None
    groups = [ev[ev["arm"] == a]["ret"] for a in ("IN", "OUT")]
    n_in, n_out = len(groups[0]), len(groups[1])
    in_mean, out_mean = np.mean(groups[0]), np.mean(groups[1])
    spread = in_mean - out_mean
    def tstat(a, b):
        p = pd.concat([a, b])
        d = a.mean() - b.mean()
        sp = (((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2)) ** 0.5
        return d / (sp * np.sqrt(1 / len(a) + 1 / len(b))), d
    t, d = tstat(groups[0], groups[1])
    quant = ev["arm"].copy()
    top5 = set(ev.nlargest(5, "ret").index) | set(ev.nsmallest(5, "ret").index)
    ex5r = [ev[ev["arm"] == a]["ret"].drop(top5, errors="ignore") for a in ("IN", "OUT")]
    ex5_spread = ex5r[0].mean() - ex5r[1].mean()
    h1 = ev[ev.index <= "2025-06-30"]; h2 = ev[ev.index > "2025-06-30"]
    halves = []
    for tag, sub in (("H1<=2025-06", h1), ("H2>2025-06", h2)):
        try:
            tt, dd = tstat(sub[sub["arm"] == "IN"]["ret"], sub[sub["arm"] == "OUT"]["ret"])
        except Exception:
            tt, dd = np.nan, np.nan
        halves.append((tag, sub["arm"].value_counts().to_dict(), dd, tt))
    # proper day-cluster/NW(2) t for the contrast d = in_mean - out_mean
    n_in_, n_out_ = n_in, n_out
    inf = []
    for _, row in ev.iterrows():
        if row["arm"] == "IN":
            inf.append((row["ret"] - out_mean) / n_in_)
        else:
            inf.append(-(row["ret"] - in_mean) / n_out_)
    inf = pd.Series(inf, index=ev.index)
    tt, _ = cluster_t(inf, n_lag=2)
    cts = tt
    ty = pd.DatetimeIndex(sorted(set(ev.index))).year
    per_year = ev.groupby([ev.index.get_level_values(0)])[ "ret"]
    by_year = ev.groupby(ev.index.year).agg(nIn=("inflow", "sum"), nOut=("outflow", "sum"), meanRet=("ret", "mean"))
    by_year["inMean"] = ev[ev["arm"] == "IN"].groupby(ev[ev["arm"] == "IN"].index.year)["ret"].mean()
    by_year["outMean"] = ev[ev["arm"] == "OUT"].groupby(ev[ev["arm"] == "OUT"].index.year)["ret"].mean()
    return dict(
        name=name, n_in=n_in, n_out=n_out, in_mean=in_mean, out_mean=out_mean,
        spread=spread, t_welch=t, day_cluster=cts, nlag=2,
        ex5=ex5_spread, net10=spread - RT, net30=spread - 30.0, halves=halves, by_year=by_year, ev=ev,
    )


def main():
    flows = load_flows()
    print("flows:", flows.index.min().date(), "->", flows.index.max().date(),
          "n =", len(flows), "nZero =", int((flows["Total"] == 0).sum()))
    out = []
    for tkr in ["IBIT", "FBTC"]:
        b = load_bars(tkr)
        res = run_leg(b, flows, tkr)
        print()
        print("=" * 62)
        print(f"{tkr}  (judge: open(t)->open(t+1), signal 1d-lag total flow, |z|>=1)")
        if res is None:
            print("no events"); continue
        print(f"IN n={res['n_in']} mean={res['in_mean']:.1f}bp | OUT n={res['n_out']} mean={res['out_mean']:.1f}bp")
        print(f"IN-OUT spread = {res['spread']:.1f}bp   Welch t={res['t_welch']:.2f}   day-cluster t={res['day_cluster']:.2f} (lag {res['nlag']})")
        print(f"ex-top-5 spread = {res['ex5']:.1f}bp   net@10bpRT = {res['net10']:.1f}bp   net@30bpRT = {res['net30']:.1f}bp")
        for tag, n, m, tt in res["halves"]:
            print(f"  {tag}: n={n.get('IN',0)}IN/{n.get('OUT',0)}OUT spread={m:.1f}bp t={tt:.2f}")
        print(str(res["by_year"].round(1).to_string()))
        out.append(res)
        # events per year (ceiling arithmetic)
        yrs = res["ev"].index.year.nunique()
        print(f"events/yr = {(res['n_in']+res['n_out'])/yrs:.0f}   (IN+OUT pairs used for pairs test)")

    print()
    print("=" * 62)
    print("VERDICT (registered bar): pair spread net of 10bp RT >= 25bp (i.e. raw>=35bp)")
    print("AND day-cluster t>=2 AND both halves positive AND ex-top-5>0 -> PASS else KILL.")
    r = out[0]
    halves_pos = all(h[2] > 0 for h in r["halves"] if not np.isnan(h[2]))
    long_only_in_net = r["in_mean"] - RT
    p = (r["net10"] >= 25) and (r["day_cluster"] >= 2) and halves_pos and r["ex5"] > 0
    print(f"spread raw {r['spread']:.1f}bp | net@10bpRT {r['net10']:.1f}bp | day-cluster t {r['day_cluster']:.2f} | ex-top-5 {r['ex5']:.1f}bp | halves_pos {halves_pos}")
    print(f"long-only IN arm mean net@10bpRT: {long_only_in_net:.1f}bp (n={r['n_in']}) <- Roth-deployable arm")
    print("RESULT BTC-ETF-FLOW:", "PASS" if p else "KILL (see numbers above)")


if __name__ == "__main__":
    main()
