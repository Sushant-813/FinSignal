"""PostgreSQL integration tests for Phase F0.2 read endpoints."""

import math
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import quote

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.accounts.models import Account
from finsignal.auth.security import create_access_token, hash_password
from finsignal.core.config import Settings
from finsignal.core.database import create_db_resources
from finsignal.dataset.models import DatasetImport, DatasetImportError
from finsignal.devices.models import Device
from finsignal.locations.models import Location
from finsignal.main import create_app
from finsignal.merchants.models import Merchant
from finsignal.ml.models import ModelVersion
from finsignal.risk.models import RiskAnalysis
from finsignal.transactions.models import Transaction
from finsignal.users.repository import UserRepository


@pytest.fixture
async def async_session(
    disposable_db: dict[str, Any],
) -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated AsyncSession bound to the disposable test database."""
    settings: Settings = disposable_db["settings"]
    engine, session_maker = create_db_resources(settings)
    async with session_maker() as session:
        yield session
        try:
            await session.rollback()
            await session.execute(
                text(
                    "TRUNCATE TABLE risk_factors, risk_analyses, model_versions, "
                    "transaction_import_records, dataset_import_errors, dataset_imports, "
                    "transactions, account_devices, accounts, merchants, devices, locations, users CASCADE;"
                )
            )
            await session.commit()
        except Exception:
            await session.rollback()
    await engine.dispose()


@pytest.fixture
async def client(
    disposable_db: dict[str, Any],
) -> AsyncGenerator[AsyncClient, None]:
    """Provide an AsyncClient wired to the FastAPI app and disposable DB."""
    settings: Settings = disposable_db["settings"]
    app = create_app(settings)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac,
    ):
        yield ac


async def _auth_headers(
    session: AsyncSession, settings: Settings, role: str = "ANALYST"
) -> dict[str, str]:
    repo = UserRepository()
    user = await repo.create(
        session=session,
        email=f"{role.lower()}_{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("Password1234!"),
        role=role,
        is_active=True,
    )
    await session.commit()
    token = create_access_token(user_id=user.id, settings=settings)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_transactions_namespace_isolation_and_entity_fencing(
    client: AsyncClient,
    async_session: AsyncSession,
    disposable_db: dict[str, Any],
) -> None:
    """Prove every list query, entity filter, count, and risk subquery enforces source_namespace."""
    headers = await _auth_headers(async_session, disposable_db["settings"])

    acc_syn = Account(
        id=uuid.uuid4(),
        source_namespace="SYNTHETIC",
        external_account_id="ACC_SHARED",
        account_type="CHECKING",
        status="ACTIVE",
    )
    acc_partner = Account(
        id=uuid.uuid4(),
        source_namespace="PARTNER_A",
        external_account_id="ACC_SHARED",
        account_type="SAVINGS",
        status="ACTIVE",
    )
    merch_partner_only = Merchant(
        id=uuid.uuid4(),
        external_merchant_id="M_PARTNER",
        merchant_name="Partner Only Store",
        merchant_category="RETAIL",
    )
    dev_partner_only = Device(
        id=uuid.uuid4(),
        external_device_id="DEV_PARTNER",
        device_type="MOBILE",
    )
    loc_partner_only = Location(
        id=uuid.uuid4(),
        city="Pune",
        state="MH",
        country="India",
    )
    model = ModelVersion(
        id=uuid.uuid4(),
        name="transaction_anomaly_isolation_forest",
        version="1.0.0",
        algorithm="isolation_forest",
        status="ACTIVE",
    )
    async_session.add_all(
        [
            acc_syn,
            acc_partner,
            merch_partner_only,
            dev_partner_only,
            loc_partner_only,
            model,
        ]
    )
    await async_session.flush()

    t_base = datetime(2026, 9, 15, 10, 0, 0, tzinfo=UTC)
    tx_syn = Transaction(
        id=uuid.uuid4(),
        source_namespace="SYNTHETIC",
        external_transaction_id="TXN_IDENTICAL",
        account_id=acc_syn.id,
        occurred_at=t_base,
        amount=Decimal("100.00"),
        currency="INR",
        transaction_type="PURCHASE",
        direction="DEBIT",
        category="GROCERY",
    )
    tx_partner = Transaction(
        id=uuid.uuid4(),
        source_namespace="PARTNER_A",
        external_transaction_id="TXN_IDENTICAL",
        account_id=acc_partner.id,
        merchant_id=merch_partner_only.id,
        device_id=dev_partner_only.id,
        location_id=loc_partner_only.id,
        occurred_at=t_base,
        amount=Decimal("900.00"),
        currency="INR",
        transaction_type="PURCHASE",
        direction="DEBIT",
        category="GROCERY",
    )
    async_session.add_all([tx_syn, tx_partner])
    await async_session.flush()

    # Partner transaction has HIGH risk; synthetic has LOW risk
    ra_syn = RiskAnalysis(
        id=uuid.uuid4(),
        transaction_id=tx_syn.id,
        model_version_id=model.id,
        config_version="rc_v1.0",
        feature_vector_hash="a" * 64,
        score=Decimal("10.000"),
        risk_level="LOW",
        ml_anomaly_score=0.1,
        ml_threshold=0.5,
        normalized_ml_score=10.0,
        rule_score=10.0,
        normalization_params={"method": "piecewise"},
    )
    ra_partner = RiskAnalysis(
        id=uuid.uuid4(),
        transaction_id=tx_partner.id,
        model_version_id=model.id,
        config_version="rc_v1.0",
        feature_vector_hash="b" * 64,
        score=Decimal("80.000"),
        risk_level="HIGH",
        ml_anomaly_score=0.8,
        ml_threshold=0.5,
        normalized_ml_score=80.0,
        rule_score=80.0,
        normalization_params={"method": "piecewise"},
    )
    async_session.add_all([ra_syn, ra_partner])
    await async_session.commit()

    # 1. Default SYNTHETIC returns only SYNTHETIC transaction
    r1 = await client.get("/api/v1/transactions", headers=headers)
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["total"] == 1
    assert d1["total_pages"] == 1
    assert [i["id"] for i in d1["items"]] == [str(tx_syn.id)]

    # 2. Cross-namespace entity IDs under SYNTHETIC return empty 200
    for param, val in (
        ("account_id", acc_partner.id),
        ("merchant_id", merch_partner_only.id),
        ("device_id", dev_partner_only.id),
        ("location_id", loc_partner_only.id),
    ):
        r_cross = await client.get(
            f"/api/v1/transactions?source_namespace=SYNTHETIC&{param}={val}",
            headers=headers,
        )
        assert r_cross.status_code == 200
        assert r_cross.json() == {
            "items": [],
            "page": 1,
            "page_size": 50,
            "total": 0,
            "total_pages": 0,
        }

    # 3. Latest-risk subquery cannot leak PARTNER_A HIGH transaction into SYNTHETIC
    r_risk = await client.get(
        "/api/v1/transactions?source_namespace=SYNTHETIC&risk_level=HIGH",
        headers=headers,
    )
    assert r_risk.status_code == 200
    assert r_risk.json()["total"] == 0
    assert r_risk.json()["items"] == []

    # 4. Nonexistent namespace returns 404 NAMESPACE_NOT_FOUND
    r_missing_ns = await client.get(
        "/api/v1/transactions?source_namespace=NONEXISTENT_NS",
        headers=headers,
    )
    assert r_missing_ns.status_code == 404
    assert r_missing_ns.json()["error"]["code"] == "NAMESPACE_NOT_FOUND"


@pytest.mark.asyncio
async def test_transactions_filters_boundaries_tie_breaking_and_precision(
    client: AsyncClient,
    async_session: AsyncSession,
    disposable_db: dict[str, Any],
) -> None:
    """Verify multi-field filters, UTC boundaries, sorting tie-breakers, latest-risk ties, and MoneyStr."""
    headers = await _auth_headers(async_session, disposable_db["settings"])

    acc1 = Account(
        id=uuid.uuid4(),
        source_namespace="SYNTHETIC",
        external_account_id="ACC_1",
        account_type="CHECKING",
        status="ACTIVE",
    )
    acc2 = Account(
        id=uuid.uuid4(),
        source_namespace="SYNTHETIC",
        external_account_id="ACC_2",
        account_type="CHECKING",
        status="ACTIVE",
    )
    merch = Merchant(
        id=uuid.uuid4(),
        external_merchant_id="M_1",
        merchant_name="Fresh Mart",
        merchant_category="GROCERY",
    )
    dev = Device(
        id=uuid.uuid4(),
        external_device_id="D_1",
        device_type="SMARTPHONE",
    )
    loc = Location(
        id=uuid.uuid4(),
        city="Mumbai",
        state="MH",
        country="India",
    )
    model = ModelVersion(
        id=uuid.uuid4(),
        name="transaction_anomaly_isolation_forest",
        version="1.0.0",
        algorithm="isolation_forest",
        status="ACTIVE",
    )
    async_session.add_all([acc1, acc2, merch, dev, loc, model])
    await async_session.flush()

    t_same = datetime(2026, 9, 10, 12, 0, 0, tzinfo=UTC)
    t_later = datetime(2026, 9, 11, 0, 0, 0, tzinfo=UTC)
    t_before = datetime(2026, 9, 9, 23, 59, 59, tzinfo=UTC)

    # Deterministic UUIDs to verify id DESC tie-breaking cleanly
    id_low = uuid.UUID("00000000-0000-4000-8000-000000000001")
    id_mid = uuid.UUID("00000000-0000-4000-8000-000000000002")
    id_high = uuid.UUID("00000000-0000-4000-8000-000000000003")
    id_big = uuid.UUID("00000000-0000-4000-8000-000000000004")

    tx_a = Transaction(
        id=id_low,
        source_namespace="SYNTHETIC",
        external_transaction_id="TX_A",
        account_id=acc1.id,
        merchant_id=merch.id,
        device_id=dev.id,
        location_id=loc.id,
        occurred_at=t_same,
        amount=Decimal("100.10"),
        currency="INR",
        transaction_type="PURCHASE",
        direction="DEBIT",
        category="GROCERY",
    )
    tx_b = Transaction(
        id=id_mid,
        source_namespace="SYNTHETIC",
        external_transaction_id="TX_B",
        account_id=acc1.id,
        counterparty_account_id=acc2.id,
        occurred_at=t_same,
        amount=Decimal("250.00"),
        currency="INR",
        transaction_type="TRANSFER",
        direction="DEBIT",
        category="OTHER",
    )
    tx_c = Transaction(
        id=id_high,
        source_namespace="SYNTHETIC",
        external_transaction_id="TX_C",
        account_id=acc1.id,
        occurred_at=t_before,
        amount=Decimal("50.00"),
        currency="USD",
        transaction_type="PURCHASE",
        direction="CREDIT",
        category="TRAVEL",
    )
    tx_d = Transaction(
        id=id_big,
        source_namespace="SYNTHETIC",
        external_transaction_id="TX_D",
        account_id=acc1.id,
        occurred_at=t_later,
        amount=Decimal("9999999999999.99"),
        currency="INR",
        transaction_type="PURCHASE",
        direction="DEBIT",
        category="GROCERY",
    )
    async_session.add_all([tx_a, tx_b, tx_c, tx_d])
    await async_session.flush()

    # Latest risk tie-breaking on tx_a: two analyses sharing identical created_at!
    ra_tie_ts = datetime(2026, 9, 15, 0, 0, 0, tzinfo=UTC)
    ra_older_id = RiskAnalysis(
        id=uuid.UUID("10000000-0000-4000-8000-000000000001"),
        transaction_id=tx_a.id,
        model_version_id=model.id,
        config_version="rc_v1.0",
        feature_vector_hash="1" * 64,
        score=Decimal("15.000"),
        risk_level="LOW",
        ml_anomaly_score=0.1,
        ml_threshold=0.5,
        normalized_ml_score=15.0,
        rule_score=15.0,
        normalization_params={"method": "piecewise"},
        created_at=ra_tie_ts,
    )
    ra_winner_id = RiskAnalysis(
        id=uuid.UUID("20000000-0000-4000-8000-000000000002"),
        transaction_id=tx_a.id,
        model_version_id=model.id,
        config_version="rc_v2.0",
        feature_vector_hash="2" * 64,
        score=Decimal("88.500"),
        risk_level="CRITICAL",
        ml_anomaly_score=0.9,
        ml_threshold=0.5,
        normalized_ml_score=88.5,
        rule_score=88.5,
        normalization_params={"method": "piecewise"},
        created_at=ra_tie_ts,
    )
    async_session.add_all([ra_older_id, ra_winner_id])
    await async_session.commit()

    # 1. Half-open UTC boundary check using +05:30 offset:
    # 2026-09-10T17:30:00+05:30 == 2026-09-10T12:00:00Z (includes tx_a & tx_b)
    # 2026-09-11T05:30:00+05:30 == 2026-09-11T00:00:00Z (excludes tx_d!)
    from_q = quote("2026-09-10T17:30:00+05:30")
    to_q = quote("2026-09-11T05:30:00+05:30")
    r_win = await client.get(
        f"/api/v1/transactions?from_time={from_q}&to_time={to_q}&page=1&page_size=1",
        headers=headers,
    )
    assert r_win.status_code == 200
    w_body = r_win.json()
    assert w_body["total"] == 2
    assert w_body["total_pages"] == 2
    # Identical occurred_at -> ordered by id DESC (tx_b id_mid > tx_a id_low)
    assert w_body["items"][0]["id"] == str(tx_b.id)

    r_win_p2 = await client.get(
        f"/api/v1/transactions?from_time={from_q}&to_time={to_q}&page=2&page_size=1",
        headers=headers,
    )
    assert r_win_p2.status_code == 200
    assert r_win_p2.json()["items"][0]["id"] == str(tx_a.id)
    assert r_win_p2.json()["items"][0]["amount"] == "100.10"

    # Out-of-range page returns empty items with accurate total/total_pages
    r_oob = await client.get(
        f"/api/v1/transactions?from_time={from_q}&to_time={to_q}&page=3&page_size=1",
        headers=headers,
    )
    assert r_oob.status_code == 200
    assert r_oob.json()["items"] == []
    assert r_oob.json()["total"] == 2
    assert r_oob.json()["total_pages"] == 2

    # 2. Latest risk tie-breaking matches GET /transactions/{id}/risk
    r_crit = await client.get(
        "/api/v1/transactions?risk_level=CRITICAL", headers=headers
    )
    assert r_crit.status_code == 200
    assert r_crit.json()["total"] == 1
    assert r_crit.json()["items"][0]["id"] == str(tx_a.id)

    r_low = await client.get("/api/v1/transactions?risk_level=LOW", headers=headers)
    assert r_low.status_code == 200
    assert r_low.json()["total"] == 0

    r_tx_risk = await client.get(
        f"/api/v1/transactions/{tx_a.id}/risk", headers=headers
    )
    assert r_tx_risk.status_code == 200
    assert r_tx_risk.json()["risk_level"] == "CRITICAL"

    # 3. Combined filters + monetary precision + count/page parity
    r_filtered = await client.get(
        f"/api/v1/transactions?account_id={acc1.id}&currency=INR&direction=DEBIT"
        f"&category=GROCERY&min_amount=100.00&max_amount=9999999999999.99"
        f"&sort_by=amount&sort_order=desc&page_size=1",
        headers=headers,
    )
    assert r_filtered.status_code == 200
    f_body = r_filtered.json()
    assert f_body["total"] == 2
    assert f_body["total_pages"] == math.ceil(2 / 1)
    assert f_body["items"][0]["amount"] == "9999999999999.99"

    # Collect all pages and confirm parity with total
    collected: list[str] = []
    for pg in range(1, f_body["total_pages"] + 1):
        rp = await client.get(
            f"/api/v1/transactions?account_id={acc1.id}&currency=INR&direction=DEBIT"
            f"&category=GROCERY&min_amount=100.00&max_amount=9999999999999.99"
            f"&sort_by=amount&sort_order=desc&page={pg}&page_size=1",
            headers=headers,
        )
        collected.extend(i["id"] for i in rp.json()["items"])
    assert collected == [str(tx_d.id), str(tx_a.id)]


@pytest.mark.asyncio
async def test_transaction_detail_context_and_namespace_fencing(
    client: AsyncClient,
    async_session: AsyncSession,
    disposable_db: dict[str, Any],
) -> None:
    """Verify GET /api/v1/transactions/{id} returns embedded entities, latest risk, and 404 anti-enumeration."""
    headers = await _auth_headers(async_session, disposable_db["settings"])

    acc = Account(
        id=uuid.uuid4(),
        source_namespace="SYNTHETIC",
        external_account_id="ACC_D1",
        account_type="SAVINGS",
        status="ACTIVE",
    )
    cp_acc = Account(
        id=uuid.uuid4(),
        source_namespace="SYNTHETIC",
        external_account_id="ACC_D2",
        account_type="CHECKING",
        status="ACTIVE",
    )
    merch = Merchant(
        id=uuid.uuid4(),
        external_merchant_id="M_D1",
        merchant_name="Acme Electronics",
        merchant_category="ELECTRONICS",
    )
    dev = Device(
        id=uuid.uuid4(),
        external_device_id="DEV_D1",
        device_type="DESKTOP",
    )
    loc = Location(
        id=uuid.uuid4(),
        city="Bengaluru",
        state="KA",
        country="India",
    )
    model = ModelVersion(
        id=uuid.uuid4(),
        name="transaction_anomaly_isolation_forest",
        version="1.2.3",
        algorithm="isolation_forest",
        status="ACTIVE",
    )
    async_session.add_all([acc, cp_acc, merch, dev, loc, model])
    await async_session.flush()

    tx = Transaction(
        id=uuid.uuid4(),
        source_namespace="SYNTHETIC",
        external_transaction_id="TXN_DETAIL_1",
        account_id=acc.id,
        counterparty_account_id=cp_acc.id,
        merchant_id=merch.id,
        device_id=dev.id,
        location_id=loc.id,
        occurred_at=datetime(2026, 9, 15, 14, 30, 0, tzinfo=UTC),
        amount=Decimal("75000.00"),
        currency="INR",
        transaction_type="TRANSFER",
        direction="DEBIT",
        category="OTHER",
        payment_method="IMPS",
        channel="MOBILE_APP",
    )
    async_session.add(tx)
    await async_session.flush()

    ra = RiskAnalysis(
        id=uuid.uuid4(),
        transaction_id=tx.id,
        model_version_id=model.id,
        config_version="rc_v1.0",
        feature_vector_hash="f" * 64,
        score=Decimal("82.500"),
        risk_level="CRITICAL",
        ml_anomaly_score=0.85,
        ml_threshold=0.5,
        normalized_ml_score=82.5,
        rule_score=80.0,
        normalization_params={"method": "piecewise"},
    )
    async_session.add(ra)
    await async_session.commit()

    # Valid retrieval with matching namespace
    r_ok = await client.get(
        f"/api/v1/transactions/{tx.id}?source_namespace=SYNTHETIC",
        headers=headers,
    )
    assert r_ok.status_code == 200
    body = r_ok.json()
    assert body["amount"] == "75000.00"
    assert body["account"]["external_account_id"] == "ACC_D1"
    assert body["counterparty_account"]["external_account_id"] == "ACC_D2"
    assert body["merchant"]["merchant_name"] == "Acme Electronics"
    assert body["device"]["external_device_id"] == "DEV_D1"
    assert body["location"]["city"] == "Bengaluru"
    assert body["location"]["country"] == "India"
    assert body["latest_risk"]["analysis_id"] == str(ra.id)
    assert body["latest_risk"]["score"] == 82.5
    assert body["latest_risk"]["risk_level"] == "CRITICAL"
    assert body["latest_risk"]["model_version"] == "1.2.3"

    # Cross-namespace fencing -> 404 TRANSACTION_NOT_FOUND
    r_fence = await client.get(
        f"/api/v1/transactions/{tx.id}?source_namespace=OTHER_NS",
        headers=headers,
    )
    assert r_fence.status_code == 404
    assert r_fence.json()["error"]["code"] == "TRANSACTION_NOT_FOUND"

    # Missing ID -> 404 TRANSACTION_NOT_FOUND
    r_missing = await client.get(
        f"/api/v1/transactions/{uuid.uuid4()}",
        headers=headers,
    )
    assert r_missing.status_code == 404
    assert r_missing.json()["error"]["code"] == "TRANSACTION_NOT_FOUND"


@pytest.mark.asyncio
async def test_dataset_imports_listing_filters_ordering_and_no_errors(
    client: AsyncClient,
    async_session: AsyncSession,
    disposable_db: dict[str, Any],
) -> None:
    """Verify GET /api/v1/datasets/imports pagination, namespace isolation, ordering, and exclusion of errors."""
    headers = await _auth_headers(async_session, disposable_db["settings"])

    t1 = datetime(2026, 10, 20, 10, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 10, 21, 10, 0, 0, tzinfo=UTC)

    imp1 = DatasetImport(
        id=uuid.uuid4(),
        source_namespace="SYNTHETIC",
        status="COMPLETED",
        source_type="SYNTHETIC",
        filename="first.csv",
        file_hash="1" * 64,
        total_rows=100,
        valid_rows=95,
        invalid_rows=5,
        started_at=t1,
        completed_at=t1 + timedelta(minutes=1),
    )
    imp2 = DatasetImport(
        id=uuid.uuid4(),
        source_namespace="SYNTHETIC",
        status="FAILED",
        source_type="CSV",
        filename="second.csv",
        file_hash="2" * 64,
        total_rows=50,
        valid_rows=0,
        invalid_rows=50,
        started_at=t2,
        completed_at=t2 + timedelta(seconds=10),
    )
    imp_other_ns = DatasetImport(
        id=uuid.uuid4(),
        source_namespace="PARTNER_B",
        status="COMPLETED",
        source_type="CSV",
        filename="partner.csv",
        file_hash="3" * 64,
        total_rows=10,
        valid_rows=10,
        invalid_rows=0,
        started_at=t2,
    )
    async_session.add_all([imp1, imp2, imp_other_ns])
    await async_session.flush()

    # Attach validation errors that MUST NOT appear in list responses
    async_session.add(
        DatasetImportError(
            id=uuid.uuid4(),
            dataset_import_id=imp1.id,
            row_number=1,
            field_name="amount",
            error_code="INVALID_AMOUNT",
            message="Bad amount",
        )
    )
    await async_session.commit()

    # Default list in SYNTHETIC ordered started_at DESC, id DESC
    r_all = await client.get("/api/v1/datasets/imports", headers=headers)
    assert r_all.status_code == 200
    body = r_all.json()
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total"] == 2
    assert body["total_pages"] == 1
    assert [i["id"] for i in body["items"]] == [str(imp2.id), str(imp1.id)]
    for item in body["items"]:
        assert "errors" not in item

    # Status + half-open time window filter
    from_q = quote("2026-10-20T00:00:00Z")
    to_q = quote("2026-10-21T00:00:00Z")
    r_filt = await client.get(
        f"/api/v1/datasets/imports?status=COMPLETED&from_time={from_q}&to_time={to_q}",
        headers=headers,
    )
    assert r_filt.status_code == 200
    f_body = r_filt.json()
    assert f_body["total"] == 1
    assert f_body["items"][0]["id"] == str(imp1.id)
