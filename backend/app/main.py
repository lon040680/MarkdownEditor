import os
import sys

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.routes.files import router as files_router
from app.routes.export import router as export_router


def create_app() -> FastAPI:
    application = FastAPI(title="Markdown Editor API")

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(files_router, prefix="/api")
    application.include_router(export_router, prefix="/api")

    # Determine static files directory
    if getattr(sys, "frozen", False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    static_dir = os.path.join(base_dir, "static")
    if os.path.exists(static_dir):
        application.mount(
            "/", StaticFiles(directory=static_dir, html=True), name="static"
        )

    return application


app = create_app()
