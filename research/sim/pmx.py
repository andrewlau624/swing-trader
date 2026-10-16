"""PMX: pre-market exit of night picks when QQQ falls overnight. Pre-registered in round1_prose.md (N 1015 -> 1016).
Usage: python research/sim/pmx.py fetch   (resume-safe, per-date cache)  |  python research/sim/pmx.py run
Fetched set: every pick-night with QQQ q_pm(08:59) <= -0.5% PLUS a seeded random 300 of the other pick-nights.
Open price = 09:30 bar open of the same raw fetch (not the official cross)."""
import os, sys, time
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, ".")
from nbh import qqq_daily, night_series, stats, NIGHT_W, COST_PICK  # noqa: E402
import glob

CACHE = "data/research/pmx"
OUT = "data/research/program/pmx_out.txt"


def qqq_pm():
    m = pd.concat(pd.read_parquet(f) for f in sorted(glob.glob("data/research/night/m1/QQQ_20*.parquet")))
    t = pd.to_datetime(m.timestamp, utc=True).dt.tz_convert("America/New_York")
    m = m.assign(d=t.dt.tz_localize(None).dt.normalize(), hm=t.dt.strftime("%H:%M"))
    c = m.pivot_table(index="d", columns="hm", values="close", aggfunc="last")
    return c


def nights():
    """date d (pick night), d1 = next QQQ session, q_pm at 08:59/08:00/09:15 (signal bar = minute before T)."""
    c = qqq_pm()
    days = c.index
    nxt = pd.Series(days[1:], index=days[:-1])
    out = pd.DataFrame(index=days[:-1])
    out["d1"] = nxt
    base = c["15:59"].reindex(out.index)
    for T, sig in [("0859", "08:59"), ("0800", "07:59"), ("0915", "09:14")]:
        out["q" + T] = (c[sig].reindex(out.d1).values / base.values - 1)
    out["q_open"] = c["09:30"].reindex(out.d1).values / base.values - 1   # not used for rule
    out["q930"] = c["09:30"].reindex(out.d1).values
    out["q_sig"] = c["08:59"].reindex(out.d1).values
    return out


def picks():
    p, s = night_series()
    return p


def fetch():
    from swingtrader.config import require_alpaca_keys
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    k, sec = require_alpaca_keys()
    cli = StockHistoricalDataClient(k, sec)
    n = nights(); p = picks()
    pn = n.loc[n.index.intersection(p.date.unique())]
    flag = pn[pn.q0859 <= -0.005]
    rest = pn[~(pn.q0859 <= -0.005)]
    rng = np.random.default_rng(1016)
    samp = rest.iloc[np.sort(rng.choice(len(rest), min(300, len(rest)), replace=False))]
    todo = pd.concat([flag, samp])
    print(f"flagged(<=-0.5%) {len(flag)}  random other {len(samp)}", flush=True)
    for d, r in todo.iterrows():
        d1 = r.d1
        f = f"{CACHE}/{d1.date()}.parquet"
        if os.path.exists(f):
            continue
        syms = sorted(p[p.date == d].sym.unique())
        st = pd.Timestamp(d1.date()).tz_localize("America/New_York") + pd.Timedelta(hours=4)
        en = pd.Timestamp(d1.date()).tz_localize("America/New_York") + pd.Timedelta(hours=9, minutes=31)
        for attempt in range(8):
            try:
                df = cli.get_stock_bars(StockBarsRequest(
                    symbol_or_symbols=syms, timeframe=TimeFrame.Minute, start=st.tz_convert("UTC").to_pydatetime(),
                    end=en.tz_convert("UTC").to_pydatetime(), feed="sip", adjustment="raw")).df
                break
            except Exception as exc:  # noqa: BLE001
                msg = str(exc)
                if "429" in msg or "rate" in msg.lower():
                    time.sleep(10 * (attempt + 1)); continue
                print("err", d1.date(), msg[:80], flush=True); df = None; break
        else:
            df = None
        if df is None:
            continue
        df = df.reset_index() if len(df) else pd.DataFrame(columns=["symbol", "timestamp", "open", "close", "volume"])
        if len(df):
            df["ts"] = pd.to_datetime(df.timestamp, utc=True).dt.tz_convert("America/New_York")
            df["hm"] = df.ts.dt.strftime("%H:%M")
            df = df[["symbol", "hm", "open", "close", "volume"]]
        else:
            df = pd.DataFrame(columns=["symbol", "hm", "open", "close", "volume"])
        df.to_parquet(f)
        print(d1.date(), len(syms), len(df), flush=True)
        time.sleep(0.3)


