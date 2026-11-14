"""Run the offline, research-only Model A temporal analysis.

Measurement-bearing outputs belong in an ignored local directory. This command
does not retrain, rewrite, or publish the v1.1.0 production artifact.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import spearmanr  # type: ignore[import-untyped]  # pinned SciPy lacks stubs; result normalized to float
from sklearn.ensemble import IsolationForest  # type: ignore[import-untyped]  # pinned sklearn lacks py.typed

from app.ai.nasa_environment_anomaly import (
    apply_preprocessing,
    feature_names,
    parse_records,
)
from app.research.model_a_environmental import (
    causal_persistence,
    consecutive_flag_episodes,
    recovery_seconds,
    robust_mad_parameters,
    robust_mad_score,
)
from app.storage.nasa_environment_model_store import load_model_a, read_metadata

SPLIT_ORDER = ("train", "validation", "test")
PRIMARY_METRICS = (
    "cabin_co2_concentration",
    "environment_temperature",
    "relative_humidity",
)
BASELINE_FEATURES = tuple(
    name
    for name in feature_names()
    if name.endswith(("_value", "_mean_30m", "_delta")) or name == "gap_seconds"
)
RESEARCH_SCOPE = {
    "source": "NASA RR-1 processed ISS environmental telemetry",
    "subject": "ISS experiment-environment observations; no astronaut identity or physiology link",
    "mission_scope": "NASA-RR1 / ISS only; CO2 is ppm; radiation is excluded",
    "intended_use": "Offline research ranking and temporal behavior review only",
    "not_a": [
        "medical probability",
        "clinical finding",
        "hazard severity",
        "spacecraft command",
    ],
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path.name}")
        rows: list[dict[str, Any]] = []
        for raw in reader:
            row: dict[str, Any] = dict(raw)
            for name in feature_names():
                value = row[name]
                row[name] = (
                    None if value is None or value.strip() == "" else float(value)
                )
            rows.append(row)
    return rows


def _number(value: Any) -> float | None:
    if value is None:
        return None
    parsed = float(value)
    return parsed if math.isfinite(parsed) else None


def _quantiles(scores: Sequence[float | None]) -> dict[str, float | None]:
    values = np.asarray(
        [value for value in scores if value is not None], dtype=np.float64
    )
    return {
        f"q{percentile:g}": float(np.quantile(values, percentile / 100))
        if values.size
        else None
        for percentile in (0, 1, 5, 25, 50, 75, 95, 99, 99.9, 100)
    }


def _distribution(values: Sequence[float | None]) -> dict[str, Any]:
    finite = [value for value in values if value is not None]
    return {
        "count": len(values),
        "observed": len(finite),
        "missing": len(values) - len(finite),
        "mean": statistics.fmean(finite) if finite else None,
        "std_population": statistics.pstdev(finite) if finite else None,
        "quantiles": _quantiles(finite),
    }


def _rank_correlation(
    left: list[float | None], right: list[float | None]
) -> float | None:
    pairs = [
        (a, b)
        for a, b in zip(left, right, strict=True)
        if a is not None and b is not None
    ]
    if len(pairs) < 2:
        return None
    result = spearmanr([pair[0] for pair in pairs], [pair[1] for pair in pairs])
    return (
        None if not math.isfinite(float(result.statistic)) else float(result.statistic)
    )


def _load_evidence(path: Path) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            evidence[str(record["sample_id"])] = record
    return evidence


def _mad_baseline(
    train_rows: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> tuple[list[float | None], dict[str, Any]]:
    parameters: dict[str, tuple[float, float]] = {}
    omitted: dict[str, str] = {}
    for name in BASELINE_FEATURES:
        values = np.asarray(
            [
                _number(row[name]) if _number(row[name]) is not None else np.nan
                for row in train_rows
            ]
        )
        fitted = robust_mad_parameters(values)
        if fitted is None:
            omitted[name] = "no observations or raw MAD is zero on training"
        else:
            parameters[name] = fitted
    scores: list[float | None] = []
    per_feature: dict[str, list[float | None]] = {name: [] for name in parameters}
    for row in rows:
        components = []
        for name, (median, mad) in parameters.items():
            value = _number(row[name])
            score = robust_mad_score(math.nan if value is None else value, median, mad)
            per_feature[name].append(score)
            if score is not None:
                components.append(score)
        scores.append(max(components) if components else None)
    return scores, {
        "method": "maximum feature-wise absolute deviation / raw MAD",
        "fitted_on": "training split only",
        "features": {
            name: {"median": median, "raw_mad": mad}
            for name, (median, mad) in parameters.items()
        },
        "features_omitted": omitted,
        "per_feature_score_quantiles": {
            name: _quantiles(values) for name, values in per_feature.items()
        },
        "limitations": [
            "Descriptive robust deviation only; not a probability or hazard severity.",
            "Maximum across features is a screening statistic and ignores joint covariance.",
            "Zero-MAD training features are left unscored; missing values are not imputed.",
        ],
    }


def _seed_scores(
    train_rows: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    preprocessing: Any,
    params: dict[str, Any],
    seed: int,
) -> list[float | None]:
    train = parse_records(train_rows)
    prepared_train = apply_preprocessing(preprocessing, train.matrix)
    estimator = IsolationForest(**{**params, "random_state": seed})
    estimator.fit(prepared_train.matrix[prepared_train.scorable])
    parsed = parse_records(rows)
    prepared = apply_preprocessing(preprocessing, parsed.matrix)
    scores: list[float | None] = [None] * len(rows)
    scored = -estimator.score_samples(prepared.matrix[prepared.scorable])
    cursor = 0
    for index, can_score in enumerate(prepared.scorable):
        if can_score:
            scores[index] = float(scored[cursor])
            cursor += 1
    return scores


def _split_summary(
    name: str,
    rows: list[dict[str, Any]],
    results: tuple[Any, ...],
    persistence: list[bool | None],
    baseline_scores: list[float | None],
    baseline_threshold: float | None,
    threshold_available: bool,
) -> dict[str, Any]:
    scores = [result.anomaly_score for result in results]
    flags = [result.is_flagged for result in results]
    gaps = [_number(row["gap_seconds"]) for row in rows]
    missing: dict[str, int] = {}
    for metric in PRIMARY_METRICS:
        missing[f"{metric}_value"] = sum(row[f"{metric}_value"] is None for row in rows)
        missing[f"{metric}_mean_30m"] = sum(
            row[f"{metric}_mean_30m"] is None for row in rows
        )
    missing_rate = sum(
        value for key, value in missing.items() if key.endswith("_value")
    ) / max(1, len(rows) * len(PRIMARY_METRICS))
    long_gaps_15m = sum(gap is not None and gap > 900 for gap in gaps)
    long_gaps_30m = sum(gap is not None and gap > 1800 for gap in gaps)
    scored_flags = [flag for flag in flags if flag is not None]
    baseline_flags = [
        score is not None
        and baseline_threshold is not None
        and score >= baseline_threshold
        for score in baseline_scores
    ]
    idempotent = 0
    max_identical = 1 if rows else 0
    run = 1
    previous: tuple[Any, ...] | None = None
    for row in rows:
        current = tuple(row[name] for name in feature_names())
        if previous is not None and current == previous:
            idempotent += 1
            run += 1
            max_identical = max(max_identical, run)
        else:
            run = 1
        previous = current
    times = [result.event_time_utc for result in results]
    episodes = consecutive_flag_episodes(times, flags)
    index_by_time = {time.isoformat(): index for index, time in enumerate(times)}
    for episode in episodes:
        end_index = index_by_time[str(episode["end_utc"])]
        episode["stable_recovery_seconds"] = recovery_seconds(times, flags, end_index)
    day_bins: dict[str, list[float]] = defaultdict(list)
    for time, score in zip(times, scores, strict=True):
        if score is not None:
            day_bins[time.date().isoformat()].append(score)
    metric_behavior: dict[str, Any] = {}
    for metric in PRIMARY_METRICS:
        metric_behavior[metric] = {}
        for suffix in ("_value", "_delta"):
            column = f"{metric}{suffix}"
            metric_behavior[metric][column] = {
                "all_rows": _distribution([_number(row[column]) for row in rows]),
                "flagged_rows": _distribution(
                    [
                        _number(row[column])
                        for row, flag in zip(rows, flags, strict=True)
                        if flag is True
                    ]
                ),
                "not_flagged_rows": _distribution(
                    [
                        _number(row[column])
                        for row, flag in zip(rows, flags, strict=True)
                        if flag is False
                    ]
                ),
            }
    return {
        "rows": len(rows),
        "scored": sum(score is not None for score in scores),
        "abstained": sum(score is None for score in scores),
        "abstention_reasons": dict(
            Counter(
                reason for result in results for reason in result.abstention_reasons
            )
        ),
        "rows_with_imputed_features": sum(
            bool(result.imputed_features) for result in results
        ),
        "imputed_feature_cells": sum(
            len(result.imputed_features) for result in results
        ),
        "threshold_decision_status": "assessed"
        if threshold_available
        else "unassessed",
        "flagged_at_original_threshold": sum(flag is True for flag in flags)
        if threshold_available
        else None,
        "flagged_fraction_of_scored": sum(flag is True for flag in flags)
        / max(1, len(scored_flags))
        if threshold_available
        else None,
        "causal_persistence_2_of_3_flagged": sum(flag is True for flag in persistence)
        if threshold_available
        else None,
        "model_a_score_distribution": _distribution(scores),
        "sampling_gap_seconds": _distribution(gaps),
        "sampling_gaps_over_15_minutes": long_gaps_15m,
        "sampling_gaps_over_30_minutes": long_gaps_30m,
        "missing_primary_measurement_cells": missing,
        "missing_primary_measurement_fraction": missing_rate,
        "consecutive_duplicate_feature_rows": idempotent,
        "longest_consecutive_duplicate_feature_run": max_identical,
        "model_a_flagged_episodes": episodes if threshold_available else None,
        "daily_model_a_score_distribution": {
            day: _distribution(values) for day, values in sorted(day_bins.items())
        },
        "environmental_metric_behavior_by_model_a_status": metric_behavior,
        "statistical_baseline": {
            "flagged_at_training_q99": sum(baseline_flags),
            "flagged_fraction_of_rows": sum(baseline_flags) / max(1, len(rows)),
            "score_distribution": _distribution(baseline_scores),
            "spearman_with_model_a": _rank_correlation(scores, baseline_scores),
        },
    }


def run_analysis(
    dataset_dir: Path, artifact_dir: Path, output_dir: Path
) -> dict[str, Any]:
    """Verify trusted local inputs, run chronological analysis and write local outputs."""
    metadata = read_metadata(artifact_dir)
    threshold = metadata.threshold
    original_cutoff = None if threshold is None else threshold.value
    if metadata.model_version != "1.1.0":
        raise ValueError("this research run is pinned to the existing Model A v1.1.0")
    manifest_path = dataset_dir / "manifest.json"
    manifest_hash = _sha256(manifest_path)
    if manifest_hash != metadata.dataset.manifest_sha256:
        raise ValueError("dataset manifest hash does not match artifact provenance")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    evidence_path = dataset_dir / "feature_evidence.jsonl"
    expected_evidence_hash = manifest.get("sha256", {}).get(evidence_path.name)
    if not expected_evidence_hash or _sha256(evidence_path) != expected_evidence_hash:
        raise ValueError(
            "feature evidence hash does not match verified dataset manifest"
        )
    evidence = _load_evidence(evidence_path)
    detector = load_model_a(artifact_dir)
    rows_by_split: dict[str, list[dict[str, Any]]] = {}
    results_by_split: dict[str, tuple[Any, ...]] = {}
    previous_end = None
    for split in SPLIT_ORDER:
        split_record = metadata.dataset.splits[split]
        path = dataset_dir / split_record.file
        if _sha256(path) != split_record.sha256:
            raise ValueError(f"{split} CSV hash does not match model metadata")
        if manifest.get("sha256", {}).get(split_record.file) != split_record.sha256:
            raise ValueError(f"{split} CSV hash does not match dataset manifest")
        rows = _read_csv(path)
        if len(rows) != split_record.rows:
            raise ValueError(f"{split} row count does not match model metadata")
        parsed = parse_records(rows)
        if not parsed.event_times:
            raise ValueError(f"{split} split is empty")
        if previous_end is not None and parsed.event_times[0] <= previous_end:
            raise ValueError("chronological splits overlap or are out of order")
        previous_end = parsed.event_times[-1]
        if any(
            a >= b
            for a, b in zip(parsed.event_times, parsed.event_times[1:], strict=False)
        ):
            raise ValueError(f"{split} timestamps are not strictly chronological")
        rows_by_split[split] = rows
        results_by_split[split] = detector.score_records(rows)

    baseline_scores: dict[str, list[float | None]] = {}
    baseline_fit: dict[str, Any] | None = None
    for split in SPLIT_ORDER:
        scores, fit = _mad_baseline(rows_by_split["train"], rows_by_split[split])
        baseline_scores[split] = scores
        if split == "train":
            baseline_fit = fit
    baseline_train_valid = [
        value for value in baseline_scores["train"] if value is not None
    ]
    baseline_threshold = (
        float(np.quantile(baseline_train_valid, 0.99)) if baseline_train_valid else None
    )

    split_reports: dict[str, Any] = {}
    persistence_by_split: dict[str, list[bool | None]] = {}
    for split in SPLIT_ORDER:
        results = results_by_split[split]
        flags = [result.is_flagged for result in results]
        persistence = causal_persistence(
            [result.event_time_utc for result in results],
            flags,
            window_rows=3,
            minimum_flags=2,
            reset_gap_seconds=1800,
        )
        persistence_by_split[split] = persistence
        split_reports[split] = _split_summary(
            split,
            rows_by_split[split],
            results,
            persistence,
            baseline_scores[split],
            baseline_threshold,
            threshold_available=threshold is not None,
        )

    train_scores = [result.anomaly_score for result in results_by_split["train"]]
    observed_train = [value for value in train_scores if value is not None]
    sensitivity: dict[str, Any] = {}
    for quantile in (0.95, 0.975, 0.99, 0.995, 0.999):
        cutoff = float(np.quantile(observed_train, quantile))
        sensitivity[f"train_q{quantile:g}"] = {
            "threshold": cutoff,
            "selected_on": "training only",
            **{
                split: {
                    "flagged": sum(
                        result.anomaly_score is not None
                        and result.anomaly_score >= cutoff
                        for result in results_by_split[split]
                    ),
                    "scored": sum(
                        result.anomaly_score is not None
                        for result in results_by_split[split]
                    ),
                }
                for split in SPLIT_ORDER
            },
        }

    seed_robustness: dict[str, Any] = {}
    params = dict(metadata.estimator.params)
    for seed in (7, 1234):
        seed_robustness[str(seed)] = {}
        for split in ("validation", "test"):
            alternate = _seed_scores(
                rows_by_split["train"],
                rows_by_split[split],
                metadata.preprocessing,
                params,
                seed,
            )
            seed_robustness[str(seed)][split] = {
                "spearman_rank_correlation_to_v1_1_0": _rank_correlation(
                    [result.anomaly_score for result in results_by_split[split]],
                    alternate,
                ),
                "flagged_at_original_threshold": None
                if original_cutoff is None
                else sum(
                    score is not None and score >= original_cutoff
                    for score in alternate
                ),
                "threshold_decision_status": "unassessed"
                if original_cutoff is None
                else "assessed",
                "training_rows_used": len(rows_by_split["train"]),
                "alternate_model_persisted": False,
            }

    contexts: list[dict[str, Any]] = []
    for split in SPLIT_ORDER:
        rows, results, persistence = (
            rows_by_split[split],
            results_by_split[split],
            persistence_by_split[split],
        )
        for row, result, persistent_flag in zip(
            rows, results, persistence, strict=True
        ):
            source_evidence = evidence.get(str(row["sample_id"]), {})
            evidence_ids = source_evidence.get("feature_observation_ids", {})
            supporting = sum(
                len(ids) for ids in evidence_ids.values() if isinstance(ids, list)
            )
            missing = [name for name in feature_names() if row[name] is None]
            status = (
                "abstained"
                if result.status == "abstained"
                else (
                    "unassessed"
                    if result.is_flagged is None
                    else "flagged"
                    if result.is_flagged
                    else "not_flagged"
                )
            )
            contexts.append(
                {
                    "contract_version": "careyonda.environmental_anomaly_research.v2",
                    "run_mode": "retrospective_research_only",
                    "scope": RESEARCH_SCOPE,
                    "model": {
                        "model_id": metadata.model_id,
                        "model_version": metadata.model_version,
                        "metadata_version": metadata.metadata_version,
                        "artifact_created_at_utc": metadata.created_at_utc.isoformat(),
                        "artifact_sha256": metadata.artifact_sha256,
                        "artifact_file": Path(metadata.artifact_file).name,
                        "source_dataset": metadata.dataset.dataset_name,
                        "dataset_version": metadata.dataset.dataset_version,
                        "dataset_manifest_sha256": manifest_hash,
                        "feature_schema_version": metadata.dataset.schema_version,
                        "feature_count": len(feature_names()),
                        "estimator_class": metadata.estimator.class_name,
                        "training_random_state": metadata.estimator.params.get(
                            "random_state"
                        ),
                    },
                    "event": {
                        "sample_ref": result.sample_id,
                        "event_time_utc": result.event_time_utc.isoformat(),
                        "split": split,
                        "feature_evidence_availability": "available"
                        if supporting
                        else "unavailable",
                        "feature_evidence_reference_count": supporting,
                        "data_quality": "incomplete"
                        if missing or result.status == "abstained"
                        else "complete_for_model_inputs",
                        "missing_features": missing,
                        "imputed_features": list(result.imputed_features),
                        "abstention_reasons": list(result.abstention_reasons),
                    },
                    "model_result": {
                        "score_name": "isolation_forest_path_length_score",
                        "score": result.anomaly_score,
                        "threshold": original_cutoff,
                        "threshold_method": None
                        if threshold is None
                        else threshold.method,
                        "comparison": None if threshold is None else ">=",
                        "status": status,
                        "temporal_persistence_2_of_3": "unassessed"
                        if threshold is None
                        else "abstained"
                        if persistent_flag is None
                        else ("flagged" if persistent_flag else "not_flagged"),
                    },
                    "explanation_limitations": [
                        "Uncalibrated ranking score; not a probability, clinical finding, or hazard severity.",
                        "No verified anomaly labels; this output does not measure accuracy.",
                        "Feature contribution attribution is not produced by this analysis.",
                        "NASA RR-1 environment is not linked to synthetic or identified astronauts.",
                    ],
                }
            )

    report: dict[str, Any] = {
        "research_only": True,
        "research_method_version": "2.0.0",
        "model": {
            "model_id": metadata.model_id,
            "model_version": metadata.model_version,
            "metadata_version": metadata.metadata_version,
            "artifact_created_at_utc": metadata.created_at_utc.isoformat(),
            "artifact_sha256": metadata.artifact_sha256,
            "estimator_class": metadata.estimator.class_name,
            "training_random_state": metadata.estimator.params.get("random_state"),
            "feature_schema_version": metadata.dataset.schema_version,
            "dataset_manifest_sha256": manifest_hash,
            "threshold": None
            if threshold is None
            else threshold.model_dump(mode="json"),
            "threshold_decision_status": "unassessed"
            if threshold is None
            else "assessed",
        },
        "dataset": {
            "dataset_name": metadata.dataset.dataset_name,
            "dataset_version": metadata.dataset.dataset_version,
            "manifest": manifest_path.name,
            "manifest_sha256": manifest_hash,
            "split_order": list(SPLIT_ORDER),
            "source_scope": RESEARCH_SCOPE,
            "split_timestamps": manifest["splits"],
        },
        "methodology": {
            "model_a": "Unchanged v1.1.0 artifact and preprocessing; train scores in-sample. "
            + (
                "Original threshold absent; threshold decisions unassessed."
                if threshold is None
                else "Original training threshold and >= comparison retained."
            ),
            "threshold_sensitivity": "Alternative thresholds are empirical quantiles of training scores only; validation/test are descriptive and never select a threshold.",
            "statistical_baseline": baseline_fit,
            "statistical_baseline_training_q99_threshold": baseline_threshold,
            "temporal_persistence": "At least 2 of current/prior 2 scored rows, within a total 30-minute lookback; history resets per split and after >30-minute gaps.",
            "episode_definition": "Directly consecutive flagged observations with <=30-minute event-time separation; recovery is three subsequent scored non-flagged rows; any missing follow-up or >30-minute gap censors the episode.",
            "drift": "Daily score distributions and chronological split distributions; differences are statistical observations, not confirmed hazards.",
            "seed_experiments": "Refit fresh IsolationForest instances on training only with random_state 7 and 1234; no alternate artifacts persisted.",
            "labels": "No verified anomaly labels. No accuracy, precision, recall, F1, or ROC AUC computed.",
        },
        "splits": split_reports,
        "threshold_sensitivity_training_quantiles": sensitivity,
        "random_seed_robustness": seed_robustness,
        "output_policy": "Measurement-bearing report and event rows must remain local pending redistribution clearance.",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "research_evaluation.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    with (output_dir / "temporal_events.jsonl").open("w", encoding="utf-8") as handle:
        for context in contexts:
            handle.write(json.dumps(context, sort_keys=True, allow_nan=False) + "\n")
    (output_dir / "RESEARCH_REPORT.md").write_text(
        _markdown_report(report), encoding="utf-8"
    )
    return report


def _markdown_report(report: dict[str, Any]) -> str:
    def fmt(value: float | None) -> str:
        return "n/a" if value is None else f"{value:.6f}"

    def decision(value: int | None) -> str:
        return "unassessed" if value is None else str(value)

    lines = [
        "# Model A Environmental Temporal Research",
        "",
        "**Research only.** Model A scores are uncalibrated ranking values, not probabilities or hazard severity. NASA RR-1 has no verified anomaly labels; this report does not contain accuracy metrics.",
        "",
        f"Model: `{report['model']['model_id']}` v`{report['model']['model_version']}`; artifact SHA-256 `{report['model']['artifact_sha256']}`.",
        f"Dataset manifest SHA-256 `{report['dataset']['manifest_sha256']}`; schema `{report['model']['feature_schema_version']}`.",
        "",
        f"Original threshold decision status: {report['model']['threshold_decision_status']}. Missing thresholds never imply not_flagged.",
        "",
        "## Chronological split results",
        "",
        "| Split | Rows | Scored | Abstained | Flagged at existing threshold | Flag fraction | Median score | q95 | q99 | MAD baseline flags |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for split, result in report["splits"].items():
        quantiles = result["model_a_score_distribution"]["quantiles"]
        lines.append(
            f"| {split} | {result['rows']} | {result['scored']} | {result['abstained']} | {decision(result['flagged_at_original_threshold'])} | {fmt(result['flagged_fraction_of_scored'])} | {fmt(quantiles['q50'])} | {fmt(quantiles['q95'])} | {fmt(quantiles['q99'])} | {result['statistical_baseline']['flagged_at_training_q99']} |"
        )
    lines.extend(
        [
            "",
            "## Temporal, quality, and robustness findings",
            "",
            "| Split | Flagged episodes | Recovered episodes | Mean recovery (min) | Gaps >15 min | Gaps >30 min | Duplicate adjacent rows | Longest duplicate run |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for split, result in report["splits"].items():
        recovery = [
            float(episode["stable_recovery_seconds"])
            for episode in result["model_a_flagged_episodes"] or []
            if episode["stable_recovery_seconds"] is not None
        ]
        mean_recovery = statistics.fmean(recovery) / 60 if recovery else None
        lines.append(
            f"| {split} | {decision(None if result['model_a_flagged_episodes'] is None else len(result['model_a_flagged_episodes']))} | {decision(None if result['model_a_flagged_episodes'] is None else len(recovery))} | {fmt(mean_recovery)} | {result['sampling_gaps_over_15_minutes']} | {result['sampling_gaps_over_30_minutes']} | {result['consecutive_duplicate_feature_rows']} | {result['longest_consecutive_duplicate_feature_run']} |"
        )
    lines.extend(
        [
            "",
            "| Split | Robust baseline flags at train q99 | Spearman rank correlation to Model A |",
            "|---|---:|---:|",
        ]
    )
    for split, result in report["splits"].items():
        baseline = result["statistical_baseline"]
        lines.append(
            f"| {split} | {baseline['flagged_at_training_q99']} | {fmt(baseline['spearman_with_model_a'])} |"
        )
    lines.extend(
        [
            "",
            "### Seed stability",
            "",
            "| Seed | Validation Spearman | Test Spearman | Validation flags at original threshold | Test flags at original threshold |",
            "|---:|---:|---:|---:|---:|",
        ]
    )
    for seed, splits in report["random_seed_robustness"].items():
        lines.append(
            f"| {seed} | {fmt(splits['validation']['spearman_rank_correlation_to_v1_1_0'])} | {fmt(splits['test']['spearman_rank_correlation_to_v1_1_0'])} | {decision(splits['validation']['flagged_at_original_threshold'])} | {decision(splits['test']['flagged_at_original_threshold'])} |"
        )
    lines.extend(
        [
            "",
            "### Threshold sensitivity (quantiles selected on training scores)",
            "",
            "| Training quantile | Threshold | Train flags | Validation flags | Test flags |",
            "|---:|---:|---:|---:|---:|",
        ]
    )
    for key, values in report["threshold_sensitivity_training_quantiles"].items():
        lines.append(
            f"| {key.removeprefix('train_q')} | {fmt(values['threshold'])} | {values['train']['flagged']} | {values['validation']['flagged']} | {values['test']['flagged']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation limits",
            "",
            "- The statistical baseline is max feature-wise absolute deviation/raw MAD, with median and raw MAD fitted on training only. It ignores joint covariance and does not establish a hazard.",
            "- Persistence uses current/prior two rows inside a total 30-minute lookback (inclusive boundary), resets per split and after long gaps, and is research only.",
            "- Episodes and recovery describe score behavior only. Three non-flagged scored rows confirm recovery; missing readings or a gap over 30 minutes censor follow-up immediately.",
            "- Train scores are in-sample. Validation and test remain chronological; thresholds were derived from train only.",
            "- NASA RR-1 environmental telemetry is ISS experiment environment data, not linked to synthetic astronauts or human physiology.",
            "- Report and event output contain measurement-derived results. Keep the output directory local until redistribution is cleared.",
            "",
            "See `temporal_events.jsonl` for the research-only interface contract at each event.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run_analysis(args.dataset, args.artifact, args.output)
    print(
        json.dumps(
            {
                "output": args.output.name,
                "splits": {
                    name: {
                        "rows": value["rows"],
                        "scored": value["scored"],
                        "abstained": value["abstained"],
                        "flagged": value["flagged_at_original_threshold"],
                    }
                    for name, value in report["splits"].items()
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
