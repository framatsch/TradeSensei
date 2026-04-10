## ADDED Requirements

### Requirement: backend-engineer agent must embed anti-pattern guardrails
The `backend-engineer` agent definition (`.opencode/agents/backend-engineer.md`) MUST
contain an explicit "Anti-Patterns — Never Do These" section covering every class of
violation found during the code review. This section acts as a persistent preventive
control so the same mistakes are not introduced in future implementation sessions.

#### Scenario: Agent definition contains service-layer anti-patterns
- **WHEN** the backend-engineer agent file is read
- **THEN** it SHALL document that `HTTPException` must never be imported in services
- **THEN** it SHALL document that raw SQLAlchemy queries must never appear in services
- **THEN** it SHALL document that `assert` must never be used as a runtime guard
- **THEN** it SHALL document that `session.commit()` must never be called inside a service
- **THEN** it SHALL document that `_repo._session` (private attribute) must never be accessed

#### Scenario: Agent definition contains API-layer anti-patterns
- **WHEN** the backend-engineer agent file is read
- **THEN** it SHALL document that services must never be constructed inline in route handlers
- **THEN** it SHALL document that raw `AsyncSession` must never be forwarded to a service
- **THEN** it SHALL document that `BaseModel` subclasses must never be defined in `api/v1/` files
- **THEN** it SHALL document that `response_model` must always be declared on `@router.*`
- **THEN** it SHALL document that all responses must be wrapped in `ResponseEnvelope`
- **THEN** it SHALL document that bare integer status codes must not be used

#### Scenario: Agent definition contains core-layer anti-patterns
- **WHEN** the backend-engineer agent file is read
- **THEN** it SHALL document that `except (SpecificError, Exception)` patterns are forbidden
- **THEN** it SHALL document that module-level mutable connection singletons must use lifespan
- **THEN** it SHALL document that `Any` requires a justification comment
- **THEN** it SHALL document that magic numbers/strings must go in `constants.py`

#### Scenario: Agent definition contains exception-handling anti-patterns
- **WHEN** the backend-engineer agent file is read
- **THEN** it SHALL document that `NotFoundError` must always be caught and mapped to 404
- **THEN** it SHALL document that dead code must be deleted, not left in place
- **THEN** it SHALL document that bare `except Exception` requires logging or re-raising

---

### Requirement: Anti-pattern guardrails must include corrected code examples
For each anti-pattern in the agent definition where the correct pattern is non-obvious,
a code example MUST be provided showing both the wrong pattern (commented "Wrong") and
the correct pattern (commented "Correct").

#### Scenario: _get_service DI pattern has a code example
- **WHEN** the backend-engineer agent file is read
- **THEN** the `_get_service` dependency injection pattern SHALL have an inline code block
  showing the correct `Depends(_get_service)` usage alongside the wrong inline construction

#### Scenario: Deferred import pattern has a comment example
- **WHEN** the backend-engineer agent file is read
- **THEN** the deferred import anti-pattern section SHALL show the required comment format:
  `# Deferred import to break circular dependency: X → Y`
