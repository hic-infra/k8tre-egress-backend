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
        x = response.json()
        return x
    
async def download_file(project_id: str, file_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.request(
            "GET",
            f"{settings.egress_app_url}{project_id}/files/{file_id}",
            auth=("admin", "admin"),
            json={"files_location": "s3://mybucket", "max_file_size": 1000, "destination": "/"}
        )
        x = response.content
        return response.content, response.headers.get("content-type", "application/octet-stream"), response.headers.get("content-disposition")