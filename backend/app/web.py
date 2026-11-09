"""Serve the compiled React app alongside the API on one origin."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles


def register_frontend(app: FastAPI, directory: Path) -> None:
    build_dir = directory.resolve()
    index_path = build_dir / "index.html"
    if not index_path.is_file():
        raise ValueError(f"Frontend build is missing: {index_path}")

    assets_dir = build_dir / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="frontend-assets")

    @app.middleware("http")
    async def frontend_path(request: Request, call_next):
        path = request.url.path.lstrip("/")
        if request.method != "GET" or path == "api" or path.startswith(("api/", "assets/")):
            return await call_next(request)
        if path in {"docs", "redoc"} or path.startswith(("docs/", "redoc/")):
            return await call_next(request)

        requested_file = (build_dir / path).resolve() if path else index_path
        if requested_file.is_relative_to(build_dir) and requested_file.is_file():
            return FileResponse(requested_file)
        if "." in Path(path).name:
            return PlainTextResponse("Not Found", status_code=404)
        return FileResponse(index_path)
