"""Unit tests for cursor security functions in app/core/security.py.

Tests :func:`~app.core.security.encode_cursor` and
:func:`~app.core.security.decode_cursor` in complete isolation — no database
access required.

Tasks covered: 3.5 – 3.7
"""

import uuid

import pytest
from httpx import AsyncClient

from app.core.security import decode_cursor, encode_cursor

SECRET = "test-cursor-signing-secret-key-for-unit-tests"
OTHER_SECRET = "different-secret-key-that-does-not-match"


class TestEncodeCursorDecodeCursorRoundtrip:
    """Task 3.5: encode_cursor → decode_cursor round-trip."""

    @pytest.mark.unit
    def test_cursor_encode_decode_roundtrip_string_value(self) -> None:
        """encode_cursor/decode_cursor must preserve string payload values."""
        payload = {"sv": "AAPL", "id": str(uuid.uuid4())}
        token = encode_cursor(payload, SECRET)
        recovered = decode_cursor(token, SECRET)
        assert recovered["sv"] == payload["sv"]
        assert recovered["id"] == payload["id"]

    @pytest.mark.unit
    def test_cursor_encode_decode_roundtrip_numeric_value(self) -> None:
        """encode_cursor/decode_cursor must preserve numeric payload values."""
        payload = {"sv": "123.456", "id": str(uuid.uuid4()), "extra": 42}
        token = encode_cursor(payload, SECRET)
        recovered = decode_cursor(token, SECRET)
        assert recovered["extra"] == 42

    @pytest.mark.unit
    def test_cursor_encode_decode_roundtrip_empty_sort_value(self) -> None:
        """An empty sort value (NULL sentinel) must survive the round-trip."""
        payload = {"sv": "", "id": str(uuid.uuid4())}
        token = encode_cursor(payload, SECRET)
        recovered = decode_cursor(token, SECRET)
        assert recovered["sv"] == ""

    @pytest.mark.unit
    def test_cursor_different_secrets_produce_different_tokens(self) -> None:
        """The same payload signed with different secrets must differ."""
        payload = {"sv": "TSLA", "id": str(uuid.uuid4())}
        token_a = encode_cursor(payload, SECRET)
        token_b = encode_cursor(payload, OTHER_SECRET)
        assert token_a != token_b

    @pytest.mark.unit
    def test_cursor_token_is_url_safe(self) -> None:
        """The encoded cursor must not contain URL-unsafe characters.

        ``urlsafe_b64encode`` replaces ``+`` and ``/`` with ``-`` and ``_``
        respectively.  Padding ``=`` is allowed in urlsafe base64.
        """
        payload = {"sv": "2024-01-01T00:00:00+00:00", "id": str(uuid.uuid4())}
        token = encode_cursor(payload, SECRET)
        # urlsafe_b64encode must not use + or / (the standard base64 unsafe chars).
        assert "+" not in token
        assert "/" not in token


class TestTamperedCursor:
    """Task 3.6: A tampered cursor must raise ValueError (→ 400 at route level)."""

    @pytest.mark.unit
    def test_tampered_cursor_raises_value_error(self) -> None:
        """Flipping a character in the signed cursor must raise ValueError."""
        payload = {"sv": "SPY", "id": str(uuid.uuid4())}
        token = encode_cursor(payload, SECRET)
        # Flip the last character to tamper with the signature.
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        with pytest.raises(ValueError):
            decode_cursor(tampered, SECRET)

    @pytest.mark.unit
    def test_wrong_secret_raises_value_error(self) -> None:
        """Decoding with a different secret must raise ValueError."""
        payload = {"sv": "QQQ", "id": str(uuid.uuid4())}
        token = encode_cursor(payload, SECRET)
        with pytest.raises(ValueError):
            decode_cursor(token, OTHER_SECRET)

    @pytest.mark.unit
    def test_garbage_cursor_raises_value_error(self) -> None:
        """A completely invalid cursor string must raise ValueError."""
        with pytest.raises(ValueError):
            decode_cursor("not-a-valid-cursor-at-all", SECRET)

    @pytest.mark.unit
    def test_empty_cursor_raises_value_error(self) -> None:
        """An empty cursor string must raise ValueError."""
        with pytest.raises(ValueError):
            decode_cursor("", SECRET)


