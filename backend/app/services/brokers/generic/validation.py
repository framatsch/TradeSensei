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

"""Validate generic input before any persistence takes place."""

from collections import defaultdict

from pydantic import ValidationError

from app.core.constants import GENERIC_ERROR_LIMIT, GENERIC_FORMAT, GENERIC_VERSION
from app.core.exceptions import GenericFormatValidationError
from app.schemas.generic_import import GenericExecutionDocumentV1, GenericExecutionV1, GenericOptionV1
from app.utils.parsers.generic_loader import GenericLoadError, load_csv, load_json


def csv_columns() -> list[str]:
    """Derive CSV header order from the public execution models."""
    columns: list[str] = []
    for name in GenericExecutionV1.model_fields:
        columns.extend(f"option_{field}" for field in GenericOptionV1.model_fields) if name == "option" else columns.append(name)
    return columns


def parse_document(content: bytes, filename: str) -> GenericExecutionDocumentV1:
    """Decode and validate the complete document with safe, capped issues."""
    csv_input = filename.lower().endswith(".csv")
    offset = 1 if csv_input else 0
    try:
        if csv_input:
            required = {name for name, field in GenericExecutionV1.model_fields.items() if field.is_required()}
            rows = load_csv(content, csv_columns(), required, {"quantity", "price", "commission", "realized_pnl", "option_strike"})
            payload: object = {"format": GENERIC_FORMAT, "version": GENERIC_VERSION, "executions": rows}
        else:
            payload = load_json(content)
    except GenericLoadError as exc:
        raise GenericFormatValidationError([{"row": exc.row, "field": exc.field, "code": exc.code, "message": "Invalid execution file structure"}]) from exc
    try:
        document = GenericExecutionDocumentV1.model_validate(payload)
    except ValidationError as exc:
        issues: list[dict[str, object]] = []
        for error in exc.errors(include_input=False, include_context=False, include_url=False)[:GENERIC_ERROR_LIMIT]:
            loc = error["loc"]
            row = loc[1] + offset if len(loc) > 1 and isinstance(loc[1], int) else None
            fields = loc[2:] if row is not None else loc
            field = ".".join(str(part) for part in fields)
            code = error["type"]
            if code == "option_requirement":
                field = "option"
            elif code == "multiplier_required":
                field = "multiplier"
            elif code == "format_marker":
                field = "format"
            issues.append({"row": row, "field": field or "document", "code": code, "message": "Field validation failed"})
        raise GenericFormatValidationError(issues) from exc
    ids: dict[str, list[int]] = defaultdict(list)
    for index, execution in enumerate(document.executions):
        if execution.external_id is not None:
            ids[execution.external_id].append(index + offset)
    issues = []
    if ids and sum(len(indices) for indices in ids.values()) != len(document.executions):
        issues.append({"row": None, "field": "external_id", "code": "mixed_id_strategy", "message": "All executions must use the same ID strategy"})
    for indices in ids.values():
        if len(indices) > 1:
            for index in indices:
                issues.append({"row": index, "field": "external_id", "code": "duplicate_external_id", "message": "Fill ID must be unique within the file"})
                if len(issues) >= GENERIC_ERROR_LIMIT:
                    break
        if len(issues) >= GENERIC_ERROR_LIMIT:
            break
    if issues:
        raise GenericFormatValidationError(issues[:GENERIC_ERROR_LIMIT])
    return document
