> Local Model A integration checkpoint: this branch includes a documented snapshot
> of previously uncommitted M2/M3/M4.2/frontend development over `bfc19cb`, plus
> M-A.1–M-A.5 integration. It is not a merged upstream baseline. See
> [checkpoint provenance and reproduction](docs/architecture/MODEL_A_CHECKPOINT.md).

# CAREYONDA

Offline-first astronaut health and spaceflight hazard research platform. M1.1 provides validated observation contracts; M1.2 provides a deterministic synthetic mission simulator and causal feature export. The local working tree also includes deterministic M2 reasoning, a synthetic local REST API, and a React frontend with fixture/API modes. Trained models and medical validation are not provided.

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

## NASA RR-1 and training handoff

The development branch `feature/hazard-reasoning` also contains the D2/D3 local NASA adapters and a separate ISS environmental feature exporter. See the [actual implementation inventory](docs/architecture/AI_IMPLEMENTATION_STATUS.md) and [training handoff](docs/architecture/TRAINING_HANDOFF.md) for exact schemas, commands, and model readiness. Branch changes require review/merge before becoming available on `main`.

The three original NASA CSVs must be provisioned separately under `datasets/raw/nasa_eda/`; redistribution permission for the supplied copies has not been verified, so they are not committed. Once appropriately authorized copies are available:

```sh
PYTHONPATH=backend backend/.venv/bin/python -m app.ingestion.nasa_rr1_export \
  --raw datasets/raw/nasa_eda \
  --output datasets/processed/nasa_rr1_eda_d2d3_validated
```

Use a new output directory. Real NASA environment features and synthetic scenario features remain separate; no paired human-health dataset or trained model is claimed. Local M2 reasoning work is intentionally excluded from this data-integration synchronization.

## Local API and connected frontend (M3)

The working tree includes a loopback-only synthetic FastAPI service and explicit fixture/API frontend modes. See [local API v1](docs/api/LOCAL_API_V1.md) for backend startup and [frontend integration](frontend/PHASE3_INTEGRATION.md) for the connected demonstration. This extends the historical milestone status above; no trained models, medical validation, authentication or persistent investigation retrieval is claimed.
