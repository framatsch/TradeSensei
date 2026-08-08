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

"""Pydantic DTOs for the broker file import endpoint."""

import uuid

from pydantic import BaseModel, Field


class FreshStartResult(BaseModel):
    """Result of a fresh-start import operation.

    Attributes:
        account_id: The account that was reset.
        executions_deleted: Number of LogicalExecution rows deleted.
        trades_deleted: Number of Trade rows deleted.
        import_result: The result of the import that followed the reset.
    """

    account_id: uuid.UUID = Field(
        ...,
        description="UUID of the account that was reset.",
    )
    executions_deleted: int = Field(
        ...,
        ge=0,
        description="Number of LogicalExecution rows deleted during reset.",
    )
    trades_deleted: int = Field(
        ...,
        ge=0,
        description="Number of Trade rows deleted during reset.",
    )
    import_result: "ImportResult" = Field(
        ...,
        description="Import result from the file processed after the reset.",
    )


class ClearTradesResult(BaseModel):
    """Result of clearing all trade data for an account.

    Attributes:
        trades_deleted: Number of Trade rows deleted.
        executions_deleted: Number of LogicalExecution rows deleted.
    """

    trades_deleted: int = Field(
        ...,
        ge=0,
        description="Number of Trade rows deleted during account reset.",
    )
    executions_deleted: int = Field(
        ...,
        ge=0,
        description="Number of LogicalExecution rows deleted during account reset.",
    )


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
        raw_transactions_created: Number of broker raw transactions newly
            inserted during this import.
        raw_suppressed_skipped: Number of BrokerRawTransaction records
            skipped because their ``suppressed`` flag is ``True``.
        raw_deleted_skipped: Number of BrokerRawTransaction records skipped
            because their linked execution has ``deleted=True`` (user intent
            preserved — execution was previously deleted by the user).
        trades_protected_reconciled: Number of metadata-protected trades
            (``is_manually_edited=True``) that absorbed new executions
            during this import instead of being skipped.
        trades_protected_skipped: Number of metadata-protected positions
            skipped because no existing trade could be resolved for them.
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
        description=("Total number of trade rows successfully parsed from the file. This is the sum of trades_created and trades_skipped."),
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
        description=("Number of rows that were skipped due to non-fatal parse errors. Inspect the warnings list for details."),
        examples=[2, 0],
    )
    raw_transactions_created: int = Field(
        default=0,
        ge=0,
        description=("Number of broker raw transactions newly inserted during this import. Re-importing identical files should produce 0."),
        examples=[339, 0],
    )
    raw_suppressed_skipped: int = Field(
        default=0,
        ge=0,
        description=(
            "Number of raw broker transactions skipped because their ``suppressed`` flag is ``True``. These records are permanently excluded from all imports."
        ),
        examples=[0, 3],
    )
    raw_deleted_skipped: int = Field(
        default=0,
        ge=0,
        description=(
            "Number of raw broker transactions skipped because their linked "
            "execution was previously deleted by the user (``deleted=True``). "
            "Re-import will not recreate these executions."
        ),
        examples=[0, 1],
    )
    trades_protected_reconciled: int = Field(
        default=0,
        ge=0,
        description=(
            "Number of metadata-protected trades (``is_manually_edited=True``) "
            "that absorbed new incoming executions during this import (linked "
            "and, if applicable, closed) instead of being skipped. Structural "
            "fields are updated; user metadata is never touched."
        ),
        examples=[0, 1],
    )
    trades_protected_skipped: int = Field(
        default=0,
        ge=0,
        description=(
            "Number of metadata-protected positions skipped during this import "
            "because no existing trade could be resolved to reconcile them "
            "onto. See ``warnings`` for the affected symbol/date."
        ),
        examples=[0, 1],
    )
    warnings: list[str] = Field(
        default_factory=list,
        description=("Human-readable descriptions of rows that were skipped during import. Empty when all rows were imported successfully."),
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
        description=("IBKR Flex Query ID as configured in the IBKR Account Management portal under Reports → Flex Queries."),
        examples=["123456"],
    )
    account_id: uuid.UUID | None = Field(
        default=None,
        description=("UUID of the broker account to associate imported trades with. Omit to create trades without an account association."),
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6", None],
    )
    from_date: str | None = Field(
        default=None,
        pattern=r"^\d{8}$",
        description=("Optional start date in ``YYYYMMDD`` format. When supplied, only trades on or after this date are included in the Flex Query report."),
        examples=["20240101", None],
    )
    overwrite_manually_edited: bool = Field(
        default=False,
        description=("When true, trades that have been manually edited are no longer protected and will be overwritten by the incoming import data."),
    )
