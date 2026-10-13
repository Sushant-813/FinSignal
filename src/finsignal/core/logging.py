"""Structured logging foundation using Python standard library."""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from finsignal.core.config import Settings

# Thread-safe, async-safe context variable holding the active request correlation ID
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Logging filter that injects the active request ID into LogRecord attributes."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = request_id_ctx.get("-")
        return True


class TextFormatter(logging.Formatter):
    """Human-readable text formatter for local development and testing."""

    DEFAULT_FORMAT = (
        "%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s"
    )
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self, fmt: str | None = None, datefmt: str | None = None) -> None:
        super().__init__(
            fmt=fmt or self.DEFAULT_FORMAT, datefmt=datefmt or self.DATE_FORMAT
        )

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "request_id"):
            record.request_id = request_id_ctx.get("-")
        return super().format(record)


class JsonFormatter(logging.Formatter):
    """Single-line JSON log formatter for production log aggregation."""

    def format(self, record: logging.LogRecord) -> str:
        record_request_id = getattr(record, "request_id", None) or request_id_ctx.get(
            "-"
        )
        created_dt = datetime.fromtimestamp(record.created, tz=UTC)

        log_entry: dict[str, Any] = {
            "timestamp": created_dt.isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": record_request_id,
        }

        # Include safe scalar extra attributes if attached to record
        standard_attrs = {
            "args",
            "asctime",
            "created",
            "exc_info",
            "exc_text",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "message",
            "msg",
            "name",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "thread",
            "threadName",
            "request_id",
        }
        for key, val in record.__dict__.items():
            if (
                key not in standard_attrs
                and not key.startswith("_")
                and isinstance(val, str | int | float | bool | type(None))
            ):
                log_entry[key] = val

        return json.dumps(log_entry, default=str)


class FinSignalStreamHandler(logging.StreamHandler[Any]):
    """Marker StreamHandler subclass to identify FinSignal-managed handlers."""

    pass


def setup_logging(settings: Settings) -> None:
    """Configure standard-library logging idempotently based on application settings.

    Avoids duplicating handlers when create_app() is called repeatedly in tests.
    """
    # Determine format: explicit setting takes precedence; defaults to json in prod, text in dev/test
    use_json = (
        settings.log_format == "json"
        if settings.log_format is not None
        else settings.environment == "production"
    )

    formatter: logging.Formatter = JsonFormatter() if use_json else TextFormatter()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove any existing FinSignalStreamHandler instances to prevent duplication
    for handler in list(root_logger.handlers):
        if isinstance(handler, FinSignalStreamHandler):
            root_logger.removeHandler(handler)

    handler = FinSignalStreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(formatter)

    root_logger.addHandler(handler)
