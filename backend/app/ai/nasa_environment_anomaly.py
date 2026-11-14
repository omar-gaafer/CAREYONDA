"""Model A inference: NASA RR-1 ISS environmental anomaly scoring.

Pure domain logic. It validates rows against the exact environmental feature
contract, applies train-fitted preprocessing, scores rows with an injected
estimator, and applies an optional unsupervised review threshold. It performs no
file, network, or model-runtime I/O; loading lives in ``app.storage``.

``anomaly_score`` is ``-score_samples`` from an Isolation Forest: the average
path-length based score in (0, 1], where larger means "easier to isolate" relative
to the training sample. It is not a probability, not calibrated, and not a
clinical, physiological, or spacecraft hazard measure.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

import numpy as np
from numpy.typing import NDArray

from app.features.environmental import environmental_schema
from app.schemas.nasa_environment_model import (
    FeatureContract,
    PreprocessingSpec,
    ThresholdSpec,
)

FloatMatrix = NDArray[np.float64]
FloatVector = NDArray[np.float64]

SAMPLE_ID_COLUMN = "sample_id"
EVENT_TIME_COLUMN = "event_time_utc"
METADATA_COLUMNS: tuple[str, str] = (SAMPLE_ID_COLUMN, EVENT_TIME_COLUMN)

# Nullable features whose blanks are structural (no earlier reading inside the
# window, or the first row of a split) and may be filled with the training median.
IMPUTABLE_SUFFIXES = ("_delta",)
IMPUTABLE_NAMES = ("gap_seconds",)
# Primary measurements: filling these would present absent evidence as typical.
ABSTAIN_SUFFIXES = ("_value", "_mean_30m")
BINARY_SUFFIXES = ("_missing",)
NON_NEGATIVE_SUFFIXES = ("_count_30m",)
NON_NEGATIVE_NAMES = ("gap_seconds",)

PREPROCESSING_METHOD = (
    "Drop metadata columns. Blank cells are missing, never zero. Each *_missing "
    "indicator must equal 1 exactly when its *_value is blank (schema definition). "
    "Structurally nullable delta/gap features are filled with the training-split "
    "median; rows missing any value/mean feature abstain. Non-indicator features "
    "constant in training cause abstention when they take a different value. "
    "No scaling (tree model)."
)


def _indicator_pairs(names: Sequence[str]) -> tuple[tuple[str, int, int], ...]:
    """(indicator name, indicator position, matching *_value position)."""
    pairs = []
    for position, name in enumerate(names):
        if name.endswith(BINARY_SUFFIXES):
            metric = name.removesuffix(BINARY_SUFFIXES[0])
            pairs.append((name, position, list(names).index(f"{metric}_value")))
    return tuple(pairs)


def _check_missing_indicators(
    matrix_row: FloatVector, pairs: tuple[tuple[str, int, int], ...], row: int
) -> None:
    """Schema: ``*_missing`` is 1 iff the timestamp has no valid ``*_value``."""
    for name, flag_position, value_position in pairs:
        value_missing = math.isnan(matrix_row[value_position])
        if (matrix_row[flag_position] == 1.0) != value_missing:
            raise ModelAInputError(
                f"row {row} column {name}: indicator contradicts value presence"
            )


class ModelAInputError(ValueError):
    """Input rows violate the Model A feature contract. Messages omit values."""


class ModelAPreprocessingError(ValueError):
    """Preprocessing cannot be fitted from the supplied training matrix."""


class ScoringEstimator(Protocol):
    """Fitted estimator boundary; satisfied by scikit-learn's IsolationForest."""

    def score_samples(self, X: FloatMatrix) -> FloatVector: ...


@dataclass(frozen=True)
class ModelProvenance:
    model_id: str
    model_version: str
    artifact_sha256: str
    feature_schema_version: str
    dataset_manifest_sha256: str
    threshold_method: str | None


@dataclass(frozen=True)
class AnomalyResult:
    """One scored or abstained row; status distinguishes the two explicitly."""

    sample_id: str
    event_time_utc: datetime
    status: Literal["scored", "abstained"]
    anomaly_score: float | None
    threshold: float | None
    is_flagged: bool | None
    imputed_features: tuple[str, ...]
    abstention_reasons: tuple[str, ...]
    provenance: ModelProvenance


@dataclass(frozen=True)
class ParsedRows:
    """Validated input split into traceability metadata and a feature matrix."""

    sample_ids: tuple[str, ...]
    event_times: tuple[datetime, ...]
    matrix: FloatMatrix  # NaN marks a missing (blank) cell


def expected_features() -> tuple[FeatureContract, ...]:
    """Exact ordered feature contract from the checked-in environmental schema."""
    features = environmental_schema()["features"]
    assert isinstance(features, list)
    return tuple(FeatureContract.model_validate(item) for item in features)


def feature_names() -> tuple[str, ...]:
    return tuple(feature.name for feature in expected_features())


