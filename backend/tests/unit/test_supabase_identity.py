"""Auth provider transport tests; no fabricated authentication in runtime code."""

from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.application.authorized_records import AccessDenied, StorageUnavailable
from app.final_main import create_app
from app.storage.supabase_identity import SupabaseIdentity


@pytest.mark.parametrize("status", [200, 401, 403, 302, 500])
def test_supabase_verifies_remotely(monkeypatch: MonkeyPatch, status: int) -> None:
    original = httpx.Client
    seen = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            status,
            json={"id": "11111111-1111-4111-8111-111111111111"},
            headers={"Location": "https://untrusted.invalid"},
        )

    def client(**kwargs: object) -> httpx.Client:
        return original(transport=httpx.MockTransport(handle))

    monkeypatch.setattr(httpx, "Client", client)
    provider = SupabaseIdentity(
        "https://configured-project.supabase.co", "public-test-key"
    )
    if status == 200:
        assert provider.verify("synthetic-token") == UUID(
            "11111111-1111-4111-8111-111111111111"
        )
    else:
        with pytest.raises(
            AccessDenied if status in (401, 403) else StorageUnavailable
        ):
            provider.verify("synthetic-token")
    assert len(seen) == 1
    assert seen[0].url.path == "/auth/v1/user"
    assert seen[0].headers["Authorization"] == "Bearer synthetic-token"


@pytest.mark.parametrize(
    "url",
    [
        "http://remote.invalid",
        "https://user:secret@remote.invalid",
        "https://remote.invalid/path",
        "https://remote.invalid?key=x",
    ],
)
def test_invalid_auth_origin(url: str) -> None:
    with pytest.raises(ValueError):
        SupabaseIdentity(url, "test-key")


def test_cors_admits_auth_only_from_local_ui() -> None:
    with TestClient(create_app(), base_url="http://127.0.0.1") as client:
        headers = {
            "Origin": "http://127.0.0.1:4173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        }
        assert client.options("/api/v1/account/me", headers=headers).status_code == 200
        headers["Origin"] = "https://external.invalid"
        assert client.options("/api/v1/account/me", headers=headers).status_code == 403
