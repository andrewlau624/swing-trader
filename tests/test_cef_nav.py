import datetime as dt
import json

from swingtrader.daily import cef_nav as N
from swingtrader.daily import cef_rv_shadow as W

TODAY = dt.date(2026, 10, 19)


def _rows(series: dict[str, float]):
    return {"tradesTable": {"rows": [{"date": dt.date.fromisoformat(d).strftime("%m/%d/%Y"), "close": c} for d, c in series.items()]}}


def _fake_get(nav: dict, px: dict, names: dict | None = None, lookup: dict | None = None):
    """Nasdaq API stand-in: nav = navsym -> {date: nav}, px = sym -> {date: close}."""
    calls = []

    def get(path, params=None):
        calls.append((path, params))
        parts = path.split("/")
        if parts[0] == "quote" and parts[2] == "info":
            sym, ac = parts[1], params["assetclass"]
            if ac == "mutualfunds":
                return {"symbol": sym} if sym in nav else None
            return {"companyName": (names or {}).get(sym)} if sym in (names or {}) else None
        if parts[0] == "quote" and parts[2] == "historical":
            src = nav if params["assetclass"] == "mutualfunds" else px
            s = {d: c for d, c in src.get(parts[1], {}).items() if d >= params["fromdate"]}
            return _rows(s) if s else None
        if parts[0] == "autocomplete":
            return (lookup or {}).get(params["search"])
        raise AssertionError(path)

    get.calls = calls
    return get


def test_fridays_match_cefconnect_shape_and_skip_holiday_fridays():
    nav = {"2026-10-15": 5.56, "2026-10-16": 5.55, "2026-10-19": 5.52, "2026-04-02": 5.0, "2026-04-03": 5.0}
    px = {"2026-10-15": "$5.20", "2026-10-16": "$5.15", "2026-10-19": "$5.16", "2026-04-02": "4.6"}
    rows = N.fridays(nav, {d: N._num(v) for d, v in px.items()})
    # 2026-04-03 is Good Friday: NAV posted, no price -> no row; 10-16 matches the CEFConnect row (-7.21%, NAV 5.55)
    assert [r[0] for r in rows] == ["2026-10-16"]
    assert abs(rows[0][1] - (5.15 / 5.55 - 1)) < 1e-12 and rows[0][2] == 5.55


def test_hist_parses_nasdaq_rows_and_drops_na():
    get = _fake_get({"XGABX": {"2026-10-16": "5.55", "2026-10-15": "N/A"}}, {})
    assert N.hist("XGABX", "mutualfunds", "2026-10-01", get) == {"2026-10-16": 5.55}
    assert N.hist("XNOPE", "mutualfunds", "2026-10-01", get) == {}


def test_nav_candidates_and_resolve_pick_the_symbol_whose_history_matches():
    get = _fake_get({"XGABX": {"2026-10-09": 5.5, "2026-10-16": 5.55}}, {},
                    names={"ADX": "Adams Diversified Equity Fund Common Stock", "ASA": "ASA  Gold and Precious Metals Limited"},
                    lookup={"Adams Diversified Equity Fund": [{"symbol": "ADX", "asset": "STOCKS", "name": "Adams Diversified Equity Fund"},
                                                              {"symbol": "XADEX", "asset": "MUTUALFUNDS", "name": "Adams Diversified Equity Fund"}]})
    assert N.nav_candidates("GAB", get) == ["XGABX"] and N.nav_symbol("GAB", get) == "XGABX"
    assert N.nav_symbol("ADX", get) == "XADEX"
    assert N.nav_symbol("ASA", get) is None and N.nav_symbol("ZZZ", get) is None
    # stored rows agree with XGABX -> accepted; a stored history that disagrees rejects even the only candidate
    assert N.resolve("GAB", [["2026-10-09", -0.05, 5.5]], get)["nav"] == "XGABX"
    assert N.resolve("GAB", [["2026-10-09", -0.05, 9.9]], get)["nav"] is None
    assert N.resolve("GAB", [], get)["nav"] == "XGABX"                       # no overlap, unambiguous -> accepted
    # a term trust and its sibling share the truncated autocomplete name: the stored history picks the right one
    get2 = _fake_get({"XBMEX": {"2026-10-16": 45.7}, "XHSTX": {"2026-10-16": 18.2}}, {},
                     names={"BMEZ": "BlackRock Health Sciences Term Trust Common Shares"},
                     lookup={"BlackRock Health Sciences Term": [{"symbol": "XBMEX", "asset": "MUTUALFUNDS", "name": "BlackRock Health Sciences T"},
                                                                {"symbol": "XHSTX", "asset": "MUTUALFUNDS", "name": "BlackRock Health Sciences T"}]})
    assert N.nav_symbol("BMEZ", get2) is None
    assert N.resolve("BMEZ", [["2026-10-16", -0.1, 18.22]], get2) == {"nav": "XHSTX", "tried": ["XBMEX", "XHSTX"]}
    assert N.resolve("BMEZ", [], get2)["nav"] is None                       # ambiguous with nothing to check against