def pm_d(p, n, T0, T1, hold_col=None):
    """per-trade d = pm_px/open930 - 1 for nights with cache. Window [T0,T1] inclusive of 1-min bar labels. NaN d => no pm print."""
    rows = []
    for d, g in p.groupby("date"):
        if d not in n.index:
            continue
        d1 = n.loc[d, "d1"]
        f = f"{CACHE}/{d1.date()}.parquet"
        if not os.path.exists(f):
            continue
        b = pd.read_parquet(f)
        for _, r in g.iterrows():
            x = b[b.symbol == r.sym]
            o = x[x.hm == "09:30"]
            if o.empty:
                rows.append((d, r.sym, r.ret, np.nan, np.nan, False)); continue   # no open bar: drop
            op = o.open.iloc[0]
            w = x[(x.hm >= T0) & (x.hm <= T1) & (x.volume > 0)]
            if w.empty:
                rows.append((d, r.sym, r.ret, op, np.nan, True))
            else:
                rows.append((d, r.sym, r.ret, op, w.sort_values("hm").close.iloc[-1] / op - 1, True))
    return pd.DataFrame(rows, columns=["date", "sym", "ret", "op", "d", "hasopen"])


def dnet(t, c):
    """pm net minus open net per trade at pm cost c per side (held trades -> 0)."""
    d = t.d.fillna(0.0)
    return (1 + t.ret) * d + 7.5e-4 - c if False else np.where(t.d.notna(), (1 + t.ret) * d + 15e-4 - 7.5e-4 - c, 0.0)


def tstat(x):
    x = pd.Series(x).dropna()
    return x.mean() / x.std() * np.sqrt(len(x)) if len(x) > 2 and x.std() > 0 else np.nan


def era_masks(idx):
    return [("2016-20", idx < "2021-01-01"), ("2021-26", idx >= "2021-01-01")]


