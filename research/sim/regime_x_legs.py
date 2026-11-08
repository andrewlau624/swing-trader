"""REGIME-X (N 1160-1164) leg cache: per-leg daily-bar book returns 1999-2026 at 5bp/side.
Same construction as upro_gate.book_series (REGIME-10M harness), but IBS and night kept separate.
  PYTHONPATH=.:../sharadar-data python3 -m research.sim.regime_x_legs"""
import pandas as pd
from research.sim import shar_crash as sc, nx
from sharadar import prices as sh_prices

F = sc.ROOT / "data/research/regime_x/legs.parquet"
COST = 5e-4


def build():
    Pp = nx.Paths(); master = nx.load_master(Pp); act = nx.read_table(Pp, "ACTIONS"); sep = nx.read_table(Pp, "SEP"); sfp = nx.read_table(Pp, "SFP")
    parts = []
    for lo, hi in (("1999-01-04", "2015-12-31"), ("2016-01-04", "2026-09-18")):
        lo, hi = pd.Timestamp(lo), pd.Timestamp(hi)
        df = sh_prices(sc.EQ18, (lo - pd.Timedelta(days=420)).strftime("%Y-%m-%d"), (hi + pd.Timedelta(days=10)).strftime("%Y-%m-%d"), adjust="split", source="funds")
        df = df[df.ticker.isin(sc.EQ18)].assign(date=pd.to_datetime(df.date))
        O, H, L_, C = [df.pivot(index="date", columns="ticker", values=c).sort_index() for c in ("open", "high", "low", "close")]
        idx = C.index[(C.index >= lo) & (C.index <= hi)]
        ibs = (sc.ibs_daily(O, H, L_, C) - 2 * COST).reindex(idx).fillna(0.0)
        bars = pd.concat([t[(t.date >= lo - sc.PAD) & (t.date <= hi + sc.PAD)] for t in (sep, sfp)], ignore_index=True)
        bars = bars.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
        tr = nx.collect_trades(nx.build_panel(bars), master, act, "primary", lo, hi)["trades"]
        ngt = tr.groupby("date").apply(lambda g: float((g.per * (g.ret - 2 * COST)).sum())).reindex(idx).fillna(0.0)
        parts.append(pd.DataFrame({"ibs": ibs, "night": ngt}))
    s = pd.concat(parts); s.index = pd.to_datetime(s.index)
    s.to_parquet(F)
    return s


if __name__ == "__main__":
    s = build()
    bk = pd.read_parquet(sc.ROOT / "data/research/upro_gate/book.parquet")["r"]
    chk = (0.5 * s.ibs + 0.5 * s.night - bk.reindex(s.index)).abs().max()
    print(len(s), s.index.min(), s.index.max(), "max |diff vs book.parquet|", chk)
