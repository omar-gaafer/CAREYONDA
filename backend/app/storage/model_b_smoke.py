"""Explicit trusted local research smoke CLI; reads inputs, never trains/writes them."""

from __future__ import annotations

import argparse
import csv
import io
import json
from datetime import UTC, datetime
from hashlib import sha256
from math import isclose
from pathlib import Path

from pydantic import BaseModel, ConfigDict, TypeAdapter

from app.ai.model_b_anomaly import AcquisitionReceipt, ModelBBinding, ModelBService
from app.features.temporal_features import SampleAnchor, build_features, feature_schema
from app.schemas.baseline import Ids, ResearchEvidence, TimeInterval
from app.schemas.model_b import (
    FEATURE_ORDER,
    FEATURE_UNITS,
    Digest,
    Finite,
    ModelBContext,
    ModelBInput,
)
from app.schemas.observation import Contract, Identifier, Observation
from app.storage.model_b_v1 import load_trusted_model_b_v1


class MappingRecord(Contract):
    sample_id: Identifier
    context: ModelBContext
    feature_observation_ids: dict[Identifier, Ids]
    window_observation_ids: Ids


class SavedPrediction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    sample_id: Identifier
    episode_id: Identifier
    anomaly_score: Finite
    prediction: int
    threshold: Finite
    status: str
    imputed_features: Ids


class Evaluation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    dataset_file_sha256: dict[str, Digest]
    dataset_manifest_sha256: Digest
    feature_order: tuple[str, ...]
    feature_units: tuple[str, ...]
    final_artifact_predictions: tuple[SavedPrediction, ...]


