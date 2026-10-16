"""NBH: night-leg market beta hedge (H1) and QQQ market-state gates (G1, G2).

Pre-registered in research/drafts/round1_prose.md (N 1011 -> 1014). Exploratory: 2016-26 is touched
for the night leg. QQQ prices all come from the SIP minute files (one adjustment basis):
  close  = 15:59 bar close, open = 09:30 bar open, p40 = 15:39 bar close (the 15:40 print).
"""
import glob

import numpy as np
import pandas as pd

COST_PICK = 2 * 7.5e-4      # round trip on picks
COST_HEDGE = 2 * 1e-4       # round trip on QQQ hedge notional
NIGHT_W = 0.65
OUT = "data/research/program/nbh_out.txt"


def qqq_daily():
    m = pd.concat(pd.read_parquet(f) for f in sorted(glob.glob("data/research/night/m1/QQQ_20*.parquet")))
    t = pd.to_datetime(m.timestamp, utc=True).dt.tz_convert("America/New_York")
    m = m.assign(d=t.dt.tz_localize(None).dt.normalize(), hm=t.dt.strftime("%H:%M"))
    g = lambda hm, col: m[m.hm == hm].set_index("d")[col]
    q = pd.DataFrame({"open": g("09:30", "open"), "p40": g("15:39", "close"), "close": g("15:59", "close")}).dropna()
    q["on"] = q.open.shift(-1) / q.close - 1             # close(d) -> open(d+1)
    q["d40"] = q.p40 / q.close.shift(1) - 1               # 15:40 day return
    q["ma20"] = q.close.shift(1).rolling(20).mean()       # prior 20 closes
    return q


def night_series():
    a = pd.read_parquet("data/research/program/night_exact_pre2021.parquet").reset_index()
    a = a[a.date < "2020-11-05"][["date", "sym", "ret"]]
    b = pd.read_parquet("data/research/recent/night_replay.parquet")[["date", "sym", "ret"]]
    b["ret"] = b.ret / 1e4
    p = pd.concat([a, b])
    p["date"] = pd.to_datetime(p.date)
    s = p.groupby("date").ret.agg(["mean", "median", "size"])
    s["net"] = s["mean"] - COST_PICK
    return p, s


def stats(r, label):
    r = r.dropna()
    eq = (1 + r * NIGHT_W).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    sh = r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else np.nan
    t = r.mean() / r.std() * np.sqrt(len(r)) if r.std() > 0 else np.nan
    yr = eq.iloc[-1] ** (252 / len(r)) - 1
    ex5 = r.drop(r.nlargest(5).index).mean()
    return (f"  {label:<26} n {len(r):5d}  mean {r.mean()*1e4:+7.1f}bp  med {r.median()*1e4:+6.1f}  t {t:5.2f}"
            f"  ex-top5 {ex5*1e4:+6.1f}  Sharpe {sh:5.2f}  maxDD {dd*100:6.1f}%  %/yr@0.65 {yr*100:+6.1f}"), sh, dd, yr


