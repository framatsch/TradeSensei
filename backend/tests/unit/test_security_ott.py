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

"""Unit tests for one-time OAuth exchange token functions in app/core/security.py.

Tests :func:`~app.core.security.create_one_time_token` and
:func:`~app.core.security.consume_one_time_token` using a mocked database session.
The DB-backed blocklist is exercised via ``consume_ott_jti``, which is mocked or
called against a real session in integration tests.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from jose import jwt
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.constants import ONE_TIME_TOKEN_EXPIRE_SECONDS, TOKEN_ALGORITHM
from app.core.exceptions import InvalidTokenError
from app.core.security import consume_one_time_token, create_one_time_token

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_session(consume_returns: bool = True) -> AsyncMock:
    """Return a mock AsyncSession whose consume_ott_jti path behaves as specified.

    Args:
        consume_returns: When True, the first consume_ott_jti call returns True
            (token fresh). When False, simulates IntegrityError (duplicate).

    Returns:
        A mock AsyncSession suitable for injection into consume_one_time_token.
    """
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    if not consume_returns:
        session.flush.side_effect = IntegrityError("duplicate", {}, Exception())
    return session


def _decode_raw(token: str) -> dict[str, Any]:
    """Decode a JWT without consuming it via the OTT logic.

    Args:
        token: A signed JWT string.

    Returns:
        The raw decoded payload dictionary.
    """
    raw: dict[str, Any] = jwt.decode(
        token, settings.secret_key, algorithms=[TOKEN_ALGORITHM]
    )
    return raw


# ---------------------------------------------------------------------------
# create_one_time_token
# ---------------------------------------------------------------------------


class TestCreateOneTimeToken:
    """Unit tests for :func:`app.core.security.create_one_time_token`."""

    @pytest.mark.unit
    def test_create_one_time_token_returns_non_empty_string(self) -> None:
        """create_one_time_token() must return a non-empty string."""
        user_id = uuid.uuid4()
        token = create_one_time_token(user_id)
        assert isinstance(token, str) and len(token) > 0

    @pytest.mark.unit
    def test_create_one_time_token_embeds_ott_claim_true(self) -> None:
        """create_one_time_token() must embed ``ott=True`` in the payload."""
        user_id = uuid.uuid4()
        token = create_one_time_token(user_id)
        payload = _decode_raw(token)
        assert payload.get("ott") is True

    @pytest.mark.unit
    def test_create_one_time_token_embeds_jti_claim(self) -> None:
        """create_one_time_token() must embed a ``jti`` UUID string."""
        user_id = uuid.uuid4()
        token = create_one_time_token(user_id)
        payload = _decode_raw(token)
        jti = payload.get("jti")
        assert isinstance(jti, str) and len(jti) > 0
        uuid.UUID(jti)  # raises ValueError if malformed

    @pytest.mark.unit
    def test_create_one_time_token_embeds_correct_sub(self) -> None:
        """create_one_time_token() must embed the caller's user UUID as ``sub``."""
        user_id = uuid.uuid4()
        token = create_one_time_token(user_id)
        payload = _decode_raw(token)
        assert payload["sub"] == str(user_id)

    @pytest.mark.unit
    def test_create_one_time_token_has_exp_claim(self) -> None:
        """create_one_time_token() must embed an ``exp`` (expiry) claim."""
        user_id = uuid.uuid4()
        token = create_one_time_token(user_id)
        payload = _decode_raw(token)
        assert "exp" in payload

    @pytest.mark.unit
    def test_create_one_time_token_expiry_within_expected_window(self) -> None:
        """The OTT expiry must be within ~ONE_TIME_TOKEN_EXPIRE_SECONDS of now."""
        user_id = uuid.uuid4()
        token = create_one_time_token(user_id)
        payload = _decode_raw(token)

        exp_ts: int = int(payload["exp"])
        expected_exp = datetime.now(UTC) + timedelta(
            seconds=ONE_TIME_TOKEN_EXPIRE_SECONDS
        )
        tolerance = timedelta(seconds=5)

        assert abs(datetime.fromtimestamp(exp_ts, tz=UTC) - expected_exp) < tolerance

    @pytest.mark.unit
    def test_create_one_time_token_each_call_produces_unique_jti(self) -> None:
        """Two separate calls must produce tokens with distinct ``jti`` values."""
        user_id = uuid.uuid4()
        token_a = create_one_time_token(user_id)
        token_b = create_one_time_token(user_id)
        jti_a = _decode_raw(token_a)["jti"]
        jti_b = _decode_raw(token_b)["jti"]
        assert jti_a != jti_b


# ---------------------------------------------------------------------------
# consume_one_time_token — happy path (mocked DB)
# ---------------------------------------------------------------------------


