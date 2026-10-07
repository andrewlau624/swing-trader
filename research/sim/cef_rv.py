"""Study CEF-RV: discount-to-NAV anchored reversion on the CEFConnect weekly panel.

Pre-registration in round1_prose.md ("Study CEF-RV"; machinery-development; the FIRST judged run
of the program's two-leg machinery: leg A = CEF price (Sharadar SFP daily bars, raw closes +
dividend credit), leg B = the NAV anchor (CEFConnect weekly series; frozen bands = own trailing-52w
10th pct in / own median out). Judge 2016-2026; live-funds survivorship caveat documented.

  .venv/bin/python research/sim/cef_rv.py
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
STORE = pathlib.Path.home() / "data" / "sharadar"
CEF = ROOT / "data" / "research" / "cefconnect"
OUT = pathlib.Path(__file__).resolve().parent / "cef_rv_out.txt"

LO, HI = pd.Timestamp("2016-01-01"), pd.Timestamp("2026-10-05")
COST = 0.005
DELIST_ACTIONS = {"delisted", "bankruptcyliquidation", "regulatorydelisting", "voluntarydelisting"}


def load_nav() -> pd.DataFrame:
    panel = pd.read_parquet(CEF / "cef_panel.parquet")
    panel["disc"] = panel["price"] / panel["nav"] - 1.0  # sign: premium positive
    return panel[["ticker", "date", "disc"]].sort_values(["ticker", "date"], kind="stable")


def load_sfp(tickers: list[str], lo: pd.Timestamp = LO, hi: pd.Timestamp = HI) -> pd.DataFrame:
    f = pd.read_parquet(
        STORE / "funds.parquet",
        columns=["ticker", "date", "close", "closeunadj", "closeadj"],
        filters=[("date", ">=", lo - pd.Timedelta(days=10)), ("date", "<=", hi)])
    f = f[f["ticker"].isin(tickers)].copy()
    f["dt"] = pd.to_datetime(f["date"]).dt.normalize()
    return f.sort_values(["ticker", "dt"], kind="stable").reset_index(drop=True)


def next_close(fS: pd.DataFrame, t: str, d: pd.Timestamp) -> tuple[int, float] | None:
    g = fS[fS["ticker"] == t]
    dd = g["dt"].to_numpy("datetime64[ns]")
    if len(g) == 0:
        return None
    # strictly AFTER d: the signal needs NAV(d), published after d's close
    pos = int(np.searchsorted(dd, np.datetime64(d, "ns"), side="right"))
    if pos >= len(g):
        return None
    # a signal before the loaded price window would otherwise take the window's first close (months late)
    if dd[pos] - np.datetime64(d, "ns") > np.timedelta64(14, "D"):
        return None
    # split- and distribution-adjusted total-return close (raw closes break across reverse splits)
    return pos, float(g["closeadj"].iloc[pos])


def build_trades(nav: pd.DataFrame, fS: pd.DataFrame) -> pd.DataFrame:
    """The frozen CEF-RV rule over every panel week that has SFP prices in fS."""
    rows: list[dict] = []
    for t, g in nav.groupby("ticker"):
        g = g.sort_values("date").reset_index(drop=True)
        if len(g) < 60:
            continue
        d = g["disc"].to_numpy(float)
        hold: int | None = None
        entry_px = None
        entry_date = None
        for i in range(56, len(g)):
            win = d[max(0, i - 51): i + 1]
            q10, med = float(np.nanpercentile(win, 10)), float(np.nanpercentile(win, 50))
            if not np.isfinite(d[i]):
                continue
            if hold is None:
                if d[i] <= q10:
                    entry = next_close(fS, t, g["date"][i])
                    if entry is not None:
                        hold, entry_px, entry_date = 0, entry[1], g["date"][i]
            else:
                hold += 1
                if d[i] >= med or (g["date"][i] - entry_date).days > 260:
                    out = next_close(fS, t, g["date"][i])
                    if out is not None and out[0] > 0:
                        ret = out[1] / entry_px - 1  # closeadj already carries distributions
                        rows.append(dict(ticker=t, edate=str(entry_date)[:10],
                                         xdate=str(g["date"][i])[:10], ret=float(ret),
                                         disc_in=float(d[max(0, i - hold)]), med=med, q10=q10,
                                         hold_weeks=hold))
                    hold, entry_px, entry_date = None, None, None
    return pd.DataFrame(rows)


def main() -> int:
    nav = load_nav()
    tr = build_trades(nav, load_sfp(sorted(nav["ticker"].unique())))
    gross = tr["ret"].to_numpy(float)
    net_judge = gross - COST
    edate = pd.to_datetime(tr["edate"]).values.astype("datetime64[ns]")
    dd = pd.DataFrame({"edate": edate, "net": net_judge})
    by = dd.groupby("edate")["net"].mean().sort_index()
    x, n_w = by.to_numpy(), len(by)
    cl_sum = pd.Series(x - x.mean()).groupby(by.index.to_numpy()).sum().to_numpy()
    t_cl = x.mean() / np.sqrt(((cl_sum ** 2).sum() / (n_w - 1) / n_w)) if n_w > 1 else float("nan")
    mid = pd.Timestamp("2021-06-01")
    h1, h2 = by[by.index < mid], by[by.index >= mid]
    order = np.argsort(-net_judge)
    ex5 = float(np.delete(net_judge, order[: min(5, len(net_judge))]).mean())
    o5 = np.delete(net_judge, order[: min(5, len(net_judge))])
    gate = bool(len(tr) >= 300 and np.isfinite(t_cl) and t_cl >= 2.0 and h1.mean() > 0
                and h2.mean() > 0 and np.median(net_judge) > 0 and (net_judge > 0).mean() >= 0.55)
    line = [
        f"trades {len(tr)} funds {tr['ticker'].nunique()} weeks {n_w}",
        f"mean net {np.mean(net_judge)*1e4:.1f}bp med {np.median(net_judge)*1e4:.1f}bp "
        f"t_cl {t_cl:.2f} hit {(net_judge > 0).mean():.1%}",
        f"halves {h1.mean()*1e4:.1f} / {h2.mean()*1e4:.1f}bp; ex-top-5 {ex5*1e4:.1f}bp",
        f"shock2x {np.mean(net_judge - COST) * 1e4:.1f}bp shock3x {np.mean(gross - 0.015) * 1e4:.1f}bp",
        f"gross pctiles {np.percentile(gross*1e4, [1,10,50,90,99]).round(1).tolist()}",
        f"PASS={gate}",
    ]
    OUT.write_text("\n".join(line) + "\n")
    tr.to_csv(CEF / "cef_rv_trades.csv", index=False)
    print("\n".join(line), flush=True)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
