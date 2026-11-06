# Changelog

## v0.3.1 (2026-11-06)

- Paper and README: redeeming at net asset value rather than par **cuts the depeg by a third**, not by half. In the
  solvency run at five times today's size the price trough rises from 0.75 to 0.83 (depeg 25.3% to 16.9%), as
  Table 4 already showed; the abstract, introduction and discussion now say so.
- E3 summary header and the `run_e3` default now state the 200 paths per cell that `run_all.py` uses (the paper
  was already right).
- LinkedIn poster (`scripts/make_linkedin_poster.py`) and post; Hugging Face dataset card
  (`docs/hf_dataset_card.md`, built by `scripts/make_hf_dataset.py`).
- Package version aligned across `pyproject.toml`, `CITATION.cff` and `stablerun.__version__`.
- No simulation result changed.

## v0.3.0 (2026-11-06)

- First archived release: calibrated agent-based model, experiments E1 to E5, closed-form benchmark and calibration
  validation, and the 23-page working paper. DOI 10.5281/zenodo.23996044.
- Figures in one house style, booktabs tables generated from `results/tables`, arXiv bundle script.
- Simulation outputs on Hugging Face: `thanatchon36/stablerun`.
