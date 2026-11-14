"""Model C tests with SYNTHETIC longitudinal records only.

Every value below is invented to exercise software behaviour. None is a clinical,
physiological or NASA reference value, and passing tests do not validate the method.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest
from pydantic import ValidationError

from app.ai.isolation_confinement import (
    DEFAULT_RESEARCH_PARAMETERS,
    METHOD_VERSION,
    ModelCInputError,
    assess_isolation_confinement,
)
from app.schemas.isolation_confinement import (
    LIMITATIONS,
    CategoricalIndicatorAssessment,
    IsolationConfinementAssessment,
    ModelCRequest,
    NumericIndicatorAssessment,
)
from app.schemas.observation import AstronautScope

T0 = datetime(2030, 1, 1, tzinfo=UTC)
REFERENCE_DAYS = 14
STABLE_SLEEP = (7.0, 7.5, 6.8, 7.2, 7.1, 6.9, 7.4, 7.3, 7.0, 6.7, 7.6, 7.2, 7.0, 7.1)
SUBJECT = "syn-crew-a"


def evidence(
    oid: str,
    metric: str,
    measurement: dict[str, Any],
    day: float,
    *,
    subject: str = SUBJECT,
    quality: dict[str, Any] | None = None,
    origin: str = "simulated",
    sensor: str | None = "syn-sensor",
    ingest_delay: timedelta | None = timedelta(minutes=5),
) -> dict[str, Any]:
    timestamp = T0 + timedelta(days=day, hours=7)
    provenance: dict[str, Any] = {
        "source_type": "simulator",
        "source_id": "syn-source",
        "method": "synthetic-fixture",
        "origin": "simulated",
        "simulation": {
            "scenario_id": "syn-longitudinal",
            "run_id": "syn-run",
            "generator_version": "test-1",
            "seed": 1,
        },
    }
    if origin == "measured":
        provenance = {
            "source_type": "sensor",
            "source_id": "syn-source",
            "method": "synthetic-fixture",
            "origin": "measured",
        }
    elif origin == "self_reported":
        provenance = {
            "source_type": "crew_report",
            "source_id": "syn-source",
            "method": "synthetic-fixture",
            "origin": "self_reported",
        }
    return {
        "dataset_id": "syn-dataset",
        "run_id": "syn-run",
        "sensor_id": sensor,
        "sensor_epoch": None if sensor is None else "epoch-1",
        "data_origin": "synthetic" if origin == "simulated" else "real",
        "temporal_support": {"start": timestamp - timedelta(hours=6), "end": timestamp},
        "observation": {
            "schema_version": "1.0.0",
            "observation_id": oid,
            "timestamp": timestamp,
            "ingested_at": None if ingest_delay is None else timestamp + ingest_delay,
            "domain": "behavioral",
            "metric": metric,
            "scope": {
                "kind": "astronaut",
                "astronaut_id": subject,
                "mission_id": "syn-mission",
            },
            "measurement": measurement,
            "quality": quality or {"status": "valid"},
            "provenance": provenance,
        },
    }


def sleep(oid: str, hours: float, day: float, **kwargs: Any) -> dict[str, Any]:
    return evidence(
        oid,
        "sleep_duration",
        {"kind": "numeric", "value": hours, "unit": "h"},
        day,
        **kwargs,
    )


def fatigue(oid: str, category: str, day: float, **kwargs: Any) -> dict[str, Any]:
    return evidence(
        oid,
        "fatigue_self_report",
        {"kind": "categorical", "value": category},
        day,
        **kwargs,
    )


def history(
    values: tuple[float, ...] = STABLE_SLEEP,
    window: tuple[float, ...] = (7.1, 7.0, 7.2),
) -> list[dict[str, Any]]:
    rows = [sleep(f"syn-sleep-{d:02d}", v, d) for d, v in enumerate(values)]
    rows += [
        sleep(f"syn-sleep-w{i}", v, REFERENCE_DAYS + i) for i, v in enumerate(window)
    ]
    return rows


def request(
    rows: list[dict[str, Any]],
    *,
    subject: str = SUBJECT,
    data_origin: str = "synthetic",
    sensor: str | None = "syn-sensor",
    indicators: tuple[str, ...] = ("sleep_duration",),
    parameters: dict[str, Any] | None = None,
    anomaly_policy: dict[str, Any] | None = None,
    assessed_day: float = REFERENCE_DAYS + 3.5,
) -> ModelCRequest:
    payload: dict[str, Any] = {
        "schema_version": "1.0.0",
        "interpretation": "research_only",
        "subject_id": subject,
        "mission_id": "syn-mission",
        "dataset_id": "syn-dataset",
        "run_id": "syn-run",
        "data_origin": data_origin,
        "assessed_at": T0 + timedelta(days=assessed_day),
        "reference_interval": {"start": T0, "end": T0 + timedelta(days=REFERENCE_DAYS)},
        "assessment_interval": {
            "start": T0 + timedelta(days=REFERENCE_DAYS),
            "end": T0 + timedelta(days=assessed_day),
        },
        "sources": [
            {
                "indicator": indicator,
                "instrument_kind": "self_report_form"
                if indicator == "fatigue_self_report"
                else "sensor",
                "source_id": "syn-source",
                "sensor_id": sensor,
                "sensor_epoch": None if sensor is None else "epoch-1",
            }
            for indicator in indicators
        ],
        "parameters": parameters or DEFAULT_RESEARCH_PARAMETERS.model_dump(),
        "evidence": rows,
    }
    if anomaly_policy is not None:
        payload["anomaly_policy"] = anomaly_policy
    return ModelCRequest.model_validate(payload)


def numeric(result: IsolationConfinementAssessment) -> NumericIndicatorAssessment:
    item = next(i for i in result.indicators if i.indicator == "sleep_duration")
    assert isinstance(item, NumericIndicatorAssessment)
    return item


def categorical(
    result: IsolationConfinementAssessment,
) -> CategoricalIndicatorAssessment:
    item = next(i for i in result.indicators if i.indicator == "fatigue_self_report")
    assert isinstance(item, CategoricalIndicatorAssessment)
    return item


def approved_policy(value: float = 3.0) -> dict[str, Any]:
    calibration = {
        "artifact_id": "syn-calibration",
        "artifact_version": "1.0.0",
        "source": "synthetic test declaration, not an approval",
    }
    return {
        "schema_version": "1.0.0",
        "interpretation": "research_only",
        "policy_id": "syn-sleep-policy",
        "policy_version": "1.0.0",
        "metric": "sleep_duration",
        "unit": "h",
        "score_definition": "absolute_deviation_over_raw_mad",
        "threshold_governance": "approved_research",
        "governance_source": "synthetic test only",
        "calibration": calibration,
        "threshold": {
            "value": value,
            "comparison": "greater_than",
            "approval_reference": "SYNTHETIC-TEST-ONLY",
            "approved_at": T0,
            "calibration": calibration,
        },
    }


# ------------------------------------------------------------------- stable history


def test_stable_history_scores_against_own_baseline() -> None:
    result = assess_isolation_confinement(request(history()))
    item = numeric(result)
    assert result.status == "assessed" and item.status == "assessed"
    assert item.baseline.status == "ready"
    assert item.baseline.summary.occupied_bins == REFERENCE_DAYS
    assert item.baseline.median_value == pytest.approx(7.1)
    assert item.baseline.raw_mad == pytest.approx(0.15)  # median |bin median - 7.1|
    assert item.summary.findings == item.summary.scored == 3
    assert item.summary.maximum_raw_mad_score is not None
    assert item.summary.maximum_raw_mad_score <= 1.0
    assert all(f.threshold_status == "unassessed" for f in item.findings)
    assert result.safety_status == "not_evaluated"
    assert set(LIMITATIONS) <= set(result.limitations)
    assert "not a z-score" in item.findings[0].explanation


def test_contracts_define_no_composite_risk_probability_or_diagnosis_field() -> None:
    forbidden = ("risk", "probab", "severity", "diagnos", "confidence", "composite")
    for model in (
        IsolationConfinementAssessment,
        NumericIndicatorAssessment,
        CategoricalIndicatorAssessment,
    ):
        for name in model.model_fields:
            assert not any(word in name for word in forbidden), (model, name)
    assert "score" not in IsolationConfinementAssessment.model_fields


# ------------------------------------------------------------------------ deviations


def test_shortened_sleep_is_reported_below_reference_without_flagging() -> None:
    result = assess_isolation_confinement(request(history(window=(5.0, 4.8, 5.2))))
    item = numeric(result)
    assert item.summary.below_reference == 3
    assert item.baseline.raw_mad is not None
    assert item.summary.median_raw_mad_score == pytest.approx(
        (7.1 - 5.0) / item.baseline.raw_mad
    )
    assert item.summary.threshold_exceeded == 0  # no approved threshold by default
    assert all(f.direction == "below" for f in item.findings)
    assert "below the personal reference median" in item.findings[0].explanation


def test_synthetic_approved_research_threshold_is_applied_exactly() -> None:
    result = assess_isolation_confinement(
        request(history(window=(5.0, 7.0, 7.2)), anomaly_policy=approved_policy(3.0))
    )
    statuses = [f.threshold_status for f in numeric(result).findings]
    assert statuses == ["exceeded", "not_exceeded", "not_exceeded"]
    assert numeric(result).summary.threshold_exceeded == 1


def test_threshold_approval_after_assessment_is_rejected() -> None:
    policy = approved_policy()
    policy["threshold"]["approved_at"] = T0 + timedelta(days=60)
    with pytest.raises(ValidationError, match="approval cannot follow"):
        request(history(), anomaly_policy=policy)


# --------------------------------------------------------- insufficient / flat / gaps


def test_short_history_abstains_without_reference_statistics() -> None:
    rows = history(values=STABLE_SLEEP[:3])
    item = numeric(assess_isolation_confinement(request(rows)))
    assert item.status == "abstained"
    assert item.baseline.status == "insufficient_reference"
    assert item.baseline.median_value is None and item.baseline.raw_mad is None
    assert "insufficient_occupied_bins" in item.abstention_reasons
    assert all(f.score_status == "insufficient_reference" for f in item.findings)
    assert all(f.raw_mad_score is None for f in item.findings)


def test_empty_history_abstains_explicitly() -> None:
    rows = [sleep("syn-sleep-w0", 7.0, REFERENCE_DAYS)]
    result = assess_isolation_confinement(request(rows))
    assert result.status == "abstained"
    assert result.abstention_reasons == ("no_indicator_assessed",)
    assert "no_valid_reference_evidence" in numeric(result).abstention_reasons


def test_flat_reference_reports_deviation_but_never_a_score() -> None:
    rows = history(values=(7.0,) * REFERENCE_DAYS, window=(6.0,))
    item = numeric(assess_isolation_confinement(request(rows)))
    assert item.baseline.status == "flat_reference" and item.baseline.raw_mad == 0
    finding = item.findings[0]
    assert finding.score_status == "flat_reference"
    assert finding.raw_mad_score is None and finding.signed_deviation == -1.0
    assert item.status == "abstained"


def test_large_gap_in_history_abstains() -> None:
    values = list(STABLE_SLEEP)
    rows = [
        sleep(f"syn-sleep-{d:02d}", v, d)
        for d, v in enumerate(values)
        if not 3 <= d <= 8
    ]
    rows.append(sleep("syn-sleep-w0", 7.0, REFERENCE_DAYS))
    item = numeric(assess_isolation_confinement(request(rows)))
    assert "reference_gap_exceeds_maximum" in item.abstention_reasons


# ---------------------------------------------------------------------- missingness


def test_missing_and_suspect_records_are_preserved_not_zeroed() -> None:
    rows = history()
    rows[2] = evidence(
        "syn-sleep-02",
        "sleep_duration",
        {"kind": "unavailable", "reason": "not_received"},
        2,
        quality={"status": "missing", "reason_codes": ["sensor_dropout"]},
    )
    rows[-1] = sleep(
        "syn-sleep-w2",
        7.2,
        REFERENCE_DAYS + 2,
        quality={"status": "suspect", "reason_codes": ["syn_artifact"]},
    )
    rows[-2] = evidence(
        "syn-sleep-w1",
        "sleep_duration",
        {"kind": "unavailable", "reason": "sensor_offline"},
        REFERENCE_DAYS + 1,
        quality={"status": "unavailable", "reason_codes": ["sensor_offline"]},
    )
    item = numeric(assess_isolation_confinement(request(rows)))
    excluded = {
        e.evidence.observation.observation_id: e.reason_codes
        for e in item.baseline.excluded
    }
    assert "quality_missing" in excluded["syn-sleep-02"]
    assert "measurement_unavailable" in excluded["syn-sleep-02"]
    by_id = {f.evidence.observation.observation_id: f for f in item.findings}
    assert by_id["syn-sleep-w1"].score_status == "unsupported"
    assert by_id["syn-sleep-w1"].original_value is None
    assert by_id["syn-sleep-w1"].quality_limitations == ("sensor_offline",)
    assert by_id["syn-sleep-w2"].score_status == "invalid_observation"
    assert by_id["syn-sleep-w2"].original_value == 7.2
    assert by_id["syn-sleep-w0"].score_status == "scored"


def test_conflicting_simultaneous_reference_readings_are_excluded() -> None:
    rows = history()
    rows.append(sleep("syn-sleep-dup", 3.0, 4))
    item = numeric(assess_isolation_confinement(request(rows)))
    reasons = {
        e.evidence.observation.observation_id: e.reason_codes
        for e in item.baseline.excluded
    }
    assert reasons["syn-sleep-dup"] == ("conflicting_simultaneous_readings",)
    assert reasons["syn-sleep-04"] == ("conflicting_simultaneous_readings",)


# ----------------------------------------------------- sources, origin and subjects


def test_unknown_sensor_identity_is_unsupported() -> None:
    rows = [{**r, "sensor_id": None, "sensor_epoch": None} for r in history()]
    item = numeric(assess_isolation_confinement(request(rows, sensor=None)))
    assert item.baseline.status == "unsupported"
    assert item.abstention_reasons == ("sensor_identity_unavailable",)
    assert all(f.score_status == "unsupported" for f in item.findings)


def test_records_from_another_source_are_excluded_not_mixed() -> None:
    rows = history()
    rows[0] = {**rows[0], "sensor_id": "other-sensor"}
    item = numeric(assess_isolation_confinement(request(rows)))
    first = item.baseline.excluded[0]
    assert first.reason_codes == ("source_or_sensor_mismatch",)


def test_multiple_subjects_are_assessed_independently() -> None:
    other = "syn-crew-b"
    rows_b = [
        {**sleep(f"syn-b-{d:02d}", v + 1.0, d, subject=other)}
        for d, v in enumerate(STABLE_SLEEP)
    ] + [sleep("syn-b-w0", 8.1, REFERENCE_DAYS, subject=other)]
    a = numeric(assess_isolation_confinement(request(history())))
    b = numeric(assess_isolation_confinement(request(rows_b, subject=other)))
    assert a.baseline.median_value == pytest.approx(7.1)
    assert b.baseline.median_value == pytest.approx(8.1)
    assert a.baseline.profile_id != b.baseline.profile_id
    scopes = [e.observation.scope for e in b.baseline.included]
    assert all(isinstance(s, AstronautScope) for s in scopes)
    assert {s.astronaut_id for s in scopes if isinstance(s, AstronautScope)} == {other}


def test_other_subjects_evidence_is_rejected_not_silently_pooled() -> None:
    rows = history() + [sleep("syn-b-01", 9.0, 1, subject="syn-crew-b")]
    with pytest.raises(ValidationError, match="another subject"):
        request(rows)


def test_mixed_synthetic_and_real_origin_is_rejected() -> None:
    rows = history() + [sleep("syn-real-declared", 7.0, 1.5, origin="measured")]
    with pytest.raises(ValidationError, match="data origin differs"):
        request(rows)


def test_provenance_nature_is_reported_per_indicator() -> None:
    rows = [
        sleep(f"syn-m-{d:02d}", v, d, origin="measured")
        for d, v in enumerate(STABLE_SLEEP)
    ] + [sleep("syn-m-w0", 7.0, REFERENCE_DAYS, origin="measured")]
    rows += [
        fatigue(f"syn-f-{d:02d}", "rested", d, origin="self_reported") for d in range(8)
    ]
    rows.append(fatigue("syn-f-w0", "tired", REFERENCE_DAYS, origin="self_reported"))
    result = assess_isolation_confinement(
        request(
            rows,
            data_origin="real",
            indicators=("sleep_duration", "fatigue_self_report"),
        )
    )
    assert numeric(result).evidence_provenance == ("direct_measurement",)
    assert numeric(result).registry_reporting_mode == "unspecified_by_contract"
    assert categorical(result).evidence_provenance == ("self_report",)
    assert categorical(result).registry_reporting_mode == "self_report"


def test_unsupported_metric_is_rejected() -> None:
    row = evidence(
        "syn-hr", "heart_rate", {"kind": "numeric", "value": 60.0, "unit": "bpm"}, 1
    )
    row["observation"]["domain"] = "physiological"
    with pytest.raises(ValidationError, match="no declared Model C source"):
        request(history() + [row])


# ------------------------------------------------------------------- time handling


def test_non_utc_input_is_normalised_and_boundaries_are_half_open() -> None:
    plus_two = timezone(timedelta(hours=2))
    rows = history()
    boundary = sleep("syn-sleep-boundary", 7.0, 0)
    end = T0 + timedelta(days=REFERENCE_DAYS)
    boundary["observation"]["timestamp"] = end.astimezone(plus_two).isoformat()
    boundary["observation"]["ingested_at"] = end + timedelta(minutes=1)
    boundary["temporal_support"] = {"start": end - timedelta(hours=6), "end": end}
    item = numeric(assess_isolation_confinement(request(rows + [boundary])))
    included = {e.observation.observation_id for e in item.baseline.included}
    assert "syn-sleep-boundary" in included  # (start, end]: the end instant belongs
    assert item.baseline.included[0].observation.timestamp.tzinfo == UTC
    assert "syn-sleep-boundary" not in {
        f.evidence.observation.observation_id for f in item.findings
    }


def test_prospective_mode_excludes_late_or_unknown_ingestion() -> None:
    params = {
        **DEFAULT_RESEARCH_PARAMETERS.model_dump(),
        "availability_mode": "prospective",
    }
    rows = history()
    rows[-1] = sleep(
        "syn-sleep-w2", 7.2, REFERENCE_DAYS + 2, ingest_delay=timedelta(days=5)
    )
    rows[0] = sleep("syn-sleep-00", 7.0, 0, ingest_delay=None)
    item = numeric(assess_isolation_confinement(request(rows, parameters=params)))
    excluded = {
        e.evidence.observation.observation_id: e.reason_codes
        for e in item.baseline.excluded
    }
    assert "unavailable_at_assessment" in excluded["syn-sleep-00"]
    late = next(
        f
        for f in item.findings
        if f.evidence.observation.observation_id == "syn-sleep-w2"
    )
    assert late.score_status == "unsupported"


def test_reference_too_old_for_assessment_time_abstains() -> None:
    item = numeric(
        assess_isolation_confinement(
            request(history(), assessed_day=REFERENCE_DAYS + 8)
        )
    )
    assert "reference_too_old" in item.abstention_reasons


def test_invalid_period_ordering_is_rejected() -> None:
    with pytest.raises(ValidationError, match="reference end <= assessment start"):
        request(history(), assessed_day=REFERENCE_DAYS)  # empty assessment period


def test_parameters_that_cannot_fit_reference_raise_input_error() -> None:
    params = {**DEFAULT_RESEARCH_PARAMETERS.model_dump(), "minimum_occupied_bins": 30}
    with pytest.raises(ModelCInputError, match="research parameters"):
        assess_isolation_confinement(request(history(), parameters=params))


# ----------------------------------------------------------------- categorical path


def test_fatigue_reports_are_counted_without_any_score() -> None:
    rows = [
        fatigue(f"syn-f-{d:02d}", c, d)
        for d, c in enumerate(["rested"] * 10 + ["tired"] * 4)
    ]
    rows += [
        fatigue(f"syn-f-w{i}", c, REFERENCE_DAYS + i)
        for i, c in enumerate(["tired", "very_tired", "very_tired"])
    ]
    item = categorical(
        assess_isolation_confinement(request(rows, indicators=("fatigue_self_report",)))
    )
    assert item.status == "assessed"
    counts = {
        c.category: (c.reference_count, c.assessment_count) for c in item.categories
    }
    assert counts == {"rested": (10, 0), "tired": (4, 1), "very_tired": (0, 2)}
    assert "no score, distance or threshold" in item.explanation
    assert "score" not in type(item).model_fields


def test_fatigue_with_too_few_reference_reports_abstains() -> None:
    rows = [fatigue(f"syn-f-{d:02d}", "rested", d) for d in range(3)]
    rows.append(fatigue("syn-f-w0", "tired", REFERENCE_DAYS))
    item = categorical(
        assess_isolation_confinement(request(rows, indicators=("fatigue_self_report",)))
    )
    assert item.status == "abstained"
    assert item.abstention_reasons == ("insufficient_reference_reports",)


def test_partial_assessment_when_one_indicator_abstains() -> None:
    rows = history() + [
        fatigue("syn-f-00", "rested", 1),
        fatigue("syn-f-w0", "tired", REFERENCE_DAYS),
    ]
    result = assess_isolation_confinement(
        request(rows, indicators=("sleep_duration", "fatigue_self_report"))
    )
    assert result.status == "partially_assessed"
    assert result.abstention_reasons == ()


# ------------------------------------------------------- determinism and lineage


def test_assessment_is_deterministic_and_round_trips() -> None:
    first = assess_isolation_confinement(request(history()))
    second = assess_isolation_confinement(request(list(reversed(history()))))
    assert first.indicators == second.indicators  # input order does not matter
    again = assess_isolation_confinement(request(history()))
    assert again.model_dump_json() == first.model_dump_json()
    restored = IsolationConfinementAssessment.model_validate_json(
        first.model_dump_json()
    )
    assert restored == first
    assert first.method_version == METHOD_VERSION


def test_findings_trace_to_exact_evidence_and_profile() -> None:
    item = numeric(assess_isolation_confinement(request(history())))
    for finding in item.findings:
        assert finding.evidence_ids == (finding.evidence.observation.observation_id,)
        assert finding.profile_lineage_ids == (item.baseline.profile_id,)
        assert finding.evidence.observation.provenance.simulation is not None
    bins = {oid for b in item.baseline.summary.bins for oid in b.observation_ids}
    assert bins == {e.observation.observation_id for e in item.baseline.included}


def test_evidence_outside_both_periods_is_listed_as_unused() -> None:
    rows = history() + [sleep("syn-sleep-late", 7.0, REFERENCE_DAYS + 4)]
    result = assess_isolation_confinement(request(rows))
    assert result.unused_evidence_ids == ("syn-sleep-late",)


@pytest.mark.parametrize("mode", ["retrospective", "prospective"])
@pytest.mark.parametrize("outside", ["future", "reference_overlap", "before_window"])
def test_numeric_target_support_must_fit_assessment(mode: str, outside: str) -> None:
    rows = history()
    original = request(rows)
    target = rows[-1]
    if outside == "future":
        target["temporal_support"]["end"] = original.assessed_at + timedelta(days=1)
    else:
        target["temporal_support"]["start"] = (
            original.reference_interval.start + timedelta(seconds=1)
            if outside == "reference_overlap"
            else original.assessment_interval.start
        )
    parameters = DEFAULT_RESEARCH_PARAMETERS.model_dump()
    parameters["availability_mode"] = mode
    result = assess_isolation_confinement(request(rows, parameters=parameters))
    finding = numeric(result).findings[-1]
    assert finding.score_status == "unsupported"
    assert finding.raw_mad_score is None
    assert finding.signed_deviation is None
    assert finding.threshold_status == "unassessed"
    assert finding.abstention_reasons == ("target_support_outside_assessment",)


def test_reversed_support_interval_rejected_before_inference() -> None:
    rows = history()
    target = rows[-1]
    target["temporal_support"] = {
        "start": target["observation"]["timestamp"] + timedelta(seconds=1),
        "end": target["observation"]["timestamp"],
    }
    with pytest.raises(ValidationError, match="interval start must not follow end"):
        request(rows)


# ------------------------------------- categorical temporal support & missingness


def _fatigue_history() -> list[dict[str, Any]]:
    return [fatigue(f"syn-f-{d:02d}", "rested", d) for d in range(10)]


def test_fatigue_support_outside_either_period_is_excluded_not_counted() -> None:
    rows = _fatigue_history()
    original = request(
        rows + [fatigue("syn-f-w0", "tired", REFERENCE_DAYS)],
        indicators=("fatigue_self_report",),
    )
    ref_end = original.reference_interval.end
    leaking_reference = fatigue("syn-f-13", "very_tired", REFERENCE_DAYS - 1)
    leaking_reference["temporal_support"]["end"] = ref_end + timedelta(hours=1)
    overlapping_window = fatigue("syn-f-w1", "very_tired", REFERENCE_DAYS + 1)
    overlapping_window["temporal_support"]["start"] = ref_end - timedelta(hours=1)
    beyond_window = fatigue("syn-f-w2", "very_tired", REFERENCE_DAYS + 2)
    beyond_window["temporal_support"]["end"] = original.assessed_at + timedelta(days=1)
    item = categorical(
        assess_isolation_confinement(
            request(
                rows
                + [
                    leaking_reference,
                    fatigue("syn-f-w0", "tired", REFERENCE_DAYS),
                    overlapping_window,
                    beyond_window,
                ],
                indicators=("fatigue_self_report",),
            )
        )
    )
    assert item.assessment_report_ids == ("syn-f-w0",)
    assert "syn-f-13" not in item.reference_report_ids
    excluded = {
        e.evidence.observation.observation_id: e.reason_codes for e in item.excluded
    }
    for oid in ("syn-f-13", "syn-f-w1", "syn-f-w2"):
        assert "support_outside_period" in excluded[oid], oid
    counts = {
        c.category: (c.reference_count, c.assessment_count) for c in item.categories
    }
    assert counts["very_tired"] == (0, 0)


def test_missing_and_suspect_fatigue_reports_are_never_counted_as_valid() -> None:
    rows = _fatigue_history()
    rows.append(
        evidence(
            "syn-f-missing",
            "fatigue_self_report",
            {"kind": "unavailable", "reason": "not_received"},
            10,
            quality={"status": "missing", "reason_codes": ["syn_not_received"]},
        )
    )
    rows.append(
        fatigue(
            "syn-f-suspect",
            "very_tired",
            11,
            quality={"status": "suspect", "reason_codes": ["syn_artifact"]},
        )
    )
    rows.append(
        evidence(
            "syn-f-w-missing",
            "fatigue_self_report",
            {"kind": "unavailable", "reason": "sensor_offline"},
            REFERENCE_DAYS,
            quality={"status": "unavailable", "reason_codes": ["sensor_offline"]},
        )
    )
    item = categorical(
        assess_isolation_confinement(request(rows, indicators=("fatigue_self_report",)))
    )
    assert len(item.reference_report_ids) == 10
    assert item.assessment_report_ids == ()
    excluded = {
        e.evidence.observation.observation_id: e.reason_codes for e in item.excluded
    }
    assert {"quality_missing", "measurement_unavailable"} <= set(
        excluded["syn-f-missing"]
    )
    assert excluded["syn-f-suspect"] == ("quality_suspect",)
    assert "measurement_unavailable" in excluded["syn-f-w-missing"]
    assert item.status == "abstained"
    assert item.abstention_reasons == ("no_valid_assessment_reports",)


def test_prospective_fatigue_report_without_ingestion_time_is_excluded() -> None:
    params = {
        **DEFAULT_RESEARCH_PARAMETERS.model_dump(),
        "availability_mode": "prospective",
    }
    rows = _fatigue_history() + [
        fatigue("syn-f-w0", "tired", REFERENCE_DAYS, ingest_delay=None)
    ]
    item = categorical(
        assess_isolation_confinement(
            request(rows, indicators=("fatigue_self_report",), parameters=params)
        )
    )
    excluded = {
        e.evidence.observation.observation_id: e.reason_codes for e in item.excluded
    }
    assert "unavailable_at_assessment" in excluded["syn-f-w0"]
    assert item.status == "abstained"


@pytest.mark.parametrize("mode", ["retrospective", "prospective"])
def test_unavailable_sleep_target_is_never_scored(mode: str) -> None:
    rows = history()
    rows[-1] = evidence(
        "syn-sleep-w2",
        "sleep_duration",
        {"kind": "unavailable", "reason": "not_received"},
        REFERENCE_DAYS + 2,
        quality={"status": "missing", "reason_codes": ["syn_not_received"]},
    )
    parameters = {**DEFAULT_RESEARCH_PARAMETERS.model_dump(), "availability_mode": mode}
    item = numeric(assess_isolation_confinement(request(rows, parameters=parameters)))
    finding = item.findings[-1]
    assert finding.score_status == "unsupported"
    assert finding.original_value is None and finding.raw_mad_score is None
    assert finding.abstention_reasons == ("target_measurement_unavailable",)
    assert finding.quality_limitations == ("syn_not_received",)
    assert item.summary.scored == len(item.findings) - 1


# ------------------------------------------------------------- provenance retained


def test_result_retains_scope_time_source_and_evidence_provenance() -> None:
    rows = (
        history() + _fatigue_history() + [fatigue("syn-f-w0", "tired", REFERENCE_DAYS)]
    )
    req = request(rows, indicators=("sleep_duration", "fatigue_self_report"))
    result = assess_isolation_confinement(req)
    assert (result.subject_id, result.mission_id) == (SUBJECT, "syn-mission")
    assert (result.dataset_id, result.run_id, result.data_origin) == (
        "syn-dataset",
        "syn-run",
        "synthetic",
    )
    assert result.assessed_at == req.assessed_at
    assert result.reference_interval == req.reference_interval
    assert result.assessment_interval == req.assessment_interval
    sleep_item = numeric(result)
    assert sleep_item.unit == "h"
    for finding in sleep_item.findings:
        obs = finding.evidence.observation
        assert finding.evidence_ids == (obs.observation_id,)
        assert obs.ingested_at is not None and obs.timestamp <= obs.ingested_at
        assert obs.provenance.source_id == "syn-source"
        assert (finding.evidence.sensor_id, finding.evidence.sensor_epoch) == (
            "syn-sensor",
            "epoch-1",
        )
        assert obs.scope.kind == "astronaut"
    fatigue_item = categorical(result)
    assert [c.category for c in fatigue_item.categories] == [
        "rested",
        "tired",
        "very_tired",
    ]
    assert fatigue_item.assessment_report_ids == ("syn-f-w0",)
    assert result.safety_status == "not_evaluated"