def run_smoke(
    artifact: Path,
    dataset: Path,
    *,
    expected_artifact_sha256: str,
    expected_manifest_sha256: str,
    trusted_local_artifact: bool,
) -> dict[str, str | int | float]:
    loaded = load_trusted_model_b_v1(
        artifact,
        trusted_local_artifact=trusted_local_artifact,
        expected_artifact_sha256=expected_artifact_sha256,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    evaluation = Evaluation.model_validate_json(loaded.evaluation_bytes)
    manifest_bytes = (dataset / "manifest.json").read_bytes()
    manifest_digest = sha256(manifest_bytes).hexdigest()
    if (
        manifest_digest != loaded.model.metadata.training_manifest_sha256
        or evaluation.dataset_manifest_sha256 != manifest_digest
    ):
        raise ValueError("training dataset manifest mismatch")
    manifest = TypeAdapter(dict[str, object]).validate_json(manifest_bytes)
    data = {
        name: (dataset / name).read_bytes()
        for name in (
            "README.md",
            "evidence_mapping.json",
            "feature_schema.json",
            "features.csv",
            "labels.csv",
            "observations.json",
        )
    }
    hashes = {name: sha256(raw).hexdigest() for name, raw in data.items()}
    if hashes != evaluation.dataset_file_sha256 or manifest.get("sha256") != hashes:
        raise ValueError("dataset payload hash mismatch")
    if (
        json.loads(data["feature_schema.json"]) != feature_schema(300)
        or evaluation.feature_order != FEATURE_ORDER
        or evaluation.feature_units != FEATURE_UNITS
    ):
        raise ValueError("dataset feature schema mismatch")
    observations = TypeAdapter(tuple[Observation, ...]).validate_json(
        data["observations.json"]
    )
    mappings = TypeAdapter(tuple[MappingRecord, ...]).validate_json(
        data["evidence_mapping.json"]
    )
    obs = {o.observation_id: o for o in observations}
    mapping = {m.sample_id: m for m in mappings}
    reader = csv.DictReader(io.StringIO(data["features.csv"].decode()))
    if tuple(reader.fieldnames or ()) != ("sample_id", *FEATURE_ORDER):
        raise ValueError("dataset column mismatch")
    rows = list(reader)
    if (
        len({r["sample_id"] for r in rows}) != len(rows)
        or len(obs) != len(observations)
        or len(mapping) != len(mappings)
    ):
        raise ValueError("duplicate input identities")
    rebuilt = {
        f.anchor.sample_id: f
        for f in build_features(
            observations,
            [SampleAnchor.model_validate(m.context.model_dump()) for m in mappings],
        )
    }
    saved = {p.sample_id: p for p in evaluation.final_artifact_predictions}
    if (
        len(saved) != 780
        or len(saved) != len(evaluation.final_artifact_predictions)
        or not set(saved) <= set(mapping)
    ):
        raise ValueError("exactly 780 distinct recorded holdout inputs required")
    # This is a NEW factual local read receipt, not a reconstructed historic arrival.
    acquired_at = datetime.now(UTC)
    reference = "ai-i1.2-local-verified-dataset-read"
    receipt = AcquisitionReceipt(manifest_digest, acquired_at, reference)
    assessed_at = datetime.now(UTC)
    max_delta = 0.0
    matched = 0
    partially_imputed = 0
    for row in rows:
        sid = row["sample_id"]
        if sid not in saved:
            continue
        m = mapping[sid]
        f = rebuilt[sid]
        prediction = saved[sid]
        values = tuple(None if row[n] == "" else float(row[n]) for n in FEATURE_ORDER)
        if (
            values != tuple(f.values[n] for n in FEATURE_ORDER)
            or m.feature_observation_ids != f.evidence
            or m.window_observation_ids != f.window_observation_ids
        ):
            raise ValueError("feature reconstruction mismatch")
        evidence = []
        for oid in m.window_observation_ids:
            o = obs[oid]
            sim = o.provenance.simulation
            if sim is None:
                raise ValueError("synthetic provenance required")
            evidence.append(
                ResearchEvidence(
                    observation=o,
                    dataset_id="m1_2_seed42",
                    run_id=sim.run_id,
                    sensor_id=None,
                    sensor_epoch=None,
                    data_origin="synthetic",
                    temporal_support=TimeInterval(start=o.timestamp, end=o.timestamp),
                )
            )
        if not evidence:
            raise ValueError("holdout evidence absent")
        run_id = evidence[0].run_id
        sample = ModelBInput(
            dataset_manifest_sha256=manifest_digest,
            dataset_id="m1_2_seed42",
            run_id=run_id,
            context=m.context,
            assessed_at=assessed_at,
            availability_mode="retrospective",
            acquired_at=acquired_at,
            acquisition_reference=reference,
            feature_order=FEATURE_ORDER,
            units=FEATURE_UNITS,
            values=values,
            feature_evidence_ids=tuple(
                m.feature_observation_ids[n] for n in FEATURE_ORDER
            ),
            window_observation_ids=m.window_observation_ids,
            evidence=tuple(evidence),
        )
        c = sample.context
        binding = ModelBBinding(
            c.mission_id,
            c.astronaut_id,
            c.spacecraft_id,
            c.compartment_id,
            sample.dataset_id,
            run_id,
            manifest_digest,
        )
        # Carry experimental configuration with no approval; canonical flag remains null.
        result = ModelBService(
            binding,
            model=loaded.model,
            scorer=loaded.scorer,
            receipts=(receipt,),
            policy=loaded.experimental_policy,
        ).assess(sample)
        original_score = -loaded.scorer.score_raw_samples((values,))[0]
        if (
            result.anomaly_score is None
            or result.status != "unassessed"
            or result.flagged is not None
        ):
            raise ValueError("canonical default must remain scored and unassessed")
        if result.imputed_features != prediction.imputed_features:
            raise ValueError("saved imputation lineage mismatch")
        partially_imputed += bool(result.imputed_features)
        delta = abs(result.anomaly_score - prediction.anomaly_score)
        max_delta = max(max_delta, delta)
        if not isclose(
            result.anomaly_score, prediction.anomaly_score, rel_tol=1e-12, abs_tol=1e-12
        ) or not isclose(
            result.anomaly_score, original_score, rel_tol=1e-12, abs_tol=1e-12
        ):
            raise ValueError("saved score or fitted imputation reproduction failed")
        experimental_flag = result.anomaly_score > loaded.experimental_policy.threshold
        if (
            experimental_flag != bool(prediction.prediction)
            or prediction.threshold != loaded.experimental_policy.threshold
            or prediction.status != ("flagged" if experimental_flag else "not_flagged")
            or c.episode_id != prediction.episode_id
            or c.sample_id in loaded.training_sample_ids
            or c.episode_id in loaded.training_episode_ids
        ):
            raise ValueError("experimental decisions or holdout lineage mismatch")
        matched += 1
    if matched != 780:
        raise ValueError("holdout reproduction incomplete")
    return {
        "samples": matched,
        "experimental_decisions_matched": matched,
        "canonical_unassessed": matched,
        "partially_imputed_samples": partially_imputed,
        "maximum_absolute_score_difference": max_delta,
        "score_absolute_tolerance": 1e-12,
        "score_relative_tolerance": 1e-12,
        "acquired_at": acquired_at.isoformat(),
        "assessed_at": assessed_at.isoformat(),
        "artifact_sha256": expected_artifact_sha256,
        "original_manifest_sha256": loaded.original_manifest_sha256,
        "original_metadata_sha256": loaded.original_metadata_sha256,
        "v2_metadata_sha256": loaded.model.metadata_sha256,
        "threshold": loaded.experimental_policy.threshold,
        "canonical_approval": "pending",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--expected-artifact-sha256", required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--trusted-local-artifact", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            run_smoke(
                args.artifact,
                args.dataset,
                expected_artifact_sha256=args.expected_artifact_sha256,
                expected_manifest_sha256=args.expected_manifest_sha256,
                trusted_local_artifact=args.trusted_local_artifact,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
