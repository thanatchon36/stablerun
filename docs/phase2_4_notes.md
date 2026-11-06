# Phases 2-4 notes

## Calibration (Phase 2)
Two-stage grid against USDC-2023 (Issuer B) and USDT-2022 (Issuer A); see `results/tables/calibration.md`.
Best fit: eta 0.1, threshold scale 1.0, w1 0.5, psi 1.0, feared USDT exposure 2%; processing cap A 1.2% / B 3% of
supply per day; arbitrage capital A 1.1% / B 3%. Redemption targets matched; the USDC trough is under-predicted
(0.90 vs 0.875) and the USDT trough over-predicted (0.93 vs 0.96). Config patched in place (version 0.3).

## Model changes after Phase 1
- weekend blackout days (no processing), fee-aware arbitrage, redemption-at-NAV policy, contagion spillover signal,
  fixed-belief benchmark switch, exposure-loss probability psi
- liquidity management: cash kept = min(queue, 5 days x cap); the day's maturities are rolled back into bills with
  any cash above that; the buffer is spent, not rebuilt. An earlier rule that rebuilt the initial cash level during
  a run made cash buffers *increase* demand withdrawal; E3 was re-run after the fix.
- rails variants for E2: calibrated (1.2%/day), fast (5%), instant (20%)

## Results files
E1 `results/tables/E1_{A,B}_summary.md`, E2 `E2_tipping_point.md`, E3 `E3_policy_grid.md`, E4 `E4_contagion.md`,
E5 `E5_sensitivity.csv`, benchmark `benchmark_check.csv`; figures F1-F6 in `results/figures`; paper in `paper/`.

## Not done (stated in the paper)
Hourly time step; Sobol/Morris global sensitivity (one-at-a-time instead); inflows/minting in normal times;
bank-deposit channel; weekend-specific liquidity.
