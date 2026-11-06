"""Holder population and the threshold exit rule (vectorised over Monte Carlo paths)."""
from __future__ import annotations

import numpy as np

TYPES = ["retail", "exchange_mm", "defi", "institutional", "arbitrageur"]


def allocate_counts(n: int, weights) -> np.ndarray:
    """Integer agent counts per type that sum exactly to n (largest-remainder rounding)."""
    w = np.asarray(weights, dtype=float)
    raw = w / w.sum() * n
    counts = np.floor(raw).astype(int)
    short = n - counts.sum()
    counts[np.argsort(-(raw - counts))[:short]] += 1
    return counts


def build_population(hcfg: dict, direct_types, rng: np.random.Generator) -> dict:
    """Agent types, holdings (shares of supply, sum to 1), thresholds moments, attention, access."""
    n = int(hcfg["n_agents"])
    counts = allocate_counts(n, [hcfg["type_agent_counts"][t] for t in TYPES])
    type_idx = np.repeat(np.arange(len(TYPES)), counts)
    holdings = np.zeros(n)
    for k, t in enumerate(TYPES):
        m = type_idx == k
        if not m.any():
            continue
        w = rng.lognormal(0.0, float(hcfg["holding_dispersion"][t]), int(m.sum()))
        holdings[m] = float(hcfg["type_shares"][t]) * w / w.sum()
    holdings /= holdings.sum()

    def per_type(values):
        return np.asarray([values[t] for t in TYPES], dtype=float)[type_idx]

    return {
        "n": n,
        "type_idx": type_idx,
        "counts": counts,
        "holdings": holdings,
        "thr_mean": per_type({t: hcfg["thresholds"][t]["mean"] for t in TYPES}),
        "thr_sd": per_type({t: hcfg["thresholds"][t]["sd"] for t in TYPES}),
        "attention": per_type(hcfg["attention"]),
        "is_direct": np.isin(np.asarray(TYPES)[type_idx], list(direct_types)),
    }


def draw_thresholds(pop: dict, n_paths: int, rng: np.random.Generator, floor: float) -> np.ndarray:
    thr = pop["thr_mean"][None, :] + pop["thr_sd"][None, :] * rng.standard_normal((n_paths, pop["n"]))
    return np.maximum(thr, floor)


def run_signal(x: np.ndarray, price: np.ndarray, herding: np.ndarray, suspended: np.ndarray, w: dict):
    """Returns (exit signal, core signal); x is (P, N), the rest (P,).

    core_i = w2*x_i + w3*H + w4*1[suspended]      fundamentals, herding, suspension
    exit_i = core_i + w1*(1-p)                      a visible depeg adds fear for exit decisions
    Re-entry is judged on core_i only: once fundamentals are fine, a discount is a buying
    opportunity rather than a reason to stay away."""
    common = w["w3_herding"] * herding + w["w4_suspension"] * suspended
    core = w["w2_private"] * x + common[:, None]
    return core + (w["w1_depeg"] * (1.0 - price))[:, None], core


def decide_exits(s: np.ndarray, thr: np.ndarray, exited: np.ndarray, attention: np.ndarray,
                 rng: np.random.Generator) -> np.ndarray:
    """Agents who have not exited, pay attention today, and whose signal exceeds their threshold."""
    awake = rng.random(s.shape) < attention[None, :]
    return (~exited) & awake & (s > thr)


def decide_reentry(s: np.ndarray, thr: np.ndarray, exited: np.ndarray, attention: np.ndarray,
                   hysteresis: float, rng: np.random.Generator) -> np.ndarray:
    """Exited agents who pay attention today and whose signal has fallen clearly below their threshold
    re-enter (buy tokens back at the market price, absorbing the secondary-market overhang)."""
    awake = rng.random(s.shape) < attention[None, :]
    return exited & awake & (s < thr - hysteresis)
