"""Study INTL-PREF (pre-reg round1_prose.md, N 1021 -> 1022): PREF-EX rule on TSX $25-par preferreds.
Data: WRDS Datastream tr_ds_equities (ds2ctryqtinfo typecode PREF region CA; ds2primqtprc exch 197 Toronto raw OHLCV; ds2div effectivedate = ex-date).
Usage: .venv/bin/python -m research.sim.intl_pref   (cache: data/research/intl_pref/)
"""
from __future__ import annotations
import pathlib, numpy as np, pandas as pd
D = pathlib.Path("data/research/intl_pref"); D.mkdir(parents=True, exist_ok=True)
OUT = pathlib.Path("data/research/program/intl_pref_out.txt")


def fetch():
    f1, f2, f3 = D / "px.parquet", D / "div.parquet", D / "info.parquet"
    if f1.exists() and f2.exists() and f3.exists():
        return pd.read_parquet(f1), pd.read_parquet(f2), pd.read_parquet(f3)
    from research.sim.borrow_xs import conn
    db = conn()
    info = db.raw_sql("select infocode,dscode,dsqtname,dslocalcode,statuscode,delistdate,primisocurrcode from tr_ds_equities.ds2ctryqtinfo where region='CA' and typecode='PREF'")
    ics = [int(x) for x in info.infocode.dropna().unique()]
    px, dv = [], []
    for i in range(0, len(ics), 100):
        ch = ",".join(map(str, ics[i:i + 100]))
        px.append(db.raw_sql(f"select infocode,marketdate,open_,high,low,close_,volume,isocurrcode from tr_ds_equities.ds2primqtprc where exchintcode=197 and infocode in ({ch}) and marketdate>='2004-01-01'"))
        dv.append(db.raw_sql(f"select infocode,divtypecode,divrate,isocurrcode,effectivedate,effdateestflag,recorddate,paydate from tr_ds_equities.ds2div where infocode in ({ch}) and effectivedate>='2004-06-01'"))
    px, dv = pd.concat(px), pd.concat(dv)
    px.to_parquet(f1); dv.to_parquet(f2); info.to_parquet(f3)
    return px, dv, info


def line(e, c):
    day = e.groupby("date")[c].mean()
    t = day.mean() / day.std() * np.sqrt(len(day))
    yrs = e.groupby(e.date.dt.year)[c].mean()
    return (f"{c}: n {len(e)} mean {e[c].mean()*1e4:+.1f} med {e[c].median()*1e4:+.1f} t(day) {t:+.2f} "
            f"ex-top5 {e[c].sort_values().iloc[:-5].mean()*1e4:+.1f} hit {(e[c]>0).mean():.2f} yrs>0 {(yrs>0).sum()}/{len(yrs)}"), t, yrs


def build():
    px, dv, info = fetch()
    px = px.dropna(subset=["close_"]).copy()
    px["date"] = pd.to_datetime(px.marketdate)
    px = px[px.isocurrcode.eq("CAD") & px.close_.gt(0)].sort_values(["infocode", "date"]).drop_duplicates(["infocode", "date"]).reset_index(drop=True)
    g = px.groupby("infocode", sort=False)
    px["pc"] = g.close_.shift(1)
    px["gapdays"] = (px.date - g.date.shift(1)).dt.days
    px["vol"] = px.volume.fillna(0)
    px["dvol"] = px.close_ * px.vol
    px["adv"] = px.groupby("infocode").dvol.transform(lambda s: s.shift(1).rolling(20, min_periods=10).median())
    d = dv[dv.isocurrcode.eq("CAD") & dv.effdateestflag.fillna("A").eq("A") & dv.effectivedate.notna()].copy()
    d["date"] = pd.to_datetime(d.effectivedate)
    d = d.groupby(["infocode", "date"], as_index=False).divrate.sum().rename(columns={"divrate": "div"})
    m = px.merge(d, on=["infocode", "date"], how="left")
    m["ex"] = m["div"].notna(); m["div"] = m["div"].fillna(0.0)
    m["y"] = m["div"] / m.pc
    m["open_ok"] = m.open_.gt(0)
    m["co"] = (m.open_ + m["div"]) / m.pc - 1
    m["cc"] = (m.close_ + m["div"]) / m.pc - 1
    m["drop_cc"] = (m.pc - m.close_) / m["div"].where(m.ex)
    m["drop_co"] = (m.pc - m.open_) / m["div"].where(m.ex)
    m["stale"] = m.open_.eq(m.pc)
    m = m[m.date.between("2005-01-01", "2025-12-31") & m.pc.between(10, 30) & (m.adv >= 5e4) & (m.gapdays <= 7)].dropna(subset=["pc"])
    return m, info, dv


