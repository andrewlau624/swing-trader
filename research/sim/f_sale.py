"""Study F-SALE (N 1054): mutual-fund fire-sale pressure (tfn.s12) -> next-quarter reversal. usage: ... f_sale pull | run"""
from __future__ import annotations
import pathlib, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[2]; D = ROOT / "data/research/fsale"; D.mkdir(parents=True, exist_ok=True)
SH = pathlib.Path.home() / "data/sharadar"; OUT = ROOT / "data/research/program/f_sale_out.txt"
MIN_ASSETS = 100.0          # s12 assets are in $ millions
LAG_DAYS, FLOW = 60, 0.05


def log(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True)
    with OUT.open("a") as f: f.write(s + "\n")


def pull():
    """year-by-year (the single 2009+ query grew past 2GB in memory); fdate, fundno, cusip, shares, assets only."""
    import wrds
    u = open(pathlib.Path.home() / ".pgpass").readline().split(":")[3]
    db = wrds.Connection(wrds_username=u)
    for y in range(2010, 2027):
        f = D / f"s12_{y}.parquet"
        if f.exists():
            continue
        q = f"""select fdate, fundno, cusip, shares, assets from tfn.s12
                where fdate >= '{y - 1}-12-01' and fdate < '{y}-12-01' and assets >= {MIN_ASSETS} and cusip is not null and shares > 0"""
        x = db.raw_sql(q, date_cols=["fdate"])
        x["fundno"] = x.fundno.astype("int32"); x["shares"] = x.shares.astype("float32"); x["assets"] = x.assets.astype("float32")
        x.to_parquet(f)
        print(f"{y}: rows {len(x):,} funds {x.fundno.nunique():,} fdates {sorted(x.fdate.dt.date.unique())[:4]}...", flush=True)
        del x
    db.close()



def cusip_map() -> pd.Series:
    """cusip8 -> Sharadar ticker (SEP), preferring domestic common stock and the latest listing."""
    t = pd.read_parquet(SH / "tickers.parquet", columns=["table", "ticker", "cusips", "category", "lastpricedate", "isdelisted"])
    t = t[(t.table == "SEP") & t.cusips.notna()].copy()
    t["dom"] = t.category.fillna("").str.startswith("Domestic Common Stock")
    t = t.assign(cusip=t.cusips.str.split()).explode("cusip")
    t["c8"] = t.cusip.str[:8]
    t = t.sort_values(["dom", "lastpricedate"]).drop_duplicates("c8", keep="last")
    return t.set_index("c8").ticker


