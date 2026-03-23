"""Pydantic DTOs for the broker file import endpoint."""

import uuid

from pydantic import BaseModel, Field


class ImportResult(BaseModel):
    """Result of a broker file import operation.

    Attributes:
        broker: Broker identifier used for this import (e.g. ``"ibkr"``).
        filename: Original filename supplied in the upload request.
        trades_parsed: Total number of trade rows successfully parsed from
            the file.
        trades_created: Number of trades actually persisted to the database.
        trades_skipped: Number of rows that were skipped due to parse
            errors or other non-fatal issues.
        warnings: Human-readable descriptions of each skipped row.
    """

    broker: str = Field(
        ...,
        description=("Broker identifier used for this import (e.g. 'ibkr', 'schwab')."),
        examples=["ibkr", "schwab"],
    )
    filename: str = Field(
        ...,
        description="Original filename supplied with the upload request.",
        examples=["activity_statement.csv", "trade_history.csv"],
    )
    trades_parsed: int = Field(
        ...,
        ge=0,
        description=(
            "Total number of trade rows successfully parsed from the file. "
            "This is the sum of trades_created and trades_skipped."
        ),
        examples=[42, 0],
    )
    trades_created: int = Field(
        ...,
        ge=0,
        description="Number of trades that were persisted to the database.",
        examples=[40, 0],
    )
    trades_skipped: int = Field(
        ...,
        ge=0,
        description=(
            "Number of rows that were skipped due to non-fatal parse errors. "
            "Inspect the warnings list for details."
        ),
        examples=[2, 0],
    )
    cash_transactions_parsed: int = Field(
        default=0,
        ge=0,
        description="Total number of cash transactions successfully parsed from the file.",
        examples=[10, 0],
    )
    cash_transactions_created: int = Field(
        default=0,
        ge=0,
        description="Number of cash transactions that were persisted to the database.",
        examples=[10, 0],
    )
    cash_transactions_skipped: int = Field(
        default=0,
        ge=0,
        description="Number of cash transactions that were skipped due to non-fatal parse errors.",
        examples=[0],
    )
    warnings: list[str] = Field(
        default_factory=list,
        description=(
            "Human-readable descriptions of rows that were skipped during "
            "import. Empty when all rows were imported successfully."
        ),
        examples=[
            ["IBKR row 3: skipped — Row has only 5 columns; expected at least 16."],
            [],
        ],
    )


class FlexImportRequest(BaseModel):
    """Request body for the IBKR Flex Query automatic import endpoint.

    Attributes:
        query_id: IBKR Flex Query ID configured in Account Management.
        account_id: Optional UUID of the broker account to associate
            imported trades with.
        from_date: Optional start date (``YYYYMMDD``) to restrict the
            report period sent to the Flex API.
    """

    query_id: str = Field(
        ...,
        min_length=1,
        description=(
            "IBKR Flex Query ID as configured in the IBKR Account Management "
            "portal under Reports → Flex Queries."
        ),
        examples=["123456"],
    )
    account_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "UUID of the broker account to associate imported trades with. "
            "Omit to create trades without an account association."
        ),
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6", None],
    )
    from_date: str | None = Field(
        default=None,
        pattern=r"^\d{8}$",
        description=(
            "Optional start date in ``YYYYMMDD`` format. "
            "When supplied, only trades on or after this date are included "
            "in the Flex Query report."
        ),
        examples=["20240101", None],
    )
    overwrite_manually_edited: bool = Field(
        default=False,
        description=(
            "When true, trades that have been manually edited are no longer "
            "protected and will be overwritten by the incoming import data."
        ),
    )
