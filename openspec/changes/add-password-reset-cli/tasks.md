## 1. CLI Setup & Parsing

- [x] 1.1 Create `backend/reset_password.py` file with basic executable permissions and python shebang.
- [x] 1.2 Implement `argparse` configuration to accept mutually exclusive `-u/--username` or `-e/--email` arguments.
- ~~[x] 1.3 Add required `-p/--password` argument to argparse.~~ **Removed** — superseded by `security-hardening` tasks 4.1–4.4 which implement `getpass`-based interactive input instead. Do NOT add a `-p` argument.
- [x] 1.4 Add help and epilog descriptions to argparse.

## 2. Environment & Dependency Management

- [x] 2.1 Add fallback logic for missing `SECRET_KEY` env var to satisfy pydantic settings.
- [x] 2.2 Add fallback logic for `DATABASE_URL` (and warning message) if not present in the environment.
- [x] 2.3 Implement monkeypatch workaround for `passlib` and `bcrypt` (`__about__` attribute error) prior to importing settings and sqlalchemy.

## 3. Database & Core Logic

- [x] 3.1 Initialize `async_sessionmaker` and `create_async_engine` from settings.
- [x] 3.2 Query the `User` model using either the provided username or email.
- [x] 3.3 Return an error message and exit cleanly if the user is not found.
- [x] 3.4 Hash the new password using `hash_password` from `app.core.security`.
- [x] 3.5 Update the user's `hashed_password` and increment `refresh_token_version`.
- [x] 3.6 Commit the transaction and close the database engine cleanly.
- [x] 3.7 Print success message confirming the operation worked.
