from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class DatabaseHealth(BaseModel):
    status: str = Field(..., description="Connection status: connected, error, etc.")
    dialect: str = Field(..., description="SQL dialect: postgresql, sqlite, etc.")
    latency_ms: float = Field(..., description="Query response time in milliseconds")
    error: Optional[str] = Field(None, description="Error message if status is error")


class StorageHealth(BaseModel):
    backend: str = Field(..., description="Storage backend type: local, supabase, etc.")
    status: str = Field(..., description="Storage status: ready, unavailable")
    path_or_bucket: str = Field(..., description="Base directory or bucket name")


class HealthResponse(BaseModel):
    status: str = Field("ok", description="Overall service status")
    app_name: str
    version: str
    environment: str
    timestamp: str
    database: DatabaseHealth
    storage: StorageHealth
