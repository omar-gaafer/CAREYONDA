# NASA RR-1 ISS environmental features

Real ISS experiment-environment telemetry only; no human physiology pairing or anomaly labels. Raw source files remain under datasets/raw/nasa_eda. Ground-control measurements are adapted under a separate mission scope and never used as ISS features.

Use train.csv, validation.csv, and test.csv chronologically. Drop sample_id and event_time_utc from predictors; feature_schema.json lists the 16 numeric features. No scaling, imputation, normality assumption, or model fitting is applied. Fit preprocessing on training only. Trailing 30-minute windows use actual event times and reset per split, so no evidence crosses split boundaries. Means are sample-weighted, not time-weighted. Empty cells are missing, not zero.

Controller_Time_GMT is interpreted as UTC+00:00; original timestamp tokens and numeric strings are retained in source_records.jsonl. No CO2 ppm-to-partial-pressure conversion occurs because paired total pressure is absent. Radiation is a separate daily series, represented at assumed next-midnight UTC boundaries and flagged suspect for temporal uncertainty. Accumulated-dose units are ambiguous and were not corrected: raw values remain in the sidecar; typed accumulated observations are unavailable. Radiation is not interpolated or joined into telemetry features.

See audit.json for raw ranges, intervals, quality counts, and summary comparisons, and docs/architecture/D2_D3_NASA_RR1.md for interpretation and limitations.
