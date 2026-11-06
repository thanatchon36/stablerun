# Phase 1 notes — core model, tests and baseline (E1)

Status: Phase 1 delivered 2026-11-05. All numbers below come from `config/params_default.yaml` v0.2
with **uncalibrated** behavioural parameters; Phase 2 fits them to the USDC-2023 and USDT-2022 episodes.

## 1. Model as implemented (daily steps, 30 business days, vectorised over Monte Carlo paths)

Holders i (N = 10,000; five types; holdings lognormal within type) see a public expected-loss share
`belief_t = L_t / S_t` (L = loss publicly known, S = remaining supply: the loss concentrates on those who stay),
a private signal `x_i = belief_t + eps_i` (eps fixed per agent, sd 0.02), the price `p_{t-1}`, a herding
state `H_t = 0.6 H_{t-1} + exit flow_t / S_0`, a suspension flag, and a common daily sentiment shock `nu_t`.

- exit signal   `s_i = w2 x_i + w3 H + w4 1[susp] + nu_t + w1 (1 - p_{t-1})`, exit if `s_i > theta_i` and the agent
  pays attention that day (type-specific attention probabilities spread decisions over days)
- re-entry      exited agents whose core signal (same without the depeg term) falls below `theta_i - 0.02`
  buy back at the market price; this demand at par absorbs the secondary-market overhang first
- routing       institutional and arbitrageur holders redeem directly at par (queue); others sell on the
  secondary market
- secondary market  offered = new sales + overhang held by dip buyers; re-entry demand is served first,
  then arbitrageurs buy `min(offered, daily capital, room in the redemption queue within 2 days)` and
  redeem at par; the rest stays as overhang. `price = 1 - belief - (c 1[offered>0] + eta overhang/S_0 + delta 1[susp])`
- issuer        bill ladder run-off (uniform; tb1 matures in 21 days, tb3 rolls into tb1 over 42 days) adds
  cash; processes `min(queue, cap)` through the waterfall cash -> repo -> MMF -> bills (shortest first,
  grossed up for the price concession) -> other (30% haircut); shortfall = suspension that day; surplus cash
  above the initial cash level is rolled back into bills unless there is a backlog beyond one day's capacity
- bill market   persistent impact `Y_P = lam_p g(C) m`, with `C` = cumulative bills sold + maturities not rolled
  - MMF reinvestment (rho = 0.5 of redemptions after 2 days); temporary impact `Y_T = 0.7 Y_T + lam_t g(sold) m`;
  dealer inventory `I = 0.9 I + sold - buys`, multiplier `m = 1 + (I/K)^2`; `g` is linear up to the $3.5bn
  anchor and square-root beyond it (approved D2), with `linear` as the upper bound
- fire-sale loss  bills sold x duration x yield deviation (bucket durations 0.04y and 0.17y), plus the haircut
  on other assets; NAV marks bills at the current concession

## 2. Changes relative to the Phase 0 table (all assumptions, flagged for Phase 2)

| Item | Phase 0 | Phase 1 | Why |
|---|---|---|---|
| Sell impact, persistent | 1.0 bp/$bn | 2.0 bp/$bn on cumulative net demand withdrawn | Matches the ~7 bp 10-day effect of a $3.5bn outflow in the A&A anchor [verify] |
| Impact shape | sqrt | linear below $3.5bn, sqrt above | Pure sqrt has infinite slope at small flows |
| Signal noise sd | 0.05 | 0.02 | At 0.05 the no-shock control produced a 30% run from noise alone |
| Depeg weight w1 | 1.0 | 0.5 | Price already embeds the public loss share; avoids double counting |
| Herding weight w3 | 0.5 on cumulative redemptions | 0.3 on a decaying exit-flow state | Level-based herding never switched off |
| Liquidity depth eta | 0.02 (flow) | 0.2 on the overhang stock | Stock-based inventory discount; calibrated in Phase 2 |
| New | — | attention rates, holding dispersion, re-entry hysteresis 0.02, aggregate noise sd 0.005 | Needed for realistic timing and path variation |
| New | — | non-rollover channel (`withdrawn`) | With a 2.8%/day processing cap, Issuer A never sells bills; demand is withdrawn at auction instead |
| Processing cap / arbitrage capital | $5bn, $2bn absolute | shares of supply (A: 2.8%, 1.1%; B: 7%, 2.7% per day) | So that E2 size scaling keeps issuer behaviour fixed and isolates the market |

## 3. What E1 shows (Issuer A, 1,000 paths, uncalibrated)

- With a realised loss of 5-20% the run is certain: ~20% of supply is redeemed in week 1 (the processing
  cap binds), ~47-50% by day 30 (arbitrage capital binds); the price settles at `1 - loss share - liquidity`
  and keeps falling as the loss concentrates on remaining holders (first-come-first-served).
- The USDC-style scare (8% exposure resolved on day 3) produces a 0.83 trough, 20% redeemed in week 1 and
  26% by day 30, then full recovery as re-entrants absorb the overhang. Targets [verify]: 0.87-0.88, 12-15%,
  25%. So the trough is too deep and week 1 too fast: Phase 2 knobs are eta, the processing cap, the
  arbitrage capital share, thresholds and attention.
- Issuer A sells **no bills outright** in any scenario: $26bn of liquid assets plus $2.8bn/day of run-off
  cover a throttled run. The bill-market effect comes from $68-72bn of maturities not rolled over, half of
  which returns via MMFs: peak impact ~19 bp (sqrt), fire-sale loss ~0. Issuer B (no "other" cushion,
  faster cap) does sell $7-13bn of bills, is drained within the month in the loss scenarios and suspends.
- Fire-sale losses on bills are negligible because bill duration is tiny; fragility comes from the
  realised loss, the processing queue and the secondary-market overhang, while the externality falls on the
  Treasury market (yield impact, dealer capacity) rather than on the issuer. This is a candidate headline.

## 4. Known limitations to fix or state

- No inflows (new minting) in normal times: the no-shock control therefore shows a 2% monthly net outflow
  and 2-5 bp of impact; stress effects should be read relative to the control.
- Monte Carlo variation is small (law of large numbers over 10,000 agents); dispersion comes from the common
  sentiment shock and, in Phase 3, from parameter uncertainty (E5).
- Direct-access holders can re-enter while their claim is still queued (minor inconsistency).
- Hourly intraday dynamics, the second issuer (E4) and policies (E3) are wired in the config but not yet run.
