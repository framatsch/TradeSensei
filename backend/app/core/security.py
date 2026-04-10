"""Password hashing and JWT utility functions.

All cryptographic operations used across the auth layer live here so
they can be tested and imported without pulling in any HTTP concerns.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any  # JWT payload values are heterogeneous (str, int, float)

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.constants import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ONE_TIME_TOKEN_EXPIRE_SECONDS,
    REFRESH_TOKEN_EXPIRE_DAYS,
    TOKEN_ALGORITHM,
)
from app.core.exceptions import InvalidTokenError
from app.schemas.auth import TokenPayload

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return the bcrypt hash of the given plain-text password.

    Args:
        plain: The raw password string supplied by the user.

    Returns:
        A bcrypt hash string suitable for storing in the database.
    """
    return str(_pwd_context.hash(plain))


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against its stored hash.

    Args:
        plain: The raw password string to verify.
        hashed: The stored bcrypt hash to verify against.

    Returns:
        ``True`` if the password matches, ``False`` otherwise.
    """
    result: bool = _pwd_context.verify(plain, hashed)
    return result


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def _create_token(
    user_id: uuid.UUID,
    expire_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Internal helper that encodes a JWT with a given expiry offset.

    Args:
        user_id: The subject (user UUID) to embed in the token.
        expire_delta: How long the token should remain valid.
        extra_claims: Optional additional claims to embed in the payload.

    Returns:
        A signed JWT string.
    """
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + expire_delta,
    }
    if extra_claims:
        payload.update(extra_claims)
    return str(jwt.encode(payload, settings.secret_key, algorithm=TOKEN_ALGORITHM))


def create_access_token(user_id: uuid.UUID) -> str:
    """Create a short-lived access JWT for the given user.

    Args:
        user_id: UUID of the authenticated user.

    Returns:
        A signed JWT string valid for
        :data:`~app.core.constants.ACCESS_TOKEN_EXPIRE_MINUTES` minutes.
    """
    return _create_token(user_id, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))


def create_refresh_token(user_id: uuid.UUID, token_version: int) -> str:
    """Create a long-lived refresh JWT for the given user.

    The ``rtv`` (refresh token version) claim is embedded in the payload
    so that all existing refresh tokens can be invalidated by incrementing
    the stored version counter on the user record.

    Args:
        user_id: UUID of the authenticated user.
        token_version: Current ``refresh_token_version`` from the user record.

    Returns:
        A signed JWT string valid for
        :data:`~app.core.constants.REFRESH_TOKEN_EXPIRE_DAYS` days.
    """
    return _create_token(
        user_id,
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        extra_claims={"rtv": token_version},
    )


def decode_token(token: str) -> uuid.UUID:
    """Decode a JWT and return the embedded user UUID.

    Uses :class:`~app.schemas.auth.TokenPayload` to validate the decoded
    payload structure before extracting the subject claim.

    Args:
        token: A signed JWT string (access or refresh).

    Returns:
        The :class:`uuid.UUID` extracted from the ``sub`` claim.

    Raises:
        :class:`~app.core.exceptions.InvalidTokenError`: If the token is
            expired, malformed, or missing a valid ``sub`` claim.
    """
    try:
        raw: dict[str, Any] = jwt.decode(
            token, settings.secret_key, algorithms=[TOKEN_ALGORITHM]
        )
        validated = TokenPayload.model_validate(raw)
        return validated.sub
    except (JWTError, ValueError) as exc:
        raise InvalidTokenError("Invalid or expired token.") from exc


def decode_refresh_token(token: str) -> tuple[uuid.UUID, int]:
    """Decode a refresh JWT and return the user UUID and token version.

    In addition to the standard ``sub`` claim validation performed by
    :func:`decode_token`, this function also extracts and validates the
    ``rtv`` (refresh token version) claim, which is used to detect
    revoked refresh tokens.

    Args:
        token: A signed refresh JWT string.

    Returns:
        A two-tuple of ``(user_id, token_version)`` where ``token_version``
        is the ``rtv`` claim embedded at issuance.

    Raises:
        :class:`~app.core.exceptions.InvalidTokenError`: If the token is
            expired, malformed, missing a valid ``sub`` claim, or missing
            the ``rtv`` claim.
    """
    try:
        raw: dict[str, Any] = jwt.decode(
            token, settings.secret_key, algorithms=[TOKEN_ALGORITHM]
        )
        validated = TokenPayload.model_validate(raw)
        rtv = raw.get("rtv")
        if rtv is None or not isinstance(rtv, int):
            raise InvalidTokenError("Refresh token is missing version claim.")
        return validated.sub, rtv
    except InvalidTokenError:
        raise
    except (JWTError, ValueError) as exc:
        raise InvalidTokenError("Invalid or expired refresh token.") from exc


# ---------------------------------------------------------------------------
# One-time OAuth exchange tokens
# ---------------------------------------------------------------------------

# In-memory store: jti → expiry. Works only per-process; in multi-process
# production deployments this must be replaced with shared state (e.g. Redis).
_used_ott_jti: set[str] = set()


def create_one_time_token(user_id: uuid.UUID) -> str:
    """Create a short-lived one-time token for the OAuth callback exchange.

    The token is a JWT with a unique ``jti`` claim.  After a single use
    (validated via :func:`consume_one_time_token`) the ``jti`` is added to
    an in-memory blocklist so it cannot be replayed.

    Args:
        user_id: UUID of the authenticated user.

    Returns:
        A signed JWT string valid for
        :data:`~app.core.constants.ONE_TIME_TOKEN_EXPIRE_SECONDS` seconds.
    """
    jti = str(uuid.uuid4())
    return _create_token(
        user_id,
        timedelta(seconds=ONE_TIME_TOKEN_EXPIRE_SECONDS),
        extra_claims={"jti": jti, "ott": True},
    )


def consume_one_time_token(token: str) -> uuid.UUID:
    """Decode and invalidate a one-time token, returning the user UUID.

    The token is validated for signature, expiry, and the ``ott`` claim.
    On success the ``jti`` is added to the blocklist so the same token
    cannot be used again.

    Args:
        token: A signed one-time JWT string.

    Returns:
        The :class:`uuid.UUID` of the authenticated user.

    Raises:
        :class:`~app.core.exceptions.InvalidTokenError`: If the token is
            expired, already used, malformed, or missing required claims.
    """
    try:
        raw: dict[str, Any] = jwt.decode(
            token, settings.secret_key, algorithms=[TOKEN_ALGORITHM]
        )
        if not raw.get("ott"):
            raise InvalidTokenError("Not a one-time token.")
        jti = raw.get("jti")
        if not isinstance(jti, str):
            raise InvalidTokenError("One-time token missing jti claim.")
        if jti in _used_ott_jti:
            raise InvalidTokenError("One-time token already used.")
        validated = TokenPayload.model_validate(raw)
        # Mark as used
        _used_ott_jti.add(jti)
        return validated.sub
    except InvalidTokenError:
        raise
    except (JWTError, ValueError) as exc:
        raise InvalidTokenError("Invalid or expired one-time token.") from exc
