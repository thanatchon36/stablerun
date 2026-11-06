# Phase 0 Proposal — When Stablecoins Run: Fire-Sale Spillovers to the Treasury Bill Market

*An agent-based stress test. Status: DRAFT for approval (Phase 0). Date: 2026-11-05.*

## 1. Motivation and gap

Payment stablecoins are now large holders of US Treasury bills, and the GENIUS Act (2025) will push reserves further into bills of ≤93 days [verify]. Existing work measures the *normal-times* link between stablecoin flows and bill yields (Ahmed & Aldasoro 2025 [verify]) or models runs on a single issuer (Ma, Zeng & Zhang 2023; Anadu et al. 2023 [verify]). What is missing is a quantitative bridge between the two: **when a run happens, how much bill-market dislocation does the forced liquidation of reserves cause, and at what sector size does this become a financial-stability problem?** Historical episodes (USDT May 2022, USDC March 2023) are too few and too small for econometrics, so we need a calibrated simulation model.

## 2. Research questions and contribution

- **RQ1** Propagation and size of the spillover: redemption run → reserve liquidation → bill-yield impact (bp) and fire-sale loss.
- **RQ2** The *tipping point*: at which sector size (1×, 2×, 5×, 10× today) does liquidation exceed dealer absorption capacity and move 3M bill yields by more than 10/25/50 bp.
- **RQ3** Ranking of design and policy levers: cash buffer, maturity cap (93d rule), redemption fee/gate, redemption at NAV vs par, Fed backstop (MMLF analogue).
- **RQ4** Validation: the model must reproduce USDC-2023 and USDT-2022 qualitatively and within an order of magnitude.

Contribution: (i) first calibrated agent-based stress test linking stablecoin run dynamics to Treasury-market price impact with an explicit dealer-capacity constraint; (ii) a size-scaling exercise that turns "stablecoins might be systemic one day" into a number; (iii) a policy-lever ranking directly relevant to GENIUS Act implementation and FSB/BIS discussions; (iv) an analytic global-games benchmark that the simulation nests, so results are not a black box.

## 3. Model in one paragraph

Discrete time, daily steps, 30-day horizon (hourly steps for the first 5 days as robustness). **Holders** (N = 10,000, five types) receive a noisy private signal about reserve impairment θ, observe the secondary-market price p and cumulative redemptions R, and exit when a run signal s = w1·(1−p) + w2·x̂ + w3·R exceeds a type-specific threshold (global-games threshold rule). Only authorized redeemers (institutions, arbitrageurs) redeem at par with the issuer; everyone else sells on the **secondary market**, where order imbalance moves p below $1. **Arbitrageurs** buy discounted tokens and redeem at par, subject to daily capital and the issuer's processing capacity — this converts secondary selling into primary redemptions. The **issuer** pays redemptions through a liquidation waterfall (cash → overnight repo/MMF → T-bills shortest-first → other) and suspends when liquid assets run out, which itself feeds the depeg. **Bill-market** impact has permanent and temporary components, calibrated to the outflow elasticity in Ahmed & Aldasoro (2025) [verify], a square-root (baseline) or linear (upper bound) functional form, and a convex penalty once cumulative dealer inventory exceeds capacity K. A share ρ of redeemed cash returns to the bill market via MMFs with a lag, so the system-wide net sale is smaller than gross liquidation. A **second issuer** receives a belief spillover from the first issuer's depeg (contagion).

**Analytic benchmark.** A Goldstein–Pauzner-style global game with a fire-sale liquidation cost c(n) gives a unique run threshold θ*; we show dθ*/dλ > 0 (price impact raises fragility) and that the ABM's run probability converges to the benchmark as herding w3 → 0.

## 4. Calibration and validation

Parameter table with defaults: `config/params_default.yaml` and the summary below. All issuer figures are defaults from public attestations as I remember them and are marked **[verify]**; please confirm or replace before the final run. Validation targets (all [verify]): USDC March 2023 — trough ≈ $0.87–0.88, first-week net redemptions ≈ 12–15% of supply, 30-day ≈ 25%; USDT May 2022 — trough ≈ $0.95 on some venues, ≈ 12% redeemed in two weeks; March 2020 prime MMFs — ≈ $125bn (≈ 15% of AUM) in two weeks with the MMLF arriving around day 10, used as the structural analogue for "other holders" and for the backstop design.

## 5. Experiments

