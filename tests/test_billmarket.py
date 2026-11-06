import numpy as np

from stablerun.billmarket import bill_price, concession, impact_g, new_state, step

MCFG = {"impact": {"reference_flow": 3.5, "sell_permanent_bp_per_bn": 2.0, "sell_temporary_bp_per_bn": 1.0,
                   "buy_bp_per_bn": 0.5, "temporary_decay_per_day": 0.3, "functional_form": "sqrt", "runoff_weight": 1.0},
        "dealers": {"capacity_K": 150.0, "convexity_gamma": 2.0, "absorption_per_day": 0.1}}


def test_sqrt_matches_linear_at_anchor_and_is_concave():
    q0 = 3.5
    assert np.isclose(impact_g(np.array([q0]), "sqrt", q0), impact_g(np.array([q0]), "linear", q0))
    assert impact_g(np.array([4 * q0]), "sqrt", q0) == 2 * q0
    assert impact_g(np.array([4 * q0]), "linear", q0) == 4 * q0
    assert impact_g(np.array([0.5 * q0]), "sqrt", q0) == 0.5 * q0          # linear below the anchor
    assert np.isclose(impact_g(np.array([0.5 * q0]), "pure_sqrt", q0), np.sqrt(0.5) * q0)


def test_concession_and_price():
    assert np.isclose(concession(np.array([100.0]), 0.25), 0.0025)
    assert np.isclose(bill_price(0.04, 0.25), 1 / 1.01)


def test_anchor_flow_gives_literature_range_after_ten_days():
    st = new_state(1)
    z = np.zeros(1)
    step(st, np.array([3.5]), z, z, MCFG)        # one-day $3.5bn sale
    for _ in range(9):
        step(st, z, z, z, MCFG)
    assert 6.0 <= st["Y"][0] <= 8.5               # persistent 7bp + small residual temporary


def test_capacity_multiplier_and_buys_reduce_net_demand():
    st = new_state(1)
    z = np.zeros(1)
    step(st, np.array([150.0]), z, z, MCFG)      # inventory = K after day 1
    y1 = st["Y"][0]
    step(st, np.array([150.0]), z, z, MCFG)      # multiplier 1 + (135/150)^2 on day 2
    assert st["Y"][0] > y1
    st2 = new_state(1)
    step(st2, np.array([10.0]), np.array([10.0]), z, MCFG)
    assert np.isclose(st2["C"][0], 0.0) and np.isclose(st2["YP"][0], 0.0)


def test_withdrawn_demand_is_persistent_only():
    st = new_state(1)
    z = np.zeros(1)
    step(st, z, z, np.array([3.5]), MCFG)
    assert np.isclose(st["YP"][0], 7.0) and np.isclose(st["YT"][0], 0.0) and np.isclose(st["I"][0], 0.0)


def test_backstop_removes_capacity_penalty_and_scales_impact():
    st = new_state(1)
    z = np.zeros(1)
    step(st, np.array([300.0]), z, z, MCFG, backstop={"impact_multiplier": 0.5, "capacity_unbounded": True})
    expected = 0.5 * 2.0 * np.sqrt(3.5 * 300.0) + 0.5 * 1.0 * np.sqrt(3.5 * 300.0)
    assert np.isclose(st["Y"][0], expected)
