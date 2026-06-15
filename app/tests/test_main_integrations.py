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
def test_egress_approve_live(authed_client):
    """
    Test we can approve a file and see said approvals and comments
    """
    project_id = "1"
    dct = {"projectId": project_id, "userId": "user1", "bucketId": "test-bucket"}
    token = jwt.encode(dct, settings.secret_key)
    response = authed_client.get(f"/egress/{token}")
    assert response.status_code == 200
    
    res = response.json()
    assert len(res) > 0
    file_id = res[0]["id"]
    body = {file_id: {"status": "approve", "comment": "example"}}
    response = authed_client.put(f"/egress/{token}", json=body)
    assert response.status_code == 200

    response = authed_client.get(f"/egress/{token}")
    assert response.status_code == 200
    res = response.json()
    assert len(res[0]["approvals"]) > 0
    # assert res["approvals"][0]["comment"] == "example"

    # Delete the approval
    body = {file_id: {"status": "reject", "comment": ""}}
    response = authed_client.put(f"/egress/{token}", json=body)
    assert response.status_code == 200
