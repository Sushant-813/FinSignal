"""API tests for RequestIdMiddleware correlation, headers, and exception behavior."""

import logging
import re
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from finsignal.core.config import Settings
from finsignal.core.logging import RequestIdFilter, request_id_ctx
from finsignal.core.middleware import RequestIdMiddleware
from finsignal.main import create_app


@pytest.fixture
def middleware_test_app() -> FastAPI:
    """Provide an isolated FastAPI app wired with RequestIdMiddleware for edge-case testing."""
    application = FastAPI()
    application.add_middleware(RequestIdMiddleware)

    @application.get("/success")
    async def success_endpoint() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/with-existing-headers")
    async def existing_headers_endpoint() -> JSONResponse:
        # Simulate an endpoint or handler that tries to set its own X-Request-ID or X-Process-Time
        return JSONResponse(
            content={"status": "ok"},
            headers={
                "X-Request-ID": "inner-id-attempt",
                "X-Process-Time": "999ms",
            },
        )

    @application.get("/fail-pre-start")
    async def fail_pre_start() -> dict[str, str]:
        msg = "Unexpected pre-start failure"
        raise RuntimeError(msg)

    @application.get("/fail-mid-stream")
    async def fail_mid_stream() -> StreamingResponse:
        async def event_generator() -> AsyncGenerator[bytes, None]:
            yield b"first chunk\n"
            msg = "Mid-stream streaming explosion"
            raise RuntimeError(msg)

        return StreamingResponse(event_generator(), media_type="text/plain")

    return application


@pytest.mark.asyncio
async def test_request_id_generated_when_missing(middleware_test_app: FastAPI) -> None:
    """Verify missing X-Request-ID generates a 32-character hex UUID in response."""
    async with AsyncClient(
        transport=ASGITransport(app=middleware_test_app), base_url="http://test"
    ) as client:
        response = await client.get("/success")
        assert response.status_code == 200
        req_id = response.headers.get("X-Request-ID")
        assert req_id is not None
        assert re.match(r"^[0-9a-f]{32}$", req_id)


@pytest.mark.asyncio
async def test_request_id_preserved_when_valid(middleware_test_app: FastAPI) -> None:
    """Verify valid client-supplied X-Request-ID is preserved and returned."""
    client_id = "trace-client-1234_abc"
    async with AsyncClient(
        transport=ASGITransport(app=middleware_test_app), base_url="http://test"
    ) as client:
        response = await client.get("/success", headers={"X-Request-ID": client_id})
        assert response.status_code == 200
        assert response.headers.get("X-Request-ID") == client_id


@pytest.mark.asyncio
async def test_request_id_regenerated_when_malformed(
    middleware_test_app: FastAPI,
) -> None:
    """Verify malformed client ID (control chars, spaces, symbols) is discarded and regenerated."""
    async with AsyncClient(
        transport=ASGITransport(app=middleware_test_app), base_url="http://test"
    ) as client:
        # Invalid with space and special characters
        response = await client.get(
            "/success", headers={"X-Request-ID": "bad id with spaces!"}
        )
        assert response.status_code == 200
        req_id = response.headers.get("X-Request-ID")
        assert req_id is not None
        assert req_id != "bad id with spaces!"
        assert re.match(r"^[0-9a-f]{32}$", req_id)


@pytest.mark.asyncio
async def test_request_id_regenerated_when_too_long(
    middleware_test_app: FastAPI,
) -> None:
    """Verify client ID exceeding 64 characters is discarded and regenerated."""
    oversized_id = "a" * 65
    async with AsyncClient(
        transport=ASGITransport(app=middleware_test_app), base_url="http://test"
    ) as client:
        response = await client.get("/success", headers={"X-Request-ID": oversized_id})
        assert response.status_code == 200
        req_id = response.headers.get("X-Request-ID")
        assert req_id is not None
        assert req_id != oversized_id
        assert re.match(r"^[0-9a-f]{32}$", req_id)


