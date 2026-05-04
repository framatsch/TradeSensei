"""Dedicated FastAPI entrypoint for MCP endpoints.

This module creates a minimal FastAPI application that includes only the
MCP router (`app.api.mcp`). It is intended to be run on a separate port
(e.g., 8001) to provide network isolation from the main REST API.
"""

from fastapi import FastAPI

from app.api.mcp import router as mcp_router


def create_app() -> FastAPI:
    """Create a FastAPI app exposing only the MCP router.

    Returns:
        FastAPI: Configured FastAPI instance.
    """
    application = FastAPI(
        title="Trade Sensei MCP API",
        description="MCP endpoints isolated on a dedicated port.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    application.include_router(mcp_router)
    return application


app: FastAPI = create_app()
