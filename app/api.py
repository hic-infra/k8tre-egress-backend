import httpx
from app.settings import settings

async def get_files(project_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.request(
            "GET",
            f"{settings.egress_app_url}{project_id}/files",
            auth=("admin", "admin"),
            json={"files_location": "s3://mybucket"}
        )
        return response.json()
    
async def download_file(project_id: str, file_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.request(
            "GET",
            f"{settings.egress_app_url}{project_id}/files/{file_id}",
            auth=("admin", "admin"),
            json={"files_location": "s3://mybucket", "max_file_size": 1000, "destination": "/"}
        )
        return response.content, response.headers.get("content-type", "application/octet-stream"), response.headers.get("content-disposition")
    
async def approve_file(project_id: str, file_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.request(
            "PUT",
            f"{settings.egress_app_url}{project_id}/files/{file_id}/approve",
            auth=("admin", "admin"),
            json={"user_id": "1", "destination": "/"}
        )
        if response.status_code == 204:
            return {"message": "success"}
        else:
            return response.json()