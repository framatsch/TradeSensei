## Context

Developers and operators need to recover user accounts or manage test users easily without relying on web-based "Forgot Password" flows, which might require working email infrastructure that isn't always configured locally.

## Goals / Non-Goals

**Goals:**
- Provide a robust CLI script in the `backend/` directory (`reset_password.py`).
- Read CLI arguments cleanly (using `argparse`).
- Securely hash passwords exactly as the core application does.
- Increment the token version to enforce secure session invalidation.

**Non-Goals:**
- This is not an exposed web endpoint.
- We will not integrate this into the frontend.

## Decisions

- **Argument Parsing**: We will use the built-in `argparse` module because it allows mutually exclusive groups natively (either `-u` OR `-e`, but not both) and is standard in Python.
- **Passlib/Bcrypt Workaround**: The project uses an outdated `passlib` version that crashes with `bcrypt >= 4.0.0` due to a missing `__about__` attribute. We will inject a targeted monkeypatch early in the script to provide a dummy `__about__` attribute so that `passlib` can import correctly without breaking.
- **Environment Fallbacks**: We will defensively handle missing `SECRET_KEY` and `DATABASE_URL` by setting environment fallbacks or printing helpful warnings, since users often run CLI scripts without pre-loading `.env` files. We use a dummy string for `SECRET_KEY` since password hashing does not require the true secret key, just the DB connection.

## Risks / Trade-offs

- **Risk**: A user runs the script without the environment variable `DATABASE_URL` set, and the script silently updates a different database.
  - **Mitigation**: Warn the user explicitly if falling back to the default local connection string.
