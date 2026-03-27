## What I do

Automate version bumping across all project files (`package.json`, `frontend/package.json`) and prepare a consistent release or snapshot checkpoint.

## Usage

### 🚀 Release Bumping
Sets a clean version for a formal release.

```bash
python tools/bump_version.py 0.5.0
```

### 🌙 Snapshot Bumping (Nightly)
Adds `-SNAPSHOT+<git-hash>` for development or nightly builds.

```bash
python tools/bump_version.py 0.5.1 --snapshot
```

## Guardrails

- Version must follow Semantic Versioning (`X.Y.Z`).
- Both root and frontend `package.json` must be kept in sync.
- Snapshot versions include the short git hash for traceability.

## Workflow

1.  **Select new version**
    Check latest tag: `git describe --tags --abbrev=0`
2.  **Run bump script**
    `python tools/bump_version.py <new-version> [--snapshot]`
3.  **Review changes**
    `git diff package.json frontend/package.json`
4.  **Automatic Snapshot Progression (Post-Release)**
    After a formal release (e.g., `0.5.1`), the skill automatically prepares the next development cycle:
    `python tools/bump_version.py <next-patch-version> --snapshot`
    Example: `0.5.1` -> `0.5.2-SNAPSHOT`
5.  **Commit using `commit-helper`**
    Category: `config` (Emoji: ⚙️)
    Message: `config: bump version to <version>`
6.  **Tag and push (Releases only)**
    `git tag -a v<version> -m "Release <version>"`
    `git push origin main --tags`
