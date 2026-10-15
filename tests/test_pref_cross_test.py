import datetime as dt
import json

from research.sim import pref_cross_test as P


def test_candidates_formats():
    c = P.candidates("PSEC.PRA")
    assert c[0] == "PSEC/PRA" and "PSEC-A" in c and "PSEC.PRA" in c
    assert P.candidates("JRI") == ["JRI"]


def test_pick_next_weekday(tmp_path, monkeypatch):
    f = tmp_path / "pref-ex.jsonl"
    f.write_text("\n".join(json.dumps(r) for r in [
        {"sym": "A.PRA", "ex": "2026-10-09"}, {"sym": "B.PRB", "ex": "2026-10-12"}, {"sym": "C.PRC", "ex": "2026-10-13"}]))
    monkeypatch.setattr(P, "SHADOW", f)
    assert [r["sym"] for r in P.pick(dt.date(2026, 10, 8))] == ["A.PRA"]      # Thu -> Fri
    assert [r["sym"] for r in P.pick(dt.date(2026, 10, 9))] == ["B.PRB"]      # Fri -> Mon


def test_buy_is_dry_run_without_go(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "LOG", tmp_path / "log.jsonl")

    class Ad:
        def submit(self, *a, **k):
            raise AssertionError("must not place an order without --go")

    import swingtrader.daily.brokers as B
    monkeypatch.setattr(B, "make_adapter", lambda acct: Ad())

    class FakeDT(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return dt.datetime(2026, 10, 8, 14, 0, tzinfo=tz)
    monkeypatch.setattr(P.dt, "datetime", FakeDT)
    assert P.main(["buy", "PSEC.PRA", "--schwab", "PSEC/PRA"]) == 0
    row = json.loads((tmp_path / "log.jsonl").read_text().splitlines()[-1])
    assert row["dry_run"] is True and row["schwab"] == "PSEC/PRA" and row["qty"] == 1
