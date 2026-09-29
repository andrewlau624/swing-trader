"""Addendum 30: the night pool's opt-in raw-price switch (research/sim).

Tiny synthetic frames only: no research data, no network."""
import numpy as np
import pandas as pd

from research.sim import book as B
from research.sim import data as D

D1, D2 = pd.Timestamp("2025-03-03"), pd.Timestamp("2025-03-04")


def _cands():
    # REV later did a 1:100 reverse split: adjusted $40 is really $0.40.
    # FWD later did a 10:1 forward split: adjusted $3 is really $30.
    # PLAIN never split.
    rows = []
    for d in (D1, D2):
        for sym, p in (("REV", 40.0), ("FWD", 3.0), ("PLAIN", 25.0)):
            rows.append(dict(date=d, sym=sym, p50=p, L50=p * 0.99, H50=p * 1.20, pc=p / 0.88,
                             day50=-0.12, ibs50=0.05, ret=0.02, close_move=0.0, vol20=0.9,
                             ret20=-0.1, adv=3e7))
    x = pd.DataFrame(rows)
    x["C"] = x.p50 * (1 + x.close_move)
    return x


def _raw():
    rows = []
    for sym, f in (("REV", 0.01), ("FWD", 10.0), ("PLAIN", 1.0)):
        for d in (D1,):                      # D2 missing on purpose: nearest-date fallback
            adj = {"REV": 40.0, "FWD": 3.0, "PLAIN": 25.0}[sym]
            rows.append(dict(symbol=sym, date=d, raw_close=adj * f, adj_close=adj))
    return pd.DataFrame(rows)


def _R():
    idx = pd.bdate_range("2025-01-01", D2)
    rng = np.random.default_rng(0)
    return pd.DataFrame(rng.normal(0, 0.03, (len(idx), 3)), index=idx, columns=["REV", "FWD", "PLAIN"])


def test_raw_factor_exact_nearest_none():
    x = _cands()
    x = pd.concat([x, x.iloc[[0]].assign(sym="GONE")], ignore_index=True)
    y = D.add_raw_factor(x, _raw())
    g = y.set_index(["date", "sym"])
    assert g.loc[(D1, "REV"), "raw_src"] == "exact"
    assert g.loc[(D2, "REV"), "raw_src"] == "nearest"
    assert np.isclose(g.loc[(D2, "REV"), "raw_p50"], 0.40)
    assert np.isclose(g.loc[(D1, "FWD"), "raw_C"], 30.0)
    assert g.loc[(D1, "GONE"), "raw_src"] == "none" and g.loc[(D1, "GONE"), "raw_f"] == 1.0
    assert (y.ret == x.ret).all(), "returns are split-invariant and must not change"


def test_night_days_default_unchanged_and_raw_floor():
    x = _cands(); R = _R()
    adj = B.night_days(x=x, R=R, max_corr=None)
    assert set(adj[D1].syms) == {"REV", "PLAIN"}          # adjusted: FWD looks like $3
    raw = B.night_days(x=D.add_raw_factor(x, _raw()), R=R, max_corr=None, raw_price=True)
    assert set(raw[D1].syms) == {"FWD", "PLAIN"}          # live saw REV at $0.40, FWD at $30
    nd = raw[D1]
    i = list(nd.syms).index("FWD")
    assert np.isclose(nd.price[i], 30.0) and np.isclose(nd.close[i], 30.0)
    assert np.allclose(nd.day_ret, -0.12)                  # day_ret / IBS invariant
    # a lower floor on raw prices lets REV back in
    low = B.night_days(x=D.add_raw_factor(x, _raw()), R=R, max_corr=None, raw_price=True, price_min=0.3)
    assert "REV" in set(low[D1].syms)


def test_cost_tier_and_whole_shares_on_raw_price():
    # tier on raw: $0.40 -> the <$10 tier; tick floor: 0.5c / $0.40 = 125bp
    c = B.cost_bps("tier", np.array([0.40, 30.0]), np.array([3e7, 3e7]))
    assert list(c) == [15.0, 7.5]
    ct = B.cost_bps("tier+tick", np.array([0.40, 30.0]), np.array([3e7, 3e7]))
    assert np.isclose(ct[0], 125.0) and ct[1] == 7.5
    assert np.isclose(B.cost_bps("flat3+tick", np.array([1.0]), np.array([1e8]))[0], 50.0)
    assert B.cost_bps(3.0, np.array([1.0]), np.array([1e8]))[0] == 3.0     # default untouched
    # whole shares: $100 per name buys 3 shares at $30 (raw), 33 at $3 (adjusted)
    per = 100.0
    assert np.floor(per / 30.0) * 30.0 == 90.0 and np.floor(per / 3.0) * 3.0 == 99.0
