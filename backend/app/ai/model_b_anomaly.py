"""Policy-neutral Model B inference boundary; no fitting or deserialization."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Protocol

from app.features.temporal_features import SampleAnchor, build_features
from app.schemas.model_b import (
    FEATURE_ORDER,
    ModelBFinding,
    ModelBInput,
    ThresholdPolicy,
    VerifiedModelB,
)


class ModelBError(ValueError):
    """Input identity, feature, or estimator failure without sensitive values."""


class ScoreSamples(Protocol):
    def score_samples(self, values: Sequence[Sequence[float]]) -> Sequence[float]:
        """Original sklearn orientation: lower means more anomalous."""
        ...


@dataclass(frozen=True)
class ModelBBinding:
    mission_id: str
    astronaut_id: str
    spacecraft_id: str
    compartment_id: str
    dataset_id: str
    run_id: str
    dataset_manifest_sha256: str


@dataclass(frozen=True)
class AcquisitionReceipt:
    dataset_manifest_sha256: str
    acquired_at: datetime
    reference: str


class ModelBService:
    """Receipts/scorer supplied by trusted composition, never by inference input.

    Missing model/provenance never triggers synthetic fallback. The existing
    published IsolationForest implementation is retained separately unchanged.
    """

    def __init__(
        self,
        binding: ModelBBinding,
        *,
        model: VerifiedModelB | None,
        scorer: ScoreSamples | None,
        receipts: tuple[AcquisitionReceipt, ...] = (),
        policy: ThresholdPolicy | None = None,
    ) -> None:
        if (model is None) != (scorer is None):
            raise ModelBError("model and scorer must coexist")
        if (
            model is not None
            and policy is not None
            and policy.model_artifact_sha256 != model.metadata.artifact_sha256
        ):
            raise ModelBError("threshold policy belongs to another artifact")
        self.binding, self.model, self.scorer = binding, model, scorer
        self.receipts, self.policy = receipts, policy

    def assess(self, sample: ModelBInput) -> ModelBFinding:
        sample = ModelBInput.model_validate(sample.model_dump())
        actual = ModelBBinding(
            sample.context.mission_id,
            sample.context.astronaut_id,
            sample.context.spacecraft_id,
            sample.context.compartment_id,
            sample.dataset_id,
            sample.run_id,
            sample.dataset_manifest_sha256,
        )
        if actual != self.binding:
            raise ModelBError("assessment scope or dataset identity mismatch")
        anchor = SampleAnchor.model_validate(sample.context.model_dump())
        generated = build_features([e.observation for e in sample.evidence], [anchor])[
            0
        ]
        if (
            tuple(generated.values[n] for n in FEATURE_ORDER) != sample.values
            or tuple(generated.evidence[n] for n in FEATURE_ORDER)
            != sample.feature_evidence_ids
            or generated.window_observation_ids != sample.window_observation_ids
        ):
            raise ModelBError("features do not reproduce from original window evidence")
        reasons: list[str] = []
        if sample.availability_mode == "retrospective":
            if sample.acquired_at is None or not any(
                receipt.dataset_manifest_sha256 == sample.dataset_manifest_sha256
                and receipt.acquired_at == sample.acquired_at
                and receipt.reference == sample.acquisition_reference
                and receipt.acquired_at.tzinfo is not None
                and receipt.acquired_at <= sample.assessed_at
                for receipt in self.receipts
            ):
                reasons.append("acquisition_not_verified")
        if any(
            e.observation.ingested_at is not None
            and e.observation.ingested_at > sample.assessed_at
            for e in sample.evidence
        ):
            reasons.append("future_unavailable_evidence")
        if sample.availability_mode == "prospective" and any(
            not e.available_at(sample.assessed_at, "prospective")
            for e in sample.evidence
        ):
            reasons.append("prospective_availability_unknown")
        if all(
            value is None
            for name, value in zip(FEATURE_ORDER, sample.values, strict=True)
            if not name.endswith("_missing")
        ):
            reasons.append("no_usable_observed_metrics")
        if self.model is None or self.scorer is None:
            reasons.append("model_unavailable")
        metadata = self.model.metadata if self.model else None
        if reasons or metadata is None or self.scorer is None:
            return ModelBFinding(
                sample=sample,
                model=metadata,
                policy=self.policy,
                metadata_sha256=self.model.metadata_sha256 if self.model else None,
                evidence_availability_scope="careyonda_replay"
                if sample.availability_mode == "retrospective"
                else "declared_source_stream",
                anomaly_score=None,
                flagged=None,
                status="abstained",
                imputed_features=(),
                imputation_values=(None,) * 16,
                reasons=tuple(reasons),
            )
        missing = tuple(
            n for n, v in zip(FEATURE_ORDER, sample.values, strict=True) if v is None
        )
        imputation = tuple(
            metadata.imputation_medians[i] if v is None else None
            for i, v in enumerate(sample.values)
        )
        row = tuple(
            metadata.imputation_medians[i] if v is None else v
            for i, v in enumerate(sample.values)
        )
        try:
            scores = tuple(self.scorer.score_samples((row,)))
            if len(scores) != 1 or not isfinite(scores[0]):
                raise ModelBError("estimator returned invalid scores")
            score = -float(scores[0])
        except (ValueError, TypeError, RuntimeError, OverflowError) as exc:
            raise ModelBError("estimator scoring failed") from exc
        flag = self.policy.decide(score) if self.policy else None
        return ModelBFinding(
            sample=sample,
            model=metadata,
            policy=self.policy,
            metadata_sha256=self.model.metadata_sha256 if self.model else None,
            evidence_availability_scope="careyonda_replay"
            if sample.availability_mode == "retrospective"
            else "declared_source_stream",
            anomaly_score=score,
            flagged=flag,
            status="unassessed"
            if flag is None
            else ("flagged" if flag else "not_flagged"),
            imputed_features=missing,
            imputation_values=imputation,
            reasons=("owner_approved_threshold_missing",) if flag is None else (),
        )
