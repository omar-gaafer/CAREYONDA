# D2/D3 — Local NASA RR-1 environmental integration

## Scope and reproducibility

Only the three user-supplied CSVs under `datasets/raw/nasa_eda/` are used. No research, downloads, package installation, model training, human physiological pairing, or clinical rules are involved. Raw files and the M1.2 synthetic dataset remain separate and unchanged. Existing uncommitted M2 reasoning work is preserved.

Generate the validated real-data export from the repository root:

```sh
PYTHONPATH=backend backend/.venv/bin/python -m app.ingestion.nasa_rr1_export \
  --raw datasets/raw/nasa_eda \
  --output datasets/processed/nasa_rr1_eda_d2d3_validated
```

Outputs must use a new directory; the exporter refuses to overwrite existing datasets. The initial pre-final-audit export at `datasets/processed/nasa_rr1_eda_d2d3/` is retained locally; use the `_validated` directory above for training. Raw/processed data paths are already ignored by Git.

## Raw audit

| File | CSV data rows (excluding header) | Timestamp range / designation |
| --- | --- | --- |
| `RR-1_EDA_Telemetry_table.csv` | **12,087** | `Controller_Time_GMT`: 2014-09-20 03:59 through 2014-11-01 03:54 |
| `RR-1_EDA_Radiation_table.csv` | **39** | `Date`: 2014-09-21 through 2014-10-29, daily date labels without timezone |
| `RR-1_EDA_Summary_table.csv` | **10** | Descriptive summary; no timestamps |

The request stated 12,086 and 38 records; those are the counts of consecutive intervals, not CSV data rows. No data rows are dropped to make the source fit the stated counts. All numeric cells are finite and present. Neither telemetry nor radiation has duplicate timestamps, invalid timestamps, out-of-order intervals, or physical-domain violations under the documented unit interpretation. These checks do not establish calibration or sensor accuracy.

Telemetry headers are `Controller_Time_GMT`, `Temp_degC_Ground`, `Temp_degC_ISS`, `RH_percent_Ground`, `RH_percent_ISS`, `CO2_ppm_Ground`, and `CO2_ppm_ISS`.

Sampling intervals in source order:

| Interval | Count |
| --- | --- |
| 3 minutes | 1 |
| 4 minutes | 5 |
| 5 minutes | 12,071 |
| 6 minutes | 6 |
| 8 minutes | 1 |
| 20 minutes | 1 |
| 33 minutes | 1 |

There are **15 non-five-minute intervals**. Radiation has 38 consecutive one-day intervals. No regular-grid resampling or interpolation is performed for either table.

Telemetry raw descriptive statistics (sample standard deviation, n-1):

| Column | Min | Max | Mean | SD |
| --- | --- | --- | --- | --- |
| ISS temperature (degC) | 18.5 | 26.8 | 22.761124 | 0.808262 |
| Ground temperature (degC) | 18.3 | 27.1 | 22.757028 | 0.818211 |
| ISS relative humidity (%) | 31 | 76 | 43.981302 | 6.778033 |
| Ground relative humidity (%) | 32 | 75 | 44.121370 | 6.644435 |
| ISS CO2 (ppm) | 1862 | 4667 | 3197.267229 | 562.148827 |
| Ground CO2 (ppm) | 438 | 4690 | 2853.738562 | 1096.735523 |

Radiation raw ranges: GCR 0.13–0.14 mGy/day, SAA 0.06–0.10 mGy/day, total 0.19–0.23 mGy/day. Accumulated-column raw numbers range from 0.21 to 7.96; its units are unresolved and must not be presented as verified dose or rate. Raw numeric values and full-precision computed statistics are in `audit.json` and `source_records.jsonl`.

## Time and source interpretation

`Controller_Time_GMT` contains naive minute-resolution strings. Its explicit GMT column designation is interpreted as UTC+00:00, without local-time conversion or daylight-saving adjustment. The observation timestamp is timezone-aware UTC, while the original exact string, column name, CSV row number, filename, full source SHA-256, and numeric tokens remain in `source_records.jsonl`. No ingestion timestamp is fabricated.

Radiation has only civil date labels and no confirmed timezone, interval boundaries, or availability time. A daily record is represented at the **following midnight UTC** as an explicit conservative daily-interval convention, not a claimed instrument event timestamp. Thus source dates September 21–October 29 map to timestamps September 22–October 30. The original date labels are retained. Each numeric rate observation is `suspect` with `daily_timezone_and_boundary_assumed`; radiation remains a separate daily series and is never joined into minute-level features. Online availability is not established.

Provenance uses `source_type="mission_log"`, `origin="measured"`, a table/hash-specific source ID, and an explicit CSV interpretation method. This identifies transcription of reported NASA table measurements, not direct access to calibrated sensor hardware. The local files do not supply detector identity, calibration, hardware accuracy, exact ISS sensor location, or detailed acquisition methods. None is invented.

