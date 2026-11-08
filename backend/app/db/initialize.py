"""Non-destructive setup for a new synthetic demonstration database."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.db.seed_demo import reset_and_seed_demo
from app.models.application import Application
from app.models.organization import Organization


DEMO_REFERENCES = {
    "APP-2026-CLEAN-001",
    "APP-2026-MISM-002",
    "APP-2026-WARN-003",
}


def initialize_demo_if_empty(db: Session) -> bool:
    """Seed a migrated database once; never replace existing organisations or cases."""
    if db.scalar(select(Organization.id).limit(1)) is not None:
        existing = set(
            db.scalars(
                select(Application.reference_number).where(
                    Application.reference_number.in_(DEMO_REFERENCES)
                )
            )
        )
        if existing != DEMO_REFERENCES:
            raise RuntimeError("Incomplete demo database; startup will not erase or replace existing data")
        return False
    reset_and_seed_demo(db)
    return True


if __name__ == "__main__":
    with SessionLocal() as session:
        seeded = initialize_demo_if_empty(session)
    print("Seeded a new synthetic demo." if seeded else "Existing demo data preserved.")
