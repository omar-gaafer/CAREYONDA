"""Final local composition: selected UI, verified research, optional secure records."""

import logging
import os
from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import FastAPI

from app.api.authorized_records import build_authorized_router
from app.application.authorized_records import AuthorizedRecords
from app.real_data_main import create_app as create_research_app
from app.storage.authorized_postgres import PsqlRepository
from app.storage.supabase_identity import SupabaseIdentity


def create_app(
    service: AuthorizedRecords | None = None,
    *,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> FastAPI:
    # Optional external auth/database never blocks offline research startup.
    if service is None and os.environ.get("CAREYONDA_ENABLE_DATABASE") == "1":
        url = os.environ.get("CAREYONDA_SUPABASE_URL")
        key = os.environ.get("CAREYONDA_SUPABASE_PUBLIC_KEY")
        database = os.environ.get("CAREYONDA_DATABASE_URL")
        if url and key and database:
            try:
                service = AuthorizedRecords(
                    SupabaseIdentity(url, key), PsqlRepository(database)
                )
            except ValueError:
                logging.getLogger(__name__).warning(
                    "Optional database configuration invalid"
                )
    app = create_research_app()
    # Extend only header admission on the existing narrow loopback CORS policy.
    for middleware in app.user_middleware:
        if getattr(middleware.cls, "__name__", None) == "CORSMiddleware":
            middleware.kwargs["allow_headers"] = ["Content-Type", "Authorization"]
    app.include_router(build_authorized_router(service, clock))
    return app
