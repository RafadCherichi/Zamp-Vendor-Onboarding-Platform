"""A fresh hosted database must match the models used by the app."""

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect

from app.models import Base


def test_fresh_alembic_database_has_every_model_column(tmp_path):
    root = Path(__file__).resolve().parents[2]
    database_url = f"sqlite:///{(tmp_path / 'migrated.db').as_posix()}"
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    environment["PYTHONPATH"] = str(root / "backend")
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(root / "backend/alembic.ini"), "upgrade", "head"],
        cwd=root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        for table in Base.metadata.sorted_tables:
            assert inspector.has_table(table.name), table.name
            actual = {column["name"] for column in inspector.get_columns(table.name)}
            missing = set(table.columns.keys()) - actual
            assert not missing, f"{table.name} missing {sorted(missing)}"
    finally:
        engine.dispose()
