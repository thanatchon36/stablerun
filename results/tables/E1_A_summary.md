# E1 baseline — Issuer A, 1000 Monte Carlo paths, 30 business days

Supply $180bn; impact form `sqrt`; processing cap 1.2% of supply per day; arbitrage capital 1.1% of supply per day. All inputs are Phase-1 defaults (uncalibrated); see config/params_default.yaml.

Scenarios: `control` = 0% of reserves at risk, 100% of it lost; `loss05` = 5% of reserves at risk, 100% of it lost; `loss10` = 10% of reserves at risk, 100% of it lost; `loss20` = 20% of reserves at risk, 100% of it lost; `scare08` = 8% of reserves at risk, 0% of it lost, resolved on day 2

| Metric | control | loss05 | loss10 | loss20 | scare08 |
|---|---|---|---|---|---|
| Min price (med) | 0.997 | 0.872 | 0.783 | 0.628 | 0.904 |
| Redeemed day 7 | 1.2% | 8.4% | 8.4% | 8.4% | 7.2% |
| Redeemed day 30 | 2.2% | 36.0% | 35.8% | 35.8% | 19.3% |
| P(run >=20%) | 0% | 100% | 100% | 100% | 0% |
| P(run >=50%) | 0% | 0% | 0% | 0% | 0% |
| Peak 3M bill impact, bp (med) | 4.2 | 22.1 | 21.2 | 21.5 | 17.5 |
| Peak impact, bp (p95) | 5.8 | 22.2 | 21.3 | 21.5 | 17.6 |
| P(impact >10bp) | 0% | 100% | 100% | 100% | 100% |
| Bills sold outright, $bn (med) | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Maturing bills not rolled, $bn (med) | 3.1 | 66.1 | 63.5 | 64.3 | 33.9 |
| Peak net bill demand withdrawn, $bn (med) | 2.1 | 34.8 | 32.2 | 33.1 | 22.0 |
| Other assets sold, $bn (med) | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Peak dealer inventory / K | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| P(any suspension day) | 0% | 0% | 0% | 0% | 0% |
| Fire-sale + haircut loss, $bn (med) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| NAV day 30 (med) | 1.000 | 0.923 | 0.845 | 0.690 | 1.000 |

Medians across paths unless stated; p95 = 95th percentile. Run = cumulative redemptions >= 20% of initial supply by day 30.