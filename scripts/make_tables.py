"""Build the LaTeX tables in paper/tables from results/tables and the config (reproducible tables)."""
import sys
from pathlib import Path
import pandas as pd, yaml
ROOT = Path(__file__).resolve().parents[1]
T, OUT = ROOT / "results" / "tables", ROOT / "paper" / "tables"
OUT.mkdir(parents=True, exist_ok=True)

def write(name, lines): (OUT / name).write_text("\n".join(lines) + "\n", encoding="utf-8")

# Table: E1 baseline, Issuer A and B
for iss in ["A", "B"]:
    s = pd.read_csv(T / f"E1_{iss}_summary.csv", index_col=0)
    rows = [("Minimum token price (median)", "min_price_med", "{:.3f}"), ("Redeemed by day 7", "R_day7_med", "{:.1%}"),
            ("Redeemed by day 30", "R_end_med", "{:.1%}"), ("P(redemptions $\\geq$ 20\\%)", "run_prob", "{:.0%}"),
            ("P(redemptions $\\geq$ 50\\%)", "severe_run_prob", "{:.0%}"), ("Peak 3M bill-yield impact, bp (median)", "peak_Y_bp_med", "{:.1f}"),
            ("Peak impact, bp (95th pct.)", "peak_Y_bp_p95", "{:.1f}"), ("Bills sold outright, \\$bn", "bills_sold_med", "{:.1f}"),
            ("Maturing bills not rolled, \\$bn", "withdrawn_med", "{:.1f}"), ("Peak net bill demand withdrawn, \\$bn", "net_demand_withdrawn_med", "{:.1f}"),
            ("Other assets sold, \\$bn", "other_sold_med", "{:.1f}"), ("P(any suspension day)", "susp_any", "{:.0%}"),
            ("Fire-sale and haircut loss, \\$bn", "fs_loss_med", "{:.2f}"), ("NAV on day 30 (median)", "nav_end_med", "{:.3f}")]
    cols = ["control", "loss05", "loss10", "loss20", "scare08"]
    head = ["No shock", "5\\% loss", "10\\% loss", "20\\% loss", "8\\% exposure, resolved"]
    L = ["\\begin{tabular}{l" + "r" * 5 + "}", "\\toprule", "Metric & " + " & ".join(head) + " \\\\", "\\midrule"]
    for lab, k, f in rows:
        L.append(lab + " & " + " & ".join(f.format(s.loc[c, k]).replace("%", "\\%") for c in cols) + " \\\\")
    L += ["\\bottomrule", "\\end{tabular}"]
    write(f"e1_{iss}.tex", L)

# Table: calibration validation
v = pd.read_csv(T / "calibration_validation.csv")
L = ["\\begin{tabular}{llrrr}", "\\toprule", "Episode & Target & Observed (tol.) & Model & $z$ \\\\", "\\midrule"]
names = {"min_price": "Minimum price", "R_day5": "Redeemed, 5 business days", "R_day22": "Redeemed, 22 business days", "R_day10": "Redeemed, 10 business days"}
for _, r in v.iterrows():
    ep = "USDC, March 2023 (Issuer B)" if r["episode"] == "usdc_2023" else "USDT, May 2022 (Issuer A)"
    L.append(f"{ep} & {names[r['target']]} & {r['observed']:.3f} ({r['tolerance']:.3f}) & {r['model']:.3f} & {r['z']:+.1f} \\\\")
L += ["\\bottomrule", "\\end{tabular}"]
write("validation.tex", L)

# Table: E2 peaks and crossings
e2 = pd.read_csv(T / "E2_tipping_point.csv"); cr = pd.read_csv(T / "E2_crossings.csv")
sizes = sorted(e2["size"].unique())
L = ["\\begin{tabular}{lll" + "r" * len(sizes) + "rrr}", "\\toprule",
     "Scenario & Impact & Rails & " + " & ".join(f"{int(s)}$\\times$" for s in sizes) + " & $>$10 bp & $>$25 bp & $>$50 bp \\\\", "\\midrule"]
for (sc, form, rails), g in e2.groupby(["scenario", "impact", "rails"]):
    g = g.sort_values("size"); c = cr[(cr.scenario == sc) & (cr.impact == form) & (cr.rails == rails)].iloc[0]
    scn = "Liquidity run" if sc == "scare" else "Solvency run"
    L.append(f"{scn} & {form} & {rails} & " + " & ".join(f"{v:.0f}" for v in g["peak_Y_bp_med"]) + f" & {c['size_10bp']} & {c['size_25bp']} & {c['size_50bp']} \\\\".replace("x", "$\\times$"))
L += ["\\bottomrule", "\\end{tabular}"]
write("e2.tex", L)

