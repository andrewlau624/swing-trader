"""Study INCOME-SHOCK (pre-reg round1_prose.md, N 1020 -> 1021). One run, no tuning.
Usage: .venv/bin/python research/sim/income_shock.py"""
import warnings; warnings.filterwarnings("ignore")
import pathlib, sys, io, numpy as np, pandas as pd, pyarrow.dataset as ds
ROOT = pathlib.Path(__file__).resolve().parents[2]
S = pathlib.Path.home() / "data" / "sharadar"
C = ROOT / "data/research/income_shock"; C.mkdir(parents=True, exist_ok=True)
OUT = ROOT / "data/research/program/income_shock_out.txt"
buf = io.StringIO()
def P(*a):
    s = " ".join(str(x) for x in a); print(s); buf.write(s + "\n")
COST = 0.005

# ---------- universe + prices
t = ds.dataset(S / "tickers.parquet").to_table().to_pandas()
u = t[((t.table == "SEP") & (t.category == "Domestic Preferred Stock")) | ((t.table == "SFP") & (t.category == "ETD"))].drop_duplicates(["table", "ticker"])
meta = u.set_index("ticker")[["table", "name", "permaticker", "relatedtickers", "cusips"]]
def load(path, tb):
    tk = u[u.table == tb].ticker.tolist()
    b = ds.dataset(S / path).to_table(columns=["ticker", "date", "closeunadj", "volume"], filter=ds.field("ticker").isin(tk)).to_pandas()
    return b
b = pd.concat([load("stocks.parquet", "SEP"), load("funds.parquet", "SFP")])
b["date"] = pd.to_datetime(b.date); b = b[b.closeunadj > 0].drop_duplicates(["ticker", "date"]).sort_values(["ticker", "date"])
b = b.rename(columns={"closeunadj": "px"})
b["dv"] = (b.px * b.volume).groupby(b.ticker).transform(lambda s: s.shift(1).rolling(20, min_periods=10).median())
b["elig"] = b.dv >= 5e4
px = b.pivot(index="date", columns="ticker", values="px")
el = b.pivot(index="date", columns="ticker", values="elig").reindex_like(px).fillna(False).astype(bool)
dates = px.index
# ---------- dividends with FXD guard
a = ds.dataset(S / "actions.parquet").to_table(columns=["date", "action", "ticker", "value"]).to_pandas()
a = a[(a.action == "dividend") & a.ticker.isin(px.columns)].copy(); a["date"] = pd.to_datetime(a.date)
a = a.groupby(["ticker", "date"], as_index=False).value.sum()
# adjusted close for the guard
def adj(path, tb):
    tk = u[u.table == tb].ticker.tolist()
    return ds.dataset(S / path).to_table(columns=["ticker", "date", "closeadj", "close"], filter=ds.field("ticker").isin(tk)).to_pandas()
ad = pd.concat([adj("stocks.parquet", "SEP"), adj("funds.parquet", "SFP")]); ad["date"] = pd.to_datetime(ad.date)
ad = ad.drop_duplicates(["ticker", "date"]).sort_values(["ticker", "date"])
g = ad.groupby("ticker", sort=False)
ad["y_adj"] = 1 - (ad.close / g.close.shift(1)) / (ad.closeadj / g.closeadj.shift(1))
a = a.merge(ad[["ticker", "date", "y_adj"]], on=["ticker", "date"], how="left")
pc = px.shift(1).stack().rename("pc").reset_index()
a = a.merge(pc, on=["ticker", "date"], how="left")
a["y"] = a.value / a.pc
a["ok"] = (a.y - a.y_adj).abs() < 0.10
P(f"dividends: {len(a)}, FXD-guard fail {(~a.ok).sum()} ({(~a.ok).mean():.3%}), dropped; NaN-guard kept as fail")
a = a[a.ok]
dv = a.pivot_table(index="date", columns="ticker", values="value", aggfunc="sum").reindex(index=dates, columns=px.columns).fillna(0.0)

# ---------- trigger
r10 = px / px.shift(10) - 1
r10 = r10.where(el & el.shift(10, fill_value=False))        # eligible at both ends
n_el = el.sum(axis=1)
ew = r10.mean(axis=1); med = px.where(el).median(axis=1)
trig = (ew <= -0.10) & (med <= 0.90 * 25)
P(f"universe: {px.shape[1]} tickers; eligible/day median {int(n_el.median())}, max {int(n_el.max())}")
fires = []; last = -10**9
for i, d in enumerate(dates):
    if d.year < 2002: continue
    if trig.iloc[i] and i - last > 120:
        fires.append(i); last = i
P("fires (date, n eligible, EW10d, median px):")
for i in fires: P("  ", dates[i].date(), int(n_el.iloc[i]), f"{ew.iloc[i]:+.3f}", f"{med.iloc[i]:.2f}")
P("all trigger days by year:", trig.groupby(dates.year).sum()[lambda s: s > 0].to_dict())

