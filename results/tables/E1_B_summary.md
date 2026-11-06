# E1 baseline — Issuer B, 1000 Monte Carlo paths, 30 business days

Supply $75bn; impact form `sqrt`; processing cap 3.0% of supply per day; arbitrage capital 3.0% of supply per day. All inputs are Phase-1 defaults (uncalibrated); see config/params_default.yaml.

Scenarios: `control` = 0% of reserves at risk, 100% of it lost; `loss05` = 5% of reserves at risk, 100% of it lost; `loss10` = 10% of reserves at risk, 100% of it lost; `loss20` = 20% of reserves at risk, 100% of it lost; `scare08` = 8% of reserves at risk, 0% of it lost, resolved on day 2

| Metric | control | loss05 | loss10 | loss20 | scare08 |
|---|---|---|---|---|---|
| Min price (med) | 0.998 | 0.607 | 0.500 | 0.500 | 0.904 |
| Redeemed day 7 | 1.9% | 21.0% | 21.0% | 21.0% | 18.0% |
| Redeemed day 30 | 2.3% | 90.0% | 90.0% | 80.0% | 24.0% |
| P(run >=20%) | 0% | 100% | 100% | 100% | 99% |
| P(run >=50%) | 0% | 100% | 100% | 100% | 0% |
| Peak 3M bill impact, bp (med) | 0.0 | 0.6 | 8.6 | 12.6 | 1.8 |
| Peak impact, bp (p95) | 0.0 | 0.6 | 8.6 | 12.6 | 1.8 |
| P(impact >10bp) | 0% | 0% | 0% | 100% | 0% |
| Bills sold outright, $bn (med) | 0.0 | 0.4 | 4.3 | 7.7 | 0.0 |
| Maturing bills not rolled, $bn (med) | 0.0 | 25.9 | 25.7 | 22.3 | 7.1 |
| Peak net bill demand withdrawn, $bn (med) | 0.0 | 0.1 | 2.5 | 4.7 | 0.9 |
| Other assets sold, $bn (med) | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Peak dealer inventory / K | 0.00 | 0.00 | 0.01 | 0.01 | 0.00 |
| P(any suspension day) | 0% | 0% | 100% | 100% | 0% |
| Fire-sale + haircut loss, $bn (med) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| NAV day 30 (med) | 1.000 | 0.500 | 0.000 | 0.000 | 1.000 |

Medians across paths unless stated; p95 = 95th percentile. Run = cumulative redemptions >= 20% of initial supply by day 30.