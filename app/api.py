import asyncio

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import httpx
import jwt
from keycloak import KeycloakOpenID
from pydantic import TypeAdapter, ValidationError
from app.exceptions import EgressConnectionError, EgressServiceError
from app.schemas import FileAction, FileItem, TokenPayload
from app.settings import settings

keycloak_bearer_scheme = HTTPBearer() if not settings.disable_auth else lambda: None

keycloak_openid = KeycloakOpenID(
    server_url=settings.keycloak_url,
    client_id=settings.keycloak_client_id,
    realm_name=settings.keycloak_realm,
)


async def get_files(project_id: str, bucket_id: str) -> list[FileItem]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                "GET",
                f"{settings.egress_app_url}{project_id}/files",
                auth=(settings.egress_username, settings.egress_password),
                json={"files_location": f"s3://{bucket_id}"},
            )
            print(response.content)
            return TypeAdapter(list[FileItem]).validate_json(response.content)

    except httpx.HTTPError as e:
        raise EgressConnectionError(
            status_code=502, detail=f"Upstream Egress app unreachable: {e}"
        )
    except ValidationError as e:
        raise EgressServiceError(
            status_code=502, detail=f"Unexpected response from Egress app: {e}"
        )


async def download_file(project_id: str, bucket_id: str, file_id: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                "GET",
                f"{settings.egress_app_url}{project_id}/files/{file_id}",
                auth=(settings.egress_username, settings.egress_password),
                json={
                    "files_location": f"s3://{bucket_id}",
                    "max_file_size": 1000,
                    "destination": "/",
                },
            )
        return (
            response.content,
            response.headers.get("content-type", "application/octet-stream"),
            response.headers.get("content-disposition"),
        )
    except httpx.HTTPError as e:
        raise EgressConnectionError(
            status_code=502, detail=f"Upstream Egress app unreachable: {e}"
        )

async def set_file_status(project_id: str, user_id: str, file_id: str, action: FileAction, comment: str = "") -> bool:
    url = ""
    if action == FileAction.approve:
        url = f"{settings.egress_app_url}{project_id}/files/{file_id}/approve"
    elif action == FileAction.reject:
        url = f"{settings.egress_app_url}{project_id}/files/{file_id}/reject"

    try:    
        async with httpx.AsyncClient() as client:
            response = await client.request(
                "PUT",
                url,
                auth=(settings.egress_username, settings.egress_password),
                json={"user_id": user_id, "destination": "/", "comment" : comment},
            )

        print(response.text)
        if response.status_code == 204:
            return True
        else:
            raise EgressServiceError(status_code=502, detail=response.json())
    except httpx.HTTPError as e:
        raise EgressConnectionError(
            status_code=502, detail=f"Upstream Egress app unreachable: {e}"
        )


async def approve_file(project_id: str, user_id: str, file_id: str, comment: str = "") -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                "PUT",
                f"{settings.egress_app_url}{project_id}/files/{file_id}/approve",
                auth=(settings.egress_username, settings.egress_password),
                json={"user_id": user_id, "destination": "/", "comment" : comment},
            )

        print(response.text)
        if response.status_code == 204:
            return True
        else:
            raise EgressServiceError(status_code=502, detail=response.json())
    except httpx.HTTPError as e:
        raise EgressConnectionError(
            status_code=502, detail=f"Upstream Egress app unreachable: {e}"
        )


async def reject_file(project_id: str, user_id: str, file_id: str, comment: str = "") -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                "PUT",
                f"{settings.egress_app_url}{project_id}/files/{file_id}/reject",
                auth=(settings.egress_username, settings.egress_password),
                json={"user_id": user_id, "destination": "/", "comment" : comment},
            )
        print(response.text)

        if response.status_code == 204:
            return True
        else:
            raise EgressServiceError(status_code=502, detail=response.json())
    except httpx.HTTPError as e:
        raise EgressConnectionError(
            status_code=502, detail=f"Upstream Egress app unreachable: {e}"
        )


async def verify_keycloak_token(
    credentials: HTTPAuthorizationCredentials = Depends(keycloak_bearer_scheme),
) -> dict:
    if credentials is None and settings.disable_auth:
        return {"sub": "dev-user"}
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


def decode_token(token: str):
    try:
        raw = jwt.decode(token, settings.secret_key, algorithms="HS256")
        payload = TokenPayload.model_validate(raw)
        return payload
    except ValidationError:
        raise HTTPException(status_code=401, detail="Invalid token claims")
    except jwt.DecodeError as e:
        raise HTTPException(status_code=401, detail=str(e))
