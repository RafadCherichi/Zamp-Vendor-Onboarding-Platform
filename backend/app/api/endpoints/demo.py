import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.config import settings
from app.core.deps import require_roles
from app.database import get_db
from app.db.seed_demo import reset_and_seed_demo
from app.models.role import RoleEnum

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/reset",
    summary="Reset Demo Environment",
    description="Deterministically cleans and re-seeds the demo database with 3 standard test cases (Clean, Mismatch, Verification Issue), demo accounts, and synthetic documents.",
)
def api_reset_demo(
    db: Session = Depends(get_db),
    _admin=Depends(require_roles([RoleEnum.ADMIN])),
):
    if settings.ENVIRONMENT.lower() == "production":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    try:
        result = reset_and_seed_demo(db)
        return result
    except Exception:
        logger.exception("Demo reset failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Demo reset failed.",
        )