def main():
    L = []; P = L.append
    m, info, dv = build()
    P(f"INTL-PREF (N 1021->1022). Source: WRDS Datastream tr_ds_equities, ds2primqtprc exch 197 (Toronto, raw, CAD) + ds2div effectivedate.")
    P(f"Universe: {info.infocode.nunique()} CA PREF quotes in Datastream ({int(info.delistdate.notna().sum())} delisted = survivorship-free); eligible name-days {len(m)}, names {m.infocode.nunique()}")
    ne = m[~m.ex]; ex = m[m.ex & m.y.between(0.002, 0.04)]
    P(f"ex-events with CAD div: {int(m.ex.sum())}; after yield 0.2-4% filter {len(ex)} (y median {ex.y.median()*1e4:.0f}bp); other-currency/estimated-date dividends excluded")
    # opens reliability
    P("\nOPEN RELIABILITY (eligible name-days / ex events):")
    P(f"  open present: all days {m.open_ok.mean():.1%}, ex events {ex.open_ok.mean():.1%}")
    P(f"  open == prior close (stale-open flag), non-ex days: {ne[ne.open_ok].stale.mean():.1%}; ex events: {ex[ex.open_ok].stale.mean():.1%}")
    yy = m.groupby(m.date.dt.year).agg(op=("open_ok", "mean"), st=("stale", "mean"))
    P("  by year open-present/stale: " + " ".join(f"{y}:{r.op:.0%}/{r.st:.0%}" for y, r in yy.iterrows()))
    rel = ex.open_ok.mean() >= 0.90 and ne[ne.open_ok].stale.mean() < 0.20
    P(f"  rule (stated before reading): open reliable iff present >=90% on ex events AND stale share <20% on non-ex days -> {'RELIABLE: primary CO' if rel else 'NOT RELIABLE: primary CC (registered fallback)'}")
    prim = "co" if rel else "cc"
    x = ex.dropna(subset=[prim]).copy()
    x = x[(x.close_ / x.pc - 1).abs() < 0.25]
    x["net"] = x[prim] - 0.0010
    P(f"\nPRIMARY = {prim.upper()} net of 10bp RT; events n {len(x)} (|ret|>25% guard applied), names {x.infocode.nunique()}, ex-dates {x.date.nunique()}")
    for c in ["co", "cc"]:
        xx = ex.dropna(subset=[c]); xx = xx[(xx.close_ / xx.pc - 1).abs() < 0.25]
        s, _, _ = line(xx, c); P("  gross " + s + f"  | drop/div med {xx['drop_'+c].median():.2f} mean {xx['drop_'+c].clip(-3,5).mean():.2f}")
        P(f"    non-ex nights {c}: mean {ne[c].mean()*1e4:+.1f} med {ne[c].median()*1e4:+.1f}")
    s, t, yrs = line(x, "net"); P("\nNET " + s)
    dr = x["drop_" + prim]
    ratio = dr.median(); ratio_m = x["drop_"+prim].clip(-3, 5).mean()
    # ratio of aggregate
    agg = (x.pc - (x.close_ if prim == "cc" else x.open_)).sum() / x["div"].sum()
    P(f"drop/div: median {ratio:.2f}, mean(clipped) {ratio_m:.2f}, aggregate {agg:.2f}")
    h1, h2 = x[x.date < "2015-01-01"], x[x.date >= "2015-01-01"]
    P(f"halves net: 2005-14 {h1.net.mean()*1e4:+.1f} (n {len(h1)}), 2015-25 {h2.net.mean()*1e4:+.1f} (n {len(h2)})")
    P("by year net/n: " + " ".join(f"{y}:{r.net*1e4:+.0f}/{r.n}" for y, r in x.groupby(x.date.dt.year).agg(net=("net", "mean"), n=("net", "size")).iterrows()))
    # descriptive bins
    P("by yield bin: " + " | ".join(f"{lab} {line(x[q],'net')[0]}" for lab, q in [("y<1%", x.y < .01), ("y1-1.5%", x.y.between(.01, .015)), ("y>=1.5%", x.y >= .015)] if q.sum() > 20))
    P("by liquidity (ADV C$): " + " | ".join(f"{lab} n {q.sum()} mean {x[q].net.mean()*1e4:+.1f} med {x[q].net.median()*1e4:+.1f}" for lab, q in [("<150k", x.adv < 1.5e5), ("150k-500k", x.adv.between(1.5e5, 5e5)), (">=500k", x.adv >= 5e5)] if q.sum() > 0))
    # other arm for transparency
    other = "cc" if prim == "co" else "co"
    xo = ex.dropna(subset=[other]); xo = xo[(xo.close_ / xo.pc - 1).abs() < 0.25]
    P(f"(secondary, not the verdict) {other.upper()} net10: mean {(xo[other]-0.001).mean()*1e4:+.1f}, median {(xo[other]-0.001).median()*1e4:+.1f}")
    gate = {
        "net mean >= +15bp": x.net.mean() * 1e4 >= 15,
        "median > 0": x.net.median() > 0,
        "day-clustered t >= 2": t >= 2,
        ">= 80% of years > 0": (yrs > 0).mean() >= 0.8,
        "drop/div <= 0.9 (median)": ratio <= 0.9,
        "ex-top-5 > +10bp": x.net.sort_values().iloc[:-5].mean() * 1e4 > 10,
        "both halves > 0": h1.net.mean() > 0 and h2.net.mean() > 0,
    }
    P("\nGATE:"); [P(f"  {'PASS' if v else 'FAIL'}  {k}") for k, v in gate.items()]
    P("VERDICT: " + ("PASS" if all(gate.values()) else "KILL"))
    OUT.write_text("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    main()
