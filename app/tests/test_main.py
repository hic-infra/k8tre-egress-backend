from contextlib import contextmanager
import secrets

from httpx import ConnectError, Response
from fastapi.testclient import TestClient
import jwt
import pytest
import respx
import json
from app.settings import settings
from app.api import verify_keycloak_token
from ..main import app

client = TestClient(app)


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


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}


def test_get_no_token(monkeypatch):
    monkeypatch.setattr(settings, "disable_auth", False)
    response = client.get("/egress/1")
    assert response.status_code == 401


def test_put_no_token(monkeypatch):
    monkeypatch.setattr(settings, "disable_auth", False)
    response = client.put("/egress/1")
    assert response.status_code == 401


def test_protected_get_with_invalid_token():
    response = client.get("/egress/1", headers={"Authorization": "Bearer sometoken"})
    assert response.status_code == 401


def test_egress_get_with_invalid_jwt(authed_client):
    project_id = "1"
    dct = {"projectId": project_id, "userId": 1, "bucketId": "test-bucket"}
    key = secrets.token_hex(32)
    token = jwt.encode(dct, key)
    response = authed_client.get(f"/egress/{token}")
    assert response.status_code == 404


def test_egress_get_with_valid_jwt(authed_client):
    project_id = "1"
    dct = {"projectId": project_id, "userId": "user1", "bucketId": "test-bucket"}
    token = jwt.encode(dct, settings.secret_key)
    with mock_ucl_egress_get(project_id) as router:
        response = authed_client.get(f"/egress/{token}")
        assert response.status_code == 200


def test_egress_put_with_valid_jwt(authed_client):
    project_id = "1"
    file_id = "9f73a22f"
    dct = {"projectId": project_id, "userId": "user1", "bucketId": "test-bucket"}
    token = jwt.encode(dct, settings.secret_key)
    body = {file_id: "approve"}
    with mock_ucl_egress_put(project_id, file_id) as router:
        response = authed_client.put(f"/egress/{token}", json=body)
        assert response.status_code == 200


def test_egress_put_fail(authed_client):
    project_id = "1"
    file_id = "9f73a22f"
    dct = {"projectId": project_id, "userId": "user1", "bucketId": "test-bucket"}
    token = jwt.encode(dct, settings.secret_key)
    body = {file_id: "approve"}
    with mock_ucl_egress_fail() as router:
        response = authed_client.put(f"/egress/{token}", json=body)
        assert response.status_code == 502
