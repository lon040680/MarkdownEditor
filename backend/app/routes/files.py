import os

from fastapi import APIRouter, HTTPException, Query

from ..schemas.file_schema import FileWriteRequest, FileResponse

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
