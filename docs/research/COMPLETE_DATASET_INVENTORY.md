# Complete CAREYONDA dataset inventory and publication

Inventory date: 2026-11-13. Target branch: `feature/training-ready`.

This release inventories the complete available local collection and publishes every independently approved file. It is **not a complete NASA measurement release**: 27 measurement-bearing NASA source/derived files remain blocked on source-rights evidence. No file was omitted merely because training does not immediately need it. Original files and directory names are preserved. Nothing was deleted, truncated, transformed, or regenerated.

## Scope, counts and integrity

Six collections contain **50 unique relative paths**, **311,910,935 bytes**. The original workspace has 32 files; 18 additional unique paths are verification datasets already present in the training worktree. Same-path identical copies are counted once; distinct directories are retained even when content duplicates.

**Approved: 23 dataset files, 24,468,383 bytes. Blocked: 27 files, 287,442,552 bytes.** Inventory/provenance documentation and the checksum manifest are release metadata, not counted as dataset payload files.

| Collection | Files | Bytes | Approved / blocked |
| --- | --- | --- | --- |
| `datasets/processed/nasa_rr1_eda_d2d3/` | 11 | 95,533,389 | 3 / 8 |
| `datasets/processed/nasa_rr1_eda_d2d3_validated/` | 11 | 95,534,014 | 3 / 8 |
| `datasets/processed/windows_handoff_verification/` | 11 | 95,534,014 | 3 / 8 |
| `datasets/raw/nasa_eda/` | 3 | 858,730 | 0 / 3 |
| `datasets/synthetic/m1_2_seed42/` | 7 | 12,225,394 | 7 / 0 |
| `datasets/synthetic/windows_handoff_verification/` | 7 | 12,225,394 | 7 / 0 |

[COMPLETE_DATASET_INVENTORY.json](COMPLETE_DATASET_INVENTORY.json) records every file's relative path, bytes, SHA-256, type, origin, original Git tracking/ignore state, rights decision and exact block reason. [DATASET_PUBLICATION_SHA256SUMS](DATASET_PUBLICATION_SHA256SUMS) covers every published dataset payload, with no self-referential checksum. `.gitattributes` disables text conversion for dataset bytes so Windows `core.autocrlf` cannot alter them.

## Sources, attribution and rights

Synthetic data comes entirely from CAREYONDA's seeded `simulator.mission_generator` and `simulator.run_simulation`, using seed 42, eight episodes per scenario, thirty steps, and 0.03 configured missing probability. All observation provenance is explicitly simulated; these are not private human health records. Both synthetic directories contain the full seven-file collection, including observations, features, evaluation labels, evidence mapping, feature schema, manifest and documentation.

NASA source attribution: NASA Open Science Data Repository, Environmental Data Application, Rodent Research-1 (RR-1), https://visualization.osdr.nasa.gov/eda/. The user confirms manual export from that official application. Download date and release version are unknown and are not inferred from mission dates or file modification times. Original filenames and checksums are recorded in [NASA_RR1_PROVENANCE.json](NASA_RR1_PROVENANCE.json), with confirmed and unverified facts separated.

