"""Study DDR (clean-window judge of the lag+5 entry rule, PCAL C2 machinery): calibration of the program's own PASS machinery.

Registered in round1_prose.md ("Study PCAL", diagnostic, no N). One config-run of the NX
night-leg machinery on 2021-2026 with 1 implementation check (C0) and 7 pre-named negative
controls (C1-C7). Judges no candidate signal; produces a false-pass rate p-hat.

  .venv/bin/python research/sim/pcal.py
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from research.sim import book
from swingtrader.daily.signals import loser_picks, night_sizing

STORE = pathlib.Path.home() / "data" / "sharadar"
OUT = pathlib.Path(__file__).resolve().parent / "ddr_out.txt"

LO, HI = pd.Timestamp("1998-01-01"), pd.Timestamp("2020-12-31")
DAY_RET_MAX, IBS_MAX, PRICE_MIN, PRICE_MAX = -0.08, 0.10, 5.0, 2000.0
ADV_MIN = 1e7
MAX_CORR = 0.7
VOL_MIN, CROWD_N, NAME_CAP = 0.60, 30, 0.10
COST = "tier"
SEED = 20261006
DELIST_ACTIONS = {"delisted", "bankruptcyliquidation", "regulatorydelisting", "voluntarydelisting"}


def _roll_prior(x: np.ndarray, w: int) -> np.ndarray:
    cs = np.r_[0.0, np.cumsum(x)]
    i = np.arange(len(x))
    return cs[i] - cs[np.maximum(i - w, 0)]


def build_panel(bars: pd.DataFrame) -> dict:
    """Same semantics as research.sim.nx.build_panel."""
    n = len(bars)
    code = pd.factorize(bars["ticker"].astype(str))[0]
    newg = np.r_[True, code[1:] != code[:-1]]
    start = np.maximum.accumulate(np.where(newg, np.arange(n), 0))
    pos = np.arange(n) - start
    c = bars["close"].to_numpy(float)
    cu = bars["closeunadj"].to_numpy(float)
    o = bars["open"].to_numpy(float)
    h = bars["high"].to_numpy(float)
    l = bars["low"].to_numpy(float)
    v = bars["volume"].to_numpy(float)
    date = np.asarray(bars["date"], dtype="datetime64[ns]")
    sessions = np.unique(date)
    sidx = np.searchsorted(sessions, date)

    def prev(x):
        out = np.full(n, np.nan)
        out[1:] = x[:-1]
        out[pos == 0] = np.nan
        return out

    c_prev, cu_prev = prev(c), prev(cu)
    with np.errstate(divide="ignore", invalid="ignore"):
        lr = np.log(c / c_prev)
        f = cu / c
    ok = np.isfinite(lr)
    lr0 = np.where(ok, lr, 0.0)
    dv = np.nan_to_num(c * v)
    adv = np.where(pos >= 20, _roll_prior(dv, 20) / 20.0, np.nan)
    cnt = _roll_prior(ok.astype(float), 20)
    s1, s2 = _roll_prior(lr0, 20), _roll_prior(lr0 ** 2, 20)
    with np.errstate(divide="ignore", invalid="ignore"):
        var = (s2 - s1 ** 2 / cnt) / (cnt - 1)
    vol20 = np.where((pos >= 20) & (cnt >= 19), np.sqrt(np.maximum(var, 0)) * np.sqrt(252), np.nan)
    nxt_same = np.r_[(code[1:] == code[:-1]) & (sidx[1:] == sidx[:-1] + 1), False]
    o_next = np.full(n, np.nan)
    c_next = np.full(n, np.nan)
    o_next[:-1] = o[1:]
    c_next[:-1] = c[1:]
    o_next[~nxt_same] = np.nan
    c_next[~nxt_same] = np.nan
    return dict(n=n, code=code, tickers=bars["ticker"].astype(str).to_numpy(), pos=pos, start=start,
                c=c, cu=cu, o=o, h=h, l=l, v=v, f=f, date=date, sessions=sessions, sidx=sidx,
                c_prev=c_prev, cu_prev=cu_prev, lr=lr, adv=adv, vol20=vol20, has_next=nxt_same,
                o_next=o_next, c_next=c_next)


def load() -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    bars = pd.read_parquet(STORE / "stocks.parquet",
                           columns=["ticker", "date", "open", "high", "low", "close", "volume",
                                    "closeunadj"],
                           filters=[("date", ">=", LO - pd.Timedelta(days=90)),
                                    ("date", "<=", HI)])
    bars = bars.sort_values(["ticker", "date"], kind="stable").reset_index(drop=True)
    tk = pd.read_parquet(STORE / "tickers.parquet",
                         columns=["table", "ticker", "category", "isdelisted", "lastpricedate"])
    m = tk[tk["table"] == "SEP"].copy()
    cu_ = m["category"].astype(str).str.upper()
    common = cu_.str.contains("COMMON STOCK") & ~cu_.str.contains("WARRANT|PREFERRED|UNIT")
    m = m[common].drop_duplicates("ticker", keep="first").set_index("ticker")
    bars = bars[bars["ticker"].isin(m.index)].reset_index(drop=True)
    mt = m[["isdelisted", "lastpricedate"]]
    act = pd.read_parquet(STORE / "actions.parquet")
    return build_panel(bars), mt, act


def resolve_term(pn, mt, dprice, row, price) -> tuple[float, str]:
    tk = str(pn["tickers"][row])
    lastbar = mt.at[tk, "lastpricedate"] if tk in mt.index else pd.NaT
    gone = tk in mt.index and str(mt.at[tk, "isdelisted"]).upper().startswith("Y")
    ended = bool(gone) and pd.Timestamp(lastbar) <= pd.Timestamp(pn["date"][row])
    px = dprice.get(tk, (None, None))[1] if ended else None
    if ended and px is not None and 0 < px / price[row] <= 5:
        return px / price[row] - 1.0, "delist_price"
    if ended:
        return -1.0, "delist_nopx"
    return -1.0, "nobar_halt"


def trade(pn: dict, mt: pd.DataFrame, act: pd.DataFrame, evlo: pd.Timestamp,
          evhi: pd.Timestamp, *, lag: int = 0, ibs_high: bool = False, dd_max: float | None = None,
          permute_ibs: bool = False, random_names: bool = False, rng: np.random.Generator) -> pd.DataFrame:
    price, date = pn["cu"], pn["date"]
    el = (pn["pos"] >= 20) & (pn["cu_prev"] >= PRICE_MIN) & (pn["adv"] >= ADV_MIN)
    inwin = (date >= np.datetime64(evlo)) & (date <= np.datetime64(evhi))
    with np.errstate(invalid="ignore"):
        daygap = pn["c"] / pn["c_prev"] - 1.0
    if dd_max is not None:
        cand = np.flatnonzero(el & inwin & np.isfinite(pn["c_prev"]) & (daygap >= dd_max))
    else:
        cand = np.flatnonzero(el & inwin & np.isfinite(pn["c_prev"]) & (daygap <= DAY_RET_MAX))

    dlu = act.copy()
    dlu["val"] = pd.to_numeric(dlu["value"], errors="coerce")
    dp = dlu[dlu["action"].isin(DELIST_ACTIONS) & (dlu["val"] > 0)].astype({"date": "datetime64[ns]"})
    dp = dp.sort_values(["ticker", "date"]).drop_duplicates("ticker", keep="last")
    dprice = {r.ticker: (r.date, float(r.val)) for r in dp.itertuples()}
    da = dlu[dlu["action"] == "dividend"].astype({"date": "datetime64[ns]"})
    divs = {(r.ticker, np.datetime64(r.date, "ns")): float(r.val)
            for r in da.dropna(subset=["ticker", "date", "val"]).itertuples()}

    by_date: dict = {}
    for i in cand:
        by_date.setdefault(pn["date"][i], []).append(int(i))

    def add_trade(i_row: int, tk: str, ev_date, adv: float):
        """Append the overnight trade entered at close of bar i_row (or its termination)."""
        if not pn["has_next"][i_row]:
            ret, kind = resolve_term(pn, mt, dprice, i_row, price)
            rows.append(dict(date=pd.Timestamp(ev_date), ticker=tk, ret=float(ret), kind=kind,
                             cu=float(price[i_row]), adv=float(adv)))
            return
        e = i_row
        if lag > 0:
            target = pn["sidx"][e] + lag
            if target >= len(pn["sessions"]):
                return
            eq = np.flatnonzero((pn["sidx"] == target) & (pn["tickers"] == tk))
            if len(eq) == 0:
                return
            e = int(eq[0])
            if not pn["has_next"][e]:
                ret, kind = resolve_term(pn, mt, dprice, e, price)
                rows.append(dict(date=pd.Timestamp(pn["date"][e]), ticker=tk, ret=float(ret),
                                 kind=kind, cu=float(price[e]), adv=float(adv)))
                return
        ret = pn["o_next"][e] / pn["c"][e] - 1.0
        kind = "open"
        nxt_date = pd.Timestamp(pn["sessions"][pn["sidx"][e] + 1])
        d_ = divs.get((tk, np.datetime64(nxt_date, "ns")))
        if d_ and 0 < d_ / price[e] < 0.25:
            ret += d_ / price[e]
        if not np.isfinite(ret):
            ret, kind = resolve_term(pn, mt, dprice, e, price)
        rows.append(dict(date=pd.Timestamp(ev_date), ticker=tk, ret=float(ret), kind=kind,
                         cu=float(price[e]), adv=float(adv)))

    rows: list[dict] = []
    ndays = len(by_date)
    for dkn, dd in enumerate(sorted(by_date)):
        idx = sorted(by_date[dd])
        df = pd.DataFrame({"price": price[idx],
                           "prev_close": pn["c_prev"][idx] * pn["f"][idx],
                           "high": pn["h"][idx] * pn["f"][idx],
                           "low": pn["l"][idx] * pn["f"][idx],
                           "vol20": pn["vol20"][idx], "adv": pn["adv"][idx], "row": idx},
                          index=pn["tickers"].astype(str)[idx], copy=False)
        if dd_max is not None:  # momentum mirror, same shape as the night leg
            df["day_ret"] = df["price"] / df["prev_close"] - 1.0
            r_ = (df["price"] - df["low"]).to_numpy(float)
            h_ = (df["high"] - df["low"]).to_numpy(float)
            with np.errstate(invalid="ignore"):
                df["ibs"] = np.where(h_ > 0, r_ / h_, np.nan)
            picks = df[(df["day_ret"] >= dd_max) & (df["ibs"] < IBS_MAX)].sort_values("day_ret",
                                                                                     ascending=False)
        elif permute_ibs:
            df["day_ret"] = df["price"] / df["prev_close"] - 1.0
            pr = (df["price"] - df["low"]).to_numpy(float)
            ph = (df["high"] - df["low"]).to_numpy(float)
            with np.errstate(invalid="ignore"):
                ibs_ = np.where(ph > 0, pr / ph, np.nan)
            df["ibs"] = rng.permutation(np.nan_to_num(ibs_, nan=0.0))
            picks = df[(df["day_ret"] <= DAY_RET_MAX) & (df["ibs"] < IBS_MAX)].sort_values("day_ret")
        else:
            picks = loser_picks(df, day_ret_max=DAY_RET_MAX, ibs_max=1.5 if ibs_high else IBS_MAX,
                                price_min=PRICE_MIN, price_max=PRICE_MAX)
            if ibs_high:
                picks = picks[picks["ibs"] >= 0.90]
            picks = picks.sort_values("day_ret")
        if picks.empty:
            continue
        if dkn % 200 == 0:
            print(f"  {pd.Timestamp(dd).date()} day/{ndays} rows {len(rows)}", flush=True)
        tgt = picks[~picks.index.duplicated(keep="first")].copy()
        rows_i = tgt["row"].astype(int).to_numpy()
        j0s = np.maximum(rows_i - 20, pn["start"][rows_i] + 1)
        R = np.zeros((len(rows_i), 20))
        for k_, (j0, i) in enumerate(zip(j0s, rows_i)):
            sl = np.asarray(pn["lr"][j0:i], dtype=float)
            R[k_, -len(sl):] = np.nan_to_num(sl, nan=0.0)[-20:]
        Z = R - R.mean(1, keepdims=True)
        sd = np.sqrt((Z ** 2).sum(1))
        ok20 = sd > 1e-12
        Z = Z / np.where(ok20, sd, 1.0)[:, None]
        keep_pos: list[int] = []
        kept_of = []
        for q in range(len(rows_i)):
            dup = False
            if ok20[q] and keep_pos:
                C = Z[keep_pos] @ Z[q]
                if C.max(initial=-2.0) > MAX_CORR:
                    dup = True
            if not dup:
                keep_pos.append(q)
                kept_of.append(q)
        tgt = tgt.iloc[kept_of]
        tgt = tgt.copy()
        tgt["ticker"] = tgt.index.astype(str)
        tgt = tgt.reset_index(drop=True)
        kept, _frac = night_sizing(tgt, vol_min=VOL_MIN, crowd_n=CROWD_N, max_name_pct=NAME_CAP)
        if kept.empty:
            continue
        candf = kept.reset_index(drop=True)
        if random_names:
            # count-matched: same days, same counts, random eligible names instead of picks
            allpos = np.flatnonzero(el & (pn["date"] == dd) & np.isfinite(pn["c_prev"]))
            used = set(candf["ticker"].astype(str))
            pool = [int(j) for j in allpos if str(pn["tickers"][j]) not in used]
            if not pool:
                continue
            for k2, j2 in enumerate(rng.permutation(pool)[: max(len(candf), 1)]):
                tk = str(pn["tickers"][j2])
                add_trade(j2, tk, dd, float(pn["adv"][j2]))
            continue
        for r_ in candf.itertuples():
            add_trade(int(r_.row), str(r_.ticker), dd, float(r_.adv))
    return pd.DataFrame(rows)


def stats(tr: pd.DataFrame) -> dict:
    if len(tr) < 3:
        nan = float("nan")
        return dict(n_nights=0, n_trades=len(tr), mean=nan, median=nan, t_cl=nan,
                    halves=(nan, nan), ex5=nan)
    net = tr["ret"].to_numpy(float) - 2 * book.cost_bps(COST, tr["cu"].to_numpy(float),
                                                       tr["adv"].to_numpy(float)) / 1e4
    dd = pd.DataFrame({"date": tr["date"].values, "net": net})
    by = dd.groupby(pd.to_datetime(dd["date"].values))["net"].mean().sort_index()
    x, g = by.to_numpy(), by.index.values
    m = x.mean()
    xd = x - m
    s = pd.Series(xd).groupby(g).sum().to_numpy()
    var_cl = (s ** 2).sum() / (len(x) - 1) / len(x)
    t_cl = m / np.sqrt(max(var_cl, 1e-16))
    mid = by.index[len(by) // 2]
    h1, h2 = by[by.index < mid], by[by.index >= mid]
    order = np.argsort(-net)
    ex5 = float(np.delete(net, order[: min(5, len(net))]).mean())
    return dict(n_nights=len(x), n_trades=len(net), mean=float(m), median=float(np.median(net)),
                t_cl=float(t_cl), halves=(float(h1.mean()), float(h2.mean())), ex5=float(ex5))


def main() -> int:
    pn, mt, act = load()
    print(f"panel rows {pn['n']}, sessions {len(pn['sessions'])}, "
          f"{pn['sessions'][0]}..{pn['sessions'][-1]}", flush=True)
    rng = np.random.default_rng(SEED)
    out = []
    for name, kw in [
        ("DDR lag+5payer", dict(lag=5)),
    ]:
        tr = trade(pn, mt, act, LO, HI, rng=rng, **kw)
        s = stats(tr)
        gate = bool(np.isfinite(s["t_cl"]) and s["t_cl"] >= 2.0 and s["halves"][0] > 0
                    and s["halves"][1] > 0 and s["median"] > 0 and s["ex5"] > 0)
        kinds = tr["kind"].value_counts().to_dict() if len(tr) else {}
        out.append(f"{name:22s} nights {s['n_nights']:5d} trades {s['n_trades']:6d} "
                   f"mean {s['mean']*1e4:8.2f}bp med {s['median']*1e4:8.2f}bp t {s['t_cl']:6.2f} "
                   f"halves {s['halves'][0]*1e4:7.1f} / {s['halves'][1]*1e4:7.1f} "
                   f"ex5 {s['ex5']*1e4:7.1f} | PASS={gate} | {kinds}")
        print(out[-1], flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(out) + "\n")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
