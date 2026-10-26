"""Secure filesystem storage and pre-load integrity verification for ML model artifacts."""

import contextlib
import hashlib
import hmac
import json
import logging
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib

from finsignal.ml.constants import FEATURE_VERSION
from finsignal.ml.exceptions import (
    ModelIntegrityError,
    ModelNotFoundError,
    SchemaValidationError,
)
from finsignal.ml.model import IsolationForestModel

logger = logging.getLogger(__name__)


class ModelArtifactStore:
    """Manages serialization, directory containment, and SHA-256 verification of model artifacts.

    Security Controls:
    - Path Containment: All artifact paths are strictly constrained within base_dir.
      Path traversal attempts (e.g. '../') are detected and rejected before disk I/O.
    - Two-Phase Atomic Write: Artifacts are written to temporary files and atomically renamed.
    - Cryptographic Digest: Computes SHA-256 digest of serialized bytes immediately upon write.
    - Pre-Deserialization Verification: Before joblib.load() is called, the file bytes are read
      and their SHA-256 digest is compared against the expected hash using constant-time comparison.
      If the digest fails to match, deserialization is aborted and ModelIntegrityError is raised.
    - Deserialization Boundary: Asserts that deserialized object is an IsolationForestModel instance
      and matches the current FEATURE_VERSION contract.
    """

    def __init__(self, base_dir: Path | str) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_contained_path(self, relative_path: str | Path) -> Path:
        """Resolve path and verify that it is strictly contained within base_dir."""
        raw_path = Path(relative_path)
        if raw_path.is_absolute():
            resolved = raw_path.resolve()
        else:
            resolved = (self.base_dir / raw_path).resolve()

        try:
            resolved.relative_to(self.base_dir)
        except ValueError as err:
            msg = f"Path traversal attempt rejected. Path '{relative_path}' escapes base directory."
            raise ValueError(msg) from err

        return resolved

    def save(
        self,
        model_id: uuid.UUID,
        model: IsolationForestModel,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[str, str]:
        """Save model artifact to disk with atomic write, SHA-256 hashing, and companion metadata.

        Returns:
            tuple of (relative_artifact_uri, sha256_hash)
        """
        model_dir = self.base_dir / str(model_id)
        model_dir.mkdir(parents=True, exist_ok=True)

        artifact_filename = "model.joblib"
        final_artifact_path = model_dir / artifact_filename
        temp_artifact_path = model_dir / f"model.{uuid.uuid4().hex[:8]}.tmp"

        try:
            # 1. Write joblib to temporary file
            joblib.dump(model, temp_artifact_path)

            # 2. Compute SHA-256 of the persisted bytes
            hasher = hashlib.sha256()
            with open(temp_artifact_path, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            sha256_hash = hasher.hexdigest()

            # 3. Atomic rename to final path
            os.replace(temp_artifact_path, final_artifact_path)

            # 4. Save companion metadata.json
            meta_path = model_dir / "metadata.json"
            meta_payload = {
                "model_id": str(model_id),
                "artifact_filename": artifact_filename,
                "sha256_hash": sha256_hash,
                "feature_version": model.feature_version,
                "created_at": datetime.now(UTC).isoformat(),
                "parameters": model.get_params(),
                "user_metadata": metadata or {},
            }
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta_payload, f, indent=2)

            relative_uri = f"{model_id}/{artifact_filename}"
            return relative_uri, sha256_hash

        except Exception:
            if temp_artifact_path.exists():
                with contextlib.suppress(OSError):
                    temp_artifact_path.unlink()
            raise

    def load(
        self,
        artifact_uri: str | Path,
        expected_hash: str,
    ) -> IsolationForestModel:
        """Verify SHA-256 digest and deserialize model artifact safely.

        Raises:
            ModelNotFoundError: If artifact file does not exist.
            ModelIntegrityError: If SHA-256 hash fails to match expected_hash.
            SchemaValidationError: If deserialized object violates feature version contract.
        """
        artifact_path = self._resolve_contained_path(artifact_uri)

        if not artifact_path.exists() or not artifact_path.is_file():
            msg = f"Model artifact file was not found at '{artifact_path}'"
            raise ModelNotFoundError(
                message=msg, details={"artifact_uri": str(artifact_uri)}
            )

        # Read bytes and verify SHA-256 BEFORE passing stream to joblib.load
        hasher = hashlib.sha256()
        with open(artifact_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        computed_hash = hasher.hexdigest()

        if not hmac.compare_digest(computed_hash.lower(), expected_hash.lower()):
            msg = (
                f"Model artifact integrity verification failed for '{artifact_uri}'. "
                f"Computed hash '{computed_hash}' does not match expected hash '{expected_hash}'."
            )
            raise ModelIntegrityError(
                message=msg,
                details={
                    "artifact_uri": str(artifact_uri),
                    "computed_hash": computed_hash,
                    "expected_hash": expected_hash,
                },
            )

        # Deserialize only after integrity verification passes
        loaded_obj = joblib.load(artifact_path)

        if not isinstance(loaded_obj, IsolationForestModel):
            msg = f"Deserialized artifact is not an IsolationForestModel: {type(loaded_obj).__name__}"
            raise SchemaValidationError(message=msg)

        if loaded_obj.feature_version != FEATURE_VERSION:
            msg = (
                f"Feature version mismatch in loaded model. Expected '{FEATURE_VERSION}', "
                f"got '{loaded_obj.feature_version}'."
            )
            raise SchemaValidationError(
                message=msg,
                details={
                    "expected_version": FEATURE_VERSION,
                    "loaded_version": loaded_obj.feature_version,
                },
            )

        return loaded_obj
