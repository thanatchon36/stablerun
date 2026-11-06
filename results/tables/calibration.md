# Phase 2 calibration

Best shared parameters (grid, 40 paths x 4,000 agents): eta = 0.1, threshold scale = 1.0, w1 = 0.5, psi = 1.0, USDT-2022 feared exposure = 0.02; Issuer A cap/arb = 0.012/0.011, Issuer B cap/arb = 0.03/0.03 (shares of supply per day).

Validation at 300 paths x 10,000 agents (z = (model - observed)/tolerance; all observed values VERIFY):

| Episode | Target | Observed | Model | z |
|---|---|---|---|---|
| usdc_2023 | min_price | 0.875 ± 0.01 | 0.9038 | 2.88 |
| usdc_2023 | R_day5 | 0.135 ± 0.015 | 0.12 | -1.0 |
| usdc_2023 | R_day22 | 0.25 ± 0.03 | 0.24 | -0.33 |
| usdt_2022 | min_price | 0.96 ± 0.015 | 0.9255 | -2.3 |
| usdt_2022 | R_day10 | 0.12 ± 0.015 | 0.12 | -0.0 |