"""Password hashing, JWT utility functions, cursor signing, and OTT blocklist.

All cryptographic operations used across the auth layer live here so
they can be tested and imported without pulling in any HTTP concerns.
"""

import base64
import hashlib
import hmac
import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any  # JWT payload values are heterogeneous (str, int, float)

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ONE_TIME_TOKEN_EXPIRE_SECONDS,
    PASSWORD_RESET_TOKEN_EXPIRE_SECONDS,
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


def generate_pat() -> str:
    """Generate a high-entropy personal access token string."""
    return secrets.token_urlsafe(48)


def hash_pat(token: str) -> str:
    """Return a SHA-256 hex digest for a personal access token."""
    return hashlib.sha256(token.encode()).hexdigest()


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
# One-time OAuth exchange tokens — DB-backed blocklist
# ---------------------------------------------------------------------------


def create_one_time_token(user_id: uuid.UUID) -> str:
    """Create a short-lived one-time token for the OAuth callback exchange.

    The token is a JWT with a unique ``jti`` claim.  After a single use
    (validated via :func:`consume_one_time_token`) the ``jti`` is stored in
    the ``used_otts`` database table so it cannot be replayed across any
    process.

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


async def consume_ott_jti(jti: str, expires_at: datetime, db: AsyncSession) -> bool:
    """Atomically consume a one-time token JTI, recording it in the database.

    Inserts the ``jti`` into ``used_otts``.  On a duplicate-key
    :class:`~sqlalchemy.exc.IntegrityError` (i.e. the JTI was already used),
    rolls back the nested savepoint and returns ``False``.

    Also prunes expired rows on every call so the table stays bounded without
    a separate cron job.

    Args:
        jti: The JWT ID claim of the one-time token.
        expires_at: When the token expires (UTC).  Used for future pruning.
        db: An open :class:`~sqlalchemy.ext.asyncio.AsyncSession`.

    Returns:
        ``True`` if the JTI was fresh (inserted successfully).
        ``False`` if the JTI was already present (replay detected).
    """
    # Deferred import to break circular dependency: models -> database
    from sqlalchemy import delete

    from app.models.used_ott import UsedOtt

    # Prune expired rows before inserting (best-effort — table stays small).
    now = datetime.now(UTC)
    await db.execute(delete(UsedOtt).where(UsedOtt.expires_at < now))

    try:
        db.add(UsedOtt(jti=jti, expires_at=expires_at))
        await db.flush()
        return True
    except IntegrityError:
        await db.rollback()
        return False


async def consume_one_time_token(token: str, db: AsyncSession) -> uuid.UUID:
    """Decode and invalidate a one-time token, returning the user UUID.

    The token is validated for signature, expiry, and the ``ott`` claim.
    On success the ``jti`` is stored in the database so the same token
    cannot be replayed on any process.

    Args:
        token: A signed one-time JWT string.
        db: An open :class:`~sqlalchemy.ext.asyncio.AsyncSession`.

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
        exp = raw.get("exp")
        if not isinstance(exp, (int, float)):
            raise InvalidTokenError("One-time token missing exp claim.")
        expires_at = datetime.fromtimestamp(float(exp), tz=UTC)
        validated = TokenPayload.model_validate(raw)
        # Atomically insert jti — returns False if already consumed (replay).
        fresh = await consume_ott_jti(jti, expires_at, db)
        if not fresh:
            raise InvalidTokenError("One-time token already used.")
        return validated.sub
    except InvalidTokenError:
        raise
    except (JWTError, ValueError) as exc:
        raise InvalidTokenError("Invalid or expired one-time token.") from exc


# ---------------------------------------------------------------------------
# Password-reset tokens — DB-backed blocklist (reuses used_otts)
# ---------------------------------------------------------------------------


