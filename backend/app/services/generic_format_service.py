"""Publication of model-derived generic format schema and CSV template."""

import csv
import io

from app.schemas.generic_import import GenericExecutionDocumentV1, GenericFormatSchema
from app.services.brokers.generic.validation import csv_columns, parse_document


class GenericFormatService:
    """Publish the same contract used by import validation."""

    def schema(self) -> GenericFormatSchema:
        """Return the complete JSON Schema, including local definitions."""
        return GenericFormatSchema.model_validate(GenericExecutionDocumentV1.model_json_schema())

    def template(self) -> bytes:
        """Generate a header and two valid example fills in model field order."""
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=csv_columns())
        writer.writeheader()
        writer.writerows(
            [
                {
                    "external_id": "example-fill-1",
                    "executed_at": "2026-01-02T14:30:00Z",
                    "symbol": "AAPL",
                    "asset_class": "EQUITY",
                    "side": "BUY",
                    "position_effect": "OPEN",
                    "quantity": "1",
                    "price": "100",
                    "currency": "USD",
                },
                {
                    "external_id": "example-fill-2",
                    "executed_at": "2026-01-05T14:30:00Z",
                    "symbol": "AAPL",
                    "asset_class": "EQUITY",
                    "side": "SELL",
                    "position_effect": "CLOSE",
                    "quantity": "1",
                    "price": "110",
                    "currency": "USD",
                },
            ]
        )
        content = output.getvalue().encode("utf-8")
        parse_document(content, "template.csv")
        return content
