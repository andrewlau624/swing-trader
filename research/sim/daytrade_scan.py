"""Discovery scan: intraday structure among ultra-liquid ETFs (spread ~0 -> leverage-able).

Exploratory only. If a signal survives a 2016-2020 vs 2021-2026 split and costs, it
graduates to a prototype. Nothing here is adopted.

Run: PYTHONPATH=. .venv/bin/python -m research.sim.daytrade_scan
"""
from __future__ import annotations

import glob
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
M1 = ROOT / "data" / "research" / "night" / "m1"
CACHE = ROOT / "data" / "research" / "program" / "daytrade_scan_cache.pkl"

SYMS = ["SPY", "QQQ", "SMH", "SOXL", "TQQQ", "IWM", "EEM", "GLD", "TLT", "USO", "XLE"]
NMIN = 391  # 09:30 .. 16:00 inclusive (m=390 is the closing auction bar)


def load_matrices() -> dict:
    if CACHE.exists():
        return pickle.load(open(CACHE, "rb"))
    out = {}
    for s in SYMS:
        days, rows = [], []
        for f in sorted(glob.glob(str(M1 / f"{s}_*.parquet"))):
            df = pd.read_parquet(f)
            ts = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert("America/New_York")
            df = df.assign(et=ts, hm=ts.dt.strftime("%H:%M"), d=ts.dt.date)
            for d, g in df.groupby("d"):
                g = g.sort_values("et")
                # minute index from 09:30
                mm = (pd.to_datetime(g["et"]).dt.hour * 60 + pd.to_datetime(g["et"]).dt.minute) - 570
                sel = (mm >= 0) & (mm <= 390)
                if sel.sum() < 300:
                    continue
                o = np.full(NMIN, np.nan)
                hi = np.full(NMIN, np.nan)
                lo = np.full(NMIN, np.nan)
                cl = np.full(NMIN, np.nan)
                vo = np.full(NMIN, np.nan)
                o[mm[sel].values] = g["open"].values[sel]
                hi[mm[sel].values] = g["high"].values[sel]
                lo[mm[sel].values] = g["low"].values[sel]
                cl[mm[sel].values] = g["close"].values[sel]
                vo[mm[sel].values] = g["volume"].values[sel]
                # ffill close/high/low gaps (illiquid minutes)
                cl = pd.Series(cl).ffill().bfill().values
                hi = pd.Series(hi).ffill().bfill().values
                lo = pd.Series(lo).ffill().bfill().values
                o = np.where(np.isnan(o), cl, o)
                rows.append(np.vstack([o, hi, lo, cl, np.nan_to_num(vo)]))
                days.append(pd.Timestamp(d))
        A = np.stack(rows)  # [n_days, 5, NMIN]
        out[s] = dict(dates=pd.DatetimeIndex(days), A=A)
        print(s, A.shape)
    pickle.dump(out, open(CACHE, "wb"))
    return out


def ret_from_close(A, dec, exit_):
    c = A[:, 3]
    return c[:, exit_] / c[:, dec] - 1.0


def stats_by_period(dates, pnl, label):
    out = []
    for lo, hi, nm in [("2016", "2020", "16-20"), ("2021", "2026", "21-26")]:
        m = (dates >= f"{lo}-01-01") & (dates <= f"{hi}-12-31")
        x = pnl[m]
        x = x[np.isfinite(x)]
        if len(x) < 20:
            out.append(f"{nm}: n/a")
            continue
        t = x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))
        out.append(f"{nm}: n{len(x):5d} {x.mean()*1e4:+7.2f}bp t{t:+5.2f}")
    print(f"  {label:52s} " + " | ".join(out))


def main():
    M = load_matrices()
    dates = M["SPY"]["dates"]
    C = {s: M[s]["A"][:, 3] for s in SYMS}
    O = {s: M[s]["A"][:, 0] for s in SYMS}
    print(f"\ndays {len(dates)} {dates.min().date()}..{dates.max().date()}")

    def pool(series_list):
        """Equal-weight across ETFs by date."""
        return pd.concat(series_list, axis=1).mean(axis=1)

    def S(sym, p):
        return pd.Series(p, index=M[sym]["dates"])

    print("\n### A. Time-series intraday momentum / reversal (per ETF, pooled) ###")
    for dec, exit_ in [(30, 390), (60, 390), (120, 390), (330, 390)]:
        for sign, nm in [(1, "MOM"), (-1, "REV")]:
            allp = []
            for s in SYMS:
                r0 = C[s][:, dec] / O[s][:, 0] - 1.0
                fwd = ret_from_close(M[s]["A"], dec, exit_)
                allp.append(S(s, sign * np.sign(r0) * fwd))
            p = pool(allp)
            stats_by_period(p.index, p.values, f"{nm} open->{dec}min -> close")

    print("\n### B. Overnight gap -> intraday (open->close), per ETF pooled ###")
    for sign, nm in [(1, "contrarian"), (-1, "momentum")]:
        allp = []
        for s in SYMS:
            c = C[s]
            n = len(c)
            g = np.full(n, np.nan)
            g[1:] = O[s][1:, 0] / c[:-1, 390] - 1.0
            fwd = c[:, 390] / O[s][:, 0] - 1.0
            allp.append(S(s, sign * np.sign(g) * fwd))
        p = pool(allp)
        stats_by_period(p.index, p.values, f"gap {nm} (open->close)")

    print("\n### C. IBS at 15:00 (m=330) -> close, per ETF pooled ###")
    for thr in [0.2, 0.8]:
        allp = []
        for s in SYMS:
            A = M[s]["A"]
            cc, hh, ll = A[:, 3], A[:, 2], A[:, 1]
            day_hi = np.nanmax(hh[:, :331], axis=1)
            day_lo = np.nanmin(ll[:, :331], axis=1)
            ibs = (cc[:, 330] - day_lo) / (day_hi - day_lo + 1e-9)
            fwd = ret_from_close(A, 330, 390)
            sig = np.where(ibs < thr, 1.0, np.where(ibs > (1 - thr), -1.0, 0.0))
            allp.append(S(s, sig * fwd))
        p = pool(allp)
        stats_by_period(p.index, p.values, f"IBS<{thr} long / >{1-thr} short -> close")

    print("\n### D. Cross-asset 30-min lead/lag: leader open->30 predicts follower 30->60 ###")
    for L in SYMS:
        for F in SYMS:
            if L == F:
                continue
            lead = C[L][:, 30] / O[L][:, 0] - 1.0
            foll = C[F][:, 60] / C[F][:, 30] - 1.0
            p = np.sign(lead) * foll
            ser = pd.concat([S(L, p), S(F, p)], axis=1).mean(axis=1)
            loc = ser[np.isfinite(ser)]
            if len(loc) < 400:
                continue
            t = loc.mean() / (loc.std(ddof=1) / np.sqrt(len(loc)))
            if abs(t) > 2.2:
                stats_by_period(ser.index, ser.values, f"{L}->{F} cont")


if __name__ == "__main__":
    main()
