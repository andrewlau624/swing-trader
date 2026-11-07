"""Study RH-FADE (brief name RETAIL-HERD; renamed: RETAIL-HERD = N 981 scalp study) step 1: ceiling + borrow evidence (no return backtest; N 1119 reserved, not consumed by this script).

Question: can a short fade of retail-attention herding events (Barber-Huang-Odean-Schwarz 2022, JF) clear the +8pp/yr-at-$10k
gate after honest borrow, capture and costs? Robintrack ended 2020-08, so the event set here is a PROXY used only to read
borrow fees and event counts, never returns: per day, the top 0.5% of US common stocks by volume / prior-20d mean volume
(mirrors the paper's "top 0.5% of user-change ratio"), 2018-2024, CRSP daily. Fee = optionm.borrate (option-implied, nearest-30d
tenor, latest read in [t-7, t]; sentinel -99.99 dropped; stored as a decimal, converted to %/yr here). Caveat: borrate is put-call-parity implied (dividend contamination near
ex-dates; most event names pay none) and only covers optionable names, so the fee panel is biased toward LOWER fees.

Usage: .venv/bin/python -m research.sim.rh_fade
Cache: data/research/rh_fade/ ; output: data/research/program/rh_fade_out.txt
"""
import pathlib, numpy as np, pandas as pd
from research.sim.borrow_xs import conn

D = pathlib.Path("data/research/rh_fade"); D.mkdir(parents=True, exist_ok=True)
OUT = pathlib.Path("data/research/program/rh_fade_out.txt")
YEARS = list(range(2018, 2025))


def events_year(db, y):
    f = D / f"events_{y}.parquet"
    if f.exists():
        return pd.read_parquet(f)
    sql = f"""
    with n as (select distinct on (permno) permno, shrcd from crsp.dsenames order by permno, namedt desc),
    d as (
      select s.permno, s.date, s.ret, abs(s.prc) as prc, s.vol, s.shrout,
             avg(s.vol) over (partition by s.permno order by s.date rows between 20 preceding and 1 preceding) as av20
      from crsp.dsf s join n on n.permno = s.permno and n.shrcd in (10, 11)
      where s.date between '{y - 1}-11-15' and '{y}-12-31')
    select permno, date, ret, prc, vol, shrout, av20, vol / nullif(av20, 0) as vr
    from d where date >= '{y}-01-01' and av20 > 0 and prc > 0
    """
    df = db.raw_sql(sql).reset_index(drop=True)  # raw_sql chunk concat can duplicate index labels
    df["date"] = pd.to_datetime(df["date"])
    df["rk"] = df.groupby("date")["vr"].rank(pct=True, ascending=False)
    ev = df[df["rk"] <= 0.005].copy()
    ev["ncs"] = df.groupby("date")["vr"].transform("size").reindex(ev.index)
    ev.to_parquet(f, index=False)
    return ev


def fees_year(db, y, ev):
    f = D / f"fees_{y}.parquet"
    if f.exists():
        return pd.read_parquet(f)
    perms = ",".join(str(int(p)) for p in ev["permno"].unique())
    link = db.raw_sql(f"select secid, permno, sdate, edate from wrdsapps_link_crsp_optionm.opcrsphist "
                      f"where score = 1 and permno in ({perms})")
    secs = ",".join(str(int(s)) for s in link["secid"].unique())
    br = db.raw_sql(f"""
      select distinct on (securityid, date) securityid as secid, date, borrowrate
      from optionm.borrate{y} where borrowrate > -99 and securityid in ({secs})
      order by securityid, date, abs(days - 30)""")
    br["date"] = pd.to_datetime(br["date"])
    link["sdate"] = pd.to_datetime(link["sdate"]); link["edate"] = pd.to_datetime(link["edate"])
    m = ev[["permno", "date"]].merge(link, on="permno")
    m = m[(m["date"] >= m["sdate"]) & (m["date"] <= m["edate"])]
    m = m.sort_values("date"); br = br.sort_values("date")
    m = pd.merge_asof(m, br.rename(columns={"date": "fdate"}), left_on="date", right_on="fdate", by="secid",
                      tolerance=pd.Timedelta("7D"), direction="backward")
    m = m.dropna(subset=["borrowrate"]).drop_duplicates(["permno", "date"])[["permno", "date", "borrowrate"]]
    m.to_parquet(f, index=False)
    return m


def q(s, ps=(0.25, 0.5, 0.75, 0.9)):
    return " ".join(f"p{int(p * 100)} {s.quantile(p):6.1f}" for p in ps)