def test_navmap_caches_and_rechecks_unmapped_monthly(tmp_path):
    get = _fake_get({"XGABX": {}}, {}, names={})
    m = N.navmap(tmp_path, ["GAB", "ASA"], TODAY, log=lambda *_: None, get=get, threads=1)
    assert m["GAB"]["nav"] == "XGABX" and m["ASA"]["nav"] is None
    n0 = len(get.calls)
    m2 = N.navmap(tmp_path, ["GAB", "ASA"], TODAY, log=lambda *_: None, get=get, threads=1)
    assert m2 == m and len(get.calls) == n0                          # nothing re-looked-up the same day
    N.navmap(tmp_path, ["GAB", "ASA"], TODAY + dt.timedelta(days=31), log=lambda *_: None, get=get, threads=1)
    assert len(get.calls) > n0                                       # the unmapped fund is retried after RECHECK_DAYS
    assert json.loads((tmp_path / N.MAP_NAME).read_text())["GAB"]["nav"] == "XGABX"


def test_refresh_extends_each_fund_from_its_own_last_week_and_flags_drift(tmp_path):
    pan = {"GAB": [["2026-10-02", -0.05, 5.4], ["2026-10-09", -0.0527, 5.5]],
           "OLD": [["2026-07-31", -0.1, 10.0]],
           "ASA": [["2026-10-09", -0.02, 20.0]]}
    nav = {"XGABX": {"2026-10-09": 5.5, "2026-10-15": 5.56, "2026-10-16": 5.55},
           "XOLDX": {"2026-07-31": 10.3, "2026-08-07": 10.1, "2026-10-16": 10.2}}
    px = {"GAB": {"2026-10-09": 5.21, "2026-10-15": 5.20, "2026-10-16": 5.15},
          "OLD": {"2026-07-31": 9.0, "2026-08-07": 9.1, "2026-10-16": 9.3}}
    logs = []
    get = _fake_get(nav, px, names={"ASA": "ASA Gold"})
    new = N.refresh(pan, tmp_path, TODAY, log=logs.append, keep=3, get=get, threads=1)
    assert [r[0] for r in new["GAB"]] == ["2026-10-02", "2026-10-09", "2026-10-16"]            # appended, keep=3 trims nothing yet
    assert abs(new["GAB"][-1][1] - (5.15 / 5.55 - 1)) < 1e-12 and new["GAB"][-1][2] == 5.55
    assert new["OLD"] == pan["OLD"]                                   # NAV 10.3 vs stored 10.0 on 07-31: XOLDX tracks another fund
    assert new["ASA"] == pan["ASA"]                                                           # unmapped: untouched
    assert pan["GAB"][-1][0] == "2026-10-09"                                                  # input not mutated
    assert "1/1 mapped funds extended" in logs[-1] and "2 unmapped" in logs[-1]
    m = json.loads((tmp_path / N.MAP_NAME).read_text())
    assert m["OLD"] == {"nav": None, "tried": ["XOLDX"], "checked": "2026-10-19"} and m["GAB"]["nav"] == "XGABX"
    # a cached (pre-verification) map entry that disagrees with the stored rows is rejected at refresh time
    m["OLD"]["nav"] = "XOLDX"
    (tmp_path / N.MAP_NAME).write_text(json.dumps(m))
    new2 = N.refresh(pan, tmp_path, TODAY, log=logs.append, keep=3, get=get, threads=1)
    assert new2["OLD"] == pan["OLD"] and "REJECTED" in logs[-1] and "OLD" in logs[-1]
    m = json.loads((tmp_path / N.MAP_NAME).read_text())
    assert m["OLD"]["nav"] is None and m["OLD"]["mismap"] == "XOLDX"
    # the fetch starts OVERLAP_DAYS before each fund's stored last week (rows to check the NAV symbol against), not a global date
    since = {p.split("/")[1]: q["fromdate"] for p, q in get.calls if "historical" in p}
    assert since["GAB"] == "2026-09-18" and since["OLD"] == "2026-07-10"
    # a rejected symbol is not retried the same month
    n0 = len(get.calls)
    N.refresh(new, tmp_path, TODAY, log=logs.append, keep=3, get=get, threads=1)
    assert not any("XOLDX" in p for p, _ in get.calls[n0:])


def test_panel_falls_back_to_nasdaq_when_cefconnect_is_blocked(tmp_path, monkeypatch):
    pan = {"GAB": [["2026-10-02", -0.05, 5.4], ["2026-10-09", -0.0527, 5.5]]}
    (tmp_path / W.PANEL_NAME).write_text(json.dumps(pan))
    monkeypatch.setattr(W, "_cefc", lambda path: None)
    get = _fake_get({"XGABX": {"2026-10-09": 5.5, "2026-10-16": 5.55}}, {"GAB": {"2026-10-09": 5.21, "2026-10-16": 5.15}})
    monkeypatch.setattr(N, "_get", get)
    logs = []
    out = W.panel(tmp_path, TODAY, log=logs.append)
    assert out["GAB"][-1][0] == "2026-10-16" and json.loads((tmp_path / W.PANEL_NAME).read_text()) == out
    assert any("panel extended from Nasdaq" in x for x in logs)
    # already fresh -> no fetch at all
    n0 = len(get.calls)
    assert W.panel(tmp_path, TODAY, log=logs.append) == out and len(get.calls) == n0
