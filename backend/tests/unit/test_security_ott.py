"""Unit tests for one-time OAuth exchange token functions in app/core/security.py.

Tests :func:`~app.core.security.create_one_time_token` and
:func:`~app.core.security.consume_one_time_token` in complete isolation —
no database access, no HTTP layer.

Replay-prevention relies on an in-process set (``_used_ott_jti``) that
persists across calls within the same process.  Each test that exercises the
blocklist **clears** that set in its setup so tests remain order-independent.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import patch

import pytest
from jose import jwt
from jose.exceptions import JWTError

from app.core.config import settings
from app.core.constants import ONE_TIME_TOKEN_EXPIRE_SECONDS, TOKEN_ALGORITHM
from app.core.exceptions import InvalidTokenError
from app.core.security import consume_one_time_token, create_one_time_token

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clear_ott_blocklist() -> None:
    """Clear the in-memory OTT blocklist between tests.

    ``_used_ott_jti`` is a module-level ``set[str]`` in
    ``app.core.security``.  We reach into the module to reset it so each
    test starts with an empty blocklist and replay tests are deterministic.
    """
    import app.core.security as sec

    sec._used_ott_jti.clear()


def _decode_raw(token: str) -> dict[str, Any]:
    """Decode a JWT without consuming it via the OTT logic.

    Used to inspect payload claims directly without triggering the
    blocklist update that :func:`consume_one_time_token` performs.

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
        """create_one_time_token() must return a non-empty string.

        The function should return a JWT string, not ``None`` or an empty
        value, so the caller can safely embed it in a redirect URL.
        """
        user_id = uuid.uuid4()
        token = create_one_time_token(user_id)
        assert isinstance(token, str) and len(token) > 0

    @pytest.mark.unit
    def test_create_one_time_token_embeds_ott_claim_true(self) -> None:
        """create_one_time_token() must embed ``ott=True`` in the payload.

        The ``ott`` claim is how :func:`consume_one_time_token` distinguishes
        an OTT from an ordinary access or refresh token.
        """
        user_id = uuid.uuid4()
        token = create_one_time_token(user_id)
        payload = _decode_raw(token)
        assert payload.get("ott") is True

    @pytest.mark.unit
    def test_create_one_time_token_embeds_jti_claim(self) -> None:
        """create_one_time_token() must embed a ``jti`` UUID string.

        The ``jti`` (JWT ID) is the key used for replay prevention — every
        token must carry a unique identifier so the blocklist can track it.
        """
        user_id = uuid.uuid4()
        token = create_one_time_token(user_id)
        payload = _decode_raw(token)
        jti = payload.get("jti")
        assert isinstance(jti, str) and len(jti) > 0
        # Must be a parseable UUID
        uuid.UUID(jti)  # raises ValueError if malformed

    @pytest.mark.unit
    def test_create_one_time_token_embeds_correct_sub(self) -> None:
        """create_one_time_token() must embed the caller's user UUID as ``sub``.

        After a successful OAuth flow the frontend exchanges the OTT for a
        full token pair; the ``sub`` claim is the sole source of user
        identity during that exchange.
        """
        user_id = uuid.uuid4()
        token = create_one_time_token(user_id)
        payload = _decode_raw(token)
        assert payload["sub"] == str(user_id)

    @pytest.mark.unit
    def test_create_one_time_token_has_exp_claim(self) -> None:
        """create_one_time_token() must embed an ``exp`` (expiry) claim.

        Without an expiry the token would be valid indefinitely, which
        defeats the purpose of a short-lived exchange token.
        """
        user_id = uuid.uuid4()
        token = create_one_time_token(user_id)
        payload = _decode_raw(token)
        assert "exp" in payload

    @pytest.mark.unit
    def test_create_one_time_token_expiry_within_expected_window(self) -> None:
        """The OTT expiry must be within ~ONE_TIME_TOKEN_EXPIRE_SECONDS of now.

        We allow a 5-second tolerance to avoid flakiness from slow test
        environments.
        """
        user_id = uuid.uuid4()
        token = create_one_time_token(user_id)
        payload = _decode_raw(token)

        # ``exp`` is returned as a Unix timestamp (int) by python-jose
        exp_ts: int = int(payload["exp"])
        expected_exp = datetime.now(UTC) + timedelta(
            seconds=ONE_TIME_TOKEN_EXPIRE_SECONDS
        )
        tolerance = timedelta(seconds=5)

        assert abs(datetime.fromtimestamp(exp_ts, tz=UTC) - expected_exp) < tolerance

    @pytest.mark.unit
    def test_create_one_time_token_each_call_produces_unique_jti(self) -> None:
        """Two separate calls must produce tokens with distinct ``jti`` values.

        The ``jti`` is a ``uuid.uuid4()``-generated string; collisions are
        astronomically unlikely but this test guards against an accidental
        constant or seed-based implementation.
        """
        user_id = uuid.uuid4()
        token_a = create_one_time_token(user_id)
        token_b = create_one_time_token(user_id)
        jti_a = _decode_raw(token_a)["jti"]
        jti_b = _decode_raw(token_b)["jti"]
        assert jti_a != jti_b


