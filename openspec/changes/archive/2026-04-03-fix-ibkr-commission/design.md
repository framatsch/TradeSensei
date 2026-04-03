## Context

The IBKR XML parser in the `tradejournal` backend currently extracts the commission from either the `ibCommission` or `commission` attribute. The code uses a logical OR: `elem.get("ibCommission") or elem.get("commission")`. In Python, the string `"0"` is truthy, meaning if IBKR sets `ibCommission="0"` and puts the actual fees in `commission="-1.50"`, the parser returns `"0"` and ignores the actual commission. This causes zero commissions to be imported when fees actually exist.

## Goals / Non-Goals

**Goals:**
- Correctly parse and persist commissions for IBKR XML imports when `ibCommission` is `"0"` but `commission` has a non-zero value.
- Maintain existing logic that prevents crashing on malformed strings.

**Non-Goals:**
- Modifying other broker parsers (e.g., Schwab).
- Changing the schema or database fields for trades.

## Decisions

**Decision 1: Calculate maximum of absolute values instead of logical OR**
- **Rationale**: Both `ibCommission` and `commission` can be negative values in the XML. By parsing both to `Decimal`, taking their absolute values, and then using `max()`, we guarantee that if one is `"0"` and the other is `"-1.50"`, we correctly capture `1.50`.
- **Alternatives Considered**: Using a string check `if elem.get("ibCommission") not in (None, "", "0", "0.0")`. This is more fragile and doesn't handle other zero-equivalent formats gracefully.

## Risks / Trade-offs

- **Risk**: Doubling of commissions if IBKR splits them across both attributes but neither is zero.
  - **Mitigation**: Using `max()` instead of `+` ensures we don't accidentally double-count if they report the same fee twice. However, if they report `ibCommission="-1.00"` and `commission="-1.50"` (representing a total of `-2.50`), taking `max()` will yield `1.50` instead of `2.50`. Given IBKR's Activity Flex Query structure, `commission` usually contains the total (or they are exclusive). Taking `max()` is safer than adding, though we could add them if `commission` strictly represents third-party fees. Wait, `ibCommission` is IB commission, `taxes` is separate, and `commission` might be the sum. Taking `max()` is safest to avoid double counting without thorough XML schema validation.
