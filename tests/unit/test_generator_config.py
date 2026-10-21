"""Unit tests for GeneratorConfig validation and constraints (ADR-029, ADR-065)."""

import pytest
from pydantic import ValidationError

from finsignal.dataset.generator.config import GeneratorConfig
from finsignal.dataset.generator.identifiers import (
    MAX_ACCOUNT_CAPACITY,
    MAX_DEVICE_CAPACITY,
    MAX_LOCATION_CAPACITY,
    MAX_MERCHANT_CAPACITY,
)


def test_default_generator_config() -> None:
    """Verify default generator configuration attributes and types."""
    cfg = GeneratorConfig()
    assert cfg.seed == 20261004
    assert cfg.generator_version == "1.0.0"
    assert cfg.source_namespace == "SYNTHETIC"
    assert cfg.account_count == 100
    assert cfg.merchant_count == 50
    assert cfg.device_count == 200
    assert cfg.location_count == 20


def test_custom_valid_config() -> None:
    """Verify valid custom generator configuration."""
    cfg = GeneratorConfig(
        seed=42,
        generator_version="2.0.0",
        source_namespace="EXPERIMENT_ALPHA",
        account_count=500,
        merchant_count=100,
        device_count=1000,
        location_count=50,
    )
    assert cfg.seed == 42
    assert cfg.generator_version == "2.0.0"
    assert cfg.source_namespace == "EXPERIMENT_ALPHA"
    assert cfg.account_count == 500


def test_config_is_immutable() -> None:
    """Verify GeneratorConfig is frozen/immutable."""
    cfg = GeneratorConfig()
    with pytest.raises(ValidationError):
        cfg.account_count = 50  # type: ignore[misc]


def test_invalid_source_namespace_rejected() -> None:
    """Verify lowercase or special character namespaces are rejected."""
    for invalid_ns in ["synthetic", "SYNTH-1", "A", "AB", "SYNTHETIC!"]:
        with pytest.raises(ValidationError, match="source_namespace"):
            GeneratorConfig(source_namespace=invalid_ns)


def test_negative_or_zero_counts_rejected() -> None:
    """Verify zero or negative entity counts are rejected."""
    with pytest.raises(ValidationError, match="account_count"):
        GeneratorConfig.model_validate({"account_count": 0})

    with pytest.raises(ValidationError, match="merchant_count"):
        GeneratorConfig.model_validate({"merchant_count": -1})

    with pytest.raises(ValidationError, match="device_count"):
        GeneratorConfig.model_validate({"device_count": 0})

    with pytest.raises(ValidationError, match="location_count"):
        GeneratorConfig.model_validate({"location_count": -5})


def test_capacity_overflow_rejected() -> None:
    """Verify counts exceeding format capacity limits are rejected."""
    with pytest.raises(ValidationError, match="account_count"):
        GeneratorConfig.model_validate({"account_count": MAX_ACCOUNT_CAPACITY + 1})

    with pytest.raises(ValidationError, match="merchant_count"):
        GeneratorConfig.model_validate({"merchant_count": MAX_MERCHANT_CAPACITY + 1})

    with pytest.raises(ValidationError, match="device_count"):
        GeneratorConfig.model_validate({"device_count": MAX_DEVICE_CAPACITY + 1})

    with pytest.raises(ValidationError, match="location_count"):
        GeneratorConfig.model_validate({"location_count": MAX_LOCATION_CAPACITY + 1})


def test_maximum_valid_capacity_accepted() -> None:
    """Verify that the exact maximum capacity boundaries are accepted."""
    cfg = GeneratorConfig(
        account_count=MAX_ACCOUNT_CAPACITY,
        merchant_count=MAX_MERCHANT_CAPACITY,
        device_count=MAX_DEVICE_CAPACITY,
        location_count=MAX_LOCATION_CAPACITY,
    )
    assert cfg.account_count == MAX_ACCOUNT_CAPACITY
    assert cfg.merchant_count == MAX_MERCHANT_CAPACITY
    assert cfg.device_count == MAX_DEVICE_CAPACITY
    assert cfg.location_count == MAX_LOCATION_CAPACITY


def test_generator_presets() -> None:
    """Verify small, medium, and full preset configurations (ADR-029)."""
    small = GeneratorConfig.small()
    assert small.account_count == 100
    assert small.merchant_count == 50
    assert small.device_count == 200
    assert small.location_count == 20
    assert small.transaction_count == 5_000

    medium = GeneratorConfig.medium()
    assert medium.account_count == 1_000
    assert medium.merchant_count == 250
    assert medium.device_count == 2_000
    assert medium.location_count == 50
    assert medium.transaction_count == 50_000

    full = GeneratorConfig.full()
    assert full.account_count == 5_000
    assert full.merchant_count == 500
    assert full.device_count == 8_000
    assert full.location_count == 100
    assert full.transaction_count == 250_000
