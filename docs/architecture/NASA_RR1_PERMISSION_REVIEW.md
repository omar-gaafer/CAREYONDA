# NASA RR-1 source and redistribution check

Reviewed 2026-11-13 for the Windows training handoff. Decision: keep all three supplied CSV copies ignored and out of Git. No additional dataset was downloaded or transferred.

## Primary sources checked

- [NASA Science Data Licenses](https://science.data.nasa.gov/about/license): the policy distinguishes explicitly licensed datasets, qualifying NASA-led mission data under CC0 unless restricted, and other data whose original source/rights should be verified. Source citation is encouraged.
- [NASA OSDR Environmental Data App](https://visualization.osdr.nasa.gov/eda/): the official application provides ISS/hardware telemetry and radiation data, with raw and summary downloads under Data Tables. Select RR-1 for the relevant tables.

These sources identify an official acquisition route and a general licensing framework. They do not establish the exact download history, release-specific metadata, or absence of third-party notices for the three local copies. No accompanying release/license/attribution document exists in the supplied local folder. General NASA policy alone was therefore not treated as a confirmed license for these exact copies. This is an evidence limitation, not a claim that the underlying NASA data is restricted.

## Excluded originals

- `RR-1_EDA_Telemetry_table.csv`
- `RR-1_EDA_Radiation_table.csv`
- `RR-1_EDA_Summary_table.csv`

Expected byte counts and SHA-256 values are recorded in [TRAINING_HANDOFF.md](TRAINING_HANDOFF.md#transfer-and-reproduce-nasa-data-model-a). No `.gitignore` exception or forced add is used. Processed datasets also remain excluded.

Teammates can obtain the RR-1 telemetry/radiation/summary tables through the official EDA Data Tables interface after reviewing accompanying terms, or receive appropriately authorized original copies from the team. The [Windows handoff](WINDOWS_TRAINING_HANDOFF.md) gives local placement and checksum commands. Retain original source attribution, acquisition date, release identifiers and any license/notice obtained during provisioning. Verify fingerprints before reproducing the validated dataset; a changed portal release needs its own audit. Only consider committing exact raw copies after their provenance and applicable redistribution terms are confirmed.

## Complete-collection release update

The user now attests that the three CSVs were manually exported from the official EDA for RR-1, but has no download log, release-specific license or independent exact-copy source record. [NASA_RR1_PROVENANCE.json](../research/NASA_RR1_PROVENANCE.json) records this distinction, the unknown download date, original filenames and verified checksums. The complete-collection release publishes independently approved synthetic data and project-authored structural metadata. NASA source/derived measurement-bearing files (including numerical quality audits) remain blocked; all 27 exact paths and missing evidence are listed in [the inventory](../research/COMPLETE_DATASET_INVENTORY.md). This is a conservative verification gate, not a finding that NASA prohibits reuse.
