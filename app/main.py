import asyncio
from fastapi import APIRouter, Depends, FastAPI, Response
from app.api import (
    approve_file,
    decode_token,
    download_file,
    get_files,
    verify_keycloak_token,
)
from app.schemas import FileAction
from app.settings import settings
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.fe_url],
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter(dependencies=[Depends(verify_keycloak_token)])


@app.get("/")
def read_root():
    return {"Hello": "World"}


@router.get("/egress/{token}")
async def get_egress(token: str):
    payload = decode_token(token)
    return await get_files(payload.projectId, payload.bucketId)


@router.get("/egress/{token}/{file_id}")
async def get_file(token: str, file_id: str):
    payload = decode_token(token)
    content, content_type, content_disposition = await download_file(
        payload.projectId, payload.bucketId, file_id
    )

    headers = {
        "Content-Disposition": content_disposition
        or f'attachment; filename="{file_id}"'
    }

    return Response(content=content, media_type=content_type, headers=headers)


@router.put("/egress/{token}")
async def approve_files(token: str, body: dict[str, FileAction]):
    payload = decode_token(token)
    approved_ids = [
        file_id for file_id, action in body.items() if action == FileAction.approve
    ]
    try:
        await asyncio.gather(
            *[approve_file(payload.projectId, fid) for fid in approved_ids]
        )

        return {"message": "success"}
    except Exception as e:
        raise e


app.include_router(router)
