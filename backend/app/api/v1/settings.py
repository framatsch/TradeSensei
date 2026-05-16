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

"""Route handlers for user settings management endpoints."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_session_with_rls
from app.core.exceptions import PersonalAccessTokenNotFoundError
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.pat import PatGenerateRequest, PatGenerateResponse, PatRead
from app.services.pat_service import PersonalAccessTokenService

router = APIRouter(prefix="/settings", tags=["settings"])


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> PersonalAccessTokenService:
    return PersonalAccessTokenService(session)


def _get_forwarded_for(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if not forwarded_for:
        return None
    return forwarded_for.split(",")[0].strip()


@router.post(
    "/tokens",
    response_model=ResponseEnvelope[PatGenerateResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Generate Personal Access Token",
)
async def create_token(
    payload: PatGenerateRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PersonalAccessTokenService, Depends(_get_service)],
) -> ResponseEnvelope[PatGenerateResponse]:
    if payload.expires_at is not None and payload.expires_at <= datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="expires_at must be in the future.",
        )

    audit_context = service.build_audit_context(
        method=request.method,
        path=request.url.path,
        ip_address=request.client.host if request.client else None,
        forwarded_for=_get_forwarded_for(request),
        user_agent=request.headers.get("user-agent"),
    )
    token, plain_text = await service.create_token(
        user_id=current_user.id,
        user_email=current_user.email,
        name=payload.name,
        expires_at=payload.expires_at,
        audit_context=audit_context,
    )

    return ResponseEnvelope[PatGenerateResponse](
        data=PatGenerateResponse(
            id=token.id,
            name=token.name,
            created_at=token.created_at,
            expires_at=token.expires_at,
            is_revoked=token.is_revoked,
            last_used_at=token.last_used_at,
            token=plain_text,
        )
    )


@router.get(
    "/tokens",
    response_model=ResponseEnvelope[list[PatRead]],
    summary="List Personal Access Tokens",
)
async def list_tokens(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PersonalAccessTokenService, Depends(_get_service)],
) -> ResponseEnvelope[list[PatRead]]:
    tokens = await service.list_tokens(user_id=current_user.id)
    return ResponseEnvelope[list[PatRead]](data=[PatRead.model_validate(token) for token in tokens])


@router.delete(
    "/tokens/{token_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke Personal Access Token",
)
async def revoke_token(
    token_id: uuid.UUID,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PersonalAccessTokenService, Depends(_get_service)],
) -> None:
    audit_context = service.build_audit_context(
        method=request.method,
        path=request.url.path,
        ip_address=request.client.host if request.client else None,
        forwarded_for=_get_forwarded_for(request),
        user_agent=request.headers.get("user-agent"),
    )
    try:
        await service.revoke_token(
            user_id=current_user.id,
            user_email=current_user.email,
            token_id=token_id,
            audit_context=audit_context,
        )
    except PersonalAccessTokenNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
