"""CRASH-C extension: Great-Crash-scale staged bottom buying on CRSP. Pre-reg in round1_prose.md."""
from __future__ import annotations
import pathlib, sys
import numpy as np, pandas as pd
ROOT = pathlib.Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
from research.sim.borrow_xs import conn  # noqa: E402
OUT = ROOT / "data/research/program/crash_c_great_out.txt"
lines = []
def say(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); lines.append(s)
WIN = {"1929-32": ("1928-01-01", "1930-01-01"), "1937-38": ("1936-01-01", "1938-01-01"),
       "1973-74": ("1972-01-01", "1974-01-01"), "2000-02": ("1999-01-01", "2001-01-01"),
       "2007-09": ("2007-01-01", "2008-01-01")}
TC = 0.0025
db = conn()
di = db.raw_sql("select date, vwretd from crsp.dsi where date>='1926-01-01' order by date")
di["date"] = pd.to_datetime(di.date); lvl = (1 + di.set_index("date").vwretd.fillna(0)).cumprod()
sma = lvl.rolling(210).mean()

def run_rule(name, lv, sma_w, trig):
    """returns equity curve (account value, start 1.0 cash) given weights path."""
    pass

def sim(lv, w):
    """w: Series of target invested fraction of the START cash notionally. Account = cash + shares."""
    r = lv.pct_change().fillna(0)
    return r

def curve(lv, buys, sells=None):
    """buys: list of (date, fraction of initial cash). sells: list of dates -> all to cash. Returns account equity series from first buy."""
    ev = sorted([(d, "b", f) for d, f in buys] + [(d, "s", 0) for d in (sells or [])])
    cash, sh = 1.0, 0.0; eq = []; k = 0
    for d in lv.index[lv.index >= ev[0][0]]:
        while k < len(ev) and ev[k][0] <= d:
            _, t, f = ev[k]
            if t == "b":
                amt = min(cash, f); cash -= amt; sh += amt * (1 - TC) / lv[d]
            else:
                cash += sh * lv[d]; sh = 0.0
            k += 1
        eq.append((d, cash + sh * lv[d]))
    return pd.Series(dict(eq))

def stats(eq, deployed0):
    if eq is None or len(eq) == 0: return None
    # drawdown of the account from its running peak after first purchase, relative to cash 1.0 start
    pk = eq.cummax(); dd = (eq / pk - 1).min()
    below = eq < 1.0 - 1e-9
    # break-even: first date after the worst point where eq >= 1.0 (initial cash)
    tr = eq.idxmin(); after = eq[eq.index >= tr]; be = after[after >= 1.0]
    sess = None
    if below.any():
        sess = (len(eq[(eq.index >= eq.index[0]) & (eq.index <= be.index[0])]) if len(be) else None)
    else: sess = 0
    return dict(dd=dd, trough=eq.min() - 1, final=eq.iloc[-1], be_sess=sess, never=len(be) == 0 and below.any())

