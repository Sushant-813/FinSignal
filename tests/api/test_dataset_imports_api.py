"""API contract and authorization tests for GET /api/v1/datasets/imports (Phase F0.2)."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from finsignal.api.v1.datasets import get_import_service
from finsignal.auth.dependencies import get_current_user
from finsignal.dataset.repository import DatasetImportRepository
from finsignal.dataset.schemas import DatasetImportListResponse, DatasetImportResponse
from finsignal.dataset.service import DatasetImportService
from finsignal.users.models import User


def _make_mock_user(role: str) -> User:
    user = User()
    user.id = uuid.uuid4()
    user.role = role
    user.email = f"{role.lower()}@example.com"
    user.is_active = True
    return user


def _make_sample_import_list() -> DatasetImportListResponse:
    now = datetime(2026, 10, 20, 10, 0, 0, tzinfo=UTC)
    return DatasetImportListResponse(
        items=[
            DatasetImportResponse(
                id=uuid.uuid4(),
                source_namespace="SYNTHETIC",
                status="COMPLETED",
                source_type="SYNTHETIC",
                filename="transactions.csv",
                file_hash="a" * 64,
                total_rows=100,
                valid_rows=98,
                invalid_rows=2,
                started_at=now,
                completed_at=now,
                is_duplicate=False,
            )
        ],
        page=1,
        page_size=20,
        total=1,
        total_pages=1,
    )


@pytest.mark.asyncio
async def test_list_dataset_imports_unauthenticated_returns_401(
    async_client: AsyncClient,
) -> None:
    """Verify GET /api/v1/datasets/imports rejects anonymous requests with 401."""
    resp = await async_client.get("/api/v1/datasets/imports")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["ADMIN", "ANALYST", "INVESTIGATOR"])
async def test_list_dataset_imports_permitted_roles(
    app: FastAPI,
    async_client: AsyncClient,
    role: str,
) -> None:
    """Verify ADMIN, ANALYST, and INVESTIGATOR can list dataset imports."""
    user = _make_mock_user(role)
    mock_service = AsyncMock(spec=DatasetImportService)
    mock_service.list_imports.return_value = _make_sample_import_list()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_import_service] = lambda: mock_service

    try:
        resp = await async_client.get("/api/v1/datasets/imports")
        assert resp.status_code == 200
        body = resp.json()
        assert body["page"] == 1
        assert body["page_size"] == 20
        assert len(body["items"]) == 1
        assert "errors" not in body["items"][0]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_dataset_imports_unauthorized_role_forbidden(
    app: FastAPI,
    async_client: AsyncClient,
) -> None:
    """Verify non-permitted role receives 403 FORBIDDEN."""
    user = _make_mock_user("AUDITOR")
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        resp = await async_client.get("/api/v1/datasets/imports")
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_dataset_imports_validation_and_error_codes(
    app: FastAPI,
    async_client: AsyncClient,
) -> None:
    """Verify structural 422s and service validation/not-found codes over HTTP."""
    user = _make_mock_user("ANALYST")
    mock_repo = AsyncMock(spec=DatasetImportRepository)
    mock_repo.verify_namespace_exists.return_value = True
    mock_repo.list_imports.return_value = ([], 0, 0)
    real_service = DatasetImportService(import_repo=mock_repo)

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_import_service] = lambda: real_service

    try:
        for bad_url in (
            "/api/v1/datasets/imports?page=0",
            "/api/v1/datasets/imports?page_size=101",
            "/api/v1/datasets/imports?status=INVALID",
        ):
            resp = await async_client.get(bad_url)
            assert resp.status_code == 422
            assert resp.json()["error"]["code"] == "VALIDATION_ERROR"

        cases = [
            (
                "/api/v1/datasets/imports?source_namespace=bad-ns",
                422,
                "INVALID_NAMESPACE_FORMAT",
            ),
            (
                "/api/v1/datasets/imports?from_time=2026-10-01T00:00:00",
                422,
                "INVALID_TIMEZONE",
            ),
            (
                "/api/v1/datasets/imports?from_time=2026-10-02T00:00:00Z&to_time=2026-10-01T00:00:00Z",
                422,
                "INVALID_DATE_RANGE",
            ),
        ]
        for url, status_code, code in cases:
            resp = await async_client.get(url)
            assert resp.status_code == status_code
            assert resp.json()["error"]["code"] == code

        mock_repo.verify_namespace_exists.return_value = False
        resp_nf = await async_client.get(
            "/api/v1/datasets/imports?source_namespace=MISSING_NS"
        )
        assert resp_nf.status_code == 404
        assert resp_nf.json()["error"]["code"] == "NAMESPACE_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()
