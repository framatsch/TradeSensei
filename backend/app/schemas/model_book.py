import datetime as dt
import uuid
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.daily_checkin import TargetIndexRead
from app.schemas.trade import AssetClass, Direction


class ModelBookTradeVariant(BaseModel):
    """Model Book entry variant representing a starred trade."""

    model_config = ConfigDict(from_attributes=True)

    type: Literal["trade"] = "trade"
    id: uuid.UUID = Field(..., description="Trade ID")
    date: dt.datetime = Field(..., description="Opened timestamp of the trade")
    symbol: str = Field(..., description="Trade symbol")
    direction: Direction = Field(..., description="Trade direction")
    asset_class: AssetClass | None = Field(..., description="Asset class")
    result_r: Decimal | None = Field(None, description="Trade Result (R-multiple)")
    net_pnl: Decimal | None = Field(None, description="Trade Net PnL")
    image_urls: list[str] = Field(..., description="Trade image URLs")
    tags: list[str] = Field(..., description="Trade tags/taxonomies")


class ModelBookCheckinVariant(BaseModel):
    """Model Book entry variant representing a starred check-in."""

    model_config = ConfigDict(from_attributes=True)

    type: Literal["checkin"] = "checkin"
    id: uuid.UUID = Field(..., description="Check-in ID")
    date: dt.datetime = Field(..., description="Date of the check-in (stored as datetime for sorting)")
    market_phase: str | None = Field(..., description="Market phase")
    screenshot_urls: list[str] = Field(..., description="Check-in screenshot URLs")
    regime_color: str | None = Field(None, description="Calculated regime color")
    target_indices: list[TargetIndexRead] = Field(default_factory=list, description="Target indices")


ModelBookEntryResponse = Annotated[
    ModelBookTradeVariant | ModelBookCheckinVariant,
    Field(discriminator="type"),
]


class ModelBookEntriesPage(BaseModel):
    """Paginated list of Model Book entries."""

    items: list[ModelBookEntryResponse] = Field(..., description="Mixed list of trades and check-ins.")
    total: int = Field(..., description="Total number of matched entries.")
    page: int = Field(..., description="Current page number.")
    per_page: int = Field(..., description="Number of items per page.")
    next_cursor: str | None = Field(None, description="Cursor for the next page if using cursor pagination.")


class ModelBookPatchRequest(BaseModel):
    """Payload for starring/unstarring an entity."""

    is_modelbook: bool = Field(..., description="True to star, false to unstar.")

