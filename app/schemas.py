from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class UCLBEApprovalStructure(BaseModel):
    comment: str
    destination: str
    user_id: str


class UCLBEFileItem(BaseModel):
    approvals: Optional[list[UCLBEApprovalStructure]]
    file_name: str
    id: str
    size: int


class UCLBEResponse(BaseModel):
    message: str


class TokenPayload(BaseModel):
    projectId: str
    userId: str
    bucketId: str
    version: str


class FileAction(str, Enum):
    approve = "approve"
    reject = "reject"


class AuditAction(str, Enum):
    approve = "Approval"
    reject = "Rejection"
    download = "Download"


class ApprovalEntry(BaseModel):
    comment: str
    action: FileAction
    user_id: str


class FileItemWithAudit(UCLBEFileItem):
    approvals: list[ApprovalEntry] = []


class FileApproval(BaseModel):
    comment: str = Field(min_length=1)
    status: FileAction


class AuditLog(BaseModel):
    action: AuditAction
    comment: str
    datetime: datetime
    destination: str
    file_id: str
    user_id: str
