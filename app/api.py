import httpx
from pydantic import TypeAdapter
from app.exceptions import EgressServiceError
from app.schemas import FileItem
from app.settings import settings


async def get_files(project_id: str) -> list[FileItem]:
    async with httpx.AsyncClient() as client:
        response = await client.request(
            "GET",
            f"{settings.egress_app_url}{project_id}/files",
            auth=(settings.egress_username, settings.egress_password),
            json={"files_location": "s3://bucket1"},
        )
    return TypeAdapter(list[FileItem]).validate_json(response.content)


async def download_file(project_id: str, file_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.request(
            "GET",
            f"{settings.egress_app_url}{project_id}/files/{file_id}",
            auth=(settings.egress_username, settings.egress_password),
            json={
                "files_location": "s3://mybucket",
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
