"""Reddit round R10: the two checks r/algotrading keeps finding broken in other people's bots. No network.

1. Causality: a decision made on `today` must not change when bars from `today` on are replaced by garbage
   (the truncate-vs-full test; catches centred windows, full-series normalisation, same-bar fills).
2. Cost monotonicity: a higher cost input never lowers the per-side cost the night leg is charged
   (catches a cost parameter that is shown but silently not applied).
"""
import numpy as np
import pandas as pd

from research.sim import book as B
from swingtrader.daily import signals as sg


def _closes(seed=0, n=600, k=8):
    rng = np.random.default_rng(seed)
    ix = pd.bdate_range("2023-01-02", periods=n)
    r = rng.normal(0.0004, 0.012, size=(n, k)) + rng.normal(0, 0.0005, size=k)
    return pd.DataFrame(100 * np.exp(np.cumsum(r, axis=0)), index=ix, columns=[f"E{i}" for i in range(k)])


def test_momentum_top_ignores_today_and_later():
    c = _closes()
    rng = np.random.default_rng(1)
    for today in c.index[300::17]:
        clean = sg.momentum_top(c[c.index < today], today, 3)
        poisoned = c.copy()
        later = poisoned.index >= today
        poisoned.loc[later] = rng.uniform(1, 1e4, size=(later.sum(), c.shape[1]))
        assert sg.momentum_top(poisoned, today, 3) == clean, today


def test_oversold_and_tow_use_only_what_they_are_given():
    # both take history through yesterday plus a decision price; appending future bars to the history
    # is the caller's bug, so pin the contract: the result depends on the last bars passed and nothing hidden
    c = _closes(2).iloc[:, 0].values
    a = sg.oversold_trigger(c[:200], c[200])
    assert a == sg.oversold_trigger(list(c[:200]), float(c[200]))
    o = c * 1.001
    assert sg.tug_of_war(o[:200], c[:200]) == sg.tug_of_war(o[150:200], c[150:200]) or \
        np.isnan(sg.tug_of_war(o[150:200], c[150:200]))


def test_cost_inputs_are_applied_and_monotone():
    price = np.array([3.0, 8.0, 15.0, 30.0, 30.0, 250.0])
    adv = np.array([1e6, 5e6, 2e7, 1e7, 1e8, 1e9])
    lo, hi = B.cost_bps("tier", price, adv), B.cost_bps("tier_hi", price, adv)
    assert (hi >= lo).all() and (hi > lo).any()
    assert (np.diff(lo[[0, 2, 3, 4]]) <= 0).all()                     # cheaper / thinner names cost more
    assert (B.cost_bps("tier+tick", price, adv) >= lo).all()
    ret = np.full(len(price), 0.002)
    net = lambda m: ret - 2 * B.cost_bps(m, price, adv) / 1e4
    assert (net("flat10") < net("flat5")).all()                        # doubling the cost lowers every net
    assert (net("tier_hi") <= net("tier")).all()
