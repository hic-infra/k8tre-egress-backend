from contextlib import contextmanager

from fastapi import Response
from fastapi.testclient import TestClient
from httpx import ConnectError
import pytest
import respx

from app import settings
from app.api import verify_keycloak_token


@pytest.fixture
def authed_client():
    app.dependency_overrides[verify_keycloak_token] = lambda: {
        "preferred_username": "testuser"
    }
    yield TestClient(app)
    app.dependency_overrides.clear()


@contextmanager
def mock_ucl_egress_get(project_id):
    with respx.mock(
        base_url=settings.egress_app_url, assert_all_called=False
    ) as router:
        example = [
            {
                "id": "9f73a22f",
                "file_name": "example.txt",
                "size": 2000,
                "approvals": [],
            }
        ]
        router.get(f"/{project_id}/files").mock(
            return_value=Response(
                status_code=200,
                content=json.dumps(example),
                headers={"content-type": "application/json"},
            )
        )
        yield router


@contextmanager
def mock_ucl_egress_put(project_id, file_id):
    with respx.mock(
        base_url=settings.egress_app_url, assert_all_called=False
    ) as router:
        router.put(f"/{project_id}/files/{file_id}/approve").mock(
            return_value=Response(204)
        )
        yield router


@contextmanager
def mock_ucl_egress_fail():
    with respx.mock(
        base_url=settings.egress_app_url, assert_all_called=False
    ) as router:
        router.put().mock(side_effect=ConnectError("connection failed"))
        yield router
