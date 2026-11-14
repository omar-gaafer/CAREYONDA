# Training handoff — D2/D3 synchronization

## Branch and scope

Repository: https://github.com/omar-gaafer/CAREYONDA.git
Development branch: `feature/hazard-reasoning`. Expected parent: `bdb29e5f0b9d4b07870cf0423c7e5a454f74cf8f`. This commit contains D2/D3, the implementation inventory, and this handoff; M2 reasoning changes remain outside the commit. The branch needs review/merge before these changes become available on `main`. No remote work is overwritten.

The team confirmed these training roles: **Model A — NASA Environmental Anomaly Detection**, an unsupervised Isolation Forest trained on real NASA RR-1 CO2, temperature, and humidity features; **Model B — Synthetic Multimodal Health Anomaly Detection**, an unsupervised Isolation Forest trained on CAREYONDA synthetic physiological and mission-context features, evaluated against synthetic scenario labels. Neither model nor its training framework is implemented or installed yet. The existing feature schemas below remain unchanged.

## Clone or update

Fresh checkout:

```sh
git clone --branch feature/hazard-reasoning https://github.com/omar-gaafer/CAREYONDA.git
cd CAREYONDA
```

For an existing clean checkout (preserve/stash personal work before changing branches):

```sh
git fetch origin
git switch feature/hazard-reasoning
git pull --ff-only origin feature/hazard-reasoning
```

If the local branch does not exist, `git switch --track origin/feature/hazard-reasoning` creates it instead. Do not copy unfinished local M2 files into this data-integration checkout.

## Dependencies

Python 3.14.8 is tested; source syntax targets 3.11+. Minimum-version runtime compatibility has not been verified. The existing tested dependency snapshot includes Pydantic and development tools, not a model training framework.

```sh
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-m1.1-resolved.txt
```

`backend/pyproject.toml` is the declared dependency source; the snapshot captures the tested resolved environment. No framework is installed by this synchronization. Installation may need network access; execution is offline once dependencies are provisioned. A fully offline installation requires a separately provisioned compatible wheel bundle.

## Reproduce synthetic data (Model B)

From the repository root:

```sh
PYTHONPATH=backend backend/.venv/bin/python -m simulator.run_simulation \
  --seed 42 --episodes-per-scenario 8 --steps 30 \
  --output datasets/synthetic/m1_2_seed42
```

Defaults produce 5,760 observations, 960 samples, 16 features, and 240 samples per scenario. Train Model B without labels using the listed predictors from `features.csv`. Join `labels.csv` by `sample_id` only for held-out evaluation against `synthetic_scenario`; do not use those labels as fitting targets or predictors. Drop sample IDs from predictors; never use label-bearing provenance or mapping context as predictors. Split by whole episode using `evidence_mapping.json`, preferably holding out a separate seed. Fit preprocessing only on training. Labels and physiological relationships are toy generator assumptions, not medical diagnoses or validated causation. This is unsupervised detection of synthetic multimodal deviations, evaluated using scenario assignments. Scenario labels are evaluation annotations, not proof that every non-baseline sample is anomalous; any binary mapping and evaluation protocol must be documented by the training developer.

## Transfer and reproduce NASA data (Model A)

No local license or redistribution permission accompanying these CSV copies was found. No assertion about general NASA licensing is made. Do not force-add ignored files or upload/share them publicly without verifying applicable source permissions. A teammate needs separately provisioned, appropriately authorized copies of:

- `RR-1_EDA_Telemetry_table.csv`
- `RR-1_EDA_Radiation_table.csv`
- `RR-1_EDA_Summary_table.csv`

Place the originals in `datasets/raw/nasa_eda/` (create that directory if necessary). Coordinate transfer through the team's authorized channel after checking access/redistribution permissions; this task does not send the files. A clone alone cannot regenerate the NASA dataset until those files are supplied. Expected local source fingerprints:

| File | Bytes | SHA-256 |
| --- | --- | --- |
| `RR-1_EDA_Radiation_table.csv` | 1683 | `15be9a9d0166eaf1d03bac0fe6056926574a1de5c4822262092a4806a93c27a1` |
| `RR-1_EDA_Summary_table.csv` | 700 | `968829a6335fcc10e014eb42a83e03d677da42993ef686865081fccfe95442b1` |
| `RR-1_EDA_Telemetry_table.csv` | 856347 | `1117dd51b7e869119b0426dd1a57c7c42a0a4edf502b7b18a8a280f0b7d0c531` |

```sh
PYTHONPATH=backend backend/.venv/bin/python -m app.ingestion.nasa_rr1_export \
  --raw datasets/raw/nasa_eda \
  --output datasets/processed/nasa_rr1_eda_d2d3_validated
```

Both exporters require a new output directory and refuse to overwrite existing data. For reruns, choose another output path. Raw data, virtual environments, processed/synthetic datasets, caches, credentials, and model artifacts remain ignored.

NASA output: 12,087 environmental samples; train 8,460, validation 1,813, test 1,814. Read the three split CSVs independently. They contain 16 predictors plus `sample_id` and `event_time_utc` metadata, which must be dropped from model inputs. Use `feature_schema.json` for exact names and units; fit preprocessing only on train. Train is not assumed anomaly-free. No anomaly ground-truth labels are supplied.

