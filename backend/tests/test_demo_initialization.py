"""Startup seeding must never erase an evaluator's work."""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base
from app.models.application import Application
from app.models.document import DocumentVersion
from app.models.organization import Organization
from app.storage.local import get_storage_adapter


def test_initialization_seeds_only_empty_database_and_preserves_later_work(tmp_path):
    from app.db.initialize import initialize_demo_if_empty

    engine = create_engine(f"sqlite:///{(tmp_path / 'fresh.db').as_posix()}")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            assert initialize_demo_if_empty(db) is True
            first = db.scalar(select(Application).where(Application.reference_number == "APP-2026-CLEAN-001"))
            document = db.scalar(select(DocumentVersion).limit(1))
            assert first is not None
            assert document is not None
            assert get_storage_adapter().file_exists(document.storage_key)

            first.decision_notes = "Evaluator added this note"
            db.commit()
            original_id = first.id
            original_document_id = document.id

            assert initialize_demo_if_empty(db) is False
            assert initialize_demo_if_empty(db) is False
            db.expire_all()
            saved = db.scalar(select(Application).where(Application.reference_number == "APP-2026-CLEAN-001"))
            assert saved.id == original_id
            assert saved.decision_notes == "Evaluator added this note"
            assert db.get(DocumentVersion, original_document_id) is not None
            assert get_storage_adapter().file_exists(document.storage_key)
            assert db.query(Organization).count() == 2
    finally:
        engine.dispose()


def test_initialization_refuses_partially_seeded_database(tmp_path):
    from app.db.initialize import initialize_demo_if_empty

    engine = create_engine(f"sqlite:///{(tmp_path / 'partial.db').as_posix()}")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            db.add(
                Organization(
                    id="partial-org",
                    name="Partial buyer",
                    slug="partial-buyer",
                    is_active=True,
                    policy_version="1",
                    settings="{}",
                )
            )
            db.commit()
            try:
                initialize_demo_if_empty(db)
            except RuntimeError as exc:
                assert "incomplete" in str(exc).lower()
            else:
                raise AssertionError("Partial seed was silently accepted")
            assert db.query(Organization).count() == 1
    finally:
        engine.dispose()
