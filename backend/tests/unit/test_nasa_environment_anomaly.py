"""Model A inference contract tests using SYNTHETIC rows only."""

from __future__ import annotations

import math
from datetime import UTC, datetime

import numpy as np
import pytest
from sklearn.ensemble import IsolationForest  # type: ignore[import-untyped]

from app.ai.nasa_environment_anomaly import (
    AnomalyResult,
    FloatMatrix,
    FloatVector,
    ModelAInputError,
    ModelAPreprocessingError,
    ModelProvenance,
    NasaEnvironmentAnomalyDetector,
    apply_preprocessing,
    expected_features,
    feature_names,
    fit_preprocessing,
    parse_records,
    parse_rows,
    validate_columns,
)
from app.schemas.nasa_environment_model import PreprocessingSpec, ThresholdSpec
from tests.model_a_fixtures import COLUMNS, record, synthetic_rows

START = datetime(2030, 1, 1, tzinfo=UTC)
NAMES = feature_names()
CO2_VALUE = NAMES.index("cabin_co2_concentration_value")
PROVENANCE = ModelProvenance(
    model_id="synthetic-test-model",
    model_version="0.0.0",
    artifact_sha256="0" * 64,
    feature_schema_version="1.0.0",
    dataset_manifest_sha256="1" * 64,
    threshold_method="training_score_quantile",
)


class FirstFeatureEstimator:
    """Test double: anomaly score equals the CO2 value feature exactly."""

    def score_samples(self, X: FloatMatrix) -> FloatVector:
        return np.asarray(-X[:, CO2_VALUE], dtype=np.float64)


def rows(count: int = 50, seed: int = 0) -> list[list[object]]:
    return synthetic_rows(count, seed, START, "unit")


def mark_missing(row: list[object], metric: str) -> None:
    """Schema-consistent dropout: no current value, so indicator 1, delta blank.

    The 30-minute mean may still be present from earlier readings in the window.
    """
    row[COLUMNS.index(f"{metric}_value")] = ""
    row[COLUMNS.index(f"{metric}_delta")] = ""
    row[COLUMNS.index(f"{metric}_missing")] = 1.0


def fitted_spec(count: int = 50) -> PreprocessingSpec:
    return fit_preprocessing(
        expected_features(), parse_rows(COLUMNS, rows(count)).matrix
    )


def threshold(value: float) -> ThresholdSpec:
    return ThresholdSpec(
        method="training_score_quantile",
        quantile=0.9,
        value=value,
        selected_on_split="train",
        rationale="synthetic test",
    )


# --- feature contract -------------------------------------------------------


def test_contract_is_exact_sixteen_features_in_schema_order() -> None:
    assert len(NAMES) == 16
    assert NAMES[0] == "cabin_co2_concentration_value"
    assert NAMES[-1] == "gap_seconds"
    assert "sample_id" not in NAMES and "event_time_utc" not in NAMES
    units = {feature.name: feature.unit for feature in expected_features()}
    assert units["cabin_co2_concentration_value"] == "ppm"
    assert units["environment_temperature_value"] == "degC"
    assert units["gap_seconds"] == "s"


def test_validate_columns_accepts_exact_order() -> None:
    validate_columns(COLUMNS)


@pytest.mark.parametrize(
    ("columns", "message"),
    [
        (COLUMNS[:-1], "missing=['gap_seconds']"),
        ((*COLUMNS, "radiation_dose"), "unexpected=['radiation_dose']"),
        ((COLUMNS[1], COLUMNS[0], *COLUMNS[2:]), "order"),
        ((*COLUMNS, COLUMNS[-1]), "duplicate"),
        (COLUMNS[2:], "missing=['event_time_utc', 'sample_id']"),
    ],
)
def test_validate_columns_rejects_wrong_sets(
    columns: tuple[str, ...], message: str
) -> None:
    with pytest.raises(ModelAInputError, match=message.replace("[", r"\[")):
        validate_columns(columns)


