"""Study CRYPTO-TA12 (round1_prose.md, N 998 -> 1002): the CRYPTO-TA rules on 12h / 8h / 6h / 4h bars.

Same rules and parameters in bars as crypto_ta.py; t clustered by calendar month. Out: data/research/program/crypto_ta12_out.txt
"""
import glob
import io
import zipfile

import numpy as np
import pandas as pd

import crypto_ta as C

IVS = {"12h": 2, "8h": 3, "6h": 4, "4h": 6}  # bars per day
RT = {"25bp/side": 0.005, "75bp/side (judge)": 0.015, "150bp/side (2x)": 0.03}
OUT = "data/research/program/crypto_ta12_out.txt"
YEARS = 8.75


def load(iv, sym):
    rows = []
    for f in sorted(glob.glob(f"data/research/crypto_spot/raw{iv}/{sym}-{iv}-*.zip")):
        with zipfile.ZipFile(f) as z:
            d = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), header=None, usecols=[0, 2, 3, 4])
        d = d[pd.to_numeric(d[0], errors="coerce").notna()].astype(float)
        rows.append(d)
    d = pd.concat(rows)
    ts = d[0].where(d[0] < 1e14, d[0] / 1000)  # spot dumps switched ms -> us in 2025
    # label each bar by its CLOSE time so .loc[START:END] and halves use the moment the signal is known
    idx = pd.to_datetime(ts, unit="ms") + pd.Timedelta(hours=24 / IVS[iv])
    out = pd.DataFrame({"close": d[4].values, "low": d[3].values}, index=idx).sort_index()
    return out[~out.index.duplicated()]


def mstats(df, rt):
    x = df.exc - rt
    def mt(v, dates):
        g = v.groupby(dates.dt.to_period("M")).mean()
        return g.mean() / (g.std(ddof=1) / np.sqrt(len(g))) if len(g) > 2 else np.nan
    srt = np.sort(x.values)
    late = df.date >= "2022-01-01"
    return dict(n=len(x), mean=x.mean() * 1e4, med=x.median() * 1e4, t=mt(x, df.date), t22=mt(x[late], df.date[late]),
                hit=(x > 0).mean(), exTop5=srt[:-5].mean() * 1e4 if len(srt) > 5 else np.nan,
                h1=x[df.date < C.SPLIT].mean() * 1e4, h2=x[df.date >= C.SPLIT].mean() * 1e4)


def run(iv, bpd, lines):
    ppy = 365 * bpd
    F = {s: C.frame(load(iv, s)) for s in C.COINS}
    R = {s: f.close.pct_change().fillna(0) for s, f in F.items()}
    MU = {s: np.log(f.close).diff().mean() for s, f in F.items()}
    bh = pd.concat([R[s] for s in F], axis=1).mean(axis=1)
    bperf = {h: C.perf(bh[m], ppy) for h, m in [("all", bh.index >= C.START), ("h1", bh.index < C.SPLIT), ("h2", bh.index >= C.SPLIT)]}
    lines += [f"\n===== {iv} bars =====", "EW buy&hold basket: " + "  ".join(
        f"{h} CAGR {v['cagr']:+.1%} Sh {v['sharpe']:.2f} mDD {v['mdd']:.0%}" for h, v in bperf.items())]
    summ = []
    for name, (ent, ext) in C.RULES.items():
        tr, pos = [], {}
        for s, f in F.items():
            t_, ps = C.event_trades(f, ent, ext, MU[s])
            tr += [(s,) + x for x in t_]
            pos[s] = pd.Series(ps, index=f.index)
        df = pd.DataFrame(tr, columns=["sym", "date", "days", "ret", "exc"])
        lines.append(f"\n{name}: trades {len(df)} ({len(df)/YEARS:.0f}/yr), mean hold {df.days.mean()/bpd:.1f}d, "
                     f"gross excess {df.exc.mean()*1e4:+.0f}bp")
        for lab, rt in RT.items():
            s_ = mstats(df, rt)
            lines.append(f"  {lab:18s} n {s_['n']:4d} mean {s_['mean']:+6.0f} med {s_['med']:+6.0f} t(mo) {s_['t']:+5.2f} "
                         f"t22 {s_['t22']:+5.2f} hit {s_['hit']:.0%} exTop5 {s_['exTop5']:+6.0f} halves {s_['h1']:+6.0f}/{s_['h2']:+6.0f}")
        b = C.book(pos, R, RT["75bp/side (judge)"])
        v = C.perf(b, ppy)
        j, sh = mstats(df, RT["75bp/side (judge)"]), mstats(df, RT["150bp/side (2x)"])
        ok = j["t"] >= 2 and j["mean"] > 0 and j["h1"] > 0 and j["h2"] > 0 and j["med"] > 0 and j["exTop5"] > 0 \
            and sh["mean"] > 0 and j["t22"] >= 1.0
        lines.append(f"  book @75bp: CAGR {v['cagr']:+.1%} Sh {v['sharpe']:.2f} mDD {v['mdd']:.0%}   VERDICT: {'PASS' if ok else 'FAIL'}")
        summ.append((name, j["mean"], j["med"], j["t"], 'PASS' if ok else 'FAIL'))
    for name, fn in C.REGIME.items():
        pos = {s: fn(f).astype(float).shift(1).fillna(0) for s, f in F.items()}
        lines.append(f"\n{name}: switches/yr/coin {np.mean([pos[s].diff().abs().sum() for s in pos])/YEARS:.1f}, "
                     f"time in market {np.mean([pos[s].mean() for s in pos]):.0%}")
        res = {}
        for lab, rt in RT.items():
            b = C.book(pos, R, rt)
            res[lab] = {h: C.perf(b[m], ppy) for h, m in [("all", b.index >= C.START), ("h1", b.index < C.SPLIT), ("h2", b.index >= C.SPLIT)]}
            lines.append(f"  {lab:18s} " + "  ".join(
                f"{h} CAGR {v['cagr']:+.1%} Sh {v['sharpe']:.2f} mDD {v['mdd']:.0%}" for h, v in res[lab].items()))
        j = res["75bp/side (judge)"]
        ok = all(j[h]["sharpe"] >= bperf[h]["sharpe"] + 0.2 for h in ("h1", "h2")) and j["all"]["mdd"] > bperf["all"]["mdd"]
        lines.append(f"  VERDICT: {'PASS' if ok else 'FAIL'}")
        summ.append((name, j["all"]["cagr"] * 100, j["h2"]["cagr"] * 100, j["h2"]["sharpe"], 'PASS' if ok else 'FAIL'))
    return summ


def main():
    lines = ["Study CRYPTO-TA12 (N 999-1002)  coins " + " ".join(c[:-4] for c in C.COINS) + f"  {C.START}..{C.END}"]
    allsum = {iv: run(iv, bpd, lines) for iv, bpd in IVS.items()}
    lines.append("\nSUMMARY (event rules: net mean / median bp / month t @150bp RT; regime rules: CAGR all / CAGR 2023-26 / Sh 2023-26)")
    for iv, sm in allsum.items():
        for name, a, b, c, v in sm:
            lines.append(f"  {iv:4s} {name:30s} {a:+8.1f} {b:+8.1f} {c:+6.2f}  {v}")
    txt = "\n".join(lines)
    open(OUT, "w").write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