def run():
    n = nights(); p = picks(); p = p[p.date.isin(n.index)]
    L = ["PMX: pre-market exit of night picks when QQQ falls overnight (exploratory, 2016-26 touched; N 1016).",
         "Fetched set: all pick-nights with QQQ q_pm(08:59) <= -0.5% plus a seeded random 300 of the other pick-nights",
         "(random sample used only for the descriptive pm->open continuation check). Open = 09:30 BAR OPEN of the raw fetch, not the official cross.",
         "d = pm_px/open930 - 1; pm net - open net = (1+ret)*d + 7.5bp - c_pm (c_pm per side; open exit pays 7.5bp/side). Picks with no pm print are held (d net 0).", ""]
    t = pm_d(p, n, "08:30", "08:59")
    t = t[t.hasopen]
    t["q"] = t.date.map(n.q0859)
    fl = t[t.q <= -0.01]
    nf = fl.date.nunique()
    L.append("== Registered rule (q_pm <= -1.0%, exit = last print 08:30-08:59)")
    for en, m in era_masks(fl.date):
        x = fl[m.values if hasattr(m, "values") else m]
        L.append(f"  {en}: flagged nights {x.date.nunique()}  trades {len(x)}  with pm print {x.d.notna().mean()*100:.1f}%  held-to-open {x.d.isna().mean()*100:.1f}%")
    # data coverage check
    allf = n.index.intersection(p.date.unique())
    nflag_all = [(d, n.loc[d, "q0859"]) for d in allf if n.loc[d, "q0859"] <= -0.01]
    L.append(f"  total flagged nights with picks (QQQ data): {len(nflag_all)}; with fetched cache: {nf}")
    L.append("")
    res = {}
    for c, lab in [(7.5e-4, "7.5bp"), (50e-4, "50bp"), (100e-4, "100bp")]:
        L.append(f"-- pm cost {lab}/side: d_net per trade; night-clustered t of per-night mean")
        for en, m in era_masks(fl.date) + [("all", fl.date == fl.date)]:
            x = fl[m.values if hasattr(m, "values") else m].copy()
            x["dn"] = dnet(x, c)
            pn = x.groupby("date").dn.mean()
            ex5 = pn.drop(pn.nlargest(5).index).mean() if len(pn) > 5 else np.nan
            res[(lab, en)] = (pn.mean(), tstat(pn), ex5)
            L.append(f"  {en:<8} nights {len(pn):3d} trades {len(x):4d}  mean(trade) {x.dn.mean()*1e4:+8.1f}bp  median {x.dn.median()*1e4:+7.1f}"
                     f"  per-night mean {pn.mean()*1e4:+8.1f}bp  t {tstat(pn):5.2f}  ex-top5 nights {ex5*1e4:+8.1f}bp")
    L.append("  raw d (gross, no cost): " + "  ".join(
        f"{en} mean {fl[(m.values if hasattr(m,'values') else m)].d.mean()*1e4:+.1f} med {fl[(m.values if hasattr(m,'values') else m)].d.median()*1e4:+.1f}bp (n print {fl[(m.values if hasattr(m,'values') else m)].d.notna().sum()})"
        for en, m in era_masks(fl.date)))
    L.append("")

    # leg series
    base_p, s = night_series()
    cal = n.index[(n.index >= s.index.min())]
    cal = cal[cal <= base_p.date.max()]
    ser = pd.DataFrame(index=cal)
    ser["net"] = s.net.reindex(cal).fillna(0.0)
    ser["pm"] = ser.net
    fl2 = fl.copy(); fl2["pmnet"] = (1 + fl2.ret) * (1 + fl2.d.fillna(0)) - 1 - 7.5e-4 - np.where(fl2.d.notna(), 50e-4, 7.5e-4)
    nm = fl2.groupby("date").pmnet.mean()
    # nights whose picks were all fetched; for partially missing-open picks use fetched trades only (minor)
    ser.loc[nm.index, "pm"] = nm
    L.append("== Leg (per-night equal-weight picks, 0 on no-pick nights, weight 0.65; pm exit at 50bp on flagged nights)")
    ok = True
    for en, m in era_masks(ser.index):
        a, sha, dda, ya = stats(ser.loc[m, "net"], "BASE " + en)
        b, shb, ddb, yb = stats(ser.loc[m, "pm"], "PMX  " + en)
        L += [a, b]
        c1 = (shb - sha >= 0.1) and (ddb > dda)
        L.append(f"    dSharpe {shb-sha:+.2f}, maxDD {ddb*100:.1f}% vs {dda*100:.1f}%, %/yr {yb*100:+.1f} vs {ya*100:+.1f} -> {'ok' if c1 else 'fail'}")
        ok &= c1
    L.append("")
    L.append("== Registered gate")
    gok = ok
    for en in ("2016-20", "2021-26"):
        mean, t_, ex5 = res[("50bp", en)]
        c2 = mean > 0 and t_ >= 2 and ex5 > 0
        L.append(f"  {en}: d@50bp mean {mean*1e4:+.1f}bp t {t_:.2f} ex-top5 {ex5*1e4:+.1f} -> {'ok' if c2 else 'fail'}")
        gok &= c2
    L.append(f"  PMX: {'PASS' if gok else 'FAIL'}")
    L.append("")

    # descriptive table
    L.append("== Descriptive (not judged): thresholds x exit time, per-night-clustered d at 7.5/50/100bp, on fetched nights only")
    L.append("   (nights fetched were chosen by the 08:59 q <= -0.5% screen; other-time signals use that same fetched set)")
    for T, (w0, w1, qc) in {"08:59 (reg)": ("08:30", "08:59", "q0859"), "08:00": ("07:30", "07:59", "q0800"),
                            "09:15": ("08:45", "09:14", "q0915")}.items():
        tt = pm_d(p, n, w0, w1); tt = tt[tt.hasopen]; tt["q"] = tt.date.map(n[qc])
        for thr in (-0.005, -0.01, -0.015):
            x = tt[tt.q <= thr]
            if x.empty: continue
            line = f"  exit {T:<12} q<= {thr*100:+.1f}%: nights {x.date.nunique():3d} trades {len(x):4d} print% {x.d.notna().mean()*100:5.1f} | "
            for c, lab in [(7.5e-4, "7.5"), (50e-4, "50"), (100e-4, "100")]:
                xx = x.copy(); xx["dn"] = dnet(xx, c); pnn = xx.groupby("date").dn.mean()
                line += f"{lab}bp: {pnn.mean()*1e4:+7.1f} (t {tstat(pnn):5.2f})  "
            L.append(line)
    L.append("")
    # continuation
    nn = n.loc[n.index.intersection(p.date.unique())].dropna(subset=["q0859", "q930"]).copy()
    nn["cont"] = nn.q930 / nn.q_sig - 1     # 08:59 close -> 09:30 open
    nn["q_open_ret"] = nn.q930 / n.loc[nn.index].q_sig * 0 + 0
    L.append("== QQQ pm(08:59) -> 09:30 open on ALL pick-nights (QQQ minute data, full set, no fetch needed)")
    for lab, m in [("q_pm<=-1.5%", nn.q0859 <= -.015), ("-1.5<q<=-1.0", (nn.q0859 > -.015) & (nn.q0859 <= -.01)),
                   ("-1.0<q<=-0.5", (nn.q0859 > -.01) & (nn.q0859 <= -.005)), ("-0.5<q<0.5", (nn.q0859 > -.005) & (nn.q0859 < .005)),
                   ("q>=+0.5%", nn.q0859 >= .005)]:
        x = nn[m]
        L.append(f"  {lab:<14} n {len(x):4d}  mean 08:59->09:30 {x.cont.mean()*1e4:+6.1f}bp  median {x.cont.median()*1e4:+6.1f}  t {tstat(x.cont):5.2f}")
    allq = n.dropna(subset=["q0859", "q930"]); allc = allq.q930 / allq.q_sig - 1
    for lab, m in [("ALL nights q<=-1.0%", allq.q0859 <= -.01), ("ALL nights q>=+1.0%", allq.q0859 >= .01)]:
        L.append(f"  {lab:<20} n {m.sum():4d}  mean {allc[m].mean()*1e4:+6.1f}bp  median {allc[m].median()*1e4:+6.1f}  t {tstat(allc[m]):5.2f}  (sign: + = continues up/reverts if q<0)")
    L.append("  corr(q_pm, 08:59->09:30) all nights: %.3f" % np.corrcoef(allq.q0859, allc)[0, 1])
    L.append("")
    # random sample check (stock level)
    r = pm_d(p, n, "08:30", "08:59"); r = r[r.hasopen]; r["q"] = r.date.map(n.q0859)
    o = r[r.q > -0.005]
    L.append(f"== Random other-night sample (q_pm > -0.5%): nights {o.date.nunique()} trades {len(o)} print% {o.d.notna().mean()*100:.1f}  mean d {o.d.mean()*1e4:+.1f}bp median {o.d.median()*1e4:+.1f}")
    L.append(f"   all fetched flagged (<= -0.5%): print% {r[r.q<=-0.005].d.notna().mean()*100:.1f}  mean d {r[r.q<=-0.005].d.mean()*1e4:+.1f}bp median {r[r.q<=-0.005].d.median()*1e4:+.1f}")
    txt = "\n".join(L); print(txt); open(OUT, "w").write(txt + "\n")


if __name__ == "__main__":
    {"fetch": fetch, "run": run}[sys.argv[1]]()
