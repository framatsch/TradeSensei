"""Aggregated v1 API router.

Import and include all v1 sub-routers here so that ``main.py`` only
needs to mount a single router.
"""

from fastapi import APIRouter

from app.api.v1 import trades

router = APIRouter(prefix="/api/v1")

router.include_router(trades.router)
