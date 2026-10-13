"""API tests for centralized exception handlers and security sanitization."""

import logging
from decimal import Decimal
from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from finsignal.common.exceptions import FinSignalError, NotFoundError, ValidationError
from finsignal.common.handlers import (
    finsignal_exception_handler,
    sqlalchemy_exception_handler,
    starlette_http_exception_handler,
    validation_exception_handler,
)
from finsignal.core.middleware import RequestIdMiddleware


class SamplePayload(BaseModel):
    """Sample payload model for request validation testing."""

    model_config = ConfigDict(extra="forbid")

    amount: Decimal = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)


@pytest.fixture
def error_test_app() -> FastAPI:
    """Provide an isolated FastAPI app wired with RequestIdMiddleware and all centralized handlers."""
    application = FastAPI()
    application.add_middleware(RequestIdMiddleware)

    application.add_exception_handler(
        FinSignalError, cast(Any, finsignal_exception_handler)
    )
    application.add_exception_handler(
        RequestValidationError, cast(Any, validation_exception_handler)
    )
    application.add_exception_handler(
        SQLAlchemyError, cast(Any, sqlalchemy_exception_handler)
    )
    application.add_exception_handler(
        StarletteHTTPException, cast(Any, starlette_http_exception_handler)
    )

    @application.post("/validate-input")
    async def validate_input(payload: SamplePayload) -> dict[str, str]:
        return {"status": "ok", "amount": str(payload.amount)}

    @application.get("/raise-domain-error")
    async def raise_domain_error() -> dict[str, str]:
        raise ValidationError(
            message="Transfer account cannot be identical to source account.",
            code="INVALID_COUNTERPARTY",
            details={"counterparty": "Source and destination match."},
        )

    @application.get("/raise-not-found")
    async def raise_not_found() -> dict[str, str]:
        raise NotFoundError(
            message="The requested account does not exist.",
            code="ACCOUNT_NOT_FOUND",
            details={"account_id": "acc-999"},
        )

    @application.get("/raise-internal-diagnostics")
    async def raise_internal_diagnostics() -> dict[str, str]:
        # Raise an application error carrying sensitive sentinel context for internal diagnostics
        raise FinSignalError(
            message="A secure business invariant failed.",
            code="BUSINESS_RULE_VIOLATION",
            status_code=400,
            details={"safe_reference": "REF-100"},
            internal_context={
                "sensitive_token": "SENTINEL_SECRET_TOKEN_XYZ_999",
                "raw_query": "SELECT * FROM users WHERE password='super_secret'",
            },
        )

    @application.get("/raise-database-error")
    async def raise_database_error() -> dict[str, str]:
        # Simulate an internal SQLAlchemy DBAPI error with sensitive query and parameters
        sql = "SELECT * FROM secret_accounts WHERE ssn=:ssn_param"
        params = {"ssn_param": "SENSITIVE_SSN_999-88-7777"}
        orig_exc = Exception(
            "Connection reset by peer with postgres://dbuser:secretpass@127.0.0.1:5432/db"
        )
        db_err = DBAPIError(statement=sql, params=params, orig=orig_exc)
        raise db_err

    @application.get("/raise-starlette-401")
    async def raise_starlette_401() -> JSONResponse:
        raise StarletteHTTPException(
            status_code=401,
            detail="Internal token decode failure with stack trace",
            headers={"WWW-Authenticate": "Bearer"},
        )

    @application.get("/raise-synthetic-validation-error")
    async def raise_synthetic_validation_error() -> None:
        raise RequestValidationError(
            errors=[
                {
                    "type": "string_too_short",
                    "loc": ("body", "<script>alert(1)</script>", "nested field"),
                    "msg": "internal parser message with stack trace",
                    "input": "super_secret_input_value",
                },
                {
                    "type": "string_too_long",
                    "loc": ("body", "valid_field_name", "malicious[injection]"),
                    "msg": "another internal message",
                    "input": "another_secret",
                },
            ]
        )

    return application


@pytest.mark.asyncio
async def test_domain_validation_error_envelope(error_test_app: FastAPI) -> None:
    """Verify application ValidationError produces HTTP 422 with domain details and request ID."""
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=error_test_app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/raise-domain-error", headers={"X-Request-ID": "dom-val-1"}
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error"]["code"] == "INVALID_COUNTERPARTY"
        assert (
            body["error"]["message"]
            == "Transfer account cannot be identical to source account."
        )
        assert body["error"]["details"] == {
            "counterparty": "Source and destination match."
        }
        assert body["error"]["request_id"] == "dom-val-1"


