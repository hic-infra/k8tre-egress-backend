from typing import Any


class EgressServiceError(Exception):
    def __init__(self, status_code: int, detail: dict[str, Any]):
        self.status_code = status_code
        self.detail = detail
