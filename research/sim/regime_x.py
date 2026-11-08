"""Study REGIME-X (N 1160-1164): drawdown-control rules on the daily-bar book (0.5 IBS + 0.5 night), one run.
Pre-reg research/drafts/round1_prose.md "Study REGIME-X". Legs from research/sim/regime_x_legs.py (REGIME-10M harness).
  PYTHONPATH=.:../sharadar-data python3 -m research.sim.regime_x
Signals use data as of d-1 (no close-of-d lookahead). Book returns are dated by the signal day (SHAR-CRASH convention):
the sleeve's close-to-close returns are therefore ~1 session out of phase with the book (stated; immaterial at monthly rebalance)."""
import pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/regime_x"
OUT = ROOT / "data/research/program/regime_x_out.txt"
SH = pathlib.Path.home() / "data/sharadar/funds.parquet"
WIN = {"JUDGE 1999-2015": ("1999-01-04", "2015-12-31"), "REPORT 2016-26": ("2016-01-04", "2026-09-18")}
STRESS = [("2000-02", "2000-01-01", "2002-12-31"), ("2008-09", "2008-01-01", "2009-12-31"), ("2011", "2011-01-01", "2011-12-31"),
          ("2015-16", "2015-08-01", "2016-02-29"), ("2018Q4", "2018-10-01", "2018-12-31"), ("2020", "2020-02-01", "2020-04-30"),
          ("2022", "2022-01-01", "2022-12-31")]
L = []
rng = np.random.default_rng(1160)


def P(s=""):
    print(s, flush=True); L.append(s)


def stats(r):
    r = r.fillna(0.0); eq = (1 + r).cumprod(); yrs = len(r) / 252
    cagr = eq.iloc[-1] ** (1 / yrs) - 1; mdd = float((eq / eq.cummax() - 1).min())
    return cagr, mdd, cagr / abs(mdd) if mdd < 0 else np.nan


def mdd(r):
    eq = (1 + r.fillna(0.0)).cumprod(); return float((eq / eq.cummax() - 1).min())


def fred(name):
    x = pd.read_csv(D / f"{name}.csv", na_values=".", parse_dates=[0], index_col=0).iloc[:, 0].dropna(); return x


legs = pd.read_parquet(D / "legs.parquet"); idx = legs.index
book = 0.5 * legs.ibs + 0.5 * legs.night
vix = pd.read_csv(ROOT / "data/research/oil_shock/VIXCLS.csv", na_values=".", parse_dates=[0], index_col=0).iloc[:, 0].dropna()
baa = fred("BAA10Y"); tb = fred("DTB3")
rf = (tb.reindex(idx, method="ffill") / 100 / 252).fillna(0.0)


def expo_credit():
    s = baa.reindex(idx, method="ffill"); sma = baa.rolling(252).mean().reindex(idx, method="ffill")
    return (~(s > sma)).astype(float).shift(1).fillna(1.0)


def expo_vix():
    return (~(vix.reindex(idx, method="ffill") > 30)).astype(float).shift(1).fillna(1.0)


def path_dependent(rule, r):
    """Exposure from the book's own equity known at the close of signal day d. The book row d-1 holds the IBS trade
    open(d)->open(d+1), not known at close d, so only rows <= d-2 are used (lag 2). GZ-DD on the gated equity,
    EQ-SMA on the ungated (shadow) equity (a gate on its own gated curve freezes once OFF)."""
    rv = r.fillna(0.0).to_numpy(); n = len(rv); e = np.ones(n); W = np.ones(n + 1); M = np.ones(n + 1); U = np.ones(n + 1)
    for i in range(n):
        k = i - 1                                   # equity index after row i-2 is k = i-1 (W[0] = start)
        if k >= 0:
            if rule == "gz":
                e[i] = min(1.0, max(0.25, (W[k] / M[k] - 0.75) / 0.25))
            else:
                e[i] = 1.0 if k < 200 or U[k] > U[k - 199:k + 1].mean() else 0.0
        W[i + 1] = W[i] * (1 + e[i] * rv[i]); M[i + 1] = max(M[i], W[i + 1]); U[i + 1] = U[i] * (1 + rv[i])
    return pd.Series(e, index=r.index)