@pytest.mark.asyncio
async def test_not_found_error_envelope(error_test_app: FastAPI) -> None:
    """Verify NotFoundError produces HTTP 404 with standard envelope."""
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=error_test_app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/raise-not-found", headers={"X-Request-ID": "nf-1"}
        )
        assert response.status_code == 404
        body = response.json()
        assert body["error"]["code"] == "ACCOUNT_NOT_FOUND"
        assert body["error"]["details"] == {"account_id": "acc-999"}
        assert body["error"]["request_id"] == "nf-1"


@pytest.mark.asyncio
async def test_internal_diagnostic_context_not_exposed_in_response_or_logs(
    error_test_app: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    """Verify sensitive sentinel diagnostics are excluded from client responses and rendered logs."""
    from httpx import ASGITransport, AsyncClient

    caplog.set_level(logging.WARNING)
    sentinel = "SENTINEL_SECRET_TOKEN_XYZ_999"
    sensitive_sql = "SELECT * FROM users WHERE password='super_secret'"

    async with AsyncClient(
        transport=ASGITransport(app=error_test_app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/raise-internal-diagnostics", headers={"X-Request-ID": "diag-test"}
        )
        assert response.status_code == 400
        body = response.json()

        # Check response body: sentinel and sensitive SQL must not be present
        assert sentinel not in str(body)
        assert sensitive_sql not in str(body)
        assert body["error"]["code"] == "BUSINESS_RULE_VIOLATION"
        assert body["error"]["details"] == {"safe_reference": "REF-100"}
        assert body["error"]["request_id"] == "diag-test"

    # Check captured log records: sentinel must not appear in rendered log message or extra attributes
    handler_records = [r for r in caplog.records if r.name == "finsignal.handlers"]
    assert len(handler_records) >= 1
    log_text = " ".join([r.getMessage() for r in handler_records])
    assert sentinel not in log_text
    assert sensitive_sql not in log_text

    for record in handler_records:
        assert getattr(record, "has_internal_context", None) is True
        assert sentinel not in str(getattr(record, "__dict__", {}))


@pytest.mark.asyncio
async def test_sqlalchemy_error_does_not_leak_sql_or_credentials(
    error_test_app: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    """Verify SQLAlchemy error returns sanitized 500 without leaking SQL, SSN, or db credentials."""
    from httpx import ASGITransport, AsyncClient

    caplog.set_level(logging.ERROR)
    sensitive_ssn = "SENSITIVE_SSN_999-88-7777"
    sensitive_db_url = "postgres://dbuser:secretpass@127.0.0.1:5432/db"

    async with AsyncClient(
        transport=ASGITransport(app=error_test_app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/raise-database-error", headers={"X-Request-ID": "db-sec-test"}
        )
        assert response.status_code == 500
        body = response.json()

        # Client response must be generic and leak zero SQL/parameters/passwords
        assert body["error"]["code"] == "DATABASE_ERROR"
        assert body["error"]["message"] == "A database error occurred."
        assert body["error"]["details"] == {}
        assert body["error"]["request_id"] == "db-sec-test"
        assert sensitive_ssn not in str(body)
        assert sensitive_db_url not in str(body)
        assert "secret_accounts" not in str(body)

    # Server logs must capture only exception class name and request ID, not raw statement or parameters
    db_records = [r for r in caplog.records if r.name == "finsignal.handlers"]
    assert len(db_records) >= 1
    log_text = " ".join([r.getMessage() for r in db_records])
    assert sensitive_ssn not in log_text
    assert sensitive_db_url not in log_text
    assert "secret_accounts" not in log_text
    assert getattr(db_records[0], "exception_class", None) == "DBAPIError"


@pytest.mark.asyncio
async def test_request_validation_sanitizes_input_reflections_and_sentinels(
    error_test_app: FastAPI,
) -> None:
    """Verify Pydantic validation failures do not reflect caller input values or sensitive keys."""
    from httpx import ASGITransport, AsyncClient

    sensitive_input = "MALICIOUS_INPUT_SECRET_PASSWORD"
    sensitive_key = "UNEXPECTED_SENTINEL_CREDIT_CARD_NUMBER"

    payload_with_bad_input = {
        "amount": sensitive_input,
        "currency": "TOOLONG",
        sensitive_key: "1234-5678-9012-3456",
    }

    async with AsyncClient(
        transport=ASGITransport(app=error_test_app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/validate-input",
            json=payload_with_bad_input,
            headers={"X-Request-ID": "val-sec-1"},
        )
        assert response.status_code == 422
        body = response.json()

        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert body["error"]["message"] == "Request validation failed."
        assert body["error"]["request_id"] == "val-sec-1"

        # Verify caller input values are not reflected in response
        assert sensitive_input not in str(body)
        # Verify unexpected sensitive key is not reflected verbatim
        assert sensitive_key not in str(body)

        # Field locations must be clean predictable labels
        details = body["error"]["details"]
        assert "amount" in details
        assert "Value must be a valid decimal amount." in details["amount"]
        assert "currency" in details
        assert "Value is too long." in details["currency"]
        assert "extra_fields" in details
        assert "Unexpected field in payload." in details["extra_fields"]


@pytest.mark.asyncio
async def test_starlette_http_exception_sanitizes_message_and_preserves_protocol_headers(
    error_test_app: FastAPI,
) -> None:
    """Verify Starlette HTTP exception maps to allowlisted safe message and preserves headers."""
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=error_test_app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/raise-starlette-401", headers={"X-Request-ID": "auth-401"}
        )
        assert response.status_code == 401
        assert response.headers.get("WWW-Authenticate") == "Bearer"

        body = response.json()
        assert body["error"]["code"] == "HTTP_401"
        assert (
            body["error"]["message"]
            == "Authentication credentials were not provided or are invalid."
        )
        assert "Internal token decode failure" not in str(body)
        assert body["error"]["request_id"] == "auth-401"


@pytest.mark.asyncio
async def test_starlette_404_not_found_on_unknown_endpoint(
    error_test_app: FastAPI,
) -> None:
    """Verify requesting an unknown route returns sanitized 404 envelope."""
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=error_test_app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/non-existent-route", headers={"X-Request-ID": "nf-404"}
        )
        assert response.status_code == 404
        body = response.json()
        assert body["error"]["code"] == "RESOURCE_NOT_FOUND"
        assert body["error"]["message"] == "The requested resource was not found."
        assert body["error"]["request_id"] == "nf-404"


@pytest.mark.asyncio
async def test_sample_payload_amount_bounds_validation(
    error_test_app: FastAPI,
) -> None:
    """Verify that zero and negative amounts are rejected with 422 while positive amounts succeed."""
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=error_test_app), base_url="http://test"
    ) as client:
        # 1. Positive amount succeeds
        resp_pos = await client.post(
            "/validate-input",
            json={"amount": "100.50", "currency": "USD"},
            headers={"X-Request-ID": "val-pos"},
        )
        assert resp_pos.status_code == 200
        assert resp_pos.json() == {"status": "ok", "amount": "100.50"}

        # 2. Zero amount is rejected
        resp_zero = await client.post(
            "/validate-input",
            json={"amount": "0.00", "currency": "USD"},
            headers={"X-Request-ID": "val-zero"},
        )
        assert resp_zero.status_code == 422
        body_zero = resp_zero.json()
        assert body_zero["error"]["code"] == "VALIDATION_ERROR"
        assert "amount" in body_zero["error"]["details"]
        assert (
            "Value is below minimum threshold."
            in body_zero["error"]["details"]["amount"]
        )

        # 3. Negative amount is rejected
        resp_neg = await client.post(
            "/validate-input",
            json={"amount": "-15.75", "currency": "USD"},
            headers={"X-Request-ID": "val-neg"},
        )
        assert resp_neg.status_code == 422
        body_neg = resp_neg.json()
        assert body_neg["error"]["code"] == "VALIDATION_ERROR"
        assert "amount" in body_neg["error"]["details"]
        assert (
            "Value is below minimum threshold."
            in body_neg["error"]["details"]["amount"]
        )


@pytest.mark.asyncio
async def test_validation_location_sanitization_filters_invalid_tokens(
    error_test_app: FastAPI,
) -> None:
    """Verify non-alphanumeric location tokens (e.g. <script>) are stripped, falling back safely."""
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=error_test_app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/raise-synthetic-validation-error",
            headers={"X-Request-ID": "val-token-sanitize"},
        )
        assert response.status_code == 422
        body = response.json()

        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert body["error"]["message"] == "Request validation failed."
        assert body["error"]["request_id"] == "val-token-sanitize"

        # Verify malicious tokens, internal messages, and inputs are never reflected
        assert "<script>" not in str(body)
        assert "alert(1)" not in str(body)
        assert "malicious[injection]" not in str(body)
        assert "internal parser message" not in str(body)
        assert "super_secret_input_value" not in str(body)

        details = body["error"]["details"]
        # Error 1 loc had only invalid tokens ('<script>...', 'nested field') -> falls back to 'payload'
        assert "payload" in details
        assert "Value is too short." in details["payload"]

        # Error 2 loc had ('valid_field_name', 'malicious[injection]') -> filtered to 'valid_field_name'
        assert "valid_field_name" in details
        assert "Value is too long." in details["valid_field_name"]
