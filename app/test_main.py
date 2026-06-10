import secrets

from fastapi.testclient import TestClient
import jwt
import pytest

from app.settings import settings
from app.api import verify_token
from .main import app

client = TestClient(app)


def mock_verify_token():
    return {"preferred_username": "testuser", "realm_access": {"roles": ["user"]}}


@pytest.fixture
def authed_client():
    app.dependency_overrides[verify_token] = lambda: {"preferred_username": "testuser"}
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}


def test_get_no_token():
    response = client.get("/egress/1")
    assert response.status_code == 401


def test_put_no_token():
    response = client.put("/egress/1")
    assert response.status_code == 401


def test_protected_get_with_invalid_token():
    response = client.get("/egress/1", headers={"Authorization": "Bearer sometoken"})
    assert response.status_code == 401

def test_egress_get_with_invalid_jwt(authed_client):
    dct = {
        "projectId": "1",
        "userId": 1,
        "bucketId": "test-bucket"
    }
    key = secrets.token_hex(32)
    token = jwt.encode(dct, key)
    response = authed_client.get(f"/egress/{token}")
    assert response.status_code == 401

def test_egress_get_with_valid_jwt(authed_client):
    dct = {
        "projectId": "1",
        "userId": 1,
        "bucketId": "test-bucket"
    }

    token = jwt.encode(dct, settings.secret_key)
    response = authed_client.get(f"/egress/{token}")
    assert response.status_code == 200