def main():
    q = qqq_daily()
    picks, s = night_series()
    cal = q.index[(q.index >= s.index.min()) & q.on.notna()]
    d = pd.DataFrame(index=cal)
    d["net"] = s.net.reindex(cal).fillna(0.0)        # no picks -> flat
    d["has"] = s["size"].reindex(cal).fillna(0) > 0
    d = d.join(q[["on", "d40", "p40", "ma20"]])
    d = d[d.index <= picks.date.max()]

    # H1: rolling beta over the prior 250 pick-nights (min 60), clipped [0, 6]
    beta = pd.Series(np.nan, index=d.index)
    pn = d[d.has]
    for i, dt in enumerate(pn.index):
        w = pn.iloc[max(0, i - 250):i]
        if len(w) >= 60:
            c = np.cov(w.net, w.on)
            beta[dt] = np.clip(c[0, 1] / c[1, 1], 0, 6)
    d["beta"] = beta.where(d.has)
    d["h1"] = np.where(d.has & d.beta.notna(), d.net - d.beta * d.on - d.beta * COST_HEDGE, np.nan)
    d.loc[~d.has, "h1"] = 0.0
    d["base"] = np.where(d.beta.notna() | ~d.has, d.net, np.nan)   # same sample as H1
    g1 = d.d40 <= -0.01
    g2 = d.p40 < d.ma20
    d["g1"] = np.where(g1, 0.0, d.net)
    d["g2"] = np.where(g2, 0.0, d.net)

    lines = ["NBH: night beta hedge + QQQ gates (exploratory; 2016-26 touched). Per-night equal-weight picks,",
             f"7.5bp/side picks, 1bp/side hedge. Sample {d.index.min().date()}..{d.index.max().date()}.", ""]
    eras = [("2016-20", d.index < "2021-01-01"), ("2021-26", d.index >= "2021-01-01"), ("all", d.index == d.index)]
    verdict = {}
    for arm, col in [("BASE", "base"), ("H1 hedge", "h1"), ("BASE (gate sample)", "net"), ("G1 skip QQQ15:40<=-1%", "g1"),
                     ("G2 skip QQQ<MA20", "g2")]:
        lines.append(arm)
        for en, m in eras:
            ln, sh, dd, yr = stats(d.loc[m, col], en)
            lines.append(ln)
            verdict[(col, en)] = (sh, dd, yr)
        lines.append("")

    lines.append("H1 detail")
    hb = d[d.has & d.beta.notna()]
    lines.append(f"  beta used: median {hb.beta.median():.2f}  p10 {hb.beta.quantile(.1):.2f}  p90 {hb.beta.quantile(.9):.2f}")
    lines.append(f"  QQQ overnight on pick nights: mean {hb.on.mean()*1e4:+.1f}bp; hedge drag mean {(hb.beta*hb.on).mean()*1e4:+.1f}bp")
    for en, m in eras:
        x = d.loc[m & d.has & d.beta.notna(), "h1"]
        lines.append(f"  residual on pick nights {en}: mean {x.mean()*1e4:+.1f}bp t {x.mean()/x.std()*np.sqrt(len(x)):.2f}"
                     f" med {x.median()*1e4:+.1f} n {len(x)}")
    lines.append("")
    lines.append("Gate detail (pick nights only, net)")
    for name, gm in [("G1", g1), ("G2", g2)]:
        for en, m in eras:
            sk = d.loc[m & gm & d.has, "net"]
            kp = d.loc[m & ~gm & d.has, "net"]
            lines.append(f"  {name} {en}: skipped n {len(sk)} mean {sk.mean()*1e4:+.1f}bp t {sk.mean()/sk.std()*np.sqrt(len(sk)):.2f}"
                         f" | kept n {len(kp)} mean {kp.mean()*1e4:+.1f}bp")
    lines.append("")

    lines.append("Registered gate")
    for arm, col, base in [("H1", "h1", "base"), ("G1", "g1", "net"), ("G2", "g2", "net")]:
        ok = True
        for en in ("2016-20", "2021-26"):
            sh, dd, yr = verdict[(col, en)]
            bsh, bdd, byr = verdict[(base, en)]
            c = (sh - bsh >= 0.15) and (dd > bdd)
            if arm == "H1":
                c = c and yr >= 0.75 * byr
            else:
                g = g1 if arm == "G1" else g2
                m = dict(eras)[en]
                c = c and d.loc[m & g & d.has, "net"].mean() < 0
            lines.append(f"  {arm} {en}: dSharpe {sh-bsh:+.2f} maxDD {dd*100:.1f}% vs {bdd*100:.1f}% %/yr {yr*100:+.1f} vs {byr*100:+.1f} -> {'ok' if c else 'fail'}")
            ok &= c
        lines.append(f"  {arm}: {'PASS' if ok else 'FAIL'}")
    txt = "\n".join(lines)
    print(txt)
    open(OUT, "w").write(txt + "\n")


if __name__ == "__main__":
    main()
