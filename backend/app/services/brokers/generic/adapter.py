"""File-only adapter for the public Trade Sensei execution format."""

from collections import defaultdict
from decimal import Decimal

from app.core.constants import GENERIC_ID_STRATEGY_KEY
from app.models.account import AccountType
from app.models.trade import AssetClass, Direction
from app.schemas.broker_raw_transaction import BrokerRawTransactionCreate
from app.schemas.corporate_action import CorporateActionCreateRequest
from app.services.brokers.contracts import BrokerAdapter, BrokerType, CanonicalImportBatch, ImportPolicy
from app.services.brokers.generic.validation import parse_document
from app.utils.raw_identity import execution_fingerprint, normalized_decimal


class GenericFileImport:
    """Validate complete JSON/CSV input and project it onto canonical records."""

    accepted_extensions = frozenset({"json", "csv"})

    def rejected_extension_message(self, extension: str) -> str | None:
        """Use the registry's standard extension rejection."""
        del extension
        return None

    def parse(self, content: bytes, filename: str) -> CanonicalImportBatch:
        """Map validated fills and splits without accessing database or HTTP."""
        document = parse_document(content, filename)
        records: list[BrokerRawTransactionCreate] = []
        ordinals: dict[str, int] = defaultdict(int)
        for execution in document.executions:
            option = execution.option
            conid = execution.contract_id
            if conid is None and option is not None:
                conid = f"{execution.symbol}:{option.expiry:%Y%m%d}:{option.right}:{normalized_decimal(option.strike)}"
            if execution.external_id is not None:
                identity = f"x:{execution.external_id}"
            else:
                fingerprint = execution_fingerprint(
                    execution.executed_at,
                    execution.symbol,
                    execution.asset_class,
                    conid,
                    execution.side,
                    execution.quantity,
                    execution.price,
                    execution.currency,
                )
                ordinals[fingerprint] += 1
                identity = f"f:{fingerprint}:{ordinals[fingerprint]}"
            multiplier = execution.multiplier or 1
            # FIFO treats a non-null pnl as the closing-leg marker and computes
            # P&L from prices; mirror the IBKR/Schwab parsers for pure closes.
            pnl = execution.realized_pnl
            if pnl is None and execution.position_effect == "CLOSE":
                pnl = Decimal("0")
            gross = execution.quantity * execution.price * multiplier
            net_cash = (-gross if execution.side == "BUY" else gross) - execution.commission
            records.append(
                BrokerRawTransactionCreate(
                    id=f"generic:{identity}",
                    broker_type=BrokerType.GENERIC.value,
                    symbol=execution.symbol,
                    conid=conid,
                    asset_class=AssetClass(execution.asset_class),
                    direction=Direction.LONG if execution.side == "BUY" else Direction.SHORT,
                    quantity=execution.quantity,
                    price=execution.price,
                    commission=execution.commission,
                    executed_at=execution.executed_at,
                    currency=execution.currency,
                    multiplier=multiplier,
                    open_close={"OPEN": "O", "CLOSE": "C"}.get(execution.position_effect or ""),
                    is_mixed_execution=execution.position_effect == "CLOSE_OPEN",
                    strike=option.strike if option else None,
                    expiry=option.expiry if option else None,
                    option_type=option.right if option else None,
                    pnl=pnl,
                    order_id=execution.order_id,
                    net_cash=net_cash if execution.order_id else None,
                    raw_data=execution.model_dump(mode="json", exclude_none=True),
                )
            )
        actions = [
            CorporateActionCreateRequest(
                symbol=action.symbol, date=action.date, ratio=action.ratio, old_conid=action.old_contract_id, new_conid=action.new_contract_id
            )
            for action in document.corporate_actions
        ]
        return CanonicalImportBatch(
            executions=records,
            corporate_actions=actions,
            warnings=[],
            id_strategy="external_id" if document.executions[0].external_id is not None else "fingerprint",
        )


GENERIC_ADAPTER = BrokerAdapter(
    key=BrokerType.GENERIC,
    account_type=AccountType.GENERIC,
    policy=ImportPolicy(
        self_heal_pending_protected_close=False, corporate_actions_overwrite=False, account_scoped_identity=True, id_strategy_property=GENERIC_ID_STRATEGY_KEY
    ),
    file_import=GenericFileImport(),
)