Telemetry `Controller_Time_GMT` is interpreted as UTC+00:00 and exact raw tokens are retained. Sampling is irregular; actual timestamps drive windows. Ground control is separate and excluded from ISS features. CO2 remains ppm, never converted to partial pressure without total pressure. Radiation is retained as a daily side series, not interpolated into telemetry. Its date boundary/timezone is assumed and flagged suspect. Accumulated-dose units are unconfirmed: original tokens remain in the sidecar and typed accumulated values are unavailable/excluded. All 45 comparable NASA summary statistics match at printed precision; the accumulated row is not comparable because of its unit conflict.

## Exact Model A input schema — real NASA environment

Machine-readable copy: [NASA_ENVIRONMENT_FEATURE_SCHEMA.json](NASA_ENVIRONMENT_FEATURE_SCHEMA.json), generated from `environmental_schema()`. Feature CSV order:

| Feature | Unit | Nullable |
| --- | --- | --- |
| `cabin_co2_concentration_value` | ppm | yes |
| `cabin_co2_concentration_mean_30m` | ppm | yes |
| `cabin_co2_concentration_delta` | ppm | yes |
| `cabin_co2_concentration_count_30m` | 1 | no |
| `cabin_co2_concentration_missing` | 1 | no |
| `environment_temperature_value` | degC | yes |
| `environment_temperature_mean_30m` | degC | yes |
| `environment_temperature_delta` | degC | yes |
| `environment_temperature_count_30m` | 1 | no |
| `environment_temperature_missing` | 1 | no |
| `relative_humidity_value` | % | yes |
| `relative_humidity_mean_30m` | % | yes |
| `relative_humidity_delta` | % | yes |
| `relative_humidity_count_30m` | 1 | no |
| `relative_humidity_missing` | 1 | no |
| `gap_seconds` | s | yes |

Windows are `(t-1800 seconds,t]` and reset at each chronological split boundary. Means are arithmetic sample means, not time-weighted. Delta means current minus most recent earlier valid reading inside the window. Count/missing are unitless; gap is actual elapsed time since the preceding sample in the same split. Nulls stay null. No future or cross-split observation enters these features.

## Exact Model B input schema — synthetic multimodal health anomalies

Machine-readable copy: [SYNTHETIC_FEATURE_SCHEMA.json](SYNTHETIC_FEATURE_SCHEMA.json), generated from `feature_schema(300)`. CSV order:

| Feature | Unit | Nullable |
| --- | --- | --- |
| `heart_rate_latest` | bpm | yes |
| `heart_rate_missing` | 1 | no |
| `heart_rate_mean` | bpm | yes |
| `cabin_co2_partial_pressure_latest` | Pa | yes |
| `cabin_co2_partial_pressure_missing` | 1 | no |
| `cabin_co2_partial_pressure_mean` | Pa | yes |
| `sleep_duration_latest` | h | yes |
| `sleep_duration_missing` | 1 | no |
| `sleep_duration_mean` | h | yes |
| `fatigue_self_report_latest` | 1 | yes |
| `fatigue_self_report_missing` | 1 | no |
| `communication_delay_latest` | s | yes |
| `communication_delay_missing` | 1 | no |
| `communication_delay_mean` | s | yes |
| `exercise_active_latest` | 1 | yes |
| `exercise_active_missing` | 1 | no |

The only non-predictor column in `features.csv` is `sample_id`. Fatigue encoding: rested=0, tired=1, very_tired=2. Exercise encoding: false=0, true=1. Synthetic windows are `(t-300 seconds,t]`; means use only evaluated-valid observations and missing flags indicate no usable value in the window. Event-time processing is retrospective and does not guarantee online arrival-time availability. Never join the NASA ppm features with synthetic Pa/physiology features and claim they are paired observations.

## Quality and M1.3 readiness

From `backend`:

```sh
.venv/bin/python -m ruff check app tests ../simulator
.venv/bin/python -m ruff format --check app tests ../simulator
.venv/bin/python -m mypy
.venv/bin/python -m pytest
```

The local full tree includes M2-only tests, so its count differs from the deliberately M2-free committed snapshot. Final verification counts for each are recorded in the synchronization report. The local NASA-file test skips if raw files have not been separately supplied. Fixture tests run without any NASA download.

Data/contracts are ready for M1.3 experiments; model implementation/training/evaluation is not yet done. Model A additionally requires authorized raw-file provisioning. Model B can be regenerated from the clone alone after dependency setup. No new training code, framework, API, or M2/M3 work is included here. Python compatibility, raw redistribution permission, radiation metadata, normal-period selection, and model evaluation remain explicit limitations.

### Verified synchronization snapshot

The full local tree passes Ruff lint/format, strict mypy for 46 files, and **192 tests**. The independently checked M2-free staged snapshot passes Ruff lint/format, strict mypy for 43 files, and **163 tests** with the separately provisioned local NASA inputs. A clone without those inputs runs 162 tests and skips the one raw-file integration test. The 29 M2-only cases are deliberately not published by this commit.

Both documented full-size dataset commands were executed from a clean staged-source snapshot using the existing provisioned interpreter. The synthetic export reproduced 960 samples/5,760 observations; the NASA export reproduced 12,087 samples and the validated manifest. Both generated feature schemas match the checked-in schema copies exactly. No raw CSVs, generated datasets, environments, credentials, model binaries, or M2 source files are staged. Source permissions remain unverified; transfer has not been performed by this synchronization.
