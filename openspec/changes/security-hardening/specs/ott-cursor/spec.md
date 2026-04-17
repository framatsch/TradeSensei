## ADDED Requirements

### Requirement: One-time tokens cannot be replayed across processes

The system SHALL store consumed OTT JTIs in a persistent database table.
A second use of the same JTI — regardless of which process or pod handles it —
SHALL be rejected.

#### Scenario: First use of OTT succeeds
- **WHEN** `POST /auth/verify-ott` (or equivalent) is called with a valid, unused OTT
- **THEN** the JTI is inserted into `used_otts`
- **AND** the request succeeds and returns the expected response

#### Scenario: Replay of same OTT is rejected
- **WHEN** the same OTT is submitted a second time
- **THEN** `used_otts` already contains the JTI
- **AND** the response is `401 Unauthorized`
- **AND** no new session is created

#### Scenario: Expired JTIs are cleaned up
- **WHEN** `consume_ott_jti()` is called
- **THEN** rows with `expires_at < now()` are deleted from `used_otts` in the same transaction
- **AND** the `used_otts` table does not grow unboundedly

#### Scenario: Concurrent replay attempts are safe
- **WHEN** two requests submit the same OTT simultaneously
- **THEN** exactly one request succeeds (PRIMARY KEY constraint ensures atomicity)
- **AND** the other receives `401 Unauthorized`

---

### Requirement: Cursor pagination is scoped to the authenticated user

All paginated list endpoints that accept a cursor parameter SHALL enforce
`user_id = current_user.id` in the WHERE clause independently of the cursor
value. A crafted cursor pointing to another user's record SHALL return no data.

#### Scenario: Valid cursor returns next page of own trades
- **WHEN** `GET /api/v1/trades?cursor=<valid_cursor>` is called by User A
- **THEN** the response contains the next page of User A's trades

#### Scenario: Cursor from another user's session returns empty result
- **WHEN** User B submits a cursor that encodes a trade_id belonging to User A
- **THEN** the query returns an empty result (not User A's data)
- **AND** no error is raised — the WHERE user_id clause simply matches nothing

#### Scenario: Tampered cursor is rejected
- **WHEN** a cursor with an invalid HMAC signature is submitted
- **THEN** response is `400 Bad Request`
- **AND** error body: `{"code": "invalid_cursor", "message": "Cursor is invalid or has been tampered with."}`

---

## MODIFIED Requirements

### Requirement: CLI password reset uses interactive input

The `reset_password.py` CLI tool SHALL NOT accept the new password as a
command-line argument. It SHALL read the password interactively via
`getpass.getpass()` when run in a terminal, or from stdin when piped.

#### Scenario: Interactive password reset
- **WHEN** `reset_password.py -u alice` is called in a terminal
- **THEN** the script prompts "New password: " (input hidden)
- **AND** prompts "Confirm password: " (input hidden)
- **AND** if the two inputs match, the password is updated
- **AND** if they do not match, the script prints an error and exits with code 1

#### Scenario: Non-interactive password reset via stdin
- **WHEN** `echo "newpass" | reset_password.py -u alice` is called
- **THEN** the password is read from stdin without a prompt
- **AND** the password is updated

#### Scenario: `-p` / `--password` argument does not exist
- **WHEN** `reset_password.py -u alice -p newpass` is called
- **THEN** argparse raises an error: unrecognised arguments: -p
- **AND** the password is NOT updated

---

### Requirement: Auth token verification uses narrow exception handling

`security.py` exception clauses around JWT verification SHALL catch only
`JWTError` and `ValueError`. A bare `except Exception` SHALL NOT be present
unless it immediately re-raises (rollback pattern), and MUST have a comment
explaining the intent.

#### Scenario: Unexpected exception propagates as 500
- **WHEN** an unexpected error (e.g. AttributeError) occurs during token verification
- **THEN** the exception propagates unhandled
- **AND** the ASGI server logs a 500 Internal Server Error
- **AND** the error is visible in application logs
