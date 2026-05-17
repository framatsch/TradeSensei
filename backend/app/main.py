# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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

from app.api.mcp import router as mcp_router
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
    configure_uvicorn_logging(suppress_reloader=not settings.uvicorn_reloader_logs)

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
        description=("REST API for the Trade Sensei Platform — trade recording, performance metrics, and analysis."),
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
    application.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")

    # ── API routers ───────────────────────────────────────────────────────────
    application.include_router(v1_router)

    if settings.MCP_ENABLED:
        application.include_router(mcp_router)

    return application


app: FastAPI = create_app()
