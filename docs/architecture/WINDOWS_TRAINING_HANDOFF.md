# Windows PowerShell training preparation

> Dataset publication update: 23 approved payload files are now included, covering both full synthetic snapshots and NASA structural README/schema/manifest files. The 27 NASA measurement-bearing files remain blocked, including all Model A split CSVs. See [the complete inventory](../research/COMPLETE_DATASET_INVENTORY.md). Some historical verification notes below predate this release. Use published Model B data directly or choose a new regeneration directory; NASA generation also needs a fresh output directory because metadata-only directories now exist.

Branch: `feature/training-ready`. Model A is an unsupervised Isolation Forest on real NASA RR-1 CO2, temperature, and humidity features. Model B is an unsupervised Isolation Forest on synthetic physiological/mission-context features, with scenario labels reserved for evaluation. Models, training scripts, and scikit-learn are not implemented or installed by this task.

## Verification scope

Use **standard Windows x64 CPython 3.14**, not a free-threaded, ARM64, or 32-bit interpreter. The existing fifteen package pins resolve to Windows-compatible binary wheels; pytest's Windows-only `colorama` dependency is additionally pinned in `backend/requirements-windows.txt`. All sixteen active package dependency constraints and Windows markers were checked. No package versions in the existing snapshot were changed, and no package was installed during this verification.

[WINDOWS_DEPENDENCY_VERIFICATION.json](WINDOWS_DEPENDENCY_VERIFICATION.json) records the selected wheel filenames, hashes, target, and verification method. This is a cross-platform dependency-resolution check from Linux, **not a native Windows installation or PowerShell end-to-end test**. No usable native Windows Python/PowerShell runtime was available in this session. The Windows user must execute installation, `pip check`, generation, and the quality commands below to complete native validation. Linux CPython 3.14.8 execution is tested. Other Python versions/architectures have not been verified.

## Clone and install

Run in PowerShell from the directory where the repository should be cloned:

```powershell
git clone --branch feature/training-ready https://github.com/omar-gaafer/CAREYONDA.git
Set-Location .\CAREYONDA
py -3.14 -m venv backend\.venv
$careyondaPython = Join-Path (Get-Location) 'backend\.venv\Scripts\python.exe'
& $careyondaPython -m pip install --only-binary=:all: -r .\backend\requirements-windows.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed; stop and report the error.' }
& $careyondaPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency consistency check failed.' }
$env:PYTHONPATH = Join-Path (Get-Location) 'backend'
```

No environment activation or execution-policy change is required. If `py -3.14` is unavailable, install standard x64 Python 3.14 through your approved software process first. Do not switch dependency versions merely to hide an error. Installation needs access to compatible packages; offline installation requires a separately provisioned wheel bundle. Data generation and tests are offline after provisioning.

For an existing clean checkout already on the training branch:

```powershell
git pull --ff-only origin feature/training-ready
```

The Unix syntax `PYTHONPATH=backend ...`, `.venv/bin/python`, and shell backslash continuation are not PowerShell commands. Use the interpreter variable and `$env:PYTHONPATH` above. Do not switch a dirty M2 checkout into this branch; use a separate clone.

## Prepare Model B inputs

From the repository root after setup:

```powershell
& $careyondaPython -m simulator.run_simulation --seed 42 --episodes-per-scenario 8 --steps 30 --output datasets/synthetic/m1_2_seed42_regenerated
if ($LASTEXITCODE -ne 0) { throw 'Synthetic export failed.' }
```

Output directory must not already exist; use a different output path for reruns. Default output contains 960 samples, 5,760 observations, and sixteen predictors. Inputs: `datasets/synthetic/m1_2_seed42/features.csv`; evaluation annotations: `labels.csv`; exact feature columns/units/encodings: `feature_schema.json`. Drop `sample_id` from fitting inputs and never fit using scenario labels or label-bearing provenance. Split by whole episode using `evidence_mapping.json`, preferably holding out another seed. Scenario assignments are synthetic annotations, not validated medical diagnoses or proof that every non-baseline record is anomalous.

## Obtain the Model A raw files

[The NASA permission review](NASA_RR1_PERMISSION_REVIEW.md) explains why the supplied local copies remain ignored. No raw data is shipped in Git. Required original files:

- `RR-1_EDA_Telemetry_table.csv`
- `RR-1_EDA_Radiation_table.csv`
- `RR-1_EDA_Summary_table.csv`

