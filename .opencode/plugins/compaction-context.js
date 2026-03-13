/**
 * compaction-context.js
 *
 * OpenCode plugin — injects project iteration status and active task context
 * into the system prompt during session compaction.
 *
 * When a session is compacted (conversation history is summarised to reduce
 * token usage), this plugin appends a structured context block so the agent
 * retains awareness of:
 *   - The current iteration and its status
 *   - The standard task flow for the project
 *   - Key architectural constraints that must not be forgotten
 */

export default {
  name: "compaction-context",
  description:
    "Injects Trading Journal iteration status and task flow into compacted sessions",

  /**
   * Hook: onCompaction
   *
   * Called when the session is about to be compacted. The returned string is
   * appended to the compacted system prompt.
   *
   * @returns {string} Additional context to include in the compacted prompt.
   */
  onCompaction() {
    return `
---
## Trading Journal — Active Project Context (injected by compaction-context plugin)

### Iteration Status
| Iteration | Focus                                                | Status      |
|-----------|------------------------------------------------------|-------------|
| 1         | Data model, Pydantic schemas, base API + DB          | Planning    |
| 2         | User model, Account model, JWT auth (multi-user)     | Open        |
| 3         | Performance metrics, statistical aggregation          | Open        |
| 4         | Broker import: IBKR + Schwab (file upload + parser)  | Open        |
| 5         | Time-series endpoints, initial frontend               | Open        |
| 6         | Playbook, tagging, psychological notes               | Open        |
| 7         | Live broker API connections (IBKR TWS, Schwab API)   | Stretch     |

### Standard Task Flow
For every feature that touches both backend and frontend:
1. backend-engineer + frontend-engineer   (parallel)
2. test-writer                            (after both complete)
3. openapi-docs                           (parallel with test-writer, after backend)
4. code-reviewer                          (after all implementation is done)
5. docs-writer                            (update AGENTS.md + api-usage.md)
6. changelog-writer                       (append to [Unreleased] section)

### Key Constraints (never violate)
- All code, comments, docstrings, and commit messages must be in English.
- mypy strict mode — no untyped code.
- SQLAlchemy async only — no sync DB calls.
- All schema changes via Alembic migrations — never create_all() in production.
- TimescaleDB hypertables via op.execute("SELECT create_hypertable(...)") in migrations.
- Alpine-based Docker images only.
- uv exclusively for Python dependency management.
- JWT auth: access token 15 min, refresh token httpOnly cookie 7 days.
- trades table has account_id FK — User/Account model must precede trade data.
---
`;
  },
};
