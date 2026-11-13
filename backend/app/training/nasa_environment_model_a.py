"""Train and evaluate Model A: unsupervised Isolation Forest on NASA RR-1 features.

Run from ``backend`` (or with ``PYTHONPATH=backend``)::

    python -m app.training.nasa_environment_model_a \
        --data-dir <processed split directory> --output <new artifact directory>

Inputs are the processed chronological ``train.csv``, ``validation.csv`` and
``test.csv`` with their ``manifest.json`` and ``feature_schema.json``. Every file
hash listed in the manifest is verified first. Preprocessing, the estimator and the
review threshold are fitted on ``train`` only; validation and test are scored
separately afterwards. No anomaly labels exist, so no supervised metric is
computed. The output directory must not exist; nothing is overwritten.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import joblib  # type: ignore[import-untyped]  # joblib ships no type information
import numpy as np
import sklearn  # type: ignore[import-untyped]  # scikit-learn ships no py.typed
from sklearn.ensemble import IsolationForest  # type: ignore[import-untyped]

from app.ai.nasa_environment_anomaly import (
    METADATA_COLUMNS,
    AnomalyResult,
    FloatMatrix,
    FloatVector,
    NasaEnvironmentAnomalyDetector,
    ParsedRows,
    anomaly_scores,
    apply_preprocessing,
    expected_features,
    fit_preprocessing,
    parse_rows,
)
from app.features.environmental import environmental_schema
from app.schemas.nasa_environment_model import (
    DatasetProvenance,
    EstimatorSpec,
    ModelAMetadata,
    ParamValue,
    SplitFileRecord,
    ThresholdSpec,
)
from app.storage.nasa_environment_model_store import (
    ARTIFACT_FILE,
    load_model_a,
    write_estimator,
    write_metadata,
)

MODEL_VERSION = "1.1.0"
EVALUATION_VERSION = "1.1.0"
SPLITS = ("train", "validation", "test")
REPORT_QUANTILES = (0.0, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 0.999, 1.0)

SCORE_DEFINITION = (
    "anomaly_score = -IsolationForest.score_samples(x): the path-length based "
    "Isolation Forest score in (0, 1]; higher means easier to isolate relative to "
    "the training sample. Uncalibrated; not a probability, severity, confidence, "
    "or clinical/hazard measure."
)
INTENDED_USE = (
    "Research decision support: rank NASA RR-1 ISS experiment-environment "
    "telemetry windows for human review. Not a diagnosis, hazard determination, "
    "treatment rule, or spacecraft command."
)
LIMITATIONS = (
    "No anomaly ground-truth labels exist; no accuracy, precision, recall, F1 or "
    "ROC AUC is reported or meaningful.",
    "Scores are uncalibrated Isolation Forest scores, not probabilities.",
    "The review threshold is an unsupervised training-score quantile chosen by "
    "convention; it flags about (1 - quantile) of training rows by construction and "
    "is not a clinical, physiological, or environmental hazard threshold.",
    "Training data is not certified anomaly-free; anomalies present in training "
    "are partly learned as normal and raise the threshold.",
    "Validation and test are later in time than training; flag-rate differences "
    "may reflect temporal drift or mission-phase changes rather than anomalies.",
    "Training contained no missing main readings (every *_missing indicator was "
    "0), so the model has never learned how a dropout should score. Rows with a "
    "missing main reading (indicator 1, value blank) abstain rather than being "
    "scored as if typical; dropouts are surfaced as abstentions, not scores.",
    "Rows missing a *_value or *_mean_30m feature abstain; blank *_delta and "
    "gap_seconds cells are filled with training medians and reported per row.",
    "Training-split scores are in-sample and optimistic relative to new data.",
    "Single mission (RR-1), ISS experiment environment only: CO2 in ppm, not "
    "comparable with synthetic CO2 partial pressure in Pa; no pairing with human "
    "physiology; radiation is excluded.",
    "Isolation Forest split points lie within the training range, so scores "
    "saturate: a value far outside the training range is not scored higher than "
    "one just beyond it, and a deviation in a single feature may rank modestly.",
    "The artifact is a joblib pickle: load only trusted local artifacts with the "
    "exact recorded scikit-learn version; SHA-256 is verified before loading.",
    "Passing software tests does not establish medical or operational suitability;"
    " outputs require human review.",
)


class DatasetIntegrityError(RuntimeError):
    """Training inputs do not match their manifest or the expected schema."""


@dataclass(frozen=True)
class TrainingConfig:
    random_state: int = 42
    n_estimators: int = 200
    max_samples: int = 256
    max_features: float = 1.0
    bootstrap: bool = False
    threshold_quantile: float = 0.99
    sensitivity_quantiles: tuple[float, ...] = (0.95, 0.975, 0.99, 0.995, 0.999)
    stability_seeds: tuple[int, ...] = (7, 1234)
    top_k: int = 15

    def estimator_params(
        self, random_state: int | None = None
    ) -> dict[str, ParamValue]:
        return {
            "n_estimators": self.n_estimators,
            "max_samples": self.max_samples,
            "contamination": "auto",
            "max_features": self.max_features,
            "bootstrap": self.bootstrap,
            "n_jobs": 1,
            "random_state": self.random_state if random_state is None else random_state,
            "warm_start": False,
        }


@dataclass
class SplitData:
    name: str
    parsed: ParsedRows
    record: SplitFileRecord


@dataclass(frozen=True)
class TrainingOutcome:
    output: Path
    metadata: ModelAMetadata
    evaluation: Evaluation


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_dump(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _read_split(path: Path) -> ParsedRows:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if header is None:
            raise DatasetIntegrityError(f"{path.name} is empty")
        rows: list[Sequence[object]] = list(reader)
    return parse_rows(header, rows)


def load_dataset(data_dir: Path) -> tuple[DatasetProvenance, dict[str, SplitData]]:
    """Verify manifest hashes, schema identity and split counts, then parse."""
    manifest_path = data_dir / "manifest.json"
    schema_path = data_dir / "feature_schema.json"
    if not manifest_path.is_file() or not schema_path.is_file():
        raise DatasetIntegrityError("manifest.json and feature_schema.json required")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    hashes = manifest.get("sha256")
    if not isinstance(hashes, dict):
        raise DatasetIntegrityError("manifest lacks a sha256 table")
    required = {"feature_schema.json", *(f"{split}.csv" for split in SPLITS)}
    if not required <= set(hashes):
        raise DatasetIntegrityError("manifest does not list all required files")
    for name, expected in sorted(hashes.items()):
        path = data_dir / name
        if Path(name).name != name or not path.is_file():
            raise DatasetIntegrityError(f"manifest file missing: {name}")
        if _sha256(path) != expected:
            raise DatasetIntegrityError(f"SHA-256 mismatch: {name}")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if schema != environmental_schema():
        raise DatasetIntegrityError("feature_schema.json differs from project schema")
    if tuple(schema["metadata_columns"]) != METADATA_COLUMNS:
        raise DatasetIntegrityError("unexpected metadata columns")
    split_meta = manifest.get("splits", {})
    splits: dict[str, SplitData] = {}
    for split in SPLITS:
        parsed = _read_split(data_dir / f"{split}.csv")
        info = split_meta.get(split, {})
        if info.get("samples") != len(parsed.sample_ids):
            raise DatasetIntegrityError(f"{split} row count differs from manifest")
        times = parsed.event_times
        if any(
            later <= earlier for earlier, later in zip(times, times[1:], strict=False)
        ):
            raise DatasetIntegrityError(f"{split} timestamps are not increasing")
        record = SplitFileRecord(
            file=f"{split}.csv",
            sha256=hashes[f"{split}.csv"],
            rows=len(parsed.sample_ids),
            start_utc=times[0] if times else None,
            end_utc=times[-1] if times else None,
        )
        splits[split] = SplitData(split, parsed, record)
    order = [splits[split] for split in SPLITS]
    for earlier, later in zip(order, order[1:], strict=False):
        if earlier.record.end_utc and later.record.start_utc:
            if later.record.start_utc <= earlier.record.end_utc:
                raise DatasetIntegrityError("splits overlap or are not chronological")
    provenance = DatasetProvenance(
        dataset_name=data_dir.name,
        dataset_version=str(manifest.get("dataset_version", "unknown")),
        schema_version=str(schema["schema_version"]),
        manifest_sha256=_sha256(manifest_path),
        feature_schema_sha256=hashes["feature_schema.json"],
        splits={split: splits[split].record for split in SPLITS},
    )
    return provenance, splits


@dataclass(frozen=True)
class SensitivityRow:
    train_quantile: float
    threshold: float
    flagged: int
    flagged_fraction: float | None


@dataclass(frozen=True)
class TopScore:
    sample_id: str
    event_time_utc: str
    anomaly_score: float
    is_flagged: bool | None
    imputed_features: tuple[str, ...]


@dataclass(frozen=True)
class IdenticalRun:
    """Longest run of consecutive rows with identical feature vectors (audit aid)."""

    length: int
    first_sample_id: str
    start_utc: str
    end_utc: str
    anomaly_score: float | None


@dataclass(frozen=True)
class SplitEvaluation:
    rows: int
    scored: int
    abstained: int
    abstention_reasons: dict[str, int]
    rows_with_imputation: int
    score_mean: float | None
    score_std: float | None
    score_quantiles: dict[str, float]
    flagged_at_selected_threshold: int
    flagged_fraction_at_selected_threshold: float | None
    threshold_sensitivity: tuple[SensitivityRow, ...]
    top_scores: tuple[TopScore, ...]
    distinct_scores: int
    longest_identical_feature_run: IdenticalRun | None


@dataclass(frozen=True)
class StabilityComparison:
    spearman_rank_correlation: float
    flag_jaccard: float | None


@dataclass(frozen=True)
class SeedStability:
    random_state: int
    splits: dict[str, StabilityComparison]


@dataclass(frozen=True)
class Evaluation:
    evaluation_version: str
    model_id: str
    model_version: str
    artifact_sha256: str
    dataset_manifest_sha256: str
    supervised_metrics: None
    supervised_metrics_reason: str
    threshold_method: str
    threshold_quantile: float
    threshold_value: float
    splits: dict[str, SplitEvaluation]
    seed_stability: tuple[SeedStability, ...]
    notes: tuple[str, ...]


def _quantiles(scores: FloatVector) -> dict[str, float]:
    if scores.size == 0:
        return {}
    values = np.quantile(scores, REPORT_QUANTILES, method="linear")
    return {f"q{q:g}": float(v) for q, v in zip(REPORT_QUANTILES, values, strict=True)}


def _scored(results: Sequence[AnomalyResult]) -> FloatVector:
    return np.array(
        [r.anomaly_score for r in results if r.anomaly_score is not None],
        dtype=np.float64,
    )


def _rank_correlation(first: FloatVector, second: FloatVector) -> float:
    """Spearman correlation via ranks (ties are negligible for continuous scores)."""
    if first.size < 2:
        return float("nan")
    ranks_a = np.argsort(np.argsort(first)).astype(np.float64)
    ranks_b = np.argsort(np.argsort(second)).astype(np.float64)
    return float(np.corrcoef(ranks_a, ranks_b)[0, 1])


def _jaccard(first: set[int], second: set[int]) -> float | None:
    union = first | second
    return None if not union else len(first & second) / len(union)


def _longest_identical_run(
    parsed: ParsedRows, results: Sequence[AnomalyResult]
) -> IdenticalRun | None:
    """Find repeated feature vectors (e.g. possible stale feeds) without judging them."""
    matrix = parsed.matrix
    if matrix.shape[0] < 2:
        return None
    both_nan = np.isnan(matrix[1:]) & np.isnan(matrix[:-1])
    same = np.all((matrix[1:] == matrix[:-1]) | both_nan, axis=1)
    best_start, best_length, start, length = 0, 1, 0, 1
    for index, equal in enumerate(same.tolist(), start=1):
        if equal:
            length += 1
        else:
            start, length = index, 1
        if length > best_length:
            best_start, best_length = start, length
    if best_length < 2:
        return None
    end = best_start + best_length - 1
    return IdenticalRun(
        length=best_length,
        first_sample_id=parsed.sample_ids[best_start],
        start_utc=parsed.event_times[best_start].isoformat(),
        end_utc=parsed.event_times[end].isoformat(),
        anomaly_score=results[best_start].anomaly_score,
    )


def _split_report(
    parsed: ParsedRows,
    results: Sequence[AnomalyResult],
    train_scores: FloatVector,
    config: TrainingConfig,
    candidate_quantiles: tuple[float, ...],
) -> SplitEvaluation:
    scores = _scored(results)
    scored = [r for r in results if r.anomaly_score is not None]
    sensitivity = []
    for quantile in candidate_quantiles:
        cutoff = float(np.quantile(train_scores, quantile, method="linear"))
        flagged = int(np.count_nonzero(scores >= cutoff))
        fraction = flagged / scores.size if scores.size else None
        sensitivity.append(SensitivityRow(quantile, cutoff, flagged, fraction))
    flagged_now = sum(1 for r in results if r.is_flagged)
    top = sorted(scored, key=lambda r: (-(r.anomaly_score or 0.0), r.sample_id))
    abstentions: dict[str, int] = {}
    for result in results:
        for reason in result.abstention_reasons:
            abstentions[reason] = abstentions.get(reason, 0) + 1
    return SplitEvaluation(
        rows=len(results),
        scored=len(scored),
        abstained=len(results) - len(scored),
        abstention_reasons=abstentions,
        rows_with_imputation=sum(1 for r in results if r.imputed_features),
        score_mean=float(scores.mean()) if scores.size else None,
        score_std=float(scores.std(ddof=0)) if scores.size else None,
        score_quantiles=_quantiles(scores),
        flagged_at_selected_threshold=flagged_now,
        flagged_fraction_at_selected_threshold=(
            flagged_now / len(scored) if scored else None
        ),
        threshold_sensitivity=tuple(sensitivity),
        top_scores=tuple(
            TopScore(
                sample_id=r.sample_id,
                event_time_utc=r.event_time_utc.isoformat(),
                anomaly_score=float(r.anomaly_score or 0.0),
                is_flagged=r.is_flagged,
                imputed_features=r.imputed_features,
            )
            for r in top[: config.top_k]
        ),
        distinct_scores=int(np.unique(scores).size),
        longest_identical_feature_run=_longest_identical_run(parsed, results),
    )


def _stability(
    train_matrix: FloatMatrix,
    split_matrices: dict[str, FloatMatrix],
    reference: dict[str, FloatVector],
    reference_train: FloatVector,
    config: TrainingConfig,
) -> tuple[SeedStability, ...]:
    """Refit with other seeds on the same train rows; compare rankings and flags."""
    report: list[SeedStability] = []
    ref_cut = float(np.quantile(reference_train, config.threshold_quantile))
    for seed in config.stability_seeds:
        model = IsolationForest(**config.estimator_params(seed)).fit(train_matrix)
        alt_train = anomaly_scores(model, train_matrix)
        alt_cut = float(np.quantile(alt_train, config.threshold_quantile))
        per_split: dict[str, StabilityComparison] = {}
        for split, matrix in split_matrices.items():
            alt = anomaly_scores(model, matrix)
            ref = reference[split]
            per_split[split] = StabilityComparison(
                spearman_rank_correlation=_rank_correlation(ref, alt),
                flag_jaccard=_jaccard(
                    set(np.flatnonzero(ref >= ref_cut).tolist()),
                    set(np.flatnonzero(alt >= alt_cut).tolist()),
                ),
            )
        report.append(SeedStability(seed, per_split))
    return tuple(report)


def _fmt(value: float | None, digits: int = 4) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def _report_markdown(metadata: ModelAMetadata, evaluation: Evaluation) -> str:
    splits = evaluation.splits
    lines = [
        "# Model A evaluation report — NASA RR-1 environmental anomaly detector",
        "",
        "> LOCAL ARTIFACT. Contains values derived from NASA measurement data whose",
        "> redistribution is not yet approved. Do not commit or publish.",
        "",
        f"- Model: `{metadata.model_id}` v{metadata.model_version}",
        f"- Created (UTC): {metadata.created_at_utc.isoformat()}",
        f"- Artifact SHA-256: `{metadata.artifact_sha256}`",
        f"- Dataset: `{metadata.dataset.dataset_name}` "
        f"v{metadata.dataset.dataset_version}, schema "
        f"v{metadata.dataset.schema_version}",
        f"- Manifest SHA-256: `{metadata.dataset.manifest_sha256}`",
        f"- Estimator: {metadata.estimator.class_name} "
        f"{json.dumps(metadata.estimator.params, sort_keys=True)}",
        f"- Runtime: {json.dumps(metadata.estimator.runtime_versions, sort_keys=True)}",
        f"- Training rows used/excluded: {metadata.training_rows_used}/"
        f"{metadata.training_rows_excluded}",
        "",
        "## Score and threshold",
        "",
        metadata.score_definition,
        "",
        f"Threshold: {evaluation.threshold_value:.6f} = training-score quantile "
        f"{evaluation.threshold_quantile} (selected on train only).",
        "",
        "No anomaly labels exist, so no supervised metric is reported.",
        "",
        "## Per-split summary",
        "",
        "| Split | Rows | Scored | Abstained | Imputed rows | Median score | "
        "q0.99 score | Max score | Flagged | Flagged fraction |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name in SPLITS:
        info = splits[name]
        q = info.score_quantiles
        lines.append(
            f"| {name} | {info.rows} | {info.scored} | {info.abstained} | "
            f"{info.rows_with_imputation} | {_fmt(q.get('q0.5'), 6)} | "
            f"{_fmt(q.get('q0.99'), 6)} | {_fmt(q.get('q1'), 6)} | "
            f"{info.flagged_at_selected_threshold} | "
            f"{_fmt(info.flagged_fraction_at_selected_threshold)} |"
        )
    lines += [
        "",
        "## Candidate thresholds (from training scores; compared on validation)",
        "",
        "Test is deliberately absent here: it is evaluated only at the fixed "
        "threshold in the per-split summary above.",
        "",
        "| Train quantile | Threshold | Train flagged | Validation flagged |",
        "| --- | --- | --- | --- |",
    ]
    for train_row, val_row in zip(
        splits["train"].threshold_sensitivity,
        splits["validation"].threshold_sensitivity,
        strict=True,
    ):
        lines.append(
            f"| {train_row.train_quantile} | {train_row.threshold:.6f} | "
            f"{train_row.flagged} ({_fmt(train_row.flagged_fraction)}) | "
            f"{val_row.flagged} ({_fmt(val_row.flagged_fraction)}) |"
        )
    lines += [
        "",
        "## Data-quality diagnostics (descriptive; no rows were removed)",
        "",
        "Repeated quantile thresholds above indicate tied training scores. Long runs "
        "of identical consecutive feature vectors may indicate stale or repeated "
        "feeds; the cause is not determined here and needs human review.",
        "",
    ]
    for name in SPLITS:
        info = splits[name]
        run = info.longest_identical_feature_run
        detail = (
            "none"
            if run is None
            else f"{run.length} rows, {run.start_utc} -> {run.end_utc}, first "
            f"`{run.first_sample_id}`, score {_fmt(run.anomaly_score, 6)}"
        )
        lines.append(
            f"- {name}: {info.distinct_scores} distinct scores of {info.scored}; "
            f"longest identical feature-vector run: {detail}"
        )
    lines += ["", "## Seed stability (same train rows, other random_state)", ""]
    for entry in evaluation.seed_stability:
        for name, values in entry.splits.items():
            lines.append(
                f"- random_state={entry.random_state} {name}: Spearman "
                f"{values.spearman_rank_correlation:.4f}, flagged-set Jaccard "
                f"{_fmt(values.flag_jaccard)}"
            )
    for name in ("validation", "test"):
        lines += [
            "",
            f"## Highest {name} scores (for audit; not confirmed anomalies)",
            "",
            "| sample_id | event_time_utc | score | flagged | imputed |",
            "| --- | --- | --- | --- | --- |",
        ]
        for item in splits[name].top_scores:
            lines.append(
                f"| `{item.sample_id}` | {item.event_time_utc} | "
                f"{item.anomaly_score:.6f} | {item.is_flagged} | "
                f"{', '.join(item.imputed_features) or '-'} |"
            )
    lines += ["", "## Limitations", ""]
    lines += [f"- {item}" for item in metadata.limitations]
    return "\n".join(lines) + "\n"


def train_model_a(
    data_dir: Path, output: Path, config: TrainingConfig | None = None
) -> TrainingOutcome:
    """Fit on train only, persist, reload, and evaluate splits independently."""
    config = config or TrainingConfig()
    if not 0.0 < config.threshold_quantile < 1.0:
        raise ValueError("threshold_quantile must be in (0, 1)")
    if output.exists():
        raise FileExistsError("output directory already exists; choose a new path")
    dataset, splits = load_dataset(data_dir)
    contracts = expected_features()

    train = splits["train"].parsed
    preprocessing = fit_preprocessing(contracts, train.matrix)
    prepared_train = apply_preprocessing(preprocessing, train.matrix)
    train_matrix = prepared_train.matrix[prepared_train.scorable]
    if train_matrix.shape[0] < 2:
        raise DatasetIntegrityError("too few scorable training rows")
    params = config.estimator_params()
    estimator = IsolationForest(**params).fit(train_matrix)
    train_scores = anomaly_scores(estimator, train_matrix)
    threshold = ThresholdSpec(
        method="training_score_quantile",
        quantile=config.threshold_quantile,
        value=float(np.quantile(train_scores, config.threshold_quantile)),
        selected_on_split="train",
        rationale=(
            "review-priority convention; flags the top "
            f"{(1 - config.threshold_quantile) * 100:g}% of training scores; "
            "validation/test never used for selection"
        ),
    )

    artifact_sha = write_estimator(output, estimator)
    metadata = ModelAMetadata(
        model_version=MODEL_VERSION,
        created_at_utc=datetime.now(UTC),
        artifact_file=ARTIFACT_FILE,
        artifact_sha256=artifact_sha,
        dataset=dataset,
        features=contracts,
        metadata_columns=METADATA_COLUMNS,
        preprocessing=preprocessing,
        estimator=EstimatorSpec(
            class_name="sklearn.ensemble.IsolationForest",
            params=params,
            runtime_versions={
                "python": platform.python_version(),
                "scikit-learn": sklearn.__version__,
                "numpy": np.__version__,
                "joblib": joblib.__version__,
                "platform": platform.platform(terse=True),
            },
        ),
        threshold=threshold,
        training_rows_used=int(train_matrix.shape[0]),
        training_rows_excluded=int(len(train.sample_ids) - train_matrix.shape[0]),
        score_definition=SCORE_DEFINITION,
        intended_use=INTENDED_USE,
        limitations=LIMITATIONS,
    )
    write_metadata(output, metadata)

    detector: NasaEnvironmentAnomalyDetector = load_model_a(output)
    results = {name: detector.score_parsed(splits[name].parsed) for name in SPLITS}
    if not np.array_equal(_scored(results["train"]), train_scores):
        raise RuntimeError("reloaded artifact does not reproduce training scores")

    split_matrices: dict[str, FloatMatrix] = {}
    reference: dict[str, FloatVector] = {}
    for name in ("validation", "test"):
        prepared = apply_preprocessing(preprocessing, splits[name].parsed.matrix)
        split_matrices[name] = prepared.matrix[prepared.scorable]
        reference[name] = _scored(results[name])
    evaluation = Evaluation(
        evaluation_version=EVALUATION_VERSION,
        model_id=metadata.model_id,
        model_version=metadata.model_version,
        artifact_sha256=metadata.artifact_sha256,
        dataset_manifest_sha256=dataset.manifest_sha256,
        supervised_metrics=None,
        supervised_metrics_reason="no anomaly ground-truth labels exist",
        threshold_method=threshold.method,
        threshold_quantile=threshold.quantile,
        threshold_value=threshold.value,
        splits={
            # Candidate thresholds are compared on train/validation only; test is
            # evaluated once, at the fixed pre-declared threshold.
            name: _split_report(
                splits[name].parsed,
                results[name],
                train_scores,
                config,
                () if name == "test" else config.sensitivity_quantiles,
            )
            for name in SPLITS
        },
        seed_stability=_stability(
            train_matrix, split_matrices, reference, train_scores, config
        ),
        notes=(
            "Train scores are in-sample.",
            "Validation and test are scored with train-fitted preprocessing, "
            "estimator and threshold only.",
        ),
    )
    _json_dump(output / "evaluation.json", asdict(evaluation))
    (output / "EVALUATION_REPORT.md").write_text(
        _report_markdown(metadata, evaluation), encoding="utf-8"
    )
    return TrainingOutcome(output=output, metadata=metadata, evaluation=evaluation)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    defaults = TrainingConfig()
    parser.add_argument("--random-state", type=int, default=defaults.random_state)
    parser.add_argument("--n-estimators", type=int, default=defaults.n_estimators)
    parser.add_argument("--max-samples", type=int, default=defaults.max_samples)
    parser.add_argument(
        "--threshold-quantile", type=float, default=defaults.threshold_quantile
    )
    args = parser.parse_args(argv)
    config = TrainingConfig(
        random_state=args.random_state,
        n_estimators=args.n_estimators,
        max_samples=args.max_samples,
        threshold_quantile=args.threshold_quantile,
    )
    outcome = train_model_a(args.data_dir, args.output, config)
    summary = {
        "output": str(outcome.output),
        "artifact_sha256": outcome.metadata.artifact_sha256,
        "threshold": None
        if outcome.metadata.threshold is None
        else outcome.metadata.threshold.value,
        "rows": {
            name: rec.rows for name, rec in outcome.metadata.dataset.splits.items()
        },
    }
    sys.stdout.write(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
