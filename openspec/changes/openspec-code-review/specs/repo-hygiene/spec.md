## ADDED Requirements

### Requirement: Dev-artifact scripts must be removed from the repository
Temporary patch and fix scripts that were used for one-off data corrections MUST NOT
remain in the repository. They create confusion about the canonical code path and clutter
the project root.

#### Scenario: fix_*.py and patch_*.py scripts are absent
- **WHEN** the repository root and `backend/` directory are listed
- **THEN** no files matching `fix_*.py`, `patch_*.py`, or `update_*.py` SHALL be present

---

### Requirement: Obsolete router files must be deleted
Any router file whose own docstring declares it obsolete or no longer needed MUST be
deleted. Its import (if any) in `router.py` MUST also be removed.

#### Scenario: trades_update.py is absent
- **WHEN** `backend/app/api/v1/` is listed
- **THEN** `trades_update.py` SHALL NOT be present
- **THEN** `router.py` SHALL NOT import from `trades_update`

---

### Requirement: Dead service code must be removed
Private helper methods in service files that are never called internally or externally
MUST be removed to reduce cognitive overhead during future reviews.

#### Scenario: _issue_token_pair is removed
- **WHEN** `auth_service.py` is reviewed
- **THEN** `_issue_token_pair` SHALL NOT exist
- **THEN** no call site for `_issue_token_pair` SHALL exist

---

### Requirement: German strings in production code must have English comments
Any string literal in German that appears in production code (error messages, log messages,
comments) MUST have an accompanying English comment or be translated.
Tax domain strings are an exception if they are legally mandated German tax terms.

#### Scenario: tax_service.py German strings are annotated
- **WHEN** `tax_service.py` is reviewed
- **THEN** each German string literal SHALL have an adjacent English comment explaining
  its meaning and why it is in German (e.g. `# German tax regulation term`)
