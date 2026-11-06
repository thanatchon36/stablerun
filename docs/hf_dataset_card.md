---
pretty_name: "When Stablecoins Run: simulation outputs"
license: cc-by-4.0
language: [en]
tags: [stablecoins, treasury-bills, fire-sales, agent-based-model, financial-stability, stress-testing, monte-carlo, finance, simulation]
size_categories: [10K<n<100K]
configs:
  - config_name: e1_paths
    data_files: data/e1_paths.csv
    default: true
  - config_name: e1_summary
    data_files: data/e1_summary.csv
  - config_name: e2_tipping_point
    data_files: data/e2_tipping_point.csv
  - config_name: e2_crossings
    data_files: data/e2_crossings.csv
  - config_name: e3_policy_grid
    data_files: data/e3_policy_grid.csv
  - config_name: e4_contagion
    data_files: data/e4_contagion.csv
  - config_name: e5_sensitivity
    data_files: data/e5_sensitivity.csv
  - config_name: benchmark_check
    data_files: data/benchmark_check.csv
  - config_name: calibration_grid
    data_files: data/calibration_grid.csv
  - config_name: calibration_validation
    data_files: data/calibration_validation.csv
---

# When Stablecoins Run: simulation outputs

Every simulation result behind the working paper *When Stablecoins Run: Fire-Sale Spillovers to the Treasury
Bill Market. An Agent-Based Stress Test* (Thanatchon Chongmankhong, November 2026). The data are outputs of
**stablerun**, a calibrated agent-based model of a payment-stablecoin run and its spillover to the US
Treasury-bill market.

- **Paper (PDF):** https://github.com/thanatchon36/stablerun/raw/main/paper.pdf
- **Code:** https://github.com/thanatchon36/stablerun (`python scripts/run_all.py --experiment all` regenerates every file here)
- **DOI:** https://doi.org/10.5281/zenodo.23996044 (Zenodo archive of release v0.3.0)

These are model outputs, not observations. Nothing here is market data. The institutional inputs (issuer
sizes, reserve mixes) are defaults flagged `VERIFY` in `config/params_default.yaml`, and the model is a
stress-testing tool, not a forecast.

## Files

| Config | Rows | Content |
|---|---|---|
| `e1_paths` | 10,000 | E1 baseline: one row per Monte Carlo path, 1,000 paths for each issuer (A, B) and scenario |
| `e1_summary` | 10 | E1 medians, 5th and 95th percentiles and probabilities per issuer and scenario |
| `e2_tipping_point` | 60 | E2: peak impact against issuer size (1, 2, 3, 5, 10× today), by scenario, impact form and redemption rails, 300 paths per cell |
| `e2_crossings` | 12 | E2: size multiple at which median peak impact first exceeds 10, 25 and 50 bp |
| `e3_policy_grid` | 196 | E3: cash buffer × redemption fee × maturity cap × Fed backstop, plus par against NAV redemption, 300 paths per cell |
| `e4_contagion` | 6 | E4: a run on Issuer A spills over to Issuer B's beliefs with weight beta |
| `e5_sensitivity` | 30 | E5: one-at-a-time sensitivity (tornado), low and high value of each parameter |
| `benchmark_check` | 9 | Simulated exit share with behavioural channels off against the closed-form threshold aggregate |
| `calibration_grid` | 48 | Calibration search over the behavioural parameters, with loss and fitted moments for both episodes |
| `calibration_validation` | 5 | Fitted moments against the USDC (March 2023) and USDT (May 2022) targets |

`config/params_default.yaml` holds every parameter with its source and a confidence note. The E1 seed is
`20261105`.

## Scenarios

| Name | Meaning |
|---|---|
| `control` | No shock |
| `loss05`, `loss10`, `loss20` | Solvency run: 5, 10 or 20% of reserves exposed and lost |
| `scare08` (E1), `scare` (E2 to E5) | Liquidity run: 8% of reserves exposed, resolved without loss on day 2, one day without processing (USDC 2023-like) |

Issuer A is a large offshore issuer (supply USD 180 bn); Issuer B is a US-regulated issuer (supply USD 75 bn). In E2 the
rails are `calibrated` (processing capacity from the calibration), `fast` (5% of supply per day) or
`instant` (20% per day); impact is `sqrt` (square root, main case) or `linear` (upper bound). E3 and E5 use two
configurations: `scare_1x_calibrated` (liquidity run at today's size) and `loss10_5x_fast` (solvency run at
5× size with fast rails).

## Columns of `e1_paths`

The horizon is 30 business days. Dollar amounts are USD billions.

| Column | Definition |
|---|---|
| `issuer`, `scenario`, `path` | Issuer, scenario and path index |
| `min_price` | Lowest secondary-market price of the token (par = 1) |
| `R_day7`, `R_day14`, `R_end` | Cumulative redemptions as a share of initial supply on day 7, day 14 and day 30 |
| `day_R10` | First day on which cumulative redemptions reach 10% of supply (empty if never) |
| `peak_Y_bp`, `Y_day7_bp`, `Y_end_bp` | Three-month bill-yield impact in basis points: peak, day 7 and day 30 |
| `bills_sold` | Bills sold outright before maturity |
| `matured` | Bills that matured over the horizon |
| `withdrawn` | Matured bills not reinvested: demand withdrawn from auctions |
| `net_demand_withdrawn` | Peak cumulative net demand withdrawn from the bill market |
| `other_sold` | Non-bill reserve assets sold |
| `peak_inv_over_K` | Peak dealer inventory relative to dealer capacity |
| `peak_queue_days` | Peak redemption queue in days of processing capacity |
| `susp_days` | Days on which redemptions were suspended |
| `fs_loss` | Issuer's fire-sale loss |
| `impairment_loss` | Realised reserve loss from the shock |
| `nav_end` | Net asset value per token on day 30 |
| `run`, `severe_run` | Redemptions by day 30 of at least 20% and 50% of supply |
| `Y_gt_10bp`, `Y_gt_25bp`, `Y_gt_50bp` | Peak impact above 10, 25 and 50 bp |

Summary tables use the same names with suffixes `_med`, `_p5` and `_p95` for the median and percentiles across
paths, and `run_prob`, `susp_any` and `P_Y_gt_*` for shares of paths.

## Loading

```python
from datasets import load_dataset
paths = load_dataset("thanatchon36/stablerun", "e1_paths", split="train").to_pandas()
paths.groupby(["issuer", "scenario"]).peak_Y_bp.median()
```

## License and citation

Data: CC BY 4.0. Code: MIT (GitHub repository).

```bibtex
@unpublished{chongmankhong2026stablerun,
  author = {Chongmankhong, Thanatchon},
  title  = {When Stablecoins Run: Fire-Sale Spillovers to the Treasury Bill Market. An Agent-Based Stress Test},
  note   = {Working paper and code repository},
  year   = {2026},
  doi    = {10.5281/zenodo.23996044},
  url    = {https://github.com/thanatchon36/stablerun}
}
```