def validate_columns(columns: Sequence[str]) -> None:
    """Require exactly ``sample_id, event_time_utc`` followed by schema features."""
    expected = (*METADATA_COLUMNS, *feature_names())
    actual = tuple(columns)
    if actual == expected:
        return
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    if missing or extra:
        raise ModelAInputError(
            f"column set mismatch; missing={missing} unexpected={extra}"
        )
    if len(actual) != len(set(actual)):
        raise ModelAInputError("duplicate columns")
    raise ModelAInputError("columns are not in the required schema order")


def _parse_cell(raw: object, column: str, row: int) -> float:
    if raw is None or raw == "":
        return math.nan
    if isinstance(raw, bool):
        raise ModelAInputError(f"row {row} column {column}: boolean not accepted")
    if isinstance(raw, int | float):
        value = float(raw)
    elif isinstance(raw, str):
        try:
            value = float(raw)
        except ValueError:
            raise ModelAInputError(f"row {row} column {column}: not a number") from None
    else:
        raise ModelAInputError(f"row {row} column {column}: unsupported type")
    if not math.isfinite(value):
        raise ModelAInputError(
            f"row {row} column {column}: non-finite value; use a blank for missing"
        )
    return value


def _check_structural(value: float, contract: FeatureContract, row: int) -> None:
    """Definitional constraints from the schema, not physiological ranges."""
    name = contract.name
    if math.isnan(value):
        if not contract.nullable:
            raise ModelAInputError(f"row {row} column {name}: required value missing")
        return
    if name.endswith(BINARY_SUFFIXES) and value not in (0.0, 1.0):
        raise ModelAInputError(f"row {row} column {name}: flag must be 0 or 1")
    non_negative = name.endswith(NON_NEGATIVE_SUFFIXES) or name in NON_NEGATIVE_NAMES
    if non_negative and value < 0:
        raise ModelAInputError(f"row {row} column {name}: must be non-negative")
    if name.endswith(NON_NEGATIVE_SUFFIXES) and not value.is_integer():
        raise ModelAInputError(f"row {row} column {name}: count must be integral")


def _parse_time(raw: object, row: int) -> datetime:
    if not isinstance(raw, str) or not raw:
        raise ModelAInputError(f"row {row}: event_time_utc must be an ISO string")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        raise ModelAInputError(f"row {row}: event_time_utc is not ISO-8601") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ModelAInputError(f"row {row}: event_time_utc lacks a timezone offset")
    return parsed


def parse_rows(columns: Sequence[str], rows: Sequence[Sequence[object]]) -> ParsedRows:
    """Validate a table whose header must match the exact Model A column order."""
    validate_columns(columns)
    contracts = expected_features()
    pairs = _indicator_pairs([contract.name for contract in contracts])
    width = len(METADATA_COLUMNS) + len(contracts)
    sample_ids: list[str] = []
    times: list[datetime] = []
    matrix = np.full((len(rows), len(contracts)), np.nan, dtype=np.float64)
    for index, row in enumerate(rows):
        if len(row) != width:
            raise ModelAInputError(f"row {index}: expected {width} cells")
        sample_id = row[0]
        if not isinstance(sample_id, str) or not sample_id:
            raise ModelAInputError(f"row {index}: sample_id must be a non-empty string")
        sample_ids.append(sample_id)
        times.append(_parse_time(row[1], index))
        for position, contract in enumerate(contracts):
            value = _parse_cell(row[position + 2], contract.name, index)
            _check_structural(value, contract, index)
            matrix[index, position] = value
        _check_missing_indicators(matrix[index], pairs, index)
    return ParsedRows(tuple(sample_ids), tuple(times), matrix)


def parse_records(records: Sequence[Mapping[str, object]]) -> ParsedRows:
    """Validate mapping rows; keys must be exactly the metadata and feature names."""
    columns = (*METADATA_COLUMNS, *feature_names())
    expected = set(columns)
    for index, record in enumerate(records):
        keys = set(record)
        if keys != expected:
            raise ModelAInputError(
                f"row {index}: key mismatch; missing={sorted(expected - keys)} "
                f"unexpected={sorted(keys - expected)}"
            )
    return parse_rows(
        columns, [[record[name] for name in columns] for record in records]
    )


def fit_preprocessing(
    contracts: Sequence[FeatureContract], train_matrix: FloatMatrix
) -> PreprocessingSpec:
    """Fit imputation and support checks from the training split only."""
    names = tuple(contract.name for contract in contracts)
    if train_matrix.ndim != 2 or train_matrix.shape[1] != len(names):
        raise ModelAPreprocessingError("training matrix shape does not match schema")
    impute: dict[str, float] = {}
    abstain: list[str] = []
    constants: dict[str, float] = {}
    for position, contract in enumerate(contracts):
        column = train_matrix[:, position]
        present = column[~np.isnan(column)]
        if present.size == 0:
            raise ModelAPreprocessingError(
                f"feature {contract.name} has no observed training values"
            )
        if contract.nullable:
            imputable = (
                contract.name.endswith(IMPUTABLE_SUFFIXES)
                or contract.name in IMPUTABLE_NAMES
            )
            if imputable:
                impute[contract.name] = float(np.median(present))
            elif contract.name.endswith(ABSTAIN_SUFFIXES):
                abstain.append(contract.name)
            else:
                raise ModelAPreprocessingError(
                    f"no missing-value policy for nullable feature {contract.name}"
                )
        # Missingness indicators are validated against value presence instead; a
        # set indicator already makes the row abstain via its missing *_value.
        indicator = contract.name.endswith(BINARY_SUFFIXES)
        if not indicator and np.all(present == present[0]):
            constants[contract.name] = float(present[0])
    return PreprocessingSpec(
        feature_names=names,
        impute_median=impute,
        abstain_if_missing=tuple(abstain),
        training_constants=constants,
        method=PREPROCESSING_METHOD,
    )