# ---------- screen: FISD / TRACE via WRDS
import wrds, time
sys.path.insert(0, str(ROOT))
U = open(pathlib.Path.home() / ".pgpass").readline().split(":")[3]
def conn():
    for k in range(20):
        try: return wrds.Connection(wrds_username=U, wrds_connect_attempts=2)
        except BaseException: time.sleep(min(60, 5 * (k + 1)))
    raise RuntimeError("wrds")
db = None
def sql(q):
    global db
    if db is None: db = conn()
    return db.raw_sql(q)

# issuer link: Sharadar sec name -> FISD issuer by name. Candidate names = Sharadar name of the (parent) issuer.
import re
def norm(s):
    s = re.sub(r"[^A-Z0-9 ]", " ", str(s).upper())
    s = re.sub(r"\b(THE|INC|CORP|CORPORATION|CO|COMPANY|LTD|LLC|LP|PLC|NEW|DE|HOLDINGS?|GROUP|FINANCIAL|TRUST|THE)\b", " ", s)
    return " ".join(s.split())
def cands(i):
    return sorted({meta.loc[tk, "name"] for tk in i})
ev_names = {}
for i in fires:
    d = dates[i]; names = px.columns[el.iloc[i].values & px.iloc[i].notna().values]
    ev_names[i] = list(names)
allnames = sorted({n for v in ev_names.values() for n in v})
nm = pd.DataFrame({"ticker": allnames}); nm["name"] = nm.ticker.map(meta.name); nm["nn"] = nm.name.map(norm)
fc = C / "fisd_issuer.parquet"
if fc.exists(): iss = pd.read_parquet(fc)
else:
    iss = sql("select issuer_id, cusip_name as issuer_name, parent_id from fisd.fisd_issuer")
    iss.to_parquet(fc)
iss["nn"] = iss.issuer_name.map(norm)
# exact normalized name match; if several issuers share it, keep all (bond screen is OR over them)
lk = nm.merge(iss[["issuer_id", "issuer_name", "nn"]], on="nn", how="left")
P(f"\nname->FISD issuer link: {lk.groupby('ticker').issuer_id.apply(lambda s: s.notna().any()).mean():.1%} of event-universe tickers matched by normalized name")
lk.to_csv(C / "links.csv", index=False)

# senior unsecured bonds & rating per issuer
ids = sorted(lk.issuer_id.dropna().unique().tolist())
def inlist(x): return ",".join(str(int(v)) for v in x) or "0"
fb = C / "fisd_issue.parquet"
if fb.exists(): iue = pd.read_parquet(fb)
else:
    iue = sql(f"select issue_id, issuer_id, complete_cusip, issue_name, offering_date, maturity, security_level, coupon_type, bond_type, principal_amt from fisd.fisd_mergedissue where issuer_id in ({inlist(ids)})")
    iue.to_parquet(fb)
P("FISD security_level values:", iue.security_level.value_counts().head(8).to_dict())
fr = C / "fisd_rating.parquet"
if fr.exists(): rat = pd.read_parquet(fr)
else:
    iids = iue.issue_id.tolist()
    rat = sql(f"select issue_id, rating_type, rating, rating_date from fisd.fisd_ratings where issue_id in ({inlist(iids)})")
    rat.to_parquet(fr)
rat["rating_date"] = pd.to_datetime(rat.rating_date)
IG = {"AAA","AA+","AA","AA-","A+","A","A-","BBB+","BBB","BBB-","Aaa","Aa1","Aa2","Aa3","A1","A2","A3","Baa1","Baa2","Baa3"}
rat = rat.merge(iue[["issue_id", "issuer_id"]], on="issue_id")
rat = rat[rat.rating_type.isin(["SPR", "MR", "FR"])]  # DPR (Duff) excluded          # S&P, Moody's, Fitch
P("ratings rows (issuer-linked):", len(rat))
sen = iue[iue.security_level.astype(str).str.strip() == "SEN"]   # FISD senior (SENS = secured, excluded)
P("senior-unsecured issues for linked issuers:", len(sen), "(security_level in", sorted(sen.security_level.astype(str).unique())[:5], ")")

_tc = {}
def trace_screen(d, cusips):
    k = (d, tuple(sorted(cusips)))
    if k not in _tc: _tc[k] = _trace_screen(d, cusips)
    return _tc[k]
def _trace_screen(d, cusips):
    """senior unsecured TRACE trade yield<8% in 10 sessions before d (strictly prior)."""
    if not cusips: return None, 0
    lo = (d - pd.offsets.BDay(10)).date(); hi = (d - pd.Timedelta(days=1)).date()
    q = f"select cusip_id, yld_pt from trace.trace_enhanced where cusip_id in ({','.join(repr(c) for c in cusips)}) and trd_exctn_dt between '{lo}' and '{hi}' and yld_pt is not null and (cmsn_trd is distinct from 'Y')"
    try: r = sql(q)
    except Exception as e:
        P("   trace_enhanced error:", str(e)[:120]); return None, 0
    return (r.yld_pt.astype(float).lt(8).any() if len(r) else False), len(r)

