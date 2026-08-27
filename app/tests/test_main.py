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


def create_token(project_id):
    dct = {
        "projectId": project_id,
        "userId": "user1",
        "bucketId": "test-bucket",
        "version": "260819-134427",
    }
    return jwt.encode(dct, settings.jwt_secret_key)


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
                "file_name": "5/260819-134427/example.txt",
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
def mock_ucl_egress_get_with_odd_filename(project_id):
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
        router.put(f"/{project_id}/files/{file_id}/reject").mock(
            return_value=Response(204)
        )
        yield router


@contextmanager
def mock_ucl_egress_audit_trail_get(project_id):
    body = [
        {
            "action": "Approval",
            "comment": "",
            "datetime": "2026-07-07T12:51:10.252099843Z",
            "destination": "/",
            "file_id": "9f73a22f",
            "user_id": "user1",
        },
        {
            "action": "Download",
            "comment": "",
            "datetime": "2026-07-09T09:37:27.805943177Z",
            "destination": "/",
            "file_id": "9f73a22f",
            "user_id": "",
        },
        {
            "action": "Rejection",
            "comment": "Example",
            "datetime": "2026-07-09T09:37:43.442483337Z",
            "destination": "/",
            "file_id": "9f73a22f",
            "user_id": "user1",
        },
    ]
    with respx.mock(
        base_url=settings.egress_app_url, assert_all_called=False
    ) as router:
        router.get(f"/{project_id}/events").mock(
            return_value=Response(
                status_code=200,
                content=json.dumps(body),
                headers={"content-type": "application/json"},
            )
        )
        yield router


@contextmanager
def mock_ucl_egress_audit_trail_of_nonexistant_project_get(project_id):
    body = []
    with respx.mock(
        base_url=settings.egress_app_url, assert_all_called=False
    ) as router:
        router.get(f"/{project_id}/events").mock(
            return_value=Response(
                status_code=200,
                content=json.dumps(body),
                headers={"content-type": "application/json"},
            )
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
    key = secrets.token_hex(32)
    dct = {
        "projectId": project_id,
        "userId": 1,
        "bucketId": "test-bucket",
        "version": "260819-134427",
    }
    key = secrets.token_hex(32)
    token = jwt.encode(dct, key)
    response = authed_client.get(f"/egress/{token}")
    assert response.status_code == 404


def test_egress_get_with_valid_jwt(authed_client):
    project_id = "1"
    token = create_token(project_id)
    with mock_ucl_egress_get(project_id) as router, mock_ucl_egress_audit_trail_get(
        project_id
    ) as audit_router:
        response = authed_client.get(f"/egress/{token}")
        assert response.status_code == 200
        res = response.json()[0]
        assert res["id"] == "9f73a22f"
        assert len(res["approvals"]) > 0
        assert res["approvals"][0]["action"] == "reject"


def test_egress_get_with_odd_filename(authed_client):
    project_id = "1"
    token = create_token(project_id)

    with mock_ucl_egress_get_with_odd_filename(
        project_id
    ) as router, mock_ucl_egress_audit_trail_get(project_id) as audit_router:
        response = authed_client.get(f"/egress/{token}")
        assert response.status_code == 200
        res = response.json()
        assert len(res) == 0  # A filename that doesn't fit shouldn't be returned


def test_egress_get_audit_trail(authed_client):
    project_id = "1"
    token = create_token(project_id)

    with mock_ucl_egress_audit_trail_get(project_id) as router:
        response = authed_client.get(f"/egress/audit/{token}")
        assert response.status_code == 200
        res = response.json()
        assert len(res) == 3


def test_egress_nonexistant_project(authed_client):
    project_id = "5"
    token = create_token(project_id)

    with mock_ucl_egress_audit_trail_of_nonexistant_project_get(project_id) as router:
        response = authed_client.get(f"/egress/audit/{token}")
        res = response.json()
        assert len(res) == 0


def test_egress_approve_put_without_comment(authed_client):
    project_id = "1"
    file_id = "9f73a22f"
    token = create_token(project_id)

    body = {file_id: {"status": "approve", "comment": ""}}
    with mock_ucl_egress_put(project_id, file_id) as router:
        response = authed_client.put(f"/egress/{token}", json=body)
        assert response.status_code == 422


def test_egress_approve_put_with_valid_jwt(authed_client):
    project_id = "1"
    file_id = "9f73a22f"
    token = create_token(project_id)

    body = {file_id: {"status": "approve", "comment": "example"}}
    with mock_ucl_egress_put(project_id, file_id) as router:
        response = authed_client.put(f"/egress/{token}", json=body)
        assert response.status_code == 200


def test_egress_reject_put_with_valid_jwt(authed_client):
    project_id = "1"
    file_id = "9f73a22f"
    token = create_token(project_id)

    body = {file_id: {"status": "reject", "comment": "example"}}
    with mock_ucl_egress_put(project_id, file_id) as router:
        response = authed_client.put(f"/egress/{token}", json=body)
        assert response.status_code == 200


def test_egress_put_fail(authed_client):
    project_id = "1"
    file_id = "9f73a22f"
    token = create_token(project_id)

    body = {file_id: {"status": "approve", "comment": "example"}}
    with mock_ucl_egress_fail() as router:
        response = authed_client.put(f"/egress/{token}", json=body)
        assert response.status_code == 502