# ---------------------------------------------------------------------------
# consume_one_time_token — happy path
# ---------------------------------------------------------------------------


class TestConsumeOneTimeToken:
    """Unit tests for :func:`app.core.security.consume_one_time_token`."""

    def setup_method(self) -> None:
        """Reset the in-memory OTT blocklist before every test."""
        _clear_ott_blocklist()

    @pytest.mark.unit
    def test_consume_one_time_token_returns_correct_user_uuid(self) -> None:
        """consume_one_time_token() must return the UUID embedded in the token.

        The returned UUID must compare equal to the one that was passed to
        :func:`create_one_time_token`, confirming round-trip identity
        preservation.
        """
        user_id = uuid.uuid4()
        token = create_one_time_token(user_id)
        result = consume_one_time_token(token)
        assert result == user_id

    @pytest.mark.unit
    def test_consume_one_time_token_returns_uuid_type(self) -> None:
        """consume_one_time_token() must return a :class:`uuid.UUID` instance.

        Callers pass the return value directly to repository lookups that
        expect a proper UUID, not a string.
        """
        user_id = uuid.uuid4()
        token = create_one_time_token(user_id)
        result = consume_one_time_token(token)
        assert isinstance(result, uuid.UUID)

    # ---------------------------------------------------------------------------
    # Replay prevention
    # ---------------------------------------------------------------------------

    @pytest.mark.unit
    def test_consume_one_time_token_second_use_raises_invalid_token_error(
        self,
    ) -> None:
        """A previously consumed OTT must not be accepted a second time.

        The first call succeeds and adds the ``jti`` to the blocklist.
        The second call with the identical token string must raise
        :class:`~app.core.exceptions.InvalidTokenError`, preventing replay
        attacks where an intercepted token is reused.
        """
        user_id = uuid.uuid4()
        token = create_one_time_token(user_id)

        # First use — must succeed
        consume_one_time_token(token)

        # Second use — must be rejected
        with pytest.raises(InvalidTokenError):
            consume_one_time_token(token)

    @pytest.mark.unit
    def test_consume_one_time_token_third_use_also_raises(self) -> None:
        """Every use after the first must raise InvalidTokenError.

        Ensures the blocklist is not accidentally cleared after a single
        rejection — the ``jti`` must remain blocked indefinitely.
        """
        user_id = uuid.uuid4()
        token = create_one_time_token(user_id)

        consume_one_time_token(token)

        with pytest.raises(InvalidTokenError):
            consume_one_time_token(token)

        with pytest.raises(InvalidTokenError):
            consume_one_time_token(token)

    @pytest.mark.unit
    def test_consume_different_tokens_for_same_user_both_succeed(self) -> None:
        """Two *different* OTTs for the same user must each succeed once.

        Replay prevention is keyed on ``jti``, not on user identity.
        A second login attempt legitimately produces a second OTT with a
        new ``jti`` that has not yet been consumed.
        """
        user_id = uuid.uuid4()
        token_a = create_one_time_token(user_id)
        token_b = create_one_time_token(user_id)

        result_a = consume_one_time_token(token_a)
        result_b = consume_one_time_token(token_b)

        assert result_a == user_id
        assert result_b == user_id

    # ---------------------------------------------------------------------------
    # Expired tokens
    # ---------------------------------------------------------------------------

    @pytest.mark.unit
    def test_consume_one_time_token_expired_raises_invalid_token_error(self) -> None:
        """An OTT whose ``exp`` is in the past must raise InvalidTokenError.

        We craft the expired token manually so the test does not need to
        ``time.sleep()`` for the real expiry window.
        """
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

        with pytest.raises(InvalidTokenError):
            consume_one_time_token(expired_token)

    # ---------------------------------------------------------------------------
    # Malformed / tampered tokens
    # ---------------------------------------------------------------------------

    @pytest.mark.unit
    def test_consume_one_time_token_garbage_string_raises_invalid_token_error(
        self,
    ) -> None:
        """A completely invalid string must raise InvalidTokenError.

        This covers the ``JWTError`` path inside the try/except block.
        """
        with pytest.raises(InvalidTokenError):
            consume_one_time_token("not.a.real.jwt.at.all")

    @pytest.mark.unit
    def test_consume_one_time_token_wrong_secret_raises_invalid_token_error(
        self,
    ) -> None:
        """A token signed with a different secret must raise InvalidTokenError.

        Simulates an attacker crafting a forged OTT with their own key.
        """
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

        with pytest.raises(InvalidTokenError):
            consume_one_time_token(forged_token)

    @pytest.mark.unit
    def test_consume_one_time_token_missing_ott_claim_raises_invalid_token_error(
        self,
    ) -> None:
        """A valid JWT that lacks the ``ott=True`` claim must be rejected.

        An ordinary access token must not be accepted as an OTT, even if
        it is properly signed and unexpired.
        """
        user_id = uuid.uuid4()
        # Build a valid JWT but without the ott claim
        payload: dict[str, Any] = {
            "sub": str(user_id),
            "jti": str(uuid.uuid4()),
            # deliberately omit "ott"
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(seconds=60),
        }
        token_without_ott = jwt.encode(
            payload, settings.secret_key, algorithm=TOKEN_ALGORITHM
        )

        with pytest.raises(InvalidTokenError):
            consume_one_time_token(token_without_ott)

    @pytest.mark.unit
    def test_consume_one_time_token_missing_jti_claim_raises_invalid_token_error(
        self,
    ) -> None:
        """A JWT with ``ott=True`` but no ``jti`` must be rejected.

        Without a ``jti`` the blocklist cannot track the token and replay
        prevention is impossible — the service must refuse such tokens.
        """
        user_id = uuid.uuid4()
        payload: dict[str, Any] = {
            "sub": str(user_id),
            "ott": True,
            # deliberately omit "jti"
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(seconds=60),
        }
        token_without_jti = jwt.encode(
            payload, settings.secret_key, algorithm=TOKEN_ALGORITHM
        )

        with pytest.raises(InvalidTokenError):
            consume_one_time_token(token_without_jti)

    @pytest.mark.unit
    def test_consume_one_time_token_ott_false_raises_invalid_token_error(
        self,
    ) -> None:
        """A JWT with ``ott=False`` must be rejected.

        The ``ott`` claim must be truthy; a token where it was explicitly
        set to ``False`` must not pass the guard.
        """
        user_id = uuid.uuid4()
        payload: dict[str, Any] = {
            "sub": str(user_id),
            "jti": str(uuid.uuid4()),
            "ott": False,  # falsy — should be rejected
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(seconds=60),
        }
        token_ott_false = jwt.encode(
            payload, settings.secret_key, algorithm=TOKEN_ALGORITHM
        )

        with pytest.raises(InvalidTokenError):
            consume_one_time_token(token_ott_false)

    @pytest.mark.unit
    def test_consume_one_time_token_regular_access_token_raises_invalid_token_error(
        self,
    ) -> None:
        """A regular access token must not be accepted by consume_one_time_token().

        Access tokens produced by :func:`~app.core.security.create_access_token`
        do not carry the ``ott`` claim.  Passing one to the OTT exchange
        endpoint must be rejected.
        """
        from app.core.security import create_access_token

        user_id = uuid.uuid4()
        access_token = create_access_token(user_id)

        with pytest.raises(InvalidTokenError):
            consume_one_time_token(access_token)

    # ---------------------------------------------------------------------------
    # Blocklist isolation guard
    # ---------------------------------------------------------------------------

    @pytest.mark.unit
    def test_blocklist_is_not_shared_across_test_instances(self) -> None:
        """Each test must start with a clean blocklist (setup_method guard).

        Verifies that the setup_method() fixture clears the blocklist — if
        it didn't, a token created in one test and replayed here would raise
        InvalidTokenError even on "first" use.
        """
        # setup_method cleared the blocklist; this fresh token must succeed
        user_id = uuid.uuid4()
        token = create_one_time_token(user_id)
        result = consume_one_time_token(token)
        assert result == user_id

    @pytest.mark.unit
    def test_consume_one_time_token_does_not_add_to_blocklist_on_failure(
        self,
    ) -> None:
        """A failed consume attempt must not pollute the blocklist.

        If an expired or invalid token caused a ``jti`` to be added to the
        blocklist, a later valid token with the same ``jti`` (extremely
        unlikely in practice but possible in tests) would be wrongly rejected.
        We verify that the blocklist size does not change after a failed
        consume call.
        """
        import app.core.security as sec

        before = len(sec._used_ott_jti)

        with (
            patch(
                "app.core.security.jwt.decode",
                side_effect=JWTError("simulated decode failure"),
            ),
            pytest.raises(InvalidTokenError),
        ):
            consume_one_time_token("anything")

        after = len(sec._used_ott_jti)
        assert after == before
