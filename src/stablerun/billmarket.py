"""Treasury-bill market: price impact with permanent and temporary components, dealer capacity."""
from __future__ import annotations

import numpy as np


def impact_g(q: np.ndarray, form: str, q0: float) -> np.ndarray:
    """Impact shape in flow units, anchored so that g(q0) = q0 for every form.

    sqrt      linear up to the anchor q0, square-root beyond it: g = q (q <= q0), sqrt(q0*q) (q > q0).
              The linear segment avoids the infinite slope of a pure square root at small flows.
    linear    g = q (upper bound used for robustness)
    pure_sqrt g = sqrt(q0*q) everywhere
    """
    q = np.maximum(np.asarray(q, dtype=float), 0.0)
    if form == "sqrt":
        return np.where(q <= q0, q, np.sqrt(q0 * q))
    if form == "linear":
        return q
    if form == "pure_sqrt":
        return np.sqrt(q0 * q)
    raise ValueError(f"unknown functional_form {form!r}")


def concession(y_bp: np.ndarray, duration: float) -> np.ndarray:
    """Price concession (share of face) for a yield deviation in bp."""
    return np.maximum(duration * y_bp / 1e4, 0.0)


def bill_price(yield_decimal: float, maturity_years: float = 0.25) -> float:
    return 1.0 / (1.0 + yield_decimal * maturity_years)


def new_state(n_paths: int) -> dict:
    z = np.zeros(n_paths)
    return {"YP": z.copy(), "YT": z.copy(), "Y": z.copy(), "I": z.copy(), "C": z.copy()}


def step(state: dict, sold: np.ndarray, buys: np.ndarray, withdrawn: np.ndarray, mcfg: dict,
         backstop: dict | None = None) -> dict:
    """Advance the market one day.

    sold      bills sold outright to dealers (bn)             -> persistent, temporary, dealer inventory
    withdrawn maturing bills not rolled over at auction (bn)  -> persistent only (demand withdrawn), weight runoff_weight
    buys      redeemed cash returning to bills via MMFs (bn)  -> reduces net demand withdrawn and dealer inventory

    YP = lam_p * g(C) * m        C = cumulative net demand withdrawn, m = dealer-capacity multiplier
    YT = (1-kappa) YT + lam_t * g(sold) * m
    I  = (1-absorb) I + sold - buys   (dealer inventory, >= 0)
    """
    imp, dl = mcfg["impact"], mcfg["dealers"]
    mult = 1.0 + (state["I"] / dl["capacity_K"]) ** dl["convexity_gamma"]
    scale = 1.0
    if backstop is not None:
        if backstop.get("capacity_unbounded", True):
            mult = np.ones_like(mult)
        scale = float(backstop.get("impact_multiplier", 1.0))
    form, q0 = imp["functional_form"], imp["reference_flow"]
    state["C"] = np.maximum(state["C"] + sold + imp.get("runoff_weight", 1.0) * withdrawn - buys, 0.0)
    state["YP"] = scale * imp["sell_permanent_bp_per_bn"] * impact_g(state["C"], form, q0) * mult
    state["YT"] = (1.0 - imp["temporary_decay_per_day"]) * state["YT"] \
        + scale * imp["sell_temporary_bp_per_bn"] * impact_g(sold, form, q0) * mult
    state["I"] = np.maximum((1.0 - dl["absorption_per_day"]) * state["I"] + sold - buys, 0.0)
    state["Y"] = state["YP"] + state["YT"]
    return state