class TestConsumeOneTimeToken:
    """Unit tests for :func:`app.core.security.consume_one_time_token`."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_consume_one_time_token_returns_correct_user_uuid(self) -> None:
        """consume_one_time_token() must return the UUID embedded in the token."""
        user_id = uuid.uuid4()
        token = create_one_time_token(user_id)
        session = _make_mock_session(consume_returns=True)
        result = await consume_one_time_token(token, session)
        assert result == user_id

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_consume_one_time_token_returns_uuid_type(self) -> None:
        """consume_one_time_token() must return a :class:`uuid.UUID` instance."""
        user_id = uuid.uuid4()
        token = create_one_time_token(user_id)
        session = _make_mock_session(consume_returns=True)
        result = await consume_one_time_token(token, session)
        assert isinstance(result, uuid.UUID)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_consume_one_time_token_second_use_raises_invalid_token_error(
        self,
    ) -> None:
        """A previously consumed OTT (IntegrityError) must raise InvalidTokenError."""
        user_id = uuid.uuid4()
        token = create_one_time_token(user_id)
        # First call succeeds, second simulates duplicate (IntegrityError path)
        session_ok = _make_mock_session(consume_returns=True)
        session_dup = _make_mock_session(consume_returns=False)

        await consume_one_time_token(token, session_ok)
        with pytest.raises(InvalidTokenError):
            await consume_one_time_token(token, session_dup)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_consume_different_tokens_for_same_user_both_succeed(self) -> None:
        """Two different OTTs for the same user must each succeed once."""
        user_id = uuid.uuid4()
        token_a = create_one_time_token(user_id)
        token_b = create_one_time_token(user_id)

        session_a = _make_mock_session(consume_returns=True)
        session_b = _make_mock_session(consume_returns=True)

        result_a = await consume_one_time_token(token_a, session_a)
        result_b = await consume_one_time_token(token_b, session_b)

        assert result_a == user_id
        assert result_b == user_id

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_consume_one_time_token_expired_raises_invalid_token_error(
        self,
    ) -> None:
        """An OTT whose ``exp`` is in the past must raise InvalidTokenError."""
        user_id = uuid.uuid4()
        jti = str(uuid.uuid4())
        expired_payload: dict[str, Any] = {
            "sub": str(user_id),
            "jti": jti,
            "ott": True,
            "iat": datetime.now(UTC) - timedelta(seconds=120),
            "exp": datetime.now(UTC) - timedelta(seconds=1),
        }
        expired_token = jwt.encode(
            expired_payload, settings.secret_key, algorithm=TOKEN_ALGORITHM
        )
        session = _make_mock_session()
        with pytest.raises(InvalidTokenError):
            await consume_one_time_token(expired_token, session)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_consume_one_time_token_garbage_string_raises_invalid_token_error(
        self,
    ) -> None:
        """A completely invalid string must raise InvalidTokenError."""
        session = _make_mock_session()
        with pytest.raises(InvalidTokenError):
            await consume_one_time_token("not.a.real.jwt.at.all", session)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_consume_one_time_token_wrong_secret_raises_invalid_token_error(
        self,
    ) -> None:
        """A token signed with a different secret must raise InvalidTokenError."""
        user_id = uuid.uuid4()
        forged_payload: dict[str, Any] = {
            "sub": str(user_id),
            "jti": str(uuid.uuid4()),
            "ott": True,
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(seconds=60),
        }
        forged_token = jwt.encode(
            forged_payload,
            "attacker-controlled-secret-key-32chars!!",
            algorithm=TOKEN_ALGORITHM,
        )
        session = _make_mock_session()
        with pytest.raises(InvalidTokenError):
            await consume_one_time_token(forged_token, session)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_consume_one_time_token_missing_ott_claim_raises_invalid_token_error(
        self,
    ) -> None:
        """A valid JWT that lacks the ``ott=True`` claim must be rejected."""
        user_id = uuid.uuid4()
        payload: dict[str, Any] = {
            "sub": str(user_id),
            "jti": str(uuid.uuid4()),
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(seconds=60),
        }
        token_without_ott = jwt.encode(
            payload, settings.secret_key, algorithm=TOKEN_ALGORITHM
        )
        session = _make_mock_session()
        with pytest.raises(InvalidTokenError):
            await consume_one_time_token(token_without_ott, session)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_consume_one_time_token_missing_jti_claim_raises_invalid_token_error(
        self,
    ) -> None:
        """A JWT with ``ott=True`` but no ``jti`` must be rejected."""
        user_id = uuid.uuid4()
        payload: dict[str, Any] = {
            "sub": str(user_id),
            "ott": True,
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(seconds=60),
        }
        token_without_jti = jwt.encode(
            payload, settings.secret_key, algorithm=TOKEN_ALGORITHM
        )
        session = _make_mock_session()
        with pytest.raises(InvalidTokenError):
            await consume_one_time_token(token_without_jti, session)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_consume_one_time_token_ott_false_raises_invalid_token_error(
        self,
    ) -> None:
        """A JWT with ``ott=False`` must be rejected."""
        user_id = uuid.uuid4()
        payload: dict[str, Any] = {
            "sub": str(user_id),
            "jti": str(uuid.uuid4()),
            "ott": False,
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(seconds=60),
        }
        token_ott_false = jwt.encode(
            payload, settings.secret_key, algorithm=TOKEN_ALGORITHM
        )
        session = _make_mock_session()
        with pytest.raises(InvalidTokenError):
            await consume_one_time_token(token_ott_false, session)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_consume_one_time_token_access_token_rejected(
        self,
    ) -> None:
        """A regular access token must not be accepted by consume_one_time_token()."""
        from app.core.security import create_access_token

        user_id = uuid.uuid4()
        access_token = create_access_token(user_id)
        session = _make_mock_session()
        with pytest.raises(InvalidTokenError):
            await consume_one_time_token(access_token, session)
