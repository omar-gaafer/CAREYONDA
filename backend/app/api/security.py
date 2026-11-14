"""Bound requests before parsing; attach safe error codes and server-owned IDs."""

import uuid

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.api.contracts import ErrorDetail, ErrorResponse

MAX_BODY_BYTES = 16_384
ALLOWED_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:4173",
    "http://localhost:4173",
)


def error_response(code: str, correlation: str, status: int) -> JSONResponse:
    return JSONResponse(
        ErrorResponse(
            error=ErrorDetail(code=code, correlation_id=correlation)
        ).model_dump(),
        status_code=status,
        headers={"X-Correlation-ID": correlation, "Cache-Control": "no-store"},
    )


class RequestGuard:
    def __init__(
        self, app: ASGIApp, allowed_origins: tuple[str, ...] = ALLOWED_ORIGINS
    ) -> None:
        self.app = app
        self.allowed_origins = allowed_origins

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        correlation = uuid.uuid4().hex
        scope.setdefault("state", {})["correlation_id"] = correlation
        headers = dict(scope["headers"])

        async def reject(code: str, status: int) -> None:
            response = error_response(code, correlation, status)
            allowed_origin = dict(scope["headers"]).get(b"origin", b"").decode("latin1")
            if allowed_origin in self.allowed_origins:
                response.headers["Access-Control-Allow-Origin"] = allowed_origin
                response.headers["Access-Control-Expose-Headers"] = "X-Correlation-ID"
            await response(scope, receive, send)

        if headers.get(b"host", b"").split(b":")[0] not in (b"127.0.0.1", b"localhost"):
            await reject("host_not_allowed", 400)
            return
        origin = headers.get(b"origin")
        if origin is not None and origin.decode("latin1") not in self.allowed_origins:
            await reject("origin_not_allowed", 403)
            return
        if len(scope.get("query_string", b"")) > 2048:
            await reject("query_too_large", 414)
            return
        try:
            length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            await reject("invalid_content_length", 400)
            return
        if length < 0 or length > MAX_BODY_BYTES:
            await reject("request_too_large", 413)
            return
        if (
            scope["method"] == "POST"
            and headers.get(b"content-type", b"").split(b";")[0].strip()
            != b"application/json"
        ):
            await reject("json_required", 415)
            return
        chunks: list[bytes] = []
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            part = message.get("body", b"")
            size += len(part)
            if size > MAX_BODY_BYTES:
                await reject("request_too_large", 413)
                return
            chunks.append(part)
            if not message.get("more_body", False):
                break
        sent_body = False
        started = False

        async def replay() -> Message:
            nonlocal sent_body
            if not sent_body:
                sent_body = True
                return {
                    "type": "http.request",
                    "body": b"".join(chunks),
                    "more_body": False,
                }
            return await receive()

        async def safe_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                message["headers"] = [
                    *[
                        (key, value)
                        for key, value in message.get("headers", [])
                        if key.lower()
                        not in (
                            b"x-correlation-id",
                            b"cache-control",
                            b"x-content-type-options",
                        )
                    ],
                    (b"x-correlation-id", correlation.encode()),
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                ]
            await send(message)

        try:
            await self.app(scope, replay, safe_send)
        except Exception:
            if started:
                raise
            await reject("internal_error", 500)
