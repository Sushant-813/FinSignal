"""Pure ASGI middleware for request correlation, latency measurement, and fallback error handling."""

import json
import logging
import re
import time
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from finsignal.core.logging import request_id_ctx

logger = logging.getLogger("finsignal.middleware")
REQUEST_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


class RequestIdMiddleware:
    """Pure ASGI middleware managing request correlation IDs, latency tracking, and unexpected exception handling.

    Client-supplied request IDs are treated strictly as correlation hints, never as an authentication
    or authorization signal.
    """

    def __init__(self, app: ASGIApp, header_name: str = "X-Request-ID") -> None:
        self.app = app
        self.header_name_bytes = header_name.lower().encode("latin-1")
        self.header_name_str = header_name

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 1. Extract and strictly validate client-supplied ID
        request_id: str | None = None
        for name, value in scope.get("headers", []):
            if name.lower() == self.header_name_bytes:
                candidate = value.decode("latin-1", errors="ignore").strip()
                if REQUEST_ID_REGEX.match(candidate):
                    request_id = candidate
                break

        # 2. Fallback to UUID4 if missing or invalid
        if not request_id:
            request_id = uuid.uuid4().hex

        # 3. Bind to ContextVar
        token = request_id_ctx.set(request_id)
        start_time = time.perf_counter()
        response_started = False

        async def send_with_headers(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                # De-duplicate: filter out any pre-existing instances of these headers
                headers = [
                    (k, v)
                    for (k, v) in message.get("headers", [])
                    if k.lower() not in (self.header_name_bytes, b"x-process-time")
                ]
                headers.append((self.header_name_bytes, request_id.encode("latin-1")))
                headers.append(
                    (b"x-process-time", f"{duration_ms:.2f}ms".encode("latin-1"))
                )
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        except Exception as exc:
            # 4. Safe Logging: Log metadata only, avoiding raw exception text/tracebacks in routine logs
            logger.error(
                "Unhandled application exception escaping boundary: exception_class=%s",
                exc.__class__.__name__,
                extra={
                    "request_id": request_id,
                    "exception_class": exc.__class__.__name__,
                },
            )

            # 5. Differentiated Handling based on response state
            if response_started:
                # Response headers already committed; HTTP protocol prohibits replacement.
                # Re-raise so the ASGI transport aborts cleanly; do NOT swallow.
                raise

            # Attempt a single sanitized 500 fallback response
            fallback_body = json.dumps(
                {
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected internal server error occurred.",
                        "details": {},
                        "request_id": request_id,
                    }
                }
            ).encode("utf-8")

            try:
                await send_with_headers(
                    {
                        "type": "http.response.start",
                        "status": 500,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (
                                b"content-length",
                                str(len(fallback_body)).encode("latin-1"),
                            ),
                        ],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": fallback_body,
                        "more_body": False,
                    }
                )
            except Exception:
                # Transport-level failure while sending fallback response; log safely without recursion
                logger.error(
                    "Failed to deliver fallback 500 response",
                    extra={"request_id": request_id},
                )
        finally:
            # 6. Guaranteed ContextVar cleanup across all execution paths
            request_id_ctx.reset(token)
