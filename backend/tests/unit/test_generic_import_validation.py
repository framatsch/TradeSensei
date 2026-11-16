"""Value-safe, all-or-nothing validation of the public execution format."""

import csv
import io
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.core.exceptions import GenericFormatValidationError
from app.services.brokers.generic.validation import parse_document

pytestmark = pytest.mark.unit


def execution(**changes: object) -> dict[str, object]:
    return {
        "executed_at": "2026-01-02T14:30:00Z",
        "symbol": " aapl ",
        "asset_class": "EQUITY",
        "side": "BUY",
        "quantity": "1",
        "price": "100",
        "currency": "USD",
        **changes,
    }


def document(rows: list[dict[str, object]], **changes: object) -> bytes:
    return json.dumps({"format": "tradesensei.executions", "version": "1.0", "executions": rows, **changes}).encode()


def csv_file(rows: list[dict[str, object]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode()


def issues(content: bytes, filename: str = "input.json") -> list[dict[str, object]]:
    with pytest.raises(GenericFormatValidationError) as error:
        parse_document(content, filename)
    result = error.value.errors
    assert result
    assert all(set(issue) == {"row", "field", "code", "message"} for issue in result)
    assert all("input" not in issue and "ctx" not in issue for issue in result)
    return result


@pytest.mark.parametrize("version", ["1.0", "1.12"])
def test_parse_document_valid_minimal_document_normalizes_fields(version: str) -> None:
    parsed = parse_document(document([execution()], version=version), "input.json")
    fill = parsed.executions[0]
    assert fill.symbol == "AAPL"
    assert fill.executed_at.tzinfo == UTC
    assert fill.commission == Decimal("0")
    assert fill.multiplier is None
    assert parsed.corporate_actions == []


@pytest.mark.parametrize(
    ("field", "value"), [("version", "2.0"), ("version", "1"), ("version", "1.a"), ("source", "x" * 101), ("executions", []), ("extra", True)]
)
def test_parse_document_invalid_envelope_reports_field(field: str, value: object) -> None:
    assert any(issue["field"] == field for issue in issues(document([execution()], **{field: value})))


@pytest.mark.parametrize("marker", [None, "wrong"])
def test_parse_document_wrong_marker_validates_before_rows(marker: object) -> None:
    payload = {"version": "1.0", "executions": [{"price": "sensitive"}]}
    if marker is not None:
        payload["format"] = marker
    result = issues(json.dumps(payload).encode())
    assert len(result) == 1
    assert result[0]["field"] == "format"


@pytest.mark.parametrize("field", ["executed_at", "symbol", "asset_class", "side", "quantity", "price", "currency"])
def test_parse_document_missing_required_execution_field_reports_row(field: str) -> None:
    row = execution()
    del row[field]
    assert any(issue["field"] == field and issue["row"] == 0 for issue in issues(document([row])))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("executed_at", "2026-01-02T14:30:00"),
        ("executed_at", 123),
        ("executed_at", (datetime.now(UTC) + timedelta(hours=25)).isoformat()),
        ("symbol", ""),
        ("asset_class", "STOCK"),
        ("side", "LONG"),
        ("position_effect", "O"),
        ("quantity", "0"),
        ("quantity", "-1"),
        ("quantity", True),
        ("quantity", "NaN"),
        ("price", "-12345.6789"),
        ("price", "Infinity"),
        ("commission", "-1"),
        ("currency", "usd"),
        ("currency", "US"),
        ("currency", "123"),
        ("multiplier", 0),
        ("multiplier", 1.5),
        ("multiplier", True),
        ("external_id", " "),
        ("external_id", "x" * 101),
        ("order_id", ""),
        ("order_id", "x" * 101),
        ("contract_id", ""),
        ("contract_id", "x" * 51),
        ("comission", "99"),
    ],
)
def test_parse_document_invalid_execution_field_reports_safe_error(field: str, value: object) -> None:
    result = issues(document([execution(**{field: value})]))
    assert any(issue["field"] == field and issue["row"] == 0 for issue in result)
    assert "12345.6789" not in json.dumps(result)


@pytest.mark.parametrize("asset_class", ["EQUITY", "FOREX", "CRYPTO", "FUTURE", "OPTION"])
def test_parse_document_supported_asset_classes_accept_valid_contracts(asset_class: str) -> None:
    changes: dict[str, object] = {"asset_class": asset_class, "price": "0", "realized_pnl": "-10"}
    if asset_class in {"OPTION", "FUTURE"}:
        changes["multiplier"] = 100
    if asset_class == "OPTION":
        changes["option"] = {"strike": "100", "expiry": "2026-12-18", "right": "C"}
    assert parse_document(document([execution(**changes)]), "input.json").executions[0].asset_class == asset_class


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"asset_class": "OPTION", "multiplier": 100}, "option"),
        ({"option": {"strike": "100", "expiry": "2026-12-18", "right": "C"}}, "option"),
        ({"asset_class": "FUTURE"}, "multiplier"),
        ({"asset_class": "OPTION", "option": {"strike": "100", "expiry": "2026-12-18", "right": "C"}}, "multiplier"),
    ],
)
def test_parse_document_contract_cross_field_violation_reports_specific_field(changes: dict[str, object], field: str) -> None:
    assert issues(document([execution(**changes)]))[0]["field"] == field


