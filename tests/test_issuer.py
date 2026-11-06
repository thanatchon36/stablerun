import numpy as np
import pytest

from stablerun.issuer import apply_impairment, initial_reserves, mark_to_market, runoff, waterfall

ICFG = {"reserves": {"cash_deposits": 0.10, "reverse_repo": 0.20, "mmf_shares": 0.10,
                     "tbills_le_1m": 0.30, "tbills_1_3m": 0.20, "other": 0.10}}


def test_initial_reserves_sum_to_supply():
    res = initial_reserves(ICFG, 100.0, 3)
    assert np.allclose(sum(res.values()), 100.0)


def test_reserves_must_sum_to_one():
    bad = {"reserves": dict(ICFG["reserves"], other=0.5)}
    with pytest.raises(ValueError):
        initial_reserves(bad, 100.0, 1)


def test_impairment_hits_other_then_cash_never_bills():
    res = initial_reserves(ICFG, 100.0, 2)
    realised = apply_impairment(res, np.array([5.0, 15.0]))
    assert np.allclose(realised, [5.0, 15.0])
    assert np.allclose(res["other"], [5.0, 0.0])
    assert np.allclose(res["cash"], [10.0, 5.0])
    assert np.allclose(res["tb1"], 30.0) and np.allclose(res["tb3"], 20.0)


def test_waterfall_order_and_no_impact_for_liquid():
    res = initial_reserves(ICFG, 100.0, 1)
    disc = {"tb1": np.array([0.0]), "tb3": np.array([0.0])}
    raised, used, short = waterfall(res, np.array([25.0]), disc, 0.3)
    assert np.allclose(raised, 25.0) and np.allclose(short, 0.0)
    assert np.allclose(used["cash"], 10.0) and np.allclose(used["repo"], 15.0)
    assert np.allclose(used["mmf"], 0.0) and np.allclose(used["tb1"], 0.0)


def test_waterfall_bills_grossed_up_for_concession_and_other_haircut():
    res = initial_reserves(ICFG, 100.0, 1)
    disc = {"tb1": np.array([0.01]), "tb3": np.array([0.02])}
    # need everything liquid (40) + all tb1 (30 face -> 29.7) + some tb3
    raised, used, short = waterfall(res, np.array([80.0]), disc, 0.3)
    assert np.allclose(raised, 80.0)
    assert np.allclose(used["tb1"], 30.0)
    assert np.allclose(used["tb3"] * 0.98, 80.0 - 40.0 - 29.7)
    assert np.allclose(short, 0.0)
    # now exhaust: other 10 at 30% haircut yields 7 -> shortfall
    raised2, used2, short2 = waterfall(res, np.array([50.0]), disc, 0.3)
    assert np.allclose(used2["other"], 10.0)
    assert short2[0] > 0 and np.allclose(raised2 + short2, 50.0)


def test_runoff_moves_bills_to_cash_and_rolls_tb3():
    res = initial_reserves(ICFG, 100.0, 1)
    tb1_0, tb3_0 = res["tb1"].copy(), res["tb3"].copy()
    mature = runoff(res, tb1_0, tb3_0, 21, 42)
    assert np.allclose(mature, 30.0 / 21)
    assert np.allclose(res["cash"], 10.0 + 30.0 / 21)
    assert np.allclose(res["tb3"], 20.0 - 20.0 / 42)
    assert np.allclose(res["tb1"], 30.0 - 30.0 / 21 + 20.0 / 42)
    assert np.allclose(sum(res.values()), 100.0)


def test_mark_to_market_applies_concession_only_to_bills():
    res = initial_reserves(ICFG, 100.0, 1)
    v = mark_to_market(res, {"tb1": np.array([0.01]), "tb3": np.array([0.02])})
    assert np.allclose(v, 100.0 - 0.3 - 0.4)
