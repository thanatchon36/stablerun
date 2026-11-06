"""Secondary market for the token: two-component depeg, overhang and capital-constrained arbitrage."""
from __future__ import annotations

import numpy as np


def arbitrage_capacity(daily_capital: float, cap: float, queue: np.ndarray, suspended: np.ndarray,
                       horizon_days: int) -> np.ndarray:
    """Arbitrageurs buy only what they can redeem within `horizon_days` of processing capacity.
    A suspended issuer removes the arbitrage bid entirely."""
    room = np.maximum(horizon_days * cap - queue, 0.0)
    return np.where(suspended, 0.0, np.minimum(daily_capital, room))


def clear(sell_volume: np.ndarray, overhang_prev: np.ndarray, reentry_demand: np.ndarray, arb_cap: np.ndarray,
          s0: float, fundamental: np.ndarray, suspended: np.ndarray, scfg: dict):
    """Returns (price, liquidity discount, arbitrage purchases, overhang after today, tokens re-absorbed).

    Tokens offered today = new sales + overhang (tokens held by uninformed dip buyers who resell).
    Demand at par from re-entering holders is served first; arbitrageurs then take what their capital
    and the redemption queue allow; the rest stays as overhang and sets the liquidity discount
    (an inventory-type discount, stock-based):
        liquidity_t = c * 1[offered > 0] + eta * overhang_t / S0 + delta * 1[suspended]
        price_t     = max(1 - min(psi * fundamental, cap) - liquidity_t, floor)
    where fundamental = expected loss share of the remaining holders (public information).
    """
    offered = sell_volume + overhang_prev
    absorbed = np.minimum(offered, reentry_demand)
    buys = np.minimum(offered - absorbed, arb_cap)
    overhang = offered - absorbed - buys
    liq = scfg["arbitrage_cost"] * (offered > 0) \
        + scfg["liquidity_depth_eta"] * overhang / s0 \
        + scfg["suspension_discount"] * suspended
    fund = np.minimum(scfg["fundamental_weight"] * fundamental, scfg["max_fundamental_discount"])
    price = np.maximum(1.0 - fund - liq, scfg["price_floor"])
    return price, liq, buys, overhang, absorbed