# Table: E3 main effects
e3 = pd.read_csv(T / "E3_policy_grid.csv"); e3["maturity_cap"] = e3["maturity_cap"].astype(str).str.replace(".0", "", regex=False)
L = ["\\begin{tabular}{llrrrr|rrrr}", "\\toprule", " & & \\multicolumn{4}{c}{Liquidity run, 1$\\times$, calibrated rails} & \\multicolumn{4}{c}{Solvency run, 5$\\times$, fast rails} \\\\",
     "Lever & Level & Impact, bp & Redeemed d30 & Min price & Bills sold & Impact, bp & Redeemed d30 & Min price & Bills sold \\\\", "\\midrule"]
levers = [("cash_buffer", "Cash buffer", lambda v: f"{float(v):.0%}"), ("fee", "Redemption fee", lambda v: f"{float(v):.1%}"),
          ("maturity_cap", "Maturity cap", lambda v: {"93": "93 d", "180": "180 d", "none": "none"}[v]), ("backstop", "Fed backstop", lambda v: "on" if v else "off")]
grid = e3[~e3.cash_buffer.astype(str).isin(["par", "nav"])].copy(); grid["cash_buffer"] = grid["cash_buffer"].astype(float)
for key, lab, fmt in levers:
    for lvl in grid[key].unique():
        cells = []
        for cname in ["scare_1x_calibrated", "loss10_5x_fast"]:
            h = grid[(grid.config == cname) & (grid[key] == lvl)]
            cells += [f"{h['peak_Y_bp_med'].mean():.1f}", f"{h['R_end_med'].mean():.1%}", f"{h['min_price_med'].mean():.3f}", f"{h['bills_sold_med'].mean():.0f}"]
        L.append((f"{lab} & {fmt(lvl)} & " + " & ".join(cells)).replace("%", "\\%") + " \\\\")
nav = e3[e3.cash_buffer.astype(str).isin(["par", "nav"])]
for basis in ["par", "nav"]:
    cells = []
    for cname in ["scare_1x_calibrated", "loss10_5x_fast"]:
        h = nav[(nav.config == cname) & (nav.cash_buffer == basis)].iloc[0]
        cells += [f"{h['peak_Y_bp_med']:.1f}", f"{h['R_end_med']:.1%}", f"{h['min_price_med']:.3f}", f"{h['bills_sold_med']:.0f}"]
    L.append(f"Redemption basis & {basis} & " + " & ".join(cells).replace("%", "\\%") + " \\\\")
L += ["\\bottomrule", "\\end{tabular}"]
write("e3.tex", L)

# Table: E4
e4 = pd.read_csv(T / "E4_contagion.csv")
L = ["\\begin{tabular}{lrrrrrr}", "\\toprule", "Shock to A & $\\beta$ & B redeemed d7 & B redeemed d30 & B min price & P(B run) & Combined impact, bp \\\\", "\\midrule"]
for _, r in e4.iterrows():
    L.append(f"{'Liquidity run' if r['scenario_A']=='scare' else 'Solvency run'} & {r['beta']:.1f} & {r['B_R_day7']:.1%} & {r['B_R_end']:.1%} & {r['B_min_price']:.3f} & {r['B_run_prob']:.0%} & {r['combined_persistent_Y']:.1f} \\\\".replace("%", "\\%"))
L += ["\\bottomrule", "\\end{tabular}"]
write("e4.tex", L)

# Table: benchmark
b = pd.read_csv(T / "benchmark_check.csv")
L = ["\\begin{tabular}{rrr}", "\\toprule", "Loss share & ABM exit share & Closed form \\\\", "\\midrule"]
for _, r in b.iterrows():
    L.append(f"{r['exposure']:.0%} & {r['abm_exit_share']:.1%} & {r['closed_form_exit_share']:.1%} \\\\".replace("%", "\\%"))
L += ["\\bottomrule", "\\end{tabular}"]
write("benchmark.tex", L)

