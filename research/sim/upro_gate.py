"""Study UPRO-GATE (N 1106-1107): trend gate on the Roth's passive 1/3 UPRO sleeve only (NOT the MR book; REGIME-10M
closed that class). Pre-reg research/drafts/round1_prose.md "Study UPRO-GATE". One look.

Synthetic 3x daily S&P TR (3 r_TR - 2 rf - 0.91%/252) judged 1955-2008, validated vs real UPRO 2009-26.
Primary 10M: month-end TR > 10-month SMA -> UPRO next month, else bills, traded at the NEXT session's 16:00 closing cross
(regular-hours; the month-end close is only known after the cross). Secondary 200D: daily price close vs 200d SMA, 1% band.

  PYTHONPATH=.:../sharadar-data python3 -m research.sim.upro_gate
(xlrd needed for Shiller's ie_data.xls.)"""
from __future__ import annotations

import json
import pathlib
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/upro_gate"
OUT = ROOT / "data/research/program/upro_gate_out.txt"
EXP, SGOV_FEE, SIDE = 0.0091, 0.0009, 2e-4
L: list[str] = []


def P(s=""):
    print(s, flush=True); L.append(s)


def yahoo(sym: str, start="1950-01-01") -> pd.DataFrame:
    """Daily close/adjclose from Yahoo chart API, cached (vt_flow.yahoo_ohlc starts at 1970; ^GSPC needs 1950)."""
    f = D / f"y_{sym.replace('^', '')}.parquet"
    if f.exists():
        return pd.read_parquet(f)
    p1 = int(pd.Timestamp(start).timestamp())
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}"
           f"?period1={p1}&period2={int(pd.Timestamp.now().timestamp())}&interval=1d&events=div,split")
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r:
        res = json.load(r)["chart"]["result"][0]
    idx = pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert("America/New_York").normalize().tz_localize(None)
    adj = res["indicators"].get("adjclose", [{}])[0].get("adjclose") or res["indicators"]["quote"][0]["close"]
    df = pd.DataFrame({"close": res["indicators"]["quote"][0]["close"], "adjclose": adj}, index=idx.astype("datetime64[ns]")).dropna()
    df = df[~df.index.duplicated(keep="last")]
    df.to_parquet(f)
    return df


def shiller_div() -> pd.Series:
    x = pd.read_excel(D / "ie_data.xls", sheet_name="Data", header=7)[["Date", "D"]].dropna()
    x = x[pd.to_numeric(x.Date, errors="coerce").notna()]
    d = x.Date.astype(float)
    per = pd.PeriodIndex.from_fields(year=d.astype(int).values, month=np.rint((d - d.astype(int)) * 100).astype(int).values, freq="M")
    return pd.Series(x.D.astype(float).values, index=per)


def build():
    g = yahoo("^GSPC")["close"]; spy = yahoo("SPY", "1993-01-01")["adjclose"]; upro = yahoo("UPRO", "2009-01-01")["adjclose"]
    dv = shiller_div()
    rp = g.pct_change()
    per = g.index.to_period("M"); nm = pd.Series(1, index=g.index).groupby(per).transform("count")
    dy = (dv.reindex(per).ffill().to_numpy() / 12) / g.shift(1).to_numpy() / nm.to_numpy()
    r_tr = (rp + dy).rename("tr")
    sp = spy.pct_change()
    cut = pd.Timestamp("1993-02-01")
    r_tr = pd.concat([r_tr[r_tr.index < cut], sp[sp.index >= cut]]).dropna()
    px = pd.concat([g[g.index < cut], (g[g.index >= cut])])            # price index for the 200D rule (^GSPC throughout)
    rf = pd.read_csv(D / "DTB3.csv", parse_dates=["observation_date"]).set_index("observation_date")["DTB3"]
    rf = pd.to_numeric(rf, errors="coerce").reindex(r_tr.index, method="ffill") / 100 / 252
    df = pd.DataFrame({"tr": r_tr, "rf": rf, "px": px.reindex(r_tr.index)}).dropna()
    df["r3"] = 3 * df.tr - 2 * df.rf - EXP / 252
    df["r3s"] = 3 * df.tr - 2 * (df.rf + 0.005 / 252) - EXP / 252
    df["bill"] = df.rf - SGOV_FEE / 252
    df["upro"] = upro.pct_change().reindex(df.index)
    df["tri"] = (1 + df.tr).cumprod()
    return df


