"""FastAPI application factory.

Creates and configures the :class:`fastapi.FastAPI` instance, registers
middleware, mounts all API routers, and applies startup migrations.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1.router import router as v1_router
from app.core.audit_middleware import AuditMiddleware
from app.core.config import settings
from app.core.logging import configure_uvicorn_logging
from app.core.migrations import run_migrations_on_startup
from app.schemas.common import ResponseEnvelope


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Run startup tasks before serving requests.

    Yields:
        Control back to FastAPI after startup work completes.
    """
    # Configure logging filters (suppress /health access logs)
    configure_uvicorn_logging()

    await run_migrations_on_startup()
    application.state.market_data_http_client = httpx.AsyncClient(
        timeout=15.0,
        follow_redirects=True,
    )
    try:
        yield
    finally:
        await application.state.market_data_http_client.aclose()


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application.

    Returns:
        A fully configured :class:`FastAPI` instance ready to be served.
    """
    application = FastAPI(
        title="Trade Sensei API",
        description=(
            "REST API for the Trade Sensei Platform — "
            "trade recording, performance metrics, and analysis."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Sessions (Required for OAuth state) ────────────────────────────────────
    application.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie="tradesensei_session",
        max_age=3600,  # 1 hour is plenty for OAuth flows
        same_site="lax",
    )

    # ── Audit logging ───────────────────────────────────────────────────────
    application.add_middleware(AuditMiddleware)

    # ── Health endpoint ───────────────────────────────────────────────────────
    @application.get("/health", tags=["health"], summary="Health check")
    async def health() -> ResponseEnvelope[dict[str, str]]:
        """Return a simple liveness probe response.

        Returns:
            A :class:`ResponseEnvelope` containing ``{"status": "ok"}``
            when the service is running.
        """
        return ResponseEnvelope[dict[str, str]](data={"status": "ok"})

    # ── Static file uploads ───────────────────────────────────────────────────
    uploads_path = Path(settings.upload_dir)
    uploads_path.mkdir(parents=True, exist_ok=True)
    application.mount(
        "/uploads", StaticFiles(directory=str(uploads_path)), name="uploads"
    )

    # ── API routers ───────────────────────────────────────────────────────────
    application.include_router(v1_router)

    return application


app: FastAPI = create_app()
