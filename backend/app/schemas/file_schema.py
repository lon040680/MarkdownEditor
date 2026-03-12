from pydantic import BaseModel
from typing import Optional


class FileWriteRequest(BaseModel):
    path: str
    content: str


class FileResponse(BaseModel):
    path: str
    content: str
    filename: str
