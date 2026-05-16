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

"""Audit event service for structured JSON logging."""

from __future__ import annotations

import hashlib
import json
import logging
import sys
import uuid
from datetime import UTC, datetime
from typing import Any

_SENSITIVE_KEYS = {
    "pnl",
    "net_pnl",
    "realized_pnl",
    "unrealized_pnl",
    "pnl_pct",
    "profit",
    "commission",
    "commissions",
    "price",
    "prices",
    "quantity",
    "qty",
    "strategy",
    "notes",
    "playbook",
    "playbook_name",
    "tag",
    "tag_name",
    "password",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "api_secret",
}


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_email(email: str | None) -> str | None:
    if not email:
        return None
    normalized = _normalize_email(email)
    return hashlib.sha256(normalized.encode()).hexdigest()


def format_timestamp(value: datetime | None = None) -> str:
    timestamp = value or datetime.now(UTC)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    timestamp = timestamp.astimezone(UTC)
    return timestamp.isoformat(timespec="microseconds").replace("+00:00", "Z")


def generate_request_id() -> str:
    return str(uuid.uuid4())


def _filter_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        filtered: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in _SENSITIVE_KEYS:
                continue
            filtered[key] = _filter_sensitive(item)
        return filtered
    if isinstance(value, list):
        return [_filter_sensitive(item) for item in value]
    return value


class AuditEventService:
    """Service for emitting structured audit events to stdout."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("audit")
        self._configure_logger()

    def _configure_logger(self) -> None:
        if self._logger.handlers:
            return
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        self._logger.addHandler(handler)
        self._logger.propagate = False
        self._logger.setLevel(logging.INFO)

    def create_audit_event(
        self,
        *,
        action: str,
        user_id: str | uuid.UUID | None,
        email: str | None,
        resource_type: str | None,
        resource_id: str | int | uuid.UUID | None,
        ip_address: str | None,
        user_agent: str | None,
        request_id: str,
        status_code: int | None,
        method: str,
        path: str,
        parent_resource_id: str | int | uuid.UUID | None = None,
        parent_resource_type: str | None = None,
        metadata: dict[str, Any] | None = None,
        forwarded_for: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "timestamp": format_timestamp(),
            "level": "INFO",
            "logger": "audit",
            "action": action,
            "user_id": str(user_id) if user_id is not None else None,
            "email_hash": hash_email(email),
            "resource_type": resource_type,
            "resource_id": str(resource_id) if resource_id is not None else None,
            "ip_address": ip_address,
            "forwarded_for": forwarded_for,
            "user_agent": user_agent,
            "request_id": request_id,
            "status_code": status_code,
            "method": method,
            "path": path,
        }

        if parent_resource_id is not None:
            payload["parent_resource_id"] = str(parent_resource_id)
        if parent_resource_type is not None:
            payload["parent_resource_type"] = parent_resource_type
        if metadata:
            payload["metadata"] = _filter_sensitive(metadata)

        message = json.dumps(payload, separators=(",", ":"), default=str)
        self._logger.info(message)
        return payload
