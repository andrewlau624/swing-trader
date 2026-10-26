"""ETF-PD (N 1059): own-history ETF discount -> next-session reversion, all US ETFs 2010-26 (CRSP daily NAV + Sharadar SFP).
Pre-registration: round1_prose.md "Study ETF-PD". Run: .venv/bin/python -m research.sim.etf_pd pull|run
"""
from __future__ import annotations

import pathlib
import re
import sys

import numpy as np
import pandas as pd

from . import winsig as W

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data" / "research" / "etf_pd"
OUT = ROOT / "data" / "research" / "program" / "etf_pd_out.txt"
COST, SHOCK = 10e-4, 30e-4
HALVES = (("2010-01-01", "2017-12-31"), ("2018-01-01", "2026-12-31"))
INTL = re.compile(r"(?i)MSCI|Emerging|EAFE|Europe|Japan|China|India|Pacific|Global|International|Intl|World|Brazil|Korea|Taiwan|Mexico|Canada|"
                  r"Australia|Germany|United Kingdom|Asia|Latin|Africa|Frontier|Developed|Ex[- ]?US|Foreign|Country")
BOND = re.compile(r"(?i)Bond|Treasury|Credit|Yield|Municipal|Muni|Fixed Income|Aggregate|Corporate|Floating|TIPS|Mortgage|Debt|Income Fund|Bill")


def pull():
    import wrds
    db = wrds.Connection(wrds_username="andrewlau624", wrds_connect_attempts=2)
    q = """select n.crsp_fundno, n.caldt, n.dnav, h.ticker, h.fund_name
           from crsp_q_mutualfunds.daily_nav n
           join crsp_q_mutualfunds.fund_hdr_hist h on h.crsp_fundno = n.crsp_fundno and n.caldt between h.chgdt and h.chgenddt
           where h.et_flag = 'F' and n.caldt >= '2009-10-01' and n.dnav > 0 and h.ticker is not null"""
    t = db.raw_sql(q)
    t["caldt"] = pd.to_datetime(t["caldt"])
    D.mkdir(parents=True, exist_ok=True)
    t.to_parquet(D / "nav.parquet")
    print("nav rows", len(t), "funds", t.crsp_fundno.nunique(), "tickers", t.ticker.nunique(), t.caldt.min(), t.caldt.max())


def panel() -> pd.DataFrame:
    nav = pd.read_parquet(D / "nav.parquet").rename(columns={"caldt": "date"})
    nav = nav.drop_duplicates(["ticker", "date"], keep="last")
    px = W.load_panel(kind="etf")[["ticker", "date", "open", "close", "closeunadj", "adv20"]]
    px = px[px.date >= "2009-10-01"]
    t = px.merge(nav[["ticker", "date", "dnav", "fund_name"]], on=["ticker", "date"], how="inner")
    t = t.sort_values(["ticker", "date"]).reset_index(drop=True)
    f = t.closeunadj / t.close
    t["O"], t["C"] = t.open * f, t.closeunadj
    t["prem"] = t.C / t.dnav - 1
    t.loc[t.prem.abs() > 0.20, "prem"] = np.nan
    g = t.groupby("ticker", sort=False)
    med60 = g["prem"].transform(lambda s: s.shift(1).rolling(60, min_periods=60).median())
    t["z"] = t.prem - med60
    sh = lambda c, k: g[c].shift(-k)
    t["s1"] = sh("C", 1) / sh("O", 1) - 1
    t["n1"] = sh("O", 2) / sh("O", 1) - 1
    t["w5"] = sh("C", 5) / sh("O", 1) - 1
    t["dnav1"] = sh("dnav", 1) / t.dnav - 1          # NAV change into d+1 (stale-NAV test)
    t["dpx1"] = sh("C", 1) / t.C - 1                  # close-to-close price change
    t["cat"] = np.where(t.fund_name.str.contains(BOND), "bond", np.where(t.fund_name.str.contains(INTL), "intl", "dom/other"))
    u = t.z.notna() & (t.C >= 5) & (t.adv20 >= 1e6) & t.s1.notna()
    t = t[u].copy()
    for c in ("s1", "n1", "w5"):
        t[f"x_{c}"] = t[c] - t.groupby("date")[c].transform("mean")
    t["dec"] = t.groupby("date")["z"].transform(lambda s: pd.qcut(s.rank(method="first"), 10, labels=False) + 1 if len(s) >= 20 else np.nan)
    return t


def stats(s: pd.DataFrame, col: str, cost=COST) -> dict:
    x = s[col]
    d = x.groupby(s.date).mean()
    h = [d[(d.index >= a) & (d.index <= b)].mean() * 1e4 for a, b in HALVES]
    return dict(n=len(x), days=len(d), mean=x.mean() * 1e4, net=(x.mean() - cost) * 1e4, med=x.median() * 1e4, hit=(x > 0).mean(),
                t=W.nw_t(d, 1), h1=h[0], h2=h[1], ex5=d.sort_values().iloc[:-5].mean() * 1e4 if len(d) > 10 else np.nan,
                shock=(x.mean() - SHOCK) * 1e4)


