from datetime import datetime, timezone
from fastapi import APIRouter, Response, status
from app.config import settings
from app.database import check_database_connection
from app.storage.local import get_storage_adapter
from app.schemas.health import HealthResponse, DatabaseHealth, StorageHealth

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Health Check",
    description="Check the operational status of the API, database connectivity, and object storage.",
)
def get_health(response: Response) -> HealthResponse:
    db_info = check_database_connection()
    storage_info = get_storage_adapter().health_check()

    is_healthy = db_info.get("status") == "connected" and storage_info.get("status") == "ready"
    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status="ok" if is_healthy else "degraded",
        app_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc).isoformat(),
        database=DatabaseHealth(
            status=db_info.get("status", "unknown"),
            dialect=db_info.get("dialect", "unknown"),
            latency_ms=db_info.get("latency_ms", 0.0),
            error=db_info.get("error"),
        ),
        storage=StorageHealth(
            backend=storage_info.get("backend", settings.STORAGE_BACKEND),
            status=storage_info.get("status", "unknown"),
            path_or_bucket=storage_info.get("path_or_bucket", ""),
        ),
    )
