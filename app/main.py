import asyncio
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from app.api import (
    decode_token,
    download_file,
    get_audit_trail,
    get_files,
    set_file_status,
    verify_keycloak_token,
)
from app.exceptions import EgressConnectionError, EgressServiceError
from app.schemas import AuditAction, AuditLog, FileApproval, FileItemWithAudit
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


@router.get("/egress/{token}", response_model=list[FileItemWithAudit])
async def get_egress(token: str):
    try:
        payload = decode_token(token)
        files = await get_files(payload.projectId, payload.bucketId)
        audit = await get_audit_trail(payload.projectId)

        # We need to add in "approve" to any files in the approvals field
        for f in files:
            for app in f.approvals:
                pass

        # Now we handle any rejections
        # Match the files to the audit logs
        audit_by_file_id: dict[str, list[AuditLog]] = collections.defaultdict(list)
        for entry in audit:
            audit_by_file_id[entry.file_id].append(entry)

        lst = []
        for file in files:
            entries = audit_by_file_id.get(file.id, [])
            # We're only interested in approvals or rejections to figure out the current state
            entries = list(
                filter(
                    lambda x: x.action == AuditAction.approve
                    or x.action == AuditAction.reject,
                    entries,
                )
            )
            user_ids = set([x.user_id for x in entries])

            # We want the latest entry associated with each user_id
            latest_audit_entry = {
                u: max(
                    filter(lambda e: e.user_id == u, entries),
                    key=lambda e: e.datetime,
                    default=None,
                )
                for u in user_ids
            }

            approvals = [
                {
                    "comment": v.comment,
                    "action": (
                        "approve" if v.action == AuditAction.approve else "reject"
                    ),
                    "user_id": v.user_id,
                }
                for v in latest_audit_entry.values()
                if v is not None
            ]

            lst.append(file.model_copy(update={"approvals": approvals}))

        return lst
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
