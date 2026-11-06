"""Daily simulation of a stablecoin redemption run and its Treasury-bill spillover.

Timing within day t (vectorised over Monte Carlo paths):
 1. public expected-loss share updates; a common daily sentiment shock nu_t is added to every
    signal; holders compare run signal with threshold and exit;
    exited holders whose signal has fallen well below their threshold re-enter (demand at par)
 2. exits route: direct-access types -> redemption queue at par; others -> secondary market sale
 3. arbitrageurs buy discounted tokens from new sellers and from the overhang held by dip buyers
    (capital- and capacity-limited) and join the redemption queue
 4. secondary price = 1 - fundamental discount - liquidity discount (stock of overhang)
 5. bill ladder run-off adds cash; issuer processes min(queue, daily cap) via the waterfall;
    a shortfall of liquid assets = suspension for that day. The issuer keeps cash for the pending claims it
    can pay within a few days and rolls the rest of the day's maturities back into bills; maturities kept as
    cash are demand withdrawn at auction
 6. bills sold and demand withdrawn hit the bill market; redeemed cash partly returns via MMFs after a lag
 7. fire-sale cost, mark-to-market NAV and all series are recorded
"""
from __future__ import annotations

from collections import deque

import numpy as np

from . import billmarket as bm
from .agents import build_population, decide_exits, decide_reentry, draw_thresholds, run_signal
from .issuer import BILLS, apply_impairment, initial_reserves, mark_to_market, runoff, waterfall
from .market import arbitrage_capacity, clear

SERIES = ["price", "fund_disc", "liq_disc", "overhang", "reentry", "supply", "R", "exit_flow", "queue", "paid", "suspended",
          "Y", "YP", "YT", "inv", "C", "sold", "buys", "withdrawn", "reinvested", "nav", "fs_loss", "cash_used",
          "repo_used", "mmf_used", "matured", "tb1_sold", "tb3_sold", "other_sold", "belief"]


