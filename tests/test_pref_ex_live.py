import datetime as dt
import json
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from swingtrader.daily import pref_ex_live as P

ET = ZoneInfo("America/New_York")
TODAY = dt.date(2026, 10, 14)                  # Wed; next session Thu 10-15
NOW = dt.datetime(2026, 10, 14, 15, 25, tzinfo=ET)


class Resp:
    def __init__(self, d):
        self.d = d

    def json(self):
        return self.d


class FakeClient:
    def __init__(self, quotes, orders=None):
        self.quotes, self.orders = quotes, orders or {}

    def get_quotes(self, syms):
        return Resp({s: {"quote": {"lastPrice": self.quotes[s]}} for s in syms if s in self.quotes})

    def get_order(self, oid, h):
        return Resp(self.orders[int(oid)])


class FakeAd:
    hash = "HASH"

    def __init__(self, quotes, settled=1000.0, equity=3000.0, positions=None, orders=None):
        self.c = FakeClient(quotes, orders)
        self.settled, self.equity, self.pos, self.submitted = settled, equity, positions or {}, []

    def account(self):
        return SimpleNamespace(equity=self.equity, cash=self.settled + 500.0, settled_cash=self.settled)

    def positions(self):
        return {s: SimpleNamespace(qty=q) for s, q in self.pos.items()}

    def submit(self, sym, side, tif, coid, qty=None, **kw):
        self.submitted.append((sym, side, tif, qty))
        return str(2000 + len(self.submitted))


def crosses(syms, start, end, H):
    # every session: close cross $ = 25 x 400 = $10k for BAC.PRP / GLADZ, $200 for TINY.PRA (5% < 1 share)
    days = [(dt.date(2026, 10, 1) + dt.timedelta(days=i)).isoformat() for i in range(14)]
    usd = {"BAC.PRP": (25.0, 400), "TINY.PRA": (25.0, 8), "GLADZ": (25.0, 400)}
    return {s: {d: (25.0, 100, usd[s][0], usd[s][1]) for d in days} for s in syms if s in usd}


