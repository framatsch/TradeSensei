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

"""Route handlers for the ``/api/v1/users`` resource.

Provides the current-user profile endpoints (read, update, delete).
All endpoints require a valid Bearer token.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_session_with_rls
from app.core.exceptions import UserAlreadyExistsError, UserNotFoundError
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.user import UserRead, UserSettingsRead, UserSettingsUpdate, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> UserService:
    """FastAPI dependency that constructs a :class:`UserService`.

    Args:
        session: Injected async database session.

    Returns:
        A :class:`UserService` bound to the current session.
    """
    return UserService(session)


@router.get(
    "/me",
    response_model=ResponseEnvelope[UserRead],
    summary="Get Current User Profile",
    description=("Return the profile of the currently authenticated user. Requires a valid ``Authorization: Bearer <token>`` header."),
    response_description=("The authenticated user's profile wrapped in a response envelope."),
    responses={
        200: {"description": "User profile returned successfully."},
        401: {"description": "Missing or invalid Bearer token."},
    },
)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> ResponseEnvelope[UserRead]:
    """Return the profile of the currently authenticated user.

    Reads the user ORM instance injected by the ``get_current_user``
    dependency and serialises it into a :class:`UserRead` DTO.

    Args:
        current_user: Injected authenticated user ORM instance.

    Returns:
        A :class:`ResponseEnvelope` containing the :class:`UserRead` DTO
        for the calling user.
    """
    return ResponseEnvelope[UserRead](data=UserRead.model_validate(current_user))


@router.patch(
    "/me",
    response_model=ResponseEnvelope[UserRead],
    summary="Update Current User Profile",
    description=(
        "Apply a partial update to the currently authenticated user's profile. "
        "Only fields present in the request body are modified; omitted fields "
        "retain their current values. "
        "Both ``username`` and ``email`` must remain unique across all users."
    ),
    response_description="The updated user profile wrapped in a response envelope.",
    responses={
        200: {"description": "Profile updated successfully."},
        401: {"description": "Missing or invalid Bearer token."},
        409: {"description": "The requested username or email is already taken."},
        422: {"description": "Request payload failed schema validation."},
    },
)
async def update_me(
    payload: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UserService, Depends(_get_service)],
) -> ResponseEnvelope[UserRead]:
    """Partially update the current user's profile.

    Only the fields present in the request body are written. Fields that are
    absent (or explicitly set to ``None``) are left unchanged.

    Args:
        payload: Partial update data (``username`` and/or ``email``).
        current_user: Injected authenticated user ORM instance.
        service: Injected user service.

    Returns:
        A :class:`ResponseEnvelope` containing the updated
        :class:`UserRead` DTO reflecting all applied changes.

    Raises:
        HTTPException: 409 if the username or email is already in use.
    """
    try:
        updated = await service.update_user(current_user, payload)
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email address is already in use.",
        ) from exc
    return ResponseEnvelope[UserRead](data=updated)


@router.get(
    "/me/settings",
    response_model=ResponseEnvelope[UserSettingsRead],
    summary="Get User Settings",
    description=("Return the UI preferences of the currently authenticated user. Missing keys are returned with their default values."),
    response_description="The user's settings wrapped in a response envelope.",
    responses={
        200: {"description": "Settings returned successfully."},
        401: {"description": "Missing or invalid Bearer token."},
    },
)
async def get_settings(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UserService, Depends(_get_service)],
) -> ResponseEnvelope[UserSettingsRead]:
    """Return the UI settings for the currently authenticated user.

    Args:
        current_user: Injected authenticated user ORM instance.
        service: Injected user service.

    Returns:
        A :class:`ResponseEnvelope` containing the :class:`UserSettingsRead`
        DTO with all settings keys populated (defaults for missing keys).
    """
    result = await service.get_settings(current_user.id)
    return ResponseEnvelope[UserSettingsRead](data=result)


@router.put(
    "/me/settings",
    response_model=ResponseEnvelope[UserSettingsRead],
    summary="Update User Settings",
    description=("Partially update the UI preferences of the currently authenticated user. Only fields present in the request body are modified."),
    response_description="The updated settings wrapped in a response envelope.",
    responses={
        200: {"description": "Settings updated successfully."},
        401: {"description": "Missing or invalid Bearer token."},
        422: {"description": "Request payload failed schema validation."},
    },
)
async def update_settings(
    payload: UserSettingsUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UserService, Depends(_get_service)],
) -> ResponseEnvelope[UserSettingsRead]:
    """Update UI settings for the currently authenticated user.

    Args:
        payload: Partial settings update (``theme`` and/or ``default_date_range``).
        current_user: Injected authenticated user ORM instance.
        service: Injected user service.

    Returns:
        A :class:`ResponseEnvelope` containing the full updated
        :class:`UserSettingsRead` DTO.
    """
    result = await service.update_settings(current_user.id, payload)
    return ResponseEnvelope[UserSettingsRead](data=result)


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Current User Account",
    description=(
        "Permanently delete the currently authenticated user's account and all "
        "associated data (trading accounts, trades). "
        "**This operation is irreversible.** "
        "After deletion, any existing access or refresh tokens for this user "
        "will be rejected by the API."
    ),
    response_description=("No content — the account and all associated data have been deleted."),
    responses={
        204: {"description": "User account and all associated data deleted."},
        401: {"description": "Missing or invalid Bearer token."},
    },
)
async def delete_me(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UserService, Depends(_get_service)],
) -> None:
    """Delete the current user's account and all owned data.

    Cascades the deletion to all trading accounts and trades that belong
    to this user. The operation commits atomically — either all data is
    removed or none is.

    Args:
        current_user: Injected authenticated user ORM instance.
        service: Injected user service.

    Raises:
        HTTPException: 404 if the user is not found.
    """
    try:
        await service.delete_user(current_user)
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        ) from exc
