"""Business-logic service for Schwab live broker API integration.

Orchestrates OAuth 2.0 PKCE flow, token management, and incremental
trade synchronisation.  No HTTP concepts appear in this layer.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BrokerConnectionNotFoundError, ConfigurationError
from app.models.trade import Trade
from app.repositories.broker_connection_repository import BrokerConnectionRepository
from app.schemas.broker import BrokerStatusResponse, SchwabSyncResult
from app.schemas.trade import TradeCreate
from app.utils.encryption import decrypt_token, encrypt_token
from app.utils.schwab_client import SchwabClient
from app.utils.schwab_normalizer import SchwabOrderNormalizer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level in-memory state for pending PKCE exchanges.
# Maps state → (user_id, code_verifier).
# A production implementation would use Redis or the DB; this is sufficient
# for a single-process stub.
# ---------------------------------------------------------------------------
_pending_states: dict[str, tuple[uuid.UUID, str]] = {}

# Number of seconds before token expiry at which we proactively refresh.
_TOKEN_REFRESH_BUFFER_SECONDS: int = 300  # 5 minutes

_SCHWAB_BROKER_KEY: str = "schwab"


def _generate_pkce_pair() -> tuple[str, str]:
    """Generate a PKCE code_verifier / code_challenge pair (S256 method).

    Returns:
        A tuple of ``(code_verifier, code_challenge)`` where:

        - ``code_verifier`` is a cryptographically random URL-safe string.
        - ``code_challenge`` is the URL-safe base64 SHA-256 of the verifier
          (no padding).
    """
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return code_verifier, code_challenge


class BrokerService:
    """Service layer for broker OAuth connections and trade synchronisation.

    Handles the full Schwab OAuth 2.0 PKCE lifecycle and delegates data
    persistence to
    :class:`~app.repositories.broker_connection_repository.BrokerConnectionRepository`.

    Args:
        session: An open :class:`~sqlalchemy.ext.asyncio.AsyncSession`
            managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with a database session.

        Args:
            session: The session to use for all operations within this
                request lifecycle.
        """
        self._session = session
        self._repo = BrokerConnectionRepository(session)
        self._client = SchwabClient()

    async def get_schwab_connect_url(self, user_id: uuid.UUID) -> str:
        """Generate and return a Schwab OAuth 2.0 PKCE authorization URL.

        Generates a fresh PKCE pair and a random CSRF state token, stores them
        in the module-level ``_pending_states`` dict, and returns the full
        authorization URL for the user to visit.

        Args:
            user_id: UUID of the authenticated user initiating the connection.

        Returns:
            A fully-qualified Schwab authorization URL string.

        Raises:
            :class:`~app.core.exceptions.ConfigurationError`: If
                ``SCHWAB_CLIENT_ID`` is not configured.
        """
        code_verifier, code_challenge = _generate_pkce_pair()
        state = secrets.token_urlsafe(32)
        _pending_states[state] = (user_id, code_verifier)
        return self._client.get_authorization_url(
            state=state,
            code_challenge=code_challenge,
        )

    async def handle_schwab_callback(self, code: str, state: str) -> None:
        """Process the Schwab OAuth callback and persist the tokens.

        Validates the ``state`` parameter against the pending PKCE exchange,
        exchanges the authorization code for tokens, encrypts them, and
        stores the connection via the repository.

        Args:
            code: The authorization code from the Schwab redirect callback.
            state: The CSRF state token echoed back from Schwab.

        Raises:
            :class:`ValueError`: If the ``state`` is not found in
                ``_pending_states`` (invalid or expired CSRF token).
            :class:`~app.core.exceptions.ConfigurationError`: If Schwab
                credentials are not configured.
            :class:`httpx.HTTPStatusError`: If the token exchange fails.
        """
        pending = _pending_states.pop(state, None)
        if pending is None:
            raise ValueError(
                f"Unknown or expired OAuth state: {state!r}. "
                "The authorization request may have timed out."
            )
        user_id, code_verifier = pending

        token_data: dict[str, Any] = await self._client.exchange_code(
            code=code,
            code_verifier=code_verifier,
        )

        access_token: str = token_data["access_token"]
        refresh_token: str = token_data.get("refresh_token", "")
        expires_in: int = int(token_data.get("expires_in", 1800))
        token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)

        await self._repo.upsert(
            user_id=user_id,
            broker=_SCHWAB_BROKER_KEY,
            access_token=encrypt_token(access_token),
            refresh_token=encrypt_token(refresh_token),
            token_expires_at=token_expires_at,
        )
        await self._session.commit()

    async def disconnect_schwab(self, user_id: uuid.UUID) -> None:
        """Delete the Schwab OAuth connection for the given user.

        Args:
            user_id: UUID of the authenticated user.

        Raises:
            :class:`~app.core.exceptions.BrokerConnectionNotFoundError`: If
                no Schwab connection exists for this user.
        """
        connection = await self._repo.get_by_user_broker(
            user_id=user_id,
            broker=_SCHWAB_BROKER_KEY,
        )
        if connection is None:
            raise BrokerConnectionNotFoundError(
                f"No Schwab connection found for user {user_id}."
            )
        await self._repo.delete(user_id=user_id, broker=_SCHWAB_BROKER_KEY)
        await self._session.commit()

    async def get_schwab_status(self, user_id: uuid.UUID) -> BrokerStatusResponse:
        """Return the current Schwab connection status for a user.

        Args:
            user_id: UUID of the authenticated user.

        Returns:
            A :class:`~app.schemas.broker.BrokerStatusResponse` indicating
            whether the user is connected and when the last sync occurred.
        """
        connection = await self._repo.get_by_user_broker(
            user_id=user_id,
            broker=_SCHWAB_BROKER_KEY,
        )
        if connection is None:
            return BrokerStatusResponse(connected=False, last_sync_at=None)
        return BrokerStatusResponse(
            connected=True,
            last_sync_at=connection.last_sync_at,
        )

    async def sync_schwab_trades(
        self,
        user_id: uuid.UUID,
        days: int = 30,
    ) -> SchwabSyncResult:
        """Fetch recent orders from Schwab and import new trades.

        1. Retrieves the stored connection and decrypts tokens.
        2. Proactively refreshes the access token if it expires within
           :data:`_TOKEN_REFRESH_BUFFER_SECONDS` seconds.
        3. Fetches orders from the Schwab API for the last ``days`` days.
        4. Normalises each order via
           :class:`~app.utils.schwab_normalizer.SchwabOrderNormalizer`.
        5. Deduplicates by ``broker_order_id`` — skips orders already in DB.
        6. Inserts new trades and updates the ``last_sync_at`` timestamp.

        Args:
            user_id: UUID of the authenticated user.
            days: Number of past days to fetch orders for (default 30).

        Returns:
            A :class:`~app.schemas.broker.SchwabSyncResult` with counts
            of imported, skipped, and errored orders.

        Raises:
            :class:`~app.core.exceptions.BrokerConnectionNotFoundError`: If
                no Schwab connection exists for this user.
            :class:`~app.core.exceptions.ConfigurationError`: If Schwab
                credentials are not configured.
        """
        connection = await self._repo.get_by_user_broker(
            user_id=user_id,
            broker=_SCHWAB_BROKER_KEY,
        )
        if connection is None:
            raise BrokerConnectionNotFoundError(
                f"No Schwab connection found for user {user_id}. "
                "Connect first via GET /broker/schwab/connect."
            )

        # Decrypt tokens
        try:
            access_token = decrypt_token(connection.access_token)
            refresh_token = decrypt_token(connection.refresh_token)
        except Exception as exc:
            raise ConfigurationError(
                "Failed to decrypt stored tokens. The BROKER_ENCRYPTION_KEY may "
                "have changed since the tokens were stored."
            ) from exc

        # Proactively refresh if expiring soon
        now = datetime.now(UTC)
        expires_at = connection.token_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at - now < timedelta(seconds=_TOKEN_REFRESH_BUFFER_SECONDS):
            logger.info(
                "Schwab access token expiring soon for user %s — refreshing.",
                user_id,
            )
            token_data = await self._client.refresh_access_token(refresh_token)
            access_token = token_data["access_token"]
            new_refresh = token_data.get("refresh_token", refresh_token)
            new_expires_in = int(token_data.get("expires_in", 1800))
            new_expires_at = now + timedelta(seconds=new_expires_in)

            await self._repo.upsert(
                user_id=user_id,
                broker=_SCHWAB_BROKER_KEY,
                access_token=encrypt_token(access_token),
                refresh_token=encrypt_token(new_refresh),
                token_expires_at=new_expires_at,
            )

        # Build date range
        to_date = now.strftime("%Y-%m-%d")
        from_date = (now - timedelta(days=days)).strftime("%Y-%m-%d")

        # Fetch orders from Schwab
        orders = await self._client.get_orders(
            access_token=access_token,
            from_date=from_date,
            to_date=to_date,
        )

        # Normalise orders
        normalizer = SchwabOrderNormalizer()
        normalised: list[TradeCreate] = []
        error_messages: list[str] = []
        skipped_count = 0

        for order in orders:
            try:
                trade_create = normalizer.normalize(order)
                if trade_create is None:
                    skipped_count += 1
                    continue
                normalised.append(trade_create)
            except Exception as exc:
                order_id = order.get("orderId", "?")
                error_messages.append(f"Order {order_id}: {exc}")
                logger.warning("Failed to normalise Schwab order %s: %s", order_id, exc)

        # Collect all broker_order_ids from normalised orders for deduplication
        candidate_ids = [
            tc.broker_order_id for tc in normalised if tc.broker_order_id is not None
        ]

        # Fetch existing broker_order_ids in bulk
        existing_ids: set[str] = set()
        if candidate_ids:
            stmt = select(Trade.broker_order_id).where(
                Trade.user_id == user_id,
                Trade.broker_order_id.in_(candidate_ids),
            )
            result = await self._session.execute(stmt)
            existing_ids = {row[0] for row in result if row[0] is not None}

        # Insert new trades
        imported_count = 0
        for trade_create in normalised:
            if (
                trade_create.broker_order_id is not None
                and trade_create.broker_order_id in existing_ids
            ):
                skipped_count += 1
                continue

            trade_create.user_id = user_id
            create_dict = trade_create.model_dump(exclude={"tag_ids"})
            trade = Trade(**create_dict)
            self._session.add(trade)
            imported_count += 1

        # Update last_sync_at and commit
        await self._session.flush()
        await self._repo.update_last_sync(user_id=user_id, broker=_SCHWAB_BROKER_KEY)
        await self._session.commit()

        return SchwabSyncResult(
            imported_count=imported_count,
            skipped_count=skipped_count,
            errors=error_messages,
        )