ISS observations have spacecraft `ISS` and experiment/mission context `NASA-RR1`. Ground controls use a separate mission/experiment scope `NASA-RR1-ground-control`, never an astronaut or a fictional spacecraft. Source columns preserve the ISS/Ground distinction. These data are not paired human measurements, and no such pairing is exported.

## Minimal registry additions and units

The original ten metrics retain their behavior. Seven additive metrics cover the local quantities:

| Metric | Domain | Canonical unit | Scope |
| --- | --- | --- | --- |
| `cabin_co2_concentration` | environmental | `ppm` | spacecraft / mission (ground experiment) |
| `environment_temperature` | environmental | `degC` (degrees Celsius) | spacecraft / mission |
| `relative_humidity` | environmental | `%` | spacecraft / mission |
| `radiation_gcr_dose_rate` | radiation | `mGy/d` | spacecraft |
| `radiation_saa_dose_rate` | radiation | `mGy/d` | spacecraft |
| `radiation_total_dose_rate` | radiation | `mGy/d` | spacecraft |
| `radiation_accumulated_dose` | radiation | `mGy` for a future verified accumulated-dose measurement | spacecraft |

Celsius/percent/ppm numerical values are unchanged. Canonical spellings correspond to the original header declarations; exact original header names and lexical values are preserved in the sidecar. Source `mGy_d`/summary `mGy/day` is expressed as canonical `mGy/d` for the three rate fields, with no numerical scaling. CO2 ppm and partial pressure remain different metrics; no corresponding total pressure exists here, so no conversion to Pa occurs.

Only basic physical checks apply: concentration/rates are nonnegative, relative humidity is between 0 and 100%, and Celsius temperatures cannot be below absolute zero. These are physical-domain checks, not clinical limits. Missing cells become explicit missing measurements; malformed/non-finite tokens become unavailable/rejected measurements with reason codes, preserving their raw tokens. Finite physically invalid values remain recorded as numeric invalid observations. Rows with malformed timestamps are retained in the source sidecar with an issue code and no fabricated event timestamp. Duplicate timestamps are retained and marked suspect, not silently deduplicated or averaged as independent samples.

### Accumulated-dose conflict and user decision

The column name `Accumulated_Dose_mGy_d` and summary label `Radiation Accumulated [mGy/day]` both indicate a rate unit, while the increasing numeric series looks cumulative. The user confirmed there is **no local unit confirmation** and requested flagging/exclusion. The adapter therefore does **not** assign those raw numeric values to either mGy or mGy/day observations. Each accumulated observation is `unavailable/rejected` with `ambiguous_accumulated_unit`; the untouched raw token remains in its linked source row. Its distinct accumulated-dose metric prevents conflating accumulated quantity with rates without asserting an unverified numeric unit.

The audit includes raw numeric cumulative/component consistency diagnostics. Rounding-level differences are reported, never corrected. These diagnostics are not documentation of physical units. Neither accumulated dose nor any radiation metric is included in environmental training features.

## NASA summary comparison

For each of six telemetry columns and three radiation-rate columns, compare Max, Min, Mean, sample SD, and Median against the summary at its printed decimal precision: **45/45 comparable values match**. Sample SD (n-1) reproduces the supplied printed statistics; population SD is also reported in the audit so the choice is explicit. Summary rounding is only a reporting comparison, not a data transformation or clinical tolerance.

The accumulated summary row is explicitly `not_comparable_unit_ambiguity`; its supplied unit conflicts with its apparent quantity. It is not silently relabeled or counted as a successful match. A mismatch in any comparable statistic is emitted as `mismatch` with both supplied and computed values. The tests exercise a deliberate mismatch. Dataset-wide summary statistics are audit outputs only, never preprocessing fitted across validation/test data.

## Environmental training export

Only the three ISS environmental metrics are used. There are **12,087 event-time samples**, with chronological splits by unique timestamp:

| Split | Samples | UTC start | UTC end |
| --- | --- | --- | --- |
| Train | 8,460 | 2014-09-20 03:59 | 2014-10-19 13:38 |
| Validation | 1,813 | 2014-10-19 13:43 | 2014-10-25 20:46 |
| Test | 1,814 | 2014-10-25 20:51 | 2014-11-01 03:54 |

There are **16 numeric features**. For each prefix `cabin_co2_concentration`, `environment_temperature`, and `relative_humidity`, export:

- `<metric>_value`: current evaluated-valid value, in ppm / degC / % respectively.
- `<metric>_mean_30m`: sample mean in the actual causal `(t-1800 seconds,t]` window, same unit.
- `<metric>_delta`: current minus most recent earlier valid value inside that window, same unit; not a per-minute derivative.
- `<metric>_count_30m`: number of valid samples in the window, unitless count.
- `<metric>_missing`: current timestamp lacks a unique usable reading, 0/1.

`gap_seconds` is elapsed time since the preceding sample in the same split, in seconds. Its evidence may refer to an older timestamp beyond the rolling window because the gap itself describes that separation. All source times are at or before the current event. First-split deltas and gaps are null; first rolling windows start with only current data. Means are sample-weighted, not time-weighted. No time-grid assumption, interpolation, backward fill, future observation, whole-dataset scaling, or imputation is used. Empty CSV cells represent nulls, not zero.

