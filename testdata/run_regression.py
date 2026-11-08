"""Run the backend suite against a disposable, seeded SQLite database."""

import os
import sys
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parent.parent
with tempfile.TemporaryDirectory(prefix="zamp-regression-", ignore_cleanup_errors=True) as tmp:
    sandbox = Path(tmp)
    os.chdir(sandbox)
    os.environ.update(
        DATABASE_URL=f"sqlite:///{(sandbox / 'regression.db').as_posix()}",
        STORAGE_LOCAL_DIR=str(sandbox / "uploads"),
        GEMINI_API_KEY="",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="1",
    )
    sys.path.insert(0, str(root / "backend"))
    from app.database import Base, engine
    from app.db.seed_demo import reset_and_seed_demo
    import pytest

    Base.metadata.create_all(engine)
    reset_and_seed_demo()
    targets = [str((root / target).resolve()) for target in sys.argv[1:]] or [str(root / "backend/tests")]
    result = pytest.main([*targets, "-q", "--disable-warnings"])
    engine.dispose()
    os.chdir(root)
    raise SystemExit(result)
