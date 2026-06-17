"""
These tests require the UCL backend to be setup and working
"""

from fastapi.testclient import TestClient
import jwt
import pytest

from app.settings import settings
from ..main import app
from app.api import verify_keycloak_token

client = TestClient(app)


@pytest.fixture
def authed_client():
    app.dependency_overrides[verify_keycloak_token] = lambda: {
        "preferred_username": "testuser"
    }
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.mark.integration
def test_egress_get_live(authed_client):
    project_id = "1"
    dct = {"projectId": project_id, "userId": "user1", "bucketId": "test-bucket"}
    token = jwt.encode(dct, settings.secret_key)
    response = authed_client.get(f"/egress/{token}")
    assert response.status_code == 200


@pytest.mark.integration
def test_egress_download_live(authed_client):
    project_id = "1"
    dct = {"projectId": project_id, "userId": "user1", "bucketId": "test-bucket"}
    token = jwt.encode(dct, settings.secret_key)
    response = authed_client.get(f"/egress/{token}")
    assert response.status_code == 200
    res = response.json()
    assert len(res) > 0
    file_id = res[0]["id"]

    # Approve file
    body = {file_id: "approve"}
    response = authed_client.put(f"/egress/{token}", json=body)
    assert response.status_code == 200

    response = authed_client.get(f"/egress/{token}/{file_id}")
    assert response.status_code == 200

    # Now reject it
    body = {file_id: "reject"}
    response = authed_client.put(f"/egress/{token}", json=body)
    assert response.status_code == 200

    # BE should stop us from downloading this
    response = authed_client.get(f"/egress/{token}/{file_id}")
    assert response.status_code == 502
