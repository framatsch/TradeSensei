## Why

When importing IBKR XML Activity Flex Queries, commission fees are sometimes ignored. The XML parser reads the `ibCommission` attribute first, which IBKR often sets to `"0"` when no direct IB commission is charged. Because `"0"` is logically truthy in Python, the fallback to the `commission` attribute (which contains the actual third-party fees) never triggers. This results in the trade commission being incorrectly saved as 0.00.

## What Changes

- Update the IBKR XML parser to safely parse both `ibCommission` and `commission` attributes into `Decimal` values.
- Calculate the total commission by taking the maximum of both absolute values (since both represent fees that should be captured, and at least one might be zero).
- Add a unit test to verify that when `ibCommission="0"` and `commission="-2.50"`, the parser correctly extracts `2.50`.

## Capabilities

### New Capabilities

- `ibkr-xml-parsing`: Defines the requirements for parsing Interactive Brokers Flex Query XML files, specifically correctly interpreting commission fees and fallback logic.

### Modified Capabilities

## Impact

- `backend/app/utils/parsers/ibkr_xml.py` (Parser logic)
- `backend/tests/test_import.py` (Unit tests)