def dec_10m(df):
    me = df.tri.groupby(df.index.to_period("M")).last()
    st = (me > me.rolling(10).mean()).astype(float).where(me.rolling(10).mean().notna())
    last_day = df.index.to_series().groupby(df.index.to_period("M")).transform("max")
    dec = pd.Series(np.nan, index=df.index)
    m_end = df.index[df.index == last_day]
    dec.loc[m_end] = st.reindex(m_end.to_period("M")).to_numpy()
    return dec.ffill()


def dec_200(df):
    sma = df.px.rolling(200).mean(); s = np.nan; out = []
    for c, m in zip(df.px.to_numpy(), sma.to_numpy()):
        if not np.isnan(m):
            if c > 1.01 * m: s = 1.0
            elif c < 0.99 * m: s = 0.0
            elif np.isnan(s): s = 1.0 if c > m else 0.0
        out.append(s)
    return pd.Series(out, index=df.index)


def sleeve(df, pos, lev="r3", side=SIDE):
    pos = pos.fillna(1.0)
    sw = pos.diff().abs().fillna(0)
    return pos * df[lev] + (1 - pos) * df.bill - sw * 2 * side, sw


def static_mix(df, w, lev="r3"):
    """w lev + (1-w) bills, rebalanced at each month-end close."""
    a, b = df[lev].to_numpy(), df.bill.to_numpy(); per = df.index.to_period("M").to_numpy()
    out = np.empty(len(a)); va, vb = w, 1 - w
    for i in range(len(a)):
        if i and per[i] != per[i - 1]:
            t = va + vb; va, vb = w * t, (1 - w) * t
        t0 = va + vb; va *= 1 + a[i]; vb *= 1 + b[i]; out[i] = (va + vb) / t0 - 1
    return pd.Series(out, index=df.index)


def stats(r):
    r = r.dropna(); eq = (1 + r).cumprod(); yrs = len(r) / 252
    cagr = eq.iloc[-1] ** (1 / yrs) - 1; mdd = (eq / eq.cummax() - 1).min()
    me = eq.groupby(eq.index.to_period("M")).last(); w12 = (me / me.shift(12) - 1).min()
    return dict(cagr=cagr, mdd=mdd, mar=cagr / abs(mdd), w12=w12, vol=r.std() * np.sqrt(252))


def win(r, a, b):
    x = r[(r.index >= a) & (r.index <= b)]; eq = (1 + x).cumprod()
    return eq.iloc[-1] - 1, (eq / eq.cummax() - 1).min()


def fmt(n, s):
    return f"{n:<34} CAGR {s['cagr']*100:6.1f}%  maxDD {s['mdd']*100:6.1f}%  MAR {s['mar']:5.2f}  worst12m {s['w12']*100:6.1f}%  vol {s['vol']*100:5.1f}%"


def solve_w(df, target_mdd):
    lo, hi = 0.0, 1.0
    for _ in range(30):
        m = (lo + hi) / 2
        if stats(static_mix(df, m))["mdd"] < target_mdd: hi = m
        else: lo = m
    return (lo + hi) / 2


def whipsaws(pos):
    ch = pos.index[pos.diff().abs() > 0]
    return sum(1 for a, b in zip(ch[:-1], ch[1:]) if (b - a).days <= 62)


def book_series():
    """0.5 IBS + 0.5 night daily-bar book at 5bp/side, REGIME-10M harness (research/sim/regime_10m.py)."""
    f = D / "book.parquet"
    if f.exists():
        return pd.read_parquet(f)["r"]
    from research.sim import shar_crash as sc, nx
    from sharadar import prices as sh_prices
    cost = 5e-4
    Pp = nx.Paths(); master = nx.load_master(Pp); act = nx.read_table(Pp, "ACTIONS"); sep = nx.read_table(Pp, "SEP"); sfp = nx.read_table(Pp, "SFP")
    parts = []
    for lo, hi in (("1999-01-04", "2015-12-31"), ("2016-01-04", "2026-09-18")):
        lo, hi = pd.Timestamp(lo), pd.Timestamp(hi)
        df = sh_prices(sc.EQ18, (lo - pd.Timedelta(days=420)).strftime("%Y-%m-%d"), (hi + pd.Timedelta(days=10)).strftime("%Y-%m-%d"), adjust="split", source="funds")
        df = df[df.ticker.isin(sc.EQ18)].assign(date=pd.to_datetime(df.date))
        O, H, L_, C = [df.pivot(index="date", columns="ticker", values=c).sort_index() for c in ("open", "high", "low", "close")]
        idx = C.index[(C.index >= lo) & (C.index <= hi)]
        ibs = (sc.ibs_daily(O, H, L_, C) - 2 * cost).reindex(idx).fillna(0.0)
        bars = pd.concat([t[(t.date >= lo - sc.PAD) & (t.date <= hi + sc.PAD)] for t in (sep, sfp)], ignore_index=True)
        bars = bars.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
        tr = nx.collect_trades(nx.build_panel(bars), master, act, "primary", lo, hi)["trades"]
        ngt = tr.groupby("date").apply(lambda g: float((g.per * (g.ret - 2 * cost)).sum())).reindex(idx).fillna(0.0)
        parts.append(0.5 * ibs + 0.5 * ngt)
    s = pd.concat(parts); s.index = pd.to_datetime(s.index)
    s.rename("r").to_frame().to_parquet(f)
    return s


