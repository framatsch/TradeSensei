"""Common Pydantic schemas: response envelopes and pagination types."""

from typing import Any, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseEnvelope[T](BaseModel):
    """Uniform response wrapper for all non-paginated API responses.

    Attributes:
        data: The actual response payload.
        meta: Optional metadata dictionary (e.g. request-id, timing).
    """

    data: T = Field(
        ...,
        description=(
            "The primary response payload. The type depends on the endpoint — "
            "e.g. a single TradeRead object or a CursorPage of TradeRead objects."
        ),
    )
    meta: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Optional metadata accompanying the response, such as request "
            "identifiers or server-side timing information. Empty by default."
        ),
        examples=[{}, {"request_id": "abc-123", "duration_ms": 12}],
    )


class CursorPage[T](BaseModel):
    """Paginated response using opaque cursor tokens.

    Attributes:
        items: The list of result items for this page.
        next_cursor: Base-64 encoded cursor pointing to the next page,
            or ``None`` if this is the last page.
        total: Total item count across all pages, or ``None`` when the
            count is prohibitively expensive to compute.
    """

    items: list[T] = Field(
        ...,
        description="The list of result items contained in this page.",
    )
    next_cursor: str | None = Field(
        ...,
        description=(
            "Opaque, base-64 encoded cursor token pointing to the next page. "
            "Pass this value as the `cursor` query parameter in your next request. "
            "Null if this is the last page."
        ),
        examples=["eyJpZCI6IjNmYTg1ZjY0LTU3MTcifQ==", None],
    )
    total: int | None = Field(
        ...,
        description=(
            "Total number of items across all pages, or null when computing "
            "the exact count would be prohibitively expensive."
        ),
        examples=[142, None],
    )


class OffsetPage[T](BaseModel):
    """Paginated response using limit/offset.

    Attributes:
        items: The list of result items for this page.
        total: Total item count.
        limit: The limit used.
        offset: The offset used.
    """

    items: list[T] = Field(description="The list of result items.")
    total: int = Field(description="Total number of items.")
    limit: int = Field(description="The limit used.")
    offset: int = Field(description="The offset used.")
