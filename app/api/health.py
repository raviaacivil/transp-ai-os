"""Health check endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.database import get_db

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str


class HealthDetailResponse(HealthResponse):
    """Detailed health check response with database status."""

    database: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check."""
    return HealthResponse(status="ok", version=__version__)


@router.get("/health/ready", response_model=HealthDetailResponse)
async def readiness_check(db: AsyncSession = Depends(get_db)) -> HealthDetailResponse:
    """Readiness check including database connectivity."""
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return HealthDetailResponse(
        status="ok" if db_status == "connected" else "degraded",
        version=__version__,
        database=db_status,
    )