@pytest.mark.asyncio
async def test_exactly_one_request_id_and_process_time_header(
    middleware_test_app: FastAPI,
) -> None:
    """Verify middleware de-duplicates headers, enforcing exactly one authoritative instance."""
    async with AsyncClient(
        transport=ASGITransport(app=middleware_test_app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/with-existing-headers", headers={"X-Request-ID": "authoritative-id"}
        )
        assert response.status_code == 200
        # In httpx, multi-headers are separated by comma if duplicated
        req_id = response.headers.get("X-Request-ID")
        assert req_id == "authoritative-id"
        assert "inner-id-attempt" not in str(req_id)

        proc_time = response.headers.get("X-Process-Time")
        assert proc_time is not None
        assert "999ms" not in proc_time
        assert re.match(r"^\d+\.\d{2}ms$", proc_time)


@pytest.mark.asyncio
async def test_contextvar_cleanup_after_success_and_failure(
    middleware_test_app: FastAPI,
) -> None:
    """Verify request_id_ctx is reset to default '-' after both successful and failed requests."""
    assert request_id_ctx.get("-") == "-"

    async with AsyncClient(
        transport=ASGITransport(app=middleware_test_app), base_url="http://test"
    ) as client:
        # Success path
        await client.get("/success")
        assert request_id_ctx.get("-") == "-"

        # Failure path
        await client.get("/fail-pre-start")
        assert request_id_ctx.get("-") == "-"


@pytest.mark.asyncio
async def test_request_id_correlation_with_application_logs(
    middleware_test_app: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    """Verify log records emitted during request execution capture the exact request ID."""
    test_logger = logging.getLogger("finsignal.test_logger")
    test_logger.addFilter(RequestIdFilter())

    @middleware_test_app.get("/logged-route")
    async def logged_route() -> dict[str, str]:
        test_logger.info("Executing logged route business logic")
        return {"status": "logged"}

    caplog.set_level(logging.INFO)
    async with AsyncClient(
        transport=ASGITransport(app=middleware_test_app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/logged-route", headers={"X-Request-ID": "log-trace-555"}
        )
        assert response.status_code == 200
        req_id = response.headers.get("X-Request-ID")
        assert req_id == "log-trace-555"

    records = [r for r in caplog.records if r.name == "finsignal.test_logger"]
    assert len(records) >= 1
    assert getattr(records[0], "request_id", None) == "log-trace-555"


@pytest.mark.asyncio
async def test_unhandled_pre_start_exception_sanitized_500(
    middleware_test_app: FastAPI,
) -> None:
    """Verify unexpected pre-start exception produces sanitized HTTP 500 JSON envelope with headers."""
    async with AsyncClient(
        transport=ASGITransport(app=middleware_test_app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/fail-pre-start", headers={"X-Request-ID": "err-corr-777"}
        )
        assert response.status_code == 500
        assert response.headers.get("X-Request-ID") == "err-corr-777"
        assert response.headers.get("X-Process-Time") is not None

        body = response.json()
        assert "error" in body
        assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert (
            body["error"]["message"] == "An unexpected internal server error occurred."
        )
        assert body["error"]["details"] == {}
        assert body["error"]["request_id"] == "err-corr-777"
        # Ensure no traceback or internal error message is leaked
        assert "Unexpected pre-start failure" not in str(body)


@pytest.mark.asyncio
async def test_mid_stream_exception_is_reraised_without_duplicate_response_start(
    middleware_test_app: FastAPI,
) -> None:
    """Verify exception after response start is re-raised rather than swallowed, and context cleaned."""
    async with AsyncClient(
        transport=ASGITransport(app=middleware_test_app), base_url="http://test"
    ) as client:
        # In httpx streaming or standard ASGI transport, raising mid-stream propagates
        with pytest.raises(RuntimeError, match="Mid-stream streaming explosion"):
            await client.get("/fail-mid-stream")

    # Verify contextvar was safely reset in finally even when exception escaped
    assert request_id_ctx.get("-") == "-"


@pytest.mark.asyncio
async def test_failed_fallback_send_does_not_recurse() -> None:
    """Verify that if the ASGI transport fails while sending fallback 500, no recursive crash occurs."""

    async def broken_app(scope: Any, receive: Any, send: Any) -> None:
        msg = "Initial failure"
        raise RuntimeError(msg)

    async def broken_send(message: Any) -> None:
        # Fail when sending http.response.start or http.response.body
        msg = "Socket disconnected"
        raise ConnectionResetError(msg)

    async def dummy_receive() -> dict[str, Any]:
        return {"type": "http.request"}

    middleware = RequestIdMiddleware(broken_app)
    scope: dict[str, Any] = {
        "type": "http",
        "method": "GET",
        "headers": [(b"x-request-id", b"broken-conn-id")],
    }

    # Calling middleware should execute without raising or recursing unbounded
    await middleware(scope, dummy_receive, broken_send)
    assert request_id_ctx.get("-") == "-"


@pytest.mark.asyncio
async def test_configurable_request_id_header_app_wiring() -> None:
    """Verify application wiring when configured with a non-default header (e.g. X-Correlation-ID)."""
    custom_settings = Settings(
        request_id_header="X-Correlation-ID",
        database_password=SecretStr("pw"),
        _env_file=None,
    )
    app = create_app(custom_settings)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Valid custom header accepted and returned under configured name
        resp_valid = await client.get(
            "/health", headers={"X-Correlation-ID": "custom-trace-123"}
        )
        assert resp_valid.status_code == 200
        assert resp_valid.headers.get("X-Correlation-ID") == "custom-trace-123"
        assert resp_valid.headers.get("X-Request-ID") is None
        assert resp_valid.headers.get("X-Process-Time") is not None

        # Ensure no duplicate headers in raw response
        corr_headers = [
            v for k, v in resp_valid.headers.raw if k.lower() == b"x-correlation-id"
        ]
        assert len(corr_headers) == 1

        # 2. Missing header generates 32-hex UUID under configured name
        resp_missing = await client.get("/health")
        assert resp_missing.status_code == 200
        gen_id = resp_missing.headers.get("X-Correlation-ID")
        assert gen_id is not None
        assert len(gen_id) == 32
        assert re.match(r"^[0-9a-f]{32}$", gen_id)
        assert resp_missing.headers.get("X-Request-ID") is None

        # 3. Malformed header is discarded and regenerated under configured name
        resp_malformed = await client.get(
            "/health", headers={"X-Correlation-ID": "bad value with spaces!"}
        )
        assert resp_malformed.status_code == 200
        fallback_id = resp_malformed.headers.get("X-Correlation-ID")
        assert fallback_id is not None
        assert fallback_id != "bad value with spaces!"
        assert len(fallback_id) == 32
        assert re.match(r"^[0-9a-f]{32}$", fallback_id)
