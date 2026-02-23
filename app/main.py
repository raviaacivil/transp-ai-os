"""FastAPI application entry point."""

from fastapi import FastAPI

from app import __version__
from app.api import health

app = FastAPI(
    title="Transportation AI OS",
    description="Transportation Engineering AI SaaS Platform",
    version=__version__,
)

app.include_router(health.router, tags=["health"])