@pytest.mark.parametrize(("field", "value"), [("strike", "0"), ("strike", "-1"), ("expiry", "bad-date"), ("right", "CALL"), ("unknown", "secret")])
def test_parse_document_invalid_option_field_reports_nested_path(field: str, value: object) -> None:
    option = {"strike": "100", "expiry": "2026-12-18", "right": "C", field: value}
    assert issues(document([execution(asset_class="OPTION", multiplier=100, option=option)]))[0]["field"] == f"option.{field}"


def test_parse_document_json_numbers_are_lossless_and_offsets_normalize() -> None:
    content = document([execution(executed_at="2026-01-02T16:30:00+02:00", external_id=" fill-1 ")]).replace(b'"100"', b"0.12345678")
    fill = parse_document(content, "input.json").executions[0]
    assert fill.price == Decimal("0.12345678")
    assert fill.external_id == "fill-1"
    assert fill.executed_at == datetime(2026, 1, 2, 14, 30, tzinfo=UTC)


@pytest.mark.parametrize("extension", ["json", "csv"])
def test_parse_document_duplicate_trimmed_ids_reports_both_rows(extension: str) -> None:
    rows = [execution(external_id=" TT-1 "), execution(external_id="TT-1")]
    content = document(rows) if extension == "json" else csv_file(rows)
    result = issues(content, f"input.{extension}")
    assert [issue["row"] for issue in result] == ([0, 1] if extension == "json" else [1, 2])
    assert all(issue["code"] == "duplicate_external_id" for issue in result)


def test_parse_document_mixed_ids_rejects_entire_file() -> None:
    assert issues(document([execution(external_id="one"), execution()]))[0]["code"] == "mixed_id_strategy"


@pytest.mark.parametrize("duplicate", [False, True])
def test_parse_document_more_than_200_errors_caps_safe_list(duplicate: bool) -> None:
    row = execution(external_id="one") if duplicate else execution(price="-12345.6789", quantity="-98765.4321", realized_pnl="sensitive-pnl")
    result = issues(document([row] * 250))
    assert len(result) == 200
    assert not any(value in json.dumps(result) for value in ["12345.6789", "98765.4321", "sensitive-pnl"])


@pytest.mark.parametrize("bom", [b"", b"\xef\xbb\xbf"])
def test_parse_document_valid_csv_matches_json_with_empty_optional_cells(bom: bytes) -> None:
    row = execution(external_id="one", commission="", order_id="")
    parsed = parse_document(bom + csv_file([row]), "input.CSV")
    assert parsed == parse_document(document([execution(external_id="one")]), "input.json")


def test_parse_document_csv_flattened_option_and_integer_multiplier_accepts() -> None:
    row = execution(asset_class="OPTION", multiplier="100", option_strike="120", option_expiry="2026-12-18", option_right="P")
    fill = parse_document(csv_file([row]), "input.csv").executions[0]
    assert fill.option is not None and fill.option.strike == Decimal("120")
    assert fill.multiplier == 100


@pytest.mark.parametrize("value", ["1.234,50", "1,234.50", "1e3", "NaN", "Infinity"])
def test_parse_document_csv_noncanonical_number_reports_data_row(value: str) -> None:
    result = issues(csv_file([execution(price=value)]), "input.csv")
    assert result[0]["field"] == "price" and result[0]["row"] == 1
    assert result[0]["code"] == "invalid_number"


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"1,2,3\n",
        b"symbol,symbol\nA,A\n",
        b"executed_at,symbol,asset_class,side,quantity,price,currency,typo\n",
        b"executed_at,symbol,asset_class,side,quantity,price,currency\n1,2\n",
        b"\xff",
    ],
)
def test_parse_document_malformed_csv_rejects_structure(content: bytes) -> None:
    issues(content, "input.csv")


@pytest.mark.parametrize("content", [b"{", b"\xff", b'{"format":"tradesensei.executions","format":"wrong"}', b'{"quantity":NaN}', b"[]"])
def test_parse_document_malformed_json_rejects_structure(content: bytes) -> None:
    issues(content)


@pytest.mark.parametrize("ratio", ["0.1", "2"])
def test_parse_document_valid_split_accepts_reverse_and_forward(ratio: str) -> None:
    split = {"type": "SPLIT", "symbol": "xyz", "date": "2026-05-01", "ratio": ratio, "old_contract_id": "old", "new_contract_id": "new"}
    parsed = parse_document(document([execution()], corporate_actions=[split]), "input.json")
    assert parsed.corporate_actions[0].ratio == Decimal(ratio)
    assert parsed.corporate_actions[0].symbol == "XYZ"


@pytest.mark.parametrize(("field", "value"), [("ratio", "0"), ("ratio", "-1"), ("type", "DIVIDEND"), ("date", "bad"), ("extra", "secret")])
def test_parse_document_invalid_split_rejects_entire_document(field: str, value: object) -> None:
    split = {"type": "SPLIT", "symbol": "XYZ", "date": "2026-05-01", "ratio": "0.1", field: value}
    assert any(issue["field"] == field for issue in issues(document([execution()], corporate_actions=[split])))