# --- cell parsing -----------------------------------------------------------


def test_blank_cells_are_missing_not_zero() -> None:
    parsed = parse_rows(COLUMNS, rows(3))
    first = parsed.matrix[0]
    assert math.isnan(first[NAMES.index("cabin_co2_concentration_delta")])
    assert math.isnan(first[NAMES.index("gap_seconds")])
    assert not np.isnan(parsed.matrix[1]).any()
    assert parsed.sample_ids[0] == "synthetic-unit-00000"
    assert parsed.event_times[0] == START


def test_none_is_missing_and_numeric_strings_parse() -> None:
    data = rows(2)
    data[1][2 + NAMES.index("gap_seconds")] = None
    data[1][2 + CO2_VALUE] = "12.5"
    parsed = parse_rows(COLUMNS, data)
    assert math.isnan(parsed.matrix[1, NAMES.index("gap_seconds")])
    assert parsed.matrix[1, CO2_VALUE] == 12.5


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("cabin_co2_concentration_value", "98765.4321xyz", "not a number"),
        ("cabin_co2_concentration_value", "inf", "non-finite"),
        ("cabin_co2_concentration_value", float("nan"), "non-finite"),
        ("cabin_co2_concentration_value", True, "boolean"),
        ("cabin_co2_concentration_value", [1.0], "unsupported type"),
        ("cabin_co2_concentration_missing", 2.0, "flag must be 0 or 1"),
        ("relative_humidity_count_30m", -1.0, "non-negative"),
        ("relative_humidity_count_30m", 2.5, "integral"),
        ("gap_seconds", -3.0, "non-negative"),
        ("environment_temperature_count_30m", "", "required value missing"),
    ],
)
def test_invalid_cells_raise_without_echoing_values(
    column: str, value: object, message: str
) -> None:
    data = rows(2)
    data[1][COLUMNS.index(column)] = value
    with pytest.raises(ModelAInputError, match=message) as caught:
        parse_rows(COLUMNS, data)
    assert "98765" not in str(caught.value)
    assert column in str(caught.value)


@pytest.mark.parametrize(
    ("index", "value", "message"),
    [
        (0, "", "sample_id"),
        (1, "2030-01-01T00:00:00", "timezone"),
        (1, "not-a-time", "ISO-8601"),
        (1, None, "ISO string"),
    ],
)
def test_invalid_metadata_rejected(index: int, value: object, message: str) -> None:
    data = rows(2)
    data[1][index] = value
    with pytest.raises(ModelAInputError, match=message):
        parse_rows(COLUMNS, data)


def test_short_row_rejected() -> None:
    data = rows(2)
    data[1] = data[1][:-1]
    with pytest.raises(ModelAInputError, match="expected 18 cells"):
        parse_rows(COLUMNS, data)


def test_records_require_exact_keys() -> None:
    good = record(rows(2)[1])
    assert parse_records([good]).matrix.shape == (1, 16)
    extra = {**good, "co2_partial_pressure_pa": 1.0}
    with pytest.raises(ModelAInputError, match="unexpected"):
        parse_records([extra])
    missing = {key: value for key, value in good.items() if key != "gap_seconds"}
    with pytest.raises(ModelAInputError, match="missing"):
        parse_records([missing])


def test_non_utc_offset_preserved() -> None:
    data = rows(2)
    data[1][1] = "2030-01-01T02:00:00+02:00"
    parsed = parse_rows(COLUMNS, data)
    assert parsed.event_times[1].utcoffset() is not None
    assert parsed.event_times[1] == START


# --- preprocessing ----------------------------------------------------------