The official [NASA OSDR Environmental Data App](https://visualization.osdr.nasa.gov/eda/) provides raw/summary downloads in **Data Tables**. Select **RR-1** and obtain the telemetry, radiation, and summary tables, reviewing any accompanying notices. Alternatively receive the existing originals through a team-approved transfer after checking the source permissions. No transfer or additional dataset download was performed by this task.

Place the three files under `datasets/raw/nasa_eda/`. Example for files already received in an approved local folder (replace the example source path):

```powershell
New-Item -ItemType Directory -Force .\datasets\raw\nasa_eda | Out-Null
$approvedRawDirectory = 'C:\ApprovedTransfer\nasa_eda'
$requiredCsvFiles = @('RR-1_EDA_Telemetry_table.csv', 'RR-1_EDA_Radiation_table.csv', 'RR-1_EDA_Summary_table.csv')
foreach ($csvName in $requiredCsvFiles) {
    Copy-Item -LiteralPath (Join-Path $approvedRawDirectory $csvName) -Destination .\datasets\raw\nasa_eda\
}
Get-FileHash .\datasets\raw\nasa_eda\*.csv -Algorithm SHA256
```

Compare with the exact source hashes in [TRAINING_HANDOFF.md](TRAINING_HANDOFF.md#transfer-and-reproduce-nasa-data-model-a). Preserve original bytes and filenames; do not open/save the originals in Excel or silently convert delimiters, decimals, encodings, or timestamps. A fresh portal export may differ from the validated historical snapshot; if hashes/schema/counts differ, inspect and report the new data rather than altering files or tests to force a match.

## Prepare Model A inputs

```powershell
& $careyondaPython -m app.ingestion.nasa_rr1_export --raw datasets/raw/nasa_eda --output datasets/processed/nasa_rr1_eda_local
if ($LASTEXITCODE -ne 0) { throw 'NASA export failed.' }
```

A new output directory is required. The validated originals produce 12,087 samples: 8,460 train, 1,813 validation, 1,814 test. After local regeneration, inputs are `datasets/processed/nasa_rr1_eda_local/train.csv`, `validation.csv`, and `test.csv`. Use the sixteen features in `feature_schema.json`; drop `sample_id` and `event_time_utc`. Preserve chronological splits, and fit preprocessing only on training. Training data is not certified anomaly-free.

NASA CO2 is ppm, not the synthetic partial-pressure metric in Pa. Never combine them as if they were paired human physiological records. Radiation remains daily and separate; accumulated-dose units are ambiguous and its typed values remain unavailable/excluded. Original raw values and provenance are retained in `source_records.jsonl`.

The exact schema copies are [NASA_ENVIRONMENT_FEATURE_SCHEMA.json](NASA_ENVIRONMENT_FEATURE_SCHEMA.json) and [SYNTHETIC_FEATURE_SCHEMA.json](SYNTHETIC_FEATURE_SCHEMA.json). The existing export commands create these same schema contents. Output text newline conventions and therefore artifact hashes can differ across operating systems; do not claim cross-platform byte identity without checking it. Raw-transfer hashes must still match the exact originals.

## Quality checks

Keep `$careyondaPython` as the absolute path assigned at repository root:

```powershell
Push-Location .\backend
& $careyondaPython -m ruff check app tests ../simulator
if ($LASTEXITCODE -ne 0) { throw 'Ruff lint failed.' }
& $careyondaPython -m ruff format --check app tests ../simulator
if ($LASTEXITCODE -ne 0) { throw 'Formatting failed.' }
& $careyondaPython -m mypy
if ($LASTEXITCODE -ne 0) { throw 'Typing failed.' }
& $careyondaPython -m pytest
if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
Pop-Location
```

Caches now use relative ignored paths for Windows/Linux portability. With the validated raw NASA inputs, the training branch has 163 passing tests on Linux. Without those inputs, 162 pass and the one raw-data integration test skips. A native Windows failure must be reported with its actual error rather than treated as a passed check. No generated data, private data, credentials, virtual environment, or unfinished M2 implementation is included in the branch.

## Delivery verification

Ruff lint, formatting (43 files), strict mypy (43 files), and 163 tests passed in the isolated training worktree on Linux CPython 3.14.8. Both full-size generation commands reproduced the prior validated manifests and exact feature schemas after the cache-path change. Windows x64 CPython 3.14 binary-wheel dry-run and win32 dependency-marker/version closure passed for all sixteen packages. No native Windows run is claimed. The committed original dependency pins and all data-pipeline implementations remain unchanged. Only relative cache configuration, a Windows-specific requirements wrapper, and documentation/verification evidence are added.
