from enum import Enum
from typing import Optional
from pydantic import BaseModel

class ApprovalStructure(BaseModel):
    comment: str
    destination: str
    user_id: str

class FileItem(BaseModel):
    approvals: Optional[list[ApprovalStructure]]
    file_name: str
    id: str
    size: int


class TokenPayload(BaseModel):
    projectId: str
    userId: str
    bucketId: str

class FileAction(str, Enum):
    approve = "approve"
    reject = "reject"

class FileApproval(BaseModel):
    comment: str
    status: FileAction