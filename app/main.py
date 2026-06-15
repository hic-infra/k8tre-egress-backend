import asyncio
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Response
from app.api import (
    approve_file,
    decode_token,
    download_file,
    get_files,
    reject_file,
    set_file_status,
    verify_keycloak_token,
)
from app.exceptions import EgressConnectionError, EgressServiceError
from app.schemas import FileAction, FileApproval
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
    try:
        payload = decode_token(token)
        return await get_files(payload.projectId, payload.bucketId)
    except EgressConnectionError as e:
        raise HTTPException(status_code=502, detail=e.detail)
    except EgressServiceError as e:
        raise HTTPException(status_code=502, detail=e.detail)


@router.get("/egress/{token}/{file_id}")
async def get_file(token: str, file_id: str):
    try:
        payload = decode_token(token)
        content, content_type, content_disposition = await download_file(
            payload.projectId, payload.bucketId, file_id
        )

        headers = {
            "Content-Disposition": content_disposition
            or f'attachment; filename="{file_id}"'
        }

        return Response(content=content, media_type=content_type, headers=headers)
    except EgressConnectionError as e:
        raise HTTPException(status_code=502, detail=e.detail)


@router.put("/egress/{token}")
async def approve_reject_files(token: str, body: dict[str, FileApproval]):
    payload = decode_token(token)
    try:
        await asyncio.gather(
            *[
                set_file_status(
                    payload.projectId,
                    payload.userId,
                    fid,
                    params.status,
                    params.comment,
                )
                for fid, params in body.items()
            ]
        )

        return {"message": "success"}
    except EgressConnectionError as e:
        raise HTTPException(status_code=502, detail=e.detail)
    except EgressServiceError as e:
        raise HTTPException(status_code=502, detail=e.detail)


app.include_router(router)
