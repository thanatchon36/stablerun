# E2 tipping point — Issuer A, sector size multiples, 300 paths

Sector size at which the median peak 3M bill-yield impact first exceeds 10 / 25 / 50 bp (log-linear interpolation between simulated sizes 1, 2, 3, 5, 10). 'rails' = redemption processing capacity: calibrated 1.2%/day, fast 5%/day or instant 20%/day.

| Scenario | Impact form | Rails | >10 bp | >25 bp | >50 bp |
|---|---|---|---|---|---|
| loss10 | linear | calibrated | <1x | <1x | <1x |
| loss10 | linear | fast | <1x | <1x | 1.1x |
| loss10 | linear | instant | <1x | <1x | <1x |
| loss10 | sqrt | calibrated | <1x | 1.4x | 5.5x |
| loss10 | sqrt | fast | <1x | 1.9x | 7.5x |
| loss10 | sqrt | instant | <1x | 1.7x | 6.7x |
| scare | linear | calibrated | <1x | <1x | 1.1x |
| scare | linear | fast | 1.8x | 4.4x | 8.8x |
| scare | linear | instant | 1.1x | 2.6x | 5.3x |
| scare | sqrt | calibrated | <1x | 2.0x | 8.1x |
| scare | sqrt | fast | 2.5x | >10x | >10x |
| scare | sqrt | instant | 1.3x | 7.4x | >10x |

Median peak impact (bp) by size:

| Scenario | Impact | Rails | 1x | 2x | 3x | 5x | 10x |
|---|---|---|---|---|---|---|---|
| loss10 | linear | calibrated | 64 | 129 | 193 | 322 | 644 |
| loss10 | linear | fast | 47 | 95 | 142 | 237 | 473 |
| loss10 | linear | instant | 53 | 107 | 160 | 266 | 533 |
| loss10 | sqrt | calibrated | 21 | 30 | 37 | 47 | 67 |
| loss10 | sqrt | fast | 18 | 26 | 32 | 41 | 58 |
| loss10 | sqrt | instant | 19 | 27 | 33 | 43 | 61 |
| scare | linear | calibrated | 44 | 88 | 132 | 220 | 440 |
| scare | linear | fast | 6 | 11 | 17 | 28 | 57 |
| scare | linear | instant | 9 | 19 | 28 | 47 | 94 |
| scare | sqrt | calibrated | 18 | 25 | 30 | 39 | 55 |
| scare | sqrt | fast | 6 | 9 | 11 | 14 | 20 |
| scare | sqrt | instant | 9 | 13 | 16 | 20 | 29 |

Median bills sold outright ($bn) and peak dealer inventory / K, instant rails, loss10:

| Size | 1x | 2x | 3x | 5x | 10x |
|---|---|---|---|---|---|
| Bills sold, $bn | 3 | 5 | 8 | 14 | 27 |
| Dealer inventory / K | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| P(suspension) | 0% | 0% | 0% | 0% | 0% |