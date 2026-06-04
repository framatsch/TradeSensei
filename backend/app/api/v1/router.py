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

"""Aggregated v1 API router.

Import and include all v1 sub-routers here so that ``main.py`` only
needs to mount a single router.
"""

from fastapi import APIRouter

from app.api.v1 import (
    accounts,
    analytics,
    annotation_definitions,
    auth,
    broker,
    checkin_metadata,
    checkins,
    corporate_actions,
    deprecated,
    executions,
    imports,
    market_data,
    market_indexes,
    metrics,
    notes,
    playbook_attachments,
    playbook_links,
    playbook_taxonomies,
    playbooks,
    portfolios,
    saved_checkin_filters,
    saved_trade_filters,
    screenshots,
    settings,
    taxonomies,
    timeseries,
    trade_metadata,
    trades,
    users,
    views,
)

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(portfolios.router)
router.include_router(accounts.router)
router.include_router(executions.router)
router.include_router(trades.router)
router.include_router(trades.global_router)
router.include_router(metrics.router)
router.include_router(views.router)
router.include_router(analytics.router)
router.include_router(imports.router)
router.include_router(timeseries.router)
router.include_router(playbooks.router)
router.include_router(playbook_taxonomies.router)
router.include_router(playbook_attachments.router)
router.include_router(playbook_links.router)
router.include_router(taxonomies.router)
router.include_router(annotation_definitions.router)
router.include_router(notes.router)
router.include_router(screenshots.router)
router.include_router(broker.router)
router.include_router(deprecated.router)
router.include_router(corporate_actions.router)
router.include_router(market_data.router)
router.include_router(market_indexes.router)
router.include_router(checkins.router)
router.include_router(saved_checkin_filters.router)
router.include_router(trade_metadata.router)
router.include_router(checkin_metadata.router)
router.include_router(settings.router)
router.include_router(
    saved_trade_filters.router,
    prefix="/saved-trade-filters",
    tags=["saved-trade-filters"],
)
