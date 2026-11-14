"""Verify caller-trusted Model B bytes; never deserialize, fit or write artifacts."""

from hashlib import sha256

from app.schemas.model_b import ModelBMetadata, VerifiedModelB


class ModelBArtifactError(ValueError):
    """Untrusted, inconsistent or incompatible artifact metadata."""


def verify_model_b_artifact(
    *,
    metadata_bytes: bytes,
    artifact_bytes: bytes,
    expected_metadata_sha256: str,
    expected_artifact_sha256: str,
    trusted_local_artifact: bool,
    runtime_versions: dict[str, str],
) -> VerifiedModelB:
    """Pins must come from a separately trusted source; a hash is not authenticity.

    This verifies bytes only. A future trusted loader must consume these same bytes
    and verify actual fitted preprocessing/parameters before injecting a scorer.
    """
    if trusted_local_artifact is not True:
        raise ModelBArtifactError("trusted-local opt-in required")
    if (
        sha256(metadata_bytes).hexdigest() != expected_metadata_sha256
        or sha256(artifact_bytes).hexdigest() != expected_artifact_sha256
    ):
        raise ModelBArtifactError("artifact or metadata manifest pin mismatch")
    metadata = ModelBMetadata.model_validate_json(metadata_bytes)
    if metadata.artifact_sha256 != expected_artifact_sha256:
        raise ModelBArtifactError("metadata artifact digest mismatch")
    if metadata.runtime_versions != runtime_versions:
        raise ModelBArtifactError("artifact runtime mismatch")
    return VerifiedModelB(metadata, expected_metadata_sha256)
