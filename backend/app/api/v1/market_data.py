"""Route handlers for the ``/api/v1/market-data`` resource.

This module acts as a thin server-side proxy between the frontend and the
Market Data Hub (LSEG provider).  Placing the proxy in the backend avoids
TLS/DNS issues that occur when Next.js Route Handlers try to reach the Hub
directly from inside Docker containers using the undici HTTP stack.

The hub base URL is read from :attr:`app.core.config.Settings.market_data_hub_url`.
When that setting is ``None`` (not configured) the endpoint immediately
returns ``503 Service Unavailable`` so the frontend can fall back to the
TradingView embedded widget without displaying an error to the user.
"""

from datetime import datetime
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.services.market_data_service import MarketDataService

router = APIRouter(prefix="/market-data", tags=["market-data"])


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MarketDataService:
    """FastAPI dependency that constructs a :class:`MarketDataService`."""
    return MarketDataService(session)


# Shared async httpx client — reused across requests for connection pooling.
_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    """Return (or lazily create) the shared :class:`httpx.AsyncClient`.

    Returns:
        A singleton :class:`httpx.AsyncClient` instance.
    """
    global _http_client  # noqa: PLW0603
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=15.0, follow_redirects=True)
    return _http_client


def _hub_base() -> str:
    """Return the Hub base URL with any trailing slash stripped.

    Returns:
        The resolved Hub base URL string.

    Raises:
        :class:`fastapi.HTTPException`: 503 if ``MARKET_DATA_HUB_URL`` is not
            configured in the environment.
    """
    url = settings.market_data_hub_url
    if not url:
        raise HTTPException(
            status_code=503,
            detail="Market Data Hub is not configured (MARKET_DATA_HUB_URL unset).",
        )
    return url.rstrip("/")


@router.get(
    "/prices/{symbol}/history",
    summary="Proxy: OHLC price history for a symbol",
    response_model=None,
)
async def get_price_history(
    symbol: str,
    request: Request,
    service: Annotated[MarketDataService, Depends(_get_service)],
    provider: str = Query(default="lseg"),
    interval: str = Query(default="1d"),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    sec_type: str | None = Query(default=None),
) -> Any:
    """Proxy OHLC candlestick history from the Market Data Hub with local caching.

    Checks the local database cache first. If data is missing or incomplete,
    fetches from the upstream Hub and updates the cache.

    Args:
        symbol: Ticker symbol, e.g. ``AAPL`` or ``SPX``.
        request: Incoming FastAPI request.
        service: Market data service for DB access.
        provider: Data provider identifier passed to the Hub.
        interval: Candlestick interval, e.g. ``"1h"``, ``"4h"``, ``"1d"``.
        start: ISO-8601 start datetime for the requested range (inclusive).
        end: ISO-8601 end datetime for the requested range (inclusive).
        sec_type: Optional security type hint, e.g. ``"index"``.

    Returns:
        The JSON body with OHLC data.
    """
    # 1. Check local cache
    # ─────────────────────────────────────────────
    start_dt = datetime.fromisoformat(start.replace("Z", "+00:00")) if start else None
    end_dt = datetime.fromisoformat(end.replace("Z", "+00:00")) if end else None

    # Try to serve from cache if we have the full range
    cached_bars = await service.get_cached_prices(
        symbol, interval, provider, start_dt, end_dt
    )

    # Simplified coverage check: if we have bars and the first/last match
    # our requested range (with some tolerance for weekend/market hours),
    # we consider it a hit. For crypto/FX it's exact.
    # For now, if we have bars, we skip the upstream call IF the end_dt
    # is in the past. If end_dt is None (requesting until "now"), we always fetch.
    if cached_bars and end_dt and cached_bars[-1].start >= end_dt:
        return {"data": service.format_bars(cached_bars)}

    # 2. Fetch from upstream Hub
    # ─────────────────────────────────────────────
    base = _hub_base()

    params: dict[str, str] = {"provider": provider, "interval": interval}
    if start is not None:
        params["start"] = start
    if end is not None:
        params["end"] = end
    if sec_type is not None:
        params["sec_type"] = sec_type

    target_url = f"{base}/prices/{symbol}/history"

    client = _get_http_client()
    try:
        upstream = await client.get(target_url, params=params)
    except httpx.RequestError as exc:
        # On Hub failure, serve from cache as fallback
        cached = await service.get_cached_prices(
            symbol, interval, provider, start_dt, end_dt
        )
        if cached:
            return {"data": service.format_bars(cached)}
        raise HTTPException(
            status_code=502,
            detail=f"Market Data Hub unreachable: {exc}",
        ) from exc

    if not upstream.is_success:
        # Same here: if Hub fails, maybe we have cached data?
        cached = await service.get_cached_prices(
            symbol, interval, provider, start_dt, end_dt
        )
        if cached:
            return {"data": service.format_bars(cached)}
        raise HTTPException(
            status_code=upstream.status_code,
            detail=f"Hub returned {upstream.status_code}: {upstream.text[:200]}",
        )

    response_json = upstream.json()
    bars = response_json.get("data", [])

    # 3. Update Cache (Background)
    # ─────────────────────────────────────────────
    if bars:
        # Ensure bars have interval/provider info for caching
        for b in bars:
            b["interval"] = interval
            b["provider"] = provider
        await service.cache_prices(bars)

    return response_json
