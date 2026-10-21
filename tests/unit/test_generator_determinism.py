"""Unit tests for deterministic generation, random stream isolation, and prefix stability (ADR-029, ADR-065)."""

from finsignal.dataset.generator.config import GeneratorConfig
from finsignal.dataset.generator.reference_generator import ReferenceEntityGenerator
from finsignal.dataset.generator.schemas import GeneratedReferenceDataset


def test_generation_exact_byte_identical_reproducibility() -> None:
    """Verify that identical (seed, version, config) produces byte-for-byte identical output."""
    cfg = GeneratorConfig(
        seed=20261004,
        generator_version="1.0.0",
        source_namespace="SYNTHETIC",
        account_count=50,
        merchant_count=20,
        device_count=80,
        location_count=10,
    )

    gen1 = ReferenceEntityGenerator(cfg)
    gen2 = ReferenceEntityGenerator(cfg)

    dataset1 = gen1.generate()
    dataset2 = gen2.generate()

    assert dataset1.to_json() == dataset2.to_json()


def test_generation_canonical_json_and_roundtrip() -> None:
    """Verify JSON serialization round-trip fidelity through from_json and from_dict."""
    cfg = GeneratorConfig(
        seed=42,
        generator_version="1.0.0",
        source_namespace="SYNTHETIC",
        account_count=10,
        merchant_count=5,
        device_count=15,
        location_count=4,
    )
    dataset = ReferenceEntityGenerator(cfg).generate()

    json_str = dataset.to_json()
    reconstructed_from_json = GeneratedReferenceDataset.from_json(json_str)

    assert reconstructed_from_json == dataset
    assert reconstructed_from_json.to_json() == json_str

    dict_payload = dataset.to_dict()
    reconstructed_from_dict = GeneratedReferenceDataset.from_dict(dict_payload)

    assert reconstructed_from_dict == dataset
    assert reconstructed_from_dict.config == cfg


def test_seed_sensitivity() -> None:
    """Verify that distinct seeds produce divergent entity attributes and assignments."""
    cfg1 = GeneratorConfig(
        seed=1001,
        account_count=30,
        merchant_count=10,
        device_count=40,
        location_count=5,
    )
    cfg2 = GeneratorConfig(
        seed=2002,
        account_count=30,
        merchant_count=10,
        device_count=40,
        location_count=5,
    )

    dataset1 = ReferenceEntityGenerator(cfg1).generate()
    dataset2 = ReferenceEntityGenerator(cfg2).generate()

    assert dataset1.to_dict() != dataset2.to_dict()


def test_random_stream_isolation_across_entity_types() -> None:
    """Verify that changing merchant_count does NOT alter generated locations, devices, or accounts."""
    cfg_base = GeneratorConfig(
        seed=5555,
        account_count=25,
        merchant_count=10,
        device_count=50,
        location_count=5,
    )
    # Scaled merchant count only
    cfg_more_merchants = GeneratorConfig(
        seed=5555,
        account_count=25,
        merchant_count=80,
        device_count=50,
        location_count=5,
    )

    ds_base = ReferenceEntityGenerator(cfg_base).generate()
    ds_more_m = ReferenceEntityGenerator(cfg_more_merchants).generate()

    # Locations must be 100% identical
    assert ds_base.locations == ds_more_m.locations
    # Devices must be 100% identical
    assert ds_base.devices == ds_more_m.devices
    # Accounts must be 100% identical
    assert ds_base.accounts == ds_more_m.accounts
    # Account devices must be 100% identical
    assert ds_base.account_devices == ds_more_m.account_devices


def test_progressive_prefix_stability_on_account_scaling() -> None:
    """Verify that scaling account_count preserves the first N accounts as an exact prefix."""
    cfg_small = GeneratorConfig(
        seed=7777,
        account_count=30,
        merchant_count=15,
        device_count=100,
        location_count=10,
    )
    cfg_large = GeneratorConfig(
        seed=7777,
        account_count=100,
        merchant_count=15,
        device_count=100,
        location_count=10,
    )

    ds_small = ReferenceEntityGenerator(cfg_small).generate()
    ds_large = ReferenceEntityGenerator(cfg_large).generate()

    # The 30 accounts in ds_small must exactly match the first 30 accounts in ds_large
    assert len(ds_small.accounts) == 30
    assert len(ds_large.accounts) == 100
    assert ds_small.accounts == ds_large.accounts[:30]

    # The account_devices for the first 30 accounts must also match
    small_account_ids = {a.account_id for a in ds_small.accounts}
    large_prefix_account_devices = [
        ad for ad in ds_large.account_devices if ad.account_id in small_account_ids
    ]
    assert ds_small.account_devices == large_prefix_account_devices


def test_progressive_prefix_stability_on_reference_entities() -> None:
    """Verify that scaling reference entity counts preserves the first N records as an exact prefix."""
    seed = 8888
    # 1. Locations scaling
    cfg_loc_small = GeneratorConfig(seed=seed, location_count=5, account_count=10)
    cfg_loc_large = GeneratorConfig(seed=seed, location_count=15, account_count=10)
    ds_loc_s = ReferenceEntityGenerator(cfg_loc_small).generate()
    ds_loc_l = ReferenceEntityGenerator(cfg_loc_large).generate()
    assert ds_loc_s.locations == ds_loc_l.locations[:5]

    # 2. Devices scaling
    cfg_dev_small = GeneratorConfig(seed=seed, device_count=10, account_count=10)
    cfg_dev_large = GeneratorConfig(seed=seed, device_count=30, account_count=10)
    ds_dev_s = ReferenceEntityGenerator(cfg_dev_small).generate()
    ds_dev_l = ReferenceEntityGenerator(cfg_dev_large).generate()
    assert ds_dev_s.devices == ds_dev_l.devices[:10]

    # 3. Merchants scaling (when location pool is constant)
    cfg_merch_small = GeneratorConfig(
        seed=seed, merchant_count=8, location_count=10, account_count=10
    )
    cfg_merch_large = GeneratorConfig(
        seed=seed, merchant_count=20, location_count=10, account_count=10
    )
    ds_merch_s = ReferenceEntityGenerator(cfg_merch_small).generate()
    ds_merch_l = ReferenceEntityGenerator(cfg_merch_large).generate()
    assert ds_merch_s.merchants == ds_merch_l.merchants[:8]
