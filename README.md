# CAREYONDA

Offline-first astronaut health and spaceflight hazard research platform. M1.1 provides validated observation contracts; M1.2 provides a deterministic synthetic mission simulator and causal feature export. AI reasoning, medical validation, API, and frontend implementations are not included yet.

## Clone and prepare

Python 3.14.8 is the tested runtime; source syntax targets Python 3.11+. Other interpreter versions require validation. The virtual environment and generated datasets are intentionally excluded from Git.

```sh
git clone https://github.com/omar-gaafer/CAREYONDA.git
cd CAREYONDA
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-m1.1-resolved.txt
```

`backend/pyproject.toml` declares runtime/development dependency ranges; the resolved requirements snapshot records the tested M1.1/M1.2 environment. Installation may require network access. Offline provisioning requires separately supplied compatible wheels; no wheel bundle is committed. Simulator execution and tests require no network or cloud service after provisioning.

## Generate M1.2 training artifacts

Run from the repository root:

```sh
PYTHONPATH=backend backend/.venv/bin/python -m simulator.run_simulation \
  --seed 42 --episodes-per-scenario 8 --steps 30 \
  --output datasets/synthetic/m1_2_seed42
```

Choose a new output directory on each run; existing directories are never overwritten. Default output: 5,760 observations, 960 samples, 16 features, and 240 samples per synthetic scenario. Files are `features.csv`, `labels.csv`, `observations.json`, `feature_schema.json`, `evidence_mapping.json`, `manifest.json`, and `README.md`.

Train only on the feature columns listed in `feature_schema.json`, dropping `sample_id`. Join separate labels by ID and split by whole episode using the evidence mapping; random row splits leak overlapping window evidence. Labels and exposure-response relationships are synthetic assumptions, not medical diagnoses or established clinical relationships. No model training is implemented.

## Quality checks

```sh
cd backend
.venv/bin/python -m ruff check app tests ../simulator
.venv/bin/python -m ruff format --check app tests ../simulator
.venv/bin/python -m mypy
.venv/bin/python -m pytest
```

Read [AGENTS.md](AGENTS.md), [coding standards](docs/architecture/CODING_STANDARDS.md), the [M1.1 contract report](docs/architecture/M1.1_UNIFIED_OBSERVATION.md), and the [M1.2 training handoff](docs/architecture/M1.2_TRAINING_PIPELINE.md) before development. The milestone reports retain historical local delivery results; generated artifacts described there are regenerated locally rather than included in the repository.
