from typing import Optional
from pydantic import BaseModel

class FileItem(BaseModel):
    approvals: Optional[list[dict]]
    file_name: str
    id: str
    size: int