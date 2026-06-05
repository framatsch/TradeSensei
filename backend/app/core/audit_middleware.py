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

"""Audit logging middleware for authenticated API requests."""

from __future__ import annotations

import logging
import re
import traceback
from dataclasses import dataclass
from typing import Any

from fastapi import Request
from jose import JWTError, jwt
from sqlalchemy.exc import SQLAlchemyError
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import settings
from app.core.constants import TOKEN_ALGORITHM
from app.services.audit_service import AuditEventService, generate_request_id

_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_RESOURCE_PATTERN = re.compile(r"/api/v1/(?P<resource>[a-z_-]+)(?:/(?P<id>[^/]+))?")
_NESTED_RESOURCE_PATTERN = re.compile(r"/api/v1/(?P<parent_resource>[a-z_-]+)/(?P<parent_id>[^/]+)/(?P<resource>[a-z_-]+)(?:/(?P<id>[^/]+))?")
_PUBLIC_PATHS = {
    "/api/v1/auth/config",
    "/api/v1/auth/token",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/auth/logout",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
}
_ACTION_OVERRIDES: dict[tuple[str, str], str | tuple[str, str | None]] = {
    ("POST", "/api/v1/auth/token"): "auth.login",
    ("POST", "/api/v1/auth/logout"): "auth.logout",
    ("POST", "/api/v1/imports/upload"): "import.started",
    ("POST", "/api/v1/imports/flex"): "import.started",
    ("POST", "/api/v1/trades/merge"): "trade.merged",
    ("POST", "/api/v1/trades/bulk/delete"): "trade.deleted",
    ("POST", "/api/v1/trades/bulk/assign-tags"): "trade.updated",
    ("POST", "/api/v1/trades/bulk/assign-playbook"): "trade.updated",
    ("POST", "/api/v1/checkins/filters"): ("checkin_filter.created", "checkin_filter"),
    ("PUT", "/api/v1/checkins/filters/*"): ("checkin_filter.updated", "checkin_filter"),
    ("DELETE", "/api/v1/checkins/filters/*"): ("checkin_filter.deleted", "checkin_filter"),
}


@dataclass
class _AuditContext:
    user_id: str | None
    email: str | None
    ip_address: str | None
    forwarded_for: str | None
    user_agent: str | None
    request_id: str
    auth_error_reason: str | None
    token_present: bool


