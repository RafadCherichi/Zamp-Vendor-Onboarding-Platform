"""Serve a disposable, seeded preview of the built web app."""

import os
import socket
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

with tempfile.TemporaryDirectory(prefix="zamp-visible-preview-", ignore_cleanup_errors=True) as tmp:
    preview_dir = Path(tmp)
    os.chdir(preview_dir)
    os.environ.update(
        DATABASE_URL=f"sqlite:///{(preview_dir / 'preview.db').as_posix()}",
        STORAGE_LOCAL_DIR=str(preview_dir / "uploads"),
        GEMINI_API_KEY="",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="1",
    )
    sys.path.insert(0, str(ROOT / "backend"))

    from app.main import app
    from app.database import Base, engine
    from app.db.seed_demo import reset_and_seed_demo
    from fastapi.staticfiles import StaticFiles
    import uvicorn

    Base.metadata.create_all(engine)
    reset_and_seed_demo()
    app.mount("/assets", StaticFiles(directory=str(ROOT / "frontend/dist/assets")), name="assets")
    app.mount("/web", StaticFiles(directory=str(ROOT / "frontend/dist"), html=True), name="web")

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    print(f"PREVIEW_URL=http://127.0.0.1:{port}/web/", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
