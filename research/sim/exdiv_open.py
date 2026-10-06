"""Study EXDIV-OPEN: ex-date open-auction under-adjustment, judged on official SIP cross prints 2021-2026.

Pre-registration: "Amendment — Study EXDIV-OPEN" in research/drafts/round1_prose.md (program N 843 -> 846).
Arms: A ex-dividend (yield >= 0.6%), B forward-split ex-date, C spin-off parent ex-date.

Trade: buy the closing cross on T-1, sell the opening cross on T. P&L adds the dividend (A) or applies the split ratio
(B). Judged excess = P&L minus the same ticker's mean official overnight return on nights T-35..T-5 (sessions).

    PYTHONPATH=. .venv/bin/python -m research.sim.exdiv_open
"""
from __future__ import annotations

import glob
import json
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from lh_panel import Panel, cluster_t  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/exdiv"
OUT = pathlib.Path(__file__).resolve().parent / "exdiv_open_out.txt"
STORE = pathlib.Path.home() / "data" / "sharadar"
YMIN = 0.006


def crosses(rows: list[dict]) -> pd.DataFrame:
    """date -> official open/close cross (largest-size print) price and size."""
    out = []
    for x in rows:
        o = max(x["o"], key=lambda q: q.get("s", 0)) if x.get("o") else None
        c = max(x["c"], key=lambda q: q.get("s", 0)) if x.get("c") else None
        out.append((pd.Timestamp(x["d"]), o["p"] if o else np.nan, o["s"] if o else np.nan,
                    c["p"] if c else np.nan, c["s"] if c else np.nan))
    return pd.DataFrame(out, columns=["d", "op", "os", "cp", "cs"]).drop_duplicates("d").set_index("d").sort_index()


def overnight(x: pd.DataFrame) -> pd.Series:
    """Official close cross d-1 -> open cross d, raw, indexed by d."""
    return x["op"] / x["cp"].shift(1) - 1


def judge(df: pd.DataFrame, spy_on: pd.Series, label: str, log) -> None:
    df = df.dropna(subset=["pnl", "plac"]).copy()
    df["x"] = df.pnl - df.plac
    df["xspy"] = df.x - (spy_on.reindex(df.d).to_numpy() - spy_on.rolling(31).mean().shift(5).reindex(df.d).to_numpy())
    g = df.d.dt.strftime("%Y-%m-%d")
    m, t = cluster_t(df.x, g)
    ms, ts = cluster_t(df.xspy, g)
    srt = np.sort(df.x.to_numpy())
    h1 = df[df.d.dt.year <= 2023].x.mean()
    h2 = df[df.d.dt.year >= 2024].x.mean()
    log(f"{label}: n={len(df)} sessions={g.nunique()} excess {m*1e4:+.1f}bp t {t:.2f} median {df.x.median()*1e4:+.1f}bp "
        f"hit {(df.x > 0).mean()*100:.0f}% ex-top5 {srt[:-5].mean()*1e4:+.1f}bp | halves 21-23 {h1*1e4:+.1f} "
        f"24-26 {h2*1e4:+.1f} | SPY-adj {ms*1e4:+.1f}bp t {ts:.2f} | raw pnl {df.pnl.mean()*1e4:+.1f}bp "
        f"placebo {df.plac.mean()*1e4:+.1f}bp")
    checks = [m > 0 and t >= 2, h1 > 0 and h2 > 0, df.x.median() > 0, srt[:-5].mean() > 0, m > 5e-4, ms > 0]
    verdict = "PASS" if all(checks) else ("FAIL" if (m <= 0 or t < 1) else "WEAK")
    log(f"   checks {['t', 'halves', 'median', 'ex-top5', '>5bp', 'spy-adj']} = {checks} -> {verdict}")
    return df


