"""F-SALE2 (N 1060): CRSP-MF flow-induced selling pressure (Edmans-Goldstein-Jiang MFFlow) -> next-quarter reversal.
Pre-registration: round1_prose.md "Study F-SALE2". Data: research/sim/f_sale2_pull.py -> data/research/fsale2/pressure_YYYY.parquet.
Reuses f_sale.run() (same judge/gates) on a pressure panel built here. Run: .venv/bin/python -m research.sim.f_sale2
"""
from __future__ import annotations
import glob, pathlib
import numpy as np, pandas as pd
from . import f_sale as F

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/fsale2"
OUT = ROOT / "data/research/program/f_sale2_out.txt"


def build() -> pd.DataFrame:
    pr = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(D / "pressure_*.parquet")))], ignore_index=True)
    pr["q"] = pd.PeriodIndex(pd.to_datetime(pr.q), freq="Q")
    pr["qend"] = pr.q.dt.end_time.dt.normalize()
    nm = pd.read_parquet(D / "stocknames.parquet")
    nm["namedt"] = pd.to_datetime(nm.namedt); nm["nameenddt"] = pd.to_datetime(nm.nameenddt)
    nm = nm[nm.shrcd.isin([10, 11])]
    # name row covering the quarter end (fallback: latest row for the permno)
    m = pr[["permno", "qend"]].drop_duplicates().merge(nm, on="permno", how="left")
    ok = m[(m.qend >= m.namedt) & (m.qend <= m.nameenddt)]
    last = m.sort_values("nameenddt").drop_duplicates("permno", keep="last")
    m = pd.concat([ok, last[~last.set_index(["permno"]).index.isin(ok.permno)]]).drop_duplicates(["permno", "qend"])
    cm = F.cusip_map()
    m["ticker_sh"] = m.ncusip.str[:8].map(cm)
    miss = m.ticker_sh.isna()
    sh_tk = set(pd.read_parquet(F.SH / "tickers.parquet", columns=["ticker", "table"]).query("table == 'SEP'").ticker)
    m.loc[miss, "ticker_sh"] = m.loc[miss, "ticker"].where(m.loc[miss, "ticker"].isin(sh_tk))
    pr = pr.merge(m[["permno", "qend", "ticker_sh"]], on=["permno", "qend"], how="left").dropna(subset=["ticker_sh"]).rename(columns={"ticker_sh": "ticker"})
    F.log(f"F-SALE2 (N 1060): pressure rows {len(pr):,} ({pr.permno.nunique():,} permnos -> {pr.ticker.nunique():,} Sharadar tickers), quarters {pr.q.min()}..{pr.q.max()}; "
          f"funds/stock-quarter: sell median {pr.n_sell.median():.0f}, buy median {pr.n_buy.median():.0f}")
    st = pd.read_parquet(F.SH / "stocks.parquet", columns=["ticker", "date", "closeadj", "closeunadj", "volume"], filters=[("ticker", "in", sorted(set(pr.ticker)))])
    st["date"] = pd.to_datetime(st.date); st = st[st.date >= "2008-06-01"].sort_values(["ticker", "date"])
    st["q"] = st.date.dt.to_period("Q")
    st["advsh"] = st.volume.groupby(st.ticker).transform(lambda x: x.rolling(20, min_periods=15).median())
    qe = st.groupby(["ticker", "q"]).agg(px=("closeadj", "last"), pxu=("closeunadj", "last"), advsh=("advsh", "last")).reset_index()
    qe["ret_q"] = qe.groupby("ticker").px.pct_change()
    qe["ret_next"] = qe.groupby("ticker").ret_q.shift(-1)
    pr = pr.groupby(["ticker", "q"], as_index=False).agg(sell_sh=("sell_sh", "sum"), buy_sh=("buy_sh", "sum"), n_out=("n_sell", "sum"), n_in=("n_buy", "sum"), sell_sh10=("sell_sh10", "sum"))
    pr = pr.merge(qe, on=["ticker", "q"], how="left")
    pr["sell_p"] = -pr.sell_sh.fillna(0); pr["buy_p"] = pr.buy_sh.fillna(0)
    pr["pressure"] = (pr.sell_sh.fillna(0) + pr.buy_sh.fillna(0)) / pr.advsh     # days of volume; NEGATIVE = net flow-forced selling
    pr = pr[np.isfinite(pr.pressure) & (pr.advsh > 0)]
    nq = pr[pr.ret_next.notna() & (pr.pxu >= 5)].groupby("q").size()
    pr = pr[pr.q.isin(nq[nq >= 200].index)]          # drop stub quarters (no next-quarter return yet)
    pr["q"] = pr.q.astype(str)
    return pr


if __name__ == "__main__":
    F.OUT = OUT
    F.build = build
    F.run()
    F.log("Disclosed (F-SALE2): pressure = (sum_j flowpct_j x shares_ij over |flow| >= 5% domestic-equity portfolios) / 20d median share volume, "
          "sign-checked: D1 = most negative = most flow-forced SELLING. Holdings = latest report before the quarter start (<= 6 months); flows from "
          "CRSP monthly TNA and returns summed over share classes per portfolio.")