def test_fit_preprocessing_uses_train_medians_ignoring_missing() -> None:
    parsed = parse_rows(COLUMNS, rows(40))
    spec = fit_preprocessing(expected_features(), parsed.matrix)
    gap = parsed.matrix[:, NAMES.index("gap_seconds")]
    assert spec.impute_median["gap_seconds"] == pytest.approx(
        float(np.median(gap[~np.isnan(gap)]))
    )
    assert set(spec.impute_median) == {
        "cabin_co2_concentration_delta",
        "environment_temperature_delta",
        "relative_humidity_delta",
        "gap_seconds",
    }
    assert set(spec.abstain_if_missing) == {
        name for name in NAMES if name.endswith(("_value", "_mean_30m"))
    }
    # Indicators are validated against value presence, not treated as constants.
    assert not any(name.endswith("_missing") for name in spec.training_constants)
    assert spec.training_constants["relative_humidity_count_30m"] == 6.0
    assert spec.feature_names == NAMES


def test_fit_preprocessing_rejects_unobserved_feature_and_bad_shape() -> None:
    matrix = parse_rows(COLUMNS, rows(5)).matrix
    matrix[:, NAMES.index("gap_seconds")] = np.nan
    with pytest.raises(ModelAPreprocessingError, match="gap_seconds"):
        fit_preprocessing(expected_features(), matrix)
    with pytest.raises(ModelAPreprocessingError, match="shape"):
        fit_preprocessing(expected_features(), matrix[:, :3])


def test_apply_imputes_structural_gaps_and_abstains_on_primary_missing() -> None:
    spec = fitted_spec()
    data = rows(4, seed=9)
    mark_missing(data[2], "cabin_co2_concentration")
    matrix = parse_rows(COLUMNS, data).matrix
    original = matrix.copy()
    prepared = apply_preprocessing(spec, matrix)
    np.testing.assert_array_equal(matrix, original)  # input not mutated
    assert prepared.scorable.tolist() == [True, True, False, True]
    assert "gap_seconds" in prepared.imputed[0]
    assert (
        prepared.matrix[0, NAMES.index("gap_seconds")]
        == (spec.impute_median["gap_seconds"])
    )
    assert prepared.reasons[2] == ("missing_required:cabin_co2_concentration_value",)


def test_missing_indicator_row_abstains_only_for_missing_reading() -> None:
    """Indicator=1 with a blank value is schema-valid missing data, not invalid."""
    spec = fitted_spec()  # synthetic training never had a set indicator
    data = rows(3, seed=9)
    mark_missing(data[1], "environment_temperature")
    prepared = apply_preprocessing(spec, parse_rows(COLUMNS, data).matrix)
    assert not prepared.scorable[1]
    assert prepared.reasons[1] == ("missing_required:environment_temperature_value",)
    assert prepared.scorable[2]


@pytest.mark.parametrize(
    ("flag", "value"),
    [(1.0, 21.5), (0.0, "")],  # flag set with a value / flag clear without one
)
def test_contradictory_missing_indicator_is_rejected(
    flag: float, value: object
) -> None:
    data = rows(3, seed=9)
    data[1][COLUMNS.index("relative_humidity_missing")] = flag
    data[1][COLUMNS.index("relative_humidity_value")] = value
    data[1][COLUMNS.index("relative_humidity_delta")] = ""
    with pytest.raises(
        ModelAInputError, match="relative_humidity_missing: indicator contradicts"
    ) as caught:
        parse_rows(COLUMNS, data)
    assert "21.5" not in str(caught.value)


def test_non_indicator_constant_feature_still_abstains() -> None:
    spec = fitted_spec()  # synthetic count_30m is always 6 in training
    data = rows(3, seed=9)
    data[1][COLUMNS.index("relative_humidity_count_30m")] = 5.0
    prepared = apply_preprocessing(spec, parse_rows(COLUMNS, data).matrix)
    assert prepared.reasons[1] == (
        "outside_training_support:relative_humidity_count_30m",
    )


def test_preprocessing_spec_rejects_inconsistent_policy() -> None:
    spec = fitted_spec()
    with pytest.raises(ValueError, match="both imputed and abstaining"):
        PreprocessingSpec(
            feature_names=spec.feature_names,
            impute_median={"gap_seconds": 1.0},
            abstain_if_missing=("gap_seconds",),
            training_constants={},
            method="x",
        )


