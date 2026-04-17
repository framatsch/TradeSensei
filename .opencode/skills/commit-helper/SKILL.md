---
name: commit-helper
description: Create consistent git commits for the tradesensei project using the project's emoji+category format and Keep a Changelog conventions
license: MIT
compatibility: opencode
metadata:
  toolchain: git
  runner: tools/commit_helper
---

## What I do

Guide the creation of well-formed commit messages that align with this project's
conventions and map cleanly to CHANGELOG.md entries.

## Commit format

```
[emoji] [category]: [concise title]

[Optional: brief explanation of what changed]
[Optional: why it matters]
```

## Categories and their CHANGELOG mapping

| Category | Emoji | CHANGELOG section | Use when |
|----------|-------|------------------|---------|
| `feat` | ✨ | Added | New endpoint, component, or model |
| `fix` | 🔧 | Fixed | Bug fix in any layer |
| `infra` | 📦 | Changed | Docker, K8s, CI/CD |
| `db` | 🗄️ | Changed | Alembic migration, model change |
| `api` | 🔌 | Added | FastAPI route or schema change |
| `frontend` | 🖥️ | Added | Next.js / React component |
| `test` | 🧪 | Changed | Test additions |
| `docs` | 📝 | Changed | AGENTS.md, user guide, OpenAPI |
| `config` | ⚙️ | Changed | pyproject.toml, settings, uv.lock |
| `security` | 🔒 | Security | Auth, JWT, permissions |

## When to use me

Use this skill when you are ready to commit changes and want to:
- Determine the correct commit category
- Format the message correctly
- Validate an existing commit message

## How to run

```bash
# Interactive guided commit
python tools/commit_helper.py

# Auto-suggest category, then prompt for title
python tools/commit_helper.py --auto

# Stage everything first, then commit
python tools/commit_helper.py --auto --add-all

# Validate last commit message
python tools/commit_helper.py --validate

# Preview without committing
python tools/commit_helper.py --auto --preview
```

## Validation rules

A commit message passes when:
- First line starts with a recognized emoji
- Contains `:` separator between category and title
- First line is 10–100 characters

## Relationship to CHANGELOG.md

After committing, the `changelog-writer` agent maps these categories to the
correct CHANGELOG.md sections. Consistent commit messages make that automatic.

## Release Notes & GitHub Release

When creating a GitHub release, the release notes body **MUST** be a single line
without literal newlines. The shell (zsh) will break on multi-line strings passed
directly to `gh release create`.

**Preferred approach — write to a temp file first:**

```bash
# 1. Write the notes body to a file
cat > /tmp/release_notes.md << 'HEREDOC'
## v0.8.0 - Title

### Fixed
- **🔧 Fix**: Description of the fix

### Added
- Description of new feature
HEREDOC

# 2. Create the release using the file
gh release create v0.8.0 --title "v0.8.0" --notes-file /tmp/release_notes.md

# 3. Clean up
rm /tmp/release_notes.md
```

**Why**: `--notes "..."` with literal newlines inside double quotes causes the
shell to split the argument at each line break, interpreting subsequent lines as
commands (`command not found`). Using `--notes-file` or a heredoc avoids this entirely.
