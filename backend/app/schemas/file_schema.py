from pydantic import BaseModel
from typing import Optional


class FileWriteRequest(BaseModel):
    path: str
    content: str


class FileResponse(BaseModel):
    path: str
    content: str
    filename: str


class ImageSaveRequest(BaseModel):
    directory: str  # absolute path to directory
    filename: str   # image filename (basename only)
    data: str       # base64 encoded image data