def ceiling(tiers):
    """Paper inputs (BHOS 2022 SSRN draft 201123, Table 11, 5-day FF5+mom AR, 2018-05..2020-08, IN-SAMPLE):
    all -2.94%, price>$5 -0.85%, mcap<$1B -4.25%, mcap>$1B +0.14%. The $5+ & <$1B intersection is not reported:
    take a generous -1.5%. Shape: 5-session hold, ~50 rotations/yr (events ~10/day, never event-limited), gross short
    0.5x of equity (squeeze tail), capture 50%. Cost = assumed round trip; borrow = proxy-event fee mean (portfolio pays the
    mean) and median (optimistic) over the hold."""
    L = ["", "CEILING (pp/yr on the whole account; same % at $2.3k/$10k/$25k: whole shares fine at $5+, margin min $2k binds at $2.3k)"]
    cells = {"prc>=5 & mcap<1B (shortable cell)": ("prc>=5 & mcap<1B", 1.5, 0.30),
             "prc<5 (where the effect lives; FINRA 4210 short margin = max($2.50/sh, 100%))": ("prc<5", 4.25, 1.00)}
    for name, (tk, edge, rt) in cells.items():
        f = tiers[tk]["borrowrate"].dropna()
        for cap in (0.5, 1.0):
            g = 50 * edge * cap * 0.5
            c = 50 * rt * 0.5
            for lab, fee in (("mean fee", f.mean()), ("median fee", f.median())):
                b = fee * 0.5  # fee %/yr on 0.5x notional, continuously deployed
                L.append(f"  {name}: edge {edge}%/5d capture {cap:.0%} -> gross {g:5.1f} - cost({rt}% rt) {c:4.1f} - "
                         f"borrow({lab} {fee:4.1f}%) {b:4.1f} = net {g - c - b:+6.1f}pp")
    L.append("  GATE: +8pp at $10k under capture <= 50%. Shortable cell at 50% capture: below gate at every fee read -> CEILING-KILL.")
    return L


def main():
    db = None
    evs, fees = [], []
    for y in YEARS:
        if not (D / f"fees_{y}.parquet").exists():
            db = db or conn()
        ev = events_year(db, y)
        fees.append(fees_year(db, y, ev)); evs.append(ev)
    ev = pd.concat(evs); fe = pd.concat(fees)
    ev = ev.merge(fe, on=["permno", "date"], how="left")
    ev["borrowrate"] = ev["borrowrate"] * 100.0  # borrate is a DECIMAL fraction/yr (GME 2021-01-22 = 0.94; cross-section p50 ~0.02,
    # p99 ~0.5-1.5); repo docstrings that say "percent" conflict with this, see memory 82
    ev["mcap"] = ev["prc"] * ev["shrout"] / 1e3  # $M
    L = ["RH-FADE step 1: proxy attention events (top 0.5%/day of vol/avg20, US common, CRSP) x optionm.borrate, 2018-2024",
         f"events {len(ev)}  days {ev['date'].nunique()}  per day {len(ev) / ev['date'].nunique():.1f}"]
    tiers = {"all": ev, "prc>=5": ev[ev.prc >= 5], "prc>=5 & mcap<1B": ev[(ev.prc >= 5) & (ev.mcap < 1000)],
             "prc<5": ev[ev.prc < 5], "mcap<1B (paper's effect cell)": ev[ev.mcap < 1000]}
    for k, t in tiers.items():
        f = t["borrowrate"].dropna()
        L.append(f"[{k}] n {len(t)} ({len(t) / ev['date'].nunique():.1f}/day)  fee coverage {len(f) / max(len(t), 1):.0%}  "
                 f"fee %/yr: mean {f.mean():6.1f} {q(f)}  share fee>10% {np.mean(f > 10):.0%}  >25% {np.mean(f > 25):.0%}  "
                 f"median prc {t.prc.median():.2f} median mcap ${t.mcap.median():.0f}M")
    L.append("by year, prc>=5 & mcap<1B: median fee / p75 / share>10% / events")
    t = tiers["prc>=5 & mcap<1B"]
    for y, g in t.groupby(t.date.dt.year):
        f = g["borrowrate"].dropna()
        L.append(f"  {y}: {f.median():6.1f} {f.quantile(.75):6.1f} {np.mean(f > 10):5.0%}  n {len(g)}")
    L.append("reference: whole optionable cross-section borrate p50 1.2-2.7%/yr, p90 10-22%/yr (mid-June reads 2019-24)")
    L += ceiling(tiers)
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