def gate_returns(e, base, cash=True):
    return e * base + ((1 - e) * rf.reindex(base.index) if cash else 0.0)


def placebo(e, base, lo, hi, cut_real, n=200):
    """Circular shift of the gate series by >= 252 sessions; share of placebos with a smaller maxDD cut than the real gate."""
    m = (base.index >= lo) & (base.index <= hi); b = base[m]; ev = e[m].to_numpy(); bm = mdd(b); cnt = 0
    for _ in range(n):
        k = rng.integers(252, len(ev) - 252); ep = np.roll(ev, k)
        cut = 1 - mdd(pd.Series(ep * b.to_numpy() + (1 - ep) * rf[m].to_numpy())) / bm
        cnt += cut < cut_real
    return cnt / n


def report_gate(nm, e_full, path=None):
    P(f"== {nm}: OFF/de-risked share {(e_full < 1).mean()*100:.0f}% of sessions, mean exposure {e_full.mean():.2f}")
    verdict = []
    for w, (lo, hi) in WIN.items():
        m = (idx >= lo) & (idx <= hi); b = book[m]
        e = path_dependent(path, b) if path else e_full[m]
        g = gate_returns(e, b) ; st = e.mean() * b + (1 - e.mean()) * rf[m]
        (bc, bm, bk), (gc, gm, gk), (sc_, sm, sk) = stats(b), stats(g), stats(st)
        cut = 1 - gm / bm; give = 1 - gc / bc
        off = b[e < 1]; on = b[e >= 1]
        pl = placebo(e_full, book, lo, hi, cut) if path is None else (placebo(path_dependent(path, book), book, lo, hi, cut) if path == 'eqsma' else np.nan)
        ok = cut >= 1 / 3 and give <= 0.20 and gk > sk and (path == 'gz' or pl >= 0.9)
        verdict.append(ok)
        P(f"  {w}: base CAGR {bc*100:5.1f}% maxDD {bm*100:6.1f}% Calmar {bk:4.2f} | gated {gc*100:5.1f}% / {gm*100:6.1f}% / {gk:4.2f} | "
          f"static@{e.mean():.2f} {sc_*100:5.1f}% / {sm*100:6.1f}% / {sk:4.2f} | DD cut {cut*100:+5.1f}% CAGR given up {give*100:+5.1f}% | "
          f"book on OFF days {off.mean()*1e4:+5.1f}bp (n {len(off)}) vs ON {on.mean()*1e4:+5.1f}bp | placebo pct {pl if pl == pl else 'n/a'} | {'ok' if ok else 'FAIL'}")
        for sn, a, z in STRESS:
            if a >= lo and z <= hi:
                mm = (b.index >= a) & (b.index <= z)
                P(f"     {sn:8s} maxDD base {mdd(b[mm])*100:6.1f}%  gated {mdd(g[mm])*100:6.1f}%  exposure {e[mm].mean():.2f}")
        if path is None:
            for leg in ("ibs", "night"):
                lg = legs[leg][m]; P(f"     leg {leg:5s}: OFF {lg[e < 1].mean()*1e4:+5.1f}bp vs ON {lg[e >= 1].mean()*1e4:+5.1f}bp")
    P(f"  => {'PASS candidate' if all(verdict) else 'KILL'}"); P()


P("REGIME-X (N 1160-1164). Book = 0.5 IBS + 0.5 night, 5bp/side, daily-bar delisted-complete Sharadar; cash earns DTB3.")
report_gate("N 1160 CREDIT (BAA10Y > 252d SMA -> OFF)", expo_credit())
report_gate("N 1161 VIX30 (VIX > 30 -> OFF)", expo_vix())
report_gate("N 1162 GZ-DD (D=0.25, floor 0.25)", pd.Series(1.0, index=idx), path="gz")
report_gate("N 1163 EQ-SMA (book equity < 200d SMA -> OFF)", pd.Series(1.0, index=idx), path="eqsma")

