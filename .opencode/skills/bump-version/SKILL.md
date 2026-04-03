## What I do

Automate version bumping across all project files (`package.json`, `frontend/package.json`, `backend/pyproject.toml`) and prepare a consistent release or snapshot checkpoint. This is the skill to use when the user asks to "create release version X.Y.Z".

## Usage

### 🚀 Release Bumping & GitHub Release
Sets a clean version for a formal release, pushes it, creates the release, and prepares the next dev cycle.

```bash
python tools/bump_version.py 0.10.0
```

### 🌙 Snapshot Bumping (Nightly)
Adds `-SNAPSHOT+<git-hash>` for development or nightly builds.

```bash
python tools/bump_version.py 0.10.1 --snapshot
```

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
