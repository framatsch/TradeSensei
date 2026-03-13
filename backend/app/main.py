"""FastAPI application factory.

Creates and configures the :class:`fastapi.FastAPI` instance, registers
middleware, mounts all API routers, and applies startup migrations.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.migrations import run_migrations_on_startup
from app.schemas.common import ResponseEnvelope


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Run startup tasks before serving requests.

    Yields:
        Control back to FastAPI after startup work completes.
    """
    await run_migrations_on_startup()
    yield


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application.

    Returns:
        A fully configured :class:`FastAPI` instance ready to be served.
    """
    application = FastAPI(
        title="Trading Journal API",
        description=(
            "REST API for the Trading Journal Platform — "
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

    # ── Health endpoint ───────────────────────────────────────────────────────
    @application.get("/health", tags=["health"], summary="Health check")
    async def health() -> ResponseEnvelope[dict[str, str]]:
        """Return a simple liveness probe response.

        Returns:
            A :class:`ResponseEnvelope` containing ``{"status": "ok"}``
            when the service is running.
        """
        return ResponseEnvelope[dict[str, str]](data={"status": "ok"})

    # ── API routers ───────────────────────────────────────────────────────────
    application.include_router(v1_router)

    return application


app: FastAPI = create_app()
