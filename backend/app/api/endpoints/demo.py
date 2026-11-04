from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.db.seed_demo import reset_and_seed_demo

router = APIRouter()


@router.post(
    "/reset",
    summary="Reset Demo Environment",
    description="Deterministically cleans and re-seeds the demo database with 3 standard test cases (Clean, Mismatch, Verification Issue), demo accounts, and synthetic documents.",
)
def api_reset_demo(db: Session = Depends(get_db)):
    try:
        result = reset_and_seed_demo(db)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Demo reset failed: {str(e)}",
        )
