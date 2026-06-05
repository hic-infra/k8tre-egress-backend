import asyncio

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import httpx
from keycloak import KeycloakOpenID
from pydantic import TypeAdapter
from app.exceptions import EgressServiceError
from app.schemas import FileItem
from app.settings import settings

keycloak_bearer_scheme = HTTPBearer()
keycloak_openid = KeycloakOpenID(
    server_url=f"{settings.keycloak_url}/",
    client_id=settings.keycloak_client_id,
    realm_name=settings.keycloak_realm,
)


async def get_files(project_id: str) -> list[FileItem]:
    async with httpx.AsyncClient() as client:
        response = await client.request(
            "GET",
            f"{settings.egress_app_url}{project_id}/files",
            auth=(settings.egress_username, settings.egress_password),
            json={"files_location": "s3://test-bucket"},
        )
    return TypeAdapter(list[FileItem]).validate_json(response.content)


async def download_file(project_id: str, file_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.request(
            "GET",
            f"{settings.egress_app_url}{project_id}/files/{file_id}",
            auth=(settings.egress_username, settings.egress_password),
            json={
                "files_location": "s3://test-bucket",
                "max_file_size": 1000,
                "destination": "/",
            },
        )
    return (
        response.content,
        response.headers.get("content-type", "application/octet-stream"),
        response.headers.get("content-disposition"),
    )


async def approve_file(project_id: str, file_id: str) -> bool:
    async with httpx.AsyncClient() as client:
        response = await client.request(
            "PUT",
            f"{settings.egress_app_url}{project_id}/files/{file_id}/approve",
            auth=(settings.egress_username, settings.egress_password),
            json={"user_id": "1", "destination": "/"},
        )
    if response.status_code == 204:
        return True
    else:
        raise EgressServiceError(response.status_code, response.json())


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(keycloak_bearer_scheme),
) -> dict:
    token = credentials.credentials
    try:
        options = {"verify_signature": True, "verify_aud": False, "verify_exp": True}
        payload = await asyncio.to_thread(keycloak_openid.decode_token, token, options)
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
