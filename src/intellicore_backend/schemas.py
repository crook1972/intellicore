from typing import Optional

from pydantic import BaseModel


class ScanRequest(BaseModel):
    target_ip: Optional[str] = None
