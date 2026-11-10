from swingtrader.daily import quote_guard as qg

NOW = 1_800_000_000.0


def q(**kw):
    base = dict(lastPrice=25.0, bidPrice=24.95, askPrice=25.05, closePrice=25.0, quoteTime=(NOW - 10) * 1000,
                securityStatus="Normal")
    base.update(kw)
    return base


def test_in_session_accepts_a_fresh_two_sided_quote():
    px, d = qg.check(q(), NOW, in_session=True)
    assert px == 25.0 and "reason" not in d and d["mid"] == 25.0


def test_in_session_refuses_stale_halted_one_sided_wide_quotes():
    for bad, why in ((q(quoteTime=(NOW - 900) * 1000), "old"), (q(securityStatus="Halted"), "status"),
                     (q(bidPrice=0), "one-sided"), (q(bidPrice=25.2), "crossed"),
                     (q(bidPrice=20.0, askPrice=25.0), "spread"), (q(quoteTime=None), "no quote time")):
        px, d = qg.check(bad, NOW, in_session=True)
        assert px is None and why in d["reason"], (bad, d)


def test_in_session_uses_mid_when_the_last_trade_is_stale():
    px, _ = qg.check(q(lastPrice=23.0), NOW, in_session=True)       # hours-old print far below the live quote
    assert px == 25.0


def test_pre_open_allows_prior_session_quote_but_not_a_jump_or_week_old_data():
    px, _ = qg.check(q(quoteTime=(NOW - 64 * 3600) * 1000), NOW, in_session=False)   # Friday quote, Monday 09:05
    assert px == 25.0
    assert qg.check(q(lastPrice=30.0), NOW, in_session=False)[0] is None
    assert qg.check(q(quoteTime=(NOW - 6 * 86400) * 1000), NOW, in_session=False)[0] is None


def test_fetch_reports_refusals():
    class C:
        def get_quotes(self, syms):
            class R:
                def json(_):
                    return {"A": {"quote": q()}, "B": {"quote": q(securityStatus="Halted")}}
            return R()
    ad = type("Ad", (), {"c": C()})()
    px, det = qg.fetch(ad, ["A", "B", "C"], in_session=True, now_s=NOW)
    assert px == {"A": 25.0}
    assert set(qg.refused(det)) == {"B", "C"}
