from fastapi.testclient import TestClient
import pytest

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


def test_protected_get_with_valid_token(authed_client):
    response = authed_client.get("/egress/1")
    assert response.status_code == 200

def test_egress_get_with_jwt(authed_client):
    response = authed_client.get("/egress/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwcm9qZWN0SWQiOjEsInVzZXJJZCI6MSwiYnVja2V0SWQiOiJ0ZXN0LWJ1Y2tldCJ9.yj_Jbei6L5z9sh_ANEM9-AgI61ggEckOQGFmYPqPjNo")
    assert response.status_code == 200
