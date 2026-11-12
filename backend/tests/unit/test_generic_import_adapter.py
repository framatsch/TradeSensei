"""Canonical mapping and deterministic account-scoped fill identity."""

from decimal import Decimal

import pytest

from app.models.trade import Direction
from app.services.brokers.generic.adapter import GENERIC_ADAPTER, GenericFileImport
from app.utils.raw_identity import normalized_decimal, stamped_raw_id
from tests.unit.test_generic_import_validation import document, execution

pytestmark = pytest.mark.unit


def raw(**changes: object):
    return GenericFileImport().parse(document([execution(**changes)]), "input.json").executions[0]


@pytest.mark.parametrize(("side", "direction", "cash"), [("BUY", Direction.LONG, "-201"), ("SELL", Direction.SHORT, "199")])
@pytest.mark.parametrize(("effect", "open_close", "mixed"), [(None, None, False), ("OPEN", "O", False), ("CLOSE", "C", False), ("CLOSE_OPEN", None, True)])
def test_parse_side_and_position_effect_maps_canonical_fields(
    side: str, direction: Direction, cash: str, effect: str | None, open_close: str | None, mixed: bool
) -> None:
    fill = raw(side=side, position_effect=effect, order_id="order", quantity="2", commission="1", realized_pnl="-5")
    assert fill.direction == direction
    assert fill.open_close == open_close and fill.is_mixed_execution is mixed
    assert fill.net_cash == Decimal(cash)
    assert fill.pnl == Decimal("-5") and fill.order_id == "order"
    assert fill.raw_data["side"] == side


def test_parse_option_contract_derivation_separates_strikes_and_normalizes_scale() -> None:
    def option(strike: str, **changes: object):
        return raw(asset_class="OPTION", multiplier=100, option={"strike": strike, "expiry": "2026-12-18", "right": "C"}, **changes)

    assert option("580.00").conid == option("580").conid == "AAPL:20261218:C:580"
    assert option("580").conid != option("590").conid
    assert option("580", contract_id="broker-contract").conid == "broker-contract"
    assert raw().conid is None and raw().net_cash is None
    assert option("580", order_id="order").net_cash == Decimal("-10000")


def test_parse_fingerprint_ignores_restatable_fields_and_source() -> None:
    original = raw()
    changed = raw(
        commission="9", realized_pnl="-77", position_effect="CLOSE", order_id="order", price="100.00", quantity="1.000", executed_at="2026-01-02T16:30:00+02:00"
    )
    assert original.id == changed.id
    batch = GenericFileImport().parse(document([execution()], source="different broker name"), "input.json")
    assert batch.executions[0].id == original.id


@pytest.mark.parametrize(
    "changes",
    [
        {"executed_at": "2026-01-02T14:30:01Z"},
        {"symbol": "SPY"},
        {"asset_class": "CRYPTO"},
        {"contract_id": "one"},
        {"side": "SELL"},
        {"quantity": "2"},
        {"price": "101"},
        {"currency": "EUR"},
    ],
)
def test_parse_fingerprint_changed_identity_field_changes_hash(changes: dict[str, object]) -> None:
    assert raw(**changes).id != raw().id


def test_parse_identical_fills_assigns_per_fingerprint_ordinals_in_file_order() -> None:
    rows = [execution(), execution(symbol="SPY"), execution(), execution()]
    ids = [fill.id for fill in GenericFileImport().parse(document(rows), "input.json").executions]
    assert [value.rsplit(":", 1)[1] for value in ids] == ["1", "1", "2", "3"]
    assert len(set(ids)) == 4
    assert ids[0].rsplit(":", 1)[0] == ids[2].rsplit(":", 1)[0]


def test_stamped_raw_id_namespaces_accounts_and_disjoint_strategies() -> None:
    assert stamped_raw_id("generic:x:1001", "user", "a", True) == "user:generic:a:x:1001"
    assert stamped_raw_id("generic:x:1001", "user", "a", True) != stamped_raw_id("generic:x:1001", "user", "b", True)
    assert stamped_raw_id("ibkr:1001", "user", "a", False) == "user:ibkr:1001"
    assert stamped_raw_id("user:ibkr:1001", "user", "a", False) == "user:ibkr:1001"
    with pytest.raises(ValueError, match="Account is required"):
        stamped_raw_id("generic:x:1001", "user", None, True)


def test_normalized_decimal_large_values_does_not_round_to_decimal_context() -> None:
    assert normalized_decimal(Decimal("123456789012345678901234567890.1234567890")) == "123456789012345678901234567890.123456789"


def test_generic_adapter_split_policy_is_insert_only_and_capabilities_file_only() -> None:
    assert not GENERIC_ADAPTER.policy.corporate_actions_overwrite
    assert not GENERIC_ADAPTER.policy.self_heal_pending_protected_close
    assert GENERIC_ADAPTER.remote_sync is GENERIC_ADAPTER.connection is GENERIC_ADAPTER.account_binding is None
    split = {"type": "SPLIT", "symbol": "XYZ", "date": "2026-05-01", "ratio": "0.1", "old_contract_id": "old", "new_contract_id": "new"}
    batch = GenericFileImport().parse(document([execution()], corporate_actions=[split]), "input.json")
    assert batch.corporate_actions[0].ratio == Decimal("0.1")
    assert batch.corporate_actions[0].old_conid == "old" and batch.corporate_actions[0].new_conid == "new"
    assert batch.id_strategy == "fingerprint"
    assert raw(external_id="1001").id == "generic:x:1001"
