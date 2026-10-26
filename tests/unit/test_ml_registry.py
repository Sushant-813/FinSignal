"""Unit tests for Stage 2 ModelArtifactStore, path containment, and SHA-256 pre-deserialization checks (TG-02)."""

import uuid
from pathlib import Path

import numpy as np
import pytest

from finsignal.ml.exceptions import (
    ModelIntegrityError,
    ModelNotFoundError,
    SchemaValidationError,
)
from finsignal.ml.model import IsolationForestModel
from finsignal.ml.registry import ModelArtifactStore


@pytest.fixture
def artifact_store(tmp_path: Path) -> ModelArtifactStore:
    """Provide a ModelArtifactStore rooted in an isolated temporary directory."""
    return ModelArtifactStore(base_dir=tmp_path / "artifacts" / "models")


@pytest.fixture
def trained_model() -> IsolationForestModel:
    """Provide a fitted IsolationForestModel on 30 dummy rows."""
    rng = np.random.default_rng(seed=42)
    X = rng.normal(loc=0.0, scale=1.0, size=(30, 34)).astype(np.float64)
    model = IsolationForestModel(random_state=42)
    model.fit(X)
    return model


def test_artifact_save_and_load_roundtrip(
    artifact_store: ModelArtifactStore,
    trained_model: IsolationForestModel,
) -> None:
    """Verify that a model can be saved, hashed, and loaded with intact predictions."""
    model_id = uuid.uuid4()
    rel_uri, sha256_hash = artifact_store.save(
        model_id=model_id,
        model=trained_model,
        metadata={"author": "test_engineer"},
    )

    assert rel_uri == f"{model_id}/model.joblib"
    assert len(sha256_hash) == 64

    # Load with expected hash
    loaded_model = artifact_store.load(artifact_uri=rel_uri, expected_hash=sha256_hash)
    assert isinstance(loaded_model, IsolationForestModel)
    assert loaded_model.is_fitted
    assert loaded_model.feature_version == "v1.0"

    # Assert predictions are identical
    X_test = np.ones((5, 34), dtype=np.float64)
    orig_scores = trained_model.score_samples(X_test)
    loaded_scores = loaded_model.score_samples(X_test)
    np.testing.assert_array_equal(orig_scores, loaded_scores)


def test_artifact_load_rejects_corrupted_file(
    artifact_store: ModelArtifactStore,
    trained_model: IsolationForestModel,
) -> None:
    """Verify TG-02: Corrupted artifact file must raise ModelIntegrityError before deserialization."""
    model_id = uuid.uuid4()
    rel_uri, sha256_hash = artifact_store.save(model_id=model_id, model=trained_model)

    # Corrupt 1 byte in the saved artifact file
    final_file = artifact_store.base_dir / rel_uri
    content = bytearray(final_file.read_bytes())
    content[10] = (content[10] + 1) % 256
    final_file.write_bytes(content)

    with pytest.raises(ModelIntegrityError, match="integrity verification failed"):
        artifact_store.load(artifact_uri=rel_uri, expected_hash=sha256_hash)


def test_artifact_load_rejects_mismatched_hash(
    artifact_store: ModelArtifactStore,
    trained_model: IsolationForestModel,
) -> None:
    """Verify that passing an altered expected hash raises ModelIntegrityError."""
    model_id = uuid.uuid4()
    rel_uri, sha256_hash = artifact_store.save(model_id=model_id, model=trained_model)

    altered_hash = "0" * 64
    with pytest.raises(
        ModelIntegrityError, match="Computed hash '.*' does not match expected hash"
    ):
        artifact_store.load(artifact_uri=rel_uri, expected_hash=altered_hash)


def test_artifact_load_missing_file_raises_not_found(
    artifact_store: ModelArtifactStore,
) -> None:
    """Verify that attempting to load a non-existent artifact raises ModelNotFoundError."""
    missing_uri = f"{uuid.uuid4()}/model.joblib"
    with pytest.raises(ModelNotFoundError, match="Model artifact file was not found"):
        artifact_store.load(artifact_uri=missing_uri, expected_hash="a" * 64)


def test_artifact_path_traversal_rejected(
    artifact_store: ModelArtifactStore,
) -> None:
    """Verify that path traversal attempts escaping base_dir are rejected before disk I/O."""
    with pytest.raises(ValueError, match="Path traversal attempt rejected"):
        artifact_store.load(
            artifact_uri="../../sensitive_file.joblib", expected_hash="a" * 64
        )


def test_artifact_load_rejects_incompatible_feature_version(
    artifact_store: ModelArtifactStore,
) -> None:
    """Verify that an artifact with an incompatible feature version raises SchemaValidationError."""
    model_id = uuid.uuid4()
    # Create model with synthetic wrong version
    wrong_model = IsolationForestModel(feature_version="v0.9-incompatible")
    wrong_model.fit(np.ones((10, 34), dtype=np.float64))

    rel_uri, sha256_hash = artifact_store.save(model_id=model_id, model=wrong_model)

    with pytest.raises(SchemaValidationError, match="Feature version mismatch"):
        artifact_store.load(artifact_uri=rel_uri, expected_hash=sha256_hash)
