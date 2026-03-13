"""Pydantic DTOs for the broker file import endpoint."""

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
