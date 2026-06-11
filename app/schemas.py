from enum import Enum
from typing import Optional
from pydantic import BaseModel


class FileItem(BaseModel):
    approvals: Optional[list[dict]]
    file_name: str
    id: str
    size: int


class TokenPayload(BaseModel):
    projectId: str
    userId: int
    bucketId: str


class FileAction(str, Enum):
    approve = "approve"
    reject = "reject"
