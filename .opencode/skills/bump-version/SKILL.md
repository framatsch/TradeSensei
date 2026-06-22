---
name: bump-version
description: Automate version bumping across project files and prepare releases or development versions
license: MIT
compatibility: opencode
metadata:
  toolchain: python, git, gh
---

## What I do

Automate version bumping across all project files (`package.json`, `frontend/package.json`, `backend/pyproject.toml`) and prepare a consistent release or development version. This is the skill to use when the user asks to "create release version X.Y.Z".

## Usage

### 🚀 Release Bumping & GitHub Release
Sets a clean version for a formal release, pushes it, creates the release, and prepares the next dev cycle.

```bash
python tools/bump_version.py 0.10.0 --release
```

### 🌙 Development Version Bumping
Adds `.dev0` suffix for development versions (PEP 440 compliant).

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
- Development versions use `.dev0` suffix (PEP 440 compliant).

## Workflow: Creating a Release

When the user asks to "create release version <X.Y.Z>":

1. **Check latest tag (optional)**
   `git describe --tags --abbrev=0`

2. **Ensure CHANGELOG.md `[Unreleased]` is populated**
   The bump script will fail if `[Unreleased]` is empty. Before bumping:
   - Check `## [Unreleased]` in CHANGELOG.md contains entries for all commits since the last tag
   - If empty, add entries under `## [Unreleased]` grouped by `### Added`, `### Fixed`, `### Changed`
   - Also ensure compare links at the bottom of CHANGELOG.md are up to date:
     ```
     [unreleased]: https://github.com/scheffold/TradeSensei/compare/v<X.Y.Z>...HEAD
     [<X.Y.Z>]: https://github.com/scheffold/TradeSensei/compare/v<prev>...v<X.Y.Z>
     ```
   - Commit the CHANGELOG update before bumping:
     ```bash
     git add CHANGELOG.md
     git commit -m "📝 docs: update CHANGELOG for <X.Y.Z>"
     ```

3. **Run bump script** (moves `[Unreleased]` → `[X.Y.Z]` in CHANGELOG automatically)
   ```bash
   python tools/bump_version.py <X.Y.Z> --release --yes
   ```
   This commits the version bump and creates+pushes the tag.

4. **Create GitHub Release** from the CHANGELOG content
   The bump script extracts the `[Unreleased]` content as release notes. If it ran
   successfully with `--release`, create the GitHub release:
   ```bash
   cat > /tmp/release_notes.md << 'HEREDOC'
   ## v<X.Y.Z> - <short title>

   ### Fixed
   - <entry from CHANGELOG>
   HEREDOC
   gh release create v<X.Y.Z> --title "v<X.Y.Z>" --notes-file /tmp/release_notes.md
   rm /tmp/release_notes.md
   ```

5. **Start next dev cycle**
   Ask the user what the next version should be (e.g. `X.Y+1.Z` or `X.Y.Z+1`).
   ```bash
   python tools/bump_version.py <next-version> --snapshot --yes
   git push origin main
   ```
