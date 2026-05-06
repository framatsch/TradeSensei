## Context

In the "Account-Centric Broker Sync" updates, `Account` entities became explicitly linked to `Portfolio` entities via `portfolio_id`. Each `Portfolio` has a `base_currency`. Currently, `Account` still has a `currency` field that users must manually select during creation. This introduces an unnecessary manual step and risk of divergence between the account and its parent portfolio. Users report this selection is redundant.

## Goals / Non-Goals

**Goals:**
- Remove user-facing currency selection from account creation and editing forms.
- Ensure newly created accounts inherit the currency of their parent portfolio.
- Prevent modifying the currency of existing accounts.

**Non-Goals:**
- Database migration to remove the `accounts.currency` column entirely. Given the complexity of existing schemas, queries, and constraints, we will leave the column in the DB and default its value from the portfolio during account creation to satisfy the constraint safely. A future database cleanup can remove it if fully redundant.
- Changing `Portfolio.base_currency` rules.
- Multi-currency portfolio support.

## Decisions

- **Decision 1:** Retain `accounts.currency` column but make it a derived value.
  - *Rationale:* Modifying SQLAlchemy models and generating an Alembic migration to drop the column might require sweeping changes across metric calculations and trade models that currently join or query `account.currency`. Setting it automatically upon creation preserves backend logic but achieves the user-facing goal.
  - *Alternative:* Drop the column immediately. This would be cleaner but higher risk, requiring more complex tasks.
- **Decision 2:** Remove `currency` from `AccountCreate` schema payload.
  - *Rationale:* Since `portfolio_id` is provided on creation, the backend `AccountService.create` can easily fetch the portfolio and inject its `base_currency` into the account model being saved.
  - *Alternative:* Make `currency` optional. Not ideal because clients might accidentally supply it.

## Risks / Trade-offs

- [Risk] Legacy API clients might still send `currency` in the JSON payload, leading to validation errors. → Mitigation: We can accept it but ignore it, or remove it and let strict validation reject it. We will remove it and ensure the frontend is updated. If external API clients exist, they might break. Since this is an internal tool, breaking changes are acceptable if the frontend is synced.
