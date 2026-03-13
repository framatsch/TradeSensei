"""Unit tests for app/core/security.py — no database access required.

Covers password hashing, password verification, JWT creation, and JWT
decoding including the expired-token and garbage-input error paths.
All tests are self-contained and rely only on the ``SECRET_KEY`` env var
seeded by ``conftest.py``.

Note on passlib/bcrypt compatibility: ``passlib 1.7.4`` is incompatible with
``bcrypt 5+`` under Python 3.14.  The ``_fix_passlib_bcrypt_backend`` fixture
patches the internal ``_finalize_backend_mixin`` so that passlib can load its
bcrypt backend without triggering the 72-byte wrap-bug detection failure.
This fixture is applied automatically (``autouse=True``) to every test in this
module and does **not** affect the correctness of the tested functions.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import patch

import pytest
from jose import jwt

from app.core.constants import TOKEN_ALGORITHM
from app.core.exceptions import InvalidTokenError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


@pytest.fixture(autouse=True)
def _fix_passlib_bcrypt_backend() -> Any:
    """Patch passlib's bcrypt backend initialisation for Python 3.14 compatibility.

    ``passlib 1.7.4`` generates a 256-byte internal test vector to detect a
    bcrypt wrap-bug, but ``bcrypt 5.0`` enforces the 72-byte limit strictly,
    raising ``ValueError`` during the backend selection that passlib performs
    on its first hash/verify call.  This patch bypasses the detection so that
    ``hash_password`` and ``verify_password`` can exercise their real logic.

    Yields:
        Nothing — the patch is active for the duration of each test.
    """
    with patch(
        "passlib.handlers.bcrypt._BcryptCommon._finalize_backend_mixin",
        return_value=True,
    ):
        yield


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------


class TestHashPassword:
    """Tests for :func:`hash_password`."""

    @pytest.mark.unit
    def test_hash_password_differs_from_plain(self) -> None:
        """The returned hash must not equal the original plain-text password.

        bcrypt always produces a string starting with ``$2b$``; storing the
        raw password would be a critical security bug.
        """
        plain = "SuperSecret99!"
        hashed = hash_password(plain)
        assert hashed != plain

    @pytest.mark.unit
    def test_hash_password_returns_bcrypt_string(self) -> None:
        """The returned value should be a recognisable bcrypt hash string.

        Bcrypt hashes always start with ``$2`` (covers ``$2a$``, ``$2b$``,
        ``$2y$`` variants), confirming the correct algorithm was used.
        """
        hashed = hash_password("any-password")
        assert hashed.startswith("$2")


class TestVerifyPassword:
    """Tests for :func:`verify_password`."""

    @pytest.mark.unit
    def test_verify_password_correct(self) -> None:
        """Verifying the original plain text against its hash must return True."""
        plain = "CorrectHorseBattery9"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    @pytest.mark.unit
    def test_verify_password_wrong_returns_false(self) -> None:
        """Verifying the wrong password against a hash must return False."""
        hashed = hash_password("correct-password")
        assert verify_password("wrong-password", hashed) is False

    @pytest.mark.unit
    def test_verify_password_empty_plain_returns_false(self) -> None:
        """An empty string must not verify against a hash of a real password."""
        hashed = hash_password("not-empty")
        assert verify_password("", hashed) is False


# ---------------------------------------------------------------------------
# Token creation
# ---------------------------------------------------------------------------


class TestCreateAccessToken:
    """Tests for :func:`create_access_token`."""

    @pytest.mark.unit
    def test_create_access_token_decodes_correctly(self) -> None:
        """A freshly created access token must decode to the original user_id.

        The ``sub`` claim in the decoded payload should match the UUID that
        was passed to :func:`create_access_token`.
        """
        from app.core.config import settings

        user_id = uuid.uuid4()
        token = create_access_token(user_id)

        payload: dict[str, Any] = jwt.decode(
            token, settings.secret_key, algorithms=[TOKEN_ALGORITHM]
        )
        assert payload["sub"] == str(user_id)

    @pytest.mark.unit
    def test_create_access_token_contains_exp_claim(self) -> None:
        """The access token payload must contain an ``exp`` claim.

        Without ``exp``, the token would never expire, which is a security
        risk.
        """
        from app.core.config import settings

        token = create_access_token(uuid.uuid4())
        payload: dict[str, Any] = jwt.decode(
            token, settings.secret_key, algorithms=[TOKEN_ALGORITHM]
        )
        assert "exp" in payload

    @pytest.mark.unit
    def test_create_access_token_contains_iat_claim(self) -> None:
        """The access token payload must contain an ``iat`` (issued-at) claim."""
        from app.core.config import settings

        token = create_access_token(uuid.uuid4())
        payload: dict[str, Any] = jwt.decode(
            token, settings.secret_key, algorithms=[TOKEN_ALGORITHM]
        )
        assert "iat" in payload


class TestCreateRefreshToken:
    """Tests for :func:`create_refresh_token`."""

    @pytest.mark.unit
    def test_create_refresh_token_decodes_correctly(self) -> None:
        """A freshly created refresh token must decode to the original user_id.

        The ``sub`` claim in the decoded payload should equal the UUID
        that was passed to :func:`create_refresh_token`.
        """
        from app.core.config import settings

        user_id = uuid.uuid4()
        token = create_refresh_token(user_id, token_version=0)

        payload: dict[str, Any] = jwt.decode(
            token, settings.secret_key, algorithms=[TOKEN_ALGORITHM]
        )
        assert payload["sub"] == str(user_id)

    @pytest.mark.unit
    def test_create_refresh_token_embeds_rtv_claim(self) -> None:
        """A refresh token must contain the ``rtv`` (refresh token version) claim.

        The version counter is used to detect revoked tokens after logout
        or explicit session invalidation.
        """
        from app.core.config import settings

        user_id = uuid.uuid4()
        token = create_refresh_token(user_id, token_version=3)

        payload: dict[str, Any] = jwt.decode(
            token, settings.secret_key, algorithms=[TOKEN_ALGORITHM]
        )
        assert payload["rtv"] == 3

    @pytest.mark.unit
    def test_create_refresh_token_has_longer_expiry_than_access(self) -> None:
        """The refresh token must live longer than the access token.

        This is verified by comparing the ``exp`` values of both tokens
        created at approximately the same time.
        """
        from app.core.config import settings

        user_id = uuid.uuid4()
        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id, token_version=0)

        access_payload: dict[str, Any] = jwt.decode(
            access_token, settings.secret_key, algorithms=[TOKEN_ALGORITHM]
        )
        refresh_payload: dict[str, Any] = jwt.decode(
            refresh_token, settings.secret_key, algorithms=[TOKEN_ALGORITHM]
        )

        assert refresh_payload["exp"] > access_payload["exp"]


# ---------------------------------------------------------------------------
# Token decoding
# ---------------------------------------------------------------------------


class TestDecodeToken:
    """Tests for :func:`decode_token`."""

    @pytest.mark.unit
    def test_decode_token_returns_correct_uuid(self) -> None:
        """decode_token on a valid access token must return the embedded UUID."""
        user_id = uuid.uuid4()
        token = create_access_token(user_id)
        result = decode_token(token)
        assert result == user_id

    @pytest.mark.unit
    def test_decode_token_works_for_refresh_token(self) -> None:
        """decode_token should also work on a valid refresh token."""
        user_id = uuid.uuid4()
        token = create_refresh_token(user_id, token_version=0)
        result = decode_token(token)
        assert result == user_id

    @pytest.mark.unit
    def test_decode_token_expired_raises_invalid_token_error(self) -> None:
        """A token whose ``exp`` is in the past must raise InvalidTokenError.

        The token is crafted with ``exp = now − 1 second`` so that it is
        already expired the moment it is decoded.
        """
        from app.core.config import settings

        expired_payload: dict[str, Any] = {
            "sub": str(uuid.uuid4()),
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) - timedelta(seconds=1),
        }
        expired_token = jwt.encode(
            expired_payload, settings.secret_key, algorithm=TOKEN_ALGORITHM
        )

        with pytest.raises(InvalidTokenError):
            decode_token(expired_token)

    @pytest.mark.unit
    def test_decode_token_invalid_raises_invalid_token_error(self) -> None:
        """A completely invalid (garbage) token string must raise InvalidTokenError.

        This covers the path where the JWT library raises ``JWTError`` due
        to a malformed or unsigned token.
        """
        with pytest.raises(InvalidTokenError):
            decode_token("this.is.not.a.real.jwt.token")

    @pytest.mark.unit
    def test_decode_token_missing_sub_raises_invalid_token_error(self) -> None:
        """A JWT that lacks a ``sub`` claim must raise InvalidTokenError.

        The service encodes user identity in the ``sub`` field; without it
        there is no way to identify the requesting user.
        """
        from app.core.config import settings

        payload_without_sub: dict[str, Any] = {
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=15),
        }
        token_no_sub = jwt.encode(
            payload_without_sub, settings.secret_key, algorithm=TOKEN_ALGORITHM
        )

        with pytest.raises(InvalidTokenError):
            decode_token(token_no_sub)

    @pytest.mark.unit
    def test_decode_token_wrong_secret_raises_invalid_token_error(self) -> None:
        """A token signed with a different secret must raise InvalidTokenError.

        This simulates an attacker forging a token with their own key.
        """
        from jose import jwt as jose_jwt

        forged_payload: dict[str, Any] = {
            "sub": str(uuid.uuid4()),
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=15),
        }
        forged_token = jose_jwt.encode(
            forged_payload,
            "attacker-controlled-secret-key-32chars!!",
            algorithm=TOKEN_ALGORITHM,
        )

        with pytest.raises(InvalidTokenError):
            decode_token(forged_token)