| ID | Design | Output |
|---|---|---|
| E1 Baseline | Issuer-A shock "x% of reserves impaired", x ∈ {5, 10, 20}; ≥1,000 Monte Carlo paths | Redemption and depeg paths, liquidation by asset, 3M bill-yield impact, fire-sale loss, run probability |
| E2 Tipping point | Sector size × {1, 2, 5, 10} | Headline figure: yield impact and dealer-capacity utilisation vs size; size at which 10/25/50 bp are crossed |
| E3 Policy grid | Cash buffer {0,10,20,30%} × fee {0,0.5,1,2%} × maturity cap {93d,180d,none} × Fed backstop {off,on} | Heatmaps and ranked lever table (96 cells; 500 paths each if compute binds) |
| E4 Contagion | Spillover to Issuer B, baseline vs best policy | Second-issuer depeg and redemptions |
| E5 Robustness | sqrt vs linear impact, hourly vs daily, N, herding, ρ; Sobol/Morris global sensitivity | Tornado chart |

## 6. Deliverables and phases

Phase 1 core model + tests + E1 → Phase 2 validation + E2 → Phase 3 E3–E5 → Phase 4 paper.pdf (LaTeX, 15–25 pp), repo.zip, headline chart PNG, 150-word LinkedIn post, references-check list. Files are presented at every phase.

## 7. Feasibility check (sandbox, done today)

Python 3.12 with numpy/scipy/pandas/matplotlib/yaml present; numba, SALib, pytest to be installed from PyPI. LaTeX (pdflatex, xelatex, latexmk) and pandoc are available, so paper.pdf can be compiled here. Constraint: 1 CPU and ~3 GB RAM, so the simulation must be fully vectorised; if the 96-cell policy grid is too slow at 1,000 paths, it runs at 500 paths with the baseline and tipping-point experiments at 1,000. No web access from the sandbox: all figures are from the model or from [verify]-flagged sources.

## 8. Limitations to state in the paper

The model is a stress-testing tool, not a forecast. Behavioural thresholds are calibrated to two episodes only; price impact is extrapolated from small normal-times flows; reserve compositions are point-in-time; the Fed backstop is stylised; no interaction with the bank-deposit channel or repo-market stress beyond the dealer-capacity constraint.

## 9. Decisions needed before Phase 1

- **D1** Issuer defaults: A (large offshore issuer, Tether-like) $180bn; B (US-regulated, Circle-like) $75bn, with the reserve mixes in the table. Use as-is for now, or send the latest attestation figures?
- **D2** Price-impact baseline: square-root (my recommendation; linear reported as upper bound) or linear?
- **D3** Naming: name Tether/Circle as calibration sources but present scenarios as "Issuer A / Issuer B", or name them throughout?
- **D4** (default unless you object) Daily step, 30-day horizon, 1,000 paths; hourly first five days as robustness.

## 10. Parameter defaults (summary)

| Parameter | Default | Source | Confidence |
|---|---|---|---|
| Issuer A supply | $180bn | Tether attestation, mid-2026 [verify] | Low–Med |
| Issuer B supply | $75bn | Circle attestation, mid-2026 [verify] | Low–Med |
| A reserve mix | T-bills 66% (half ≤1M, half 1–3M), reverse repo 10%, MMF 4%, cash 0.5%, other 19.5% | Tether attestation [verify] | Med |
| B reserve mix (look-through) | Cash/deposits 12%, T-bills 40%, overnight repo 48% | Circle attestation / Circle Reserve Fund [verify] | Med |
| Direct-redemption access | A: verified customers, $100k minimum, 0.1% fee; B: Circle Mint institutions, no fee | Issuer terms [verify] | Med |
| Redemption processing cap | $5bn/day per issuer | Assumption (USDC processed ≈ $3.8bn on 13 Mar 2023 [verify]) | Low |
| Bills outstanding / daily volume | $6.5tn / $250bn | Treasury, TRACE [verify] | Med |
| Sell impact (permanent + temporary) | 1.0 + 1.0 bp per $1bn at $3.5bn reference flow, temporary decay 0.3/day | Ahmed & Aldasoro 2025 outflow elasticity [verify] | Med |
| Buy impact | 0.5 bp per $1bn | A&A 2025 asymmetry [verify] | Med |
| Impact functional form | sqrt baseline, linear upper bound | Square-root law literature | Design |
| Dealer capacity K / convexity γ | $150bn / 2 | Assumption | Low |
| Reinvestment share ρ / lag | 0.5 / 2 days | Assumption | Low |
| Holder type shares | Retail 30%, exchanges & MMs 30%, DeFi 20%, institutional 15%, arbitrageurs 5% | Assumption | Low |
| Signal noise σ | 0.05 | Assumption, varied in E5 | Low |
| Run-signal weights w1, w2, w3 | 1.0, 1.0, 0.5 | Calibrated to episodes | Low |
| Arbitrage cost / daily capital | 0.2% / $2bn | Assumption | Low |
| Belief spillover β | 0.3 | Assumption, varied in E4 | Low |
| Fed backstop (on) | Impact halved and K unbounded from day 2 | MMLF analogue, March 2020 [verify] | Design |

Citations to verify: `docs/references_to_verify.md`.