def fmt(lab, r):
    return (f"{lab:42} n {r['n']:7} mean {r['mean']:+6.1f} net {r['net']:+6.1f} med {r['med']:+6.1f} hit {r['hit']:.0%} t {r['t']:+5.2f} "
            f"halves {r['h1']:+5.1f}/{r['h2']:+5.1f} ex5 {r['ex5']:+5.1f} shock {r['shock']:+6.1f}")


def run():
    t = panel()
    L = [f"ETF-PD (N 1059) one look {pd.Timestamp.today():%Y-%m-%d}. {t.ticker.nunique()} ETFs, {len(t)} name-days, {t.date.nunique()} days "
         f"{t.date.min():%Y-%m-%d}..{t.date.max():%Y-%m-%d}. z = premium - own 60d median; deciles daily; excess vs EW same-day universe; "
         f"cost {COST*1e4:.0f}bp RT, shock {SHOCK*1e4:.0f}bp."]
    L.append(f"premium (bp) distribution: median {t.prem.median()*1e4:+.1f}, p10 {t.prem.quantile(.1)*1e4:+.1f}, p90 {t.prem.quantile(.9)*1e4:+.1f}; "
             f"z p10 {t.z.quantile(.1)*1e4:+.1f}, p90 {t.z.quantile(.9)*1e4:+.1f}")
    for leg in ("s1", "n1", "w5"):
        dm = t.groupby("dec")[f"x_{leg}"].mean() * 1e4
        L.append(f"deciles {leg} (bp excess, D1 deepest discount): " + " ".join(f"D{int(k)}:{v:+.1f}" for k, v in dm.items()))
    d1, d10 = t[t.dec == 1], t[t.dec == 10]
    L.append("\n-- D1 (deepest discount) --")
    res = {}
    for leg in ("s1", "n1", "w5"):
        res[leg] = stats(d1, f"x_{leg}")
        L.append(fmt(f"D1 {leg}", res[leg]))
    L.append("-- D10 (highest premium) --")
    for leg in ("s1", "n1", "w5"):
        L.append(fmt(f"D10 {leg}", stats(d10, f"x_{leg}")))
    L.append("-- D1 s1 by category / ADV bucket --")
    for c, s in d1.groupby("cat"):
        L.append(fmt(f"D1 s1 {c}", stats(s, "x_s1")))
    b5 = d1[d1.adv20 >= 5e6]
    r5 = stats(b5, "x_s1", cost=SHOCK)
    L.append(fmt("D1 s1 ADV>=$5M at 30bp RT  [bar >= +10]", r5))
    for lo, hi, lab in [(1e6, 5e6, "$1-5M"), (5e6, 50e6, "$5-50M"), (50e6, 1e12, ">$50M")]:
        L.append(fmt(f"D1 s1 ADV {lab}", stats(d1[(d1.adv20 >= lo) & (d1.adv20 < hi)], "x_s1")))
    yr = d1.groupby(d1.date.dt.year)["x_s1"].agg(["mean", "size"])
    L.append("D1 s1 by year (bp/n): " + " ".join(f"{y}:{v['mean']*1e4:+.0f}/{int(v['size'])}" for y, v in yr.iterrows()))
    L.append("\n-- mechanism: slope of next-day NAV change and price change on z (bp per 100bp of z), by category --")
    for c, s in t.groupby("cat"):
        s = s.dropna(subset=["dnav1", "dpx1", "z"])
        bn = np.polyfit(s.z, s.dnav1, 1)[0]; bp = np.polyfit(s.z, s.dpx1, 1)[0]
        L.append(f"   {c:10} n {len(s):8}  dNAV(d+1)/z {bn*100:+6.1f}   dPx(d+1)/z {bp*100:+6.1f}   (stale NAV: NAV slope > 0; mispricing: price slope < 0)")
    dm5 = t.groupby("dec")["x_s1"].mean() * 1e4
    mono = dm5.get(1, np.nan) > dm5.get(5, np.nan) > dm5.get(10, np.nan)
    r = res["s1"]
    ok = r["net"] >= 15 and r["t"] >= 3 and min(r["h1"], r["h2"]) > 0 and r["med"] > 0 and r["ex5"] > 0 and mono and r5["net"] >= 10
    L.append(f"\nVERDICT (registered): {'PASS' if ok else 'KILL'}  (monotone {mono}, ADV>=$5M net@30bp {r5['net']:+.1f})")
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    {"pull": pull, "run": run}[sys.argv[1]]()
