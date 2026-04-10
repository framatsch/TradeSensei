## ADDED Requirements

### Requirement: Bare except clauses must log before continuing
Any `except Exception` block that does not re-raise MUST call a structured logger before
proceeding. Silent exception swallowing is prohibited per AGENTS.md.

#### Scenario: user_service.py logs JSON parse failure
- **WHEN** `UserService` fails to parse features JSON
- **THEN** it SHALL call `logger.warning("Failed to parse features JSON for user %s", user_id, exc_info=True)`
- **THEN** it SHALL continue with the fallback value `merged_features = {}`

---

### Requirement: Class docstrings must immediately follow the class declaration
Python class docstrings MUST be placed immediately after the `class Foo:` line, before
any method definitions. A docstring placed after a method is not associated with the class.

#### Scenario: TradeService class docstring is correctly placed
- **WHEN** Python parses `TradeService`
- **THEN** `TradeService.__doc__` SHALL return the intended class description
- **THEN** the docstring SHALL appear on the line immediately following `class TradeService:`

---

### Requirement: Standard library imports must be at module level
`import` statements for standard library modules (e.g. `import json`, `import calendar`)
MUST appear at the top of the file, not inside function or method bodies.

#### Scenario: user_service.py has top-level json import
- **WHEN** the file is parsed
- **THEN** `import json` SHALL appear in the module-level import block
- **THEN** no `import json` SHALL appear inside a method body

#### Scenario: timeseries_service.py has top-level calendar import
- **WHEN** the file is parsed
- **THEN** `import calendar` SHALL appear in the module-level import block

---

### Requirement: Deferred imports to break circular dependencies must be commented
Any `import` statement placed inside a function or method body to break a circular
dependency MUST have an inline comment explaining the reason.

#### Scenario: trade_service.py deferred import is annotated
- **WHEN** `ExecutionService` is imported inside a `TradeService` method
- **THEN** the import line SHALL have a comment such as:
  `# Deferred import to break circular dependency: execution → trade`

---

### Requirement: type: ignore comments must include a justification
Every `# type: ignore[...]` comment MUST include a short explanation of why the
suppression is necessary, to allow future reviewers to evaluate its continued necessity.

#### Scenario: user_service.py type: ignore is justified
- **WHEN** mypy processes `user_service.py`
- **THEN** any `# type: ignore` SHALL be followed by a comment explaining the reason

---

### Requirement: Services must have complete module-level docstrings
Every `services/*.py` file MUST have a module-level docstring that describes the
service's responsibility in at least one sentence.

#### Scenario: execution.py has module docstring
- **WHEN** `pydoc` or an IDE introspects `app.services.execution`
- **THEN** a non-empty module docstring SHALL be returned

#### Scenario: cash_transaction_service.py has module docstring
- **WHEN** `pydoc` or an IDE introspects `app.services.cash_transaction_service`
- **THEN** a descriptive module docstring SHALL be returned

#### Scenario: saved_trade_filter_service.py has module docstring
- **WHEN** `pydoc` or an IDE introspects `app.services.saved_trade_filter_service`
- **THEN** a descriptive module docstring SHALL be returned
