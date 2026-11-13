"""Optional offline Model A application service, separate from hazard ranking."""

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from pickle import UnpicklingError
from typing import Protocol

from pydantic import ValidationError

from app.ai.nasa_environment_anomaly import (
    AnomalyResult,
)
from app.features.environmental import build_environment_features
from app.schemas.environmental_anomaly_context import (
    LIMITATIONS,
    REPLAY_LIMITATIONS,
    EnvironmentalAnomalyContext,
    EnvironmentalSample,
    ModelIdentity,
)
from app.storage.nasa_environment_model_store import (
    ModelArtifactError,
    load_model_a,
    read_metadata,
)


class EnvironmentalDetector(Protocol):
    def score_records(
        self, records: Sequence[dict[str, object]]
    ) -> tuple[AnomalyResult, ...]: ...


class EnvironmentalAnomalyInputError(ValueError):
    """Invalid stream, chronology, source or availability declarations."""


class EnvironmentalAnomalyService:
    def __init__(
        self,
        detector: EnvironmentalDetector | None,
        *,
        model_state: str = "available",
    ) -> None:
        if model_state not in {"available", "unavailable", "incompatible"}:
            raise ValueError("unsupported model state")
        if (detector is None) != (model_state != "available"):
            raise ValueError("detector and availability disagree")
        self._detector = detector
        self._state = model_state

    @classmethod
    def from_artifact(cls, directory: Path) -> "EnvironmentalAnomalyService":
        """Explicit opt-in loading of a trusted local artifact; never a fallback."""
        if (
            not (directory / "metadata.json").is_file()
            or not (directory / "model.joblib").is_file()
        ):
            return cls(None, model_state="unavailable")
        try:
            metadata = read_metadata(directory)
            if (
                metadata.model_version != "1.1.0"
                or metadata.dataset.schema_version != "1.0.0"
            ):
                return cls(None, model_state="incompatible")
            detector = load_model_a(directory)
        except (
            ModelArtifactError,
            ValidationError,
            ValueError,
            OSError,
            EOFError,
            UnpicklingError,
            ImportError,
            AttributeError,
            TypeError,
        ):
            return cls(None, model_state="incompatible")
        return cls(detector)

    def assess(
        self,
        samples: Sequence[EnvironmentalSample],
        *,
        assessed_at: datetime,
    ) -> tuple[EnvironmentalAnomalyContext, ...]:
        samples = tuple(
            EnvironmentalSample.model_validate(s.model_dump()) for s in samples
        )
        if assessed_at.tzinfo is None or assessed_at.utcoffset() is None:
            raise EnvironmentalAnomalyInputError("aware assessment time required")
        if len({s.sample_id for s in samples}) != len(samples):
            raise EnvironmentalAnomalyInputError("duplicate sample IDs")
        if any(
            a.event_time_utc >= b.event_time_utc
            for a, b in zip(samples, samples[1:], strict=False)
        ):
            raise EnvironmentalAnomalyInputError(
                "stream timestamps must strictly increase"
            )
        if any(s.evidence_available_at > assessed_at for s in samples):
            raise EnvironmentalAnomalyInputError("future-unavailable evidence")
        if any(s.scope.data_origin != "real" for s in samples):
            raise EnvironmentalAnomalyInputError(
                "NASA model cannot score synthetic context"
            )
        if samples and any(s.scope != samples[0].scope for s in samples):
            raise EnvironmentalAnomalyInputError(
                "batch must belong to one environmental stream"
            )
        if len({s.assessment_mode for s in samples}) > 1:
            raise EnvironmentalAnomalyInputError(
                "live and replay assessments must be separate batches"
            )
        for sample in samples:
            rebuilt = build_environment_features(sample.observations)
            current = next(
                (s for s in rebuilt if s.timestamp == sample.event_time_utc), None
            )
            if current is None or any(
                f.value != current.values[f.name]
                or set(f.observation_ids) != set(current.evidence[f.name])
                for f in sample.features
            ):
                raise EnvironmentalAnomalyInputError(
                    "features or lineage disagree with environmental transformation"
                )
        if self._detector is None:
            return tuple(
                EnvironmentalAnomalyContext.model_validate(
                    {
                        **_availability_context(s),
                        "sample": s,
                        "assessed_at": assessed_at,
                        "model": None,
                        "availability": "unavailable"
                        if self._state == "unavailable"
                        else "available",
                        "compatibility": "unknown"
                        if self._state == "unavailable"
                        else "incompatible",
                        "status": "abstained",
                        "anomaly_score": None,
                        "threshold": None,
                        "threshold_method": None,
                        "imputed_features": (),
                        "abstention_reasons": (f"model_{self._state}",),
                    }
                )
                for s in samples
            )
        records: list[dict[str, object]] = [
            {
                "sample_id": s.sample_id,
                "event_time_utc": s.event_time_utc.isoformat(),
                **{f.name: f.value for f in s.features},
            }
            for s in samples
        ]
        results = self._detector.score_records(records)
        if len(results) != len(samples):
            raise EnvironmentalAnomalyInputError("detector result count mismatch")
        contexts = []
        for sample, result in zip(samples, results, strict=True):
            if (
                result.sample_id != sample.sample_id
                or result.event_time_utc != sample.event_time_utc
            ):
                raise EnvironmentalAnomalyInputError(
                    "detector result identity mismatch"
                )
            provenance = result.provenance
            try:
                identity = ModelIdentity.model_validate(
                    {
                        "model_id": provenance.model_id,
                        "model_version": provenance.model_version,
                        "feature_schema_version": provenance.feature_schema_version,
                        "artifact_sha256": provenance.artifact_sha256,
                        "dataset_manifest_sha256": provenance.dataset_manifest_sha256,
                    }
                )
            except ValidationError as exc:
                raise EnvironmentalAnomalyInputError(
                    "incompatible model identity"
                ) from exc
            status = (
                "abstained"
                if result.status == "abstained"
                else (
                    "unassessed"
                    if result.is_flagged is None
                    else ("flagged" if result.is_flagged else "not_flagged")
                )
            )
            contexts.append(
                EnvironmentalAnomalyContext.model_validate(
                    {
                        **_availability_context(sample),
                        "sample": sample,
                        "assessed_at": assessed_at,
                        "model": identity,
                        "availability": "available",
                        "compatibility": "compatible",
                        "status": status,
                        "anomaly_score": result.anomaly_score,
                        "threshold": result.threshold,
                        "threshold_method": provenance.threshold_method,
                        "imputed_features": result.imputed_features,
                        "abstention_reasons": result.abstention_reasons,
                    }
                )
            )
        return tuple(contexts)


def _availability_context(sample: EnvironmentalSample) -> dict[str, object]:
    replay = sample.assessment_mode == "historical_replay"
    return {
        "assessment_mode": sample.assessment_mode,
        "historical_source_availability": sample.historical_source_availability,
        "replay_acquired_at": sample.replay_acquired_at,
        "source_event_time": sample.event_time_utc,
        "evidence_availability_scope": "careyonda_replay"
        if replay
        else "source_stream",
        "limitations": (*LIMITATIONS, *REPLAY_LIMITATIONS) if replay else LIMITATIONS,
    }
