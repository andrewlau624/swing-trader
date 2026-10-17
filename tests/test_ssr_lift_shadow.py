import pandas as pd

from swingtrader.daily import ssr_lift_shadow as W


def _rth(table):
    def f(syms, day):
        d = table.get(str(pd.Timestamp(day).date()), {})
        return pd.DataFrame({s: d[s] for s in syms if s in d}).T if any(s in d for s in syms) else pd.DataFrame(
            columns=["low", "close"])
    return f


def test_confirm_uses_regular_hours_low_and_price_floor():
    t = {"2026-10-14": {"AAA": dict(low=0, close=20.0), "BBB": dict(low=0, close=20.0), "CCC": dict(low=0, close=8.0)},
         "2026-10-15": {"AAA": dict(low=17.9, close=18), "BBB": dict(low=18.5, close=19), "CCC": dict(low=5.0, close=5.5)}}
    got = W.confirm("2026-10-15", "2026-10-14", ["AAA", "BBB", "CCC"], _rth(t))
    assert [g["sym"] for g in got] == ["AAA"]            # BBB only -7.5%, CCC under $10


def _x(o2, c2, so, sc):
    return {"AAA": {"2026-10-15": (None, None, 18.0, 1), "2026-10-16": (17, 1, 17, 1), "2026-10-19": (o2, 100, c2, 1)},
            "SPY": {"2026-10-19": (so, 1, sc, 1)}}


def test_score_short_hedged_net():
    r = dict(T="2026-10-15", sym="AAA", status="pending")
    s = W.score(r, _x(10.0, 9.0, 100.0, 101.0))
    assert s["d2"] == "2026-10-19" and abs(s["raw"] - 0.10) < 1e-9
    assert abs(s["hedged"] - (0.10 + 1.5 * 0.01)) < 1e-9
    assert abs(s["net"] - (s["hedged"] - 0.0012)) < 1e-9
    assert W.score(dict(r, sym="ZZZ"), _x(10, 9, 100, 101)) is None


def test_retrigger_dropped_and_summary_excludes_backfill():
    r = dict(T="2026-10-15", sym="AAA", status="pending")
    low = lambda syms, day: pd.DataFrame({"low": [15.0]}, index=["AAA"])  # noqa: E731  15/18-1 = -16.7%
    assert W.score(r, _x(10, 9, 100, 101), low)["status"] == "retrigger"
    rows = [dict(status="scored", d2=f"2026-10-{19 + i}", net=0.01, hedged=0.012, raw=0.01, etb=True, backfill=False) for i in range(4)]
    rows += [dict(status="scored", d2="2026-10-01", net=-0.5, hedged=-0.5, raw=-0.5, backfill=True)]
    s = W.summary(rows)
    assert s["days"] == 4 and s["events"] == 4 and s["net_bp"] == 100.0 and W.summary(rows, True)["days"] == 1
