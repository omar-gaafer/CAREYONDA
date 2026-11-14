"""Optional Supabase Auth token verification; never trust client-selected roles."""

from urllib.parse import urlparse
from uuid import UUID

import httpx
from pydantic import BaseModel, ValidationError

from app.application.authorized_records import AccessDenied, StorageUnavailable


class AuthUser(BaseModel):
    id: UUID


class SupabaseIdentity:
    def __init__(self, url: str, public_key: str) -> None:
        parsed = urlparse(url)
        if (
            parsed.scheme != "https"
            or parsed.path not in ("", "/")
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("an explicit HTTPS Supabase origin is required")
        self.url = url.rstrip("/")
        self.public_key = public_key

    def verify(self, token: str) -> UUID:
        if not token or len(token) > 8192 or any(c.isspace() for c in token):
            raise AccessDenied
        try:
            with httpx.Client(
                timeout=5, follow_redirects=False, trust_env=False
            ) as client:
                response = client.get(
                    self.url + "/auth/v1/user",
                    headers={
                        "apikey": self.public_key,
                        "Authorization": "Bearer " + token,
                    },
                )
            if response.status_code in (400, 401, 403):
                raise AccessDenied
            if response.status_code != 200 or len(response.content) > 65536:
                raise StorageUnavailable
            return AuthUser.model_validate_json(response.content).id
        except (httpx.HTTPError, ValidationError) as exc:
            raise StorageUnavailable("identity verification unavailable") from exc
