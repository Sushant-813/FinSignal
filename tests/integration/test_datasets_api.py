"""Integration tests for Dataset Import API endpoints (/api/v1/datasets/imports) (P4.5)."""

import hashlib
import io
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.auth.security import create_access_token
from finsignal.core.config import Settings
from finsignal.core.database import create_db_resources
from finsignal.dataset.generator import (
    CSVDatasetExporter,
    GeneratorConfig,
    ReferenceEntityGenerator,
    ReferenceEntityPersistenceService,
    TransactionDatasetGenerator,
)
from finsignal.dataset.models import DatasetImport
from finsignal.main import create_app
from finsignal.users.models import User
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
        # Clean up database tables for complete test isolation
        try:
            await session.rollback()
            await session.execute(
                text(
                    "TRUNCATE TABLE transaction_import_records, dataset_import_errors, dataset_imports, "
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
    """Provide an AsyncClient bound to the full application."""
    settings: Settings = disposable_db["settings"]
    app = create_app(settings)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


async def _create_test_user(
    session: AsyncSession, email: str, role: str
) -> tuple[User, str, Settings]:
    from finsignal.auth.security import hash_password
    from finsignal.core.config import get_settings

    settings = get_settings()
    repo = UserRepository()
    user = await repo.create(
        session=session,
        email=email,
        password_hash=hash_password("Password1234!"),
        role=role,
        is_active=True,
    )
    await session.commit()
    token = create_access_token(
        user_id=user.id,
        settings=settings,
    )
    return user, token, settings


@pytest.mark.asyncio
async def test_upload_dataset_unauthorized_and_forbidden(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """Verify unauthenticated requests return 401 and unauthorized roles return 403."""
    # 1. Unauthenticated -> 401
    files = {"file": ("tx.csv", io.BytesIO(b"dummy"), "text/csv")}
    resp = await client.post("/api/v1/datasets/imports", files=files)
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"

    # 2. Authenticated as INVESTIGATOR -> 403
    _, inv_token, _ = await _create_test_user(
        async_session, "inv@example.com", "INVESTIGATOR"
    )
    headers = {"Authorization": f"Bearer {inv_token}"}
    resp = await client.post("/api/v1/datasets/imports", files=files, headers=headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_upload_dataset_success_and_deduplication(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """Verify successful upload returns 201 and identical re-upload returns 200 with deduplication."""
    # Create Analyst user
    _, analyst_token, _ = await _create_test_user(
        async_session, "analyst@example.com", "ANALYST"
    )
    auth_headers = {"Authorization": f"Bearer {analyst_token}"}

    namespace = "SYNTHETIC_API_TEST"
    cfg = GeneratorConfig(
        seed=555,
        source_namespace=namespace,
        account_count=5,
        merchant_count=2,
        device_count=5,
        location_count=2,
        transaction_count=10,
    )
    ref_ds = ReferenceEntityGenerator(cfg).generate()
    await ReferenceEntityPersistenceService().persist(async_session, ref_ds)
    await async_session.commit()

    tx_dataset = TransactionDatasetGenerator(cfg, ref_ds).generate()

    out_buf = io.StringIO()
    CSVDatasetExporter.export_transactions(tx_dataset.transactions, out_buf)
    csv_bytes = out_buf.getvalue().encode("utf-8")

    # 1. First Upload -> 201 Created
    files = {"file": ("transactions.csv", io.BytesIO(csv_bytes), "text/csv")}
    data = {"source_namespace": namespace, "source_type": "SYNTHETIC"}

    res1 = await client.post(
        "/api/v1/datasets/imports",
        files=files,
        data=data,
        headers=auth_headers,
    )
    assert res1.status_code == 201
    body1 = res1.json()
    assert body1["source_namespace"] == namespace
    assert body1["status"] == "COMPLETED"
    assert body1["total_rows"] == 10
    assert body1["valid_rows"] == 10
    assert body1["is_duplicate"] is False
    first_import_id = body1["id"]

    # 2. Identical Upload in same namespace -> 200 OK (Deduplicated!)
    files2 = {"file": ("transactions.csv", io.BytesIO(csv_bytes), "text/csv")}
    res2 = await client.post(
        "/api/v1/datasets/imports",
        files=files2,
        data=data,
        headers=auth_headers,
    )
    assert res2.status_code == 200
    body2 = res2.json()
    assert body2["id"] == first_import_id
    assert body2["is_duplicate"] is True

    # 3. Lookup Import Details -> 200 OK
    detail_res = await client.get(
        f"/api/v1/datasets/imports/{first_import_id}",
        headers=auth_headers,
    )
    assert detail_res.status_code == 200
    detail_body = detail_res.json()
    assert detail_body["id"] == first_import_id
    assert "errors" in detail_body


@pytest.mark.asyncio
async def test_get_import_not_found(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """Verify querying non-existent import ID returns 404."""
    _, analyst_token, _ = await _create_test_user(
        async_session, "user2@example.com", "ANALYST"
    )
    headers = {"Authorization": f"Bearer {analyst_token}"}

    fake_id = uuid.uuid4()
    res = await client.get(f"/api/v1/datasets/imports/{fake_id}", headers=headers)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_recover_import_api_endpoint(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """Verify POST /api/v1/datasets/imports/{id}/recover succeeds and returns updated import summary."""
    _, analyst_token, _ = await _create_test_user(
        async_session, "user3@example.com", "ANALYST"
    )
    auth_headers = {"Authorization": f"Bearer {analyst_token}"}

    namespace = "API_RECOVER_NS"
    cfg = GeneratorConfig(
        seed=888,
        source_namespace=namespace,
        account_count=5,
        merchant_count=3,
        device_count=5,
        location_count=3,
        transaction_count=10,
    )
    ref_gen = ReferenceEntityGenerator(cfg)
    refs = ref_gen.generate()
    persist_svc = ReferenceEntityPersistenceService()
    await persist_svc.persist(async_session, refs)
    await async_session.commit()

    tx_gen = TransactionDatasetGenerator(cfg, refs)
    tx_ds = tx_gen.generate()
    out_buf = io.StringIO()
    CSVDatasetExporter.export_transactions(tx_ds.transactions, out_buf)
    csv_bytes = out_buf.getvalue().encode("utf-8")

    # 1. Normal upload -> 201 Created
    files = {"file": ("tx.csv", io.BytesIO(csv_bytes), "text/csv")}
    data = {"source_namespace": namespace}
    res = await client.post(
        "/api/v1/datasets/imports", files=files, data=data, headers=auth_headers
    )
    assert res.status_code == 201
    import_id = res.json()["id"]

    # 2. Invoke recovery endpoint with same file -> 200 OK
    files_rec = {"file": ("tx.csv", io.BytesIO(csv_bytes), "text/csv")}
    rec_res = await client.post(
        f"/api/v1/datasets/imports/{import_id}/recover",
        files=files_rec,
        headers=auth_headers,
    )
    assert rec_res.status_code == 200
    rec_body = rec_res.json()
    assert rec_body["id"] == import_id
    assert rec_body["status"] == "COMPLETED"
    assert rec_body["total_rows"] == 10


@pytest.mark.asyncio
async def test_upload_and_recover_bounded_size_enforcement(
    client: AsyncClient,
    async_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify SEC-02: Enforcing file size limit on both upload and recovery endpoints."""
    import finsignal.api.v1.datasets as datasets_mod

    _, analyst_token, _ = await _create_test_user(
        async_session, "size_tester@example.com", "ANALYST"
    )
    auth_headers = {"Authorization": f"Bearer {analyst_token}"}

    # Restrict MAX_UPLOAD_BYTES to 100 bytes for test
    monkeypatch.setattr(datasets_mod, "MAX_UPLOAD_BYTES", 100)

    # 1. Oversized file to /imports -> 413 Payload Too Large
    oversized_data = b"x" * 150
    files = {"file": ("oversized.csv", io.BytesIO(oversized_data), "text/csv")}
    res = await client.post(
        "/api/v1/datasets/imports",
        files=files,
        data={"source_namespace": "TEST_SIZE_NS"},
        headers=auth_headers,
    )
    assert res.status_code == 413
    assert res.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
    assert "exceeds maximum allowable size" in res.json()["error"]["message"]

    # 2. Oversized file to /recover -> 413 Payload Too Large
    fake_import_id = uuid.uuid4()
    files_rec = {"file": ("oversized.csv", io.BytesIO(oversized_data), "text/csv")}
    rec_res = await client.post(
        f"/api/v1/datasets/imports/{fake_import_id}/recover",
        files=files_rec,
        headers=auth_headers,
    )
    assert rec_res.status_code == 413
    assert rec_res.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
    assert "exceeds maximum allowable size" in rec_res.json()["error"]["message"]

    # 3. Empty file -> 422
    empty_files = {"file": ("empty.csv", io.BytesIO(b""), "text/csv")}
    emp_res = await client.post(
        "/api/v1/datasets/imports",
        files=empty_files,
        data={"source_namespace": "TEST_SIZE_NS"},
        headers=auth_headers,
    )
    assert emp_res.status_code == 422
    assert "empty" in emp_res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_upload_dataset_utf8_bom_support(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """Verify SEC-02: CSV files with UTF-8 BOM are decoded correctly without failing header validation."""
    _, analyst_token, _ = await _create_test_user(
        async_session, "bom_analyst@example.com", "ANALYST"
    )
    auth_headers = {"Authorization": f"Bearer {analyst_token}"}

    namespace = "BOM_TEST_NS"
    cfg = GeneratorConfig(
        seed=101,
        source_namespace=namespace,
        account_count=2,
        merchant_count=1,
        device_count=1,
        location_count=1,
        transaction_count=2,
    )
    ref_ds = ReferenceEntityGenerator(cfg).generate()
    await ReferenceEntityPersistenceService().persist(async_session, ref_ds)
    await async_session.commit()

    tx_dataset = TransactionDatasetGenerator(cfg, ref_ds).generate()
    out_buf = io.StringIO()
    CSVDatasetExporter.export_transactions(tx_dataset.transactions, out_buf)
    raw_csv_bytes = out_buf.getvalue().encode("utf-8")

    # Prepend UTF-8 BOM: \xef\xbb\xbf
    bom_csv_bytes = b"\xef\xbb\xbf" + raw_csv_bytes
    expected_bom_hash = hashlib.sha256(bom_csv_bytes).hexdigest()
    files = {"file": ("bom_transactions.csv", io.BytesIO(bom_csv_bytes), "text/csv")}
    data = {"source_namespace": namespace, "source_type": "SYNTHETIC"}

    res = await client.post(
        "/api/v1/datasets/imports", files=files, data=data, headers=auth_headers
    )
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "COMPLETED"
    assert body["total_rows"] == 2
    assert body["valid_rows"] == 2
    assert body["file_hash"] == expected_bom_hash

    # 2. Verify recovery with the same BOM-prefixed file verifies hash and completes
    files_rec = {
        "file": ("bom_transactions.csv", io.BytesIO(bom_csv_bytes), "text/csv")
    }
    rec_res = await client.post(
        f"/api/v1/datasets/imports/{body['id']}/recover",
        files=files_rec,
        headers=auth_headers,
    )
    assert rec_res.status_code == 200
    rec_body = rec_res.json()
    assert rec_body["status"] == "COMPLETED"
    assert rec_body["file_hash"] == expected_bom_hash


@pytest.mark.asyncio
async def test_upload_dataset_malformed_csv_and_oversized_field(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """Verify SEC-02: Malformed CSV and oversized fields result in a controlled 422 failure and FAILED status."""
    _, analyst_token, _ = await _create_test_user(
        async_session, "malformed_tester@example.com", "ANALYST"
    )
    auth_headers = {"Authorization": f"Bearer {analyst_token}"}
    namespace = "MALFORMED_TEST_NS"

    # 1. Malformed CSV syntax (e.g. unclosed quote with NUL or corrupt formatting)
    malformed_csv = b'account_id,external_transaction_id,amount\n"unclosed_string_value'
    files_bad = {"file": ("bad.csv", io.BytesIO(malformed_csv), "text/csv")}
    res_bad = await client.post(
        "/api/v1/datasets/imports",
        files=files_bad,
        data={"source_namespace": namespace},
        headers=auth_headers,
    )
    assert res_bad.status_code == 422
    assert res_bad.json()["error"]["code"] == "DOMAIN_VALIDATION_ERROR"
    assert (
        "CSV" in res_bad.json()["error"]["message"]
        or "header" in res_bad.json()["error"]["message"].lower()
    )

    # 2. Oversized CSV field exceeding csv.field_size_limit (128 KB)
    # Generate field with 140,000 chars
    oversized_field = "X" * 140000
    huge_field_csv = (
        "transaction_id,source_namespace,account_id,occurred_at,amount,currency,transaction_type,direction,description\n"
        f"TX1,{namespace},ACC1,2026-01-01T00:00:00Z,10.00,USD,PURCHASE,DEBIT,{oversized_field}\n"
    ).encode()

    files_huge = {"file": ("huge_field.csv", io.BytesIO(huge_field_csv), "text/csv")}
    res_huge = await client.post(
        "/api/v1/datasets/imports",
        files=files_huge,
        data={"source_namespace": namespace},
        headers=auth_headers,
    )
    assert res_huge.status_code == 422
    assert res_huge.json()["error"]["code"] == "DOMAIN_VALIDATION_ERROR"
    assert "field larger than field limit" in res_huge.json()["error"]["message"]

    # Verify import status in database is FAILED and queryable via API
    stmt = select(DatasetImport).where(DatasetImport.filename == "huge_field.csv")
    import_row = (await async_session.execute(stmt)).scalar_one_or_none()
    assert import_row is not None
    assert import_row.status == "FAILED"

    # API query returns FAILED status
    get_res = await client.get(
        f"/api/v1/datasets/imports/{import_row.id}",
        headers=auth_headers,
    )
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "FAILED"

    # 3. Recovery endpoint with malformed CSV also returns controlled 422
    rec_bad_res = await client.post(
        f"/api/v1/datasets/imports/{import_row.id}/recover",
        files={"file": ("bad.csv", io.BytesIO(malformed_csv), "text/csv")},
        headers=auth_headers,
    )
    assert rec_bad_res.status_code == 422
    assert rec_bad_res.json()["error"]["code"] == "DOMAIN_VALIDATION_ERROR"
