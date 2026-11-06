import numpy as np

from stablerun.agents import TYPES, allocate_counts, build_population, decide_exits, decide_reentry, draw_thresholds, run_signal

HCFG = {"n_agents": 1000,
        "type_shares": {"retail": 0.3, "exchange_mm": 0.3, "defi": 0.2, "institutional": 0.15, "arbitrageur": 0.05},
        "type_agent_counts": {"retail": 0.6, "exchange_mm": 0.1, "defi": 0.1, "institutional": 0.15, "arbitrageur": 0.05},
        "holding_dispersion": {t: 1.0 for t in TYPES},
        "attention": {t: 1.0 for t in TYPES},
        "thresholds": {t: {"mean": 0.1, "sd": 0.0} for t in TYPES}}
W = {"w1_depeg": 1.0, "w2_private": 1.0, "w3_herding": 0.5, "w4_suspension": 0.2}


def test_counts_and_holdings():
    assert allocate_counts(10, [0.33, 0.33, 0.34]).sum() == 10
    pop = build_population(HCFG, ["institutional", "arbitrageur"], np.random.default_rng(0))
    assert pop["counts"].sum() == 1000 and np.isclose(pop["holdings"].sum(), 1.0)
    for k, t in enumerate(TYPES):
        assert np.isclose(pop["holdings"][pop["type_idx"] == k].sum(), HCFG["type_shares"][t])
    assert np.isclose(pop["holdings"][pop["is_direct"]].sum(), 0.20)


def test_threshold_rule_no_shock_nobody_exits_big_shock_everyone():
    rng = np.random.default_rng(1)
    pop = build_population(HCFG, ["institutional"], rng)
    thr = draw_thresholds(pop, 2, rng, 0.005)
    exited = np.zeros((2, 1000), dtype=bool)
    x0 = np.zeros((2, 1000))
    s, _ = run_signal(x0, np.ones(2), np.zeros(2), np.zeros(2), W)
    assert not decide_exits(s, thr, exited, pop["attention"], rng).any()
    s, _ = run_signal(x0 + 0.5, np.ones(2), np.zeros(2), np.zeros(2), W)
    assert decide_exits(s, thr, exited, pop["attention"], rng).all()
    # depeg, herding and suspension all push the exit signal up; the core signal ignores the depeg
    s2, core = run_signal(x0, np.array([0.9, 1.0]), np.array([0.0, 0.3]), np.array([0.0, 1.0]), W)
    assert np.allclose(s2[0], 0.1) and np.allclose(s2[1], 0.15 + 0.2)
    assert np.allclose(core[0], 0.0) and np.allclose(core[1], 0.35)


def test_reentry_requires_hysteresis_and_prior_exit():
    rng = np.random.default_rng(2)
    pop = build_population(HCFG, ["institutional"], rng)
    thr = draw_thresholds(pop, 1, rng, 0.005)           # all 0.1
    exited = np.ones((1, 1000), dtype=bool)
    s = np.full((1, 1000), 0.09)
    assert not decide_reentry(s, thr, exited, pop["attention"], 0.02, rng).any()
    s = np.full((1, 1000), 0.07)
    assert decide_reentry(s, thr, exited, pop["attention"], 0.02, rng).all()
    assert not decide_reentry(s, thr, ~exited, pop["attention"], 0.02, rng).any()
