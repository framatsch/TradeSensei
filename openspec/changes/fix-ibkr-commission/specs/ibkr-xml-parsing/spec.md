## ADDED Requirements

### Requirement: Safely parse commission fields
The IBKR XML parser MUST correctly extract the commission from the `<Trade>` or `<Execution>` elements even when `ibCommission` is `"0"` and `commission` holds the non-zero fee.

#### Scenario: Fallback commission value extraction
- **WHEN** an XML element has `ibCommission="0"` and `commission="-2.50"`
- **THEN** the parser extracts `2.50` as the commission value instead of `0`.

#### Scenario: Maximum commission value extraction
- **WHEN** an XML element has `ibCommission="-1.00"` and `commission="-1.50"`
- **THEN** the parser extracts `1.50` as the commission value, avoiding double-counting or picking the smaller value.
