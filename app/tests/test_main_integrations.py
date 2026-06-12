"""
These tests require the UCL backend to be setup and working
"""

import jwt
import pytest

from app import settings


@pytest.mark.integration
def test_egress_get_live(authed_client):
    project_id = "1"
    dct = {"projectId": project_id, "userId": 1, "bucketId": "test-bucket"}
    token = jwt.encode(dct, settings.secret_key)
    response = authed_client.get(f"/egress/{token}")
    assert response.status_code == 200


@pytest.mark.integration
def test_egress_put_live():
    pass
