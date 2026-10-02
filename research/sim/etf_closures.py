"""Discovery DL6: closing ETFs bought in their last week. Registered in round1_prose.md (amendment "deal rule DL6")
before this ran. Liquidation proceeds = Alpaca `cash_mergers` records; ETF = Alpaca asset name contains "ETF"."""
from __future__ import annotations

import datetime as dt
import json
import pathlib

import pandas as pd

from research.sim.event_fetch import _cache, raw_bars


def _ca(types, y):
    from alpaca.data.historical.corporate_actions import CorporateActionsClient
    from alpaca.data.requests import CorporateActionsRequest
    from swingtrader.data import _clients
    d, _ = _clients()
    c = CorporateActionsClient(d._api_key, d._secret_key)
    r = c.get_corporate_actions(CorporateActionsRequest(types=types, start=dt.date(y, 1, 1), end=dt.date(y, 12, 31), limit=None))
    return r.data


def cash_mergers() -> pd.DataFrame:
    f = _cache("alpaca_cash_mergers.parquet")
    if f.exists():
        return pd.read_parquet(f)
    from alpaca.data.enums import CorporateActionsType
    rows = []
    for y in range(2016, 2027):
        for x in _ca([CorporateActionsType.CASH_MERGER], y).get("cash_mergers", []):
            x = x if isinstance(x, dict) else x.__dict__
            rows.append(dict(sym=x.get("acquiree_symbol") or x.get("symbol"), rate=float(x.get("rate") or 0),
                             eff=str(x.get("effective_date")), pay=str(x.get("payable_date"))))
    D = pd.DataFrame(rows).drop_duplicates()
    D.to_parquet(f)
    return D


def etf_names() -> dict[str, str]:
    f = _cache("alpaca_assets.json")
    if not f.exists():
        from alpaca.trading.enums import AssetStatus
        from alpaca.trading.requests import GetAssetsRequest
        from swingtrader.data import _clients
        _, t = _clients()
        out = {}
        for st in (AssetStatus.ACTIVE, AssetStatus.INACTIVE):
            for a in t.get_all_assets(GetAssetsRequest(status=st)):
                out[a.symbol] = a.name or ""
        json.dump(out, open(f, "w"))
    return json.load(open(f))


def dividends(sym: str) -> pd.DataFrame:
    f = _cache("divs", f"{sym}.parquet")
    if f.exists():
        return pd.read_parquet(f)
    from alpaca.data.historical.corporate_actions import CorporateActionsClient
    from alpaca.data.requests import CorporateActionsRequest
    from swingtrader.data import _clients
    d, _ = _clients()
    c = CorporateActionsClient(d._api_key, d._secret_key)
    r = c.get_corporate_actions(CorporateActionsRequest(symbols=[sym], start=dt.date(2015, 10, 1), end=dt.date(2026, 9, 30), limit=None))
    rows = [dict(ex=pd.Timestamp(x.ex_date if not isinstance(x, dict) else x["ex_date"]), rate=float(x.rate if not isinstance(x, dict) else x["rate"]))
            for x in r.data.get("cash_dividends", [])]
    D = pd.DataFrame(rows, columns=["ex", "rate"])
    D.to_parquet(f)
    return D


def run(k: int = 5, sizes=(2300, 10000, 25000)) -> pd.DataFrame:
    M = cash_mergers()
    names = etf_names()
    M = M[M.sym.map(lambda s: "ETF" in names.get(s, ""))]
    out = []
    for _, m in M.iterrows():
        b = raw_bars([m.sym])[m.sym]
        if len(b) < 30:
            continue
        b.index = pd.to_datetime(b.index)
        # symbol reuse guard (data validity, not selection): the symbol must stop trading at the liquidation
        if m.eff in ("None", "NaT") or abs((b.index[-1] - pd.Timestamp(m.eff)).days) > 10:
            continue
        i0 = len(b) - 1 - k
        entry, last = b.close.iloc[i0], b.close.iloc[-1]
        dv = dividends(m.sym)
        dsum = dv[(dv.ex > b.index[i0]) & (dv.ex <= b.index[-1])].rate.sum() if len(dv) else 0.0
        pay = m.rate + dsum
        pre = b.iloc[max(0, i0 - 20):i0]
        adv = float((pre.close * pre.volume).median())
        row = dict(sym=m.sym, name=names[m.sym][:40], last_day=b.index[-1].date(), entry=entry, last=last, rate=m.rate,
                   divs=dsum, ret=pay / entry - 1, ret_last=pay / last - 1, adv=adv,
                   bad=not (0.2 * entry <= m.rate <= 5 * entry))
        for s in sizes:
            row[f"usd{s}"] = int(min(0.10 * s, 0.05 * adv) // entry) * (pay - entry)
        out.append(row)
    return pd.DataFrame(out)


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    D = run()
    D.to_csv("data/research/events/etf_closure_deals.csv", index=False)
    X = D[~D.bad]
    print("records", len(D), "data errors", int(D.bad.sum()), "deals", len(X), "years", sorted(set(pd.to_datetime(X.last_day).dt.year)))
    print(f"entry 5 sessions before: mean {X.ret.mean():.2%} median {X.ret.median():.2%} hit {(X.ret > 0).mean():.0%} worst {X.ret.min():.2%} best {X.ret.max():.2%}")
    print(f"entry last close (info): mean {X.ret_last.mean():.2%} median {X.ret_last.median():.2%} hit {(X.ret_last > 0).mean():.0%}")
    yrs = max(1, (pd.to_datetime(X.last_day).max() - pd.to_datetime(X.last_day).min()).days / 365.25)
    for s in (2300, 10000, 25000):
        print(s, "$/yr", round(X[f"usd{s}"].sum() / yrs))
    print(X.groupby(pd.to_datetime(X.last_day).dt.year).ret.agg(["count", "mean", "median"]).round(4).to_string())
    print(X.sort_values("ret").head(8)[["sym", "name", "last_day", "entry", "rate", "ret"]].to_string())
    print(X.sort_values("ret").tail(8)[["sym", "name", "last_day", "entry", "rate", "ret"]].to_string())