def main() -> None:
    lines: list[str] = []

    def log(s=""):
        print(s)
        lines.append(s)

    P = Panel.load()
    spy = crosses(json.load(open(D / "spy.json"))["SPY"])
    spy_on = overnight(spy)

    # ---- arm A: ex-dividend
    hist: dict[str, pd.DataFrame] = {}
    for f in sorted(glob.glob(str(D / "auction" / "b*.json"))):
        for s, v in json.load(open(f)).items():
            hist[s] = crosses(v)
    a = pd.read_parquet(STORE / "actions.parquet", columns=["date", "action", "ticker", "value"])
    a["date"] = pd.to_datetime(a["date"])
    dv = a[(a.action == "dividend") & a.ticker.isin(hist) & (a.date >= "2021-02-01")].drop_duplicates(["ticker", "date"])
    rows = []
    for r in dv.itertuples():
        x = hist[r.ticker]
        if r.date not in x.index:
            continue
        k = x.index.get_loc(r.date)
        if k < 36:
            continue
        g = P.row_at(r.ticker, r.date)
        if g < 1 or P.dates[P.di[g]] != np.datetime64(r.date):
            continue
        y = 1 - P.fac[g - 1] / P.fac[g]  # dividend / close(T-1) implied by the vendor's adjustment factor
        c0, o1 = x.cp.iloc[k - 1], x.op.iloc[k]
        on = overnight(x)
        exd = set(dv[dv.ticker == r.ticker].date)
        pl = on.iloc[k - 35:k - 4]
        pl = pl[~pl.index.isin(exd)]
        rows.append(dict(ticker=r.ticker, d=r.date, yld=float(y), pnl=(o1 + y * c0) / c0 - 1, plac=pl.mean(),
                         shar_on=P.tro[g] / P.tr[g - 1] - 1, ccs=x.cs.iloc[k - 1] * c0, ocs=x.os.iloc[k] * o1,
                         id_x=(x.cp.iloc[k] / o1 - 1)))
    A = pd.DataFrame(rows)
    log(f"EXDIV-OPEN arm A (ex-dividend), official SIP crosses 2021-2026; tickers with crosses: {len(hist)}")
    A = A[(A.yld >= YMIN) & (A.yld < 0.2)]
    Aj = judge(A, spy_on, "A yield>=0.6%", log)
    for lo, hi in ((0.006, 0.01), (0.01, 0.02), (0.02, 0.2)):
        s = Aj[(Aj.yld >= lo) & (Aj.yld < hi)]
        log(f"   yield {lo:.3f}-{hi:.3f}: n={len(s)} excess {s.x.mean()*1e4:+.1f}bp median {s.x.median()*1e4:+.1f}bp")
    log(f"   vendor (Sharadar) overnight TR on the same events: {(Aj.shar_on).mean()*1e4:+.1f}bp vs official raw pnl "
        f"{Aj.pnl.mean()*1e4:+.1f}bp")
    log(f"   ex-day session (open cross -> close cross, raw, no div): {Aj.id_x.mean()*1e4:+.1f}bp")
    per = Aj.groupby(Aj.d.dt.year).x.agg(["count", "mean", "median"])
    log("   by year (bp): " + "; ".join(f"{y} n{int(c)} {m*1e4:+.1f}/{md*1e4:+.1f}" for y, (c, m, md) in per.iterrows()))
    nday = Aj.groupby("d").size()
    log(f"   events/session: mean {nday.mean():.1f}, sessions with >=1 {len(nday)} of ~{252*5.7:.0f}; "
        f"median close-cross $ {Aj.ccs.median()/1e6:.1f}M, open-cross $ {Aj.ocs.median()/1e6:.2f}M, "
        f"p10 open-cross $ {Aj.ocs.quantile(.1)/1e3:.0f}k")
    Aj.to_csv(D / "armA.csv", index=False)

    # ---- arms B, C
    for arm, name in (("B", "forward split"), ("C", "spin-off parent")):
        rows = []
        sp = a[(a.action == ("split" if arm == "B" else "spinoff"))]
        for f in sorted(glob.glob(str(D / "events" / f"{arm}_*.json"))):
            _, t, d = pathlib.Path(f).stem.split("_")
            v = json.load(open(f))
            if t not in v:
                continue
            x = crosses(v[t])
            d = pd.Timestamp(d)
            if d not in x.index:
                continue
            k = x.index.get_loc(d)
            if k < 36:
                continue
            ratio = float(sp[(sp.ticker == t) & (sp.date == d)].value.iloc[0]) if arm == "B" else 1.0
            on = overnight(x)
            if arm == "B":
                on.iloc[k] = x.op.iloc[k] * ratio / x.cp.iloc[k - 1] - 1
            c0 = x.cp.iloc[k - 1]
            if arm == "C":  # child value via the vendor's spin-off adjustment factor (as for a dividend)
                g = P.row_at(t, d)
                if g < 1 or P.dates[P.di[g]] != np.datetime64(d):
                    continue
                on.iloc[k] = (x.op.iloc[k] + (1 - P.fac[g - 1] / P.fac[g]) * c0) / c0 - 1
            if c0 < 5 or c0 * x.cs.iloc[k - 1] < 1e5:
                continue
            rows.append(dict(ticker=t, d=d, pnl=on.iloc[k], plac=on.iloc[k - 35:k - 4].mean(),
                             ocs=x.os.iloc[k] * x.op.iloc[k], id_x=x.cp.iloc[k] / x.op.iloc[k] - 1))
        X = pd.DataFrame(rows)
        log("")
        log(f"EXDIV-OPEN arm {arm} ({name}), official SIP crosses 2021-2026 (close(T-1) >= $5, close cross >= $100k)")
        if len(X) >= 10:
            Xj = judge(X, spy_on, f"{arm}", log)
            log(f"   ex-day session (open cross -> close cross): {Xj.id_x.mean()*1e4:+.1f}bp; median open-cross $ "
                f"{Xj.ocs.median()/1e6:.2f}M")
            Xj.to_csv(D / f"arm{arm}.csv", index=False)
        else:
            log(f"   n={len(X)} too few")
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