The [official NASA data policy](https://science.data.nasa.gov/about/license) permits qualifying NASA-led mission data under CC0 unless restricted, while separately addressing explicitly licensed and other-source data. Official EDA documents the availability of raw/summary downloads. Public accessibility alone was not used as permission. Applicability to these exact export copies, release-specific conditions and absence of third-party restrictions remain unverified. Equivalent authoritative source/custodian confirmation can resolve this gate; a license file is not the only possible evidence.

Accordingly, the three raw CSVs and their observation/feature/source-record/quality-statistic derivatives remain blocked. Project-authored processed `README.md`, `feature_schema.json`, and `manifest.json` are approved as structural documentation, contract definitions, counts and checksums, rather than observed measurement series. **Published NASA manifests intentionally retain references to blocked payloads; they do not mean those payloads are present.** Their original contents are not edited to conceal omissions. NASA raw/derived measurement bytes remain local and ignored.

No credentials, caches, virtual environments, trained models or unrelated files are included. Pattern scanning found no secrets. Synthetic provenance was checked, and NASA data is environment/radiation experiment data, not paired human physiology. Source measurements and units are unchanged.

## Training paths and limitations

- Model A: `datasets/processed/nasa_rr1_eda_d2d3_validated/train.csv`, `validation.csv`, `test.csv` remain **blocked and absent from GitHub**. They exist locally. To generate them after authorized raw provisioning, use a fresh output directory such as `datasets/processed/nasa_rr1_eda_local`; the partially published metadata directory already exists and the exporter refuses overwrite.
- Model B: `datasets/synthetic/m1_2_seed42/features.csv` is published, with `labels.csv` for evaluation only. All 16 feature names/units are in its schema. Drop IDs; split by whole episode, fit preprocessing only on train, and never use scenario labels during unsupervised fitting.
- All three processed NASA directories are inventoried, including the preliminary and Windows verification outputs. None was silently substituted for the validated directory.

Synthetic labels and exposure-response relationships are assumptions, not diagnoses or clinical thresholds. NASA CO2 stays ppm and is not converted to Pa. Radiation remains daily; accumulated-dose units and daily timezone/boundaries remain unresolved. NASA statistics have 45 comparable matches at printed precision, but audits containing source-derived numeric summaries are held with the blocked measurement payloads. No model is implemented or trained by this publication.

## Windows clone and checksums

```powershell
git clone --branch feature/training-ready https://github.com/omar-gaafer/CAREYONDA.git
Set-Location .\CAREYONDA
$checksumLines = Get-Content .\docs\research\DATASET_PUBLICATION_SHA256SUMS
foreach ($line in $checksumLines) {
    $parts = $line -split '  ', 2
    $actualHash = (Get-FileHash -LiteralPath $parts[1] -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualHash -ne $parts[0]) { throw "Dataset checksum mismatch: $($parts[1])" }
}
```

Existing clean training checkouts can use `git pull --ff-only origin feature/training-ready`. See [the Windows handoff](../architecture/WINDOWS_TRAINING_HANDOFF.md) for environment setup. Synthetic files can be used immediately after cloning; generation is optional and must choose a fresh output path, for example `datasets/synthetic/m1_2_seed42_regenerated`. NASA originals must be obtained from the official EDA or an authorized team transfer once applicable source terms are confirmed. Do not force-add blocked files.

No Git LFS is required. The largest discovered file is 45,076,379 bytes, below GitHub's [50 MiB warning and 100 MiB block limits](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github). Published payloads are smaller still and use normal Git. No archive, truncation, split, LFS pointer, or content conversion is introduced.

## Per-file status

Git state below is the snapshot before this release's targeted staging; approved payloads are explicitly added despite their ignore rules, while security-related rules stay intact.

| Relative path | Bytes | Type | Origin | Before staging | Decision |
| --- | --- | --- | --- | --- | --- |
| `datasets/processed/nasa_rr1_eda_d2d3/README.md` | 1,487 | text/markdown | NASA structural metadata | untracked, ignored | **approved** |
| `datasets/processed/nasa_rr1_eda_d2d3/audit.json` | 18,935 | application/json | NASA measurements/derived statistics | untracked, ignored | **blocked** |
| `datasets/processed/nasa_rr1_eda_d2d3/feature_evidence.jsonl` | 38,737,763 | application/x-ndjson | NASA measurements/derived statistics | untracked, ignored | **blocked** |
| `datasets/processed/nasa_rr1_eda_d2d3/feature_schema.json` | 2,897 | application/json | NASA structural metadata | untracked, ignored | **approved** |
| `datasets/processed/nasa_rr1_eda_d2d3/manifest.json` | 1,481 | application/json | NASA structural metadata | untracked, ignored | **approved** |
| `datasets/processed/nasa_rr1_eda_d2d3/radiation_observations.jsonl` | 105,482 | application/x-ndjson | NASA measurements/derived statistics | untracked, ignored | **blocked** |
| `datasets/processed/nasa_rr1_eda_d2d3/source_records.jsonl` | 9,639,845 | application/x-ndjson | NASA measurements/derived statistics | untracked, ignored | **blocked** |
| `datasets/processed/nasa_rr1_eda_d2d3/telemetry_observations.jsonl` | 45,076,379 | application/x-ndjson | NASA measurements/derived statistics | untracked, ignored | **blocked** |
| `datasets/processed/nasa_rr1_eda_d2d3/test.csv` | 296,756 | text/csv | NASA measurements/derived statistics | untracked, ignored | **blocked** |
| `datasets/processed/nasa_rr1_eda_d2d3/train.csv` | 1,355,383 | text/csv | NASA measurements/derived statistics | untracked, ignored | **blocked** |
| `datasets/processed/nasa_rr1_eda_d2d3/validation.csv` | 296,981 | text/csv | NASA measurements/derived statistics | untracked, ignored | **blocked** |
| `datasets/processed/nasa_rr1_eda_d2d3_validated/README.md` | 1,487 | text/markdown | NASA structural metadata | untracked, ignored | **approved** |
| `datasets/processed/nasa_rr1_eda_d2d3_validated/audit.json` | 19,560 | application/json | NASA measurements/derived statistics | untracked, ignored | **blocked** |
| `datasets/processed/nasa_rr1_eda_d2d3_validated/feature_evidence.jsonl` | 38,737,763 | application/x-ndjson | NASA measurements/derived statistics | untracked, ignored | **blocked** |
| `datasets/processed/nasa_rr1_eda_d2d3_validated/feature_schema.json` | 2,897 | application/json | NASA structural metadata | untracked, ignored | **approved** |
| `datasets/processed/nasa_rr1_eda_d2d3_validated/manifest.json` | 1,481 | application/json | NASA structural metadata | untracked, ignored | **approved** |
| `datasets/processed/nasa_rr1_eda_d2d3_validated/radiation_observations.jsonl` | 105,482 | application/x-ndjson | NASA measurements/derived statistics | untracked, ignored | **blocked** |
| `datasets/processed/nasa_rr1_eda_d2d3_validated/source_records.jsonl` | 9,639,845 | application/x-ndjson | NASA measurements/derived statistics | untracked, ignored | **blocked** |
| `datasets/processed/nasa_rr1_eda_d2d3_validated/telemetry_observations.jsonl` | 45,076,379 | application/x-ndjson | NASA measurements/derived statistics | untracked, ignored | **blocked** |
| `datasets/processed/nasa_rr1_eda_d2d3_validated/test.csv` | 296,756 | text/csv | NASA measurements/derived statistics | untracked, ignored | **blocked** |
| `datasets/processed/nasa_rr1_eda_d2d3_validated/train.csv` | 1,355,383 | text/csv | NASA measurements/derived statistics | untracked, ignored | **blocked** |
| `datasets/processed/nasa_rr1_eda_d2d3_validated/validation.csv` | 296,981 | text/csv | NASA measurements/derived statistics | untracked, ignored | **blocked** |
| `datasets/processed/windows_handoff_verification/README.md` | 1,487 | text/markdown | NASA structural metadata | untracked, ignored | **approved** |
| `datasets/processed/windows_handoff_verification/audit.json` | 19,560 | application/json | NASA measurements/derived statistics | untracked, ignored | **blocked** |
| `datasets/processed/windows_handoff_verification/feature_evidence.jsonl` | 38,737,763 | application/x-ndjson | NASA measurements/derived statistics | untracked, ignored | **blocked** |
| `datasets/processed/windows_handoff_verification/feature_schema.json` | 2,897 | application/json | NASA structural metadata | untracked, ignored | **approved** |
| `datasets/processed/windows_handoff_verification/manifest.json` | 1,481 | application/json | NASA structural metadata | untracked, ignored | **approved** |
| `datasets/processed/windows_handoff_verification/radiation_observations.jsonl` | 105,482 | application/x-ndjson | NASA measurements/derived statistics | untracked, ignored | **blocked** |
| `datasets/processed/windows_handoff_verification/source_records.jsonl` | 9,639,845 | application/x-ndjson | NASA measurements/derived statistics | untracked, ignored | **blocked** |
| `datasets/processed/windows_handoff_verification/telemetry_observations.jsonl` | 45,076,379 | application/x-ndjson | NASA measurements/derived statistics | untracked, ignored | **blocked** |
| `datasets/processed/windows_handoff_verification/test.csv` | 296,756 | text/csv | NASA measurements/derived statistics | untracked, ignored | **blocked** |
| `datasets/processed/windows_handoff_verification/train.csv` | 1,355,383 | text/csv | NASA measurements/derived statistics | untracked, ignored | **blocked** |
| `datasets/processed/windows_handoff_verification/validation.csv` | 296,981 | text/csv | NASA measurements/derived statistics | untracked, ignored | **blocked** |
| `datasets/raw/nasa_eda/RR-1_EDA_Radiation_table.csv` | 1,683 | text/csv | NASA measurements/derived statistics | untracked, ignored | **blocked** |
| `datasets/raw/nasa_eda/RR-1_EDA_Summary_table.csv` | 700 | text/csv | NASA measurements/derived statistics | untracked, ignored | **blocked** |
| `datasets/raw/nasa_eda/RR-1_EDA_Telemetry_table.csv` | 856,347 | text/csv | NASA measurements/derived statistics | untracked, ignored | **blocked** |
| `datasets/synthetic/m1_2_seed42/README.md` | 2,270 | text/markdown | synthetic | untracked, ignored | **approved** |
| `datasets/synthetic/m1_2_seed42/evidence_mapping.json` | 5,908,175 | application/json | synthetic | untracked, ignored | **approved** |
| `datasets/synthetic/m1_2_seed42/feature_schema.json` | 3,534 | application/json | synthetic | untracked, ignored | **approved** |
| `datasets/synthetic/m1_2_seed42/features.csv` | 148,834 | text/csv | synthetic | untracked, ignored | **approved** |
| `datasets/synthetic/m1_2_seed42/labels.csv` | 46,110 | text/csv | synthetic | untracked, ignored | **approved** |
| `datasets/synthetic/m1_2_seed42/manifest.json` | 1,458 | application/json | synthetic | untracked, ignored | **approved** |
| `datasets/synthetic/m1_2_seed42/observations.json` | 6,115,013 | application/json | synthetic | untracked, ignored | **approved** |
| `datasets/synthetic/windows_handoff_verification/README.md` | 2,270 | text/markdown | synthetic | untracked, ignored | **approved** |
| `datasets/synthetic/windows_handoff_verification/evidence_mapping.json` | 5,908,175 | application/json | synthetic | untracked, ignored | **approved** |
| `datasets/synthetic/windows_handoff_verification/feature_schema.json` | 3,534 | application/json | synthetic | untracked, ignored | **approved** |
| `datasets/synthetic/windows_handoff_verification/features.csv` | 148,834 | text/csv | synthetic | untracked, ignored | **approved** |
| `datasets/synthetic/windows_handoff_verification/labels.csv` | 46,110 | text/csv | synthetic | untracked, ignored | **approved** |
| `datasets/synthetic/windows_handoff_verification/manifest.json` | 1,458 | application/json | synthetic | untracked, ignored | **approved** |
| `datasets/synthetic/windows_handoff_verification/observations.json` | 6,115,013 | application/json | synthetic | untracked, ignored | **approved** |

Every blocked path is listed above and has the same precise missing evidence recorded per file in JSON: exact-export/source-release reuse applicability and third-party restriction status. Raw originals also lack an established download date and independent exact-copy export record. Source hash integrity is confirmed locally; that does not itself establish redistribution rights.