res = {}
for w, (a, b) in WIN.items():
    seg = lvl[(lvl.index >= a) & (lvl.index <= b)]
    pk_d = seg.idxmax(); pk = lvl[pk_d]
    after = lvl[lvl.index >= pk_d]
    rec = after[(after >= pk) & (after.index > pk_d)]
    end_cap = pk_d + pd.DateOffset(years=6)
    end = min(end_cap, rec.index[0] if len(rec) else end_cap)
    # extend end to cap even if recovered? use recovery for index; evaluation window ends at the cap so rules can break even
    lv = lvl[(lvl.index >= pk_d) & (lvl.index <= end_cap)]
    dd = lv / pk - 1
    trough_d = dd[dd.index <= end_cap].idxmin()
    say(f"\n=== {w}: peak {pk_d.date()}, index maxDD {dd.min()*100:.1f}% on {trough_d.date()}, recovers peak: {rec.index[0].date() if len(rec) else 'not within 6y'}, window end {lv.index[-1].date()} ===")
    def first(th):
        x = dd[dd <= -th]; return x.index[0] if len(x) else None
    rules = {}
    # R1 staged
    b1 = [(first(t), 1 / 3) for t in (0.30, 0.50, 0.70) if first(t) is not None]
    rules["R1 staged -30/-50/-70"] = curve(lv, b1) if b1 else None
    d30 = first(0.30)
    rules["R2 all-in at -30%"] = curve(lv, [(d30, 1.0)]) if d30 is not None else None
    # R3 trend-confirmed after >=40% DD: all-in at first close >=40% below peak seen AND close above 210d SMA
    ev_b, ev_s, inpos, seen40 = [], [], False, False
    sm = sma.reindex(lv.index)
    for d in lv.index:
        if dd[d] <= -0.40: seen40 = True
        if not seen40 or not np.isfinite(sm[d]): continue
        if not inpos and lv[d] > sm[d]:
            ev_b.append((d, 1.0)); inpos = True
        elif inpos and lv[d] < 0.95 * sm[d] and len(ev_s) < 1:
            ev_s.append(d); inpos = False
    say(f"  R3 events: buys {[str(d.date()) for d,_ in ev_b]} sells {[str(d.date()) for d in ev_s]}")
    rules["R3 trend-confirmed (>=40% DD, >210d SMA)"] = curve(lv, ev_b[:1] if not ev_s else ev_b, ev_s) if ev_b else None
    # R4 hold from peak
    rules["R4 buy&hold from peak (benchmark)"] = curve(lv, [(pk_d, 1.0)])
    for nme, eq in rules.items():
        if eq is None: say(f"  {nme}: never triggered"); continue
        s = stats(eq, 1.0); res[(w, nme)] = (s, eq)
        say(f"  {nme}: first buy {eq.index[0].date()}, worst acct dd {s['dd']*100:.1f}%, lowest value {s['trough']*100:+.1f}% vs cash, "
            f"final {s['final']*100-100:+.1f}%, break-even sessions {('NEVER in window' if s['never'] else s['be_sess'])} | $2.3k->{2300*s['final']:,.0f} $10k->{10000*s['final']:,.0f} $25k->{25000*s['final']:,.0f}")
    # R5 cheapest decile at d30 via msf
    if d30 is None: continue
    me = pd.Timestamp(d30) + pd.offsets.MonthEnd(0)
    lo = (me - pd.DateOffset(months=14)).strftime("%Y-%m-%d"); hi = end_cap.strftime("%Y-%m-%d")
    try:
        m = db.raw_sql(f"""select a.permno, a.date, abs(a.prc) prc, a.ret, d.dlret from crsp.msf a
            join crsp.msenames n on a.permno=n.permno and a.date between n.namedt and n.nameendt and n.shrcd in (10,11)
            left join crsp.msedelist d on a.permno=d.permno and date_trunc('month',a.date)=date_trunc('month',d.dlstdt)
            where a.date between '{lo}' and '{hi}' """, date_cols=["date"])
        m = m.sort_values(["permno", "date"]); m["ret"] = m.ret.fillna(0)
        m["tr"] = (1 + m.ret) * (1 + m.dlret.fillna(0)) - 1
        e = m[m.date <= me]; ent = e.groupby("permno").agg(p=("prc", "last"), h=("prc", lambda s: s.tail(12).max()), n=("prc", "size"), ld=("date", "max"))
        ent = ent[(ent.ld == ent.ld.max()) & (ent.n >= 10) & (ent.p >= 1)]
        ent["ratio"] = ent.p / ent.h
        low = ent[ent.ratio <= ent.ratio.quantile(0.10)].index
        h = m[(m.date > me)]
        def basket(ids):
            g = h[h.permno.isin(ids)].pivot(index="date", columns="permno", values="tr").fillna(0)
            return (1 + g.mean(axis=1)).cumprod() * (1 - TC)
        bk = basket(low); allb = basket(ent.index)
        idx_end = lvl[(lvl.index > me) & (lvl.index <= pd.Timestamp(h.date.max()))]
        idxc = idx_end / lvl[lvl.index <= me].iloc[-1]
        eqc = pd.concat([pd.Series([1.0], index=[me]), bk]); pkc = eqc.cummax()
        say(f"  R5 cheapest decile (price/52w-high, n {len(low)}) from {me.date()}: final {bk.iloc[-1]*100-100:+.1f}% | all-stock EW {allb.iloc[-1]*100-100:+.1f}% | "
            f"index {idxc.iloc[-1]*100-100:+.1f}% | worst dd {(eqc/pkc-1).min()*100:.1f}% (monthly) | lowest value {eqc.min()*100-100:+.1f}%"
            f" | $10k -> {10000*bk.iloc[-1]:,.0f}")
    except Exception as ex:
        say(f"  R5 failed: {ex!r}")
OUT.write_text("\n".join(lines) + "\n")