def pit_ig(d, iids):
    """issuer IG as of d: majority of latest VALID (non-NR/WD) agency ratings across its issues are investment grade."""
    r = rat[rat.issue_id.isin(iids) & (rat.rating_date <= d)].copy()
    r["rating"] = r.rating.astype(str).str.strip()
    r = r[~r.rating.isin(["NR", "WD", "NM", "", "None"])]
    if r.empty: return None
    r = r.sort_values("rating_date").groupby(["issue_id", "rating_type"]).tail(1)
    return bool(r.rating.isin(IG).mean() > 0.5)

# ---------- trade
def basket_ret(i, tk, h):
    """1/3 each at i, i+5, i+10; exit i+h; raw closes + dividends + 50bp/side; delisted = last price."""
    legs = []
    for k in (0, 5, 10):
        e = i + k
        if e >= len(dates) or e + h - k > len(dates) + 10**6: continue
        e0 = px[tk].iloc[e]
        # exit at i+h (last available price if delisted before)
        x = min(i + h, len(dates) - 1)
        seg = px[tk].iloc[:x + 1]
        lastp = seg.ffill().iloc[-1]
        # dividends between e (excl) and x (incl) for the days the name traded
        dsum = dv[tk].iloc[e + 1:x + 1].sum()
        if pd.isna(e0): legs.append(np.nan); continue
        legs.append((lastp + dsum) / e0 - 1 - 2 * COST)
    return np.nanmean(legs) if legs else np.nan
res = []
for i in fires:
    d = dates[i]; names = ev_names[i]
    P(f"\n=== EVENT {d.date()}  n eligible {len(names)} ===")
    # exclude names whose entry px unavailable at i (need price at trigger close)
    tk_scr, tk_uns, trace_hit, rate_hit, nolink = [], [], 0, 0, 0
    for tk in names:
        lrow = lk[lk.ticker == tk]
        iid = lrow.issuer_id.dropna().unique()
        if len(iid) == 0: nolink += 1; tk_uns.append(tk); continue
        ii = sen[sen.issuer_id.isin(iid)]
        cus = ii.complete_cusip.dropna().unique().tolist()
        tr, nt = trace_screen(d, cus) if len(cus) else (None, 0)
        allii = iue[iue.issuer_id.isin(iid)].issue_id.tolist()
        ig = pit_ig(d, allii)
        if nt > 0: trace_hit += 1
        if ig is not None: rate_hit += 1
        ok = bool(tr) or bool(ig)
        (tk_scr if ok else tk_uns).append(tk)
    P(f"  linked {len(names) - nolink}/{len(names)}; with a TRACE obs in 10d {trace_hit}; with a PIT rating {rate_hit}; screened {len(tk_scr)}, unscreened {len(tk_uns)} (incl. {nolink} unlinked)")
    for h in (60, 120, 250):
        out = {}
        for lab, tks in (("scr", tk_scr), ("uns", tk_uns)):
            if not tks: out[lab] = (np.nan, np.nan, np.nan, np.nan, ""); continue
            r = pd.Series({tk: basket_ret(i, tk, h) for tk in tks}).dropna()
            if r.empty: out[lab] = (np.nan, np.nan, np.nan, np.nan, ""); continue
            out[lab] = (r.mean(), r.median(), (r < -0.30).mean(), len(r), f"{r.idxmin()}:{r.min():+.2f}")
        res.append(dict(date=d.date(), h=h, scr=out["scr"][0], uns=out["uns"][0], nscr=out["scr"][3], nuns=out["uns"][3]))
        P(f"  +{h}d: screened mean {out['scr'][0]:+.3f} med {out['scr'][1]:+.3f} (n {out['scr'][3]}, <-30%: {out['scr'][2]:.0%}, worst {out['scr'][4]}) | unscreened mean {out['uns'][0]:+.3f} med {out['uns'][1]:+.3f} (n {out['uns'][3]}, <-30%: {out['uns'][2]:.0%}, worst {out['uns'][4]})")
    # all-name reference
r = pd.DataFrame(res)
P("\n=== GATE ===")
x = r[r.h == 120]
if x.empty: P("no fires -> cannot evaluate")
else:
    pos = (x.scr > 0); med = x.scr.median(); beat = (x.scr > x.uns).mean()
    P(f"events {len(x)}; screened +120d>0 in every event: {bool(pos.all())} ({pos.sum()}/{len(x)}); median across events {med:+.3f} (>= +0.10: {med >= 0.10}); screened beats unscreened {beat:.0%} (>=75%: {beat >= 0.75})")
    bad = x[~(x.scr > 0)]
    ok = bool(pos.all()) and med >= 0.10 and beat >= 0.75
    P("VERDICT:", "PASS" if ok else "KILL", "" if ok else f"(broken by: {[str(v) for v in bad.date] or 'median/beat criteria'})")
OUT.write_text(buf.getvalue())