def simulate(cfg: dict, shock: dict, n_paths: int | None = None, seed: int | None = None,
             issuer: str = "A", size_multiplier: float = 1.0, policy: dict | None = None,
             chunk: int = 250) -> dict:
    """Run n_paths Monte Carlo paths. shock = {exposure, realized_share, resolution_day}.

    exposure       share of reserves publicly known to be at risk from day 1
    realized_share fraction of the exposure that is actually lost (1 = loss, 0 = scare only)
    resolution_day day on which the public learns the realised loss (None = exposure is the loss)
    Returns dict of (n_paths, T+1) series plus per-path metrics inputs.
    """
    from .config import apply_policy
    cfg = apply_policy(cfg, issuer, policy)
    n_paths = n_paths or cfg["meta"]["monte_carlo_paths"]
    seed = cfg["meta"]["seed"] if seed is None else seed
    T = int(cfg["meta"]["horizon_days"])
    rng = np.random.default_rng(seed)

    icfg, hcfg, mcfg, scfg = cfg["issuers"][issuer], cfg["holders"], cfg["bill_market"], cfg["secondary_market"]
    w = hcfg["run_signal_weights"]
    rcfg = icfg["redemption"]
    backstop = cfg["policy_grid"]["backstop"] if cfg.get("_policy", {}).get("fed_backstop") else None

    pop = build_population(hcfg, rcfg["direct_access_types"], rng)
    s0 = float(icfg["supply"]) * size_multiplier
    h_all = pop["holdings"] * s0
    h_direct = h_all * pop["is_direct"]
    h_secondary = h_all * (~pop["is_direct"])
    cap = rcfg["processing_cap_share_per_day"] * s0
    arb_daily = rcfg["arbitrage_capital_share_per_day"] * s0
    fee = float(rcfg["fee"])
    dur = mcfg["duration_years"]
    rho, lag = mcfg["reinvestment"]["share_rho"], int(mcfg["reinvestment"]["lag_days"])
    exposure = float(shock.get("exposure", 0.0))
    realized = exposure * float(shock.get("realized_share", 1.0))
    resolution_day = shock.get("resolution_day")
    blackout = int(shock.get("blackout_days", 0))          # days with no redemption processing (weekend proxy)
    fixed_belief = bool(shock.get("fixed_belief", False))  # benchmark check: belief does not rise with redemptions
    spill = np.asarray(shock.get("spillover_signal", np.zeros(T + 1)), dtype=float)  # E4: added to belief
    redeem_at_nav = bool(cfg.get("_policy", {}).get("redeem_at_nav", False))

    out = {k: [] for k in SERIES}
    out["impairment_loss"] = []
    for start in range(0, n_paths, chunk):
        P = min(chunk, n_paths - start)
        res = initial_reserves(icfg, s0, P)
        tb1_0, tb3_0 = res["tb1"].copy(), res["tb3"].copy()
        loss = apply_impairment(res, np.full(P, realized * s0))
        thr = draw_thresholds(pop, P, rng, hcfg["threshold_floor"])
        noise = hcfg["signal_noise_sigma"] * rng.standard_normal((P, pop["n"]))

        price, liq, overhang = np.ones(P), np.zeros(P), np.zeros(P)
        supply = np.full(P, s0)
        herd, susp, queue = np.zeros(P), np.zeros(P, dtype=bool), np.zeros(P)
        exited = np.zeros((P, pop["n"]), dtype=bool)
        market = bm.new_state(P)
        paid_hist = deque([np.zeros(P) for _ in range(lag)], maxlen=lag)
        fs_loss = np.zeros(P)
        rec = {k: np.zeros((P, T + 1)) for k in SERIES}
        rec["price"][:, 0], rec["supply"][:, 0], rec["nav"][:, 0] = 1.0, s0, (s0 - loss) / s0
        nav_prev = np.minimum((s0 - loss) / s0, 1.0)

        for t in range(1, T + 1):
            # 1. beliefs and exits
            psi = hcfg["exposure_loss_probability"]
            expected_pre = exposure * (realized / max(exposure, 1e-12) + (1.0 - realized / max(exposure, 1e-12)) * psi) if exposure > 0 else 0.0
            public_loss = expected_pre if (resolution_day is None or t < resolution_day) else realized
            if fixed_belief or redeem_at_nav:
                belief = np.full(P, public_loss) + spill[t]          # loss is shared pro rata: share does not grow
            else:
                belief = public_loss * s0 / np.maximum(supply, 1e-9) + spill[t]   # loss concentrates on who stays
            x = belief[:, None] + noise
            nu = hcfg["aggregate_noise_sigma"] * rng.standard_normal(P)   # common daily sentiment shock
            s_exit, s_core = run_signal(x, price, herd + nu / max(w["w3_herding"], 1e-9), susp.astype(float), w)
            new = decide_exits(s_exit, thr, exited, pop["attention"], rng)
            back = decide_reentry(s_core, thr, exited, pop["attention"], hcfg["reentry_hysteresis"], rng)
            exited |= new
            newf = new.astype(float)
            direct_req = newf @ h_direct
            sell_vol = newf @ h_secondary
            reentry_demand = back.astype(float) @ h_all
            herd = hcfg["herding_memory"] * herd + (direct_req + sell_vol) / s0

            # 2-4. secondary market and arbitrage
            cap_t = 0.0 if t <= blackout else cap
            arb_cap = arbitrage_capacity(arb_daily, cap_t, queue, susp, scfg["arbitrage_horizon_days"])
            arb_cap = np.where(1.0 - price > fee + scfg["arbitrage_cost"], arb_cap, 0.0)   # discount must cover fee + cost
            price, liq, arb_buys, overhang, absorbed = clear(sell_vol, overhang, reentry_demand, arb_cap, s0,
                                                              belief, susp, scfg)
            # re-entrants only get tokens if the overhang can supply them (accepted pro rata at random)
            fill = np.where(reentry_demand > 0, absorbed / np.maximum(reentry_demand, 1e-12), 0.0)
            exited &= ~(back & (rng.random(back.shape) < fill[:, None]))
            queue = queue + direct_req + arb_buys

            # 5. run-off, processing, waterfall
            matured = runoff(res, tb1_0, tb3_0, icfg["ladder_days"]["tb1"], icfg["ladder_days"]["tb3"])
            demand = np.minimum(queue, cap_t)
            disc = {a: bm.concession(market["Y"], dur[a]) for a in BILLS}
            payout = (1.0 - fee) * (nav_prev if redeem_at_nav else 1.0)
            need = demand * payout
            raised, used, shortfall = waterfall(res, need, disc, icfg["other_asset_haircut"])
            paid = np.where(need > 0, demand * raised / np.maximum(need, 1e-12), 0.0)
            paid = np.minimum(paid, demand)
            queue = queue - paid
            supply = supply - paid
            res["cash"] += paid * fee * (nav_prev if redeem_at_nav else 1.0)   # fee income stays with the issuer
            susp = shortfall > 1e-9

            # 5b. liquidity management: keep cash for the pending claims it can pay within cash_hoard_days and roll
            #     today's maturities back into bills with any cash above that; the cash buffer is spent, not rebuilt,
            #     during a run (never buys bills beyond the day's run-off)
            hoard = np.minimum(queue, icfg["cash_hoard_days"] * cap_t)
            surplus = np.maximum(res["cash"] - hoard, 0.0)
            reinvested = np.minimum(surplus, matured)
            res["cash"] -= reinvested
            res["tb1"] += reinvested
            withdrawn = matured - reinvested

            # 6. bill market
            sold = used["tb1"] + used["tb3"]
            paid_hist.append(paid)
            buys = rho * paid_hist[0] if lag > 0 else rho * paid
            bm.step(market, sold, buys, withdrawn, mcfg, backstop if (backstop and t >= backstop["start_day"]) else None)
            disc_post = {a: bm.concession(market["Y"], dur[a]) for a in BILLS}
            fs_loss = fs_loss + used["tb1"] * disc_post["tb1"] + used["tb3"] * disc_post["tb3"] \
                + used["other"] * icfg["other_asset_haircut"]

            # 7. record
            nav = mark_to_market(res, disc_post) / np.maximum(supply, 1e-9)
            nav_prev = np.minimum(nav, 1.0)
            vals = {"price": price, "fund_disc": np.minimum(belief, scfg["max_fundamental_discount"]),
                    "liq_disc": liq, "overhang": overhang, "reentry": absorbed, "supply": supply, "R": 1.0 - supply / s0,
                    "exit_flow": (direct_req + sell_vol) / s0, "queue": queue, "paid": paid,
                    "suspended": susp.astype(float), "Y": market["Y"], "YP": market["YP"], "YT": market["YT"],
                    "inv": market["I"], "C": market["C"], "sold": sold, "buys": buys, "withdrawn": withdrawn,
                    "reinvested": reinvested, "nav": nav,
                    "fs_loss": fs_loss, "cash_used": used["cash"], "repo_used": used["repo"],
                    "mmf_used": used["mmf"], "matured": matured, "tb1_sold": used["tb1"],
                    "tb3_sold": used["tb3"], "other_sold": used["other"], "belief": belief}
            for k, v in vals.items():
                rec[k][:, t] = v
        for k in SERIES:
            out[k].append(rec[k])
        out["impairment_loss"].append(loss)

    result = {k: np.concatenate(v, axis=0) for k, v in out.items()}
    result.update({"s0": s0, "issuer": issuer, "shock": dict(shock), "size_multiplier": size_multiplier,
                   "cash0": float(icfg["reserves"]["cash_deposits"]) * s0,
                   "policy": policy or {}, "n_paths": n_paths, "T": T, "cap": cap,
                   "capacity_K": mcfg["dealers"]["capacity_K"], "pop_counts": pop["counts"]})
    return result