Windows are reset at split boundaries: not even past training evidence crosses into validation/test feature windows. Equal timestamps cannot be divided across partitions. Keep split files separate, drop `sample_id` and `event_time_utc` metadata from model inputs, and use only feature-schema predictor names. Fit any scaler/imputer/anomaly model on training only. The training partition is historical data, **not a verified anomaly-free baseline**. There are no anomaly labels or clinical targets.

## Generated files

Under `datasets/processed/nasa_rr1_eda_d2d3_validated/`:

- `train.csv`, `validation.csv`, `test.csv` — 16 predictors plus sample ID and UTC event-time metadata.
- `telemetry_observations.jsonl` — **72,522 observations** (36,261 ISS and 36,261 ground), all structurally/physically valid in the supplied data.
- `radiation_observations.jsonl` — **156 observations**: 117 suspect daily rates and 39 unavailable accumulated quantities.
- `source_records.jsonl` — **12,126 source rows** with untouched tokens, source hashes, record numbers, time interpretation, and observation IDs.
- `feature_evidence.jsonl` — per-feature observation-ID lineage and split membership for all 12,087 samples.
- `feature_schema.json` — feature names, units, nullability, and temporal/split policies.
- `audit.json` — complete raw audit, count discrepancies, unit limitations, and summary comparisons.
- `manifest.json` — counts, split boundaries, and SHA-256 hashes of the other output files.
- `README.md` — short training handoff.

Raw numeric invalid/missing cells: **0**. Raw timestamp-invalid or duplicate rows: **0**. Typed observation counts: **72,522 valid, 117 suspect, 39 unavailable, 0 invalid**. The suspect/unavailable statuses concern unresolved source temporal/unit metadata, not corruption of the original numeric values. No observation is assigned to a human subject.

## Implementation and remaining limits

New adapter/audit code is isolated in `app/ingestion/nasa_rr1.py`; export orchestration is `app/ingestion/nasa_rr1_export.py`; real-only temporal features are `app/features/environmental.py`. M1.2's synthetic feature/export implementation is untouched. The existing starter-registry test now asserts preservation of its original ten names as a subset, permitting the explicitly requested additive metrics without weakening validation of existing behavior.

The environmental dataset is ready for unlabeled anomaly-detection experiments. It does not establish environmental hazard thresholds, human health effects, clinical validity, a verified normal period, or calibrated radiation exposure. Accumulated-dose unit documentation and radiation daily timezone/boundaries remain unresolved; instrument calibration/provenance detail is limited to the supplied tables. Python 3.14.8 is tested; minimum-version runtime testing and cross-platform dependency locks remain existing limitations.

Quality commands, from `backend`:

```sh
.venv/bin/python -m ruff check app tests ../simulator
.venv/bin/python -m ruff format --check app tests ../simulator
.venv/bin/python -m mypy
.venv/bin/python -m pytest
```

## Final verification and changed files

On the existing Python 3.14.8 environment: Ruff lint passed; Ruff formatting passed for 46 files; strict mypy passed for 46 source files; pytest **192 passed** (172 existing cases plus 19 new fixture cases and one local-data integration case). The local-data integration test skips when the ignored NASA files are absent, and never downloads them. Two initial test type-narrowing errors were fixed with explicit type checks; no typing/lint suppressions or dependencies were added.

All 72,678 serialized observations were independently revalidated. The manifest's ten artifact hashes match. All 12,126 source-row/hash links and all 12,087 sample mappings were verified: no feature uses a future observation or evidence from another split. Raw source hashes still match the adapter audit. Component/total numerical discrepancies reach 0.01 and cumulative-series discrepancies reach 0.02 in the source's printed numbers; the final total-number sum and final accumulated number both equal 7.96. These differences are retained without adjustment and do not resolve the unit ambiguity. The validated output occupies approximately 95.5 MB and is ignored by Git.

Exact project files changed in D2/D3:

1. `backend/app/schemas/observation.py` — seven additive registry entries.
2. `backend/app/ingestion/nasa_rr1.py` — adapters, raw audit, provenance sidecar, summary comparison.
3. `backend/app/ingestion/nasa_rr1_export.py` — separate real-data CLI/export.
4. `backend/app/features/environmental.py` — causal real-only environmental features and chronological splits.
5. `backend/tests/unit/test_nasa_rr1.py` — focused synthetic CSV fixture tests.
6. `backend/tests/integration/test_nasa_rr1_local.py` — supplied local-file validation.
7. `backend/tests/unit/test_training_pipeline.py` — preserve original metric subset while permitting registry extension; all original cases remain.
8. `docs/architecture/D2_D3_NASA_RR1.md` — this report.

The eleven validated output files are listed above; the eleven preliminary export files remain in their earlier ignored output directory. No raw file, synthetic dataset, training implementation, AI/reasoning implementation, safety module, dependency declaration, or earlier documentation was changed in this assignment. Existing uncommitted M2 files remain uncommitted. No Git commits or pushes were performed.