# Table: parameters (appendix) from config
c = yaml.safe_load(open(ROOT / "config" / "params_default.yaml"))
A, B, M, H, S = c["issuers"]["A"], c["issuers"]["B"], c["bill_market"], c["holders"], c["secondary_market"]
rows = [
 ("Issuer A supply, \\$bn", f"{A['supply']:.0f}", "attestation, mid-2026 [verify]"),
 ("Issuer B supply, \\$bn", f"{B['supply']:.0f}", "attestation, mid-2026 [verify]"),
 ("A reserves: cash / repo / MMF / bills $\\leq$1M / 1--3M / other", " / ".join(f"{A['reserves'][k]:.1%}" for k in ["cash_deposits","reverse_repo","mmf_shares","tbills_le_1m","tbills_1_3m","other"]), "attestation [verify]"),
 ("B reserves: cash / repo / MMF / bills $\\leq$1M / 1--3M / other", " / ".join(f"{B['reserves'][k]:.1%}" for k in ["cash_deposits","reverse_repo","mmf_shares","tbills_le_1m","tbills_1_3m","other"]), "reserve report, look-through [verify]"),
 ("Other-asset fire-sale haircut", f"{A['other_asset_haircut']:.0%}", "assumption"),
 ("Bill ladder (tb1 / tb3 days)", f"{A['ladder_days']['tb1']} / {A['ladder_days']['tb3']}", "assumption"),
 ("Processing capacity, A / B (share of supply per day)", f"{A['redemption']['processing_cap_share_per_day']:.1%} / {B['redemption']['processing_cap_share_per_day']:.1%}", "calibrated"),
 ("Arbitrage capital, A / B (share of supply per day)", f"{A['redemption']['arbitrage_capital_share_per_day']:.1%} / {B['redemption']['arbitrage_capital_share_per_day']:.1%}", "calibrated"),
 ("Redemption fee, A / B", f"{A['redemption']['fee']:.1%} / {B['redemption']['fee']:.1%}", "issuer terms [verify]"),
 ("Cash hoarding horizon, days", f"{A['cash_hoard_days']}", "assumption"),
 ("Impact anchor flow, \\$bn", f"{M['impact']['reference_flow']}", "Ahmed--Aldasoro [verify]"),
 ("Persistent / temporary sell impact, bp per \\$bn at anchor", f"{M['impact']['sell_permanent_bp_per_bn']} / {M['impact']['sell_temporary_bp_per_bn']}", "Ahmed--Aldasoro outflow range [verify]"),
 ("Buy impact, bp per \\$bn", f"{M['impact']['buy_bp_per_bn']}", "asymmetry [verify]"),
 ("Temporary impact decay per day", f"{M['impact']['temporary_decay_per_day']}", "assumption"),
 ("Impact shape", M['impact']['functional_form'] + " (linear below anchor)", "square-root law"),
 ("Dealer capacity $K$, \\$bn / convexity $\\gamma$ / absorption per day", f"{M['dealers']['capacity_K']:.0f} / {M['dealers']['convexity_gamma']} / {M['dealers']['absorption_per_day']}", "assumption"),
 ("MMF reinvestment share $\\rho$ / lag, days", f"{M['reinvestment']['share_rho']} / {M['reinvestment']['lag_days']}", "assumption"),
 ("Bill durations sold, years (tb1 / tb3)", f"{M['duration_years']['tb1']} / {M['duration_years']['tb3']}", "bucket midpoints"),
 ("Agents $N$", f"{H['n_agents']:,}", "design"),
 ("Holder type shares of supply (retail / exch. / DeFi / inst. / arb.)", " / ".join(f"{H['type_shares'][t]:.0%}" for t in ["retail","exchange_mm","defi","institutional","arbitrageur"]), "assumption"),
 ("Attention probabilities per day", " / ".join(f"{H['attention'][t]:.2f}" for t in ["retail","exchange_mm","defi","institutional","arbitrageur"]), "assumption"),
 ("Exit threshold means", " / ".join(f"{H['thresholds'][t]['mean']:.2f}" for t in ["retail","exchange_mm","defi","institutional","arbitrageur"]), "calibrated (scale 1.0)"),
 ("Exit threshold s.d.", " / ".join(f"{H['thresholds'][t]['sd']:.2f}" for t in ["retail","exchange_mm","defi","institutional","arbitrageur"]), "assumption"),
 ("Signal weights $w_1, w_2, w_3, w_4$", f"{H['run_signal_weights']['w1_depeg']}, {H['run_signal_weights']['w2_private']}, {H['run_signal_weights']['w3_herding']}, {H['run_signal_weights']['w4_suspension']}", "calibrated / assumption"),
 ("Private-signal s.d. / common shock s.d.", f"{H['signal_noise_sigma']} / {H['aggregate_noise_sigma']}", "assumption"),
 ("Herding memory / re-entry hysteresis", f"{H['herding_memory']} / {H['reentry_hysteresis']}", "assumption"),
 ("Loss probability $\\psi$", f"{H['exposure_loss_probability']}", "calibrated"),
 ("Liquidity depth $\\eta$ / arbitrage cost / horizon, days", f"{S['liquidity_depth_eta']} / {S['arbitrage_cost']} / {S['arbitrage_horizon_days']}", "calibrated / assumption"),
 ("Suspension discount / price floor", f"{S['suspension_discount']} / {S['price_floor']}", "assumption"),
 ("Belief spillover $\\beta$ (E4)", "0, 0.3, 0.6", "assumption"),
]
L = ["\\begin{tabular}{p{6.9cm}p{4.5cm}p{3.2cm}}", "\\toprule", "Parameter & Value & Source \\\\", "\\midrule"]
L += [f"{a} & {b} & {c_} \\\\".replace("%", "\\%") for a, b, c_ in rows]
L += ["\\bottomrule", "\\end{tabular}"]
write("params.tex", L)
print("tables:", sorted(p.name for p in OUT.iterdir()))