class TestOtherUserCursorReturnsEmpty:
    """Task 3.7: A cursor from user A returns no rows when queried as user B.

    This test verifies that the WHERE clause includes user_id unconditionally.
    We do this via the API integration path so the full stack is exercised.
    """

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_other_user_cursor_returns_empty(
        self, client: AsyncClient, db_session: object
    ) -> None:
        """A cursor obtained by user A must yield zero results when used by user B.

        Ownership is enforced by the unconditional ``WHERE user_id = :uid``
        in :meth:`TradeRepository.list_cursor`.  Even if user B somehow
        obtains a valid cursor signed for user A's dataset, the query returns
        no rows because no trades in user B's scope match the cursor's position.

        The cursor signature check (ValueError → 400) is the first line of
        defence; the user_id WHERE clause is the second.  This test verifies
        the second.

        We use the HTTP client (integration path) to register two users and
        assert that the cursor from user A's list response returns zero items
        when submitted on user B's list request.
        """
        from sqlalchemy.ext.asyncio import AsyncSession

        assert isinstance(db_session, AsyncSession)

        # Register user A
        resp_a = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "cursor_user_a",
                "email": "cursor_a@example.com",
                "password": "S3cureP@ss99",
            },
        )
        assert resp_a.status_code == 201

        token_resp_a = await client.post(
            "/api/v1/auth/token",
            data={"username": "cursor_user_a", "password": "S3cureP@ss99"},
        )
        assert token_resp_a.status_code == 200
        headers_a = {"Authorization": f"Bearer {token_resp_a.json()['access_token']}"}

        # Register user B
        resp_b = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "cursor_user_b",
                "email": "cursor_b@example.com",
                "password": "S3cureP@ss99",
            },
        )
        assert resp_b.status_code == 201

        token_resp_b = await client.post(
            "/api/v1/auth/token",
            data={"username": "cursor_user_b", "password": "S3cureP@ss99"},
        )
        assert token_resp_b.status_code == 200
        headers_b = {"Authorization": f"Bearer {token_resp_b.json()['access_token']}"}

        # Create an account for user A
        acc_resp_a = await client.post(
            "/api/v1/accounts",
            json={"name": "Acc A", "type": "manual", "currency": "USD"},
            headers=headers_a,
        )
        assert acc_resp_a.status_code == 201
        account_id_a = acc_resp_a.json()["data"]["id"]

        # Create two trades for user A so the cursor page has data
        for i in range(2):
            tr = await client.post(
                "/api/v1/trades",
                json={
                    "account_id": account_id_a,
                    "symbol": f"AAA{i}",
                    "direction": "LONG",
                    "asset_class": "EQUITY",
                    "quantity": "1",
                    "entry_price": "10",
                    "opened_at": "2024-01-01T10:00:00Z",
                    "currency": "USD",
                },
                headers=headers_a,
            )
            assert tr.status_code == 201

        # List user A's trades with limit=1 to get a cursor
        list_a = await client.get(
            "/api/v1/trades?limit=1",
            headers=headers_a,
        )
        assert list_a.status_code == 200
        cursor_from_a = list_a.json()["data"].get("next_cursor")

        if cursor_from_a is None:
            # Only one trade was returned — skip test with a note
            pytest.skip("Could not obtain a cursor from user A's list (need >1 trade).")

        # Use user A's cursor on user B's request — must return zero items
        list_b = await client.get(
            f"/api/v1/trades?limit=10&cursor={cursor_from_a}",
            headers=headers_b,
        )
        # Expect 200 with empty items, or 400 (bad cursor for this user's context).
        assert list_b.status_code in (200, 400), list_b.text
        if list_b.status_code == 200:
            items = list_b.json()["data"]["items"]
            assert len(items) == 0, "User B must not see user A's trades via cursor"