# ---------------- N 1164 SLEEVE
f = pd.read_parquet(SH, columns=["ticker", "date", "close", "closeadj"], filters=[("ticker", "in", ["TLT", "GLD", "WTMF", "DBMF"])])
f["date"] = pd.to_datetime(f["date"]); f = f.drop_duplicates(["ticker", "date"])
ca = f.pivot(index="date", columns="ticker", values="closeadj").sort_index(); cl = f.pivot(index="date", columns="ticker", values="close").sort_index()


def sleeve_sim(start_v, w, names, lo, hi, whole=True):
    """Dollar sim: book fraction (1-w) gets book returns; sleeve rebalanced to w at each month start, whole shares, 2bp/side."""
    lo = max(pd.Timestamp(lo), max(ca[n].first_valid_index() for n in names) + pd.Timedelta(days=31))
    days = idx[(idx >= lo) & (idx <= hi)]
    rets = ca[names].pct_change(fill_method=None).reindex(days).fillna(0.0)
    vb = start_v * (1 - w); sh = {n: 0.0 for n in names}; cash = start_v * w; vals = []; prevm = None; px = None
    for d in days:
        if d.to_period("M") != prevm:
            prevm = d.to_period("M")
            px = cl[names].loc[:d].ffill().iloc[-1].to_dict()          # raw price at the prior/current close
            V = vb + cash + sum(sh[n] * px[n] for n in names)
            vb = V * (1 - w); tgt = V * w / len(names); cash = V * w; old = dict(sh)
            for n in names:
                sh[n] = np.floor(tgt / px[n]) if whole else tgt / px[n]
                cash -= sh[n] * px[n] + abs(sh[n] - old[n]) * px[n] * 2e-4
        vb *= 1 + book.get(d, 0.0); cash *= 1 + rf.get(d, 0.0)
        for n in names:
            px[n] = px[n] * (1 + rets.at[d, n])     # adjusted (total) return on the held position
        vals.append(vb + cash + sum(sh[n] * px[n] for n in names))
    return pd.Series(vals, index=days)


def vstats(v):
    return stats(v.pct_change(fill_method=None).fillna(0.0))


P("== N 1164 SLEEVE: 75% book + 25% sleeve, monthly, whole shares (book part fractional as the book series). 'bills' = 75% book + 25% DTB3.")
SWIN = {"JUDGE 2003-2015": ("2003-01-02", "2015-12-31"), "REPORT 2016-26": ("2016-01-04", "2026-09-18"),
        "WTMF 2011-26": ("2011-06-01", "2026-09-18"), "DBMF 2019-26": ("2019-06-03", "2026-09-18")}
CASES = {"JUDGE 2003-2015": [["TLT"], ["GLD"], ["TLT", "GLD"]], "REPORT 2016-26": [["TLT"], ["GLD"], ["TLT", "GLD"]],
         "WTMF 2011-26": [["WTMF"], ["TLT"]], "DBMF 2019-26": [["DBMF"], ["TLT"]]}
for w, (lo, hi) in SWIN.items():
    m = (idx >= lo) & (idx <= hi); b = book[m]; bills = 0.75 * b + 0.25 * rf[m]
    (bc, bm, bk), (lc, lm, lk) = stats(b), stats(bills)
    P(f"  {w}: book {bc*100:5.1f}% / {bm*100:6.1f}% / Calmar {bk:4.2f} | bills mix {lc*100:5.1f}% / {lm*100:6.1f}% / {lk:4.2f}")
    for names in CASES[w]:
        row = []
        for v0 in (2300, 10000, 25000):
            c, dd, k = vstats(sleeve_sim(v0, 0.25, names, lo, hi)); row.append(f"${v0/1000:g}k {c*100:5.1f}%/{dd*100:6.1f}%/{k:4.2f}")
        c, dd, k = vstats(sleeve_sim(1e7, 0.25, names, lo, hi, whole=False))
        ok = (1 - dd / bm) >= 1 / 3 and (1 - c / bc) <= 0.20 and k > lk
        P(f"    sleeve {'+'.join(names):8s} frac {c*100:5.1f}% / {dd*100:6.1f}% / {k:4.2f} | DD cut {(1-dd/bm)*100:+5.1f}% given up {(1-c/bc)*100:+5.1f}% | "
          + " ".join(row) + f" | {'ok' if ok else 'FAIL'}")
OUT.write_text("\n".join(L) + "\n")
