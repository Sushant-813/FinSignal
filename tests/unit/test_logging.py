"""Unit tests for structured logging components."""

import json
import logging
from collections.abc import Generator

import pytest
from pydantic import SecretStr

from finsignal.core.config import Settings
from finsignal.core.logging import (
    FinSignalStreamHandler,
    JsonFormatter,
    RequestIdFilter,
    TextFormatter,
    request_id_ctx,
    setup_logging,
)


@pytest.fixture(autouse=True)
def restore_root_logger() -> Generator[None, None, None]:
    """Preserve and restore root logger handlers and log level across tests."""
    root = logging.getLogger()
    old_handlers = list(root.handlers)
    old_level = root.level
    try:
        yield
    finally:
        root.handlers = old_handlers
        root.setLevel(old_level)


def test_text_formatter_with_request_id() -> None:
    """Verify TextFormatter includes bracketed request_id and message."""
    formatter = TextFormatter()
    record = logging.LogRecord(
        name="finsignal.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Sample log message",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-12345"
    formatted = formatter.format(record)
    assert "[INFO]" in formatted
    assert "[req-12345]" in formatted
    assert "Sample log message" in formatted


def test_text_formatter_missing_request_id_fallback() -> None:
    """Verify TextFormatter safely falls back when request_id is not set on record."""
    formatter = TextFormatter()
    record = logging.LogRecord(
        name="finsignal.test",
        level=logging.WARNING,
        pathname="test.py",
        lineno=10,
        msg="No request ID record",
        args=(),
        exc_info=None,
    )
    # Ensure ContextVar is default
    token = request_id_ctx.set("-")
    try:
        formatted = formatter.format(record)
        assert "[-]" in formatted
        assert "No request ID record" in formatted
    finally:
        request_id_ctx.reset(token)


def test_json_formatter_valid_structure() -> None:
    """Verify JsonFormatter outputs single-line JSON with required schema fields."""
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="finsignal.auth",
        level=logging.ERROR,
        pathname="test.py",
        lineno=25,
        msg="Operation failed",
        args=(),
        exc_info=None,
    )
    record.__dict__["request_id"] = "corr-999"
    # Attach extra safe scalars
    record.__dict__["operation"] = "login"
    record.__dict__["attempt"] = 3

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["level"] == "ERROR"
    assert parsed["logger"] == "finsignal.auth"
    assert parsed["message"] == "Operation failed"
    assert parsed["request_id"] == "corr-999"
    assert "timestamp" in parsed
    assert parsed["operation"] == "login"
    assert parsed["attempt"] == 3


def test_request_id_filter_injects_contextvar() -> None:
    """Verify RequestIdFilter reads from request_id_ctx."""
    filt = RequestIdFilter()
    token = request_id_ctx.set("ctx-trace-abc")
    try:
        record = logging.LogRecord(
            name="finsignal.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=5,
            msg="Context test",
            args=(),
            exc_info=None,
        )
        filt.filter(record)
        assert getattr(record, "request_id", None) == "ctx-trace-abc"
    finally:
        request_id_ctx.reset(token)


def test_repeated_setup_logging_idempotency() -> None:
    """Verify setup_logging does not accumulate duplicate handlers on repeated calls."""
    settings = Settings(
        environment="development",
        log_level="DEBUG",
        database_password=SecretStr("pw"),
        _env_file=None,
    )

    root = logging.getLogger()
    initial_count = len(
        [h for h in root.handlers if isinstance(h, FinSignalStreamHandler)]
    )

    setup_logging(settings)
    setup_logging(settings)
    setup_logging(settings)

    finsignal_handlers = [
        h for h in root.handlers if isinstance(h, FinSignalStreamHandler)
    ]
    assert len(finsignal_handlers) == 1
    assert initial_count <= 1


def test_setup_logging_production_environment_selects_json_formatter() -> None:
    """Verify setup_logging attaches JsonFormatter when environment is production."""
    settings = Settings(
        environment="production",
        database_password=SecretStr("pw"),
        jwt_secret_key=SecretStr("a" * 32),
        _env_file=None,
    )
    setup_logging(settings)

    root = logging.getLogger()
    finsignal_handlers = [
        h for h in root.handlers if isinstance(h, FinSignalStreamHandler)
    ]
    assert len(finsignal_handlers) == 1
    assert isinstance(finsignal_handlers[0].formatter, JsonFormatter)


def test_setup_logging_explicit_json_format_selects_json_formatter() -> None:
    """Verify setup_logging attaches JsonFormatter when log_format is explicitly json."""
    settings = Settings(
        environment="development",
        log_format="json",
        database_password=SecretStr("pw"),
        _env_file=None,
    )
    setup_logging(settings)

    root = logging.getLogger()
    finsignal_handlers = [
        h for h in root.handlers if isinstance(h, FinSignalStreamHandler)
    ]
    assert len(finsignal_handlers) == 1
    assert isinstance(finsignal_handlers[0].formatter, JsonFormatter)


def test_setup_logging_explicit_text_format_in_production() -> None:
    """Verify explicit log_format='text' overrides production environment default."""
    settings = Settings(
        environment="production",
        log_format="text",
        database_password=SecretStr("pw"),
        jwt_secret_key=SecretStr("a" * 32),
        _env_file=None,
    )
    setup_logging(settings)

    root = logging.getLogger()
    finsignal_handlers = [
        h for h in root.handlers if isinstance(h, FinSignalStreamHandler)
    ]
    assert len(finsignal_handlers) == 1
    assert isinstance(finsignal_handlers[0].formatter, TextFormatter)
