## 1. Tests

- [x] 1.1 Add a unit test in `backend/tests/test_import.py` to verify that when `ibCommission="0"` and `commission="-2.50"`, the parser correctly extracts `2.50`.
- [x] 1.2 Add a unit test in `backend/tests/test_import.py` to verify that when `ibCommission="-1.00"` and `commission="-1.50"`, the parser extracts `1.50` (max of absolute values).

## 2. Implementation

- [x] 2.1 Update `_parse_trade_element` in `backend/app/utils/parsers/ibkr_xml.py` to parse `ibCommission` and `commission` separately into `Decimal` values, then assign `commission = max(ib_comm, gen_comm)`.
- [x] 2.2 Apply the same fix to `_parse_execution_element` in `backend/app/utils/parsers/ibkr_xml.py`.
- [x] 2.3 Apply the same fix to the `asset_category == "CASH"` handling section inside `_parse_trade_element`.

## 3. Verification

- [x] 3.1 Run `pytest backend/tests/test_import.py` to ensure all tests pass.
- [x] 3.2 Run linting (`ruff check`) and type checking (`mypy --strict`).
