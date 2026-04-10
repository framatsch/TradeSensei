## ADDED Requirements

### Requirement: security.py must not catch Exception after specific exceptions
`except` clauses in `security.py` that already catch `JWTError` and `ValueError` MUST NOT
also include a bare `Exception`. Catching `Exception` after specific types masks programming
errors that should surface as 500 responses in logs.

#### Scenario: verify_token uses narrow except
- **WHEN** token verification encounters an unexpected error type
- **THEN** it SHALL propagate as an unhandled exception (visible in logs as 500)
- **THEN** the except clause SHALL read `except (JWTError, ValueError) as exc:`

---

### Requirement: In-memory OTT blocklist must document its production limitation
The `_used_ott_jti: set[str]` module-level set in `security.py` is not suitable for
multi-process production deployments. It MUST have a comment referencing this limitation
and (optionally) a tracking issue.

#### Scenario: _used_ott_jti has documented limitation
- **WHEN** a developer reads `security.py`
- **THEN** a comment above `_used_ott_jti` SHALL document the in-memory limitation
  and note that a Redis-backed implementation is needed for multi-process deployments

---

### Requirement: Magic numbers and strings must be in constants.py
All numeric and string literals with project-wide significance MUST be defined as named
constants in `backend/app/core/constants.py`. Inline literals are only permitted for
locally-scoped values with no reuse potential.

#### Scenario: BYTES_PER_MB constant exists
- **WHEN** any file needs to convert megabytes to bytes
- **THEN** it SHALL import `BYTES_PER_MB` from `app.core.constants`

#### Scenario: FLEX_POLL constants exist
- **WHEN** `flex_import_service.py` polls the FLEX API
- **THEN** it SHALL use `FLEX_POLL_INTERVAL_SECONDS` and `FLEX_POLL_MAX_ATTEMPTS` from `app.core.constants`

#### Scenario: SCREENSHOT_MAX_FILE_SIZE_MB constant exists
- **WHEN** `screenshots.py` validates upload size
- **THEN** it SHALL use `SCREENSHOT_MAX_FILE_SIZE_MB` from `app.core.constants`

---

### Requirement: Any type annotations must have justification comments
Any use of `typing.Any` in `core/` files MUST be accompanied by an inline comment
explaining why a more specific type cannot be used.

#### Scenario: config.py parse_cors_origins is annotated
- **WHEN** mypy processes `config.py`
- **THEN** the `Any` in `parse_cors_origins` SHALL have a justification comment

---

### Requirement: Except-with-reraise must have a justification comment
An `except Exception` block that immediately re-raises (e.g. after a `session.rollback()`)
MUST have an inline comment clarifying the intent, so it is not confused with a bare swallow.

#### Scenario: database.py get_session except is commented
- **WHEN** a developer reads `get_session` in `database.py`
- **THEN** the `except Exception` block SHALL have a comment such as:
  `# Re-raise after rollback — caller sees the original exception`

---

### Requirement: Duplicate constants must be consolidated
If the same constant is defined under multiple names in `constants.py`, one definition
MUST be removed and all call sites updated to use the canonical name.

#### Scenario: NOTE_CONTENT_MAX_LENGTH duplicate is removed
- **WHEN** `constants.py` is read
- **THEN** only one name for the note content length limit SHALL exist
- **THEN** all imports across the codebase SHALL use that single name