def events(tmp_path, *rows):
    (tmp_path / "pref-ex.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def ev(sym, ex="2026-10-15", div=0.25, cls="pref"):
    return dict(sym=sym, ex=ex, div=div, cls=cls, status="upcoming")


def test_off_mode_is_a_no_op(tmp_path):
    out = P.run("off", tmp_path, tmp_path, log=lambda *_: None, today=TODAY, now=NOW, ad=None)
    assert out["skipped"] == "off" and not (tmp_path / P.LOG_NAME).exists()


def test_schwab_symbol_mapping():
    assert P.schwab_symbol("BAC.PRP") == "BAC/PRP" and P.schwab_symbol("GLADZ") == "GLADZ"


def test_candidates_are_tomorrows_pref_and_etd_ex_dates():
    rows = [ev("BAC.PRP"), ev("GLADZ", cls="etd"), ev("JRI", cls="cef"), ev("NEE.PRW", ex="2026-10-16"),
            dict(sym="OLD.PRA", ex="2026-10-15", div=0.3, cls="pref", status="scored")]
    assert sorted(c["sym"] for c in P.candidates(rows, TODAY)) == ["BAC.PRP", "GLADZ"]


def test_sizing_is_five_percent_of_the_cross_whole_shares_yield_first_capped_at_three():
    cands = [ev("A.PRA", div=0.20), ev("B.PRB", div=0.50), ev("C.PRC", div=0.40), ev("D.PRD", div=0.45), ev("TINY.PRA", div=0.9)]
    last = {c["sym"]: 25.0 for c in cands}
    auction = {"A.PRA": 10_000, "B.PRB": 10_000, "C.PRC": 10_000, "D.PRD": 10_000, "TINY.PRA": 400}  # 5% of 400 = $20 < 1 share
    out = P.size(cands, last, auction, settled=5000, equity=20000)
    assert [o["sym"] for o in out] == ["B.PRB", "D.PRD", "C.PRC"]      # yield order, 3 names, TINY skipped (0 shares)
    assert all(o["qty"] == 20 and o["usd"] == 500.0 and o["schwab"].endswith("/PR" + o["sym"][-1]) for o in out)


def test_budget_is_settled_cash_and_half_of_equity():
    cands = [ev("A.PRA", div=0.5), ev("B.PRB", div=0.4)]
    last = {"A.PRA": 25.0, "B.PRB": 25.0}
    auction = {"A.PRA": 10_000, "B.PRB": 10_000}
    out = P.size(cands, last, auction, settled=600, equity=20000)            # settled binds: 20 sh ($500) + 4 sh ($100)
    assert [(o["sym"], o["qty"]) for o in out] == [("A.PRA", 20), ("B.PRB", 4)]
    out = P.size(cands, last, auction, settled=5000, equity=1000)            # 50% of equity binds: $500 total
    assert [(o["sym"], o["qty"]) for o in out] == [("A.PRA", 20)]
    assert P.size(cands, last, auction, settled=0, equity=1000) == []


def test_dry_run_sizes_logs_and_reserves_but_places_nothing(tmp_path):
    events(tmp_path, ev("BAC.PRP"), ev("TINY.PRA", div=0.9), ev("GLADZ", cls="etd", div=0.39))
    ad = FakeAd({"BAC/PRP": 25.0, "TINY/PRA": 25.0, "GLADZ": 25.0}, settled=1000, equity=3000)
    out = P.run("dry", tmp_path, tmp_path, log=lambda *_: None, today=TODAY, now=NOW, ad=ad, crosses_fn=crosses, H={})
    assert ad.submitted == [] and sorted(out["bought"]) == ["BAC.PRP", "GLADZ"]
    rows = [json.loads(x) for x in (tmp_path / P.LOG_NAME).read_text().splitlines()]
    buys = [r for r in rows if r["cmd"] == "buy"]
    assert all(r["dry_run"] for r in buys) and {r["sym"] for r in buys} == {"BAC.PRP", "GLADZ"}
    assert any(r["cmd"] == "buy-skip" and r["sym"] == "TINY.PRA" for r in rows)
    res = json.loads((tmp_path / P.RESERVED_NAME).read_text())
    assert res["date"] == TODAY.isoformat() and abs(res["usd"] - sum(r["usd"] for r in buys)) < 1e-6
    st = json.loads((tmp_path / P.STATE_NAME).read_text())
    assert set(st["open"]) == {"BAC.PRP", "GLADZ"} and st["open"]["BAC.PRP"]["schwab"] == "BAC/PRP"


def test_live_submits_moc_buys_with_schwab_symbols(tmp_path):
    events(tmp_path, ev("BAC.PRP"))
    ad = FakeAd({"BAC/PRP": 25.0}, settled=1000, equity=3000)
    out = P.run("live", tmp_path, tmp_path, log=lambda *_: None, today=TODAY, now=NOW, ad=ad, crosses_fn=crosses, H={})
    assert ad.submitted == [("BAC/PRP", "buy", "cls", 20)] and out["bought"] == ["BAC.PRP"]
    rows = [json.loads(x) for x in (tmp_path / P.LOG_NAME).read_text().splitlines()]
    assert [r for r in rows if r["cmd"] == "buy"][0]["order_id"] == "2001"


def test_sell_leg_on_the_ex_date_never_exceeds_what_is_held(tmp_path):
    (tmp_path / P.STATE_NAME).write_text(json.dumps({"open": {
        "BAC.PRP": dict(schwab="BAC/PRP", qty=20, ex="2026-10-14", bought="2026-10-13", px=25.0),
        "GONE.PRA": dict(schwab="GONE/PRA", qty=5, ex="2026-10-14", bought="2026-10-13", px=25.0),
        "LATER.PRB": dict(schwab="LATER/PRB", qty=5, ex="2026-10-15", bought="2026-10-13", px=25.0)}}))
    ad = FakeAd({}, positions={"BAC/PRP": 12.0})      # account holds fewer than bought: sell 12, never 20; GONE not held
    out = P.run("live", tmp_path, tmp_path, log=lambda *_: None, today=TODAY, now=NOW, ad=ad, crosses_fn=crosses, H={})
    assert ad.submitted == [("BAC/PRP", "sell", "cls", 12)] and out["sold"] == ["BAC.PRP"]
    st = json.loads((tmp_path / P.STATE_NAME).read_text())
    assert set(st["open"]) == {"LATER.PRB"}
    rows = [json.loads(x) for x in (tmp_path / P.LOG_NAME).read_text().splitlines()]
    assert any(r["cmd"] == "sell-skip" and r["sym"] == "GONE.PRA" for r in rows)


def test_no_orders_after_the_cutoff_or_on_a_non_session(tmp_path):
    events(tmp_path, ev("BAC.PRP"))
    ad = FakeAd({"BAC/PRP": 25.0})
    late = dt.datetime(2026, 10, 14, 15, 44, tzinfo=ET)
    P.run("live", tmp_path, tmp_path, log=lambda *_: None, today=TODAY, now=late, ad=ad, crosses_fn=crosses, H={})
    sat = dt.date(2026, 10, 10)
    P.run("live", tmp_path, tmp_path, log=lambda *_: None, today=sat, now=NOW.replace(day=10), ad=ad, crosses_fn=crosses, H={})
    assert ad.submitted == []


def test_score_compares_yesterdays_fills_to_the_closing_cross(tmp_path):
    (tmp_path / P.LOG_NAME).write_text(json.dumps(dict(ts="2026-10-13T15:30:00-04:00", mode="live", cmd="buy", sym="BAC.PRP",
                                                       schwab="BAC/PRP", qty=20, order_id="2001")) + "\n")
    order = {"orderActivityCollection": [{"executionLegs": [{"price": 25.05, "quantity": 20, "time": "2026-10-13T20:00:01Z"}]}]}
    ad = FakeAd({}, orders={2001: order})
    out = P.run("live", tmp_path, tmp_path, log=lambda *_: None, today=TODAY, now=NOW, ad=ad, crosses_fn=crosses, H={})
    rows = [json.loads(x) for x in (tmp_path / P.LOG_NAME).read_text().splitlines()]
    sc = [r for r in rows if r["cmd"] == "score"]
    assert out["scored"] == 1 and len(sc) == 1 and sc[0]["diff_bp"] == 20.0 and sc[0]["close_cross"] == 25.0
    # a second run does not re-score
    P.run("live", tmp_path, tmp_path, log=lambda *_: None, today=TODAY, now=NOW, ad=ad, crosses_fn=crosses, H={})
    assert sum(1 for x in (tmp_path / P.LOG_NAME).read_text().splitlines() if json.loads(x)["cmd"] == "score") == 1
    assert "1/30" not in P.line(rows) and "buy +20.0bp" in P.line(rows)
    assert sc[0]["share"] == 0.05                                         # 20 of the 400-share cross


def _trips(n, buy_bp, sell_bp):
    rows = [dict(cmd="score", side="buy", diff_bp=buy_bp) for _ in range(n)]
    return rows + [dict(cmd="score", side="sell", diff_bp=-sell_bp) for _ in range(n)]


def test_participation_steps_to_ten_percent_only_after_the_cost_gate():
    assert P.part([]) == P.PART == 0.05
    assert P.part(_trips(29, 0.0, 0.0)) == 0.05                           # gate needs 30 round trips
    assert P.part(_trips(30, 4.0, 5.0)) == 0.10                           # 9bp round trip <= 10bp
    assert P.part(_trips(30, 6.0, 5.0)) == 0.05                           # 11bp: stays (and steps back) at 5%
    assert "participation 10%" in P.line(_trips(30, 0.0, 0.0))
    cands, last, auction = [ev("BAC.PRP")], {"BAC.PRP": 25.0}, {"BAC.PRP": 10_000.0}
    assert P.size(cands, last, auction, settled=5000, equity=20000)[0]["qty"] == 20
    assert P.size(cands, last, auction, settled=5000, equity=20000, part=P.part(_trips(30, 0.0, 0.0)))[0]["qty"] == 40


def test_executor_roth_night_cash_honours_todays_reservation(tmp_path):
    from swingtrader.config import Config
    from swingtrader.daily import executor as E
    from test_daily import FakeBroker   # tests/ is on sys.path under pytest's default import mode
    ex = E.DailyExecutor(Config.load(), account="roth", broker=FakeBroker(), state_dir=tmp_path, log_dir=tmp_path)
    assert ex._pref_ex_reserved("2026-10-14") == 0.0
    (tmp_path / "pref-ex-reserved.json").write_text(json.dumps({"date": "2026-10-14", "usd": 512.5}))
    assert ex._pref_ex_reserved("2026-10-14") == 512.5
    assert ex._pref_ex_reserved("2026-10-15") == 0.0                      # stale file: ignored
    ex.cash_account = False
    assert ex._pref_ex_reserved("2026-10-14") == 0.0                      # taxable book: never
