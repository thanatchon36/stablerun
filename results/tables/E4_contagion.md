# E4 contagion — Issuer A shock, belief spillover to Issuer B (300 paths)

Issuer B's holders add beta x (1 - price_A) to their expected-loss belief. Combined impact = persistent component on the sum of both issuers' net demand withdrawn.

| A scenario | beta | B redeemed day 7 | B redeemed day 30 | B min price | P(B run) | A peak impact, bp | Combined persistent impact, bp |
|---|---|---|---|---|---|---|---|
| scare | 0.0 | 2.0% | 2.3% | 0.998 | 0% | 17.5 | 17.5 |
| scare | 0.3 | 14.0% | 14.0% | 0.967 | 9% | 17.5 | 17.5 |
| scare | 0.6 | 21.0% | 30.0% | 0.908 | 100% | 17.5 | 17.5 |
| loss10 | 0.0 | 2.0% | 2.3% | 0.998 | 0% | 21.2 | 21.2 |
| loss10 | 0.3 | 21.0% | 70.1% | 0.879 | 100% | 21.2 | 21.3 |
| loss10 | 0.6 | 21.0% | 90.0% | 0.819 | 100% | 21.2 | 21.2 |