# --- detector ---------------------------------------------------------------


def detector(
    estimator: object, cutoff: float | None, spec: PreprocessingSpec | None = None
) -> NasaEnvironmentAnomalyDetector:
    return NasaEnvironmentAnomalyDetector(
        estimator=estimator,  # type: ignore[arg-type]  # test doubles/sklearn
        preprocessing=spec or fitted_spec(),
        threshold=None if cutoff is None else threshold(cutoff),
        provenance=PROVENANCE,
    )


def test_threshold_boundary_is_inclusive() -> None:
    data = rows(4, seed=2)
    for index, value in enumerate((9.0, 10.0, 11.0)):
        data[index + 1][2 + CO2_VALUE] = value
    results = detector(FirstFeatureEstimator(), 10.0).score_table(COLUMNS, data[1:])
    assert [r.anomaly_score for r in results] == [9.0, 10.0, 11.0]
    assert [r.is_flagged for r in results] == [False, True, True]
    assert all(r.threshold == 10.0 for r in results)


def test_no_threshold_means_no_decision() -> None:
    results = detector(FirstFeatureEstimator(), None).score_table(COLUMNS, rows(3))
    assert all(r.status == "scored" for r in results)
    assert all(r.is_flagged is None and r.threshold is None for r in results)


def test_abstained_rows_have_no_score_and_keep_traceability() -> None:
    data = rows(3, seed=4)
    data[1][2 + NAMES.index("relative_humidity_mean_30m")] = ""
    results = detector(FirstFeatureEstimator(), 0.0).score_table(COLUMNS, data)
    abstained: AnomalyResult = results[1]
    assert abstained.status == "abstained"
    assert abstained.anomaly_score is None and abstained.is_flagged is None
    assert abstained.sample_id == "synthetic-unit-00001"
    assert abstained.provenance == PROVENANCE
    assert results[0].status == results[2].status == "scored"
    assert results[0].imputed_features  # structural first-row blanks were filled


def test_isolation_forest_scores_are_deterministic_and_rank_outlier_high() -> None:
    train = parse_rows(COLUMNS, rows(200, seed=1))
    spec = fit_preprocessing(expected_features(), train.matrix)
    matrix = apply_preprocessing(spec, train.matrix).matrix

    def fit() -> IsolationForest:
        return IsolationForest(
            n_estimators=50, max_samples=64, random_state=0, n_jobs=1
        ).fit(matrix)

    probe = rows(5, seed=8)
    for position, name in enumerate(NAMES):  # synthetic extreme in every measure
        if name.endswith(("_value", "_mean_30m")):
            probe[3][2 + position] = 1.0e6
    first = detector(fit(), None, spec).score_table(COLUMNS, probe)
    second = detector(fit(), None, spec).score_table(COLUMNS, probe)
    assert [r.anomaly_score for r in first] == [r.anomaly_score for r in second]
    scores = [r.anomaly_score for r in first if r.anomaly_score is not None]
    assert len(scores) == len(probe)
    assert all(0.0 < score <= 1.0 for score in scores)
    assert scores[3] == max(scores)


def test_detector_rejects_mismatched_preprocessing() -> None:
    spec = fitted_spec()
    reordered = PreprocessingSpec(
        feature_names=tuple(reversed(spec.feature_names)),
        impute_median=spec.impute_median,
        abstain_if_missing=spec.abstain_if_missing,
        training_constants=spec.training_constants,
        method=spec.method,
    )
    with pytest.raises(ModelAInputError, match="feature schema"):
        detector(FirstFeatureEstimator(), None, reordered)


def test_empty_input_returns_empty() -> None:
    assert detector(FirstFeatureEstimator(), 1.0).score_table(COLUMNS, []) == ()
