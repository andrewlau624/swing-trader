"""Index-beat A9: the IBS leg's rule on closed-end funds, in the IBS half's idle cash.

    PYTHONPATH=. .venv/bin/python -m research.sim.ib_a9 fetch
    PYTHONPATH=. .venv/bin/python -m research.sim.ib_a9 explore        # 2021-23 only (select half)

Spec (index_beat_log.md, written before any bar was fetched): universe U below, kept if 2020 median daily $ volume
>= $2M. V1 = live IBS rule on U (momentum top-3 monthly, IBS <= 0.2, next open -> open after); V2 = the 3 lowest-IBS
names with IBS <= 0.10, no momentum filter. Returns from dividend-adjusted bars; cost B.cost_bps('tier') per side on
the raw price and 20d ADV. Capital = the IBS half's idle cash (0.5E - IBS used) in the taxable V7 book.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

from swingtrader.daily import signals as sg

from . import book as B
from . import roth_opt as RO

ROOT = pathlib.Path(__file__).resolve().parents[2]
CACHE = ROOT / "data/research/program/ib/cef"
SELECT = ("2021-01-01", "2023-12-31")
U = """ADX GAM USA CLM CRF GAB GDV GGT GUT EOS EOI ETY ETV ETW ETB ETJ EXG EXD BDJ BOE BME BMEZ BST BSTZ BUI BIGZ CII BGY
STK QQQX SPXX DIAX BXMX NFJ CHI CHY CHW CSQ PTY PDI PDO PCN PFN PHK PCM RCS PFL PFO NCV NCZ ACV NIE AWP RA RQI RNP RFI
UTF UTG UTL BTZ BIT DSL DBL HYT JPC JQC JFR NVG NEA NAD NZF NMZ NUV NIM NXP KYN NML CEM EMO DNP DPG GOF GLO GLV GLQ
HQH HQL THQ THW IGD IGA IDE IIF ASA ASGI ECAT FPF FFC FLC HTD HPI HPF HPS DFP PSF JRI JCE EVT EVV EFR EFT EIM EVN AOD
AGD AVK BGT BHK BKT BLW BNY BYM BFK MUI MYI MQY MHN EIM KIO FSCO OXLC ECC XFLT OPP RIV NRO NHS GHY SDHY BCX BGR NDP""".split()


def _fetch(symbols, adj):
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from swingtrader.daily.marketdata import _clients, trade_date
    data, _ = _clients()
    d = CACHE / adj
    d.mkdir(parents=True, exist_ok=True)
    need = [s for s in sorted(set(symbols)) if not (d / f"{s}.parquet").exists()]
    for i in range(0, len(need), 40):
        chunk = need[i:i + 40]
        try:
            df = data.get_stock_bars(StockBarsRequest(symbol_or_symbols=chunk, timeframe=TimeFrame.Day,
                                                      start=pd.Timestamp("2015-10-01", tz="UTC"),
                                                      end=pd.Timestamp("2026-09-30", tz="UTC"), feed="sip",
                                                      adjustment=adj)).df
        except Exception as exc:
            print("fetch failed", chunk[:3], str(exc)[:80]); continue
        df = df.reset_index(); df["date"] = trade_date(df["timestamp"])
        for s, g in df.groupby("symbol"):
            g.set_index("date")[["open", "high", "low", "close", "volume"]].to_parquet(d / f"{s}.parquet")
        print(f"  {adj} {i + len(chunk)}/{len(need)}", flush=True)


def panels():
    P = {}
    for adj in ("all", "raw"):
        fr = {}
        for f in (CACHE / adj).glob("*.parquet"):
            g = pd.read_parquet(f); g.index = pd.to_datetime(g.index)
            fr[f.stem] = g
        P[adj] = {k: pd.DataFrame({s: g[k] for s, g in fr.items()}).sort_index() for k in ("open", "high", "low", "close", "volume")}
    return P


def universe(P):
    raw = P["raw"]
    dv = (raw["close"] * raw["volume"])["2020-01-01":"2020-12-31"].median()
    return sorted(dv[dv >= 2e6].index)


def cef_days(P, uni, variant, end):
    """day d -> [(sym, raw open d+1, open d+2 / open d+1 - 1 (dividend-adjusted), cost bp/side)] as book.ibs_days."""
    A, R = P["all"], P["raw"]
    O, H, L, C = (A[k][uni] for k in ("open", "high", "low", "close"))
    adv = (R["close"] * R["volume"])[uni].rolling(20).median().shift(1)
    days = C.index[C.index <= end]
    out, mom = {}, {}
    for j in range(260, len(days) - 2):
        d, nxt, nx2 = days[j], days[j + 1], days[j + 2]
        rng = (H.loc[d] - L.loc[d])
        ibs = ((C.loc[d] - L.loc[d]) / rng).where(rng > 0)
        if variant == "V1":
            m = nxt.to_period("M")
            if m not in mom:
                mom[m] = sg.momentum_top(C[C.index < nxt].dropna(axis=1, how="all"), nxt, 3)
            last = {s: {"high": H.at[d, s], "low": L.at[d, s], "close": C.at[d, s]} for s in mom[m]
                    if np.isfinite(C.at[d, s])}
            tg = sg.ibs_targets(last, 0.2)
        else:
            x = ibs.dropna()
            tg = list(x[x <= 0.10].nsmallest(3).index)
        legs = []
        for s in tg:
            o1, o2, p = O.at[nxt, s], O.at[nx2, s], R["open"].at[nxt, s]
            if np.isfinite(o1) and np.isfinite(o2) and np.isfinite(p) and np.isfinite(adv.at[nxt, s]):
                c = float(B.cost_bps("tier", np.array([p]), np.array([adv.at[nxt, s]]))[0])
                legs.append((s, float(p), o2 / o1 - 1, c))
        if legs:
            out[d] = legs
    return out


def book_increment(s, cefd, E0, a, b, whole=True):
    """Run the taxable V7 book's IBS-idle cash through the CEF trades: increment $ per day / E (fixed capital E0)."""
    I = s.I
    inc = {}
    for d in s.days[(s.days >= a) & (s.days <= b)]:
        used = 0.0
        legs = I.get(d, [])
        if legs:
            used = 0.5 * E0          # the IBS leg splits its half across its picks (as live): no idle cash
        idle = 0.5 * E0 - used
        x = 0.0
        if idle > 0 and d in cefd:
            per = idle / len(cefd[d])
            for sym, p, r, c in cefd[d]:
                q = np.floor(per / p) if whole else per / p
                x += q * p * (r - 2 * c / 1e4 - RO.bil(s, d))     # the cash leaves BIL for the day
        inc[d] = x / E0
    return pd.Series(inc)


