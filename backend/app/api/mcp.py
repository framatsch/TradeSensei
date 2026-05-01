"""MCP transport endpoints secured by personal access tokens."""

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.core.deps import get_current_user_from_pat
from app.models.user import User

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.get(
    "/sse",
    summary="Initialize MCP SSE transport",
    responses={401: {"description": "Missing or invalid PAT."}},
)
async def mcp_sse(
    current_user: Annotated[User, Depends(get_current_user_from_pat)],
) -> Response:
    payload = json.dumps(
        {
            "message_endpoint": "/mcp/messages",
            "user_id": str(current_user.id),
        }
    )
    body = f"event: ready\ndata: {payload}\n\n"
    return Response(
        content=body,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.post(
    "/messages",
    summary="Process MCP JSON-RPC message",
    responses={401: {"description": "Missing or invalid PAT."}},
)
async def mcp_messages(
    payload: dict[str, Any],
    current_user: Annotated[User, Depends(get_current_user_from_pat)],
) -> dict[str, Any]:
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
