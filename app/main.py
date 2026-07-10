import asyncio
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from app.api import (
    approve_file,
    decode_token,
    download_file,
    get_audit_trail,
    get_files,
    reject_file,
    set_file_status,
    verify_keycloak_token,
)
from app.exceptions import EgressConnectionError, EgressServiceError
from app.schemas import AuditAction, AuditLog, FileAction, FileApproval
from app.settings import settings
from fastapi.middleware.cors import CORSMiddleware
import logging
import collections

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.fe_url],
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter(dependencies=[Depends(verify_keycloak_token)])
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/health")
def health():
    return {"status": "ok"}


@router.get("/egress/{token}")
async def get_egress(token: str):
    try:
        payload = decode_token(token)
        files = await get_files(payload.projectId, payload.bucketId)
        audit = await get_audit_trail(payload.projectId)

        # Match the files to the audit logs
        audit_by_file_id: dict[str, list[AuditLog]] = collections.defaultdict(list)
        for entry in audit:
            audit_by_file_id[entry.file_id].append(entry)

        lst = []
        for file in files:
            x = dict(file)
            entries = audit_by_file_id.get(file.id, [])
            # We're only interested in approvals or rejections to figure out the current state
            entries = list(filter(
                lambda x: x.action == AuditAction.approve or x.action == AuditAction.reject,
                entries,
            ))            
            user_ids = set([x.user_id for x in entries])
            latest_audit_entry = dict()
            # We want the latest one associated with each user_id
            for u in user_ids:
                latest_audit_entry[u] = max(
                    filter(lambda x: x.user_id == u, entries), key=lambda e: e.datetime, default=None
                )
            logger.info(latest_audit_entry)

            # We need to put rejects into the approvals array with the comment
            for k,v in latest_audit_entry.items():
                if v.action == AuditAction.reject:
                    x["approvals"].append(
                        {
                            "comment": v.comment,
                            "action": "reject",
                            "user_id": v.user_id
                        }
                    )

            lst.append(x)


        logger.info(x)
        return files
    except EgressServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


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
    except EgressServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.put("/egress/{token}")
async def approve_reject_files(token: str, body: dict[str, FileApproval]):
    payload = decode_token(token)
    print(body.items())
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
        raise HTTPException(status_code=e.status_code, detail=e.detail)


app.include_router(router)
