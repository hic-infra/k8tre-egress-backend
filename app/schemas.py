from enum import Enum
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class ApprovalStructure(BaseModel):
    comment: str
    destination: str
    user_id: str


class FileItem(BaseModel):
    approvals: Optional[list[ApprovalStructure]]
    file_name: str
    id: str
    size: int


class UCLBEResponse(BaseModel):
    message: str


class TokenPayload(BaseModel):
    projectId: str
    userId: str
    bucketId: str


class FileAction(str, Enum):
    approve = "approve"
    reject = "reject"

class AuditAction(str, Enum):
    approve = "Approval"
    reject = "Rejection"
    download = "Download"


class FileApproval(BaseModel):
    comment: str
    status: FileAction


class AuditLog(BaseModel):
    action: AuditAction
    comment: str
    datetime: datetime
    destination: str
    file_id: str
    user_id: str