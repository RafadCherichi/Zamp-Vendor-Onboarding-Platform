from fastapi import APIRouter
from app.api.endpoints import health, auth, invitations, applications, validation, exceptions, notifications

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(invitations.router, prefix="/invitations", tags=["Invitations"])
api_router.include_router(applications.router, prefix="/applications", tags=["Applications"])
api_router.include_router(validation.router, prefix="/applications", tags=["Validation"])
api_router.include_router(exceptions.router, prefix="/exceptions", tags=["Exceptions"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
