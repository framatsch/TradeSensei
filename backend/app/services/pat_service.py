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

"""Service layer for personal access token management."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PersonalAccessTokenNotFoundError
from app.core.security import generate_pat, hash_pat
from app.models.pat import PersonalAccessToken
from app.repositories.pat_repository import PersonalAccessTokenRepository
from app.services.audit_service import AuditEventService, generate_request_id


@dataclass
class AuditContext:
    """Request metadata used for manual audit events."""

    method: str
    path: str
    ip_address: str | None
    forwarded_for: str | None
    user_agent: str | None
    request_id: str


class PersonalAccessTokenService:
    """Business logic for personal access token CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = PersonalAccessTokenRepository(session)
        self._audit = AuditEventService()

    async def create_token(
        self,
        *,
        user_id: uuid.UUID,
        user_email: str | None,
        name: str,
        expires_at: datetime | None,
        audit_context: AuditContext,
    ) -> tuple[PersonalAccessToken, str]:
        plain_token = generate_pat()
        token = await self._repo.create(
            user_id=user_id,
            name=name,
            token_hash=hash_pat(plain_token),
            expires_at=expires_at,
        )
        self._emit_audit_event(
            action="pat.created",
            user_id=user_id,
            user_email=user_email,
            token_id=token.id,
            audit_context=audit_context,
        )
        return token, plain_token

    async def list_tokens(self, *, user_id: uuid.UUID) -> list[PersonalAccessToken]:
        return await self._repo.list_for_user(user_id)

    async def revoke_token(
        self,
        *,
        user_id: uuid.UUID,
        user_email: str | None,
        token_id: uuid.UUID,
        audit_context: AuditContext,
    ) -> PersonalAccessToken:
        token = await self._repo.get_by_id_for_user(token_id, user_id)
        if token is None:
            raise PersonalAccessTokenNotFoundError("Token not found.")

        revoked = await self._repo.revoke(token)
        self._emit_audit_event(
            action="pat.revoked",
            user_id=user_id,
            user_email=user_email,
            token_id=revoked.id,
            audit_context=audit_context,
        )
        return revoked

    @staticmethod
    def build_audit_context(
        *,
        method: str,
        path: str,
        ip_address: str | None,
        forwarded_for: str | None,
        user_agent: str | None,
    ) -> AuditContext:
        return AuditContext(
            method=method,
            path=path,
            ip_address=ip_address,
            forwarded_for=forwarded_for,
            user_agent=user_agent,
            request_id=generate_request_id(),
        )

    def _emit_audit_event(
        self,
        *,
        action: str,
        user_id: uuid.UUID,
        user_email: str | None,
        token_id: uuid.UUID,
        audit_context: AuditContext,
    ) -> None:
        self._audit.create_audit_event(
            action=action,
            user_id=user_id,
            email=user_email,
            resource_type="pat",
            resource_id=token_id,
            ip_address=audit_context.ip_address,
            user_agent=audit_context.user_agent,
            request_id=audit_context.request_id,
            status_code=200,
            method=audit_context.method,
            path=audit_context.path,
            forwarded_for=audit_context.forwarded_for,
            metadata={
                "token_id": str(token_id),
                "recorded_at": datetime.now(UTC).isoformat(),
            },
        )