def clus_t(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else float("nan")


def qstats(s: pd.Series) -> str:
    x = s.dropna().to_numpy(float)
    if len(x) < 3: return f"q {len(x)}"
    top = np.sort(x)[-5:].sum()
    return f"quarters {len(x)} mean {x.mean():+.0f} med {np.median(x):+.0f} hit {np.mean(x > 0):.2f} t {clus_t(x):.2f} ex-top5 {(x.sum() - top) / (len(x) - 5):+.0f}"


def build() -> pd.DataFrame:
    """PRESSURE per (ticker, quarter) from consecutive s12 holdings and the fund flow proxy."""
    f = D / "pressure.parquet"
    if f.exists():
        return pd.read_parquet(f)
    cm = cusip_map()
    parts = []
    for x in sorted(D.glob("s12_*.parquet")):           # per file: map, filter, aggregate (the raw years run to 25M rows each)
        h = pd.read_parquet(x)
        h = h[h.fdate.dt.month.isin([3, 6, 9, 12])]
        h["ticker"] = h.cusip.str[:8].map(cm)
        h = h.dropna(subset=["ticker"])
        h["q"] = h.fdate.dt.to_period("Q")
        parts.append(h.groupby(["fundno", "q", "ticker"], as_index=False).agg(shares=("shares", "sum"), assets=("assets", "max")))
        del h
    h = pd.concat(parts, ignore_index=True).drop_duplicates(["fundno", "q", "ticker"], keep="last")
    del parts
    log(f"s12 mapped: {len(h):,} fund-quarter-stock rows, {h.fundno.nunique():,} funds, {h.ticker.nunique():,} tickers, quarters {h.q.min()}..{h.q.max()}")
    # quarter-end prices and ADV (shares) per ticker
    st = pd.read_parquet(SH / "stocks.parquet", columns=["ticker", "date", "closeadj", "closeunadj", "volume"], filters=[("ticker", "in", sorted(set(h.ticker)))])
    st["date"] = pd.to_datetime(st.date); st = st[st.date >= "2009-06-01"].sort_values(["ticker", "date"])
    st["q"] = st.date.dt.to_period("Q")
    st["advsh"] = st.volume.groupby(st.ticker).transform(lambda x: x.rolling(20, min_periods=15).median())
    qe = st.groupby(["ticker", "q"]).agg(px=("closeadj", "last"), pxu=("closeunadj", "last"), advsh=("advsh", "last")).reset_index()
    qe["ret_q"] = qe.groupby("ticker").px.pct_change()               # return over quarter q (close q-1 -> close q)
    qe["ret_next"] = qe.groupby("ticker").ret_q.shift(-1)
    # fund return proxy over quarter q from holdings at q-1
    hp = h.merge(qe[["ticker", "q", "px"]], on=["ticker", "q"], how="left")
    hp["val"] = hp.shares * hp.px
    hp["q_next"] = hp.q + 1
    nxt = qe[["ticker", "q", "ret_q"]].rename(columns={"q": "q_next"})
    hp = hp.merge(nxt, on=["ticker", "q_next"], how="left")
    hv = hp.dropna(subset=["val", "ret_q"]).assign(wr=lambda d: d.val * d.ret_q)
    fr = hv.groupby(["fundno", "q_next"]).agg(wr=("wr", "sum"), val=("val", "sum")).reset_index().rename(columns={"q_next": "q"})
    fr = fr[fr.val > 0].assign(r_proxy=lambda d: d.wr / d.val)[["fundno", "q", "r_proxy"]]
    fa = h.groupby(["fundno", "q"]).assets.max().reset_index()
    fa["assets_prev"] = fa.groupby("fundno").assets.shift(1)
    fa["q_prev"] = fa.groupby("fundno").q.shift(1)
    fa = fa[fa.q_prev == fa.q - 1].merge(fr, on=["fundno", "q"], how="left")
    fa["flow"] = fa.assets / fa.assets_prev - (1 + fa.r_proxy)
    fa = fa.dropna(subset=["flow"])
    log(f"fund-quarters with a flow proxy: {len(fa):,}; outflow <= -{FLOW:.0%}: {(fa.flow <= -FLOW).mean():.2f}, inflow >= +{FLOW:.0%}: {(fa.flow >= FLOW).mean():.2f}")
    # share changes per fund-stock between consecutive quarters
    cur = h[["fundno", "q", "ticker", "shares"]]
    prev = cur.assign(q=cur.q + 1).rename(columns={"shares": "shares_prev"})
    d = cur.merge(prev, on=["fundno", "q", "ticker"], how="outer")
    d["shares"] = d.shares.fillna(0); d["shares_prev"] = d.shares_prev.fillna(0)
    d["dsh"] = d.shares - d.shares_prev
    d = d.merge(fa[["fundno", "q", "flow"]], on=["fundno", "q"], how="inner")
    d["sell_p"] = np.where((d.flow <= -FLOW) & (d.dsh < 0), -d.dsh, 0.0)
    d["buy_p"] = np.where((d.flow >= FLOW) & (d.dsh > 0), d.dsh, 0.0)
    d["n_out"] = (d.sell_p > 0).astype(int); d["n_in"] = (d.buy_p > 0).astype(int)
    pr = d.groupby(["ticker", "q"]).agg(sell_p=("sell_p", "sum"), buy_p=("buy_p", "sum"), n_out=("n_out", "sum"), n_in=("n_in", "sum")).reset_index()
    pr = pr.merge(qe, on=["ticker", "q"], how="left")
    pr["pressure"] = (pr.sell_p - pr.buy_p) / pr.advsh          # in days of volume; negative = net fire-sold
    pr = pr[np.isfinite(pr.pressure) & (pr.advsh > 0)]
    pr["q"] = pr.q.astype(str)
    pr.to_parquet(f)
    return pr


def run() -> None:
    if OUT.exists(): OUT.unlink()
    pr = build()
    pr["q"] = pd.PeriodIndex(pr.q, freq="Q")
    # eligibility at the signal date ~ quarter end + 60d: use quarter-end px/ADV as the screen (conservative proxy)
    pr["advusd"] = pr.advsh * pr.pxu
    el = pr[(pr.pxu >= 5) & (pr.advusd >= 1e7) & ((pr.sell_p > 0) | (pr.buy_p > 0))].copy()
    # holding-period return: next-quarter close-to-close as the quarterly rebalance proxy (open crosses: daily opens not pulled here)
    el = el.dropna(subset=["ret_next"])
    el["dec"] = el.groupby("q").pressure.transform(lambda x: pd.qcut(x.rank(method="first"), 10, labels=False))
    spy = pd.read_parquet(SH / "funds.parquet", columns=["ticker", "date", "closeadj"], filters=[("ticker", "==", "SPY")])
    spy["date"] = pd.to_datetime(spy.date); spy["q"] = spy.date.dt.to_period("Q")
    sq = spy.sort_values("date").groupby("q").closeadj.last().pct_change().shift(-1).rename("spy_next")
    univ = el.groupby("q").ret_next.mean().rename("univ")
    log(f"F-SALE (N 1054): {len(el):,} eligible stock-quarters with flow-fund activity, {el.q.nunique()} quarters {el.q.min()}..{el.q.max()}; "
        f"pressure median {el.pressure.median():+.3f} days-of-volume, p10 {el.pressure.quantile(.1):+.3f}, p90 {el.pressure.quantile(.9):+.3f}")
    tab = el.groupby("dec").agg(pressure=("pressure", "mean"), ret_q=("ret_q", "mean"), ret_next=("ret_next", "mean"), n=("ret_next", "size"))
    tab["x_univ_next"] = el.groupby(["dec", "q"]).ret_next.mean().unstack(0).sub(univ, axis=0).mean()
    log("deciles (D1 = most fire-sold): mean pressure / pressure-quarter ret / next-quarter ret / next-quarter excess vs EW (bp):")
    for dq, r in tab.iterrows():
        log(f"  D{int(dq)+1}: {r.pressure:+.3f} / {r.ret_q*1e4:+.0f} / {r.ret_next*1e4:+.0f} / {r.x_univ_next*1e4:+.0f}   n {int(r.n)}")
    b = el[el.dec == 0].groupby("q").agg(ret_next=("ret_next", "mean"), ret_q=("ret_q", "mean"), n=("ret_next", "size"))
    b = b.join(univ).join(sq)
    b["x"] = (b.ret_next - b.univ) * 1e4; b["x_spy"] = (b.ret_next - b.spy_next) * 1e4
    uq = el.groupby("q").ret_q.mean()
    b["press_x"] = (b.ret_q - uq) * 1e4
    log(f"\nBOTTOM DECILE next-quarter excess vs EW: {qstats(b.x)} | vs SPY: {qstats(b.x_spy)}")
    log(f"  pressure-quarter excess (must be < 0 for the mechanism): {qstats(b.press_x)}")
    for nm, m in (("2010-17", b.index.year <= 2017), ("2018-26", b.index.year >= 2018)):
        log(f"  {nm}: x_univ {qstats(b[m].x)}")
    log("  by year x_univ: " + ", ".join(f"{y} {g.x.mean():+.0f}" for y, g in b.groupby(b.index.year)))
    t = el[el.dec == 9].groupby("q").ret_next.mean().to_frame("ret_next").join(univ); t["x"] = (t.ret_next - t.univ) * 1e4
    log(f"  TOP decile (inflow-bought) next-quarter excess: {qstats(t.x)}")
    mid = el[el.dec.between(3, 6)].groupby("q").ret_next.mean().to_frame("ret_next").join(univ); mid["x"] = (mid.ret_next - mid.univ) * 1e4
    x = b.x.dropna()
    ok = dict(mean=x.mean() >= 150, t=clus_t(x) >= 2, median=x.median() > 0, h1=b[b.index.year <= 2017].x.mean() > 0, h2=b[b.index.year >= 2018].x.mean() > 0,
              extop5=(x.sum() - np.sort(x)[-5:].sum()) / (len(x) - 5) > 0, monotone=x.mean() > mid.x.mean(), mechanism=b.press_x.mean() < 0)
    log(f"\nGATES {ok} -> {'PASS' if all(ok.values()) else 'KILL'}")
    log("Disclosed: holding period = next quarter close-to-close (the registered open-cross entry at quarter end + 60d is a stricter, later "
        "entry; if this proxy fails, the stricter one cannot pass); eligibility screened at the quarter end; deciles among stocks touched by a "
        "heavy-flow fund; flow proxy from holdings-weighted returns (no MFLinks on this WRDS account).")


if __name__ == "__main__":
    {"pull": pull, "run": run}[sys.argv[1] if len(sys.argv) > 1 else "run"]()
