import asyncio
from enum import Enum

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Response
import jwt
from pydantic import ValidationError
from app.api import approve_file, download_file, get_files, verify_token
from app.schemas import TokenPayload
from app.settings import Settings
from fastapi.middleware.cors import CORSMiddleware


class FileAction(str, Enum):
    approve = "approve"
    reject = "reject"


settings = Settings()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.fe_url],
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter(dependencies=[Depends(verify_token)])


@app.get("/")
def read_root():
    return {"Hello": "World"}


@router.get("/egress/{token}")
async def get_egress(token: str, claims=Depends(verify_token)):
    try:
        raw = jwt.decode(token, settings.secret_key, algorithms="HS256")
        payload = TokenPayload.model_validate(raw)
        return await get_files(payload.projectId, payload.bucketId)
    except ValidationError:
        raise HTTPException(status_code=401, detail="Invalid token claims")
    except jwt.DecodeError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/egress/{egress_id}/{file_id}")
async def get_file(egress_id: str, file_id: str):
    content, content_type, content_disposition = await download_file(egress_id, file_id)

    headers = {
        "Content-Disposition": content_disposition
        or f'attachment; filename="{file_id}"'
    }

    return Response(content=content, media_type=content_type, headers=headers)


@router.put("/egress/{egress_id}")
async def approve_files(egress_id: str, body: dict[str, FileAction]):
    approved_ids = [
        file_id for file_id, action in body.items() if action == FileAction.approve
    ]
    try:
        await asyncio.gather(*[approve_file(egress_id, fid) for fid in approved_ids])

        return {"message": "success"}
    except Exception as e:
        raise e


app.include_router(router)