def roth_path(r_roth, start, dep=7500.0):
    v = start; vals = []; prev_y = None
    for d, x in r_roth.items():
        if prev_y is not None and d.year != prev_y: v += dep
        prev_y = d.year; v *= 1 + x; vals.append(v)
    return vals[-1]


def two_mix(df_r, a, b, wa):
    """wa*a + (1-wa)*b, month-end rebalanced (a, b daily return series on the same index)."""
    x = pd.DataFrame({"r3": a, "bill": b}).dropna()
    return static_mix(x, wa)


def main():
    df = build()
    P(f"UPRO-GATE run {pd.Timestamp.now():%Y-%m-%d %H:%M}. data {df.index.min().date()}..{df.index.max().date()}; "
      f"TR = ^GSPC + Shiller D/12 to 1993-01, SPY adjclose after; rf FRED DTB3; real UPRO from {df.upro.first_valid_index().date()}")
    # ---- validation vs real UPRO
    v = df.dropna(subset=["upro"]); v = v[v.index >= "2009-07-01"]
    te = (v.r3 - v.upro).std() * np.sqrt(252); te_s = (v.r3s - v.upro).std() * np.sqrt(252)
    P("\n== Synthetic 3x vs real UPRO 2009-07..")
    for n, c in (("real UPRO", "upro"), ("synthetic 2rf", "r3"), ("synthetic 2(rf+50bp)", "r3s")):
        P(fmt(n, stats(v[c])))
    P(f"tracking error (ann.) synth {te*100:.1f}%  synth+50bp {te_s*100:.1f}%  corr {v.r3.corr(v.upro):.4f}; "
      f"note: close-to-close timing noise inflates TE; drift = CAGR gap above")
    dec10, dec2 = dec_10m(df), dec_200(df)
    pos = {"10M (N1106, T+1 close)": dec10.shift(2), "200D band (N1107, T+1 close)": dec2.shift(2), "10M same-day close (desc)": dec10.shift(1)}
    J = {"JUDGE 1955-2008": ("1955-01-03", "2008-12-31"), "  half A 1955-1981": ("1955-01-03", "1981-12-31"),
         "  half B 1982-2008": ("1982-01-04", "2008-12-31"), "DESC 2009-2026 synth": ("2009-07-01", "2026-12-31"),
         "DESC post-Faber 2007-07..2026 (added after first look)": ("2007-07-02", "2026-12-31")}
    res = {}; WST = {}
    for jn, (a, b) in J.items():
        x = df[(df.index >= a) & (df.index <= b)]
        bh = stats(x.r3); P(f"\n== {jn}: {len(x)} sessions"); P(fmt("B&H synthetic 3x", bh)); P(fmt("B&H 1x S&P TR", stats(x.tr)))
        res[jn] = {"bh": bh}
        for pn, ps in pos.items():
            p = ps.reindex(x.index)
            r, sw = sleeve(x, p); r3x, _ = sleeve(x, p, side=3 * SIDE); s = stats(r); s3 = stats(r3x)
            yrs = len(x) / 252; nsw = sw.sum()
            g1, g2, g3 = s["mar"] >= 1.5 * bh["mar"], s["cagr"] >= 0.8 * bh["cagr"], s["w12"] > bh["w12"]
            res[jn][pn] = (s, g1, g2, g3)
            P(fmt(pn, s) + f"  | ON {p.fillna(1).mean()*100:3.0f}%  switches/yr {nsw/yrs:4.2f}  whipsaws {whipsaws(p.fillna(1))}"
              f"  3x-cost CAGR {s3['cagr']*100:5.1f}%  G1 {'Y' if g1 else 'n'} G2 {'Y' if g2 else 'n'} G3 {'Y' if g3 else 'n'}")
            if not pn.startswith("10M same"):
                if jn.startswith("JUDGE"): WST[pn] = solve_w(x, s["mdd"])
                w = WST[pn]
                sm = stats(static_mix(x, w))
                P(fmt(f"   static w={w:.2f} (maxDD-matched on judge)", sm) + f"  gate-minus-static CAGR {(s['cagr']-sm['cagr'])*100:+.1f}pp")
        P(fmt("   static w=1/2 (=1/6 of account)", stats(static_mix(x, 0.5))))
    # ---- gate verdicts
    P("\n== Gate (all three in BOTH halves)")
    for pn in list(pos)[:2]:
        ok = all(all(res[h][pn][1:]) for h in ("  half A 1955-1981", "  half B 1982-2008"))
        P(f"{pn}: {'PASS' if ok else 'FAIL'}  " + "  ".join(f"{h.strip()}: G1/G2/G3 {''.join('Y' if g else 'n' for g in res[h][pn][1:])}"
                                                          for h in ("JUDGE 1955-2008", "  half A 1955-1981", "  half B 1982-2008")))
    # ---- episodes
    P("\n== Episodes (sleeve total return / maxDD inside window)")
    eps = [("1973-74", "1973-01-01", "1974-12-31"), ("1987 crash", "1987-08-01", "1987-12-31"), ("2000-02", "2000-03-01", "2002-12-31"),
           ("2007-09", "2007-10-01", "2009-03-31"), ("2018Q4", "2018-10-01", "2018-12-31"), ("2020-02..06", "2020-02-19", "2020-06-30"), ("2022", "2022-01-01", "2022-12-31")]
    arms = {"B&H synth": df.r3, "10M": sleeve(df, pos["10M (N1106, T+1 close)"])[0], "200D": sleeve(df, pos["200D band (N1107, T+1 close)"])[0],
            "w=1/2 static": static_mix(df, 0.5)}
    for en, a, b in eps:
        P(f"{en:<12} " + "  ".join(f"{k} {win(v_, a, b)[0]*100:+6.1f}%/{win(v_, a, b)[1]*100:6.1f}%" for k, v_ in arms.items()))
    if df.upro.notna().any():
        u = df.copy(); u["r3"] = u.upro
        for en, a, b in eps[-3:]:
            P(f"{en:<12} REAL UPRO B&H {win(u.r3.dropna(), a, b)[0]*100:+6.1f}%/{win(u.r3.dropna(), a, b)[1]*100:6.1f}%  10M on real UPRO "
              f"{win(sleeve(u, pos['10M (N1106, T+1 close)'])[0].dropna(), a, b)[0]*100:+6.1f}%/{win(sleeve(u, pos['10M (N1106, T+1 close)'])[0].dropna(), a, b)[1]*100:6.1f}%")
        uu = u[u.index >= "2009-07-01"].dropna(subset=["upro"])
        P(fmt("REAL UPRO B&H 2009-26", stats(uu.r3)))
        P(fmt("10M on REAL UPRO 2009-26", stats(sleeve(uu, pos["10M (N1106, T+1 close)"].reindex(uu.index))[0])))
        P(fmt("200D on REAL UPRO 2009-26", stats(sleeve(uu, pos["200D band (N1107, T+1 close)"].reindex(uu.index))[0])))
    # ---- whole Roth
    P("\n== Whole Roth = 1/3 sleeve + 2/3 book (book = 0.5 IBS + 0.5 night, 5bp/side, REGIME-10M harness), month-end rebalanced")
    try:
        bk = book_series()
    except Exception as e:  # noqa: BLE001
        P(f"book series unavailable ({type(e).__name__}: {e}); whole-Roth skipped"); bk = None
    if bk is not None:
        uproreal = df.upro.where(df.index >= "2009-07-01", df.r3)          # synthetic before UPRO, real after
        base = df.assign(r3=uproreal)
        sl = {"1/3 B&H UPRO": base.r3, "1/3 10M-gated": sleeve(base, pos["10M (N1106, T+1 close)"])[0],
              "1/3 200D-gated": sleeve(base, pos["200D band (N1107, T+1 close)"])[0], "1/6 UPRO + 1/6 bills": static_mix(base, 0.5)}
        for wn, (a, b) in {"1999-2008 (synth 3x)": ("1999-01-04", "2008-12-31"), "2009-07..2026-09 (real UPRO)": ("2009-07-01", "2026-09-18")}.items():
            P(f"-- {wn}")
            for k, s_ in sl.items():
                x = pd.DataFrame({"r3": s_, "bill": bk}).dropna(); x = x[(x.index >= a) & (x.index <= b)]
                rr = static_mix(x, 1 / 3); st = stats(rr)
                P(fmt(k, st) + "  end $ (+7.5k/yr): " + "  ".join(f"${s0/1e3:.1f}k->{roth_path(rr, s0)/1e3:,.0f}k" for s0 in (2300, 10000, 25000)))
            P(fmt("book alone", stats(bk[(bk.index >= a) & (bk.index <= b)])))
    OUT.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
