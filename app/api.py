import asyncio

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import httpx
import jwt
from keycloak import KeycloakOpenID
from pydantic import TypeAdapter, ValidationError
from app.exceptions import EgressConnectionError, EgressServiceError
from app.schemas import AuditLog, FileAction, TokenPayload, UCLBEFileItem, UCLBEResponse
from app.settings import settings

keycloak_bearer_scheme = HTTPBearer() if not settings.disable_auth else lambda: None

keycloak_openid = KeycloakOpenID(
    server_url=settings.keycloak_url,
    client_id=settings.keycloak_client_id,
    realm_name=settings.keycloak_realm,
)


def _egress_url(project_id: str, suffix: str = "") -> str:
    return f"{settings.egress_app_url}{project_id}{suffix}"


async def _egress_request(method: str, url: str, **kwargs) -> httpx.Response:
    """Shared entrypoint for all upstream Egress app calls.

    Handles client creation, auth, and connection-level error wrapping so
    individual endpoint functions only need to deal with response parsing.
    """
    try:
        async with httpx.AsyncClient(
            auth=(settings.egress_username, settings.egress_password)
        ) as client:
            return await client.request(method, url, **kwargs)
    except httpx.HTTPError as e:
        raise EgressConnectionError(
            status_code=502, detail=f"Upstream Egress app unreachable: {e}"
        )


def _raise_service_error(response: httpx.Response) -> EgressServiceError:
    """Parse an unexpected/error response body from the Egress app."""
    try:
        info = TypeAdapter(UCLBEResponse).validate_json(response.content)
        detail = info.message
    except ValidationError:
        detail = response.text
    return EgressServiceError(status_code=502, detail=detail)


async def get_files(project_id: str, bucket_id: str) -> list[UCLBEFileItem]:
    response = await _egress_request(
        "GET",
        _egress_url(project_id, "/files"),
        json={"files_location": f"s3://{bucket_id}"},
    )
    try:
        return TypeAdapter(list[UCLBEFileItem]).validate_json(response.content)
    except ValidationError:
        raise _raise_service_error(response)


async def download_file(project_id: str, bucket_id: str, file_id: str):
    response = await _egress_request(
        "GET",
        _egress_url(project_id, f"/files/{file_id}"),
        json={
            "files_location": f"s3://{bucket_id}",
            "max_file_size": 10000000000,
            "destination": "/",
            "required_approvals": settings.required_approvals,
        },
    )
    content_type = response.headers.get("content-type", "")

    if content_type.startswith("application/json"):
        info = TypeAdapter(UCLBEResponse).validate_json(response.content)
        raise EgressServiceError(status_code=401, detail=info.message)

    return (
        response.content,
        content_type or "application/octet-stream",
        response.headers.get("content-disposition"),
    )


async def set_file_status(
    project_id: str, user_id: str, file_id: str, action: FileAction, comment: str = ""
) -> bool:
    if action not in (FileAction.approve, FileAction.reject):
        raise ValueError(f"Unsupported file action: {action}")

    endpoint = "approve" if action == FileAction.approve else "reject"
    response = await _egress_request(
        "PUT",
        _egress_url(project_id, f"/files/{file_id}/{endpoint}"),
        json={"user_id": user_id, "destination": "/", "comment": comment},
    )

    if response.status_code == 204:
        return True
    raise EgressServiceError(status_code=502, detail=response.json())


async def approve_file(
    project_id: str, user_id: str, file_id: str, comment: str = ""
) -> bool:
    return await set_file_status(
        project_id, user_id, file_id, FileAction.approve, comment
    )


async def reject_file(
    project_id: str, user_id: str, file_id: str, comment: str = ""
) -> bool:
    return await set_file_status(
        project_id, user_id, file_id, FileAction.reject, comment
    )

async def get_audit_trail(project_id: str):
    response = await _egress_request(
        "GET",
        _egress_url(project_id, f"/events"))
    
    try:
        return TypeAdapter(list[AuditLog]).validate_json(response.content)
    except ValidationError:
        raise _raise_service_error(response)


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
    except jwt.DecodeError:
        raise HTTPException(status_code=404, detail="Egress does not exist")