def explore():
    from .validate import load_sim
    P = panels()
    uni = universe(P)
    print(f"universe: {len(uni)} of {len(U)} CEFs with 2020 median $vol >= $2M")
    s = load_sim(raw_price=True)
    for v in ("V1", "V2"):
        cd = cef_days(P, uni, v, pd.Timestamp(SELECT[1]))
        tr = pd.DataFrame([(d, *x) for d, L in cd.items() for x in L], columns=["d", "sym", "p", "r", "c"])
        tr = tr[(tr.d >= SELECT[0]) & (tr.d <= SELECT[1])]
        net = (tr.r - 2 * tr.c / 1e4) * 1e4
        t = net.mean() / net.std() * np.sqrt(len(net))
        print(f"{v}: trades {len(tr)} ({len(tr) / 3:.0f}/yr), gross {tr.r.mean() * 1e4:+.1f}bp, cost/side {tr.c.mean():.1f}bp, "
              f"net {net.mean():+.1f}bp t {t:+.2f}, hit {(net > 0).mean():.0%}; by year "
              + " ".join(f"{y}: {g.mean():+.1f}" for y, g in net.groupby(tr.d.dt.year)))
        for E0, wh in ((10000, False), (10000, True), (2300, True)):
            inc = book_increment(s, cd, E0, *SELECT, whole=wh)
            cagr = (1 + inc).prod() ** (252 / len(inc)) - 1
            print(f"   increment on IBS-idle cash at ${E0:,} {'whole' if wh else 'frac'}: {cagr * 100:+.2f}pp/yr pre-tax "
                  f"(days in a CEF {(inc != 0).mean():.0%})")


if __name__ == "__main__":
    if sys.argv[1:2] == ["fetch"]:
        _fetch(U, "all"); _fetch(U, "raw")
    else:
        explore()
