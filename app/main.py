import asyncio
from enum import Enum

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from keycloak import KeycloakOpenID
from pydantic import BaseModel
from app.api import approve_file, download_file, get_files, verify_token
from app.settings import Settings
from fastapi.middleware.cors import CORSMiddleware
import jwt

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


@router.get("/egress/{egress_id}")
async def get_egress(egress_id: str, claims = Depends(verify_token)):
    return await get_files(egress_id)


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
        await asyncio.gather(
            *[approve_file(egress_id, fid) for fid in approved_ids]
        )

        return {"message": "success"}
    except Exception as e:
        raise e
    
app.include_router(router)