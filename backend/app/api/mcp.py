"""MCP transport endpoints secured by personal access tokens."""

import asyncio
import json
import re
from collections.abc import AsyncGenerator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from app.core.deps import get_current_user_from_pat
from app.models.user import User

router = APIRouter(prefix="/mcp", tags=["mcp"])

_KEEPALIVE_INTERVAL = 15


def _sse_event_stream(
    request: Request,
    session_id: str | None,
    user_id: str,
) -> StreamingResponse:
    if session_id and not re.match(r"^[A-Za-z0-9_-]{1,64}$", session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session_id format.",
        )

    base = {
        "message_endpoint": "/mcp/messages",
        "user_id": user_id,
    }
    if session_id:
        base["message_endpoint"] = f"/mcp/messages?session_id={session_id}"
        base["session_id"] = session_id

    init_payload = json.dumps(base)

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }

    async def event_generator() -> AsyncGenerator[str, None]:
        yield f"event: ready\ndata: {init_payload}\n\n"

        # In test environments with ASGITransport, disconnects can cause deadlocks.
        if request.headers.get("x-test-no-sse-keepalive") == "true":
            return

        while not await request.is_disconnected():
            # Check for disconnect frequently to avoid hanging in tests
            for _ in range(int(max(1, _KEEPALIVE_INTERVAL * 2))):
                if await request.is_disconnected():
                    return
                await asyncio.sleep(0.5)
            yield ": keepalive\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=headers,
    )


@router.get(
    "/sse",
    summary="Initialize MCP SSE transport",
    responses={401: {"description": "Missing or invalid PAT."}},
)
async def mcp_sse(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user_from_pat)],
    session_id: str | None = Query(default=None, description="MCP session identifier"),
) -> StreamingResponse:
    return _sse_event_stream(
        request=request,
        session_id=session_id,
        user_id=str(current_user.id),
    )


@router.post(
    "/messages",
    summary="Process MCP JSON-RPC message",
    responses={401: {"description": "Missing or invalid PAT."}},
)
async def mcp_messages(
    payload: dict[str, Any],
    current_user: Annotated[User, Depends(get_current_user_from_pat)],
    session_id: str | None = Query(default=None, description="MCP session identifier"),
) -> dict[str, Any]:
    if session_id and not re.match(r"^[A-Za-z0-9_-]{1,64}$", session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session_id format.",
        )

    if payload.get("jsonrpc") != "2.0":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="jsonrpc must be '2.0'.",
        )

    message_id = payload.get("id")
    method = payload.get("method")
    if not isinstance(method, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="method is required.",
        )

    if method == "initialize":
        result: dict[str, Any] = {
            "server": {"name": "Trade Sensei MCP", "version": "1.0"},
            "capabilities": {"tools": {}, "prompts": {}, "resources": {}},
        }
        return {"jsonrpc": "2.0", "id": message_id, "result": result}

    if method == "ping":
        return {
            "jsonrpc": "2.0",
            "id": message_id,
            "result": {"pong": True, "user_id": str(current_user.id)},
        }

    return {
        "jsonrpc": "2.0",
        "id": message_id,
        "error": {"code": -32601, "message": f"Unknown method: {method}"},
    }
