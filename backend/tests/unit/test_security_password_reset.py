"""Unit tests for password-reset token functions in app/core/security.py.

Tests :func:`~app.core.security.create_password_reset_token` and
:func:`~app.core.security.consume_password_reset_token` using a mocked
database session.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from jose import jwt
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.constants import PASSWORD_RESET_TOKEN_EXPIRE_SECONDS, TOKEN_ALGORITHM
from app.core.exceptions import InvalidTokenError
from app.core.security import consume_password_reset_token, create_password_reset_token

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_session(consume_returns: bool = True) -> AsyncMock:
    """Return a mock AsyncSession configured for consume_ott_jti behaviour.

    Args:
        consume_returns: When True the flush succeeds (fresh token).
            When False flush raises IntegrityError (already used).

    Returns:
        A mock AsyncSession suitable for injection.
    """
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    if not consume_returns:
        session.flush.side_effect = IntegrityError("duplicate", {}, None)
        session.rollback = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# create_password_reset_token
# ---------------------------------------------------------------------------


class TestCreatePasswordResetToken:
    """Tests for :func:`create_password_reset_token`."""

    def test_returns_string(self) -> None:
        token = create_password_reset_token(uuid.uuid4())
        assert isinstance(token, str)

    def test_contains_pwreset_claim(self) -> None:
        token = create_password_reset_token(uuid.uuid4())
        payload: dict[str, Any] = jwt.decode(
            token, settings.secret_key, algorithms=[TOKEN_ALGORITHM]
        )
        assert payload.get("pwreset") is True

    def test_contains_unique_jti(self) -> None:
        user_id = uuid.uuid4()
        token1 = create_password_reset_token(user_id)
        token2 = create_password_reset_token(user_id)
        p1: dict[str, Any] = jwt.decode(
            token1, settings.secret_key, algorithms=[TOKEN_ALGORITHM]
        )
        p2: dict[str, Any] = jwt.decode(
            token2, settings.secret_key, algorithms=[TOKEN_ALGORITHM]
        )
        assert p1["jti"] != p2["jti"]

    def test_embeds_correct_user_id(self) -> None:
        user_id = uuid.uuid4()
        token = create_password_reset_token(user_id)
        payload: dict[str, Any] = jwt.decode(
            token, settings.secret_key, algorithms=[TOKEN_ALGORITHM]
        )
        assert payload["sub"] == str(user_id)

    def test_expires_in_one_hour(self) -> None:
        token = create_password_reset_token(uuid.uuid4())
        payload: dict[str, Any] = jwt.decode(
            token, settings.secret_key, algorithms=[TOKEN_ALGORITHM]
        )
        now = datetime.now(UTC).timestamp()
        assert (
            PASSWORD_RESET_TOKEN_EXPIRE_SECONDS - 5
            <= payload["exp"] - now
            <= PASSWORD_RESET_TOKEN_EXPIRE_SECONDS + 5
        )


# ---------------------------------------------------------------------------
# consume_password_reset_token
# ---------------------------------------------------------------------------


class TestConsumePasswordResetToken:
    """Tests for :func:`consume_password_reset_token`."""

    @pytest.mark.asyncio
    async def test_valid_token_returns_user_id(self) -> None:
        user_id = uuid.uuid4()
        token = create_password_reset_token(user_id)
        session = _make_mock_session(consume_returns=True)
        result = await consume_password_reset_token(token, session)
        assert result == user_id

    @pytest.mark.asyncio
    async def test_rejects_ott_token(self) -> None:
        from app.core.security import create_one_time_token

        ott = create_one_time_token(uuid.uuid4())
        session = _make_mock_session()
        with pytest.raises(InvalidTokenError, match="Not a password-reset token"):
            await consume_password_reset_token(ott, session)

    @pytest.mark.asyncio
    async def test_rejects_replayed_token(self) -> None:
        user_id = uuid.uuid4()
        token = create_password_reset_token(user_id)
        session = _make_mock_session(consume_returns=False)
        with pytest.raises(InvalidTokenError, match="already used"):
            await consume_password_reset_token(token, session)

    @pytest.mark.asyncio
    async def test_rejects_expired_token(self) -> None:
        user_id = uuid.uuid4()
        import uuid as _uuid

        jti = str(_uuid.uuid4())
        expired_payload: dict[str, Any] = {
            "sub": str(user_id),
            "iat": datetime.now(UTC) - timedelta(hours=2),
            "exp": datetime.now(UTC) - timedelta(hours=1),
            "jti": jti,
            "pwreset": True,
        }
        expired_token: str = jwt.encode(
            expired_payload, settings.secret_key, algorithm=TOKEN_ALGORITHM
        )
        session = _make_mock_session()
        with pytest.raises(InvalidTokenError):
            await consume_password_reset_token(expired_token, session)

    @pytest.mark.asyncio
    async def test_rejects_tampered_token(self) -> None:
        token = create_password_reset_token(uuid.uuid4())
        tampered = token[:-4] + "XXXX"
        session = _make_mock_session()
        with pytest.raises(InvalidTokenError):
            await consume_password_reset_token(tampered, session)