class AuditMiddleware:
    """Pure-ASGI middleware that emits audit logs for write operations.

    Implemented as a plain ASGI callable (not BaseHTTPMiddleware) so that
    it never buffers or races against streaming / SSE responses.  It wraps
    the *send* callable to capture the response status code from the
    ``http.response.start`` message without touching the body at all.
    """

    def __init__(self, app: ASGIApp) -> None:
        self._app = app
        self._service = AuditEventService()
        self._logger = logging.getLogger(__name__)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        request = Request(scope, receive)
        path = request.url.path

        # Pass health checks through without any wrapping.
        if path == "/health":
            await self._app(scope, receive, send)
            return

        context = await self._build_context(request)
        method = request.method.upper()
        should_log = method in _WRITE_METHODS or (method == "GET" and settings.log_level.upper() == "DEBUG")

        if not context.user_id and path == "/api/v1/auth/token" and should_log:
            self._log_auth_failure(context, request, reason="invalid_credentials")

        # Capture the response status code by wrapping send.
        status_code: int = 0

        async def send_wrapper(message: Any) -> None:
            nonlocal status_code
            if message.get("type") == "http.response.start":
                status_code = message.get("status", 0)
                # Capture user_id that PAT auth may have stored in request.state
                if hasattr(request.state, "user_id") and not context.user_id:
                    context.user_id = request.state.user_id
            await send(message)

        exc_to_raise: BaseException | None = None
        try:
            await self._app(scope, receive, send_wrapper)
        except Exception as exc:  # noqa: BLE001
            exc_to_raise = exc
            if hasattr(request.state, "user_id") and not context.user_id:
                context.user_id = request.state.user_id
            if should_log:
                self._log_exception(context, request, exc)

        # Capture user_id set by PAT auth after the app finishes.
        if hasattr(request.state, "user_id") and not context.user_id:
            context.user_id = request.state.user_id

        if should_log and status_code:
            if status_code == 401 and path not in _PUBLIC_PATHS:
                reason = context.auth_error_reason or "unauthorized"
                self._log_auth_failure(context, request, reason=reason)
            else:
                self._log_response_by_status(context, request, status_code)

        if exc_to_raise is not None:
            raise exc_to_raise

    async def _build_context(self, request: Request) -> _AuditContext:
        forwarded_for_header = request.headers.get("x-forwarded-for")
        forwarded_for = forwarded_for_header.split(",")[0].strip() if forwarded_for_header else None
        ip_address = request.client.host if request.client else None
        token = self._extract_bearer_token(request)
        user_id, email, error_reason = self._decode_token(token)
        if request.url.path == "/api/v1/auth/token":
            email = self._extract_login_identifier_from_scope(request)
        return _AuditContext(
            user_id=user_id,
            email=email,
            ip_address=ip_address,
            forwarded_for=forwarded_for,
            user_agent=request.headers.get("user-agent"),
            request_id=generate_request_id(),
            auth_error_reason=error_reason,
            token_present=bool(token),
        )

    @staticmethod
    def _extract_bearer_token(request: Request) -> str | None:
        auth_header = request.headers.get("authorization")
        if not auth_header:
            return None
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        return parts[1]

    def _decode_token(self, token: str | None) -> tuple[str | None, str | None, str | None]:
        if not token:
            return None, None, None
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[TOKEN_ALGORITHM],
            )
        except JWTError:
            return None, None, "invalid_token"
        user_id = payload.get("sub")
        email = payload.get("email") or payload.get("email_address")
        return (
            str(user_id) if user_id else None,
            str(email) if email else None,
            None,
        )

    @staticmethod
    def _extract_login_identifier_from_scope(request: Request) -> str | None:
        """Extract the login identifier from the query string without reading the body.

        Reading the request body in middleware before passing ``receive`` to the
        downstream app causes a deadlock in httpx's ASGI transport (used in tests):
        once all body chunks are consumed, the transport's ``receive`` callable
        waits for the response to finish before returning ``http.disconnect``, so
        any subsequent attempt by the route handler to read the body via the same
        ``receive`` callable blocks forever.

        As a safe alternative we extract the username from the URL query string when
        it is present (some clients send it there), and return ``None`` otherwise.
        The missing email hash on the early auth-failure log is an acceptable
        trade-off — the log still records path, method, status, and reason.
        """
        username = request.query_params.get("username")
        return username if username else None

    def _infer_action(self, request: Request) -> tuple[str, str | None, str | None, str | None, str | None]:
        # Infer actions for standard CRUD endpoints; overrides handle special routes.
        method = request.method.upper()
        path = request.url.path

        override = _ACTION_OVERRIDES.get((method, path))
        if override:
            if isinstance(override, tuple):
                return override[0], override[1], None, None, None
            return override, None, None, None, None
            
        for (o_method, o_path), override in _ACTION_OVERRIDES.items():
            if method == o_method and o_path.endswith("*") and path.startswith(o_path[:-1]):
                # For wildcard matches, extract the resource_id if possible
                resource_id = path[len(o_path) - 1 :] if len(path) > len(o_path) - 1 else None
                if isinstance(override, tuple):
                    return override[0], override[1], resource_id, None, None
                return override, "checkin_filter" if "checkin_filter" in override else None, resource_id, None, None

        route_metadata = self._extract_route_metadata(request)
        if route_metadata.get("action"):
            return (
                route_metadata["action"],
                route_metadata.get("resource_type"),
                route_metadata.get("resource_id"),
                route_metadata.get("parent_resource_type"),
                route_metadata.get("parent_resource_id"),
            )

        nested_match = _NESTED_RESOURCE_PATTERN.match(path)
        if nested_match:
            resource = nested_match.group("resource").rstrip("s")
            resource_id = nested_match.group("id")
            parent_resource = nested_match.group("parent_resource").rstrip("s")
            parent_id = nested_match.group("parent_id")
            if resource_id and resource_id in {
                "merge",
                "bulk",
                "upload",
                "fresh-start",
            }:
                resource_id = None
            action = self._infer_resource_action(method, resource, resource_id)
            return action, resource, resource_id, parent_resource, parent_id

        match = _RESOURCE_PATTERN.match(path)
        if not match:
            return f"{method.lower()}.unknown", None, None, None, None

        resource = match.group("resource").rstrip("s")
        resource_id = match.group("id")
        if resource_id and resource_id in {"merge", "bulk", "upload", "fresh-start"}:
            resource_id = None
        action = self._infer_resource_action(method, resource, resource_id)
        return action, resource, resource_id, None, None

    @staticmethod
    def _infer_resource_action(method: str, resource: str, resource_id: str | None) -> str:
        # Actions follow <resource>.<verb> naming convention.
        if method == "POST" and resource_id is None:
            return f"{resource}.created"
        if method in {"PUT", "PATCH"}:
            return f"{resource}.updated"
        if method == "DELETE":
            return f"{resource}.deleted"
        if method == "GET":
            verb = "list" if resource_id is None else "read"
            return f"{resource}.{verb}"
        return f"{resource}.{method.lower()}"

    @staticmethod
    def _extract_route_metadata(request: Request) -> dict[str, Any]:
        route = request.scope.get("route")
        if not route:
            return {}
        endpoint = getattr(route, "endpoint", None)
        metadata: dict[str, Any] = {}
        for source in (route, endpoint):
            if source is None:
                continue
            meta = getattr(source, "audit_metadata", None)
            if isinstance(meta, dict):
                metadata.update(meta)
        return metadata

    def _log_response_by_status(self, context: _AuditContext, request: Request, status_code: int) -> None:
        (
            action,
            resource_type,
            resource_id,
            parent_resource_type,
            parent_resource_id,
        ) = self._infer_action(request)
        if status_code >= 400:
            action = self._map_error_action(status_code, action)

        try:
            self._service.create_audit_event(
                action=action,
                user_id=context.user_id,
                email=context.email,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=context.ip_address,
                user_agent=context.user_agent,
                request_id=context.request_id,
                status_code=status_code,
                method=request.method,
                path=request.url.path,
                forwarded_for=context.forwarded_for,
                parent_resource_type=parent_resource_type,
                parent_resource_id=parent_resource_id,
                metadata=None,
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.error("Audit logging failed: %s", exc)

    def _log_auth_failure(
        self,
        context: _AuditContext,
        request: Request,
        reason: str,
    ) -> None:
        try:
            self._service.create_audit_event(
                action="auth.failed",
                user_id=None,
                email=context.email,
                resource_type="auth",
                resource_id=None,
                ip_address=context.ip_address,
                user_agent=context.user_agent,
                request_id=context.request_id,
                status_code=401,
                method=request.method,
                path=request.url.path,
                forwarded_for=context.forwarded_for,
                metadata={"reason": reason},
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.error("Audit logging failed: %s", exc)

    def _log_exception(
        self,
        context: _AuditContext,
        request: Request,
        exc: Exception,
    ) -> None:
        # Map exception types to audit error categories without breaking responses.
        error_action = "error.unhandled"
        if isinstance(exc, SQLAlchemyError):
            error_action = "error.database"
        try:
            self._service.create_audit_event(
                action=error_action,
                user_id=context.user_id,
                email=context.email,
                resource_type=None,
                resource_id=None,
                ip_address=context.ip_address,
                user_agent=context.user_agent,
                request_id=context.request_id,
                status_code=500,
                method=request.method,
                path=request.url.path,
                forwarded_for=context.forwarded_for,
                metadata={
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                    "stack_trace": traceback.format_exc(),
                },
            )
        except Exception as log_exc:  # noqa: BLE001
            self._logger.error("Audit logging failed: %s", log_exc)

    @staticmethod
    def _map_error_action(status_code: int, default_action: str) -> str:
        if status_code == 404:
            return "error.not_found"
        if status_code == 403:
            return "error.forbidden"
        if status_code == 422:
            return "error.validation"
        if status_code >= 500:
            return "error.internal"
        return default_action
