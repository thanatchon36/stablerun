import numpy as np

from stablerun import load_config, simulate, with_overrides
from stablerun.metrics import path_metrics


def small_cfg():
    return with_overrides(load_config(), {"holders": {"n_agents": 500}, "meta": {"horizon_days": 10}})


def test_no_shock_is_quiet_and_accounting_holds():
    cfg = small_cfg()
    r = simulate(cfg, {"exposure": 0.0}, n_paths=8, seed=3)
    assert r["R"][:, -1].max() < 0.05
    assert r["price"].min() > 0.98
    assert np.allclose(r["supply"][:, 0], r["s0"])
    # tokens redeemed never exceed initial supply; queue and overhang non-negative
    assert (r["R"] <= 1.0 + 1e-9).all() and (r["queue"] >= -1e-9).all() and (r["overhang"] >= -1e-9).all()
    # cumulative cash paid equals cumulative cash raised from the sources (before fee income)
    paid = r["paid"].sum(axis=1) * (1 - cfg["issuers"]["A"]["redemption"]["fee"])
    sources = (r["cash_used"] + r["repo_used"] + r["mmf_used"] + r["tb1_sold"] + r["tb3_sold"]).sum(axis=1)
    assert np.allclose(paid, sources, rtol=1e-6, atol=1e-6)


def test_loss_shock_triggers_run_and_metrics_shape():
    cfg = small_cfg()
    r = simulate(cfg, {"exposure": 0.10}, n_paths=8, seed=4)
    df = path_metrics(r, cfg)
    assert len(df) == 8 and df["R_end"].median() > 0.1
    assert (df["peak_Y_bp"] > 0).all()
    assert (r["price"] <= 1.0).all()


def test_scare_recovers_after_resolution():
    cfg = small_cfg()
    r = simulate(cfg, {"exposure": 0.08, "realized_share": 0.0, "resolution_day": 3}, n_paths=8, seed=5)
    assert r["fund_disc"][:, 2].min() > 0 and r["fund_disc"][:, 3:].max() == 0
    assert r["price"][:, -1].mean() > r["price"][:, 1:3].mean()
    assert np.allclose(r["impairment_loss"], 0.0)


def test_seed_reproducible_and_size_scaling():
    cfg = small_cfg()
    a = simulate(cfg, {"exposure": 0.05}, n_paths=4, seed=7)
    b = simulate(cfg, {"exposure": 0.05}, n_paths=4, seed=7)
    assert np.allclose(a["R"], b["R"]) and np.allclose(a["Y"], b["Y"])
    big = simulate(cfg, {"exposure": 0.05}, n_paths=4, seed=7, size_multiplier=5.0)
    assert np.isclose(big["s0"], 5 * a["s0"]) and big["Y"].max() > a["Y"].max()


def test_policy_hooks_change_reserves_and_fee():
    from stablerun.config import apply_policy
    cfg = apply_policy(load_config(), "A", {"cash_buffer": 0.2, "redemption_fee": 0.01, "maturity_cap_days": 180})
    res = cfg["issuers"]["A"]["reserves"]
    assert np.isclose(res["cash_deposits"], 0.2) and np.isclose(sum(res.values()), 1.0)
    assert cfg["issuers"]["A"]["redemption"]["fee"] == 0.01
    assert cfg["issuers"]["A"]["ladder_days"]["tb3"] == 84