def create_password_reset_token(user_id: uuid.UUID) -> str:
    """Create a one-hour password-reset token for the given user.

    The token is a JWT with a unique ``jti`` claim and a ``pwreset: True``
    marker.  After a single use (validated via
    :func:`consume_password_reset_token`) the ``jti`` is stored in the
    ``used_otts`` table so the link cannot be replayed.

    Args:
        user_id: UUID of the user requesting a password reset.

    Returns:
        A signed JWT string valid for
        :data:`~app.core.constants.PASSWORD_RESET_TOKEN_EXPIRE_SECONDS`
        seconds (1 hour).
    """
    jti = str(uuid.uuid4())
    return _create_token(
        user_id,
        timedelta(seconds=PASSWORD_RESET_TOKEN_EXPIRE_SECONDS),
        extra_claims={"jti": jti, "pwreset": True},
    )


async def consume_password_reset_token(token: str, db: AsyncSession) -> uuid.UUID:
    """Decode and invalidate a password-reset token, returning the user UUID.

    The token is validated for signature, expiry, and the ``pwreset`` claim.
    On success the ``jti`` is stored in the database so the same token
    cannot be replayed on any process.

    Args:
        token: A signed password-reset JWT string.
        db: An open :class:`~sqlalchemy.ext.asyncio.AsyncSession`.

    Returns:
        The :class:`uuid.UUID` of the user whose password should be reset.

    Raises:
        :class:`~app.core.exceptions.InvalidTokenError`: If the token is
            expired, already used, malformed, or missing required claims.
    """
    try:
        raw: dict[str, Any] = jwt.decode(
            token, settings.secret_key, algorithms=[TOKEN_ALGORITHM]
        )
        if not raw.get("pwreset"):
            raise InvalidTokenError("Not a password-reset token.")
        jti = raw.get("jti")
        if not isinstance(jti, str):
            raise InvalidTokenError("Password-reset token missing jti claim.")
        exp = raw.get("exp")
        if not isinstance(exp, (int, float)):
            raise InvalidTokenError("Password-reset token missing exp claim.")
        expires_at = datetime.fromtimestamp(float(exp), tz=UTC)
        validated = TokenPayload.model_validate(raw)
        fresh = await consume_ott_jti(jti, expires_at, db)
        if not fresh:
            raise InvalidTokenError("Password-reset token already used.")
        return validated.sub
    except InvalidTokenError:
        raise
    except (JWTError, ValueError) as exc:
        raise InvalidTokenError("Invalid or expired password-reset token.") from exc


# ---------------------------------------------------------------------------
# Cursor signing (HMAC-SHA256)
# ---------------------------------------------------------------------------


def encode_cursor(payload: dict[str, Any], secret: str) -> str:
    """Encode a pagination cursor payload as an HMAC-SHA256 signed, base64url token.

    The payload is serialised to compact JSON, then the HMAC-SHA256 hex
    digest is appended with a ``"."`` separator before the whole string is
    base64url-encoded.  This lets :func:`decode_cursor` verify that the
    cursor was produced by this application and has not been tampered with.

    Args:
        payload: Arbitrary JSON-serialisable dict (e.g. cursor keyset values).
        secret: Application secret used to sign the cursor.

    Returns:
        A URL-safe base64-encoded cursor token string.
    """
    data = json.dumps(payload, separators=(",", ":"))
    sig = hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()
    raw = f"{data}.{sig}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(token: str, secret: str) -> dict[str, Any]:
    """Decode and verify an HMAC-signed cursor token.

    Decodes the base64url token, splits on the last ``"."`` to separate the
    JSON payload from the HMAC signature, and verifies the signature using
    :func:`hmac.compare_digest` (constant-time comparison).

    Args:
        token: A cursor token previously produced by :func:`encode_cursor`.
        secret: Application secret used to verify the signature.

    Returns:
        The decoded payload dict.

    Raises:
        ValueError: If the token cannot be decoded, is malformed, or the
            signature does not match.
    """
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        data, sig = raw.rsplit(".", 1)
        expected = hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise ValueError("Invalid cursor signature")
        result: dict[str, Any] = json.loads(data)
        return result
    except (ValueError, Exception) as exc:
        # Re-raise ValueError for signature mismatch; wrap everything else.
        if isinstance(exc, ValueError):
            raise
        raise ValueError(f"Malformed cursor token: {exc}") from exc
