"""Explicit local-only synthetic viewer composition; never used by public factories."""

import ipaddress
import os

from fastapi import FastAPI
from starlette.types import ASGIApp, Receive, Scope, Send

from app.api.security import error_response
from app.api.synthetic_viewer import build_synthetic_router
from app.final_main import create_app as create_final_app
from app.storage.synthetic_viewer import SyntheticViewer

VIEWER_ORIGINS = ("http://127.0.0.1:5181", "http://localhost:5181")


class LocalOnly:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            client = scope.get("client")
            try:
                local = bool(client and ipaddress.ip_address(client[0]).is_loopback)
            except ValueError:
                local = False
            headers = dict(scope["headers"])
            if not local or any(
                h in headers
                for h in (
                    b"forwarded",
                    b"x-forwarded-for",
                    b"x-real-ip",
                    b"x-forwarded-host",
                )
            ):
                await error_response("local_viewer_only", "local-viewer", 403)(
                    scope, receive, send
                )
                return
        await self.app(scope, receive, send)


def create_app() -> FastAPI:
    app = create_final_app()
    viewer = None
    if os.environ.get("CAREYONDA_ENABLE_SYNTHETIC_DB_VIEWER") == "1":
        try:
            viewer = SyntheticViewer(os.environ.get("CAREYONDA_SYNTHETIC_DB_URL", ""))
        except ValueError:
            viewer = None
    app.include_router(build_synthetic_router(viewer))
    for middleware in app.user_middleware:
        name = getattr(middleware.cls, "__name__", None)
        if name == "RequestGuard":
            middleware.kwargs["allowed_origins"] = VIEWER_ORIGINS
        if name == "CORSMiddleware":
            middleware.kwargs["allow_origins"] = list(VIEWER_ORIGINS)
    app.add_middleware(LocalOnly)
    return app
