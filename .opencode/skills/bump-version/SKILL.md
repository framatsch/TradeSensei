---
name: bump-version
description: Automate version bumping across project files and prepare releases or snapshot versions
license: MIT
compatibility: opencode
metadata:
  toolchain: python, git, gh
---

## What I do

Automate version bumping across all project files (`package.json`, `frontend/package.json`, `backend/pyproject.toml`) and prepare a consistent release or snapshot checkpoint. This is the skill to use when the user asks to "create release version X.Y.Z".

## Usage

### 🚀 Release Bumping & GitHub Release
Sets a clean version for a formal release, pushes it, creates the release, and prepares the next dev cycle.

```bash
python tools/bump_version.py 0.10.0 --release
```

### 🌙 Snapshot Bumping (Nightly)
Adds `-SNAPSHOT+<git-hash>` for development or nightly builds.

```bash
python tools/bump_version.py 0.10.1 --snapshot
```

### 🏷️ Release + GitHub Release (non-interactive)

```bash
# Commit the bump, create and push a tag, and create a GitHub release with notes
python tools/bump_version.py 0.10.0 --release --gh-release --yes --notes "Release 0.10.0 - fixes and improvements"
```

Flags added:
- `--release`: commit the bump, create an annotated tag `vX.Y.Z`, push tag and HEAD to origin
- `--gh-release`: after pushing the tag, create a GitHub release using `gh release create`
- `--yes`: assume yes for interactive confirmations (useful for CI)
- `--notes`: provide inline release notes text (used to create a temporary notes file for `gh`)

Changelog integration:
- If `--release` is used and `CHANGELOG.md` contains a `## [Unreleased]` section, the script will move the Unreleased content into a new `## [X.Y.Z] - YYYY-MM-DD` section, add a compare link, and use the extracted text as release notes for the GitHub release (unless `--notes` is provided).

## Guardrails

- Version must follow Semantic Versioning (`X.Y.Z`).
- `package.json`, `frontend/package.json`, and `backend/pyproject.toml` MUST all be kept in sync.
- Snapshot versions include the short git hash for traceability.

## Workflow: Creating a Release

When the user asks to "create release version <X.Y.Z>":

1. **Check latest tag (optional)**
   `git describe --tags --abbrev=0`

2. **Run bump script**
   `python tools/bump_version.py <X.Y.Z>`

3. **Commit the version bump**
   ```bash
   git add package.json frontend/package.json backend/pyproject.toml
   git commit -m "⚙️ config: bump version to <X.Y.Z>"
   ```

4. **Tag the release**
   ```bash
   git tag -a v<X.Y.Z> -m "v<X.Y.Z>"
   git push origin main v<X.Y.Z>
   ```

5. **Create GitHub Release**
   Create a temporary file for notes to avoid shell newline issues:
   ```bash
   cat > /tmp/release_notes.md << 'HEREDOC'
   ## v<X.Y.Z>

   ### Changed
   - Describe changes here
   HEREDOC
   gh release create v<X.Y.Z> --title "v<X.Y.Z>" --notes-file /tmp/release_notes.md
   rm /tmp/release_notes.md
   ```

6. **Automatic Snapshot Progression (Next Version)**
   Immediately ask the user what the *next* version should be (e.g. `0.11.0` or `0.10.1-SNAPSHOT`).
   If they approve, run `python tools/bump_version.py <next-version> [--snapshot]` and commit the new development version:
   ```bash
   git add package.json frontend/package.json backend/pyproject.toml
   git commit -m "⚙️ config: start next dev cycle <next-version>"
   git push origin main
   ```
