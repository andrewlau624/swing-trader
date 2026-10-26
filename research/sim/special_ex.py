"""Study SPECIAL-EX (N 1052): special-dividend ex-nights on liquid commons, close E-1 -> open E + dividend, vs SPY overnight."""
from __future__ import annotations
import warnings
from pathlib import Path
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]; SH = Path.home() / "data/sharadar"
OUT = ROOT / "data/research/program/special_ex_out.txt"


def log(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True)
    with OUT.open("a") as f: f.write(s + "\n")


def clus_t(y, d):
    y = np.asarray(y, float); e = y - y.mean(); s = pd.Series(e).groupby(np.asarray(d)).sum().to_numpy()
    se = np.sqrt((s * s).sum()) / len(y); return y.mean() / se if se > 0 else float("nan")


def stats(y, d):
    y = np.asarray(y, float); m = np.isfinite(y); y, d = y[m], np.asarray(d)[m]
    if len(y) < 3: return f"n {len(y)}"
    top = np.sort(y)[-5:].sum()
    return f"n {len(y)} mean {y.mean():+.1f} med {np.median(y):+.1f} hit {np.mean(y > 0):.2f} t {clus_t(y, d):.2f} ex-top5 {(y.sum() - top) / (len(y) - 5):+.1f}"


def main():
    if OUT.exists(): OUT.unlink()
    tk = pd.read_parquet(SH / "tickers.parquet", columns=["table", "ticker", "category"])
    ok = set(tk[(tk.table == "SEP") & tk.category.fillna("").str.startswith("Domestic Common Stock")].ticker)
    a = pd.read_parquet(SH / "actions.parquet"); a = a[(a.action == "dividend") & a.ticker.isin(ok)].copy()
    a["date"] = pd.to_datetime(a.date); a = a[(a.date >= "2000-01-01") & (a.date <= "2026-09-30")]
    st = pd.read_parquet(SH / "stocks.parquet", columns=["ticker", "date", "open", "close", "closeunadj", "volume"], filters=[("ticker", "in", sorted(set(a.ticker)))])
    st["date"] = pd.to_datetime(st.date); st = st.sort_values(["ticker", "date"])
    g = st.groupby("ticker")
    st["pcu"] = g.closeunadj.shift(1); st["pc"] = g.close.shift(1); st["pdate"] = g.date.shift(1)
    st["adv"] = (st.closeunadj * st.volume).groupby(st.ticker).transform(lambda x: x.shift(1).rolling(20, min_periods=15).median())
    st["open_raw"] = st.open * st.closeunadj / st.close
    st["close_raw"] = st.closeunadj
    x = a.merge(st[["ticker", "date", "pcu", "pc", "pdate", "adv", "open_raw", "close_raw"]], on=["ticker", "date"], how="inner")
    x["yld"] = x.value / x.pcu
    x = x[(x.yld >= 0.03) & (x.yld <= 0.50) & (x.pcu >= 5) & (x.adv >= 1e7)].copy()
    spy = pd.read_parquet(SH / "funds.parquet", columns=["ticker", "date", "open", "close"], filters=[("ticker", "==", "SPY")])
    spy["date"] = pd.to_datetime(spy.date); spy = spy.sort_values("date"); spy["spy_on"] = (spy.open / spy.close.shift(1) - 1) * 1e4
    x = x.merge(spy[["date", "spy_on"]], on="date", how="left")
    x["r"] = ((x.open_raw + x.value) / x.pcu - 1) * 1e4
    x["exc"] = x.r - x.spy_on.fillna(0)
    x["drop"] = (x.pcu - x.open_raw) / x.value
    x["r_close"] = ((x.close_raw + x.value) / x.pcu - 1) * 1e4 - x.spy_on.fillna(0)
    x["arm"] = pd.cut(x.yld, [0.03, 0.10, 0.25, 0.50], labels=["3-10%", "10-25%", "25-50%"], right=False)
    log(f"SPECIAL-EX (N 1052): {len(x):,} ex-nights 2000-26 on {x.ticker.nunique():,} names; by arm {x.arm.value_counts().to_dict()}; "
        f"by era {x.groupby(x.date.dt.year // 5 * 5).size().to_dict()}")
    for arm, s in [("3-10%", x[x.arm == "3-10%"]), ("10-25%", x[x.arm == "10-25%"]), ("POOLED 3-25%", x[x.arm != "25-50%"]), ("25-50% (due-bill, not gated)", x[x.arm == "25-50%"])]:
        log(f"\n=== {arm}: drop ratio median {s['drop'].median():.2f} (mean {s['drop'].mean():.2f})")
        log(f"  close E-1 -> open E + div, vs SPY: {stats(s.exc, s.date)} | net 5bp mean {s.exc.mean() - 5:+.1f} | raw {s.r.mean():+.1f}")
        log(f"  -> close E instead: {stats(s.r_close, s.date)}")
        for nm, m in (("2000-12", s.date < "2013-01-01"), ("2013-26", s.date >= "2013-01-01"), ("2021-26", s.date >= "2021-01-01"), ("ADV>=50M", s.adv >= 5e7)):
            log(f"    {nm:9s} {stats(s[m].exc, s[m].date)}")
        log("    by era: " + ", ".join(f"{e} {g.exc.mean():+.0f}/{len(g)}" for e, g in s.groupby(s.date.dt.year // 3 * 3)))
    p = x[x.arm != "25-50%"]; y = p.exc.to_numpy(float); d = p.date.to_numpy()
    ok = dict(mean=y.mean() >= 30, t=clus_t(y, d) >= 2, median=np.median(y) > 0, hit=np.mean(y > 0) >= 0.55,
              h1=p[p.date < "2013-01-01"].exc.mean() > 0, h2=p[p.date >= "2013-01-01"].exc.mean() > 0,
              extop5=(y.sum() - np.sort(y)[-5:].sum()) / (len(y) - 5) > 0, drop=p["drop"].median() < 0.9, recent=p[p.date >= "2021-01-01"].exc.mean() > 0)
    log(f"\nGATES (pooled 3-25%) {ok} -> {'PASS' if all(ok.values()) else 'KILL'}")
    log("Disclosed: Sharadar actions date taken as the ex-date; raw open = adjusted open x closeunadj/close; dividends > 50% of price excluded.")


if __name__ == "__main__":
    main()
