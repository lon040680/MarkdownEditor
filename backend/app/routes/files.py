import base64
import os

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse as DiskFileResponse

from ..schemas.file_schema import FileWriteRequest, FileResponse, ImageSaveRequest

router = APIRouter()


def validate_path(file_path: str) -> str:
    """Validate and normalize file path. Only allow absolute paths to .md files."""
    normalized = os.path.normpath(file_path)
    if not os.path.isabs(normalized):
        raise HTTPException(status_code=400, detail="Absolute path required")
    if not normalized.lower().endswith(".md"):
        raise HTTPException(status_code=400, detail="Only .md files are supported")
    return normalized


@router.get("/file", response_model=FileResponse)
async def read_file(path: str = Query(..., description="Absolute path to .md file")):
    normalized = validate_path(path)
    if not os.path.exists(normalized):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        with open(normalized, "r", encoding="utf-8") as f:
            content = f.read()
        return FileResponse(
            path=normalized,
            content=content,
            filename=os.path.basename(normalized),
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/file")
async def write_file(req: FileWriteRequest):
    normalized = validate_path(req.path)
    try:
        dir_path = os.path.dirname(normalized)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        with open(normalized, "w", encoding="utf-8") as f:
            f.write(req.content)
        return {"status": "ok", "path": normalized}
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health():
    return {"status": "ok"}


_ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg"}


@router.get("/image")
async def get_image(path: str = Query(..., description="Absolute path to image file")):
    normalized = os.path.normpath(path)
    if not os.path.isabs(normalized):
        raise HTTPException(status_code=400, detail="Absolute path required")
    ext = os.path.splitext(normalized)[1].lower()
    if ext not in _ALLOWED_IMAGE_EXTS:
        raise HTTPException(status_code=400, detail="Not a supported image file")
    if not os.path.exists(normalized):
        raise HTTPException(status_code=404, detail="File not found")
    return DiskFileResponse(normalized)


@router.post("/file/image")
async def save_image(req: ImageSaveRequest):
    # Validate directory
    norm_dir = os.path.normpath(req.directory)
    if not os.path.isabs(norm_dir):
        raise HTTPException(status_code=400, detail="Absolute directory path required")

    # Validate filename: strip directory components, allow only image extensions
    safe_name = os.path.basename(req.filename)
    ext = os.path.splitext(safe_name)[1].lower()
    if ext not in _ALLOWED_IMAGE_EXTS:
        raise HTTPException(status_code=400, detail="Not a supported image extension")
    if not safe_name:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Make filename unique if it already exists
    dest = os.path.join(norm_dir, safe_name)
    if os.path.exists(dest):
        base, suffix = os.path.splitext(safe_name)
        counter = 1
        while os.path.exists(dest):
            safe_name = f"{base}_{counter}{suffix}"
            dest = os.path.join(norm_dir, safe_name)
            counter += 1

    try:
        os.makedirs(norm_dir, exist_ok=True)
        img_bytes = base64.b64decode(req.data)
        with open(dest, "wb") as f:
            f.write(img_bytes)
        return {"status": "ok", "path": dest, "filename": safe_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