@dataclass(frozen=True)
class PreparedMatrix:
    matrix: FloatMatrix  # rows that can be scored, fully imputed
    scorable: NDArray[np.bool_]
    imputed: tuple[tuple[str, ...], ...]
    reasons: tuple[tuple[str, ...], ...]


def apply_preprocessing(spec: PreprocessingSpec, matrix: FloatMatrix) -> PreparedMatrix:
    """Impute structural gaps and mark rows that must abstain, without mutation."""
    names = spec.feature_names
    if matrix.ndim != 2 or matrix.shape[1] != len(names):
        raise ModelAInputError("feature matrix shape does not match schema")
    filled = matrix.copy()
    scorable = np.ones(matrix.shape[0], dtype=np.bool_)
    imputed: list[tuple[str, ...]] = []
    reasons: list[tuple[str, ...]] = []
    index = {name: position for position, name in enumerate(names)}
    for row in range(matrix.shape[0]):
        row_imputed: list[str] = []
        row_reasons: list[str] = []
        for name, median in spec.impute_median.items():
            if math.isnan(filled[row, index[name]]):
                filled[row, index[name]] = median
                row_imputed.append(name)
        for name in spec.abstain_if_missing:
            if math.isnan(filled[row, index[name]]):
                row_reasons.append(f"missing_required:{name}")
        for name, constant in spec.training_constants.items():
            value = filled[row, index[name]]
            if not math.isnan(value) and value != constant:
                row_reasons.append(f"outside_training_support:{name}")
        if row_reasons or np.isnan(filled[row]).any():
            scorable[row] = False
            if not row_reasons:
                row_reasons.append("missing_unhandled")
        imputed.append(tuple(row_imputed))
        reasons.append(tuple(row_reasons))
    return PreparedMatrix(filled, scorable, tuple(imputed), tuple(reasons))


def anomaly_scores(estimator: ScoringEstimator, matrix: FloatMatrix) -> FloatVector:
    """Higher means more anomalous; see module docstring for interpretation."""
    if matrix.shape[0] == 0:
        return np.empty(0, dtype=np.float64)
    return np.asarray(-estimator.score_samples(matrix), dtype=np.float64)


class NasaEnvironmentAnomalyDetector:
    """Scores validated NASA RR-1 environmental rows with a fitted estimator."""

    def __init__(
        self,
        estimator: ScoringEstimator,
        preprocessing: PreprocessingSpec,
        threshold: ThresholdSpec | None,
        provenance: ModelProvenance,
    ) -> None:
        if preprocessing.feature_names != feature_names():
            raise ModelAInputError("preprocessing does not match the feature schema")
        self._estimator = estimator
        self._preprocessing = preprocessing
        self._threshold = threshold
        self._provenance = provenance

    @property
    def provenance(self) -> ModelProvenance:
        return self._provenance

    @property
    def threshold(self) -> ThresholdSpec | None:
        return self._threshold

    def score_table(
        self, columns: Sequence[str], rows: Sequence[Sequence[object]]
    ) -> tuple[AnomalyResult, ...]:
        return self.score_parsed(parse_rows(columns, rows))

    def score_records(
        self, records: Sequence[Mapping[str, object]]
    ) -> tuple[AnomalyResult, ...]:
        return self.score_parsed(parse_records(records))

    def score_parsed(self, parsed: ParsedRows) -> tuple[AnomalyResult, ...]:
        prepared = apply_preprocessing(self._preprocessing, parsed.matrix)
        scores = anomaly_scores(self._estimator, prepared.matrix[prepared.scorable])
        cutoff = None if self._threshold is None else self._threshold.value
        results: list[AnomalyResult] = []
        cursor = 0
        for row, sample_id in enumerate(parsed.sample_ids):
            score: float | None = None
            flagged: bool | None = None
            if prepared.scorable[row]:
                score = float(scores[cursor])
                cursor += 1
                flagged = None if cutoff is None else score >= cutoff
            results.append(
                AnomalyResult(
                    sample_id=sample_id,
                    event_time_utc=parsed.event_times[row],
                    status="scored" if score is not None else "abstained",
                    anomaly_score=score,
                    threshold=cutoff,
                    is_flagged=flagged,
                    imputed_features=prepared.imputed[row],
                    abstention_reasons=prepared.reasons[row],
                    provenance=self._provenance,
                )
            )
        return tuple(results)
