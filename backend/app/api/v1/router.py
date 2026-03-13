"""Aggregated v1 API router.

Import and include all v1 sub-routers here so that ``main.py`` only
needs to mount a single router.
"""

from fastapi import APIRouter

from app.api.v1 import accounts, auth, imports, metrics, trades, users

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(accounts.router)
router.include_router(trades.router)
router.include_router(metrics.router)
router.include_router(imports.router)
