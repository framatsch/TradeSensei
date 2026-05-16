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

"""Service for retrieving and caching EUR/USD daily exchange rates.

Orchestrates the two-layer lookup:
1. Check the ``fx_rates`` DB cache via
   :class:`~app.repositories.fx_rate_repository.FxRateRepository`.
2. On cache miss, fetch from the ECB API via
   :func:`~app.utils.fx_rates.fetch_ecb_rate`.
3. Persist the fetched rate to the cache (upsert).

The service never commits the session — that is the caller's responsibility.
"""

import datetime as dt
import logging
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.fx_rate_repository import FxRateRepository
from app.utils.fx_rates import fetch_ecb_rate

logger = logging.getLogger(__name__)


class FxRateService:
    """Facade that combines DB caching and ECB API fetching.

    Attributes:
        _repo: The underlying
            :class:`~app.repositories.fx_rate_repository.FxRateRepository`.
    """

    def __init__(self) -> None:
        """Initialise with a default :class:`FxRateRepository` instance."""
        self._repo = FxRateRepository()

    async def get_usd_to_eur(
        self,
        session: AsyncSession,
        date: dt.date,
    ) -> Decimal | None:
        """Return the EUR/USD rate for *date*, using the DB cache if available.

        The rate represents ``1 USD = <rate> EUR``.

        Lookup order:
        1. DB cache (``fx_rates`` table) — instant, no network.
        2. ECB API (with fallback for weekends / holidays).
        3. If the API is unreachable: returns ``None`` and logs a warning.

        When a fresh rate is fetched from the API it is written back to the
        cache **without committing the session** — the caller must commit.

        Args:
            session: Active async SQLAlchemy session.
            date: The calendar date for which the rate is needed.

        Returns:
            The rate as :class:`~decimal.Decimal`, or ``None`` if unavailable.
        """
        # 1. Cache hit?
        cached = await self._repo.get_by_date(session, date, "USD", "EUR")
        if cached is not None:
            logger.debug("FX cache hit: USD/EUR on %s = %s", date, cached)
            return cached

        # 2. API fetch (includes weekend/holiday fallback internally).
        rate = await fetch_ecb_rate(date)
        if rate is None:
            logger.warning("EUR/USD rate unavailable for %s — pnl_eur will be NULL.", date)
            return None

        # 3. Persist to cache.
        await self._repo.upsert(session, date, "USD", "EUR", rate)
        logger.debug("FX rate fetched and cached: USD/EUR on %s = %s", date, rate)
        return rate
