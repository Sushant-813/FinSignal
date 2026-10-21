"""Unit tests for ReferenceEntityGenerator rules and referential integrity."""

from finsignal.dataset.generator.config import GeneratorConfig
from finsignal.dataset.generator.identifiers import (
    is_valid_account_id,
    is_valid_device_id,
    is_valid_location_id,
    is_valid_merchant_id,
)
from finsignal.dataset.generator.reference_generator import ReferenceEntityGenerator


def test_reference_entity_generation_counts() -> None:
    """Verify generated entity collections match configured counts."""
    cfg = GeneratorConfig(
        seed=12345,
        account_count=40,
        merchant_count=25,
        device_count=60,
        location_count=15,
        source_namespace="TEST_NS",
    )
    generator = ReferenceEntityGenerator(cfg)
    dataset = generator.generate()

    assert len(dataset.locations) == 15
    assert len(dataset.merchants) == 25
    assert len(dataset.devices) == 60
    assert len(dataset.accounts) == 40
    assert len(dataset.account_devices) >= 40


def test_reference_entity_identifier_syntax() -> None:
    """Verify all business identifiers conform to the documented format."""
    cfg = GeneratorConfig(
        account_count=20, merchant_count=10, device_count=30, location_count=5
    )
    dataset = ReferenceEntityGenerator(cfg).generate()

    for loc in dataset.locations:
        assert is_valid_location_id(loc.location_id)
        assert loc.city
        assert loc.country == "IND"

    for m in dataset.merchants:
        assert is_valid_merchant_id(m.merchant_id)
        assert m.merchant_name
        assert m.merchant_category

    for d in dataset.devices:
        assert is_valid_device_id(d.device_id)
        assert d.device_type in ("MOBILE", "DESKTOP", "TABLET", "POS")
        assert d.operating_system

    for a in dataset.accounts:
        assert is_valid_account_id(a.account_id)
        assert a.source_namespace == "SYNTHETIC"
        assert a.account_type in ("PERSONAL", "BUSINESS", "PREMIUM")
        assert a.status in ("ACTIVE", "SUSPENDED")


def test_reference_entity_referential_integrity() -> None:
    """Verify foreign references resolve strictly within the generated reference pools."""
    cfg = GeneratorConfig(
        account_count=50, merchant_count=30, device_count=70, location_count=10
    )
    dataset = ReferenceEntityGenerator(cfg).generate()

    loc_ids = dataset.location_ids
    dev_ids = dataset.device_ids
    acc_ids = dataset.account_ids

    # Every merchant location exists
    for m in dataset.merchants:
        assert m.location_id in loc_ids

    # Every account home location exists
    for a in dataset.accounts:
        assert a.home_location_id in loc_ids

    # Every account_device reference exists
    primary_count_per_account: dict[str, int] = {acc_id: 0 for acc_id in acc_ids}
    for ad in dataset.account_devices:
        assert ad.account_id in acc_ids
        assert ad.device_id in dev_ids
        if ad.is_primary:
            primary_count_per_account[ad.account_id] += 1

    # Exactly one primary device per account
    for acc_id, count in primary_count_per_account.items():
        assert count == 1, (
            f"Account {acc_id} must have exactly 1 primary device, found {count}"
        )


def test_namespace_propagation_to_accounts() -> None:
    """Verify explicit source_namespace is set on every generated account."""
    custom_ns = "CUSTOM_PARTITION_2026"
    cfg = GeneratorConfig(source_namespace=custom_ns, account_count=15)
    dataset = ReferenceEntityGenerator(cfg).generate()

    assert dataset.config.source_namespace == custom_ns
    for a in dataset.accounts:
        assert a.source_namespace == custom_ns
